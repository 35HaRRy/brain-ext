import importlib
import json
from dataclasses import replace
from uuid import UUID

import httpx
import pytest
from notion_markdown_fixture import page_markdown
from test_notion_sync import API, CHILD, CREATED, OUTSIDE, ROOT, WORK, child, page

from brainext.config import Config
from brainext.mdio import read_json, read_note, write_json, write_note
from brainext.notion.client import NotionClient
from brainext.notion.pull import pull

JOURNAL = ".brain-ext/state/changes_state.json"


def changes():
    try:
        return importlib.import_module("brainext.notion.changes")
    except ModuleNotFoundError:
        pytest.fail("Notion değişiklik kuyruğu henüz uygulanmadı")


class ChangeAPI(API):
    def __init__(self):
        super().__init__()
        self.pages[OUTSIDE] = page(OUTSIDE, title="Accessible outside memory")
        self.children[OUTSIDE] = []
        self.markdown[OUTSIDE] = {"markdown": "Outside\n", "truncated": False,
                                  "unknown_block_ids": []}

    def __call__(self, request):
        path = request.url.path.removeprefix("/v1")
        override = self.overrides.get((request.method, path))
        if override:
            return super().__call__(request)
        if request.method == "GET" and path.endswith("/markdown"):
            id = path.split("/")[2]
            if id in self.markdown:
                self.calls.append((request.method, path, request))
                return httpx.Response(200, json=page_markdown(self, id))
        if request.method == "POST" and path == "/pages":
            self.calls.append((request.method, path, request))
            data = json.loads(request.content)
            parent = data["parent"]["page_id"]
            assert data["markdown_version"] == "v2"
            if self.commit:
                self.pages[CREATED] = page(CREATED, parent, title=data["properties"]["title"]["title"][0]["text"]["content"])
                self.children[parent].append(child(CREATED, parent))
                self.children[CREATED] = []
                self.markdown[CREATED] = {"markdown": data["markdown"], "truncated": False,
                                          "unknown_block_ids": []}
            return httpx.Response(self.post_status, json=self.pages.get(CREATED, {}))
        if request.method == "PATCH":
            self.calls.append((request.method, path, request))
            id = path.split("/")[2]
            data = json.loads(request.content)
            assert "allow_deleting_content" not in request.content.decode()
            if path.endswith("/markdown"):
                assert data["type"] == "update_content"
                edit, = data["update_content"]["content_updates"]
                text = self.markdown[id]["markdown"]
                assert text.count(edit["old_str"]) == 1
                if self.commit:
                    self.markdown[id]["markdown"] = text.replace(edit["old_str"], edit["new_str"], 1)
            else:
                assert data == {"in_trash": True}
                if self.commit:
                    self.pages[id]["in_trash"] = True
            if self.commit:
                self.pages[id]["last_edited_time"] += "+"
            return httpx.Response(self.patch_status, json={"id": id, "warnings": self.patch_warnings})
        return super().__call__(request)


@pytest.fixture
def queue_setup(tmp_path, monkeypatch):
    monkeypatch.setattr("brainext.notion.client.time.sleep", lambda _: None)
    config = Config(tmp_path, brain_root_page_id=ROOT, agent_workspace_id=WORK)
    api = ChangeAPI()
    with NotionClient(config, "secret-token", httpx.MockTransport(api)) as client:
        yield config, api, client


def proposal(config, client, action="update", target=CHILD, **kwargs):
    if action == "update":
        kwargs = {"old_str": "İçerik", "new_str": "Yeni içerik", **kwargs}
    return changes().propose(config, client, action=action, target=target,
                             reason="Kullanıcının istediği düzeltme", **kwargs)


def rows(config):
    return changes().review(config)["results"]


def approve_all(config):
    return changes().approve(config, {
        row["id"]: row["request_hash"] for row in rows(config)
        if row["status"] == "queued"
    })


def mutations(api):
    return [(m, p) for m, p, _ in api.calls
            if m == "PATCH" or (m == "POST" and p == "/pages")]


def test_create_is_automatic_at_any_accessible_parent(queue_setup):
    config, api, client = queue_setup
    staged = proposal(config, client, "create", OUTSIDE, title="Yeni not", body="Özet\n")
    assert staged["exit_code"] == 0
    assert rows(config)[0]["status"] == "queued"
    assert not mutations(api)
    assert changes().apply(config, client)["counts"]["applied"] == 1
    assert api.pages[CREATED]["parent"]["page_id"] == OUTSIDE
    assert "brainext-push-id: " + staged["id"] in api.markdown[CREATED]["markdown"]
    assert rows(config)[0]["status"] == "applied"
    before = len(mutations(api))
    assert changes().apply(config, client)["exit_code"] == 0
    assert len(mutations(api)) == before


def test_update_waits_for_hash_bound_batch_approval_and_uses_targeted_edit(queue_setup):
    config, api, client = queue_setup
    proposal(config, client)
    row, = rows(config)
    assert "-İçerik" in row["diff"] and "+Yeni içerik" in row["diff"]
    assert changes().apply(config, client)["counts"]["waiting"] == 1
    assert not mutations(api)
    assert changes().approve(config, {row["id"]: "sha256:" + "0" * 64})["exit_code"] == 1
    assert approve_all(config)["exit_code"] == 0
    assert changes().apply(config, client)["counts"]["applied"] == 1
    assert api.markdown[CHILD]["markdown"] == "Yeni içerik\n"
    assert rows(config)[0]["status"] == "applied"


@pytest.mark.parametrize("action", ["update", "delete"])
def test_remote_changes_invalidate_approved_operation(queue_setup, action):
    config, api, client = queue_setup
    proposal(config, client, action)
    approve_all(config)
    api.markdown[CHILD]["markdown"] += "İnsan düzenlemesi\n"
    assert changes().apply(config, client)["counts"]["conflicts"] == 1
    assert not mutations(api)
    assert rows(config)[0]["status"] == "conflict"


def test_delete_is_reviewed_trash_with_acknowledged_unique_history(queue_setup):
    config, api, client = queue_setup
    proposal(config, client, "delete")
    assert changes().apply(config, client)["counts"]["waiting"] == 1
    approve_all(config)
    assert changes().apply(config, client)["counts"]["applied"] == 1
    assert api.pages[CHILD]["in_trash"]
    state = read_json(config.path(JOURNAL))
    tombstone, = state["tombstones"].values()
    assert tombstone["page_id"] == CHILD and tombstone["origin"] == "local"
    assert tombstone["acknowledged_at"]
    UUID(tombstone["id"])


def test_delete_subtree_changed_child_and_root_protection(queue_setup):
    config, api, client = queue_setup
    api.children[CHILD] = [child(CREATED, CHILD)]
    api.pages[CREATED] = page(CREATED, CHILD)
    api.children[CREATED] = []
    api.markdown[CREATED] = dict(api.markdown[CHILD])
    assert proposal(config, client, "delete", ROOT)["exit_code"] == 1
    proposal(config, client, "delete")
    approve_all(config)
    api.markdown[CREATED]["markdown"] += "Changed descendant"
    assert changes().apply(config, client)["counts"]["conflicts"] == 1
    assert not mutations(api)


@pytest.mark.parametrize("mode", ["partial", "missing", "duplicate", "structural"])
def test_unsafe_update_cannot_be_proposed(queue_setup, mode):
    config, api, client = queue_setup
    kwargs = {}
    if mode == "partial":
        api.markdown[CHILD]["truncated"] = True
    elif mode == "missing":
        kwargs["old_str"] = "absent"
    elif mode == "duplicate":
        api.markdown[CHILD]["markdown"] *= 2
    else:
        kwargs["new_str"] = '<page url="https://example.com"/>'
    assert proposal(config, client, **kwargs)["exit_code"] == 1
    assert not mutations(api)
    assert not config.path(JOURNAL).exists()


@pytest.mark.parametrize("action", ["create", "update", "delete"])
def test_all_remote_queue_paths_dry_run_preserve_bytes(queue_setup, action):
    config, api, client = queue_setup
    kwargs = {"title": "Note", "body": "Body"} if action == "create" else {}
    assert proposal(config, client, action, dry_run=True, **kwargs)["exit_code"] == 0
    assert list(config.vault.iterdir()) == []
    proposal(config, client, action, **kwargs)
    approve_all(config)
    before = config.path(JOURNAL).read_bytes()
    assert changes().apply(config, client, dry_run=True)["exit_code"] == 0
    assert config.path(JOURNAL).read_bytes() == before
    assert not mutations(api)


@pytest.mark.parametrize("action", ["create", "update", "delete"])
@pytest.mark.parametrize("commit", [True, False])
def test_uncertain_write_reconciles_without_blind_replay(queue_setup, action, commit):
    config, api, client = queue_setup
    kwargs = {"title": "Note", "body": "Body\n"} if action == "create" else {}
    proposal(config, client, action, **kwargs)
    approve_all(config)
    api.post_status = api.patch_status = 503
    api.commit = commit
    first = changes().apply(config, client)
    assert first["counts"]["applied" if commit else "uncertain"] == 1
    count = len(mutations(api))
    assert count == 1
    changes().apply(config, client)
    assert len(mutations(api)) == count
    assert rows(config)[0]["status"] == ("applied" if commit else "uncertain")


def test_pending_is_persisted_before_write(queue_setup):
    config, api, client = queue_setup
    proposal(config, client)
    approve_all(config)
    original = api.__call__

    def check(request):
        if request.method == "PATCH":
            state = read_json(config.path(JOURNAL))
            assert next(iter(state["operations"].values()))["status"] == "pending"
        return original(request)

    with NotionClient(config, "secret", httpx.MockTransport(check)) as checking:
        assert changes().apply(config, checking)["counts"]["applied"] == 1


def test_corrupt_or_edited_payload_fails_closed(queue_setup):
    config, api, client = queue_setup
    proposal(config, client)
    approve_all(config)
    state = read_json(config.path(JOURNAL))
    next(iter(state["operations"].values()))["new_str"] = "Unapproved change"
    write_json(config.path(JOURNAL), state)
    assert changes().apply(config, client)["exit_code"] == 1
    assert not mutations(api)


def test_cancel_only_unsent_operations(queue_setup):
    config, api, client = queue_setup
    item = proposal(config, client, "delete")
    assert changes().cancel(config, [item["id"]])["exit_code"] == 0
    assert rows(config)[0]["status"] == "cancelled"
    assert changes().apply(config, client)["counts"]["applied"] == 0
    assert not mutations(api)


def test_delete_conflicts_with_pending_descendant_update(queue_setup):
    config, api, client = queue_setup
    config = replace(config, memory_root_page_ids=(WORK,), brain_root_page_id=WORK)
    proposal(config, client, "update")
    proposal(config, client, "delete", ROOT)
    approve_all(config)
    deletion = next(r for r in rows(config) if r["action"] == "delete")
    assert changes().apply(config, client, ids=[deletion["id"]])["counts"]["conflicts"] == 1
    assert not mutations(api)


def test_subtree_delete_journals_all_pages(queue_setup):
    config, api, client = queue_setup
    config = replace(config, brain_root_page_id=OUTSIDE)
    proposal(config, client, "delete", ROOT)
    approve_all(config)
    assert changes().apply(config, client)["counts"]["applied"] == 1
    state = read_json(config.path(JOURNAL))
    assert {t["page_id"] for t in state["tombstones"].values()} == {ROOT, CHILD}


def test_batch_approval_is_atomic_on_unknown_or_stale_item(queue_setup):
    config, api, client = queue_setup
    item = proposal(config, client)
    row = rows(config)[0]
    assert changes().approve(config, {
        item["id"]: row["request_hash"], OUTSIDE: row["request_hash"],
    })["exit_code"] == 1
    assert rows(config)[0]["status"] == "queued"


def test_deleted_or_reparented_target_cannot_be_updated(queue_setup):
    config, api, client = queue_setup
    proposal(config, client)
    approve_all(config)
    api.pages[CHILD]["in_trash"] = True
    assert changes().apply(config, client)["counts"]["conflicts"] == 1
    assert not mutations(api)


def mirror_path(config, id=CHILD):
    return next(path for path in config.path("notion").glob("*.md")
                if read_note(path)[0]["notion_id"] == id)


def test_remote_trash_is_acknowledged_without_permanent_local_delete_and_can_restore(queue_setup):
    config, api, client = queue_setup
    config = replace(config, memory_root_page_ids=(ROOT,))
    assert pull(config, client)["exit_code"] == 0
    old = mirror_path(config)
    api.pages[CHILD]["in_trash"] = True
    api.children[ROOT] = []
    assert pull(config, client)["counts"]["archived"] == 1
    assert not old.exists()
    archived, = config.path("notion/_arsiv").glob("*.md")
    assert read_note(archived)[1] == "İçerik\n"
    history = changes().review(config)["tombstones"]
    assert len(history) == 1 and history[0]["acknowledged_at"]
    assert pull(config, client)["exit_code"] == 0
    assert len(changes().review(config)["tombstones"]) == 1
    api.pages[CHILD]["in_trash"] = False
    api.children[ROOT] = [child(CHILD, ROOT)]
    assert pull(config, client)["exit_code"] == 0
    assert mirror_path(config).exists() and not archived.exists()
    assert len(changes().review(config)["tombstones"]) == 1
    assert not mutations(api)


@pytest.mark.parametrize("mode", ["access", "move", "incomplete"])
def test_absence_is_not_a_remote_deletion(queue_setup, mode):
    config, api, client = queue_setup
    config = replace(config, memory_root_page_ids=(ROOT,))
    pull(config, client)
    old = mirror_path(config)
    before = old.read_bytes()
    api.children[ROOT] = []
    if mode == "access":
        api.overrides["GET", f"/pages/{CHILD}"] = httpx.Response(404, json={})
    elif mode == "move":
        api.pages[CHILD]["parent"]["page_id"] = OUTSIDE
    else:
        api.pages[ROOT]["last_edited_time"] = "changed"
        api.overrides["GET", f"/pages/{ROOT}/markdown"] = httpx.Response(200, json={
            "markdown": "", "truncated": True, "unknown_block_ids": [],
        })
        api.overrides["GET", f"/blocks/{ROOT}/children"] = httpx.Response(403, json={})
    assert pull(config, client)["exit_code"] == 2
    assert old.read_bytes() == before
    assert not changes().review(config)["tombstones"]
    assert not mutations(api)


@pytest.mark.parametrize("blocker", ["proposal", "local-edit"])
def test_remote_trash_preserves_pending_update_or_local_edit(queue_setup, blocker):
    config, api, client = queue_setup
    config = replace(config, memory_root_page_ids=(ROOT,))
    pull(config, client)
    old = mirror_path(config)
    if blocker == "proposal":
        proposal(config, client)
    else:
        old.write_bytes(old.read_bytes() + b"Local edit")
    before = old.read_bytes()
    api.children[ROOT] = []
    api.pages[CHILD]["in_trash"] = True
    assert pull(config, client)["exit_code"] == 2
    assert old.read_bytes() == before
    assert not changes().review(config)["tombstones"]
    assert not mutations(api)


def test_missing_local_mirror_never_proposes_remote_deletion(queue_setup):
    config, api, client = queue_setup
    config = replace(config, memory_root_page_ids=(ROOT,))
    pull(config, client)
    mirror_path(config).unlink()
    assert pull(config, client)["exit_code"] == 2
    assert not api.pages[CHILD]["in_trash"]
    assert not mutations(api)
    assert not rows(config)


def test_remote_parent_trash_conflicts_with_pending_child_proposal(queue_setup):
    config, api, client = queue_setup
    config = replace(config, memory_root_page_ids=(ROOT,))
    pull(config, client)
    proposal(config, client)
    api.pages[ROOT]["in_trash"] = True
    assert pull(config, client)["exit_code"] == 2
    assert mirror_path(config, ROOT).exists() and mirror_path(config, CHILD).exists()


def test_cli_queue_and_sync_end_to_end(queue_setup, monkeypatch, capsys):
    from brainext.cli import config_text, main

    config, api, client = queue_setup
    path = config.vault / "config.toml"
    path.write_text(config_text(config.vault)
                    .replace('brain_root_page_id = ""', f'brain_root_page_id = "{ROOT}"')
                    .replace('agent_workspace_id = ""', f'agent_workspace_id = "{WORK}"'),
                    encoding="utf-8")
    monkeypatch.setenv("NOTION_TOKEN", "synthetic-only")
    monkeypatch.setattr("brainext.notion.client.NotionClient",
                        lambda config, token: NotionClient(config, token, httpx.MockTransport(api)))

    def run(*args):
        assert main([*args, "--config", str(path), "--json"]) == 0
        return json.loads(capsys.readouterr().out)

    staged = run("changes", "update", "--target", CHILD, "--old-text", "İçerik",
                 "--new-text", "CLI önerisi", "--reason", "Düzeltme")
    assert run("sync")["changes"]["counts"]["waiting"] == 1
    row, = run("changes", "list")["results"]
    assert row["id"] == staged["id"]
    run("changes", "approve", "--item", row["id"] + "=" + row["request_hash"])
    before = config.path(JOURNAL).read_bytes()
    assert run("changes", "apply", "--dry-run")["counts"]["planned"] == 1
    assert config.path(JOURNAL).read_bytes() == before
    assert run("sync", "--if-stale", "30m")["changes"]["counts"]["applied"] == 1
    assert run("search", "önerisi", "--mode", "text")["results"]


def test_local_queue_commands_do_not_require_a_token(queue_setup, monkeypatch, capsys):
    from brainext.cli import config_text, main

    config, api, client = queue_setup
    path = config.vault / "config.toml"
    path.write_text(config_text(config.vault), encoding="utf-8")
    monkeypatch.delenv("NOTION_TOKEN", raising=False)
    assert main(["changes", "list", "--config", str(path), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["results"] == []


@pytest.mark.parametrize("field", ["truncated", "unknown_block_ids"])
def test_incomplete_markdown_response_schema_cannot_authorize_writes(queue_setup, field):
    config, api, client = queue_setup
    del api.markdown[CHILD][field]
    assert proposal(config, client)["exit_code"] == 1
    assert not mutations(api)


def test_targeted_edit_must_not_change_a_structural_tag_attribute(queue_setup):
    config, api, client = queue_setup
    api.markdown[CHILD]["markdown"] = '<page url="https://app.notion.com/p/abc">Title</page>'
    assert proposal(config, client, old_str="https://app.notion.com/p/abc",
                    new_str="https://example.com")["exit_code"] == 1


def test_configured_root_inside_deleted_subtree_is_also_protected(queue_setup):
    config, api, client = queue_setup
    config = replace(config, memory_root_page_ids=(CHILD,), brain_root_page_id=WORK)
    assert proposal(config, client, "delete", ROOT)["exit_code"] == 1
    assert not mutations(api)


def test_remote_delete_does_not_acknowledge_a_pending_local_write(queue_setup):
    config, api, client = queue_setup
    config = replace(config, memory_root_page_ids=(ROOT,))
    pull(config, client)
    proposal(config, client)
    approve_all(config)
    api.patch_status, api.commit = 503, False
    assert changes().apply(config, client)["counts"]["uncertain"] == 1
    api.pages[CHILD]["in_trash"] = True
    api.children[ROOT] = []
    assert pull(config, client)["exit_code"] == 2
    assert mirror_path(config).exists()
    assert rows(config)[0]["status"] == "uncertain"


def test_failed_remote_trash_recovery_is_read_only(queue_setup):
    config, api, client = queue_setup
    proposal(config, client, "delete")
    approve_all(config)
    api.patch_status, api.commit = 503, False
    changes().apply(config, client)
    api.calls.clear()
    assert changes().apply(config, client)["counts"]["uncertain"] == 1
    assert not mutations(api)
    assert changes().cancel(config, [rows(config)[0]["id"]])["exit_code"] == 1


def test_human_queue_listing_shows_action_identity_and_review_hash(queue_setup, capsys):
    from brainext.cli import config_text, main

    config, api, client = queue_setup
    item = proposal(config, client)
    path = config.vault / "config.toml"
    path.write_text(config_text(config.vault), encoding="utf-8")
    assert main(["changes", "list", "--config", str(path)]) == 0
    output = capsys.readouterr().out
    assert item["id"] in output and item["request_hash"] in output
    assert "update" in output and "queued" in output and "-İçerik" in output


def test_delete_review_names_affected_descendants(queue_setup):
    config, api, client = queue_setup
    config = replace(config, brain_root_page_id=OUTSIDE)
    proposal(config, client, "delete", ROOT)
    row, = rows(config)
    assert {p["id"] for p in row["affected_pages"]} == {ROOT, CHILD}
    assert all(p["title"] for p in row["affected_pages"])


def test_create_readback_uses_returned_id_despite_unrelated_partial_sibling(queue_setup):
    config, api, client = queue_setup
    api.children[OUTSIDE] = [child(CHILD, OUTSIDE)]
    api.pages[CHILD]["parent"]["page_id"] = OUTSIDE
    api.markdown[CHILD]["truncated"] = True
    proposal(config, client, "create", OUTSIDE, title="New note", body="New body")
    assert changes().apply(config, client)["counts"]["applied"] == 1
    assert rows(config)[0]["notion_id"] == CREATED


@pytest.mark.parametrize("private", [False, True])
def test_cli_create_body_file_respects_privacy(queue_setup, monkeypatch, capsys, private):
    from brainext.cli import config_text, main

    config, api, client = queue_setup
    path = config.vault / "config.toml"
    path.write_text(config_text(config.vault), encoding="utf-8")
    write_note(config.path("agent-out/body.md"),
               {"visibility": "private"} if private else {}, "Body without frontmatter\n")
    monkeypatch.setenv("NOTION_TOKEN", "synthetic")
    monkeypatch.setattr("brainext.notion.client.NotionClient",
                        lambda config, token: NotionClient(config, token, httpx.MockTransport(api)))
    code = main(["changes", "create", "--target", OUTSIDE, "--title", "New note",
                 "--body-file", "agent-out/body.md", "--config", str(path), "--json"])
    capsys.readouterr()
    assert code == (1 if private else 0)
    assert not mutations(api)
    if private:
        assert not rows(config)
    else:
        assert changes().apply(config, client)["counts"]["applied"] == 1
        assert api.markdown[CREATED]["markdown"].startswith("Body without frontmatter\n")
