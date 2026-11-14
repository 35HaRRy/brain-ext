from dataclasses import replace

import httpx
import pytest
from notion_markdown_fixture import page_markdown
from test_notion_sync import CHILD, ROOT, WORK, child
from test_notion_sync import setup as base_setup

from brainext.config import Config
from brainext.mdio import read_note
from brainext.notion.pull import pull

notion_setup = base_setup


@pytest.fixture
def setup(notion_setup):
    config, api, client = notion_setup
    for id in api.pages:
        api.overrides["GET", f"/pages/{id}/markdown"] = (
            lambda request, id=id: httpx.Response(200, json=page_markdown(api, id))
        )
    return config, api, client


def test_memory_roots_union_deduplicates_overlaps(setup):
    config, api, client = setup
    config = replace(config, memory_root_page_ids=(ROOT, CHILD, WORK))
    assert pull(config, client)["counts"]["new"] == 3
    paths = list(config.path("notion").glob("*.md"))
    assert {read_note(p)[0]["notion_id"] for p in paths} == {ROOT, CHILD, WORK}
    api.calls.clear()
    assert pull(config, client)["counts"]["unchanged"] == 3
    assert not any(p.endswith("/markdown") for _, p, _ in api.calls)


def test_memory_roots_replace_brain_read_scope(setup):
    config, api, client = setup
    config = replace(config, memory_root_page_ids=(WORK,))
    assert pull(config, client)["counts"]["new"] == 1
    assert not any(p == f"/pages/{ROOT}" for _, p, _ in api.calls)
    assert pull(config, client, page=CHILD)["exit_code"] == 1


def test_memory_roots_toml_roundtrip_and_validation(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        f'[vault]\npath="{tmp_path.as_posix()}"\n'
        f'[notion]\nmemory_root_page_ids=["{ROOT}", "{WORK}"]\n', encoding="utf-8")
    assert Config.load(path).memory_root_page_ids == (ROOT, WORK)
    for roots in ("not-a-list", ("bad-id",), (ROOT, ROOT.replace("-", "")), (12,), []):
        with pytest.raises(ValueError):
            Config(tmp_path, memory_root_page_ids=roots)


def test_incomplete_second_root_preserves_missing_first_root_page(setup):
    config, api, client = setup
    config = replace(config, memory_root_page_ids=(ROOT, WORK))
    assert pull(config, client)["exit_code"] == 0
    api.children[ROOT] = []
    api.pages[WORK]["last_edited_time"] = "changed"
    api.overrides["GET", f"/pages/{WORK}/markdown"] = httpx.Response(200, json={
        "markdown": "", "truncated": True, "unknown_block_ids": [],
    })
    api.overrides["GET", f"/blocks/{WORK}/children"] = httpx.Response(403, json={})
    assert pull(config, client)["exit_code"] == 2
    assert len(list(config.path("notion").glob("*.md"))) == 3
    api.children[ROOT] = [child(CHILD, ROOT)]


def test_old_scope_mirrors_are_not_memory_after_scope_change(setup):
    from brainext.search.index import scan

    config, api, client = setup
    pull(config, client)
    config = replace(config, memory_root_page_ids=(WORK,))
    # Preserved old mirror files must not keep the previous Brain scope searchable.
    pull(config, client)
    assert len(list(config.path("notion").glob("*.md"))) == 3
    assert {item["metadata"]["notion_id"] for item in scan(config).values()} == {WORK}


def test_legacy_scope_also_requires_confirmed_trash(setup):
    config, api, client = setup
    pull(config, client)
    old = next(p for p in config.path("notion").glob("*.md")
               if read_note(p)[0]["notion_id"] == CHILD)
    before = old.read_bytes()
    api.children[ROOT] = []
    assert pull(config, client)["exit_code"] == 2
    assert old.read_bytes() == before
    assert not list(config.path("notion/_arsiv").glob("*.md"))


def test_confirmed_move_revokes_search_membership_without_changing_note(setup):
    from brainext.search.index import scan

    config, api, client = setup
    config = replace(config, memory_root_page_ids=(ROOT,))
    pull(config, client)
    old = next(p for p in config.path("notion").glob("*.md")
               if read_note(p)[0]["notion_id"] == CHILD)
    before = old.read_bytes()
    api.children[ROOT] = []
    api.pages[CHILD]["parent"]["page_id"] = WORK
    assert pull(config, client)["exit_code"] == 2
    assert old.read_bytes() == before
    assert {item["metadata"]["notion_id"] for item in scan(config).values()} == {ROOT}
    api.pages[CHILD]["parent"]["page_id"] = ROOT
    api.children[ROOT] = [child(CHILD, ROOT)]
    assert pull(config, client)["exit_code"] == 0
    assert {item["metadata"]["notion_id"] for item in scan(config).values()} == {ROOT, CHILD}


def test_corrupt_scope_marker_cannot_restore_search_access(setup):
    from brainext.mdio import write_json
    from brainext.notion._sync import scope_path
    from brainext.search.index import scan

    config, api, client = setup
    pull(config, client)
    write_json(scope_path(config, CHILD), {})
    assert {item["metadata"]["notion_id"] for item in scan(config).values()} == {ROOT}
