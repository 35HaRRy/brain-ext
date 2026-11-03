"""Türkçe, JSON destekli komut satırı."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from brainext.config import Config
from brainext.mdio import atomic_write, digest, read_json, write_json


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
    from brainext.notion._sync import Inventory, load_state, retrieve
    from brainext.notion.client import NotionClient, NotionError
    from brainext.notion.push import _workspace

    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE VIRTUAL TABLE probe USING fts5(text)")
        fts5 = True
    except sqlite3.OperationalError:
        fts5 = False
    finally:
        connection.close()
    report = {
        "exit_code": 0,
        "fts5": fts5,
        "notion": "canlı erişim ayrıca doğrulanmalı" if token else "atlandı: token tanımlı değil",
        "token_tanimli": bool(token),
        "avenox_doctor": "çalıştırılmadı; Faz B onayı gerekli",
        "embedding": "yerel model ayrıca doğrulanmalı; otomatik indirme yok",
        "index": "var" if (config.state / "index.db").exists() else "henüz yok",
        "mirror_conflicts": [],
        "index_stale": True,
        "warnings": [],
    }
    try:
        state = load_state(config, "notion")
        for entry in state["pages"].values():
            path = config.path(entry["path"])
            if not path.is_file() or digest(path.read_bytes()) != entry["content_hash"]:
                report["mirror_conflicts"].append(entry["path"])
        if report["mirror_conflicts"]:
            report["exit_code"] = 2
    except (ValueError, OSError, KeyError, TypeError):
        report["warnings"].append("Ayna durum dosyası doğrulanamadı")
        report["exit_code"] = 2
    try:
        import sqlite_vec

        with sqlite3.connect(":memory:") as probe:
            try:
                probe.enable_load_extension(True)
                sqlite_vec.load(probe)
            finally:
                probe.enable_load_extension(False)
            report["vector_backend"] = "sqlite-vec " + probe.execute("SELECT vec_version()").fetchone()[0]
    except (ImportError, OSError, sqlite3.Error, AttributeError):
        report["vector_backend"] = "numpy yedeği (kuruluysa); aksi halde yalnızca metin"
    report["model_cached"] = bool(config.model_path and Path(config.model_path).is_dir())
    index = config.path(f"{config.state_dir}/index.db")
    if index.is_file():
        try:
            with sqlite3.connect(index.as_uri() + "?mode=ro", uri=True) as database:
                from brainext.search.index import scan

                rows = database.execute("SELECT path, content_hash FROM docs").fetchall()
                current = scan(config)
                report["index_stale"] = dict(rows) != {
                    path: item["hash"] for path, item in current.items()
                }
                report["broken_links"] = database.execute(
                    "SELECT count(*) FROM links WHERE dst_doc IS NULL"
                ).fetchone()[0]
        except (sqlite3.Error, ValueError, OSError):
            report["warnings"].append("İndeks okunamadı; yeniden indeksleme gerekli")
            report["exit_code"] = 2
    if token:
        try:
            with NotionClient(config, token) as client:
                retrieve(client, "page_id", config.brain_root_page_id)
                _workspace(config, client)
                inventory = Inventory(client, config.brain_root_page_id).scan()
                report["notion"] = "kök erişimleri doğrulandı"
                report["notion_pages"] = len(inventory.pages)
                if not inventory.complete:
                    report["warnings"].append("Brain taraması eksik")
                    report["exit_code"] = 2
        except (NotionError, ValueError, KeyError, TypeError):
            report["notion"] = "erişim doğrulanamadı"
            report["exit_code"] = 2
        report["warnings"].append("Tam paylaşım envanteri API ile garanti edilemez; portalda denetleyin")
    if not fts5:
        report["exit_code"] = 2
    return report


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Notion aynası ve yerel hafıza araması")
    commands = result.add_subparsers(dest="command", required=True)
    for name in ("init", "doctor", "pull", "push", "index", "sync", "search", "neighbors", "eval"):
        command = commands.add_parser(name)
        command.add_argument("--config", default="config.toml")
        command.add_argument("--json", action="store_true")
        command.add_argument("--verbose", action="store_true")
        if name == "init":
            command.add_argument("--vault")
            command.add_argument("--dry-run", action="store_true")
            command.add_argument("--mirror-git", choices=["include", "exclude"])
        if name in {"pull", "push", "index", "sync"}:
            command.add_argument("--dry-run", action="store_true")
        if name == "pull":
            command.add_argument("--page")
            command.add_argument("--full", action="store_true")
            command.add_argument("--force", action="store_true")
            command.add_argument("--confirm-force", action="store_true")
            command.add_argument("--lock-mirror", action="store_true")
        if name == "index":
            command.add_argument("--reembed", action="store_true")
        if name == "sync":
            command.add_argument("--if-stale")
        if name == "search":
            command.add_argument("query")
            command.add_argument("--mode", choices=["text", "vector", "hybrid"], default="hybrid")
            command.add_argument("--k", type=int, default=8)
            command.add_argument("--path-prefix")
            command.add_argument("--include-drafts", action="store_true")
            command.add_argument("--group-by-file", action="store_true")
        if name == "neighbors":
            command.add_argument("target")
            command.add_argument("--depth", type=int, default=2)
        if name == "eval":
            command.add_argument("queries")
    return result


def sync_is_fresh(config: Config, interval: str | None) -> bool:
    if interval is None:
        return False
    match = re.fullmatch(r"([1-9][0-9]*)([smhd])", interval)
    if not match:
        raise ValueError("Süre 30m gibi olmalı")
    seconds = int(match[1]) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[match[2]]
    state = read_json(config.path(f"{config.state_dir}/state/sync_state.json"))
    if not state:
        return False
    if set(state) != {"last_success"} or not isinstance(state["last_success"], str):
        raise ValueError("Sync durumu geçersiz")
    last = datetime.fromisoformat(state["last_success"])
    if last.tzinfo is None:
        raise ValueError("Sync zamanı saat dilimi içermeli")
    age = (datetime.now(timezone.utc) - last).total_seconds()
    return 0 <= age < seconds


def dispatch(args: argparse.Namespace, config: Config) -> dict:
    if args.command == "doctor":
        return doctor(config, config.token(Path(args.config)))
    if args.command in {"index", "search", "neighbors", "eval"}:
        if args.command == "index":
            from brainext.search.index import build_index

            return build_index(config, dry_run=args.dry_run, reembed=args.reembed)
        if args.command == "neighbors":
            from brainext.search.graph import neighbors

            return neighbors(config, args.target, depth=args.depth)
        from brainext.search.query import evaluate, search

        if args.command == "eval":
            return evaluate(config, Path(args.queries))
        return search(config, args.query, mode=args.mode, k=args.k, path_prefix=args.path_prefix,
                      include_drafts=args.include_drafts, group_by_file=args.group_by_file)
    if args.command == "sync" and sync_is_fresh(config, args.if_stale):
        return {"exit_code": 0, "skipped": True, "mesaj": "Senkron henüz bayat değil"}
    token = config.token(Path(args.config))
    if not token:
        raise ValueError("Token tanımlı değil")
    from brainext.notion.client import NotionClient
    from brainext.notion.pull import pull
    from brainext.notion.push import push

    with NotionClient(config, token) as client:
        if args.command == "push":
            return push(config, client, dry_run=args.dry_run)
        if args.command == "pull":
            return pull(config, client, dry_run=args.dry_run, page=args.page,
                        full=args.full, force=args.force, confirm_force=args.confirm_force,
                        lock_mirror=args.lock_mirror)
        report = pull(config, client, dry_run=args.dry_run)
    if report["exit_code"] == 1:
        return report
    from brainext.search.index import build_index

    indexed = build_index(config, dry_run=args.dry_run)
    code = max(report["exit_code"], indexed.get("exit_code", 0))
    if not args.dry_run and code == 0:
        write_json(config.path(f"{config.state_dir}/state/sync_state.json"), {
            "last_success": datetime.now(timezone.utc).isoformat(),
        })
    return {"exit_code": code, "pull": report, "index": indexed, "dry_run": args.dry_run}


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
            output = dispatch(args, config)
        if args.json:
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            labels = {"mode": "mod", "warnings": "uyarılar", "exit_code": "çıkış kodu"}
            for key, value in output.items():
                if key == "results":
                    for row in value:
                        print(f"- {row.get('path', row.get('query', ''))}: "
                              f"{row.get('snippet', row.get('title', row))}")
                else:
                    print(f"{labels.get(key, key)}: {json.dumps(value, ensure_ascii=False)}")
        return output.get("exit_code", 0)
    except (ValueError, OSError, sqlite3.Error, yaml.YAMLError, ImportError):
        # Never echo exception text: external errors may contain credentials or note content.
        print(json.dumps({"hata": "İşlem güvenle durduruldu; yapılandırma/yol/izinleri denetleyin. Config yoksa brainext init kullanın"}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
