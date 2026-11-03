"""FTS5 BM25, cosine candidates, reciprocal rank fusion, and honest local eval."""

from contextlib import closing
from pathlib import Path

import yaml

from brainext.search.embed import budget, get_embedder, prefixed
from brainext.search.index import connect, live_docs
from brainext.search.normalize import fts_query
from brainext.search.vectors import VectorBackend, pack


def rrf(text_ids, vector_ids, k=60):
    scores = {}
    for ranking in (text_ids, vector_ids):
        for rank, id in enumerate(dict.fromkeys(ranking), 1):
            scores[id] = scores.get(id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


def search(config, query, *, mode="hybrid", k=8, path_prefix=None, include_drafts=False,
           embedder=None, group_by_file=False) -> dict:
    output = {"exit_code": 0, "report": {}, "results": [], "mode": mode, "warnings": []}
    if (mode not in {"text", "vector", "hybrid"} or not isinstance(query, str)
            or type(k) is not int or k < 1):
        return {**output, "exit_code": 1, "warnings": ["Arama parametreleri geçersiz"]}
    connection = connect(config, readonly=True)
    if connection is None:
        return {**output, "mode": "text", "warnings": ["İndeks yok; önce brainext index çalıştırın"]}
    with closing(connection) as db:
        docs = live_docs(config, db, include_drafts=include_drafts, path_prefix=path_prefix)
        chunks = {row["id"]: dict(row) for row in db.execute("SELECT * FROM chunks")
                  if row["doc_id"] in docs}
        text_scores, vector_scores = {}, {}
        expression = fts_query(query, config.prefix_min_length)
        if expression:
            for row in db.execute("""SELECT rowid,bm25(chunks_fts) AS score FROM chunks_fts
                                   WHERE chunks_fts MATCH ? ORDER BY score,rowid""", (expression,)):
                if row["rowid"] in chunks:
                    text_scores[row["rowid"]] = -row["score"]
                    if len(text_scores) == 50:
                        break
        if mode != "text":
            model, warnings = get_embedder(config, embedder)
            output["warnings"].extend(warnings)
            meta = dict(db.execute("SELECT key,value FROM meta"))
            if model and (meta.get("embedding_model") != config.embedding_model
                          or meta.get("embedding_dim") != str(model.dimension)):
                model = None
                output["warnings"].append("Model/boyut uyuşmuyor; index --reembed gerekli")
            if model:
                try:
                    query_text = prefixed(query, config.embedding_model, query=True)
                    if model.count_tokens(query_text) > budget(model):
                        raise ValueError("Sorgu token bütçesini aşıyor")
                    vectors = list(model.embed([query_text]))
                    if len(vectors) != 1:
                        raise ValueError("Sorgu embedding sayısı uyuşmuyor")
                    vector = vectors[0]
                    pack(vector, model.dimension)
                    rows = [(row["chunk_id"], row["embedding"]) for row in db.execute(
                        "SELECT chunk_id,embedding FROM chunk_vec") if row["chunk_id"] in chunks]
                    if not rows:
                        raise ValueError("Uygun vektör yok")
                    backend = VectorBackend(db)
                    output["report"]["vector_backend"] = backend.name
                    for id, score in backend.rank(rows, vector):
                        if id not in vector_scores:
                            vector_scores[id] = score
                        if len(vector_scores) == 50:
                            break
                except (ImportError, OSError, RuntimeError, ValueError):
                    output["warnings"].append("Vektör arama kullanılamıyor; yalnızca metin")
            if not vector_scores:
                output["mode"] = "text"
        text_ranks = {id: rank for rank, id in enumerate(text_scores, 1)}
        vector_ranks = {id: rank for rank, id in enumerate(vector_scores, 1)}
        if output["mode"] == "hybrid":
            ranking = rrf(text_scores, vector_scores, config.rrf_k)
        elif output["mode"] == "vector":
            ranking = list(vector_scores.items())
        else:
            ranking = list(text_scores.items())
        # Embedding may be slow; a source can become private while it is running.
        still_live = live_docs(config, db, include_drafts=include_drafts, path_prefix=path_prefix)
        seen = set()
        for id, score in ranking:
            chunk = chunks[id]
            if chunk["doc_id"] not in still_live:
                continue
            doc = docs[chunk["doc_id"]]
            if group_by_file and doc["path"] in seen:
                continue
            seen.add(doc["path"])
            output["results"].append({"path": doc["path"], "title": doc["title"],
                                      "heading_path": chunk["heading_path"],
                                      "snippet": chunk["text"][:360], "score": score,
                                      "text_rank": text_ranks.get(id),
                                      "vector_rank": vector_ranks.get(id),
                                      "notion_url": doc["notion_url"] or None})
            if len(output["results"]) == k:
                break
    return output


def evaluate(config, path, embedder=None) -> dict:
    output = {"exit_code": 0, "report": {}, "results": []}
    try:
        queries = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        if not isinstance(queries, list) or not queries:
            raise ValueError
        for item in queries:
            if (not isinstance(item, dict) or set(item) != {"query", "expected"}
                    or not isinstance(item["query"], str) or not item["query"].strip()
                    or not isinstance(item["expected"], list) or not item["expected"]
                    or any(not isinstance(p, str) or not p for p in item["expected"])):
                raise ValueError
    except (OSError, ValueError, yaml.YAMLError):
        return {**output, "exit_code": 1, "warnings": ["Eval YAML biçimi geçersiz"]}
    for mode in ("text", "vector", "hybrid"):
        recalls, reciprocals, fallbacks = [], [], 0
        for item in queries:
            result = search(config, item["query"], mode=mode, k=100, embedder=embedder,
                            group_by_file=True)
            fallback = result["mode"] != mode or result["exit_code"] != 0
            fallbacks += int(fallback)
            expected = set(item["expected"])
            paths = [row["path"] for row in result["results"]]
            recall = len(expected & set(paths[:5])) / len(expected)
            reciprocal = next((1 / rank for rank, p in enumerate(paths, 1) if p in expected), 0.0)
            if not fallback:
                recalls.append(recall)
                reciprocals.append(reciprocal)
            output["results"].append({"query": item["query"], "requested_mode": mode,
                                      "mode": result["mode"], "warnings": result["warnings"],
                                      "recall@5": None if fallback else recall,
                                      "MRR": None if fallback else reciprocal})
        output["report"][mode] = {"recall@5": sum(recalls) / len(recalls) if recalls else None,
                                  "MRR": sum(reciprocals) / len(reciprocals) if reciprocals else None,
                                  "fallback_count": fallbacks, "measured_count": len(recalls)}
    return output
