import json
import subprocess
import sys

import pytest


@pytest.fixture
def service(memory_fixture, tmp_path):
    from brainext.shared_memory.service import MemoryService

    return MemoryService(memory_fixture[0], tmp_path / "local/registry.json")


def request(directory, action="context", **payload):
    return {"version": 1, "action": action,
            "session": {"id": "session-one", "directory": str(directory), "parent_id": None},
            "payload": payload}


def bind(service, directory, project="alpha", revision=0):
    return service.handle(request(directory, "bind", root=str(directory), id=project,
                                  expected_revision=revision, confirmed=True))


def test_unknown_context_does_not_create_files(service, tmp_path):
    root = tmp_path / "code"
    root.mkdir()
    result = service.handle(request(root))
    assert result["status"] == "ok" and result["mode"] == "general"
    assert result["result"]["mapping"]["status"] == "unknown"
    assert "GENERAL_ONLY" in result["context"]
    assert "A_ONLY" not in result["context"]
    assert not service.registry.path.exists()
    assert list(root.iterdir()) == []


def test_register_requires_confirmed_root_and_identity(service, tmp_path):
    root = tmp_path / "code"
    root.mkdir()
    data = dict(id="gamma", title="Gamma", purpose="My app", root=str(root), expected_revision=0)
    assert service.handle(request(root, "register", **data))["status"] == "invalid"
    assert not (service.vault / "projects/gamma/Project.md").exists()
    result = service.handle(request(root, "register", **data, confirmed=True))
    assert result["status"] == "ok", result
    assert result["project"] == "gamma"
    source = service.vault / "projects/gamma/Project.md"
    assert source.exists() and str(root) not in source.read_text("utf-8")


def test_root_must_contain_session_directory(service, tmp_path):
    root, other = tmp_path / "code", tmp_path / "other"
    root.mkdir()
    other.mkdir()
    result = service.handle(request(root, "bind", root=str(other), id="alpha",
                                    expected_revision=0, confirmed=True))
    assert result["status"] == "invalid"


def test_bind_uses_existing_project(service, tmp_path):
    root = tmp_path / "code"
    root.mkdir()
    assert bind(service, root, "missing")["status"] == "invalid"
    assert bind(service, root)["status"] == "ok"
    result = service.handle(request(root))
    assert result["project"] == "alpha"
    assert "B_ONLY" not in result["context"]


def test_ignore_keeps_general_preferences(service, tmp_path):
    root = tmp_path / "code"
    root.mkdir()
    result = service.handle(request(root, "ignore", root=str(root),
                                    expected_revision=0, confirmed=True))
    assert result["status"] == "ok"
    result = service.handle(request(root))
    assert result["result"]["mapping"]["status"] == "ignored"
    assert "GENERAL_ONLY" in result["context"]


def test_register_retry_finishes_same_project_after_registry_failure(service, tmp_path, monkeypatch):
    root = tmp_path / "code"
    root.mkdir()
    data = request(root, "register", root=str(root), id="gamma", title="Gamma",
                   purpose="My app", expected_revision=0, confirmed=True)
    original = service.registry.bind
    from brainext.shared_memory.registry import RegistryError
    monkeypatch.setattr(service.registry, "bind", lambda *a: (_ for _ in ()).throw(RegistryError()))
    assert service.handle(data)["status"] != "ok"
    assert (service.vault / "projects/gamma/Project.md").exists()
    monkeypatch.setattr(service.registry, "bind", original)
    assert service.handle(data)["status"] == "ok"
    assert len(list((service.vault / "projects").glob("gamma*/Project.md"))) == 1


def test_general_or_unavailable_session_cannot_write_project(service, tmp_path):
    root = tmp_path / "code"
    root.mkdir()
    result = service.handle(request(root, "note-create", source="projects/alpha/new.md",
                                    text="must not write", metadata={"kind": "fact"}))
    assert result["status"] == "invalid"
    assert not (service.vault / "projects/alpha/new.md").exists()


def test_task_create_update_require_confirmation_and_project(service, tmp_path):
    root = tmp_path / "code"
    root.mkdir()
    bind(service, root)
    payload = {"source": "tasks/new.md", "text": "Write a test", "metadata": {
        "id": "task-one", "kind": "task", "title": "Test", "status": "inbox",
        "owner": "user", "project": "alpha"}}
    assert service.handle(request(root, "task-create", **payload))["status"] == "invalid"
    result = service.handle(request(root, "task-create", **payload, confirmed=True))
    assert result["status"] == "ok", result
    update = dict(id="task-one", expected_revision=1, changes={"status": "active"})
    assert service.handle(request(root, "task-update", **update))["status"] == "invalid"
    assert service.handle(request(root, "task-update", **update, confirmed=True))["status"] == "ok"
    assert service.handle(request(root, "task-update", **update, confirmed=True))["status"] == "conflict"
    other = tmp_path / "beta-code"
    other.mkdir()
    bind(service, other, "beta", 1)
    update["expected_revision"] = 2
    assert service.handle(request(other, "task-update", **update, confirmed=True))["status"] == "invalid"


def test_note_edit_keeps_hash_conflict(service, tmp_path):
    root = tmp_path / "code"
    root.mkdir()
    bind(service, root)
    source = "projects/alpha/Last-Session.md"
    result = service.handle(request(root, "note-read", source=source))
    assert result["status"] == "ok", result
    result = service.handle(request(root, "note-edit", source=source,
                                    expected_sha256="0" * 64, edits=[{"old": "A_ONLY", "new": "x"}]))
    assert result["status"] == "conflict"
    assert "A_ONLY" in (service.vault / source).read_text("utf-8")


def test_receipt_rejects_other_project_refs(service, tmp_path):
    root = tmp_path / "code"
    root.mkdir()
    bind(service, root)
    result = service.handle(request(root, "receipt", event_id="result-1", summary="done",
                                    refs=["projects/beta/Project.md"]))
    assert result["status"] == "invalid"


def test_receipt_uses_opencode_harness_and_real_session(service, tmp_path):
    root = tmp_path / "code"
    root.mkdir()
    bind(service, root)
    result = service.handle(request(root, "receipt", event_id="alpha-result-1",
                                    summary="Reviewed alpha.\nÖğrenilen: yok (rutin kontrol)",
                                    refs=["projects/alpha/Project.md"]))
    assert result["status"] == "ok", result
    from brainext.mdio import read_note
    meta, _ = read_note(service.vault / result["result"]["source"])
    assert meta["harness"] == "opencode"
    assert meta["session"] == "session-one"


def test_note_edit_cannot_move_note_to_another_project(service, tmp_path):
    root = tmp_path / "code"
    root.mkdir()
    bind(service, root)
    source = "projects/alpha/Project.md"
    before = service.handle(request(root, "note-read", source=source))["result"]
    result = service.handle(request(root, "note-edit", source=source,
                                    expected_sha256=before["sha256"], edits=[{
                                        "old": '"project": "alpha"',
                                        "new": '"project": "beta"'}]))
    assert result["status"] == "invalid"


def test_general_rules_read_does_not_expose_other_project_rules(service, tmp_path):
    root = tmp_path / "code"
    root.mkdir()
    result = service.handle(request(root, "note-read", source="Test-Companion/Kurallar.md"))
    assert result["status"] == "ok"
    assert "General preference" in result["result"]["content"]
    assert "A_ONLY" not in result["result"]["content"]
    assert "B_ONLY" not in result["result"]["content"]


def test_context_refresh_reads_manual_preference_edits(service, tmp_path):
    root = tmp_path / "code"
    root.mkdir()
    core = service.vault / "Test-Companion/Core.md"
    core.write_text("NEW_PREFERENCE", encoding="utf-8")
    result = service.handle(request(root, refresh=True))
    assert "NEW_PREFERENCE" in result["context"]


def test_cross_project_search_needs_explicit_scope_and_does_not_rebind(service, tmp_path):
    root = tmp_path / "code"
    root.mkdir()
    bind(service, root)
    result = service.handle(request(root, "search", project="beta", query="beta"))
    assert result["status"] == "invalid"
    result = service.handle(request(root, "search", project="beta", query="beta",
                                    cross_project_confirmed=True))
    assert result["status"] == "ok"
    assert service.handle(request(root))["project"] == "alpha"


def test_cli_invalid_version_oversize_and_runtime_failure_return_safe_json(tmp_path):
    for raw in ('{"version":999,"secret":"DO_NOT_LOG"}', 'x' * (1024 * 1024 + 1)):
        result = subprocess.run([sys.executable, "-m", "brainext.shared_memory",
                                 "--vault", str(tmp_path), "--registry", str(tmp_path / "map.json")],
                                input=raw, capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout)
        assert data["status"] in {"invalid", "unavailable"}
        assert data["mode"] == "disabled"
        assert "DO_NOT_LOG" not in result.stdout + result.stderr
        assert not result.stderr
