"""Documented Markdown v2 graph parser; K14 live fixture remains unverified."""

import posixpath
import re
from collections import defaultdict, deque
from contextlib import closing
from html.parser import HTMLParser
from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse
from uuid import UUID

from brainext.mdio import read_json
from brainext.search.normalize import fold


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag in {"mention", "page", "database", "folder"}:
            self.links.extend((value, "notion-link") for key, value in attrs
                              if key in {"url", "data-source-url"} and value)


def parse_links(body):
    result = [(m[1].split("|", 1)[0].strip(), "wikilink")
              for m in re.finditer(r"\[\[([^\]]+)\]\]", body)]
    result.extend((m[1].strip("<>"), "markdown-link")
                  for m in re.finditer(r"(?<!!)\[[^\[\]]*\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)", body))
    parser = _Links()
    parser.feed(body)
    return result + parser.links


def _id(value):
    try:
        return str(UUID(str(value)))
    except (ValueError, AttributeError):
        return None


def _url_id(value):
    url = urlparse(value)
    if url.scheme != "https" or url.hostname not in {"notion.so", "www.notion.so", "app.notion.com"}:
        return None
    segments = unquote(url.path).strip("/").split("/")
    if url.hostname == "app.notion.com" and (len(segments) < 2 or segments[0] != "p"):
        return None
    for segment in reversed(segments):
        direct = _id(segment)
        if direct:
            return direct
        # Historical title-slug-<32 hex id>, only ever matched against a recorded ID.
        if len(segment) >= 33 and segment[-33] == "-":
            direct = _id(segment[-32:])
            if direct:
                return direct
    return None


def resolve_links(config, db):
    docs = [dict(row) for row in db.execute("SELECT * FROM docs")]
    titles, paths, ids, urls = (defaultdict(set) for _ in range(4))
    for doc in docs:
        id = doc["id"]
        titles[fold(doc["title"])].add(id)
        paths[fold(doc["path"])].add(id)
        paths[fold(str(PurePosixPath(doc["path"]).with_suffix("")))].add(id)
        notion_id = _id(doc["notion_id"])
        if notion_id:
            ids[notion_id].add(id)
        if doc["notion_url"]:
            urls[doc["notion_url"].rstrip("/")].add(id)
    try:
        state = read_json(config.path(f"{config.state_dir}/state/notion_state.json"))
        pages = state.get("pages", {})
        if not isinstance(pages, dict):
            raise ValueError("Ayna durum şeması geçersiz")
        for notion_id, item in pages.items():
            if isinstance(item, dict) and _id(notion_id):
                ids[_id(notion_id)].update(paths.get(fold(str(item.get("path", ""))), set()))
    except (ValueError, OSError):
        pass  # Mirror metadata remains authoritative if optional sync state is unreadable.
    doc_by_id = {doc["id"]: doc for doc in docs}
    for row in db.execute("SELECT rowid,* FROM links").fetchall():
        target = unquote(row["target"].split("#", 1)[0])
        candidates = set()
        if urlparse(target).scheme:
            candidates = urls.get(target.rstrip("/"), set())
            notion_id = _url_id(target)
            if notion_id:
                candidates = candidates | ids.get(notion_id, set())
        else:
            candidates = paths.get(fold(target), set())
            if not candidates:
                src = PurePosixPath(doc_by_id[row["src_doc"]]["path"])
                relative = str(src.parent / target)
                # Normalize dot segments without ever reading a filesystem target.
                candidates = paths.get(fold(posixpath.normpath(relative)), set())
            if not candidates:
                candidates = titles.get(fold(target), set())
        dst = next(iter(candidates)) if len(candidates) == 1 else None
        db.execute("UPDATE links SET dst_doc=? WHERE rowid=?", (dst, row["rowid"]))


def neighbors(config, target, depth=2) -> dict:
    from brainext.search.index import connect, live_docs

    output = {"exit_code": 0, "report": {"live_fixture_verified": False,
                                         "K14": "not_run"}, "results": []}
    if type(depth) is not int or depth < 0:
        return {**output, "exit_code": 1}
    connection = connect(config, readonly=True)
    if connection is None:
        return output
    with closing(connection) as db:
        docs = live_docs(config, db)
        matches = [id for id, doc in docs.items() if fold(doc["path"]) == fold(target)]
        if not matches:
            matches = [id for id, doc in docs.items() if fold(doc["title"]) == fold(target)]
        if len(matches) != 1:
            return output
        adjacency = defaultdict(set)
        for row in db.execute("SELECT src_doc,dst_doc FROM links WHERE dst_doc IS NOT NULL"):
            src, dst = row
            if src in docs and dst in docs:
                adjacency[src].add(dst)
                adjacency[dst].add(src)
        seen = {matches[0]}
        queue = deque([(matches[0], 0)])
        while queue:
            current, distance = queue.popleft()
            if distance >= depth:
                continue
            for id in sorted(adjacency[current], key=lambda id: docs[id]["path"]):
                if id in seen:
                    continue
                seen.add(id)
                queue.append((id, distance + 1))
                doc = docs[id]
                output["results"].append({"path": doc["path"], "title": doc["title"],
                                          "distance": distance + 1,
                                          "notion_url": doc["notion_url"] or None})
    return output
