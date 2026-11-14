"""Notion ağacından salt okunur JSON-frontmatter metin aynası."""

from __future__ import annotations

import re
import stat
import unicodedata
from contextlib import nullcontext

from yaml import YAMLError

from brainext.mdio import digest, operation_lock, read_note, write_json, write_note
from brainext.notion import change_store
from brainext.notion._sync import (
    Inventory,
    canonical,
    complete_properties,
    in_scope,
    load_state,
    markdown,
    now,
    parent_ref,
    problem,
    result,
    retrieve,
    scope_path,
    state_path,
)
from brainext.notion.client import NotionError


def _title(page):
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            return "".join(item.get("plain_text", item.get("text", {}).get("content", ""))
                           for item in prop.get("title", [])) or "Başlıksız"
    return "Başlıksız"


def _slug(title):
    title = unicodedata.normalize("NFC", title)
    title = re.sub(r'[\x00-\x1f\x7f/\\:*?"<>|]', "-", title)
    title = re.sub(r"\s+", "-", title).strip(" .-")[:80].rstrip(" .") or "Başlıksız"
    if re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", title):
        title = "_" + title
    return title


def _owned(config, id, entry, force):
    path = config.path(entry["path"])
    if not path.exists():
        raise ValueError("Ayna dosyası kayıp; sahiplik doğrulanamadı")
    metadata, _ = read_note(path)
    if metadata.get("source") != "notion-mirror" or canonical(metadata.get("notion_id")) != id:
        raise ValueError("Dosya araca ait değil")
    changed = digest(path.read_bytes()) != entry["content_hash"]
    if changed and not force:
        raise ValueError("Yerel ayna değişti; ayrı force onayı gerekli")
    return path, changed


def _destination(config, id, title, entries, old=None, archived=False):
    folder = config.mirror_dir + ("/_arsiv" if archived else "")
    slug = _slug(title)
    compact = id.replace("-", "")
    for suffix in (compact[:8], compact):
        relative = f"{folder}/{slug}__{suffix}.md"
        candidate = config.path(relative)
        reserved = any(
            key != id and entry["path"].casefold() == relative.casefold()
            for key, entry in entries.items()
        )
        # Case-fold even on Linux so a later Windows copy cannot silently collide.
        occupied = candidate.parent.exists() and any(
            p.name.casefold() == candidate.name.casefold() and p != old
            for p in candidate.parent.iterdir()
        )
        if not reserved and not occupied:
            return candidate
    raise ValueError("Hedefte sahiplenilmemiş dosya var")


def _replace(config, path, metadata, body, *, old=None, lock=False, expected=None):
    if old is not None and digest(old.read_bytes()) != expected:
        raise ValueError("Ayna işlem sırasında değişti; dosya korundu")
    if path.exists() and path != old:
        raise ValueError("Hedef dosya işlem sırasında oluşturuldu; dosya korundu")
    # Windows read-only blocks replacement/unlink; change only already-owned files.
    for item in {path, old} - {None}:
        if item.exists():
            item.chmod(item.stat().st_mode | stat.S_IWRITE)
    write_note(path, metadata, body)
    if old is not None and old != path:
        old.unlink()
    if lock:
        path.chmod(path.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    return {"path": path.relative_to(config.vault).as_posix(),
            "content_hash": digest(path.read_bytes()),
            "last_edited_time": metadata["last_edited_time"],
             "archived": metadata.get("status") == "archived"}


def _trash_signal(client, id):
    type = "page_id"
    visited = set()
    for _ in range(100):
        if (type, id) in visited:
            break
        visited.add((type, id))
        obj = retrieve(client, type, id)
        if obj.get("in_trash") is True:
            return f"{id}:{obj.get('last_edited_time', '')}"
        type, id = parent_ref(obj)
        if type is None:
            return None
    raise ValueError("Silme üst zinciri doğrulanamadı")


def _deletions(config, client, entries, active, journal, report, *, force=False, dry_run=False):
    groups = {}
    for id, entry in entries.items():
        if id in active or entry.get("archived"):
            continue
        try:
            signal = _trash_signal(client, id)
            if signal is None:
                obj = retrieve(client, "page_id", id)
                if not any(in_scope(client, obj, root) for root in config.memory_roots):
                    if not dry_run:
                        write_json(scope_path(config, id), {"in_scope": False})
                raise ValueError("Kaybolma silme kanıtı değil")
            groups.setdefault(signal, []).append(id)
        except (ValueError, OSError, NotionError, KeyError, TypeError):
            report["counts"]["failed"] += 1
            problem(report, "Sayfa erişilemiyor veya kapsam dışına taşındı; silinmiş sayılmadı")
    eligible = {}
    for signal, ids in groups.items():
        blocked = change_store.blockers(journal, ids)
        try:
            for id in ids:
                _owned(config, id, entries[id], force)
            if blocked:
                raise ValueError("Silme ile bekleyen işlem çakışıyor")
        except (ValueError, OSError, KeyError, TypeError, YAMLError):
            for op in blocked:
                if op["status"] in {"queued", "approved"}:
                    op.update(status="conflict", approved_hash="",
                              detail="Notion silmesi bekleyen yerel değişiklikle çakışıyor")
            if blocked and not dry_run:
                change_store.save(config, journal)
            report["counts"]["failed"] += len(ids)
            problem(report, "Silme çakışması; yerel düzenleme veya bekleyen işlem korundu")
            continue
        eligible.update(dict.fromkeys(ids, signal))
    return eligible


def pull(config, client, *, dry_run=False, page=None, full=False, force=False,
         confirm_force=False, lock_mirror=False) -> dict:
    report = result(new=0, updated=0, unchanged=0, archived=0, failed=0)
    if force and not confirm_force:
        problem(report, "Force için ayrıca açık onay gerekli", fatal=True)
        return report
    try:
        roots = tuple(canonical(root) for root in config.memory_roots)
        # Dry-run must not even create a lock directory.
        with nullcontext() if dry_run else operation_lock(config.state):
            state = load_state(config, "notion")
            entries = state["pages"]
            journal = change_store.load(config)
            discovery_cache = {} if config.memory_root_page_ids else None
            if discovery_cache is not None and not full:
                for id, entry in entries.items():
                    if entry.get("discovery") and not entry.get("partial"):
                        try:
                            _owned(config, id, entry, False)
                            discovery_cache[id] = entry["discovery"]
                        except (ValueError, OSError, KeyError, TypeError, YAMLError):
                            pass  # Local edits invalidate reuse, never authorize overwriting.
            inventory = Inventory(client, roots[0], discovery_cache=discovery_cache).scan()
            if discovery_cache is not None:
                discovery_cache.update(inventory.discovery)
            memberships = {id: {roots[0]} for id in inventory.pages}
            for root in roots[1:]:
                extra = Inventory(client, root, discovery_cache=discovery_cache).scan()
                inventory.pages.update(extra.pages)
                inventory.errors.extend(extra.errors)
                inventory.discovery.update(extra.discovery)
                inventory.markdown_cache.update(extra.markdown_cache)
                if discovery_cache is not None:
                    discovery_cache.update(extra.discovery)
                for id in extra.pages:
                    memberships.setdefault(id, set()).add(root)
            for error in inventory.errors:
                problem(report, error)
            selected = inventory.pages
            if page is not None:
                id = canonical(page)
                if id not in selected:
                    problem(report, "İstenen sayfa hafıza kapsamında doğrulanamadı", fatal=True)
                    return report
                selected = {id: selected[id]}
            for id, remote in selected.items():
                try:
                    entry = entries.get(id)
                    old, changed = _owned(config, id, entry, force) if entry else (None, False)
                    scope = scope_path(config, id)
                    if scope.exists() and not dry_run:
                        write_json(scope, {"in_scope": True})
                    snapshot = digest(old.read_bytes()) if old else None
                    title = _title(remote)
                    destination = _destination(config, id, title, entries, old)
                    same = entry and entry["last_edited_time"] == remote.get("last_edited_time")
                    if same and not full and not changed and not entry.get("partial"):
                        metadata, body = read_note(old)
                        if (old == destination and metadata.get("status") != "archived"
                                and metadata.get("memory_roots") == sorted(memberships[id])):
                            if id in inventory.discovery and not dry_run:
                                entry["discovery"] = inventory.discovery[id]
                            if lock_mirror and not dry_run:
                                old.chmod(old.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
                            report["counts"]["unchanged"] += 1
                            continue
                        partial = False
                        properties = metadata.get("properties", {})
                    else:
                        properties = complete_properties(client, remote)
                        body, partial = markdown(client, id, responses=inventory.markdown_cache)
                    metadata = {
                        "source": "notion-mirror", "kind": config.mirror_trust, "readonly": True,
                        "notion_id": id, "notion_url": remote.get("url", ""), "title": title,
                        "parent_id": parent_ref(remote)[1],
                        "last_edited_time": remote.get("last_edited_time", ""), "synced_at": now(),
                        "content_hash": digest(body.encode("utf-8")), "properties": properties,
                        "memory_roots": sorted(memberships[id]),
                    }
                    if partial:
                        problem(report, "Markdown eksik veya uyarılı; eksik bloklar işaretlendi")
                    if not dry_run:
                        entries[id] = _replace(config, destination, metadata, body, old=old,
                                               lock=lock_mirror, expected=snapshot)
                        entries[id]["partial"] = partial
                        if id in inventory.discovery:
                            entries[id]["discovery"] = inventory.discovery[id]
                        write_json(state_path(config, "notion"), state)
                    report["counts"]["updated" if entry else "new"] += 1
                except (ValueError, OSError, NotionError, KeyError, TypeError, YAMLError):
                    report["counts"]["failed"] += 1
                    problem(report)
            if inventory.complete and page is None:
                eligible = _deletions(
                    config, client, entries, inventory.pages, journal, report,
                    force=force, dry_run=dry_run,
                )
                for id, entry in list(entries.items()):
                    if id in inventory.pages or entry.get("archived"):
                        continue
                    if id not in eligible:
                        continue
                    try:
                        old, _ = _owned(config, id, entry, force)
                        snapshot = digest(old.read_bytes())
                        metadata, body = read_note(old)
                        destination = _destination(config, id, metadata.get("title", "Başlıksız"),
                                                   entries, old, archived=True)
                        metadata.update(status="archived", archived=True)
                        if not dry_run:
                            change_store.deletion(journal, id, origin="notion", event=eligible[id])
                            change_store.save(config, journal)
                            entries[id] = _replace(config, destination, metadata, body, old=old,
                                                    lock=lock_mirror, expected=snapshot)
                            write_json(state_path(config, "notion"), state)
                            change_store.deletion(journal, id, origin="notion",
                                                  event=eligible[id], acknowledged=True)
                            change_store.save(config, journal)
                        report["counts"]["archived"] += 1
                    except (ValueError, OSError, KeyError, TypeError, YAMLError):
                        report["counts"]["failed"] += 1
                        problem(report, "Arşivleme tamamlanamadı; dosya korundu")
            if not dry_run:
                write_json(state_path(config, "notion"), state)
    except (ValueError, OSError, NotionError, KeyError, TypeError):
        problem(report, "Durum, kilit veya yapılandırma doğrulanamadı; işlem durduruldu", fatal=True)
    return report
