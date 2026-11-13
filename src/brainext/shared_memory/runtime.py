"""Narrow compatibility layer over the user's installed Beyin runtime."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

from brainext.mdio import safe_path
from brainext.shared_memory.registry import project_id


class RuntimeUnavailable(ValueError):
    """The installed source-backed runtime cannot safely serve this request."""


def validate_contract(engine):
    store = getattr(engine, "MemoryStore", None)
    if not store or not all(callable(getattr(store, name, None)) for name in (
            "source_snapshot", "_eligible", "retrieve", "_source")):
        raise RuntimeUnavailable("runtime_contract")


class VaultRuntime:
    def __init__(self, vault: Path):
        self.vault = vault.resolve(strict=True)
        self.scripts = safe_path(self.vault, ".claude/scripts")
        if safe_path(self.vault, ".beyin-version").read_text().strip() != "3.12.0":
            raise RuntimeUnavailable("runtime_version")
        pin = json.loads(safe_path(self.vault, ".beyin-runtime.json").read_text("utf-8"))
        self.state = Path(pin["state"])
        if not self.state.is_absolute() or self.state.resolve().is_relative_to(self.vault):
            raise RuntimeUnavailable("runtime_pin")
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(self.scripts))
        self.engine = self._load("beyin_v3")
        self.companion = self._load("beyin_v3_companion")
        validate_contract(self.engine)
        safe_path(self.vault, ".beyin-projects.json")
        self.scopes = self.engine.read_project_scopes(self.vault)
        self.store = self.engine.MemoryStore(self.state, self.vault, read_only=True)

    def _load(self, name):
        spec = importlib.util.spec_from_file_location(
            "brainext_installed_" + name, safe_path(self.vault, f".claude/scripts/{name}.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def general_context(self, budget: int) -> dict:
        target = self.companion.directory(self.vault)
        if target is None or not target.is_dir():
            raise RuntimeUnavailable("companion_ambiguous")
        relative = target.relative_to(self.vault).as_posix()
        safe_path(self.vault, relative)
        records, stale = self.store._eligible()
        wanted = [f"{relative}/{name}" for name in ("Core.md", "Soul.md", "Kurallar.md")]
        selected = []
        for source in wanted:
            for record in records:
                if record["source"] == source and not self.record_scopes(record):
                    record = dict(record)
                    if source.endswith("/Kurallar.md"):
                        record["text"] = self.companion.filter_scoped_rules(
                            record["text"], active_project="__general__")
                    selected.append(record)
        return self.engine.pack_context(selected, limit=3, budget_chars=budget, stale_count=stale)

    def record_scopes(self, record: dict) -> set[str]:
        source = Path(record.get("source", ""))
        declared = record.get("project") or None
        folder = source.parts[1] if len(source.parts) > 2 and source.parts[0] == "projects" else None
        mapped = self.engine.record_scope({"source": source.as_posix()}, self.scopes
                                          ) if self.scopes else None
        return {project_id(value) for value in (declared, folder, mapped) if value}

    def record_project(self, record: dict) -> str | None:
        scopes = self.record_scopes(record)
        if record.get("generated") or record.get("kind") == "receipt":
            return None
        return next(iter(scopes)) if len(scopes) == 1 else None

    def project_catalog(self) -> list[dict]:
        records, _ = self.store._eligible()
        result = []
        for record in records:
            parts = Path(record["source"]).parts
            if len(parts) != 3 or parts[0] != "projects" or parts[2] != "Project.md":
                continue
            id = self.record_project(record)
            if id and record.get("id") == id and record.get("project") == id:
                result.append({"id": id, "title": str(record.get("title", id))[:160],
                               "purpose": str(record.get("purpose", record["text"]))[:500]})
        return sorted(result, key=lambda item: item["id"])

    def project_context(self, project: str, query: str, budget: int) -> dict:
        project_id(project)
        outer = self

        class ScopedStore(self.engine.MemoryStore):
            def _eligible(self, audience="internal", project=None, rejected_only=False, records=None):
                eligible, stale = super()._eligible(audience, None, rejected_only, records)
                return [r for r in eligible if outer.record_project(r) == project], stale

        scoped = ScopedStore(self.state, self.vault, read_only=True)
        # Direct note-level retrieval keeps the scope gate ahead of ranking and packing.
        if query.strip():
            return scoped.retrieve(query, project=project, budget_chars=budget, strict=True, limit=8)
        return scoped.snapshot_context(project=project, budget_chars=budget, limit=8)

    def continuity_context(self, project: str, budget: int) -> dict:
        project_id(project)
        records, stale = self.store._eligible()
        sources = [f"projects/{project}/{name}" for name in (
            "Project.md", "Kurallar.md", "Last-Session.md", "Threads.md")]
        selected = [record for source in sources for record in records
                    if record["source"] == source and self.record_project(record) == project]
        return self.engine.pack_context(selected, limit=4, budget_chars=budget, stale_count=stale)

    def source_record(self, source: str) -> dict | None:
        safe_path(self.vault, source)
        records, _ = self.store._eligible()
        return next((r for r in records if r["source"] == source), None)

    def beyin(self, command: str, payload: dict | None = None) -> dict:
        if command not in {"sync", "note-create", "note-read", "note-edit", "task-create",
                           "task-update", "receipt"}:
            raise RuntimeUnavailable("runtime_command")
        args = [sys.executable, "-B", str(self.scripts / "beyin_v3_cli.py"),
                "--vault", str(self.vault), "--state", str(self.state), "--json", command]
        if command == "receipt":
            args += ["--harness", "opencode"]
        if command == "note-read":
            args.append(payload["source"])
        elif command != "sync":
            args += ["--file", "-"]
        result = subprocess.run(args, input=json.dumps(payload or {}, ensure_ascii=False),
                                capture_output=True, text=True, encoding="utf-8", timeout=30,
                                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
                                     "PYTHONIOENCODING": "utf-8"})
        try:
            data = json.loads(result.stdout)
        except ValueError:
            raise RuntimeUnavailable("runtime_output") from None
        if result.returncode and data.get("status") != "conflict":
            raise RuntimeUnavailable("runtime_command_failed")
        return data
