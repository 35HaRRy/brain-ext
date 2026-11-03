"""Doğrulanan, sır içermeyen yapılandırma."""

from __future__ import annotations

import math
import os
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path, PureWindowsPath

from brainext.mdio import safe_path


@dataclass(frozen=True)
class Config:
    vault: Path
    mirror_dir: str = "notion"
    outbox_dir: str = "agent-out"
    state_dir: str = ".brain-ext"
    companion_dir: str = "🔮 850-Companion"
    api_version: str = "2026-03-11"
    markdown_version: str = "v2"
    mirror_trust: str = "untrusted"
    brain_root_page_id: str = ""
    agent_workspace_id: str = ""
    requests_per_second: float = 2.5
    token_env_var: str = "NOTION_TOKEN"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    model_path: str = ""
    rrf_k: int = 60
    prefix_min_length: int = 4

    def __post_init__(self) -> None:
        if not isinstance(self.vault, Path) or not self.vault.is_absolute():
            raise ValueError("Vault yolu mutlak olmalı")
        for field in fields(self):
            value = getattr(self, field.name)
            if isinstance(field.default, str) and not isinstance(value, str):
                raise ValueError("Metin yapılandırma değeri geçersiz")
        if type(self.rrf_k) is not int or type(self.prefix_min_length) is not int:
            raise ValueError("Arama sınırları tamsayı olmalı")
        if type(self.requests_per_second) not in {int, float}:
            raise ValueError("İstek hızı sayı olmalı")
        regions = [self.mirror_dir, self.outbox_dir, self.state_dir]
        for name in [*regions, self.companion_dir]:
            windows = PureWindowsPath(name)
            if (not name or len(windows.parts) != 1 or windows.drive
                    or name in {".", ".."} or name.endswith((".", " "))
                    or any(c in '<>:"/\\|?*' or ord(c) < 32 for c in name)
                    or name.split(".", 1)[0].upper() in {
                        "CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$",
                        *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10)),
                    }):
                raise ValueError("Bölge adı tek klasör olmalı")
            safe_path(self.vault, name)
        if len({name.casefold() for name in regions}) != 3:
            raise ValueError("Bölgeler ayrı olmalı")
        reserved = {
            "notes", "knowledge", "tasks", self.companion_dir.casefold(),
            ".claude", ".agents", ".opencode", ".brain", ".beyin-note-write", ".git", "daily", "receipts",
        }
        if any(x.casefold() in reserved for x in regions):
            raise ValueError("Kaynak not klasörleri sahiplenilemez")
        if self.mirror_dir.startswith(".") or self.outbox_dir.startswith("."):
            raise ValueError("Ayna ve taslak klasörleri gizli olamaz")
        if self.markdown_version != "v2" or self.mirror_trust not in {"untrusted", "note"}:
            raise ValueError("Markdown sürümü veya mirror_trust geçersiz")
        if not math.isfinite(self.requests_per_second) or not 0 < self.requests_per_second <= 10:
            raise ValueError("İstek hızı 0 ile 10 arasında olmalı")
        if isinstance(self.rrf_k, bool) or self.rrf_k < 1 or self.prefix_min_length < 1:
            raise ValueError("Arama sınırları pozitif olmalı")

    def path(self, relative: str) -> Path:
        return safe_path(self.vault, relative)

    @property
    def state(self) -> Path:
        return self.path(self.state_dir)

    @classmethod
    def load(cls, path: Path) -> Config:
        if not path.exists():
            raise ValueError("Config bulunamadı; brainext init kullanın")
        with path.open("rb") as stream:
            data = tomllib.load(stream)
        if set(data) - {"vault", "notion", "index"}:
            raise ValueError("Bilinmeyen yapılandırma bölümü")
        allowed = {field.name for field in fields(cls)} - {"vault"}
        values: dict = {}
        for section in ("vault", "notion", "index"):
            contents = data.get(section, {})
            if not isinstance(contents, dict):
                raise ValueError("Config bölümleri tablo olmalı")
            for key, value in contents.items():
                if section == "vault" and key == "path":
                    continue
                if key not in allowed:
                    raise ValueError("Bilinmeyen yapılandırma anahtarı")
                if key in values:
                    raise ValueError("Tekrarlanan yapılandırma anahtarı")
                values[key] = value
        raw = data.get("vault", {}).get("path", "")
        if not raw:
            raise ValueError("Vault yolu boş")
        return cls(vault=Path(raw), **values)

    def token(self, config_path: Path | None = None) -> str | None:
        value = os.environ.get(self.token_env_var)
        if value:
            return value
        if config_path:
            path = config_path.parent / ".env"
            if path.exists():
                for line in path.read_text(encoding="utf-8").splitlines():
                    key, separator, value = line.partition("=")
                    if separator and key.strip() == self.token_env_var:
                        return value.strip().strip("\"'") or None
        return None
