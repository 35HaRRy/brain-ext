"""Physical descendants from complete Notion v2 Markdown; ambiguity falls back."""

import re
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse
from uuid import UUID


def _url_id(value, *, block=False):
    url = urlparse(value)
    if url.scheme != "https" or url.hostname not in {
        "notion.so", "www.notion.so", "notion.com", "www.notion.com", "app.notion.com",
    }:
        raise ValueError("Notion adresi doğrulanamadı")
    if block and url.fragment:
        return str(UUID(unquote(url.fragment)))
    match = re.search(
        r"([0-9a-f]{32}|[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})/?$",
        unquote(url.path), re.IGNORECASE,
    )
    if match is None:
        raise ValueError("Notion kimliği eksik")
    return str(UUID(match[1]))


class _Children(HTMLParser):
    def __init__(self):
        super().__init__()
        self.children = []
        self.tags = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"unknown", "folder"}:
            raise ValueError("Blok tabanlı keşif gerekli")
        if tag not in {"page", "database"}:
            return
        urls = [value for key, value in attrs if key == "url"]
        if len(urls) != 1 or not urls[0]:
            raise ValueError("Alt sayfa adresi eksik veya belirsiz")
        self.tags += 1
        ref = ["page_id" if tag == "page" else "database_id", _url_id(urls[0])]
        if ref not in self.children:
            self.children.append(ref)


class _Unknowns(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []

    def handle_starttag(self, tag, attrs):
        if tag == "unknown":
            urls = [value for key, value in attrs if key == "url"]
            if len(urls) == 1 and urls[0]:
                try:
                    self.refs.append((self.get_starttag_text(), _url_id(urls[0], block=True)))
                except (ValueError, TypeError):
                    pass  # Keep the original marker: discovery must fall back.


def unknown_refs(text):
    parser = _Unknowns()
    parser.feed(text)
    parser.close()
    return parser.refs


def children_from_markdown(data):
    text = data.get("markdown")
    if (not isinstance(text, str) or data.get("truncated") is not False
            or data.get("unknown_block_ids") != [] or data.get("warnings")):
        raise ValueError("Markdown keşfi eksik")
    if re.search(r"<(?:folder|unknown)\b", text, re.IGNORECASE):
        raise ValueError("Blok tabanlı keşif gerekli")
    parser = _Children()
    parser.feed(text)
    parser.close()
    # HTMLParser can leave an unterminated tag buffered without reporting an error.
    if len(re.findall(r"<(?:page|database)\b", text, re.IGNORECASE)) != parser.tags:
        raise ValueError("Markdown alt sayfa etiketi bozuk")
    return parser.children
