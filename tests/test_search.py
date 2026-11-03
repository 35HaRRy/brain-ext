"""Synthetic Phase 3 contracts; no model downloads or real vault access."""

import importlib
import math
import os
import sqlite3
from dataclasses import replace

import pytest

from brainext.config import Config
from brainext.mdio import write_note


class FakeEmbedder:
    """Protocol: dimension, max_tokens, count_tokens(str), embed(list[str]).

    The production layer adds E5 prefixes; embed receives final, budgeted inputs.
    Character tokens deliberately catch truncation hidden by word counters.
    """

    dimension = 3
    max_tokens = 96

    def __init__(self):
        self.inputs = []

    def count_tokens(self, text):
        return len(text) + 2

    def embed(self, texts):
        for text in texts:
            assert self.count_tokens(text) <= self.max_tokens - 8
            self.inputs.append(text)
            yield [1.0, float("hosting" in text.lower()), float("python" in text.lower())]


@pytest.fixture
def config(tmp_path):
    return Config(vault=tmp_path)


def note(config, path, body="hosting kararı", **metadata):
    write_note(config.vault / path, metadata, body)
    return config.vault / path


def api():
    return (importlib.import_module("brainext.search.index").build_index,
            importlib.import_module("brainext.search.query").search)


def test_missing_implementation_is_observable(config):
    assert importlib.util.find_spec("brainext.search") is not None


@pytest.mark.parametrize("text", ["Iıİi", "ŞĞÇÖÜ âîû", "I\u0307", "İSTANBUL"])
def test_normalization(text):
    from brainext.search.normalize import fold

    expected = {"Iıİi": "iiii", "ŞĞÇÖÜ âîû": "sgcou aiu", "I\u0307": "i",
                "İSTANBUL": "istanbul"}
    assert fold(text) == expected[text]


def test_real_fts_prefix_escape_and_result_contract(config):
    build, search = api()
    note(config, "notes/a.md", "IŞIK projemizin hosting kararı", title="İstanbul")
    assert build(config)["exit_code"] == 0
    for query in ["ışık", "ISIK", "proje", '"proje" OR (NEAR *)']:
        result = search(config, query, mode="text")
        assert result["exit_code"] == 0
    hit = search(config, "proje", mode="text")["results"][0]
    assert set(hit) >= {"path", "title", "heading_path", "snippet", "score", "text_rank",
                        "vector_rank", "notion_url"}
    assert hit["path"] == "notes/a.md"
    assert not search(replace(config, prefix_min_length=6), "proje", mode="text")["results"]
    assert search(config, "istanbul", mode="text")["results"]
    assert not search(config, '" * : ( )', mode="text")["results"]


@pytest.mark.parametrize("path", [
    "random/a.md", "notes/.hidden/a.md", "notes/node_modules/a.md", "notes/receipts/a.md",
    "notes/daily/a.md", "notes/__pycache__/a.md", ".brain-ext/a.md", ".beyin-note-write/a.md",
    ".claude/a.md", ".agents/a.md", ".opencode/a.md", "notes/AGENTS.md", "notes/CLAUDE.md",
    "notes/GEMINI.md", "notes/SKILL.md", "notes/hooks.md", "notes/config.md",
    "notes/settings.md", "notes/instructions.md", "notes/codex.md", "notes/setup.md",
    "notes/install.md", "notes/setup-project.md", "notes/ŞİFRELERİ/a.md",
    "notes/Müşterilerim/a.md", "notes/GİZLİLİK/a.md", "notes/private/a.md",
    "notes/passwords/a.md", "notes/kimliğim/a.md", "notes/finansal/a.md",
    "notes/notion/_arsiv/a.md",
])
def test_hard_scope_exclusions(config, path):
    build, search = api()
    note(config, path)
    build(config)
    assert search(config, "hosting", mode="text", include_drafts=True)["results"] == []


@pytest.mark.parametrize("metadata", [{"visibility": "private"}, {"kind": "receipt"},
                                       {"generated": True}, {"status": "archived"},
                                       {"archived": True}])
def test_metadata_exclusions_and_stale_removal(config, metadata):
    build, search = api()
    path = note(config, "notes/a.md")
    build(config)
    write_note(path, metadata, "hosting very private")
    assert not search(config, "hosting", mode="text")["results"]
    build(config)
    with sqlite3.connect(config.state / "index.db") as db:
        assert db.execute("select count(*) from docs").fetchone()[0] == 0


def test_untrusted_drafts_and_allowlist(config):
    build, search = api()
    for path in ["notion/a.md", "notes/a.md", "knowledge/a.md", "tasks/a.md",
                 f"{config.companion_dir}/a.md", "agent-out/a.md", "notes/kasaba/a.md"]:
        note(config, path, kind="untrusted")
    build(config)
    assert len(search(config, "hosting", mode="text")["results"]) == 6
    assert len(search(config, "hosting", mode="text", include_drafts=True)["results"]) == 7
    assert len(search(config, "hosting", mode="text", path_prefix="agent-out/")["results"]) == 1
    assert not search(config, "hosting", mode="text", path_prefix="notes/a.md/evil")["results"]


def test_dryrun_and_model_missing_fallback(config):
    build, search = api()
    note(config, "notes/a.md")
    assert build(config, dry_run=True)["exit_code"] == 0
    assert not config.state.exists()
    assert search(config, "hosting")["mode"] == "text"
    assert not config.state.exists()
    build(config)
    for mode in ["vector", "hybrid"]:
        output = search(config, "hosting", mode=mode)
        assert output["mode"] == "text" and output["warnings"]
        assert output["results"][0]["vector_rank"] is None


def test_incremental_model_dimension_and_reembed(config):
    build, search = api()
    fake = FakeEmbedder()
    note(config, "notes/a.md")
    assert build(config, embedder=fake)["exit_code"] == 0
    count = len(fake.inputs)
    build(config, embedder=fake)
    assert len(fake.inputs) == count
    changed = replace(config, embedding_model="other/model")
    assert build(changed, embedder=fake)["exit_code"] == 1
    assert search(changed, "hosting", embedder=fake)["mode"] == "text"
    assert build(changed, reembed=True, embedder=fake)["exit_code"] == 0
    fake.dimension = 4
    assert build(changed, embedder=fake)["exit_code"] == 1


def test_removed_or_changed_sources_never_leak(config):
    build, search = api()
    path = note(config, "notes/a.md")
    build(config)
    path.unlink()
    assert not search(config, "hosting", mode="text")["results"]
    build(config)
    path = note(config, "notes/a.md")
    build(config)
    path.write_text("different body", encoding="utf-8")
    assert not search(config, "hosting", mode="text")["results"]


def test_symlinks_fail_closed(config, tmp_path):
    build, search = api()
    path = note(config, "notes/a.md")
    build(config)
    target = tmp_path / "outside.md"
    target.write_text("hosting", encoding="utf-8")
    path.unlink()
    try:
        path.symlink_to(target)
    except OSError:
        pytest.skip("Symlink creation privilege unavailable")
    assert not search(config, "hosting", mode="text")["results"]
    build(config)
    with sqlite3.connect(config.state / "index.db") as db:
        assert not db.execute("select * from docs").fetchall()


def test_unsafe_db_path_and_operation_lock(config, tmp_path):
    build, _ = api()
    config.state.mkdir()
    (config.state / "operation.lock").write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        build(config)
    (config.state / "operation.lock").unlink()
    try:
        (config.state / "index.db").symlink_to(tmp_path / "outside.db")
    except OSError:
        pytest.skip("Symlink creation privilege unavailable")
    with pytest.raises(ValueError):
        build(config)


def test_per_document_commit_resumes_interruption(config):
    build, search = api()
    note(config, "notes/a.md")
    note(config, "notes/b.md", "python")

    class Interrupted(FakeEmbedder):
        def embed(self, texts):
            if self.inputs:
                raise KeyboardInterrupt
            yield from super().embed(texts)

    with pytest.raises(KeyboardInterrupt):
        build(config, embedder=Interrupted())
    fake = FakeEmbedder()
    build(config, embedder=fake)
    assert len(fake.inputs) == 1
    assert len(search(config, "hosting python", embedder=fake)["results"]) == 2


def test_chunk_hierarchy_code_and_budget(config):
    from brainext.search.chunker import chunk_document

    fake = FakeEmbedder()
    body = "## Üst\nintro\n### Alt\n" + ("proje " * 90) + "\n\n```py\n" + "x=1\n" * 90 + "```\n"
    chunks, warnings = chunk_document(body, "Başlık", embedder=fake,
                                      model="intfloat/multilingual-e5-large")
    assert any(c["heading_path"] == "Başlık > Üst > Alt" for c in chunks)
    assert any("```py\n" + "x=1\n" * 90 + "```" in c["text"] for c in chunks)
    assert warnings
    for chunk in chunks:
        for text in chunk["embedding_texts"]:
            assert text.startswith("passage: ") and text.count("passage: ") == 1
            assert fake.count_tokens(text) <= 88


def test_impossible_single_code_line_is_fts_only_partial(config):
    build, search = api()
    note(config, "notes/a.md", "```\n" + "hosting" * 100 + "\n```")
    fake = FakeEmbedder()
    result = build(config, embedder=fake)
    assert result["exit_code"] == 2 and result["warnings"]
    assert search(config, "hosting", mode="text")["results"]
    assert not fake.inputs


@pytest.mark.parametrize("backend", ["sqlite-vec", "numpy"])
def test_real_vector_backends(backend):
    from brainext.search.vectors import VectorBackend, pack

    with sqlite3.connect(":memory:") as db:
        engine = VectorBackend(db, prefer=backend)
        assert engine.name == backend
        ranked = engine.rank([(1, pack([1, 0, 0])), (2, pack([0, 1, 0]))], [1, 0, 0])
        assert ranked[0][0] == 1 and math.isclose(ranked[0][1], 1.0)


def test_rrf_and_grouping(config):
    from brainext.search.query import rrf

    assert rrf([1, 2], [2, 3], 60)[0][0] == 2
    build, search = api()
    note(config, "notes/a.md", "## A\nhosting\n## B\nhosting")
    build(config, embedder=FakeEmbedder())
    result = search(config, "hosting", embedder=FakeEmbedder())
    assert result["mode"] == "hybrid"
    assert all(r["text_rank"] and r["vector_rank"] for r in result["results"])
    assert len(result["results"]) == 2
    assert len(search(config, "hosting", mode="text", group_by_file=True)["results"]) == 1


def test_graph_formats_ambiguity_bfs_and_stale_privacy(config):
    from brainext.search.graph import neighbors

    build, _ = api()
    id = "12345678-1234-1234-1234-123456789abc"
    url = "https://app.notion.com/p/" + id
    note(config, "notes/a.md", '[[B|alias]] [[Duplicate]] [old](https://www.notion.so/' +
         id.replace("-", "") + ') <mention url="' + url + '"/> <page url="' + url +
         '"/> <database url="https://unknown.invalid/x" data-source-url="' + url +
         '"/> <folder url="' + url + '"/>', title="A")
    note(config, "notes/b.md", "[[C]]", title="B")
    c = note(config, "notion/c.md", "[[missing]]", title="C", notion_id=id, notion_url=url)
    note(config, "notes/d.md", title="Duplicate")
    note(config, "notes/e.md", title="Duplicate")
    note(config, "agent-out/draft.md", "[[A]]")
    build(config)
    result = neighbors(config, "A")
    assert {r["path"] for r in result["results"]} == {"notes/b.md", "notion/c.md"}
    assert result["report"]["live_fixture_verified"] is False
    assert neighbors(config, "Duplicate")["results"] == []
    with sqlite3.connect(config.state / "index.db") as db:
        assert db.execute("select count(*) from links where dst_doc is null").fetchone()[0] >= 3
    write_note(c, {"visibility": "private"}, "private")
    assert "notion/c.md" not in str(neighbors(config, "A"))
    assert not neighbors(config, "C")["results"]


def test_eval_validation_metrics_and_honest_fallback(config, tmp_path):
    from brainext.search.query import evaluate

    build, _ = api()
    note(config, "notes/a.md")
    build(config)
    path = tmp_path / "queries.yaml"
    path.write_text('- query: hosting\n  expected: [notes/a.md]\n', encoding="utf-8")
    result = evaluate(config, path)
    assert result["report"]["text"]["recall@5"] == 1.0
    assert result["report"]["text"]["MRR"] == 1.0
    assert result["report"]["vector"]["recall@5"] is None
    assert result["report"]["vector"]["fallback_count"] == 1
    path.write_text('- query: 42\n  expected: wrong\n', encoding="utf-8")
    assert evaluate(config, path)["exit_code"] == 1


@pytest.mark.integration
@pytest.mark.skipif(os.environ.get("BRAINEXT_REAL_MODEL_TEST") != "1",
                    reason="Explicit local model opt-in required; never downloads")
def test_optional_real_cached_model(config):
    from brainext.search.embed import LocalEmbedder

    local = replace(config, model_path=os.environ.get("BRAINEXT_MODEL_PATH", ""))
    model = LocalEmbedder(local)
    vector = list(model.embed(["Türkçe deneme"]))[0]
    assert len(vector) == model.dimension
