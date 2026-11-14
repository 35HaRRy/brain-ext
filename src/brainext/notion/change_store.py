"""Durable operation identities, review hashes and acknowledged deletion history."""

from __future__ import annotations

import difflib
import json
from uuid import NAMESPACE_URL, uuid5

from brainext.mdio import digest, read_json, write_json
from brainext.notion._sync import canonical, now, state_path

ACTIVE = {"queued", "approved", "pending", "uncertain", "conflict"}
PAYLOAD = {
    "id", "action", "target", "title", "body", "old_str", "new_str", "reason",
    "baseline", "created_at",
}
FIELDS = PAYLOAD | {
    "request_hash", "status", "approved_hash", "notion_id", "completed_at", "detail",
}
def request_hash(operation):
    payload = {key: operation[key] for key in sorted(PAYLOAD)}
    return digest(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"))


def load(config):
    state = read_json(state_path(config, "changes"), {
        "version": 1, "operations": {}, "tombstones": {},
    })
    if (set(state) != {"version", "operations", "tombstones"}
            or type(state["version"]) is not int or state["version"] != 1
            or not isinstance(state["operations"], dict)
            or not isinstance(state["tombstones"], dict)):
        raise ValueError("Değişiklik günlüğü geçersiz")
    for id, op in state["operations"].items():
        if (not isinstance(op, dict) or set(op) != FIELDS or canonical(id) != id
                or op["id"] != id or canonical(op["target"]) != op["target"]
                or op["action"] not in {"create", "update", "delete"}
                or op["status"] not in ACTIVE | {"applied", "cancelled"}
                or any(not isinstance(op[key], str) for key in FIELDS - {"baseline"})
                or not isinstance(op["baseline"], dict)
                or op["request_hash"] != request_hash(op)):
            raise ValueError("Değişiklik kaydı veya onay içeriği geçersiz")
        if op["approved_hash"] and op["approved_hash"] != op["request_hash"]:
            raise ValueError("Onay artık geçerli değil")
        if op["status"] == "approved" and not op["approved_hash"]:
            raise ValueError("Onay eksik")
        if op["notion_id"]:
            canonical(op["notion_id"])
    for id, item in state["tombstones"].items():
        if (not isinstance(item, dict) or set(item) != {
                "id", "page_id", "origin", "observed_at", "acknowledged_at",
            } or canonical(id) != id or item["id"] != id
                or canonical(item["page_id"]) != item["page_id"]
                or item["origin"] not in {"local", "notion"}
                or not isinstance(item["observed_at"], str)
                or not isinstance(item["acknowledged_at"], str)):
            raise ValueError("Silme geçmişi geçersiz")
    return state


def save(config, state):
    write_json(state_path(config, "changes"), state)


def affected(op):
    if op["action"] == "delete":
        return set(op["baseline"]["pages"])
    return {op["target"]}


def blockers(state, page_ids, *, exclude=None):
    ids = set(page_ids)
    return [op for id, op in state["operations"].items()
            if id != exclude and op["status"] in ACTIVE and ids & affected(op)]


def deletion(state, page_id, *, origin, event, acknowledged=False):
    id = str(uuid5(NAMESPACE_URL, f"brainext:{origin}:{page_id}:{event}"))
    item = state["tombstones"].setdefault(id, {
        "id": id, "page_id": page_id, "origin": origin,
        "observed_at": now(), "acknowledged_at": "",
    })
    if acknowledged:
        item["acknowledged_at"] = item["acknowledged_at"] or now()
    return id


def view(op):
    before = ""
    after = op["body"]
    if op["action"] != "create":
        before = op["baseline"]["pages"][op["target"]]["body"]
        after = before.replace(op["old_str"], op["new_str"], 1) if op["action"] == "update" else ""
    diff = "".join(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile="Notion baseline", tofile="Proposed",
    ))
    pages = op["baseline"].get("pages", {})
    return {key: op[key] for key in (
        "id", "action", "target", "title", "reason", "status", "request_hash",
        "notion_id", "detail",
    )} | {"diff": diff, "affected_page_ids": sorted(affected(op)),
          "affected_pages": [{"id": id, "title": snapshot["title"]}
                             for id, snapshot in pages.items()]}
