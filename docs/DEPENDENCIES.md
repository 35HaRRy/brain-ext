# Bağımlılıklar ve Lisanslar

2026-11-03; yalnız proje `.venv` dağıtım metadatası doğrulandı. Paket sürüm aralıkları `pyproject.toml` içindedir. Bu lisans envanteri hukuki görüş değildir.

| Paket | Kurulu sürüm | Lisans | Kullanım |
|---|---|---|---|
| httpx | 0.28.1 | BSD-3-Clause | Notion HTTP; testte MockTransport |
| PyYAML | 6.0.3 | MIT | Kullanıcı/taslak frontmatter ve eval YAML okuma; safe_load |
| fastembed | 0.9.1 | Apache-2.0 | İsteğe bağlı yerel ONNX embedding |
| numpy | 2.5.4 | BSD-3-Clause ve dağıtımda 0BSD/MIT/Zlib/CC0-1.0 bileşenleri | İsteğe bağlı vektör yedeği |
| sqlite-vec | 0.1.9 | MIT veya Apache-2.0 | İsteğe bağlı SQLite vektör işlemleri |
| onnxruntime | 1.31.1 | MIT | FastEmbed inference motoru |
| tokenizers | 0.23.3 | Apache-2.0 | Modelin yerel tokenizer'ı |
| pytest | 9.2.0 | MIT | Geliştirme/test |
| ruff | 0.17.3 | MIT | Geliştirme/lint |
| setuptools | 84.2.1 | MIT | Paketleme |

Python stdlib: argparse, sqlite3, tomllib, pathlib, hashlib, json ve diğer standart modüller; Python/SQLite kendi lisansları geçerlidir. Runtime'da bağımlılık kurulmaz.

Kaynaklar: [httpx](https://github.com/encode/httpx), [PyYAML](https://github.com/yaml/pyyaml), [FastEmbed](https://github.com/qdrant/fastembed), [NumPy](https://numpy.org/doc/stable/license.html), [sqlite-vec](https://github.com/asg017/sqlite-vec), [ONNX Runtime](https://github.com/microsoft/onnxruntime), [tokenizers](https://github.com/huggingface/tokenizers), [pytest](https://github.com/pytest-dev/pytest), [ruff](https://github.com/astral-sh/ruff).

Model lisansları paket lisansından ayrıdır: mpnet/MiniLM Apache-2.0, multilingual-e5-large MIT; keşif model kartları kaynak alınmıştır. Gerçek model bu uygulamada indirilmedi; dağıtılmadan önce seçili modelin lisans/artifact sürümü tekrar kontrol edilir.

Basic Memory (AGPL-3.0) bağımlılık değildir; kodu alınmadı. BM25/RRF ve graf fikirleri bağımsız uygulanır. avenoxbeyin runtime'ı pakete gömülmez; gizlilik davranışı keşif sözleşmesine göre bağımsız uygulanır.
