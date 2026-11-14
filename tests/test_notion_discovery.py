from dataclasses import replace
from uuid import UUID

import httpx
import pytest
from notion_markdown_fixture import page_markdown
from test_notion_sync import API, BLOCK, CHILD, DB, DS, ROOT, WORK, child, database, page

from brainext.config import Config
from brainext.mdio import read_json, read_note, write_json
from brainext.notion._sync import Inventory
from brainext.notion.client import NotionClient
from brainext.notion.pull import pull


class MarkdownAPI(API):
    def __call__(self, request):
        path = request.url.path.removeprefix("/v1")
        if (request.method == "GET" and path.endswith("/markdown")
                and (request.method, path) not in self.overrides):
            id = path.split("/")[2]
            if id in self.markdown:
                self.calls.append((request.method, path, request))
                return httpx.Response(200, json=page_markdown(self, id))
        return super().__call__(request)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr("brainext.notion.client.time.sleep", lambda _: None)
    config = Config(tmp_path, brain_root_page_id=ROOT, agent_workspace_id=WORK,
                    memory_root_page_ids=(ROOT,))
    api = MarkdownAPI()
    with NotionClient(config, "synthetic", httpx.MockTransport(api)) as client:
        yield config, api, client


def test_fast_discovery_finds_same_pages_without_crawling_content_blocks(setup):
    config, api, client = setup
    api.children[ROOT] = []
    parent = ROOT
    for index in range(100, 150):
        id = str(UUID(int=index))
        block = child(id, parent, "toggle", True)
        if parent != ROOT:
            block["parent"] = {"type": "block_id", "block_id": parent}
        api.children[parent] = [block]
        api.overrides["GET", f"/blocks/{id}"] = httpx.Response(200, json=block)
        parent = id
    api.children[parent] = [child(CHILD, parent)]
    api.pages[CHILD]["parent"] = {"type": "block_id", "block_id": parent}
    strict = Inventory(client, ROOT).scan()
    assert strict.complete and set(strict.pages) == {ROOT, CHILD}
    api.calls.clear()
    fast = Inventory(client, ROOT, discovery_cache={}).scan()
    assert fast.complete and set(fast.pages) == set(strict.pages)
    assert not any(p.endswith("/children") for _, p, _ in api.calls)
    assert len(api.calls) < 60  # Metadata ancestry is still verified, not trusted from text.


def test_content_only_containers_need_one_markdown_instead_of_one_call_each(setup):
    config, api, client = setup
    api.children[ROOT] = []
    for index in range(100, 200):
        id = str(UUID(int=index))
        api.children[ROOT].append(child(id, ROOT, "toggle", True))
        api.children[id] = [child(str(UUID(int=index + 1000)), id, "paragraph")]
    strict = Inventory(client, ROOT).scan()
    strict_calls = len(api.calls)
    assert strict.complete and set(strict.pages) == {ROOT}
    api.calls.clear()
    fast = Inventory(client, ROOT, discovery_cache={}).scan()
    assert fast.complete and set(fast.pages) == set(strict.pages)
    assert strict_calls == 102 and len(api.calls) == 2


@pytest.mark.parametrize("fault", ["truncated", "unknown", "warning", "missing-url", "folder"])
def test_incomplete_or_unsupported_discovery_falls_back_without_losing_children(setup, fault):
    config, api, client = setup
    data = {"markdown": "", "truncated": False, "unknown_block_ids": []}
    if fault == "truncated":
        data["truncated"] = True
    elif fault == "unknown":
        data["markdown"] = "<unknown/>"
    elif fault == "warning":
        data["warnings"] = [{"code": "warning"}]
    elif fault == "missing-url":
        data["markdown"] = "<page>Child</page>"
    else:
        data["markdown"] = '<folder url="https://app.notion.com/p/anything">Folder</folder>'
    api.overrides["GET", f"/pages/{ROOT}/markdown"] = httpx.Response(200, json=data)
    fast = Inventory(client, ROOT, discovery_cache={}).scan()
    assert fast.complete and set(fast.pages) == {ROOT, CHILD}
    assert ROOT not in fast.discovery
    assert any(p == f"/blocks/{ROOT}/children" for _, p, _ in api.calls)


def test_database_rows_and_nested_pages_remain_in_scope(setup):
    config, api, client = setup
    database(api)
    new = str(UUID(int=50))
    api.children[CHILD] = [child(new, CHILD)]
    api.pages[new] = page(new, CHILD)
    api.children[new] = []
    api.markdown[new] = {"markdown": "Nested", "truncated": False, "unknown_block_ids": []}
    fast = Inventory(client, ROOT, discovery_cache={}).scan()
    assert fast.complete and set(fast.pages) == {ROOT, CHILD, new}
    assert any(p == f"/data_sources/{DS}/query" for _, p, _ in api.calls)
    assert not any(p.endswith("/children") for _, p, _ in api.calls)


def test_discovery_download_is_reused_for_mirror_and_second_pull_reuses_revision(setup):
    config, api, client = setup
    assert pull(config, client)["exit_code"] == 0
    assert sum(p == f"/pages/{ROOT}/markdown" for _, p, _ in api.calls) == 1
    assert not any(p.endswith("/children") for _, p, _ in api.calls)
    state = read_json(config.path(".brain-ext/state/notion_state.json"))
    assert state["pages"][ROOT]["discovery"]["children"] == [["page_id", CHILD]]
    api.calls.clear()
    assert pull(config, client)["counts"]["unchanged"] == 2
    assert not any(p.endswith(("/markdown", "/children")) for _, p, _ in api.calls)
    new = str(UUID(int=51))
    api.pages[new] = page(new, ROOT)
    api.markdown[new] = {"markdown": "New", "truncated": False, "unknown_block_ids": []}
    api.children[new] = []
    api.children[ROOT].append(child(new, ROOT))
    api.pages[ROOT]["last_edited_time"] = "changed"
    assert pull(config, client)["counts"]["new"] == 1


def test_dry_run_does_not_save_discovery_cache(setup):
    config, api, client = setup
    assert pull(config, client, dry_run=True)["exit_code"] == 0
    assert list(config.vault.iterdir()) == []
    assert not any(p.endswith("/children") for _, p, _ in api.calls)


def test_full_pull_refreshes_cached_discovery(setup):
    config, api, client = setup
    pull(config, client)
    api.calls.clear()
    assert pull(config, client, full=True)["exit_code"] == 0
    assert any(p.endswith("/markdown") for _, p, _ in api.calls)
    assert not any(p.endswith("/children") for _, p, _ in api.calls)


def test_partial_fallback_never_claims_a_complete_inventory(setup):
    config, api, client = setup
    api.overrides["GET", f"/pages/{ROOT}/markdown"] = httpx.Response(200, json={
        "markdown": "", "truncated": True, "unknown_block_ids": [],
    })
    api.overrides["GET", f"/blocks/{ROOT}/children"] = httpx.Response(403, json={})
    fast = Inventory(client, ROOT, discovery_cache={}).scan()
    assert not fast.complete


@pytest.mark.parametrize("text", ["<folder", "<unknown", "<page", "<database"])
def test_unterminated_structural_tag_cannot_hide_descendants(setup, text):
    config, api, client = setup
    api.overrides["GET", f"/pages/{ROOT}/markdown"] = httpx.Response(200, json={
        "markdown": text, "truncated": False, "unknown_block_ids": [],
    })
    fast = Inventory(client, ROOT, discovery_cache={}).scan()
    assert fast.complete and set(fast.pages) == {ROOT, CHILD}
    assert ROOT not in fast.discovery
    assert any(p == f"/blocks/{ROOT}/children" for _, p, _ in api.calls)


def test_invalid_discovery_cache_fails_closed_before_any_http(setup):
    config, api, client = setup
    pull(config, client)
    path = config.path(".brain-ext/state/notion_state.json")
    state = read_json(path)
    state["pages"][ROOT]["discovery"] = {
        "last_edited_time": "x", "children": [["page_id", "../secret"]],
    }
    write_json(path, state)
    api.calls.clear()
    assert pull(config, client)["exit_code"] == 1
    assert not api.calls


def test_strict_inventory_is_still_default_for_trash_and_legacy_workflows(setup):
    config, api, client = setup
    strict = Inventory(client, ROOT).scan()
    assert strict.complete and set(strict.pages) == {ROOT, CHILD}
    assert any(p.endswith("/children") for _, p, _ in api.calls)
    assert not any(p.endswith("/markdown") for _, p, _ in api.calls)
    legacy = replace(config, memory_root_page_ids=())
    api.calls.clear()
    assert pull(legacy, client)["exit_code"] == 0
    assert any(p.endswith("/children") for _, p, _ in api.calls)


def test_foreign_page_tags_do_not_expand_scope_or_fetch_foreign_content(setup):
    config, api, client = setup
    api.children[ROOT] = []
    api.markdown[ROOT]["markdown"] = f'<page url="https://app.notion.com/p/{WORK}">Foreign</page>'
    fast = Inventory(client, ROOT, discovery_cache={}).scan()
    assert fast.complete and set(fast.pages) == {ROOT}
    assert not any(p == f"/pages/{WORK}/markdown" for _, p, _ in api.calls)


def test_local_edit_invalidates_cache_without_authorizing_overwrite(setup):
    config, api, client = setup
    pull(config, client)
    state = read_json(config.path(".brain-ext/state/notion_state.json"))
    path = config.path(state["pages"][CHILD]["path"])
    path.write_bytes(path.read_bytes() + b"Local human edit")
    before = path.read_bytes()
    api.calls.clear()
    assert pull(config, client)["exit_code"] == 2
    assert any(p == f"/pages/{CHILD}/markdown" for _, p, _ in api.calls)
    assert path.read_bytes() == before


def test_doctor_uses_the_same_fast_memory_scope_discovery(setup, monkeypatch):
    from brainext.cli import doctor

    config, api, client = setup
    monkeypatch.setattr("brainext.notion.client.NotionClient",
                        lambda config, token: NotionClient(config, token, httpx.MockTransport(api)))
    assert doctor(config, "synthetic")["notion_pages"] == 2
    assert not any(p.endswith("/children") for _, p, _ in api.calls)


@pytest.mark.parametrize("fragment", [False, True])
@pytest.mark.parametrize("target_type", ["page_id", "database_id"])
def test_unlisted_unknown_page_link_does_not_force_whole_page_crawl(setup, fragment, target_type):
    config, api, client = setup
    url = (f"https://www.notion.so/{CHILD.replace('-', '')}#{BLOCK.replace('-', '')}"
           if fragment else f"https://app.notion.com/p/{BLOCK}")
    api.markdown[CHILD]["markdown"] = f'Before <unknown url="{url}" alt="Link"/> After'
    target = WORK if target_type == "page_id" else DB
    block = {**child(BLOCK, CHILD, "link_to_page"), "in_trash": False,
             "link_to_page": {"type": target_type, target_type: target}}
    api.overrides["GET", f"/blocks/{BLOCK}"] = httpx.Response(200, json=block)
    assert pull(config, client)["exit_code"] == 0
    assert not any(p.endswith("/children") for _, p, _ in api.calls)
    assert sum(p == f"/blocks/{BLOCK}" for _, p, _ in api.calls) == 1
    assert not any(p == f"/pages/{target}/markdown" for _, p, _ in api.calls)
    assert not any(p == f"/databases/{target}" for _, p, _ in api.calls)
    state = read_json(config.path(".brain-ext/state/notion_state.json"))
    body = read_note(config.path(state["pages"][CHILD]["path"]))[1]
    label = "[Notion page]" if target_type == "page_id" else "[Notion database]"
    assert label in body and "notion:eksik-blok" not in body
    assert "Before" in body and "After" in body


@pytest.mark.parametrize("changes", [
    {"has_children": True},
    {"type": "child_page"},
    {"in_trash": True},
    {"link_to_page": {"type": "database_id", "database_id": "invalid"}},
    {"parent": {"type": "page_id", "page_id": WORK}},
])
def test_unknown_normalization_requires_owned_active_leaf_page_link(setup, changes):
    config, api, client = setup
    api.markdown[ROOT]["markdown"] = f'<unknown url="https://app.notion.com/p/{BLOCK}"/>'
    block = {**child(BLOCK, ROOT, "link_to_page"), "in_trash": False,
             "link_to_page": {"type": "page_id", "page_id": WORK}, **changes}
    api.overrides["GET", f"/blocks/{BLOCK}"] = httpx.Response(200, json=block)
    fast = Inventory(client, ROOT, discovery_cache={}).scan()
    assert fast.complete and set(fast.pages) == {ROOT, CHILD}
    assert ROOT not in fast.discovery
    assert any(p == f"/blocks/{ROOT}/children" for _, p, _ in api.calls)
