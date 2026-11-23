from types import SimpleNamespace

import pytest


def test_incompatible_runtime_is_rejected_without_fallback():
    from brainext.shared_memory.runtime import RuntimeUnavailable, validate_contract

    with pytest.raises(RuntimeUnavailable):
        validate_contract(SimpleNamespace())


def test_installed_runtime_can_read_synthetic_vault(memory_fixture):
    from brainext.shared_memory.runtime import VaultRuntime

    vault, _ = memory_fixture
    runtime = VaultRuntime(vault)
    result = runtime.general_context(4000)
    assert "GENERAL_ONLY" in str(result)
    assert "LEGACY_ONLY" not in str(result)


@pytest.mark.parametrize("version", ["3.14.0", "3.14.99", "4.0.0"])
def test_unverified_runtime_versions_still_fail_closed(memory_fixture, version):
    from brainext.shared_memory.runtime import RuntimeUnavailable, VaultRuntime

    vault, _ = memory_fixture
    (vault / ".beyin-version").write_text(version, encoding="utf-8")
    with pytest.raises(RuntimeUnavailable, match="runtime_version"):
        VaultRuntime(vault)
