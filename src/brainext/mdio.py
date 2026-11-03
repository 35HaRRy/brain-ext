"""UTF-8 notlar, atomik dosyalar ve vault yol sınırları."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import yaml


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def safe_path(root: Path, relative: str) -> Path:
    root = root.absolute()
    candidate = Path(relative)
    if candidate.is_absolute() or candidate.drive or ".." in candidate.parts or not relative:
        raise ValueError("Güvensiz göreli yol")
    target = root / candidate
    for part in [root, *root.parents, *target.parents, target]:
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise ValueError("Sembolik bağ/junction yolu reddedildi")
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("Vault dışına çıkılamaz")
    return target


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".brainext-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def read_note(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8-sig")
    if not text.startswith("---\n"):
        return {}, text
    header, delimiter, body = text[4:].partition("\n---\n")
    if not delimiter:
        raise ValueError("Frontmatter kapanışı bulunamadı")
    metadata = yaml.safe_load(header)
    if not isinstance(metadata, dict):
        raise ValueError("Frontmatter nesne olmalı")
    return metadata, body


def note_text(metadata: dict, body: str) -> str:
    return "---\n" + json.dumps(metadata, ensure_ascii=False, indent=2) + "\n---\n" + body


def write_note(path: Path, metadata: dict, body: str) -> None:
    atomic_write(path, note_text(metadata, body))


def read_json(path: Path, default: dict | None = None) -> dict:
    if not path.exists():
        return {} if default is None else default
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Durum dosyası nesne olmalı; işlem durduruldu")
    return value


def write_json(path: Path, value: dict) -> None:
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2))


@contextmanager
def operation_lock(state_dir: Path) -> Iterator[None]:
    state_dir.mkdir(parents=True, exist_ok=True)
    lock = state_dir / "operation.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError("Başka işlem sürüyor veya kilit kaldı; otomatik silinmez") from None
    try:
        os.close(descriptor)
        yield
    finally:
        lock.unlink(missing_ok=True)
