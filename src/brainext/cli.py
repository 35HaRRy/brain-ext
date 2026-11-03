"""Türkçe, JSON destekli komut satırı."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from brainext.config import Config
from brainext.mdio import atomic_write


def config_text(vault: Path) -> str:
    return (
        "[vault]\npath = " + json.dumps(str(vault), ensure_ascii=False)
        + '\nmirror_dir = "notion"\noutbox_dir = "agent-out"\nstate_dir = ".brain-ext"\n'
        + '\n[notion]\napi_version = "2026-03-11"\nmarkdown_version = "v2"\n'
        + 'mirror_trust = "untrusted"\nbrain_root_page_id = ""\nagent_workspace_id = ""\n'
        + '# Limit plana/endpoint ve paylaşılan workspace bütçesine bağlıdır.\n'
        + 'requests_per_second = 2.5\ntoken_env_var = "NOTION_TOKEN"\n'
        + '\n[index]\nembedding_model = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"\n'
        + 'rrf_k = 60\nprefix_min_length = 4\n'
    )


def initialize(args: argparse.Namespace) -> dict:
    if not args.vault:
        raise ValueError("--vault ile mutlak vault yolunu belirtin")
    vault = Path(args.vault)
    Config(vault)
    if not vault.is_dir():
        raise ValueError("Vault mevcut bir klasör olmalı; installer çalıştırılmaz")
    config = Path(args.config)
    example = config.parent / ".env.example"
    if config.exists():
        raise ValueError("Config zaten var; üzerine yazılmadı")
    if args.dry_run:
        return {"dry_run": True, "config": str(config), "vault": str(vault)}
    choice = args.mirror_git or input("notion/ git'e dahil edilsin mi? [evet/hayır]: ").strip()
    if choice not in {"include", "exclude", "evet", "hayır"}:
        raise ValueError("Git seçimi include/exclude olmalı")
    ignore = Config(vault).path(".gitignore")
    lines = ignore.read_text(encoding="utf-8").splitlines() if ignore.exists() else []
    additions = [".brain-ext/", ".env", ".beyin-note-write/"]
    if choice in {"exclude", "hayır"}:
        additions.append("notion/")
    atomic_write(ignore, "\n".join(lines + [x for x in additions if x not in lines]) + "\n")
    atomic_write(config, config_text(vault))
    if not example.exists():
        atomic_write(example, "NOTION_TOKEN=\n")
    return {"config": str(config), "mesaj": "Yapılandırma hazır; token değerini paylaşmayın"}


def doctor(config: Config, token: str | None = None) -> dict:
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE VIRTUAL TABLE probe USING fts5(text)")
        fts5 = True
    except sqlite3.OperationalError:
        fts5 = False
    finally:
        connection.close()
    return {
        "fts5": fts5,
        "notion": "canlı erişim ayrıca doğrulanmalı" if token else "atlandı: token tanımlı değil",
        "token_tanimli": bool(token),
        "avenox_doctor": "çalıştırılmadı; Faz B onayı gerekli",
        "embedding": "yerel model ayrıca doğrulanmalı; otomatik indirme yok",
        "index": "var" if (config.state / "index.db").exists() else "henüz yok",
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Notion aynası ve yerel hafıza araması")
    commands = result.add_subparsers(dest="command", required=True)
    for name in ("init", "doctor"):
        command = commands.add_parser(name)
        command.add_argument("--config", default="config.toml")
        command.add_argument("--json", action="store_true")
        command.add_argument("--verbose", action="store_true")
        if name == "init":
            command.add_argument("--vault")
            command.add_argument("--dry-run", action="store_true")
            command.add_argument("--mirror-git", choices=["include", "exclude"])
    return result


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    try:
        if args.command == "init":
            output = initialize(args)
        else:
            config = Config.load(Path(args.config))
            output = doctor(config, config.token(Path(args.config)))
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return output.get("exit_code", 0)
    except (ValueError, OSError, sqlite3.Error):
        # Never echo exception text: external errors may contain credentials or note content.
        print(json.dumps({"hata": "İşlem güvenle durduruldu; yapılandırma/yol/izinleri denetleyin"}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
