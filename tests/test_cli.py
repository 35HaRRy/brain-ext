import pytest

from brainext.cli import main, parser


@pytest.mark.parametrize("command", ["pull", "push"])
def test_sync_commands_accept_dry_run_and_json(command):
    args = parser().parse_args([command, "--dry-run", "--json"])
    assert args.command == command
    assert args.dry_run and args.json


def test_sync_without_token_stops_safely(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("NOTION_TOKEN", raising=False)
    path = tmp_path / "config.toml"
    path.write_text('[vault]\npath="' + tmp_path.as_posix() + '"', encoding="utf-8")
    assert main(["pull", "--config", str(path), "--json"]) == 1
    assert "hata" in capsys.readouterr().err


def test_missing_config_suggests_init(tmp_path, capsys):
    assert main(["doctor", "--config", str(tmp_path / "missing.toml"), "--json"]) == 1
    assert "brainext init" in capsys.readouterr().err
