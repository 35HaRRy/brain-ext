import json
from pathlib import Path

import pytest

from brainext.config import Config
from brainext.mdio import atomic_write, read_note, write_note


def test_nested_json_roundtrip_and_atomic(tmp_path):
    path = tmp_path / "Türkçe.md"
    data = {"source": "notion-mirror", "properties": {"Durum": {"select": "Açık"}}}
    write_note(path, data, "# İstanbul\nİçerik\n")
    assert read_note(path) == (data, "# İstanbul\nİçerik\n")
    assert json.loads(path.read_text(encoding="utf-8").split("---")[1]) == data
    atomic_write(path, "yeni")
    assert path.read_text(encoding="utf-8") == "yeni"
    assert list(tmp_path.iterdir()) == [path]


def test_config_rejects_unsafe_regions(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('[vault]\npath="' + tmp_path.as_posix() + '"\nmirror_dir="../oops"', encoding="utf-8")
    with pytest.raises(ValueError):
        Config.load(path)


def test_config_paths_and_defaults(tmp_path):
    config = Config(tmp_path)
    assert config.path("notion/x.md") == tmp_path / "notion/x.md"
    assert config.embedding_model.endswith("mpnet-base-v2")
    with pytest.raises(ValueError):
        config.path("../outside")
    with pytest.raises(ValueError):
        config.path(str(Path(tmp_path.anchor) / "outside"))


def test_init_dry_run_and_preserve_existing(tmp_path, capsys):
    from brainext.cli import main

    target = tmp_path / "config.toml"
    assert main(["init", "--config", str(target), "--vault", str(tmp_path), "--dry-run", "--json"]) == 0
    assert not target.exists()
    assert "dry_run" in capsys.readouterr().out
    assert main(["init", "--config", str(target), "--vault", str(tmp_path), "--mirror-git", "exclude"]) == 0
    assert Config.load(target).vault == tmp_path
    original = target.read_bytes()
    assert main(["init", "--config", str(target), "--vault", str(tmp_path), "--mirror-git", "exclude"]) == 1
    assert target.read_bytes() == original
    assert ".env" in (tmp_path / ".gitignore").read_text(encoding="utf-8")


def test_doctor_no_token_no_network(tmp_path, monkeypatch, capsys):
    from brainext.cli import main

    path = tmp_path / "config.toml"
    path.write_text('[vault]\npath="' + tmp_path.as_posix() + '"', encoding="utf-8")
    monkeypatch.delenv("NOTION_TOKEN", raising=False)
    assert main(["doctor", "--config", str(path), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["fts5"] is True
    assert data["notion"] == "atlandı: token tanımlı değil"


def test_failed_replace_preserves_original(tmp_path, monkeypatch):
    import os

    path = tmp_path / "note.md"
    path.write_text("original", encoding="utf-8")

    def fail(*args):
        raise OSError("synthetic failure")

    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(OSError):
        atomic_write(path, "replacement")
    assert path.read_text(encoding="utf-8") == "original"
    assert list(tmp_path.iterdir()) == [path]
