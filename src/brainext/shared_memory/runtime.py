"""Narrow compatibility layer over the user's installed Beyin runtime."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from brainext.mdio import safe_path


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
        return self.store.source_snapshot(
            ["Core.md", "Soul.md", "Kurallar.md"], source_directory=relative,
            budget_chars=budget, text_transform=lambda name, text:
            self.companion.filter_scoped_rules(text, active_project="__general__")
            if name == "Kurallar.md" else text)
