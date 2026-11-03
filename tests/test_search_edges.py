"""Fail-closed regressions and runtime boundaries, using synthetic local files only."""

import builtins
import json
import os
import sqlite3
import subprocess
import sys
from dataclasses import replace
from types import SimpleNamespace

import pytest
from test_search import FakeEmbedder, note

from brainext.config import Config
from brainext.mdio import write_note
from brainext.search.embed import LocalEmbedder, model_spec
from brainext.search.graph import neighbors
from brainext.search.index import build_index
from brainext.search.query import evaluate, search


@pytest.fixture
def config(tmp_path):
    return Config(vault=tmp_path)


def test_embedding_failure_keeps_text_and_retryable_document(config):
    class Broken(FakeEmbedder):
        def embed(self, texts):
            raise RuntimeError("synthetic failure")

    note(config, "notes/a.md")
    output = build_index(config, embedder=Broken())
    assert output["exit_code"] == 2
    assert search(config, "hosting", mode="text")["results"]
    fake = FakeEmbedder()
    assert build_index(config, embedder=fake)["exit_code"] == 0
    assert fake.inputs


def test_model_mismatch_does_not_block_fresh_text_indexing(config):
    note(config, "notes/a.md")
    build_index(config, embedder=FakeEmbedder())
    note(config, "notes/b.md", "new searchable term")
    changed = replace(config, embedding_model="different/model")
    output = build_index(changed)
    assert output["exit_code"] == 1 and output["mode"] == "text"
    assert search(changed, "searchable", mode="text")["results"][0]["path"] == "notes/b.md"


def test_source_read_failure_purges_text_vectors_and_graph(config, monkeypatch):
    from pathlib import Path

    path = note(config, "notes/a.md", "hosting [[B]]", title="A")
    note(config, "notes/b.md", title="B")
    build_index(config, embedder=FakeEmbedder())
    original = Path.read_bytes

    def denied(self):
        if self == path:
            raise PermissionError
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", denied)
    assert not search(config, "hosting", mode="text", path_prefix="notes/a.md")["results"]
    assert not neighbors(config, "B")["results"]
    build_index(config)
    with sqlite3.connect(config.state / "index.db") as db:
        assert db.execute("select count(*) from docs where path='notes/a.md'").fetchone()[0] == 0
        assert db.execute("select count(*) from links").fetchone()[0] == 0


@pytest.mark.skipif(os.name != "nt", reason="Windows junction boundary")
def test_windows_junction_index_and_query_fail_closed(config):
    path = note(config, "notes/sub/a.md")
    build_index(config)
    path.unlink()
    path.parent.rmdir()
    target = config.vault / "outside"
    target.mkdir()
    (target / "a.md").write_text("hosting", encoding="utf-8")
    process = subprocess.run(["cmd", "/c", "mklink", "/J", str(path.parent), str(target)],
                             capture_output=True, check=False)
    assert process.returncode == 0
    try:
        assert not search(config, "hosting", mode="text")["results"]
        build_index(config)
        with sqlite3.connect(config.state / "index.db") as db:
            assert not db.execute("select * from docs").fetchall()
    finally:
        os.rmdir(path.parent)


def test_text_only_works_with_all_semantic_imports_blocked(config, monkeypatch):
    real_import = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in {"numpy", "fastembed", "tokenizers", "sqlite_vec"}:
            raise AssertionError("Text-only path attempted semantic import")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    note(config, "notes/a.md")
    build_index(config)
    assert search(config, "hosting")["mode"] == "text"
    assert search(config, "hosting", mode="text")["results"]


def test_automatic_numpy_fallback(config, monkeypatch):
    note(config, "notes/a.md")
    build_index(config, embedder=FakeEmbedder())
    monkeypatch.setitem(sys.modules, "sqlite_vec", None)
    output = search(config, "hosting", mode="vector", embedder=FakeEmbedder())
    assert output["mode"] == "vector"
    assert output["report"]["vector_backend"] == "numpy"
    assert output["results"]


@pytest.mark.parametrize("name,expected", [
    ("sentence-transformers/paraphrase-multilingual-mpnet-base-v2", (512, 768)),
    ("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", (128, 384)),
    ("intfloat/multilingual-e5-large", (512, 1024)),
])
def test_supported_model_budgets(name, expected):
    assert model_spec(name) == expected


def test_adapter_counts_untruncated_local_tokens_and_forces_offline(config, monkeypatch):
    from tokenizers import Tokenizer
    from tokenizers.models import WordLevel
    from tokenizers.pre_tokenizers import Whitespace

    model_dir = config.vault / "synthetic-model"
    model_dir.mkdir()
    tokenizer = Tokenizer(WordLevel({"[UNK]": 0, "a": 1}, unk_token="[UNK]"))
    tokenizer.pre_tokenizer = Whitespace()
    tokenizer.enable_truncation(max_length=3)
    tokenizer.enable_padding(length=6)
    tokenizer.save(str(model_dir / "tokenizer.json"))

    class OfflineAdapter:
        def __init__(self, **kwargs):
            assert kwargs["local_files_only"] is True
            assert kwargs["specific_model_path"] == str(model_dir.resolve())

        def embed(self, texts):
            return [[1.0] * 768 for text in texts]

    monkeypatch.setitem(sys.modules, "fastembed", SimpleNamespace(TextEmbedding=OfflineAdapter))
    model = LocalEmbedder(replace(config, model_path=str(model_dir)))
    assert model.count_tokens("a " * 1000) == 1000
    assert model.count_tokens("a") == 1
    with pytest.raises(ValueError, match="token"):
        model.embed(["a " * 1000])


def test_missing_model_never_imports_fastembed(config, monkeypatch):
    monkeypatch.setitem(sys.modules, "fastembed", None)
    with pytest.raises(ValueError):
        LocalEmbedder(config)


def test_e5_query_prefix_and_long_query_fallback(config):
    config = replace(config, embedding_model="intfloat/multilingual-e5-large")
    note(config, "notes/a.md")
    fake = FakeEmbedder()
    build_index(config, embedder=fake)
    assert fake.inputs[0].startswith("passage: ")
    output = search(config, "query: hosting", mode="vector", embedder=fake)
    assert output["mode"] == "vector"
    assert fake.inputs[-1] == "query: hosting"
    output = search(config, "hosting " * 100, embedder=fake)
    assert output["mode"] == "text" and output["warnings"]


def test_stale_vectors_never_return_private_content(config):
    note(config, "notes/a.md", "hosting")
    build_index(config, embedder=FakeEmbedder())
    note(config, "notes/a.md", "secret hosting", visibility="private")
    output = search(config, "hosting", embedder=FakeEmbedder())
    assert output["results"] == []
    assert "secret" not in json.dumps(output)


def test_state_identity_map_and_relative_links(config):
    notion_id = "12345678-1234-1234-1234-123456789abc"
    note(config, "notes/a.md", f'[b](../notion/b.md) <page url="https://app.notion.com/p/{notion_id}"/>',
         title="A")
    note(config, "notion/b.md", "[[notes/a#Heading|A]]", title="B")
    state = config.state / "state/notion_state.json"
    state.parent.mkdir(parents=True)
    state.write_text(json.dumps({"version": 1, "pages": {notion_id: {"path": "notion/b.md"}}}),
                     encoding="utf-8")
    build_index(config)
    with sqlite3.connect(config.state / "index.db") as db:
        assert db.execute("select count(*) from links where dst_doc is not null").fetchone()[0] == 3
    assert neighbors(config, "A", depth=1)["results"][0]["path"] == "notion/b.md"


def test_graph_unrelated_draft_and_private_intermediate_do_not_connect(config):
    note(config, "notes/a.md", "[[B]]", title="A")
    b = note(config, "notes/b.md", "[[C]]", title="B")
    note(config, "notes/c.md", title="C")
    note(config, "agent-out/draft.md", "[[A]] [[C]]", title="Draft")
    build_index(config)
    assert {r["title"]: r["distance"] for r in neighbors(config, "A")["results"]} == {"B": 1, "C": 2}
    write_note(b, {"visibility": "private"}, "[[C]]")
    assert neighbors(config, "A")["results"] == []


@pytest.mark.parametrize("payload", ["{}", "[]", "- query: x", "- query: x\n  expected: []",
                                      "- query: ''\n  expected: [a]", "!!python/object:bad {}"])
def test_invalid_eval_yaml_is_rejected(config, payload):
    path = config.vault / "eval.yaml"
    path.write_text(payload, encoding="utf-8")
    assert evaluate(config, path)["exit_code"] == 1


def test_eval_all_semantic_modes_measure_fake_vectors(config):
    note(config, "notes/a.md")
    build_index(config, embedder=FakeEmbedder())
    path = config.vault / "eval.yaml"
    path.write_text('- query: hosting\n  expected: [notes/a.md, notes/missing.md]', encoding="utf-8")
    result = evaluate(config, path, embedder=FakeEmbedder())
    for mode in ("text", "vector", "hybrid"):
        assert result["report"][mode]["recall@5"] == 0.5
        assert result["report"][mode]["MRR"] == 1.0
        assert result["report"][mode]["fallback_count"] == 0


def test_eval_mrr_counts_first_correct_result_beyond_five(config):
    for name in "abcdef":
        note(config, f"notes/{name}.md", "hosting", title="Same")
    build_index(config)
    path = config.vault / "eval.yaml"
    path.write_text('- query: hosting\n  expected: [notes/f.md]', encoding="utf-8")
    result = evaluate(config, path)
    assert result["report"]["text"]["recall@5"] == 0.0
    assert result["report"]["text"]["MRR"] == pytest.approx(1 / 6)


def test_optional_corrupt_graph_state_does_not_break_metadata_resolution(config):
    note(config, "notes/a.md", "[[B]]", title="A")
    note(config, "notes/b.md", title="B")
    path = config.state / "state/notion_state.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"version": 1, "pages": "corrupt"}', encoding="utf-8")
    assert build_index(config)["exit_code"] == 0
    assert neighbors(config, "A")["results"][0]["title"] == "B"


@pytest.mark.parametrize("vectors", [[], [[1.0, 2.0]], [[0.0, 0.0, 0.0]],
                                     [[float("nan"), 1.0, 1.0]], [[1e308, 1.0, 1.0]]])
def test_invalid_embedding_is_partial_text_not_mixed_vectors(config, vectors):
    class Invalid(FakeEmbedder):
        def embed(self, texts):
            return iter(vectors)

    note(config, "notes/a.md")
    result = build_index(config, embedder=Invalid())
    assert result["exit_code"] == 2
    assert search(config, "hosting", mode="text")["results"]
    with sqlite3.connect(config.state / "index.db") as db:
        assert db.execute("select count(*) from chunk_vec").fetchone()[0] == 0


def test_privacy_changes_during_query_embedding_are_rechecked(config):
    path = note(config, "notes/a.md")
    build_index(config, embedder=FakeEmbedder())

    class Privatizing(FakeEmbedder):
        def embed(self, texts):
            write_note(path, {"visibility": "private"}, "private changed")
            yield from super().embed(texts)

    assert search(config, "hosting", embedder=Privatizing())["results"] == []
