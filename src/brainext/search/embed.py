"""Cached-only embedding adapter and the small injected embedder protocol.

An embedder exposes dimension:int, max_tokens:int, count_tokens(text)->int,
and embed(list[str])->iterable[sequence[float]]. Inputs already have E5 prefixes.
count_tokens MUST include special tokens and MUST NOT truncate or pad.
"""

from pathlib import Path


def model_spec(model: str) -> tuple[int, int]:
    name = model.lower()
    if "paraphrase-multilingual-mpnet-base-v2" in name:
        return 512, 768
    if "paraphrase-multilingual-minilm-l12-v2" in name:
        return 128, 384
    if "multilingual-e5-large" in name:
        return 512, 1024
    raise ValueError("Model token sınırı bilinmiyor")


def prefixed(text: str, model: str, *, query: bool = False) -> str:
    if "e5" not in model.lower():
        return text
    while text.startswith(("query: ", "passage: ")):
        text = text.split(": ", 1)[1]
    return ("query: " if query else "passage: ") + text


def budget(embedder) -> int:
    return embedder.max_tokens - max(8, embedder.max_tokens // 32)


class LocalEmbedder:
    def __init__(self, config):
        if not config.model_path or not Path(config.model_path).is_dir():
            raise ValueError("Yerel model yok; metin moduna geçildi (indirme yapılmaz)")
        self.max_tokens, self.dimension = model_spec(config.embedding_model)
        tokenizer_path = Path(config.model_path) / "tokenizer.json"
        if not tokenizer_path.is_file():
            raise ValueError("Yerel tokenizer.json yok; metin moduna geçildi")
        from tokenizers import Tokenizer

        self.tokenizer = Tokenizer.from_file(str(tokenizer_path))
        self.tokenizer.no_truncation()
        self.tokenizer.no_padding()
        from fastembed import TextEmbedding

        self.model = TextEmbedding(model_name=config.embedding_model,
                                   specific_model_path=str(Path(config.model_path).resolve()),
                                   cache_dir=config.model_path, local_files_only=True)

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text, add_special_tokens=True).ids)

    def embed(self, texts):
        if any(self.count_tokens(text) > budget(self) for text in texts):
            raise ValueError("Embedding token bütçesi aşıldı; kırpma reddedildi")
        return self.model.embed(texts)


def get_embedder(config, embedder=None):
    if embedder is not None:
        return embedder, []
    try:
        return LocalEmbedder(config), []
    except (ImportError, OSError, ValueError, RuntimeError):
        return None, ["Yerel model/semantic desteği yok; yalnızca metin (indirme yapılmaz)"]
