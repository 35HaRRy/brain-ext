from pathlib import Path

import httpx
import pytest
from test_notion_sync import WORK, draft, listing
from test_notion_sync import setup as setup

from brainext.config import Config
from brainext.mdio import read_json
from brainext.notion.push import push


@pytest.mark.parametrize("name", [".git.", "notes.", "tasks ", "notion.", "CON", "x:y"])
def test_windows_ambiguous_region_names_are_rejected(tmp_path, name):
    (tmp_path / ".git").mkdir()
    (tmp_path / "notes").mkdir()
    with pytest.raises(ValueError):
        Config(tmp_path, state_dir=name)
    assert not (tmp_path / ".git/operation.lock").exists()


@pytest.mark.parametrize("phase", ["create", "recover"])
def test_uncertain_push_preserves_network_time_draft_edits(setup, phase):
    config, api, client = setup
    path = draft(config)
    api.commit = False
    api.post_status = 503
    if phase == "recover":
        assert push(config, client)["exit_code"] == 2

    edited = b"human content changed during HTTP; preserve exact bytes\r\n"

    def edit_during_request(request):
        path.write_bytes(edited)
        return (httpx.Response(503, json={"code": "service_unavailable"})
                if phase == "create" else httpx.Response(200, json=listing([])))

    endpoint = ("POST", "/pages") if phase == "create" else ("GET", f"/blocks/{WORK}/children")
    api.overrides[endpoint] = edit_during_request
    report = push(config, client)
    assert report["exit_code"] == 2
    assert path.read_bytes() == edited
    state = read_json(config.state / "state/push_state.json")
    assert state["drafts"]["agent-out/öneri.md"]["status"] == "uncertain"
    assert len([call for call in api.calls if call[:2] == ("POST", "/pages")]) == 1


def test_documented_full_suite_install_includes_semantic_test_dependencies():
    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    assert 'pip install -e ".[dev,semantic]"' in readme
