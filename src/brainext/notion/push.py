"""Onaylı taslaklar: kalıcı gönderim kimliği ve kapsam içi uzlaştırma."""

from __future__ import annotations

from contextlib import nullcontext
from uuid import uuid4

from yaml import YAMLError

from brainext.mdio import digest, operation_lock, read_note, write_json, write_note
from brainext.notion._sync import (
    Inventory,
    canonical,
    in_scope,
    load_state,
    markdown,
    now,
    problem,
    result,
    retrieve,
    state_path,
)
from brainext.notion.client import NotionError, UncertainWrite


def _marker(entry):
    # Visible text survives Markdown round-trips; HTML comments may be discarded by Notion.
    return "brainext-push-id: " + canonical(entry["push_id"])


def _content(body, entry):
    return body.rstrip("\r\n") + "\n\n" + _marker(entry) + "\n"


def _workspace(config, client):
    id = canonical(config.agent_workspace_id)
    for type in ("page_id", "database_id", "data_source_id"):
        try:
            obj = retrieve(client, type, id)
            break
        except NotionError as error:
            if error.status != 404:
                raise
    else:
        raise ValueError("Agent Workspace bulunamadı")
    if obj.get("archived") or obj.get("in_trash"):
        raise ValueError("Agent Workspace arşivlenmiş")
    if type == "page_id":
        return type, {"type": "page_id", "page_id": id}, "title"
    if type == "database_id":
        sources = obj.get("data_sources", [])
        if len(sources) != 1:
            raise ValueError("Tek hedef data source seçimi gerekli")
        source = retrieve(client, "data_source_id", sources[0]["id"])
        if not in_scope(client, source, id):
            raise ValueError("Data source hedef kapsamı dışında")
    else:
        source = obj
    titles = [name for name, prop in source.get("properties", {}).items()
              if prop.get("type") == "title"]
    if len(titles) != 1:
        raise ValueError("Title şeması doğrulanamadı")
    return type, {"type": "data_source_id", "data_source_id": canonical(source["id"])}, titles[0]


def _verify(client, id, root, entry):
    obj = retrieve(client, "page_id", id)
    if obj.get("archived") or obj.get("in_trash") or canonical(id) == canonical(root):
        raise ValueError("Yazma hedefi geçersiz")
    if not in_scope(client, obj, root):
        raise ValueError("Yazma hedefi Agent Workspace dışında")
    text, partial = markdown(client, id)
    if partial or _marker(entry) not in text.splitlines():
        raise ValueError("Araç sahipliği doğrulanamadı")
    return text


def _reconcile(config, client, root_type, entry, hint=None):
    candidates = set()
    for id in (hint, entry.get("notion_id")):
        if id:
            try:
                text = _verify(client, canonical(id), config.agent_workspace_id, entry)
                if entry.get("operation") != "patch" or digest(text.encode()) == entry.get("content_hash"):
                    return canonical(id)
            except (NotionError, ValueError):
                pass
    inventory = Inventory(client, config.agent_workspace_id).scan(root_type=root_type)
    for id in inventory.pages:
        if id == canonical(config.agent_workspace_id):
            continue
        try:
            text = _verify(client, id, config.agent_workspace_id, entry)
            if entry.get("operation") == "patch" and digest(text.encode()) != entry.get("content_hash"):
                continue
            candidates.add(id)
        except (NotionError, ValueError):
            continue
    if inventory.complete and len(candidates) == 1:
        return candidates.pop()
    return None


def _finish(config, state, entry, id, path, metadata, body):
    if digest(_content(body, entry).encode("utf-8")) != entry.get("content_hash"):
        raise ValueError("Taslak bekleyen gönderimden sonra değişmiş; onay korunmadı")
    if read_note(path) != (metadata, body):
        raise ValueError("Taslak işlem sırasında değişmiş; dosya korundu")
    entry.update(status="pushed", notion_id=canonical(id))
    write_json(state_path(config, "push"), state)
    metadata.update(notion_id=canonical(id), status="pushed", pushed_at=now())
    write_note(path, metadata, body)


def push(config, client, *, dry_run=False) -> dict:
    report = result(created=0, updated=0, reconciled=0, skipped=0, uncertain=0, failed=0)
    try:
        canonical(config.agent_workspace_id)
        with nullcontext() if dry_run else operation_lock(config.state):
            state = load_state(config, "push")
            entries = state["drafts"]
            outbox = config.path(config.outbox_dir)
            paths = sorted(outbox.rglob("*.md")) if outbox.exists() else []
            workspace = None
            for raw_path in paths:
                try:
                    relative = raw_path.relative_to(config.vault).as_posix()
                    path = config.path(relative)
                    metadata, body = read_note(path)
                    entry = entries.get(relative)
                    recover = entry and entry["status"] in {"pending", "uncertain"}
                    if metadata.get("status") != "approved" and not recover:
                        report["counts"]["skipped"] += 1
                        continue
                    if metadata.get("notion_target") != "agent-workspace":
                        raise ValueError("Taslak hedefi geçersiz")
                    if not isinstance(metadata.get("title"), str) or not metadata["title"].strip():
                        raise ValueError("Taslak başlığı gerekli")
                    if entry and canonical(entry["workspace_id"]) != canonical(config.agent_workspace_id):
                        raise ValueError("Taslak workspace değişmiş")
                    local_id = metadata.get("notion_id")
                    if local_id and (not entry or canonical(local_id) != entry.get("notion_id")):
                        raise ValueError("Taslak kimliği sahiplik kanıtı değil")
                    if workspace is None:
                        workspace = _workspace(config, client)
                    root_type, parent, title_key = workspace
                    if recover:
                        id = _reconcile(config, client, root_type, entry)
                        if id:
                            if not dry_run:
                                _finish(config, state, entry, id, path, metadata, body)
                            report["counts"]["reconciled"] += 1
                        else:
                            if not dry_run:
                                entry["status"] = "uncertain"
                                write_json(state_path(config, "push"), state)
                                metadata["status"] = "uncertain"
                                write_note(path, metadata, body)
                            report["counts"]["uncertain"] += 1
                            problem(report, "Gönderim belirsiz; kör tekrar yapılmadı")
                        continue
                    if entry:
                        _verify(client, entry["notion_id"], config.agent_workspace_id, entry)
                    elif local_id:
                        raise ValueError("Araç sahipliği eksik")
                    if dry_run:
                        report["counts"]["updated" if entry else "created"] += 1
                        continue
                    existing = bool(entry)
                    if entry is None:
                        entry = {"push_id": str(uuid4()), "workspace_id": canonical(config.agent_workspace_id)}
                        entries[relative] = entry
                    content = _content(body, entry)
                    entry.update(status="pending", operation="patch" if existing else "create",
                                 content_hash=digest(content.encode("utf-8")))
                    # Persist before any write request, including updates. A crash resumes read-only.
                    write_json(state_path(config, "push"), state)
                    hint = None
                    warning = False
                    try:
                        if existing:
                            id = entry["notion_id"]
                            response = client.request("PATCH", f"/pages/{id}/markdown", json={
                                "type": "replace_content", "replace_content": {"new_str": content},
                                "markdown_version": config.markdown_version,
                            })
                            hint = id
                        else:
                            response = client.request("POST", "/pages", json={
                                "parent": parent, "properties": {title_key: {"type": "title", "title": [
                                    {"type": "text", "text": {"content": metadata["title"]}}]}},
                                "markdown": content, "markdown_version": config.markdown_version,
                            })
                            hint = response.get("id")
                        warning = bool(response.get("warnings"))
                    except UncertainWrite as error:
                        hint = error.committed_resource_id
                    except NotionError:
                        warning = True
                    id = None if warning else _reconcile(config, client, root_type, entry, hint)
                    if id:
                        _finish(config, state, entry, id, path, metadata, body)
                        report["counts"]["updated" if existing else "created"] += 1
                    else:
                        entry["status"] = "uncertain"
                        write_json(state_path(config, "push"), state)
                        metadata["status"] = "uncertain"
                        write_note(path, metadata, body)
                        report["counts"]["uncertain"] += 1
                        problem(report, "Yazma uyarılı veya belirsiz; yeniden gönderilmedi")
                except (NotionError, ValueError, OSError, KeyError, TypeError, YAMLError):
                    report["counts"]["failed"] += 1
                    problem(report, "Taslak veya hedef sahipliği doğrulanamadı; gönderim durduruldu")
    except (NotionError, ValueError, OSError, KeyError, TypeError):
        problem(report, "Durum, kilit veya yapılandırma doğrulanamadı; işlem durduruldu", fatal=True)
    return report
