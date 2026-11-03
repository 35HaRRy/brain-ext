import json

import pytest

from brainext.cli import main, parser


@pytest.mark.parametrize("command,args", [
    ("index", ["--dry-run", "--reembed"]),
    ("sync", ["--dry-run", "--if-stale", "30m"]),
    ("search", ["İstanbul", "--mode", "hybrid", "--include-drafts", "--group-by-file"]),
    ("neighbors", ["notes/a.md", "--depth", "2"]),
    ("eval", ["eval/queries.yaml"]),
])
def test_search_commands_parser(command, args):
    parsed = parser().parse_args([command, *args, "--json"])
    assert parsed.command == command
    assert parsed.json


def test_fresh_sync_skips_without_reading_token_or_network(tmp_path, monkeypatch, capsys):
    from datetime import datetime, timezone

    from brainext.config import Config

    config = tmp_path / "config.toml"
    config.write_text('[vault]\npath="' + tmp_path.as_posix() + '"', encoding="utf-8")
    state = tmp_path / ".brain-ext/state/sync_state.json"
    state.parent.mkdir(parents=True)
    state.write_text(json.dumps({"last_success": datetime.now(timezone.utc).isoformat()}), encoding="utf-8")

    def forbidden(*args):
        raise AssertionError("Token gereksiz yere okunmamalı")

    monkeypatch.setattr(Config, "token", forbidden)
    assert main(["sync", "--config", str(config), "--if-stale", "30m", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["skipped"] is True
