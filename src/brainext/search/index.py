"""Allowlisted incremental SQLite index with a live, fail-closed privacy boundary."""

from __future__ import annotations

import os
import re
import sqlite3
from contextlib import closing
from pathlib import Path

import yaml

from brainext.mdio import digest, operation_lock, read_note
from brainext.search.chunker import chunk_document
from brainext.search.embed import get_embedder
from brainext.search.normalize import fold
from brainext.search.vectors import pack

SENSITIVE = re.compile(
    r"\b(?:(?:kasa|sifre|parola|kimlik|kimlig|finans|finansal|musteri|vergi|fatura|maas|"
    r"ozel|gizli|gizlilik)(?:ler|lar)?(?:i|im|in|imiz|leri|lari)?|"
    r"(?:private|secret|password|credential)s?)\b")
INSTRUCTIONS = {"agents", "claude", "gemini", "skill", "hooks", "config", "settings",
                "instructions", "codex", "setup", "install"}
BLOCKED = {"receipts", "daily", "node_modules", "__pycache__", "_arsiv"}


def allowed_path(config, relative, *, directory=False):
    path = Path(relative)
    parts = path.parts
    if not parts or parts[0] not in {config.mirror_dir, config.outbox_dir, "notes", "knowledge",
                                    "tasks", config.companion_dir}:
        return False
    for part in parts if directory else parts[:-1]:
        if (part.startswith(".") or fold(part) in BLOCKED
                or any(SENSITIVE.fullmatch(word) for word in re.findall(r"[^\W\d_]+", fold(part)))):
            return False
    if not directory:
        name = fold(path.stem)
        if (path.name.startswith(".") or path.suffix.lower() != ".md"
                or name in INSTRUCTIONS or name.startswith("setup-")):
            return False
    config.path(relative)  # Includes every ancestor and the leaf: symlinks AND junctions.
    return True


def source(config, relative):
    """None means ineligible, unreadable, changing, or gone; callers never serve old text."""
    try:
        if not allowed_path(config, relative):
            return None
        path = config.path(relative)
        raw = path.read_bytes()
        metadata, body = read_note(path)
        if (fold(str(metadata.get("visibility", ""))) == "private"
                or fold(str(metadata.get("kind", ""))) == "receipt"
                or metadata.get("generated") is True or metadata.get("archived") is True
                or fold(str(metadata.get("status", ""))) == "archived"):
            return None
        if config.path(relative).read_bytes() != raw:
            return None
        return {"metadata": metadata, "body": body, "hash": digest(raw),
                "mtime": path.stat().st_mtime}
    except (OSError, ValueError, UnicodeError, yaml.YAMLError):
        return None


def scan(config):
    found = {}
    for top in sorted({config.mirror_dir, config.outbox_dir, "notes", "knowledge", "tasks",
                       config.companion_dir}):
        try:
            if not allowed_path(config, top, directory=True):
                continue
            root = config.path(top)
        except (OSError, ValueError):
            continue
        for parent, dirs, files in os.walk(root, followlinks=False):
            safe_dirs = []
            for name in dirs:
                relative = (Path(parent) / name).relative_to(config.vault).as_posix()
                try:
                    if allowed_path(config, relative, directory=True):
                        safe_dirs.append(name)
                except (OSError, ValueError):
                    pass
            dirs[:] = sorted(safe_dirs)
            for name in sorted(files):
                relative = (Path(parent) / name).relative_to(config.vault).as_posix()
                item = source(config, relative)
                if item is not None:
                    found[relative] = item
    return found


def database_path(config):
    return config.path(f"{config.state_dir}/index.db")


def connect(config, *, readonly=False):
    path = database_path(config)
    if readonly and not path.exists():
        return None
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) if readonly else sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


def schema(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS docs(
            id INTEGER PRIMARY KEY, path TEXT UNIQUE NOT NULL, mtime REAL,
            content_hash TEXT, title TEXT, notion_id TEXT, notion_url TEXT,
            semantic_complete INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS chunks(
            id INTEGER PRIMARY KEY, doc_id INTEGER REFERENCES docs(id) ON DELETE CASCADE,
            ord INTEGER, heading_path TEXT, text TEXT, text_folded TEXT, chunk_hash TEXT);
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            text_folded, heading_path, tokenize='unicode61 remove_diacritics 2');
        CREATE TRIGGER IF NOT EXISTS chunks_delete AFTER DELETE ON chunks BEGIN
            DELETE FROM chunks_fts WHERE rowid=old.id;
        END;
        CREATE TABLE IF NOT EXISTS chunk_vec(
            id INTEGER PRIMARY KEY, chunk_id INTEGER REFERENCES chunks(id) ON DELETE CASCADE,
            embedding BLOB NOT NULL);
        CREATE TABLE IF NOT EXISTS links(
            src_doc INTEGER REFERENCES docs(id) ON DELETE CASCADE, target TEXT,
            dst_doc INTEGER REFERENCES docs(id) ON DELETE SET NULL, kind TEXT);
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
    """)


def live_docs(config, db, *, include_drafts=False, path_prefix=None):
    result = {}
    prefix = str(path_prefix).replace("\\", "/").rstrip("/") if path_prefix else None
    for row in db.execute("SELECT * FROM docs ORDER BY path"):
        path = row["path"]
        if prefix and path != prefix and not path.startswith(prefix + "/"):
            continue
        if (Path(path).parts[0] == config.outbox_dir and not include_drafts
                and not (prefix and Path(prefix).parts[0] == config.outbox_dir)):
            continue
        item = source(config, path)
        if item and item["hash"] == row["content_hash"]:
            result[row["id"]] = dict(row)
    return result


def build_index(config, *, dry_run=False, reembed=False, embedder=None) -> dict:
    database_path(config)
    sources = scan(config)
    output = {"exit_code": 0, "report": {"indexed": 0, "unchanged": 0, "removed": 0,
                                         "eligible": len(sources), "dry_run": dry_run},
              "results": [], "warnings": [], "mode": "text"}
    if dry_run:
        return output
    with operation_lock(config.state), closing(connect(config)) as db:
        schema(db)
        for row in db.execute("SELECT id,path FROM docs").fetchall():
            if row["path"] not in sources:
                db.execute("DELETE FROM docs WHERE id=?", (row["id"],))
                output["report"]["removed"] += 1
        db.commit()  # Privacy removals survive embedding failure/model mismatch.
        model, warnings = get_embedder(config, embedder)
        output["warnings"].extend(warnings)
        meta = dict(db.execute("SELECT key,value FROM meta"))
        desired = {"embedding_model": config.embedding_model,
                   "embedding_dim": str(model.dimension)} if model else {}
        mismatch = (meta.get("embedding_model") and
                    (meta["embedding_model"] != config.embedding_model or
                     (model and meta.get("embedding_dim") != str(model.dimension))))
        if mismatch and not reembed:
            output["exit_code"] = 1
            output["warnings"].append("Model/boyut uyuşmuyor; index --reembed gerekli")
            model, desired = None, {}
        if reembed:
            db.execute("DELETE FROM chunk_vec")
            db.execute("UPDATE docs SET semantic_complete=0")
            db.execute("DELETE FROM meta WHERE key IN ('embedding_model','embedding_dim')")
        if desired:
            db.executemany("INSERT OR REPLACE INTO meta VALUES(?,?)", desired.items())
            output["mode"] = "hybrid"
        db.execute("INSERT OR REPLACE INTO meta VALUES('schema_version','1')")
        db.commit()
        from brainext.search.graph import parse_links, resolve_links

        for relative, item in sorted(sources.items()):
            old = db.execute("SELECT * FROM docs WHERE path=?", (relative,)).fetchone()
            if old and old["content_hash"] == item["hash"] and (
                    model is None or old["semantic_complete"]):
                output["report"]["unchanged"] += 1
                continue
            try:
                # Re-read immediately before storing; scan is not a privacy authority.
                fresh = source(config, relative)
                if fresh is None or fresh["hash"] != item["hash"]:
                    if old:
                        db.execute("DELETE FROM docs WHERE id=?", (old["id"],))
                        db.commit()
                    continue
                metadata, body = item["metadata"], item["body"]
                title = str(metadata.get("title") or Path(relative).stem)
                properties = metadata.get("properties")
                heading = title + (" > " + str(properties) if properties else "")
                chunks, notices = chunk_document(body, heading, embedder=model,
                                                 model=config.embedding_model)
                with db:
                    if old:
                        db.execute("DELETE FROM docs WHERE id=?", (old["id"],))
                    cursor = db.execute("""INSERT INTO docs(path,mtime,content_hash,title,
                        notion_id,notion_url,semantic_complete) VALUES(?,?,?,?,?,?,?)""",
                                        (relative, item["mtime"], item["hash"], title,
                                         str(metadata.get("notion_id") or ""),
                                         str(metadata.get("notion_url") or ""), int(model is not None)))
                    doc_id = cursor.lastrowid
                    semantic_failed = False
                    for order, chunk in enumerate(chunks):
                        text, heading = chunk["text"], chunk["heading_path"]
                        cursor = db.execute("""INSERT INTO chunks(doc_id,ord,heading_path,text,
                            text_folded,chunk_hash) VALUES(?,?,?,?,?,?)""",
                                            (doc_id, order, heading, text, fold(text),
                                             digest(text.encode("utf-8"))))
                        chunk_id = cursor.lastrowid
                        db.execute("INSERT INTO chunks_fts(rowid,text_folded,heading_path) VALUES(?,?,?)",
                                   (chunk_id, fold(text), fold(heading)))
                        inputs = chunk["embedding_texts"]
                        if model and inputs and not semantic_failed:
                            try:
                                vectors = list(model.embed(inputs))
                                if len(vectors) != len(inputs):
                                    raise ValueError("Embedding sayısı uyuşmuyor")
                                db.executemany("INSERT INTO chunk_vec(chunk_id,embedding) VALUES(?,?)",
                                               [(chunk_id, pack(v, model.dimension)) for v in vectors])
                            except (ImportError, OSError, ValueError, RuntimeError):
                                semantic_failed = True
                                notices.append("Embedding başarısız; metin saklandı, yeniden denenecek")
                    if semantic_failed:
                        db.execute("DELETE FROM chunk_vec WHERE chunk_id IN "
                                   "(SELECT id FROM chunks WHERE doc_id=?)", (doc_id,))
                        db.execute("UPDATE docs SET semantic_complete=0 WHERE id=?", (doc_id,))
                    db.executemany("INSERT INTO links(src_doc,target,kind) VALUES(?,?,?)",
                                   [(doc_id, target, kind) for target, kind in parse_links(body)])
                output["warnings"].extend(notices)
                if notices:
                    output["exit_code"] = 2
                output["report"]["indexed"] += 1
            except (OSError, ValueError, RuntimeError, sqlite3.Error):
                output["exit_code"] = 2
                output["warnings"].append("Belge indekslenemedi; sonraki çalıştırmada yeniden denenir")
        resolve_links(config, db)
        db.commit()
    return output
