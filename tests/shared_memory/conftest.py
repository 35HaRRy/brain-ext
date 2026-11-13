"""Synthetic vaults; only the installed runtime's code is reused, never user notes."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def memory_fixture(tmp_path):
    installed = Path(os.environ.get(
        "BEYIN_TEST_VAULT", str(Path(__file__).resolve().parents[3] / "agent-memory-vault")))
    scripts = installed / ".claude/scripts"
    if not (scripts / "beyin_v3.py").is_file():
        pytest.skip("Installed Beyin code unavailable; set BEYIN_TEST_VAULT")
    vault = tmp_path / "vault"
    shutil.copytree(scripts, vault / ".claude/scripts", ignore=shutil.ignore_patterns(
        "__pycache__", "*.pyc"))
    shutil.copyfile(installed / ".beyin-version", vault / ".beyin-version")
    state = tmp_path / "state"
    (vault / ".beyin-runtime.json").write_text(
        json.dumps({"state": str(state)}), encoding="utf-8")
    companion = vault / "Test-Companion"
    companion.mkdir()
    (companion / "Core.md").write_text("# User\nGENERAL_ONLY", encoding="utf-8")
    (companion / "Kurallar.md").write_text(
        "# Rules\n- General preference.\n- [kapsam: alpha] A_ONLY\n"
        "- [kapsam: beta] B_ONLY\n", encoding="utf-8")
    for name in ("Last-Session.md", "Threads.md", "Journal.md"):
        (companion / name).write_text("LEGACY_ONLY", encoding="utf-8")
    for project, marker in (("alpha", "A_ONLY"), ("beta", "B_ONLY")):
        folder = vault / "projects" / project
        folder.mkdir(parents=True)
        (folder / "Project.md").write_text(
            '---\n' + json.dumps({"kind": "fact", "project": project,
                                  "title": project, "id": project})
            + '\n---\nPurpose: ' + marker, encoding="utf-8")
        (folder / "Last-Session.md").write_text(marker, encoding="utf-8")
    subprocess.run([sys.executable, "-B", str(vault / ".claude/scripts/beyin_v3_cli.py"),
                    "--vault", str(vault), "--state", str(state), "--json", "sync"],
                   capture_output=True, check=True, timeout=60)
    return vault, state
