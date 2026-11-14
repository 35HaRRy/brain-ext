import importlib
import json
from uuid import UUID

import httpx
import pytest

from brainext.config import Config
from brainext.mdio import read_json, read_note, write_json, write_note
from brainext.notion.client import NotionClient

ROOT, CHILD, WORK, CREATED, BLOCK, DB, DS, OUTSIDE = [str(UUID(int=n)) for n in range(1, 9)]


def service(name):
    try:
        return getattr(importlib.import_module("brainext.notion." + name), name)
    except ModuleNotFoundError:
        pytest.fail("Senkron servisi henüz uygulanmadı")


def page(id, parent=None, title="Türkçe İş: / Planı", edited="2026-11-03T00:00:00Z"):
    return {"object": "page", "id": id, "parent": {"type": "page_id", "page_id": parent}
            if parent else {"type": "workspace", "workspace": True},
            "last_edited_time": edited, "archived": False, "in_trash": False,
            "url": "https://app.notion.com/p/" + id,
            "properties": {"title": {"id": "title", "type": "title", "title": [
                {"plain_text": title, "type": "text", "text": {"content": title}}]}}}


def child(id, parent, type="child_page", has_children=False):
    return {"object": "block", "id": id, "type": type, type: {},
            "has_children": has_children, "parent": {"type": "page_id", "page_id": parent}}


def listing(results, **extra):
    return {"object": "list", "results": results, "has_more": False, "next_cursor": None, **extra}


class API:
    def __init__(self):
        self.pages = {ROOT: page(ROOT), CHILD: page(CHILD, ROOT), WORK: page(WORK)}
        self.children = {ROOT: [child(CHILD, ROOT)], CHILD: [], WORK: []}
        self.markdown = {id: {"object": "page_markdown", "id": id, "markdown": "İçerik\n",
                              "truncated": False, "unknown_block_ids": []} for id in self.pages}
        self.calls = []
        self.overrides = {}
        self.post_status = 200
        self.commit = True
        self.patch_status = 200
        self.patch_warnings = []

    def __call__(self, request):
        path = request.url.path.removeprefix("/v1")
        self.calls.append((request.method, path, request))
        override = self.overrides.get((request.method, path))
        if override:
            return override(request) if callable(override) else override
        parts = path.strip("/").split("/")
        if request.method == "POST" and path == "/pages":
            data = json.loads(request.content)
            assert data["markdown_version"] == "v2"
            assert "brainext-push-id: " in data["markdown"]
            if self.commit:
                self.pages[CREATED] = page(CREATED, WORK)
                self.children[WORK] = [child(CREATED, WORK)]
                self.children[CREATED] = []
                self.markdown[CREATED] = {"markdown": data["markdown"], "truncated": False,
                                          "unknown_block_ids": []}
            return httpx.Response(self.post_status, json=self.pages.get(CREATED, {}))
        if request.method == "PATCH":
            data = json.loads(request.content)
            assert data["type"] == "replace_content"
            assert data["markdown_version"] == "v2"
            assert "allow_deleting_content" not in request.content.decode()
            if not self.patch_warnings:
                self.markdown[parts[1]]["markdown"] = data["replace_content"]["new_str"]
            return httpx.Response(self.patch_status, json={"warnings": self.patch_warnings})
        if parts[0] == "pages" and len(parts) == 2 and parts[1] in self.pages:
            return httpx.Response(200, json=self.pages[parts[1]])
        if parts[0] == "pages" and len(parts) == 3 and parts[2] == "markdown":
            assert request.url.params["markdown_version"] == "v2"
            if parts[1] in self.markdown:
                return httpx.Response(200, json=self.markdown[parts[1]])
        if parts[0] == "blocks" and len(parts) == 3 and parts[1] in self.children:
            return httpx.Response(200, json=listing(self.children[parts[1]]))
        return httpx.Response(404, json={"code": "object_not_found", "message": "secret-response"})


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr("brainext.notion.client.time.sleep", lambda _: None)
    config = Config(tmp_path, brain_root_page_id=ROOT, agent_workspace_id=WORK)
    api = API()
    with NotionClient(config, "secret-token", httpx.MockTransport(api)) as client:
        yield config, api, client


def mirror(config, id=CHILD):
    return next(p for p in config.path("notion").glob("*.md") if read_note(p)[0]["notion_id"] == id)


def draft(config, **metadata):
    path = config.path("agent-out/öneri.md")
    write_note(path, {"title": "Öneri", "notion_target": "agent-workspace", "status": "approved",
                      **metadata}, "Yeni içerik\n")
    return path


def test_pull_json_incremental_discovers_new_descendants_and_local_hash(setup):
    config, api, client = setup
    pull = service("pull")
    assert pull(config, client)["exit_code"] == 0
    path = mirror(config)
    metadata, body = read_note(path)
    assert metadata["kind"] == "untrusted"
    assert metadata["source"] == "notion-mirror"
    assert body == "İçerik\n"
    assert "Türkçe" in path.name and ":" not in path.name
    json.loads(path.read_text(encoding="utf-8").split("---")[1])
    api.calls.clear()
    assert pull(config, client)["exit_code"] == 0
    assert not any(p.endswith("/markdown") for _, p, _ in api.calls)
    assert any(p == f"/blocks/{CHILD}/children" for _, p, _ in api.calls)
    path.write_text(path.read_text(encoding="utf-8") + "elle düzenleme", encoding="utf-8")
    assert pull(config, client)["exit_code"] == 2
    assert "elle düzenleme" in path.read_text(encoding="utf-8")
    assert pull(config, client, force=True)["exit_code"] == 1
    assert pull(config, client, force=True, confirm_force=True)["exit_code"] == 0
    assert "elle düzenleme" not in path.read_text(encoding="utf-8")
    api.children[CHILD].append(child(CREATED, CHILD))
    api.pages[CREATED] = page(CREATED, CHILD)
    api.children[CREATED] = []
    api.markdown[CREATED] = dict(api.markdown[ROOT])
    assert pull(config, client)["exit_code"] == 0
    assert mirror(config, CREATED).exists()


def test_pull_rename_archive_and_unowned_collision(setup):
    config, api, client = setup
    pull = service("pull")
    assert pull(config, client)["exit_code"] == 0
    old = mirror(config)
    api.pages[CHILD] = page(CHILD, ROOT, title="CON", edited="new")
    assert pull(config, client)["exit_code"] == 0
    renamed = mirror(config)
    assert not old.exists() and renamed.exists()
    api.children[ROOT] = []
    api.pages[CHILD]["in_trash"] = True
    assert pull(config, client)["exit_code"] == 0
    archived = list(config.path("notion/_arsiv").glob("*.md"))
    assert len(archived) == 1
    assert read_note(archived[0])[0]["status"] == "archived"
    assert not renamed.exists()


@pytest.mark.parametrize("failure", ["forbidden", "cursor", "incomplete"])
def test_incomplete_scan_never_archives(setup, failure):
    config, api, client = setup
    pull = service("pull")
    assert pull(config, client)["exit_code"] == 0
    old = mirror(config)
    if failure == "forbidden":
        response = httpx.Response(403, json={})
    else:
        response = httpx.Response(200, json=listing([], **(
            {"has_more": True} if failure == "cursor" else {"request_status": {"type": "incomplete"}})))
    api.overrides["GET", f"/blocks/{ROOT}/children"] = response
    assert pull(config, client)["exit_code"] == 2
    assert old.exists()


def test_unknown_expands_in_place_and_repeat_404_is_safe_partial(setup):
    config, api, client = setup
    api.markdown[CHILD] = {"markdown": f'A<unknown id="{BLOCK}"/>B<unknown id="{OUTSIDE}"/>C',
                           "truncated": True, "unknown_block_ids": [BLOCK, BLOCK, OUTSIDE]}
    api.markdown[BLOCK] = {"markdown": "ORTA", "truncated": False, "unknown_block_ids": []}
    result = service("pull")(config, client)
    assert result["exit_code"] == 2
    body = read_note(mirror(config))[1]
    assert body == f"AORTAB<!-- notion:eksik-blok {OUTSIDE} -->C"
    assert sum(p == f"/pages/{BLOCK}/markdown" for _, p, _ in api.calls) == 1
    assert "secret" not in json.dumps(result)


def test_dry_run_zero_disk_and_state_corrupt_fail_closed(setup):
    config, api, client = setup
    assert service("pull")(config, client, dry_run=True)["exit_code"] == 0
    assert list(config.vault.iterdir()) == []
    state = config.path(".brain-ext/state/notion_state.json")
    write_json(state, {"version": 1, "pages": {CHILD: {"path": "../notes/secret.md"}}})
    before = state.read_bytes()
    assert service("pull")(config, client)["exit_code"] == 1
    assert state.read_bytes() == before
    assert not config.path("notion").exists()


def test_page_outside_brain_is_rejected(setup):
    config, api, client = setup
    api.pages[OUTSIDE] = page(OUTSIDE)
    assert service("pull")(config, client, page=OUTSIDE)["exit_code"] == 1
    assert not config.path("notion").exists()


@pytest.mark.parametrize("status,commit,expected", [(200, True, 0), (503, True, 0), (503, False, 2)])
def test_push_durable_pending_and_reconciliation_never_duplicate(setup, status, commit, expected):
    config, api, client = setup
    path = draft(config)
    push = service("push")
    api.post_status, api.commit = status, commit
    original = api.__call__

    def check_pending(request):
        if request.method == "POST" and request.url.path == "/v1/pages":
            state = read_json(config.path(".brain-ext/state/push_state.json"))
            entry = state["drafts"]["agent-out/öneri.md"]
            assert entry["status"] == "pending"
            UUID(entry["push_id"])
        return original(request)

    with NotionClient(config, "secret", httpx.MockTransport(check_pending)) as checking:
        assert push(config, checking)["exit_code"] == expected
    metadata = read_note(path)[0]
    assert metadata["status"] == ("pushed" if expected == 0 else "uncertain")
    assert push(config, client)["exit_code"] in (0, 2)
    assert sum(method == "POST" and p == "/pages" for method, p, _ in api.calls) == 1


def test_push_dry_run_and_unapproved_are_no_http_writes_or_disk_changes(setup):
    config, api, client = setup
    path = draft(config)
    before = path.read_bytes()
    assert service("push")(config, client, dry_run=True)["exit_code"] == 0
    assert before == path.read_bytes()
    assert not config.state.exists()
    assert not any(m == "PATCH" or (m == "POST" and p == "/pages") for m, p, _ in api.calls)
    write_note(path, {"status": "draft"}, "unapproved")
    assert service("push")(config, client)["exit_code"] == 0
    assert not any(m == "PATCH" or (m == "POST" and p == "/pages") for m, p, _ in api.calls)


@pytest.mark.parametrize("mode", ["no_match", "timeout", "outside", "forged"])
def test_push_existing_requires_state_ownership_ancestry_and_patch_readback(setup, mode):
    config, api, client = setup
    path = draft(config)
    push = service("push")
    assert push(config, client)["exit_code"] == 0
    metadata, _ = read_note(path)
    metadata["status"] = "approved"
    write_note(path, metadata, "Düzenleme\n")
    if mode == "no_match":
        api.patch_warnings = [{"code": "no_match", "message": "secret"}]
    elif mode == "timeout":
        api.patch_status = 503
    elif mode == "outside":
        api.pages[CREATED] = page(CREATED, OUTSIDE)
        api.pages[OUTSIDE] = page(OUTSIDE)
    else:
        api.markdown[CREATED]["markdown"] = "foreign page"
    result = push(config, client)
    assert result["exit_code"] == (0 if mode == "timeout" else 2)
    if mode in {"outside", "forged"}:
        assert not any(m == "PATCH" for m, _, _ in api.calls)
    assert "secret" not in json.dumps(result)


def test_draft_notion_id_alone_never_grants_write_ownership(setup):
    config, api, client = setup
    draft(config, notion_id=CHILD)
    assert service("push")(config, client)["exit_code"] == 2
    assert not any(m == "PATCH" or (m == "POST" and p == "/pages") for m, p, _ in api.calls)


def database(api, *, workspace=False):
    root = WORK if workspace else ROOT
    api.children[root] = [child(DB, root, "child_database")]
    db = {"object": "database", "id": DB, "parent": {"type": "page_id", "page_id": root},
          "data_sources": [{"id": DS, "name": "Kaynak"}]}
    ds = {"object": "data_source", "id": DS, "parent": {"type": "database_id", "database_id": DB},
          "properties": {"İsim": {"id": "title", "type": "title", "title": {}}}}
    api.overrides["GET", f"/databases/{DB}"] = httpx.Response(200, json=db)
    api.overrides["GET", f"/data_sources/{DS}"] = httpx.Response(200, json=ds)
    row = page(CHILD)
    row["parent"] = {"type": "data_source_id", "data_source_id": DS}
    api.pages[CHILD] = row
    api.overrides["POST", f"/data_sources/{DS}/query"] = httpx.Response(200, json=listing([row]))
    return db, ds, row


def test_nested_blocks_cursors_and_property_pagination(setup):
    config, api, client = setup
    database(api)
    api.children[ROOT] = [child(BLOCK, ROOT, "toggle", True)]
    api.children[BLOCK] = [child(DB, BLOCK, "child_database")]
    prop = {"id": "rel", "type": "relation", "relation": [{"id": ROOT}], "has_more": True}
    row = api.pages[CHILD]
    row["properties"]["Bağlantı"] = prop
    api.overrides["POST", f"/data_sources/{DS}/query"] = httpx.Response(200, json=listing([row]))
    cursor_calls = []

    def property_page(request):
        cursor = request.url.params.get("start_cursor")
        cursor_calls.append(cursor)
        return httpx.Response(200, json=listing([
            {"object": "property_item", "type": "relation", "relation": {"id": ROOT if not cursor else WORK}}],
            has_more=not cursor, next_cursor="next" if not cursor else None))

    api.overrides["GET", f"/pages/{CHILD}/properties/rel"] = property_page
    assert service("pull")(config, client)["exit_code"] == 0
    relations = read_note(mirror(config))[0]["properties"]["Bağlantı"]["relation"]
    assert relations == [{"id": ROOT}, {"id": WORK}]
    assert cursor_calls == [None, "next"]


@pytest.mark.parametrize("mode", ["incomplete", "limit", "external"])
def test_database_scope_and_explicit_partial_limit(setup, mode):
    config, api, client = setup
    db, ds, row = database(api)
    if mode == "external":
        db["parent"] = {"type": "workspace", "workspace": True}
        api.overrides["GET", f"/databases/{DB}"] = httpx.Response(200, json=db)
    elif mode == "incomplete":
        api.overrides["POST", f"/data_sources/{DS}/query"] = httpx.Response(
            200, json=listing([row], request_status={"type": "incomplete"}))
    else:
        api.overrides["POST", f"/data_sources/{DS}/query"] = httpx.Response(200, json=listing([row] * 10000))
    report = service("pull")(config, client)
    assert report["exit_code"] == (0 if mode == "external" else 2)
    if mode == "external":
        assert not any("/query" in p for _, p, _ in api.calls)
        assert all(read_note(p)[0]["notion_id"] != CHILD for p in config.path("notion").glob("*.md"))
    else:
        assert "10000" in json.dumps(report)


def test_no_unowned_overwrite_even_force_and_hash_covers_header(setup):
    config, api, client = setup
    pull = service("pull")
    assert pull(config, client)["exit_code"] == 0
    old = mirror(config)
    metadata, body = read_note(old)
    metadata["source"] = "user-note"
    write_note(old, metadata, body)
    before = old.read_bytes()
    assert pull(config, client, force=True, confirm_force=True)["exit_code"] == 2
    assert before == old.read_bytes()


def test_unknown_cycles_are_bounded_and_repeated_placeholders_reuse_content(setup):
    config, api, client = setup
    api.markdown[CHILD] = {"markdown": f'<unknown id="{BLOCK}"/><unknown id="{BLOCK}"/>',
                           "unknown_block_ids": [BLOCK], "truncated": True}
    api.markdown[BLOCK] = {"markdown": f'X<unknown id="{BLOCK}"/>Y',
                           "unknown_block_ids": [BLOCK], "truncated": True}
    assert service("pull")(config, client)["exit_code"] == 2
    assert sum(p == f"/pages/{BLOCK}/markdown" for _, p, _ in api.calls) == 1
    assert read_note(mirror(config))[1] == (f"X<!-- notion:eksik-blok {BLOCK} -->Y" * 2)


@pytest.fixture
def self_unknown_page_link(setup):
    config, api, client = setup
    api.markdown[CHILD] = {
        "markdown": f'A<unknown id="{BLOCK}"/>B<unknown id="{BLOCK}"/>C',
        "unknown_block_ids": [BLOCK], "truncated": True,
    }
    api.markdown[BLOCK] = {
        "markdown": f'<unknown url="https://app.notion.com/p/{BLOCK}"/>',
        "unknown_block_ids": [BLOCK], "truncated": True,
    }
    block = {**child(BLOCK, CHILD, type="link_to_page"), "archived": False, "in_trash": False,
             "link_to_page": {"type": "page_id", "page_id": OUTSIDE}}
    api.overrides["GET", f"/blocks/{BLOCK}"] = lambda _: httpx.Response(200, json=block)
    return config, api, client, block


def test_self_unknown_page_link_is_recovered_without_fetching_target(self_unknown_page_link):
    from brainext.search.graph import parse_links

    config, api, client, _ = self_unknown_page_link

    report = service("pull")(config, client)

    assert report["exit_code"] == 0
    body = read_note(mirror(config))[1]
    link = "[Notion page](https://app.notion.com/p/00000000000000000000000000000008)"
    assert body == f"A{link}B{link}C"
    assert parse_links(body) == [
        ("https://app.notion.com/p/00000000000000000000000000000008", "markdown-link"),
        ("https://app.notion.com/p/00000000000000000000000000000008", "markdown-link"),
    ]
    assert read_json(config.path(".brain-ext/state/notion_state.json"))["pages"][CHILD]["partial"] is False
    assert sum(path == f"/blocks/{BLOCK}" for _, path, _ in api.calls) == 1
    assert sum(path == f"/pages/{BLOCK}/markdown" for _, path, _ in api.calls) == 1
    assert not any(OUTSIDE in path for _, path, _ in api.calls)
    assert all(method == "GET" for method, _, _ in api.calls)


@pytest.mark.parametrize("changes", [
    {"id": OUTSIDE}, {"id": None}, {"object": "page"}, {"type": "bookmark"},
    {"archived": True}, {"in_trash": True}, {"has_children": True},
    {"link_to_page": {"type": "data_source_id", "data_source_id": DS}},
    {"link_to_page": {"type": "page_id", "page_id": "not-a-uuid"}},
    {"link_to_page": {"type": "page_id"}}, {"link_to_page": []},
])
def test_self_unknown_page_link_rejects_unverified_block(self_unknown_page_link, changes):
    config, api, client, block = self_unknown_page_link
    block.update(changes)

    report = service("pull")(config, client)

    assert report["exit_code"] == 2
    missing = f"<!-- notion:eksik-blok {BLOCK} -->"
    assert read_note(mirror(config))[1] == f"A{missing}B{missing}C"
    assert not any(OUTSIDE in path for _, path, _ in api.calls)


@pytest.mark.parametrize("status", [403, 404])
def test_self_unknown_page_link_access_failure_stays_partial(self_unknown_page_link, status):
    config, api, client, _ = self_unknown_page_link
    api.overrides["GET", f"/blocks/{BLOCK}"] = httpx.Response(status, json={
        "code": "object_not_found", "message": "secret diagnostic text"})

    report = service("pull")(config, client)

    assert report["exit_code"] == 2
    assert "notion:eksik-blok" in read_note(mirror(config))[1]
    assert "secret" not in json.dumps(report)
    assert sum(path == f"/blocks/{BLOCK}" for _, path, _ in api.calls) == 1


def test_self_unknown_database_link_is_preserved_without_querying_target(self_unknown_page_link):
    config, api, client, block = self_unknown_page_link
    block["link_to_page"] = {"type": "database_id", "database_id": DB}
    assert service("pull")(config, client)["exit_code"] == 0
    assert "[Notion database]" in read_note(mirror(config))[1]
    assert not any(path == f"/databases/{DB}" for _, path, _ in api.calls)


@pytest.mark.parametrize("archived", ["missing", None])
def test_self_unknown_page_link_accepts_notion_null_archived(self_unknown_page_link, archived):
    config, _, client, block = self_unknown_page_link
    if archived == "missing":
        block.pop("archived")
    else:
        block["archived"] = archived
    block["in_trash"] = False

    report = service("pull")(config, client)

    assert report["exit_code"] == 0
    assert "[Notion page](https://app.notion.com/p/00000000000000000000000000000008)" in read_note(
        mirror(config))[1]
    assert read_json(config.path(".brain-ext/state/notion_state.json"))["pages"][CHILD]["partial"] is False


def test_self_unknown_page_link_does_not_hide_markdown_warnings(self_unknown_page_link):
    config, api, client, _ = self_unknown_page_link
    api.markdown[BLOCK]["warnings"] = [{"code": "unsupported_tag", "message": "warning"}]

    report = service("pull")(config, client)

    assert report["exit_code"] == 2
    assert "[Notion page](" in read_note(mirror(config))[1]
    assert read_json(config.path(".brain-ext/state/notion_state.json"))["pages"][CHILD]["partial"] is True


def test_committed_hint_outside_workspace_is_not_accepted(setup):
    config, api, client = setup
    path = draft(config)
    api.pages[OUTSIDE] = page(OUTSIDE)

    def post(request):
        content = json.loads(request.content)["markdown"]
        api.markdown[OUTSIDE] = {"markdown": content}
        return httpx.Response(503, json={"additional_data": {
            "committed_resource_id": OUTSIDE, "retry_guidance": "secret"}})

    api.overrides["POST", "/pages"] = post
    assert service("push")(config, client)["exit_code"] == 2
    assert read_note(path)[0]["status"] == "uncertain"


def test_push_database_resolves_title_and_datasource(setup):
    config, api, client = setup
    database(api, workspace=True)
    config = Config(config.vault, brain_root_page_id=ROOT, agent_workspace_id=DB)
    draft(config)
    api.pages[CREATED] = page(CREATED)
    api.pages[CREATED]["parent"] = {"type": "data_source_id", "data_source_id": DS}

    def post(request):
        payload = json.loads(request.content)
        assert payload["parent"] == {"type": "data_source_id", "data_source_id": DS}
        assert list(payload["properties"]) == ["İsim"]
        api.markdown[CREATED] = {"markdown": payload["markdown"]}
        return httpx.Response(200, json=api.pages[CREATED])

    api.overrides["POST", "/pages"] = post
    assert service("push")(config, client)["exit_code"] == 0


def test_recovery_does_not_claim_later_local_edits_were_sent(setup):
    config, api, client = setup
    path = draft(config)
    api.post_status, api.commit = 503, False
    push = service("push")
    assert push(config, client)["exit_code"] == 2
    state = read_json(config.path(".brain-ext/state/push_state.json"))
    entry = state["drafts"]["agent-out/öneri.md"]
    api.pages[CREATED] = page(CREATED, WORK)
    api.children[WORK] = [child(CREATED, WORK)]
    api.children[CREATED] = []
    api.markdown[CREATED] = {"markdown": f'Yeni içerik\n\nbrainext-push-id: {entry["push_id"]}\n'}
    metadata, _ = read_note(path)
    metadata["status"] = "approved"
    write_note(path, metadata, "Sonradan değişti\n")
    assert push(config, client)["exit_code"] == 2
    assert read_note(path)[0]["status"] != "pushed"


def test_container_cycle_is_partial_not_recursion_error(setup):
    config, api, client = setup
    api.children[ROOT] = [child(BLOCK, ROOT, "toggle", True)]
    api.children[BLOCK] = [child(BLOCK, ROOT, "toggle", True)]
    assert service("pull")(config, client)["exit_code"] == 2
    assert len(api.calls) < 10


def test_local_change_during_download_is_not_overwritten(setup):
    config, api, client = setup
    pull = service("pull")
    assert pull(config, client)["exit_code"] == 0
    old = mirror(config)
    api.pages[CHILD]["last_edited_time"] = "later"

    def changed(request):
        old.write_text(old.read_text(encoding="utf-8") + "insan değişikliği", encoding="utf-8")
        return httpx.Response(200, json={"markdown": "remote"})

    api.overrides["GET", f"/pages/{CHILD}/markdown"] = changed
    assert pull(config, client)["exit_code"] == 2
    assert read_note(old)[1].endswith("insan değişikliği")


def test_lock_mirror_on_unchanged_file_is_explicit_and_dry_run_does_not_chmod(setup):
    import os
    import stat

    config, api, client = setup
    pull = service("pull")
    assert pull(config, client)["exit_code"] == 0
    old = mirror(config)
    assert old.stat().st_mode & stat.S_IWRITE
    assert pull(config, client, lock_mirror=True, dry_run=True)["exit_code"] == 0
    assert old.stat().st_mode & stat.S_IWRITE
    assert pull(config, client, lock_mirror=True)["exit_code"] == 0
    assert not old.stat().st_mode & stat.S_IWRITE
    old.chmod(old.stat().st_mode | stat.S_IWRITE)
    assert os.access(old, os.W_OK)


@pytest.mark.parametrize("kind,data", [
    ("notion", {"version": True, "pages": {}}),
    ("push", {"version": 1, "drafts": {"agent-out/öneri.md": {
        "push_id": ROOT, "status": "pending", "workspace_id": WORK}}}),
])
def test_malformed_state_is_rejected_before_http(setup, kind, data):
    config, api, client = setup
    draft(config)
    state = config.path(f".brain-ext/state/{kind}_state.json")
    write_json(state, data)
    assert service("pull" if kind == "notion" else "push")(config, client)["exit_code"] == 1
    assert api.calls == []


def test_operation_lock_blocks_both_services_without_http(setup):
    from brainext.mdio import operation_lock

    config, api, client = setup
    draft(config)
    with operation_lock(config.state):
        assert service("pull")(config, client)["exit_code"] == 1
        assert service("push")(config, client)["exit_code"] == 1
    assert api.calls == []


def test_rollup_pagination_keeps_final_aggregate_not_incomplete_value(setup):
    config, api, client = setup
    database(api)
    row = api.pages[CHILD]
    row["properties"]["Toplam"] = {"id": "roll", "type": "rollup", "rollup": {"type": "incomplete"}}
    api.overrides["POST", f"/data_sources/{DS}/query"] = httpx.Response(200, json=listing([row]))
    api.overrides["GET", f"/pages/{CHILD}/properties/roll"] = httpx.Response(200, json=listing(
        [{"object": "property_item", "type": "number", "number": 3}], property_item={
            "id": "roll", "type": "rollup", "rollup": {"type": "number", "number": 3, "function": "sum"}}))
    assert service("pull")(config, client)["exit_code"] == 0
    assert read_note(mirror(config))[0]["properties"]["Toplam"]["rollup"] == {
        "type": "number", "number": 3, "function": "sum"}


@pytest.mark.parametrize("kind", ["mirror", "draft"])
def test_malformed_frontmatter_returns_safe_report(setup, kind):
    config, api, client = setup
    if kind == "mirror":
        assert service("pull")(config, client)["exit_code"] == 0
        path = mirror(config)
    else:
        path = draft(config)
    path.write_text("---\nkey: [secret-response\n---\nbody", encoding="utf-8")
    before = path.read_bytes()
    result = service("pull" if kind == "mirror" else "push")(config, client)
    assert result["exit_code"] == 2
    assert "secret" not in json.dumps(result)
    assert before == path.read_bytes()


def test_pull_block_children_cursor_traverses_later_pages(setup):
    config, api, client = setup
    cursors = []

    def children(request):
        cursor = request.url.params.get("start_cursor")
        cursors.append(cursor)
        return httpx.Response(200, json=listing(
            [child(CHILD, ROOT)] if cursor else [], has_more=not cursor,
            next_cursor="second" if not cursor else None))

    api.overrides["GET", f"/blocks/{ROOT}/children"] = children
    assert service("pull")(config, client)["exit_code"] == 0
    assert mirror(config).exists()
    assert cursors == [None, "second"]


def test_full_fetches_unchanged_content_but_single_page_never_archives_others(setup):
    config, api, client = setup
    pull = service("pull")
    assert pull(config, client)["exit_code"] == 0
    api.calls.clear()
    assert pull(config, client, full=True, page=CHILD)["exit_code"] == 0
    downloads = [p for _, p, _ in api.calls if p.endswith("/markdown")]
    assert downloads == [f"/pages/{CHILD}/markdown"]
    assert mirror(config, ROOT).exists()


def test_unowned_destination_is_preserved_and_not_adopted_even_force(setup):
    config, api, client = setup
    base = config.path("notion")
    base.mkdir()
    for suffix in ("00000000", CHILD.replace("-", "")):
        (base / f"Türkçe-İş----Planı__{suffix}.md").write_text("kullanıcı", encoding="utf-8")
    report = service("pull")(config, client, force=True, confirm_force=True)
    assert report["exit_code"] == 2
    for suffix in ("00000000", CHILD.replace("-", "")):
        assert (base / f"Türkçe-İş----Planı__{suffix}.md").read_text(encoding="utf-8") == "kullanıcı"
    assert CHILD not in read_json(config.path(".brain-ext/state/notion_state.json"))["pages"]
