"""Local, vault-bound directory mappings with compare-and-write revisions."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from brainext.mdio import operation_lock, safe_path, write_json


class RegistryError(ValueError):
    """Invalid, unavailable or concurrently modified registry."""


def project_id(value: str) -> str:
    if (not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", value)
            or re.fullmatch(r"con|prn|aux|nul|com[1-9]|lpt[1-9]", value)):
        raise RegistryError("invalid_project_id")
    return value


def canonical_directory(path: str | Path) -> Path:
    value = Path(path)
    if not value.is_absolute() or any(
            part.endswith((".", " ")) or ":" in part or re.fullmatch(
                r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", part)
            for part in value.parts[1:]):
        raise RegistryError("invalid_directory")
    value = value.resolve(strict=True)
    if not value.is_dir():
        raise RegistryError("invalid_directory")
    return value


def candidate_root(directory: Path) -> tuple[Path, str]:
    directory = canonical_directory(directory)
    env = {k: v for k, v in os.environ.items()
           if k not in {"GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"}}
    env["LC_ALL"] = "C"
    try:
        result = subprocess.run(
            ["git", "-C", str(directory), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, encoding="utf-8", timeout=5, env=env)
        if result.returncode == 0:
            return canonical_directory(result.stdout.strip()), "git"
        if "not a git repository (or any of the parent directories)" in result.stderr:
            return directory, "folder"
    except (OSError, subprocess.TimeoutExpired):
        pass
    raise RegistryError("git_root_unavailable")


class Registry:
    def __init__(self, path: Path, vault: Path):
        self.path = path.absolute()
        self.vault = canonical_directory(vault)

    def read(self) -> dict:
        try:
            safe_path(self.path.parent, self.path.name)
            if not self.path.exists():
                return {"version": 1, "vault": str(self.vault), "revision": 0,
                        "roots": [], "ignored": []}
            if self.path.stat().st_size > 1024 * 1024:
                raise RegistryError("registry_too_large")
            data = json.loads(self.path.read_text("utf-8"))
            if (not isinstance(data, dict) or set(data) != {
                    "version", "vault", "revision", "roots", "ignored"}
                    or data["version"] != 1 or Path(data["vault"]) != self.vault
                    or type(data["revision"]) is not int or data["revision"] < 0
                    or not isinstance(data["roots"], list)
                    or not isinstance(data["ignored"], list)):
                raise RegistryError("registry_schema_or_vault")
            for entry in data["roots"]:
                if set(entry) != {"root", "project"}:
                    raise RegistryError("registry_entry")
                project_id(entry["project"])
            for root in [e["root"] for e in data["roots"]] + data["ignored"]:
                if not isinstance(root, str) or not Path(root).is_absolute():
                    raise RegistryError("registry_root")
                # Keep moved/missing roots as stale mappings, not new shared information.
                if Path(root).exists() and canonical_directory(root) != Path(root):
                    raise RegistryError("registry_redirected_root")
            return data
        except (OSError, TypeError, KeyError, ValueError) as exc:
            raise RegistryError("registry_unavailable") from exc

    def resolve(self, directory: Path) -> dict:
        data = self.read()
        root, kind = candidate_root(directory)
        matches = [entry for entry in data["roots"] if (
            root == Path(entry["root"]) if kind == "git"
            else root.is_relative_to(Path(entry["root"]))) ]
        ignored = [Path(value) for value in data["ignored"] if (
            root == Path(value) if kind == "git" else root.is_relative_to(Path(value)))]
        status, project = "unknown", None
        if len(matches) > 1 or (matches and ignored):
            status = "conflict"
        elif matches:
            status, project = "mapped", matches[0]["project"]
            root = Path(matches[0]["root"])
        elif ignored:
            status = "ignored"
        return {"status": status, "root": str(root), "kind": kind, "project": project,
                "revision": data["revision"]}

    def bind(self, root: Path, project: str, expected_revision: int) -> dict:
        return self._write(root, project_id(project), expected_revision)

    def ignore(self, root: Path, expected_revision: int) -> dict:
        return self._write(root, None, expected_revision)

    def _write(self, root, project, expected_revision):
        root = str(canonical_directory(root))
        if type(expected_revision) is not int:
            raise RegistryError("invalid_revision")
        try:
            safe_path(self.path.parent, self.path.name)
            with operation_lock(self.path.parent):
                data = self.read()
                existing = [e for e in data["roots"] if Path(e["root"]) == Path(root)]
                if (project and existing == [{"root": root, "project": project}]
                        and root not in data["ignored"]):
                    return {"status": "ok", "revision": data["revision"]}
                if data["revision"] != expected_revision or existing or root in data["ignored"]:
                    return {"status": "conflict", "revision": data["revision"]}
                if project:
                    data["roots"].append({"root": root, "project": project})
                else:
                    data["ignored"].append(root)
                data["revision"] += 1
                write_json(self.path, data)
                return {"status": "ok", "revision": data["revision"]}
        except (OSError, ValueError) as exc:
            raise RegistryError("registry_write_conflict") from exc
