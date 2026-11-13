import json
import subprocess
import sys


def sync(vault, state):
    subprocess.run([sys.executable, "-B", str(vault / ".claude/scripts/beyin_v3_cli.py"),
                    "--vault", str(vault), "--state", str(state), "--json", "sync"],
                   check=True, capture_output=True, timeout=60)


def note(vault, path, text, **metadata):
    target = vault / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('---\n' + json.dumps(metadata) + '\n---\n' + text, encoding="utf-8")
    return target


def test_general_context_contains_only_identity_and_general_rules(memory_fixture):
    from brainext.shared_memory.runtime import VaultRuntime

    vault, state = memory_fixture
    note(vault, "notes/person.md", "PERSON_LEGACY", kind="person")
    note(vault, "knowledge/index.md", "KNOWLEDGE_LEGACY")
    sync(vault, state)
    result = VaultRuntime(vault).general_context(4000)
    text = str(result)
    assert "GENERAL_ONLY" in text and "General preference" in text
    for marker in ("A_ONLY", "B_ONLY", "LEGACY_ONLY", "PERSON_LEGACY", "KNOWLEDGE_LEGACY"):
        assert marker not in text


def test_a_context_excludes_b_and_unassigned_before_ranking(memory_fixture):
    from brainext.shared_memory.runtime import VaultRuntime

    vault, state = memory_fixture
    note(vault, "projects/alpha/design.md", "routing A_ONLY decision")
    for index in range(15):
        note(vault, f"notes/b-{index}.md", "routing " * 100 + "B_ONLY", project="beta")
    note(vault, "notes/unassigned.md", "routing LEGACY_ONLY")
    note(vault, "projects/alpha/conflicting.md", "routing WRONG_PROJECT", project="beta")
    sync(vault, state)
    result = VaultRuntime(vault).project_context("alpha", "routing", 4000)
    assert "A_ONLY" in str(result)
    assert all(value not in str(result) for value in ("B_ONLY", "LEGACY_ONLY", "WRONG_PROJECT"))


def test_private_untrusted_rejected_and_missing_sources_remain_excluded(memory_fixture):
    from brainext.shared_memory.runtime import VaultRuntime

    vault, state = memory_fixture
    note(vault, "projects/alpha/private.md", "routing PRIVATE_ONLY", visibility="private")
    note(vault, "projects/alpha/untrusted.md", "routing UNTRUSTED_ONLY", kind="untrusted")
    note(vault, "projects/alpha/rejected.md", "routing REJECTED_ONLY", kind="inference",
         validity="rejected", rejected_reason="user correction", rejected_at="2026-11-13")
    stale = note(vault, "projects/alpha/stale.md", "routing STALE_ONLY")
    gone = note(vault, "projects/alpha/gone.md", "routing GONE_ONLY")
    sync(vault, state)
    stale.write_text("changed", encoding="utf-8")
    gone.unlink()
    result = VaultRuntime(vault).project_context("alpha", "routing", 6000)
    for value in ("PRIVATE_ONLY", "UNTRUSTED_ONLY", "REJECTED_ONLY", "STALE_ONLY", "GONE_ONLY"):
        assert value not in str(result)


def test_project_catalog_is_small_and_has_no_machine_paths(memory_fixture):
    from brainext.shared_memory.runtime import VaultRuntime

    result = VaultRuntime(memory_fixture[0]).project_catalog()
    assert {entry["id"] for entry in result} == {"alpha", "beta"}
    assert all(set(entry) == {"id", "title", "purpose"} for entry in result)


def test_scoped_identity_is_not_a_general_preference(memory_fixture):
    from brainext.shared_memory.runtime import VaultRuntime

    vault, state = memory_fixture
    note(vault, "Test-Companion/Core.md", "IDENTITY_FOR_A", project="alpha")
    sync(vault, state)
    assert "IDENTITY_FOR_A" not in str(VaultRuntime(vault).general_context(4000))


def test_ambiguous_identity_fails_closed(memory_fixture):
    import pytest

    from brainext.shared_memory.runtime import RuntimeUnavailable, VaultRuntime

    vault, state = memory_fixture
    note(vault, "Other-Companion/Core.md", "OTHER_IDENTITY")
    sync(vault, state)
    with pytest.raises(RuntimeUnavailable):
        VaultRuntime(vault).general_context(4000)


def test_registered_vault_folder_scope_is_not_general(memory_fixture):
    from brainext.shared_memory.runtime import VaultRuntime

    vault, state = memory_fixture
    (vault / ".beyin-projects.json").write_text(json.dumps({
        "folders": {"Test-Companion": "beta"}, "shared_unscoped": False}), encoding="utf-8")
    sync(vault, state)
    assert "GENERAL_ONLY" not in str(VaultRuntime(vault).general_context(4000))


def test_registered_folder_and_metadata_conflict_is_excluded(memory_fixture):
    from brainext.shared_memory.runtime import VaultRuntime

    vault, state = memory_fixture
    note(vault, "notes/other/decision.md", "routing WRONG_FOLDER", project="alpha")
    (vault / ".beyin-projects.json").write_text(json.dumps({
        "folders": {"notes/other": "beta"}, "shared_unscoped": False}), encoding="utf-8")
    sync(vault, state)
    assert "WRONG_FOLDER" not in str(VaultRuntime(vault).project_context("alpha", "routing", 4000))
