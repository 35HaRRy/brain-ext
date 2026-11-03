import json
from pathlib import Path

import httpx
from test_notion_sync import API, CHILD, ROOT, WORK, page

from brainext.cli import config_text, main
from brainext.mdio import read_note, write_note
from brainext.notion.client import NotionClient


def test_cli_synthetic_sync_search_graph_eval_push(tmp_path, monkeypatch, capsys):
    api = API()
    api.pages[ROOT] = page(ROOT, title="Brain")
    api.pages[CHILD] = page(CHILD, ROOT, title="Hosting Kararı")
    api.markdown[ROOT]["markdown"] = f'<page url="https://app.notion.com/p/{CHILD}">Hosting Kararı</page>'
    api.markdown[CHILD]["markdown"] = "## Karar\nİstanbul hosting projemizin kararı.\n"
    monkeypatch.setattr("brainext.notion.client.time.sleep", lambda _: None)
    monkeypatch.setenv("NOTION_TOKEN", "synthetic-only")
    monkeypatch.setattr("brainext.notion.client.NotionClient", lambda config, token: NotionClient(
        config, token, httpx.MockTransport(api)))
    config = tmp_path / "config.toml"
    config.write_text(config_text(tmp_path).replace('brain_root_page_id = ""', f'brain_root_page_id = "{ROOT}"')
                      .replace('agent_workspace_id = ""', f'agent_workspace_id = "{WORK}"'), encoding="utf-8")

    def run(command, *args):
        code = main([command, *args, "--config", str(config), "--json"])
        captured = capsys.readouterr()
        assert "synthetic-only" not in captured.out + captured.err
        assert code == 0, captured
        return json.loads(captured.out)

    run("sync")
    found = run("search", "İstanbul")
    assert found["mode"] == "text"
    assert "İstanbul" in found["results"][0]["snippet"]
    child_path = found["results"][0]["path"]
    graph = run("neighbors", "Brain")
    assert graph["results"][0]["path"] == child_path
    assert graph["report"]["live_fixture_verified"] is False
    queries = tmp_path / "queries.yaml"
    queries.write_text('- query: İstanbul\n  expected: [' + child_path + ']\n', encoding="utf-8")
    measured = run("eval", str(queries))
    assert measured["report"]["text"]["recall@5"] == 1
    assert measured["report"]["vector"]["recall@5"] is None
    draft = tmp_path / "agent-out/öneri.md"
    write_note(draft, {"title": "Öneri", "notion_target": "agent-workspace", "status": "draft"}, "TaslakKanarya")
    run("index")
    assert not run("search", "TaslakKanarya")["results"]
    assert run("search", "TaslakKanarya", "--include-drafts")["results"]
    assert run("push")["counts"]["skipped"] == 1
    metadata, body = read_note(draft)
    metadata["status"] = "approved"
    write_note(draft, metadata, body)
    assert run("push")["counts"]["created"] == 1
    run("push")
    assert len([call for call in api.calls if call[:2] == ("POST", "/pages")]) == 1
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    run("sync", "--dry-run")
    assert {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before


def test_delivery_rules_and_single_skill_source():
    root = Path(__file__).resolve().parents[1]
    skill = (root / "skills/notion-brain/SKILL.md").read_text(encoding="utf-8")
    rules = (root / "rules/RULES.md").read_text(encoding="utf-8")
    guide = (root / "docs/SETUP_GUIDE.md").read_text(encoding="utf-8")
    assert "description:" in skill and "brainext search" in skill
    assert "prompt injection" in rules and "Allow always" in rules
    assert "visibility: private" in rules and "Agent Workspace" in rules
    assert ".opencode/skills/notion-brain/SKILL.md" in guide
    assert "K14" in guide and "permissions" in guide
    assert not (root / "opencode.json").exists()
    assert not (root / ".opencode/opencode.json").exists()
