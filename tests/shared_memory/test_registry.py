import json
import subprocess
from concurrent.futures import ThreadPoolExecutor

import pytest


def registry(tmp_path):
    from brainext.shared_memory.registry import Registry

    vault = tmp_path / "vault"
    vault.mkdir(exist_ok=True)
    return Registry(tmp_path / "local/registry.json", vault)


def git(root):
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
    return root


def test_repo_and_frontend_share_mapping(tmp_path):
    r = registry(tmp_path)
    root = git(tmp_path / "app")
    frontend = root / "frontend"
    frontend.mkdir()
    assert r.bind(root, "alpha", 0)["status"] == "ok"
    assert r.resolve(frontend)["project"] == "alpha"
    assert r.resolve(root)["project"] == "alpha"


def test_non_git_descendant_uses_confirmed_root(tmp_path):
    r = registry(tmp_path)
    root = tmp_path / "Notes Çalışma"
    child = root / "deep"
    child.mkdir(parents=True)
    r.bind(root, "alpha", 0)
    assert r.resolve(child)["project"] == "alpha"


def test_sibling_prefix_is_not_child(tmp_path):
    r = registry(tmp_path)
    root, sibling = tmp_path / "app", tmp_path / "app-two"
    root.mkdir()
    sibling.mkdir()
    r.bind(root, "alpha", 0)
    assert r.resolve(sibling)["status"] == "unknown"


def test_nested_repo_is_independent(tmp_path):
    r = registry(tmp_path)
    root = git(tmp_path / "parent")
    child = git(root / "nested")
    r.bind(root, "alpha", 0)
    assert r.resolve(child)["status"] == "unknown"


def test_clone_and_worktree_need_binding(tmp_path):
    r = registry(tmp_path)
    root = git(tmp_path / "one")
    other = git(tmp_path / "two")
    r.bind(root, "alpha", 0)
    assert r.resolve(other)["status"] == "unknown"


def test_corrupt_or_foreign_vault_registry_is_not_replaced(tmp_path):
    from brainext.shared_memory.registry import Registry, RegistryError

    r = registry(tmp_path)
    r.path.parent.mkdir()
    r.path.write_text('{"version":999}', encoding="utf-8")
    before = r.path.read_bytes()
    with pytest.raises(RegistryError):
        r.read()
    assert r.path.read_bytes() == before
    root = tmp_path / "project"
    root.mkdir()
    r.path.unlink()
    r.bind(root, "alpha", 0)
    other = tmp_path / "other-vault"
    other.mkdir()
    with pytest.raises(RegistryError):
        Registry(r.path, other).read()


def test_two_writers_cannot_rebind_same_revision(tmp_path):
    r = registry(tmp_path)
    root = tmp_path / "project"
    root.mkdir()

    def write(project):
        from brainext.shared_memory.registry import RegistryError
        try:
            return r.bind(root, project, 0)["status"]
        except RegistryError:
            return "conflict"

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(write, ["alpha", "beta"]))
    assert sorted(results) == ["conflict", "ok"]
    assert r.read()["revision"] == 1


def test_ambiguous_roots_do_not_choose_project(tmp_path):
    r = registry(tmp_path)
    root = tmp_path / "parent"
    child = root / "child"
    child.mkdir(parents=True)
    r.bind(root, "alpha", 0)
    r.bind(child, "beta", 1)
    assert r.resolve(child)["status"] == "conflict"


def test_ignore_keeps_unknown_root_unmapped(tmp_path):
    r = registry(tmp_path)
    root = tmp_path / "project"
    root.mkdir()
    r.ignore(root, 0)
    assert r.resolve(root)["status"] == "ignored"
    assert not r.read()["roots"]


@pytest.mark.parametrize("project", ["../alpha", "A", "a/b", "con", "a:stream", ""])
def test_invalid_project_id_never_writes(tmp_path, project):
    from brainext.shared_memory.registry import RegistryError

    r = registry(tmp_path)
    with pytest.raises(RegistryError):
        r.bind(tmp_path, project, 0)
    assert not r.path.exists()


def test_redirected_registry_is_rejected(tmp_path):
    from brainext.shared_memory.registry import RegistryError

    r = registry(tmp_path)
    r.path.parent.mkdir()
    target = tmp_path / "target.json"
    target.write_text("{}")
    try:
        r.path.symlink_to(target)
    except OSError:
        pytest.skip("Windows symlink privilege unavailable")
    with pytest.raises(RegistryError):
        r.read()
    assert json.loads(target.read_text()) == {}
