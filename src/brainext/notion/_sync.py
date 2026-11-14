"""Pull ve push için ortak kapsam, sayfalama ve durum güven sınırları."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from uuid import UUID

from brainext.mdio import read_json
from brainext.notion.client import NotionError
from brainext.notion.discovery import children_from_markdown, unknown_refs


def canonical(value):
    try:
        return str(UUID(value))
    except (TypeError, ValueError, AttributeError):
        raise ValueError("Geçersiz Notion kimliği") from None


def now():
    return datetime.now(timezone.utc).isoformat()


def result(**counts):
    return {"exit_code": 0, "counts": counts, "errors": []}


def problem(report, message="Sayfa işlenemedi; yerel içerik korundu", *, fatal=False):
    report["errors"].append(message)
    report["exit_code"] = 1 if fatal else max(2, report["exit_code"])


def state_path(config, name):
    return config.path(f"{config.state_dir}/state/{name}_state.json")


def scope_path(config, id):
    return config.path(f"{config.state_dir}/scope/{canonical(id)}.json")


def load_state(config, kind):
    key = "pages" if kind == "notion" else "drafts"
    path = state_path(config, kind)
    state = read_json(path, {"version": 1, key: {}})
    if (set(state) != {"version", key} or type(state["version"]) is not int
            or state["version"] != 1 or not isinstance(state[key], dict)):
        raise ValueError("Durum şeması geçersiz")
    paths = set()
    push_ids = set()
    for id, item in state[key].items():
        if not isinstance(item, dict):
            raise ValueError("Durum kaydı geçersiz")
        if kind == "notion":
            if set(item) - {"path", "content_hash", "last_edited_time", "archived", "partial",
                            "discovery"}:
                raise ValueError("Bilinmeyen ayna durum alanı")
            if any(type(item[field]) is not bool for field in ("archived", "partial") if field in item):
                raise ValueError("Ayna durum alanı geçersiz")
            if canonical(id) != id or not {"path", "content_hash", "last_edited_time"} <= item.keys():
                raise ValueError("Ayna durumu geçersiz")
            relative = item["path"]
            if not isinstance(relative, str):
                raise ValueError("Ayna yolu geçersiz")
            target = config.path(relative)
            mirror = config.path(config.mirror_dir)
            if not target.is_relative_to(mirror) or target.suffix != ".md":
                raise ValueError("Ayna yolu kapsam dışında")
            if relative.casefold() in paths:
                raise ValueError("Tekrarlanan ayna yolu")
            paths.add(relative.casefold())
            if not re.fullmatch(r"sha256:[a-f0-9]{64}", str(item["content_hash"])):
                raise ValueError("Ayna özeti geçersiz")
            if not isinstance(item["last_edited_time"], str):
                raise ValueError("Ayna zamanı geçersiz")
            if "discovery" in item:
                cached = item["discovery"]
                if (not isinstance(cached, dict)
                        or set(cached) != {"last_edited_time", "children"}
                        or not isinstance(cached["last_edited_time"], str)
                        or not cached["last_edited_time"]
                        or not isinstance(cached["children"], list)):
                    raise ValueError("Keşif önbelleği geçersiz")
                for ref in cached["children"]:
                    if (not isinstance(ref, list) or len(ref) != 2
                            or ref[0] not in {"page_id", "database_id"}
                            or canonical(ref[1]) != ref[1]):
                        raise ValueError("Keşif alt sayfa kimliği geçersiz")
        else:
            target = config.path(id)
            if not target.is_relative_to(config.path(config.outbox_dir)) or target.suffix != ".md":
                raise ValueError("Taslak yolu kapsam dışında")
            if not {"push_id", "status", "workspace_id", "operation", "content_hash"} <= item.keys():
                raise ValueError("Gönderim durumu geçersiz")
            if set(item) - {"push_id", "status", "workspace_id", "operation", "content_hash", "notion_id"}:
                raise ValueError("Bilinmeyen gönderim durum alanı")
            if item["operation"] not in {"create", "patch"} or not re.fullmatch(
                r"sha256:[a-f0-9]{64}", str(item["content_hash"])
            ):
                raise ValueError("Gönderim içeriği doğrulanamadı")
            push_id = canonical(item["push_id"])
            if push_id in push_ids or item["status"] not in {"pending", "uncertain", "pushed"}:
                raise ValueError("Gönderim kaydı geçersiz")
            push_ids.add(push_id)
            canonical(item["workspace_id"])
            if item.get("notion_id"):
                canonical(item["notion_id"])
            if item["status"] == "pushed" and not item.get("notion_id"):
                raise ValueError("Gönderim kimliği eksik")
    return state


def parent_ref(obj):
    parent = obj.get("parent", {})
    type = parent.get("type")
    if type in {"page_id", "block_id", "database_id", "data_source_id"}:
        return type, canonical(parent.get(type))
    return None, None


def retrieve(client, type, id):
    endpoint = {"page_id": "pages", "block_id": "blocks", "database_id": "databases",
                "data_source_id": "data_sources"}[type]
    obj = client.request("GET", f"/{endpoint}/{canonical(id)}")
    if canonical(obj.get("id")) != canonical(id):
        raise ValueError("Uzak kimlik uyuşmazlığı")
    return obj


def in_scope(client, obj, root, cache=None):
    root = canonical(root)
    cache = {} if cache is None else cache
    visited = set()
    for _ in range(100):
        id = canonical(obj.get("id"))
        if id == root:
            return True
        if id in visited:
            return False
        visited.add(id)
        type, parent = parent_ref(obj)
        if parent == root:
            return True
        if not parent:
            return False
        key = (type, parent)
        if key not in cache:
            cache[key] = retrieve(client, type, parent)
        obj = cache[key]
    return False


def _leaf_link(block):
    link = block.get("link_to_page")
    if (block.get("object") == "block" and block.get("type") == "link_to_page"
            and block.get("has_children") is False
            and not block.get("archived") and not block.get("in_trash")
            and isinstance(link, dict) and link.get("type") in {"page_id", "database_id"}):
        type = link["type"]
        target = canonical(link.get(type)).replace("-", "")
        label = "page" if type == "page_id" else "database"
        return f"[Notion {label}](https://app.notion.com/p/{target})"
    return None


def _unlisted_page_links(client, id, data, cache=None):
    if (not isinstance(data.get("markdown"), str) or data.get("truncated") is not False
            or data.get("unknown_block_ids") != [] or data.get("warnings")):
        return data
    cache = {} if cache is None else cache
    text = data["markdown"]
    for raw, bid in unknown_refs(text):
        try:
            key = ("block_id", bid)
            if key not in cache:
                cache[key] = retrieve(client, "block_id", bid)
            block = cache[key]
            link = _leaf_link(block)
            if link and in_scope(client, block, id, cache):
                text = text.replace(raw, link)
        except (NotionError, ValueError, KeyError, TypeError):
            pass  # Unverified markers remain visible and require the strict fallback.
    return {**data, "markdown": text}


class IncompleteQuery(ValueError):
    """Eksik sorgu zaman pencerelerine ayrılabilir; bozuk cursor bu sınıfa girmez."""


def paginated(client, method, path, *, payload=None, metadata=None):
    cursor = None
    seen = set()
    total = 0
    while True:
        args = {"page_size": 100}
        if cursor:
            args["start_cursor"] = cursor
        data = client.request(method, path, **(
            {"params": args} if method == "GET" else {"json": {**(payload or {}), **args}}))
        rows = data.get("results")
        if metadata is not None:
            metadata.clear()
            metadata.update(data)
        if not isinstance(rows, list) or not isinstance(data.get("has_more"), bool):
            raise ValueError("Sayfalama yanıtı eksik")
        incomplete = data.get("request_status", {}).get("type") == "incomplete"
        total += len(rows)
        yield rows
        if incomplete:
            raise IncompleteQuery("Uzak tarama eksik")
        if method == "POST" and total >= 10000:
            raise IncompleteQuery("10000 satır sınırı")
        if not data["has_more"]:
            return
        cursor = data.get("next_cursor")
        if not isinstance(cursor, str) or not cursor or cursor in seen:
            raise ValueError("Sayfalama imleci eksik veya yineleniyor")
        seen.add(cursor)


def data_source_rows(client, id):
    """Capped sorguyu yarı-açık created_time pencerelerine böl; asla tam sayma."""
    seen = set()

    def window(start, end, depth=0):
        payload = None if depth == 0 else {"filter": {"and": [
            {"timestamp": "created_time", "created_time": {"on_or_after": start.isoformat()}},
            {"timestamp": "created_time", "created_time": {"before": end.isoformat()}},
        ]}}
        rows = []
        try:
            for batch in paginated(client, "POST", f"/data_sources/{id}/query", payload=payload):
                rows.extend(batch)
        except IncompleteQuery:
            if depth >= 32 or end - start <= timedelta(milliseconds=1):
                raise ValueError("Aynı zaman aralığında çok fazla satır; tarama kısmi") from None
            middle = start + (end - start) / 2
            yield from window(start, middle, depth + 1)
            yield from window(middle, end, depth + 1)
            return
        for row in rows:
            key = row.get("id")
            if not isinstance(key, str):
                raise ValueError("Satır kimliği eksik")
            if key not in seen:
                seen.add(key)
                yield row

    yield from window(datetime(1970, 1, 1, tzinfo=timezone.utc),
                      datetime.now(timezone.utc) + timedelta(days=1))


class Inventory:
    def __init__(self, client, root, *, discovery_cache=None):
        self.client = client
        self.root = canonical(root)
        self.pages = {}
        self.cache = {}
        self.visited = set()
        self.errors = []
        self.discovery_cache = discovery_cache
        self.discovery = {}
        self.markdown_cache = {}

    @property
    def complete(self):
        return not self.errors

    def scan(self, *, root_type="page_id"):
        self._visit(root_type, self.root)
        return self

    def _visit(self, type, id, obj=None):
        id = canonical(id)
        if (type, id) in self.visited:
            return
        self.visited.add((type, id))
        try:
            obj = retrieve(self.client, type, id) if obj is None else obj
            if canonical(obj.get("id")) != id or not in_scope(self.client, obj, self.root, self.cache):
                # A linked external database is not part of this root's inventory.
                if type in {"database_id", "data_source_id"} or (
                        type == "page_id" and self.discovery_cache is not None):
                    return
                raise ValueError("Sayfa kapsam dışında")
            self.cache[type, id] = obj
            if obj.get("archived") or obj.get("in_trash"):
                return
            if type == "page_id":
                self.pages[id] = obj
                if self.discovery_cache is None or not self._markdown_children(id, obj):
                    self._children(id)
            elif type == "block_id":
                self._children(id)
            elif type == "database_id":
                sources = obj.get("data_sources")
                if not isinstance(sources, list):
                    raise ValueError("Veri kaynakları eksik")
                for source in sources:
                    self._visit("data_source_id", source["id"])
            else:
                for row in data_source_rows(self.client, id):
                    row_type = row.get("object")
                    if row_type not in {"page", "data_source"}:
                        raise ValueError("Sorgu nesnesi geçersiz")
                    self._visit(row_type + "_id", row["id"], row)
        except (NotionError, ValueError, KeyError, TypeError):
            self.errors.append("Ağaç taraması eksik; arşivleme kapatıldı (10000 satır sınırı dahil)")

    def _markdown_children(self, id, obj):
        revision = obj.get("last_edited_time")
        if not isinstance(revision, str) or not revision:
            return False
        cached = self.discovery_cache.get(id)
        if cached and cached["last_edited_time"] == revision:
            refs = cached["children"]
        else:
            try:
                data = self.client.request("GET", f"/pages/{id}/markdown",
                                           params={"markdown_version": "v2"})
                data = _unlisted_page_links(self.client, id, data, self.cache)
                self.markdown_cache[id] = data
                refs = children_from_markdown(data)
            except (NotionError, ValueError, KeyError, TypeError):
                return False
        self.discovery[id] = {"last_edited_time": revision, "children": refs}
        for type, child in refs:
            self._visit(type, child)
        return True

    def _children(self, id):
        if ("children", id) in self.visited:
            raise ValueError("Blok döngüsü veya yinelenen kapsayıcı")
        self.visited.add(("children", id))
        for rows in paginated(self.client, "GET", f"/blocks/{id}/children"):
            for block in rows:
                bid = canonical(block.get("id"))
                type = block.get("type")
                if type == "child_page":
                    self._visit("page_id", bid)
                elif type == "child_database":
                    self._visit("database_id", bid)
                elif block.get("has_children"):
                    # Listed container ancestry must also be verified, not merely its descendants.
                    if not in_scope(self.client, block, self.root, self.cache):
                        raise ValueError("Blok kapsam dışında")
                    self.cache["block_id", bid] = block
                    self._children(bid)


def complete_properties(client, page):
    properties = dict(page.get("properties", {}))
    for name, prop in properties.items():
        if not isinstance(prop, dict):
            raise ValueError("Özellik biçimi geçersiz")
        type = prop.get("type")
        value = prop.get(type)
        needs = prop.get("has_more") or (
            isinstance(value, list) and type in {"relation", "title", "rich_text", "people"}
            and len(value) >= 25
        ) or (type == "rollup" and isinstance(value, dict) and value.get("type") == "incomplete")
        if not needs:
            continue
        pid = quote(str(prop["id"]), safe="")
        items = []
        final = {}
        for rows in paginated(client, "GET", f"/pages/{canonical(page['id'])}/properties/{pid}", metadata=final):
            items.extend(rows)
        value = [item.get(type, item) for item in items]
        if type == "rollup":
            aggregate = final.get("property_item", {}).get("rollup")
            if not isinstance(aggregate, dict) or aggregate.get("type") in {"incomplete", "unsupported"}:
                raise ValueError("Rollup sonucu eksik")
            value = aggregate
        properties[name] = {**prop, "has_more": False, type: value}
    return properties


def markdown(client, id, *, responses=None):
    visited = set()
    cache = {}
    partial = False

    def missing(id):
        return f"<!-- notion:eksik-blok {id} -->"

    def fetch(id):
        nonlocal partial
        id = canonical(id)
        if id in cache:
            return cache[id]
        # shortcut: 128 subtrees per page; use iterative expansion for larger documents.
        if id in visited or len(visited) >= 128:
            partial = True
            return missing(id)
        visited.add(id)
        data = (responses or {}).get(id)
        if data is None:
            data = client.request("GET", f"/pages/{id}/markdown", params={"markdown_version": "v2"})
        data = _unlisted_page_links(client, id, data)
        text = data.get("markdown")
        if not isinstance(text, str):
            raise ValueError("Markdown yanıtı eksik")
        if data.get("warnings"):
            partial = True
        ids = {canonical(value) for value in data.get("unknown_block_ids", [])}
        replacements = {}
        for unknown in sorted(ids):
            try:
                if unknown == id:
                    # Unsupported page-link blocks can return themselves as unknown forever.
                    block = retrieve(client, "block_id", id)
                    link = _leaf_link(block)
                    if link:
                        replacements[unknown] = link
                        continue
                replacements[unknown] = fetch(unknown)
            except (NotionError, ValueError):
                replacements[unknown] = missing(unknown)
                partial = True
        found = set()

        def replace(match):
            nonlocal partial
            raw = match.group(0)
            for unknown in ids:
                if unknown in raw or unknown.replace("-", "") in raw:
                    found.add(unknown)
                    return replacements[unknown]
            partial = True
            return missing(id)

        text = re.sub(r"<unknown\b[^>]*?/>", replace, text, flags=re.IGNORECASE)
        for unknown in ids - found:
            partial = True
            text += "\n" + missing(unknown)
        if data.get("truncated") and not ids:
            partial = True
            text += "\n" + missing(id)
        cache[id] = text
        return text

    return fetch(canonical(id)), partial
