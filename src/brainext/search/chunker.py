"""Heading/paragraph chunks; fenced code stays whole in FTS, never silently truncated."""

import re

from brainext.search.embed import budget, prefixed


def _sections(body, title):
    headings = [title]
    lines = []
    fence = None
    for line in body.splitlines(keepends=True):
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if marker:
            if fence is None:
                fence = marker[1][0], len(marker[1])
            elif marker[1][0] == fence[0] and len(marker[1]) >= fence[1]:
                fence = None
        match = re.match(r"^(#{2,3})\s+(.+?)\s*#*\s*$", line) if fence is None else None
        if match:
            if "".join(lines).strip():
                yield " > ".join(headings), "".join(lines).strip()
            level = len(match[1]) - 1
            headings = headings[:level] + [match[2]]
            lines = []
        else:
            lines.append(line)
    if "".join(lines).strip():
        yield " > ".join(headings), "".join(lines).strip()


def _blocks(text):
    lines = []
    fence = None
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if marker and fence is None:
            if "".join(lines).strip():
                yield "".join(lines).strip(), False
            lines = [line]
            fence = marker[1][0], len(marker[1])
        elif marker and fence and marker[1][0] == fence[0] and len(marker[1]) >= fence[1]:
            lines.append(line)
            yield "".join(lines).strip(), True
            lines, fence = [], None
        elif not line.strip() and fence is None:
            if "".join(lines).strip():
                yield "".join(lines).strip(), False
            lines = []
        else:
            lines.append(line)
    if "".join(lines).strip():
        yield "".join(lines).strip(), fence is not None


def _split_units(units, fits, overlap=False):
    """Units include whitespace; no original content is discarded."""
    parts, current = [], ""
    for unit in units:
        if not fits(unit):
            return []
        if current and not fits(current + unit):
            parts.append(current)
            tail = current[-150:] if overlap else ""
            while tail and not fits(tail + unit):
                tail = tail[1:]
            current = tail
        current += unit
    if current:
        parts.append(current)
    return parts


def chunk_document(body: str, title: str, *, embedder=None, model=""):
    chunks, warnings = [], []
    for heading, section in _sections(body, title):
        def input_text(text, heading=heading):
            return prefixed(heading + "\n" + text, model)

        def fits(text):
            return embedder.count_tokens(input_text(text)) <= budget(embedder)

        for text, code in _blocks(section):
            if embedder is None:
                texts = [text] if code else _split_units(
                    re.findall(r"\S+\s*|\s+", text), lambda s: len(s) <= 2000, True)
                texts = texts or [text]
                for part in texts:
                    chunks.append({"heading_path": heading, "text": part, "embedding_texts": []})
                continue
            if fits(text):
                pieces = [text]
            elif code:
                pieces = _split_units(text.splitlines(keepends=True), fits)
                warnings.append("Uzun kod FTS'de tam saklandı; embedding satır sınırlarında bölündü"
                                if pieces else "Kod satırı/başlık token bütçesini aşıyor; yalnız FTS")
            else:
                pieces = _split_units(re.findall(r"\S+\s*|\s+", text), fits, True)
                if not pieces:
                    warnings.append("Sözcük/başlık token bütçesini aşıyor; yalnız FTS")
            if code or not pieces:
                chunks.append({"heading_path": heading, "text": text,
                               "embedding_texts": [input_text(p) for p in pieces]})
            else:
                chunks.extend({"heading_path": heading, "text": part,
                               "embedding_texts": [input_text(part)]} for part in pieces)
    return chunks, warnings
