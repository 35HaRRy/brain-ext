# brain-ext — Keşif Kararları

## 2026-11-03 — Ek-1 ile onaylanan D1–D14 (önceki önerilerin yerine geçer)

Depo konumu kullanıcı tarafından `C:\Users\35.HaRRy\Desktop\Projects\brain-ext` olarak onaylandı. Önceki geçici MiniLM/ortak skill önerileri aşağıdaki kararlara tabidir.

| Karar | Uygulama ve gerekçe |
|---|---|
| D1 | Mirror header tam JSON object; sınırlı avenox parser ile nested metadata uyumu. |
| D2 | `mirror_trust = "untrusted"`, mirror `kind: untrusted`; otomatik sıradan bağlam yerine bilinçli arama. |
| D3 | Arşiv yolu `_arsiv/` ve `status: archived`; yalnız boolean yeterli değil. |
| D4 | agent-out indekslenebilir ama varsayılan aramada dışarıda; explicit path/include-drafts gerekir. Faz B'de avenox exclusion önerilir. |
| D5 | notion/notes/knowledge/tasks/Companion allowlist ve sabit gizlilik filtreleri; private/generated/receipt, gizli ve managed yollar kesin dışarıda. |
| D6 | Tek skill `.opencode/skills/notion-brain/SKILL.md`; kurallar `.brain/notion-brain/RULES.md`. Ortak `.agents` mirror/import/sync yok. |
| D7 | Hook değişikliği yok; oturum sync ajan kuralı, OS scheduler yalnız Faz B. |
| D8 | OpenCode V2, broad ask sonra read allow; kalıcı izinler onay kapısını aşabilir, tek seferlik izin gerekir. |
| D9 | Config varsayılan mpnet (512 token/768/~1GB); MiniLM (128/384/~0.22GB), E5-large (512/1024/~2.24GB) seçenekleri. Gerçek seçim eval sonrası, sahte embedder testlerde. Başlık dahil tokenizer bütçesi, uzun kod embedding için satırlara bölünür; FTS tam metin saklar. |
| D10 | İndeks/embedding yerel, ajan parçaları model sağlayıcısına gider; mutlak gizlilik iddiası yok. |
| D11 | Rutin hash-eşleşen güncelleme tek pull onayıyla; elle değişen dosyada force ayrıca açık onay gerektirir. |
| D12 | CLI veri ağı Notion API; kurulum GitHub/PyPI, model indirme ayrıca izin, MCP/OAuth ayrıca. Medya indirme yok. |
| D13 | CLI stdout/stderr UTF-8; dosya I/O UTF-8; Türkçe testler. |
| D14 | Ayrı .venv Python 3.14.6; temel bağımlılıklar kuruldu. Semantik wheel/runtime doğrulaması ayrıca, model indirme yok. 3.14 engelinde 3.12/3.13 fallback; sqlite-vec engelinde numpy. |

Güven sınırı: state bozuksa fail-closed; eşzamanlı yazan komutlar ortak exclusive lock kullanır. Kalan kilit otomatik silinmez. Kullanıcı kaynakları otomatik düzeltilmez.

D14 yerel doğrulama: yalnız `.venv` içine `pip install -e ".[semantic]"` geçti. Python 3.14.6'da FastEmbed 0.9.1 (41 model kaydı), ONNX Runtime 1.31.1 import edildi; RAM SQLite'da `sqlite_vec.load` + `vec_version()` → v0.1.9. Hiçbir embedding modeli instantiate/indirilmedi; 3.12/3.13 fallback gerekmedi. Tokenizer/model kalitesi ve gerçek model inference hâlâ Faz B kapısıdır.

Faz 2: push işaretçisi görünür Markdown satırı `brainext-push-id: <UUID>`. HTML yorumunun uzak Markdown dönüşümünde kaybolma riskinden kaçınılır. Pending kayıt POST/PATCH öncesi yazılır; timeout/5xx sonrası kapsam ve marker doğrulanır, sonuç hâlâ belirsizse `uncertain`, kör yazma tekrarı yok. Database çok data source içeriyorsa `agent_workspace_id` açıkça hedef data source ID olabilir; belirsiz ilk kaynak seçilmez. Sorgu limitinde created_time yarı-açık pencereler bölünür; 32 seviye/1ms sınırında hâlâ capped ise kısmi sonuç ve arşivleme engeli (aynı anda >10000 satır tek timestamp ile ayrıştırılamaz).

## 2026-11-03 — Faz 0 sınırı

- Durum: **öneri; uygulama için kullanıcı onayı bekleniyor**.
- Yalnız keşif belgeleri mevcut çalışma alanında `docs/` altına yazılır. `brain-ext/` deposu, vault veya CLI bu fazda kurulmaz. Kullanıcının brief'i ve mevcut yapılandırmaları değiştirilmez.

## 2026-11-03 — Başlangıç embedding modeli

- Öneri: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (FastEmbed 0.9.1 hazır kayıtlı model).
- Gerekçe: Türkçe dahil çok dilli destek, yerel CPU kullanımı, yaklaşık 0.22 GB kayıtlı boyut, 384 boyutlu vektör; E5-large'ın 2.24 GB maliyetine karşı küçük başlangıç. Query/passage öneki gerektirmez.
- Karşılaştırma: multilingual-mpnet-base-v2 1.00 GB / 768 boyut / kayıtlı 512 token; multilingual-e5-large 2.24 GB / 1024 boyut / 512 token, İngilizce `query: ` ve `passage: ` önekleri zorunlu.
- Sınır: MiniLM'in 128 token sınırı nedeniyle brief'teki yalnız 2000 karakter kontrolü yeterli değildir. Başlık dahil tokenizer bütçesi gözetilmeli; fazla içerik sessiz kırpılmamalı. Kod bloklarının bölünmemesi ile model sınırı çatışırsa eksik semantik kapsam açıkça raporlanmalı; tam içerik FTS'de korunmalı.
- Bu seçim bir Türkçe retrieval benchmark sonucu değildir. Gerçek 15–20 sorguluk eval ve kullanıcı onayı sonrası kalıcılaştırılır; kalite yetersizse diğer adaylar değerlendirilir. Model değişimi vektörlerin yeniden üretilmesini gerektirir.
- Kaynaklar: [FastEmbed 0.9.1 model kayıtları](https://github.com/qdrant/fastembed/blob/v0.9.1/fastembed/text/pooled_embedding.py), [resmî liste](https://qdrant.github.io/fastembed/examples/Supported_Models/), [Türkçe dil/model kartı](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2), [E5 önekleri](https://huggingface.co/intfloat/multilingual-e5-large).

## 2026-11-03 — Doğrulanan dış sözleşmeler

- Yeni OpenCode yapılandırması V2 yerel anahtarlarını kullanmalı: `permissions`, `mcp.servers`, `instructions`; mevcut global ayarlara keşifte dokunulmaz.
- Notion REST başlığı `Notion-Version: 2026-03-11`; ayrıca Markdown sözdizimi açıkça `v2` seçilmeli. Kapsam Brain alt ağacıyla sınırlı; genel search eksiksiz envanter yerine kullanılamaz.
- Model indirme ve gerçek Notion/OAuth/veri testleri yapılmadı. Mutlak yerellik/gizlilik iddiasıyla bulut LLM'ine snippet aktarma çelişkisi kullanıcı onayıyla çözülmeden buna dayanan entegrasyon kurulmaz.
- Kaynak ve ayrıntılar: [DISCOVERY.md](DISCOVERY.md), Bölüm 3–10.

## 2026-11-03 — Mirror biçimi, arşiv ve otomatik bağlam

- Durum: **A2 yanlış çıktığı için kullanıcı onayı bekleyen düzeltme önerisi; uygulanmadı**.
- Frontmatter önerisi: `---` arasında kanonik JSON object; iç içe Notion properties bu biçimde korunur. Brief'teki `properties: {} # ...` satırı ve derin YAML pinned parser'da reddedildi.
- Arşiv önerisi: brief'in `archived: true` alanına ek olarak motorun tanıdığı `status: archived`; yalnız `_arsiv/` adı ve boolean alan otomatik bağlamdan çıkarmaz.
- Güven önerisi: mirror'a `kind: untrusted` ekleyip avenox'un otomatik sıradan bağlamına girmesini önlemek; brain-ext aramasıyla açıkça seçilen parçaları güvenilmeyen veri olarak kullanmak. Yalnız `untrusted: true`, `readonly: true` veya `source: notion-mirror` teknik güven kapısı değildir. Kullanıcı onayı olmadan bu politika seçilmiş/uygulanmış sayılmaz.
- Skill önerisi: avenox ile ortak kullanımda `.agents/skills/notion-brain/SKILL.md` tek kaynak; mirror'ları `skill-sync` yönetir. OpenCode'a özel bağımsız ikinci kopya oluşturmak gerekmez. Yönetilen üç çekirdek skill ve `.opencode/plugins/beyin-v3.js` değişmez.
- Kural dosyası için unmanaged aday `.brain/notion-brain/RULES.md`; oturum başlangıcında sync için yönetilen hook değişikliği yerine brief'in ajan talimatı fallback'i. Yerleşik keyfî callback API'si doğrulanmadı.
- Arama kapsamı: brain-ext indeksi `.brain-ext/index.db` ile avenox'un vault dışı `memory.sqlite3` deposundan ayrı. Kaynak notları için geniş glob'un avenox hassas/private filtrelerine otomatik eşdeğer olmadığı hesaba katılmalı; kesin privacy politikası onayla belirlenmeli.
- Kanıt: [DISCOVERY.md](DISCOVERY.md), Bölüm 2; resmî v3.12.0 kaynak/manifest analizi ve izole Windows SyncEngine/MemoryStore fixture'ları. Kurulu kullanıcı vault'u ve gerçek updater/rollback testi yapılmadı.
