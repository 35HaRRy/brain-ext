"""Turkish folding for retrieval only; never alter displayed or embedded text."""

import re
import unicodedata


def fold(text: str) -> str:
    text = unicodedata.normalize("NFC", text).replace("İ", "i").replace("I", "ı").lower()
    text = text.translate(str.maketrans("ışğçöüâîû", "isgcouaiu"))
    return "".join(c for c in unicodedata.normalize("NFD", text)
                   if not unicodedata.combining(c))


def fts_query(text: str, prefix_min_length: int = 4) -> str:
    # Operators and punctuation are words, never executable FTS syntax.
    return " AND ".join('"' + word + '"' + ("*" if len(word) >= prefix_min_length else "")
                        for word in re.findall(r"[^\W_]+", fold(text)))
