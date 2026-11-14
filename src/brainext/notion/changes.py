"""Notion-primary proposals: automatic creates, reviewed edits/trash, no blind replay."""

from __future__ import annotations

import re
from contextlib import nullcontext
from dataclasses import replace
from uuid import uuid4

from brainext.mdio import operation_lock
from brainext.notion import change_store as store
from brainext.notion._sync import (
    Inventory,
    canonical,
    now,
    parent_ref,
    problem,
    result,
    retrieve,
)
from brainext.notion.client import NotionError, UncertainWrite
from brainext.notion.pull import _title
from brainext.notion.push import _workspace

ERRORS = (ValueError, OSError, NotionError, KeyError, TypeError)
STRUCTURAL = re.compile(r"</?[a-zA-Z][^>]*>")


def _active(page):
    if page.get("in_trash") or page.get("archived"):
        raise ValueError("Sayfa çöp kutusunda")


def _snapshot(client, id):
    page = retrieve(client, "page_id", id)
    _active(page)
    data = client.request("GET", f"/pages/{id}/markdown", params={"markdown_version": "v2"})
    if (not isinstance(data.get("markdown"), str) or data.get("truncated") is not False
            or not isinstance(data.get("unknown_block_ids"), list)
            or data["unknown_block_ids"] or data.get("warnings")
            or re.search(r"<unknown\b", data["markdown"], re.IGNORECASE)):
        raise ValueError("Eksik Markdown yazılamaz")
    after = retrieve(client, "page_id", id)
    if page != after or not isinstance(page.get("last_edited_time"), str):
        raise ValueError("Sayfa okuma sırasında değişti")
    return {"page": page, "body": data["markdown"], "title": _title(page)}


def _tree(client, id):
    inventory = Inventory(client, id).scan()
    if not inventory.complete or id not in inventory.pages:
        raise ValueError("Silme kapsamı eksik")
    # Database schema changes must invalidate a subtree deletion too.
    containers = {f"{type}:{key}": obj for (type, key), obj in inventory.cache.items()
                  if type in {"database_id", "data_source_id"}}
    return {"pages": {key: _snapshot(client, key) for key in sorted(inventory.pages)},
            "containers": containers}


def _protected(config, ids):
    roots = {*config.memory_roots, config.brain_root_page_id, config.agent_workspace_id}
    protected = {canonical(root) for root in roots if root}
    if set(ids) & protected:
        raise ValueError("Yapılandırılmış kök silinemez")


def propose(config, client, *, action, target, title="", body="", old_str="", new_str="",
            reason="", dry_run=False):
    report = result(proposed=0)
    try:
        target = canonical(target)
        if (action not in {"create", "update", "delete"}
                or any(not isinstance(x, str) for x in (title, body, old_str, new_str, reason))):
            raise ValueError("Öneri geçersiz")
        with nullcontext() if dry_run else operation_lock(config.state):
            state = store.load(config)
            if action == "create":
                if not title.strip() or len(title) > 2000:
                    raise ValueError("Başlık gerekli")
                type, parent, title_key = _workspace(replace(config, agent_workspace_id=target), client)
                baseline = {"root_type": type, "parent": parent, "title_key": title_key}
            elif action == "update":
                snapshot = _snapshot(client, target)
                if (not old_str or old_str == new_str or snapshot["body"].count(old_str) != 1
                        or STRUCTURAL.search(old_str) or STRUCTURAL.search(new_str)):
                    raise ValueError("Tekil, yapısal olmayan metin değişikliği gerekli")
                start = snapshot["body"].index(old_str)
                end = start + len(old_str)
                if any(start < tag.end() and end > tag.start()
                       for tag in STRUCTURAL.finditer(snapshot["body"])):
                    raise ValueError("Yapısal etiketin içi değiştirilemez")
                baseline = {"pages": {target: snapshot}, "containers": {}}
                title = _title(snapshot["page"])
            else:
                baseline = _tree(client, target)
                _protected(config, baseline["pages"])
                title = _title(baseline["pages"][target]["page"])
            id = str(uuid4())
            op = {
                "id": id, "action": action, "target": target, "title": title,
                "body": body if action == "create" else "",
                "old_str": old_str if action == "update" else "",
                "new_str": new_str if action == "update" else "",
                "reason": reason, "baseline": baseline, "created_at": now(),
                "status": "queued", "approved_hash": "", "notion_id": "",
                "completed_at": "", "detail": "",
            }
            op["request_hash"] = store.request_hash(op)
            state["operations"][id] = op
            if not dry_run:
                store.save(config, state)
            report.update(id=id, request_hash=op["request_hash"], dry_run=dry_run)
            report["counts"]["proposed"] = 1
    except ERRORS:
        problem(report, "Öneri doğrulanamadı; hiçbir uzak değişiklik yapılmadı", fatal=True)
    return report


def review(config):
    state = store.load(config)
    return {"exit_code": 0, "results": [store.view(op) for op in state["operations"].values()],
            "tombstones": list(state["tombstones"].values())}


def approve(config, items, *, dry_run=False):
    report = result(approved=0)
    try:
        if not isinstance(items, dict) or not items:
            raise ValueError("Açık kimlik ve inceleme özeti gerekli")
        with nullcontext() if dry_run else operation_lock(config.state):
            state = store.load(config)
            for id, expected in items.items():
                op = state["operations"][canonical(id)]
                if op["status"] != "queued" or expected != op["request_hash"]:
                    raise ValueError("İncelenen sürüm geçerli değil")
            for id in items:
                op = state["operations"][canonical(id)]
                op.update(status="approved", approved_hash=op["request_hash"])
            if not dry_run:
                store.save(config, state)
            report["counts"]["approved"] = len(items)
    except ERRORS:
        problem(report, "Toplu onay uygulanmadı; kimlik ve inceleme özetlerini denetleyin", fatal=True)
    return report


def cancel(config, ids, *, dry_run=False):
    report = result(cancelled=0)
    try:
        if not ids:
            raise ValueError("İşlem kimliği gerekli")
        with nullcontext() if dry_run else operation_lock(config.state):
            state = store.load(config)
            selected = [state["operations"][canonical(id)] for id in ids]
            if any(op["status"] not in {"queued", "approved", "conflict"} for op in selected):
                raise ValueError("Gönderilmiş veya belirsiz işlem iptal edilemez")
            for op in selected:
                op.update(status="cancelled", approved_hash="")
            if not dry_run:
                store.save(config, state)
            report["counts"]["cancelled"] = len(selected)
    except ERRORS:
        problem(report, "İptal uygulanmadı; belirsiz gönderimler önce uzlaştırılmalı", fatal=True)
    return report


def _content(op):
    return op["body"].rstrip("\r\n") + "\n\nbrainext-push-id: " + op["id"] + "\n"


def _check(config, client, state, op):
    target = op["target"]
    if op["action"] == "create":
        type, parent, key = _workspace(replace(config, agent_workspace_id=target), client)
        if op["baseline"] != {"root_type": type, "parent": parent, "title_key": key}:
            raise ValueError("Oluşturma hedefi değişti")
        # Only a pending deletion prevents adding a child to an accessible page.
        if any(other["action"] == "delete" for other in store.blockers(
                state, [target], exclude=op["id"])):
            raise ValueError("Hedef silinmeyi bekliyor")
        return
    if op["approved_hash"] != op["request_hash"]:
        raise ValueError("Onay gerekli")
    if op["action"] == "delete":
        _protected(config, op["baseline"]["pages"])
        if store.blockers(state, op["baseline"]["pages"], exclude=op["id"]):
            raise ValueError("Silinecek kapsamda bekleyen değişiklik var")
        current = _tree(client, target)
    else:
        current = {"pages": {target: _snapshot(client, target)}, "containers": {}}
    if current != op["baseline"]:
        raise ValueError("Notion sürümü onaydan sonra değişti")


def _recover(client, op, hint=None):
    target = op["target"]
    if op["action"] == "delete":
        page = retrieve(client, "page_id", target)
        return target if page.get("in_trash") else None
    if op["action"] == "update":
        snapshot = _snapshot(client, target)
        before = op["baseline"]["pages"][target]
        expected = before["body"].replace(op["old_str"], op["new_str"], 1)
        # Parent changes must not acknowledge a write against a different destination.
        if (snapshot["body"] == expected
                and parent_ref(snapshot["page"]) == parent_ref(before["page"])
                and snapshot["page"].get("properties") == before["page"].get("properties")):
            return target
        return None

    def matches_request(id):
        snapshot = _snapshot(client, canonical(id))
        parent = op["baseline"]["parent"]
        return (canonical(id) != target
                and parent_ref(snapshot["page"]) == (parent["type"], parent[parent["type"]])
                and snapshot["body"].strip() == _content(op).strip()
                and snapshot["title"] == op["title"])

    if hint:
        try:
            if matches_request(hint):
                return canonical(hint)
        except ERRORS:
            pass
    matches = set()
    inventory = Inventory(client, target).scan(root_type=op["baseline"]["root_type"])
    if not inventory.complete:
        return None
    for id in inventory.pages:
        if id == target:
            continue
        try:
            if matches_request(id):
                matches.add(id)
        except ERRORS:
            # An unrelated unsupported sibling is not evidence about this write.
            continue
    return matches.pop() if len(matches) == 1 else None


def _finish(state, op, id):
    op.update(status="applied", notion_id=id, completed_at=now(), detail="")
    if op["action"] == "delete":
        for page_id in op["baseline"]["pages"]:
            store.deletion(state, page_id, origin="local", event=op["id"], acknowledged=True)


def apply(config, client, *, ids=None, dry_run=False):
    report = result(applied=0, waiting=0, conflicts=0, uncertain=0, failed=0, planned=0)
    try:
        with nullcontext() if dry_run else operation_lock(config.state):
            state = store.load(config)
            selected = state["operations"] if ids is None else {
                canonical(id): state["operations"][canonical(id)] for id in ids
            }
            for op in selected.values():
                if op["status"] in {"applied", "cancelled"}:
                    continue
                if op["status"] == "conflict":
                    report["counts"]["conflicts"] += 1
                    problem(report, "Çakışmalı işlem inceleme bekliyor")
                    continue
                if op["status"] == "queued" and op["action"] != "create":
                    report["counts"]["waiting"] += 1
                    continue
                try:
                    if op["status"] in {"pending", "uncertain"}:
                        id = _recover(client, op, op["notion_id"])
                        if id:
                            _finish(state, op, id)
                            report["counts"]["applied"] += 1
                        else:
                            op.update(status="uncertain", detail="Sonuç belirsiz; kör tekrar yapılmadı")
                            report["counts"]["uncertain"] += 1
                            problem(report, op["detail"])
                    else:
                        try:
                            _check(config, client, state, op)
                        except ERRORS:
                            op.update(status="conflict", approved_hash="",
                                      detail="Hedef değişti, eksik okundu veya bekleyen işlemle çakışıyor")
                            report["counts"]["conflicts"] += 1
                            problem(report, op["detail"])
                            if not dry_run:
                                store.save(config, state)
                            continue
                        if dry_run:
                            report["counts"]["planned"] += 1
                            continue
                        op["status"] = "pending"
                        store.save(config, state)
                        response = {}
                        try:
                            target = op["target"]
                            if op["action"] == "create":
                                response = client.request("POST", "/pages", json={
                                    "parent": op["baseline"]["parent"],
                                    "properties": {op["baseline"]["title_key"]: {
                                        "type": "title", "title": [{"type": "text", "text": {
                                            "content": op["title"],
                                        }}],
                                    }},
                                    "markdown": _content(op), "markdown_version": config.markdown_version,
                                })
                            elif op["action"] == "update":
                                response = client.request("PATCH", f"/pages/{target}/markdown", json={
                                    "type": "update_content", "update_content": {
                                        "content_updates": [{"old_str": op["old_str"],
                                                             "new_str": op["new_str"]}],
                                    }, "markdown_version": config.markdown_version,
                                })
                            else:
                                response = client.request("PATCH", f"/pages/{target}",
                                                          json={"in_trash": True})
                        except UncertainWrite as error:
                            op["notion_id"] = error.committed_resource_id or ""
                        except NotionError:
                            response = {"warnings": True}
                        id = None if response.get("warnings") else _recover(client, op, response.get("id"))
                        if id:
                            _finish(state, op, id)
                            report["counts"]["applied"] += 1
                        else:
                            op.update(status="uncertain", detail="Yazma doğrulanamadı; kör tekrar yapılmadı")
                            report["counts"]["uncertain"] += 1
                            problem(report, op["detail"])
                    if not dry_run:
                        store.save(config, state)
                except ERRORS:
                    if op["status"] == "pending":
                        op["status"] = "uncertain"
                    report["counts"]["failed"] += 1
                    problem(report, "İşlem doğrulanamadı; yeniden yazılmadı")
                    if not dry_run:
                        store.save(config, state)
    except ERRORS:
        problem(report, "Kuyruk, kilit veya kimlik doğrulanamadı; gönderim durduruldu", fatal=True)
    return report
