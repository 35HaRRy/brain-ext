import json

from brainext.cli import doctor
from brainext.config import Config
from brainext.mdio import digest, write_json, write_note


def test_doctor_reports_changed_mirror_without_touching_it(tmp_path):
    config = Config(tmp_path)
    note = tmp_path / "notion/a.md"
    write_note(note, {"source": "notion-mirror"}, "ilk")
    original_hash = digest(note.read_bytes())
    write_json(config.state / "state/notion_state.json", {"version": 1, "pages": {
        "00000000-0000-0000-0000-000000000001": {
            "path": "notion/a.md", "content_hash": original_hash, "last_edited_time": "x",
        },
    }})
    note.write_text("elle değişti", encoding="utf-8")
    before = note.read_bytes()
    report = doctor(config)
    assert report["mirror_conflicts"] == ["notion/a.md"]
    assert report["exit_code"] == 2
    assert note.read_bytes() == before


def test_doctor_corrupt_state_does_not_claim_health(tmp_path):
    config = Config(tmp_path)
    path = config.state / "state/notion_state.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"pages": []}), encoding="utf-8")
    assert doctor(config)["exit_code"] == 2


def test_doctor_detects_new_unindexed_sources(tmp_path):
    from brainext.search.index import build_index

    config = Config(tmp_path)
    write_note(tmp_path / "notes/a.md", {}, "eski not")
    build_index(config)
    assert doctor(config)["index_stale"] is False
    write_note(tmp_path / "notes/b.md", {}, "yeni not")
    assert doctor(config)["index_stale"] is True
