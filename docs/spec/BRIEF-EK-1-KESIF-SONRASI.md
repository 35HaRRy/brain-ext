# Brief Ek-1: Keşif Sonrası Kararlar, Düzeltmeler ve Faz 1 Kapsamı

> Bu ek, `NOTION-BRAIN-AGENT-BRIEF.md` ile çeliştiği her yerde **ana brief'in yerine geçer**.
> Bu dosyanın ajana verilmesi, kullanıcının aşağıdaki kararları ve Bölüm 1'deki kapsamı onayladığı anlamına gelir.
> Faz 0 raporun (`DISCOVERY.md`) kaliteliydi; özellikle "doğrulandı / doğrulanmadı" ayrımını koruman gerekiyor, bu ayrımı sürdür.

---

## 1. Onay Kapsamı

**Onaylanan (şimdi yap):**
- Faz 1, 2, 3 ve 4'ün **kod, doküman ve sentetik veriyle yazılan testleri**.
- `brain-ext/` deposunu oluşturma; bağımlılıkları yalnızca **brain-ext'in kendi sanal ortamında** (venv) kurma.
- `DISCOVERY.md` ve `DECISIONS.md`'yi bu ekteki kararlara göre güncelleme.

**Onaylanmayan (Faz B'de, her biri için ayrı açık onay iste):**
- Gerçek vault'u kurma; avenoxbeyin installer, `update` veya `doctor`'ı kullanıcı vault'unda çalıştırma.
- Notion token'ı, OAuth, gerçek Notion sayfası veya `/mcps` bağlantısı.
- Gerçek embedding modelini indirme ve gerçek modelle test/eval (boyut: yaklaşık 0.2-2.2 GB; önce kullanıcıya söyle ve onay al).
- OpenCode yapılandırma dosyalarını veya kayıtlı izinleri okuma/değiştirme.

**Tek açık soru (Faz 1'e başlarken kullanıcıya sor):** `brain-ext/` deposu hangi klasörde olsun? Varsayılan öneri: vault'un **dışında**, ayrı bir klasör. Cevap gelene kadar Faz 1'i başlatma.

---

## 2. Alınan Kararlar

Her karar `docs/DECISIONS.md`'ye gerekçesiyle yazılsın.

| # | Karar | Gerekçe (keşiften) |
|---|---|---|
| D1 | Mirror dosyalarının frontmatter'ı **JSON object** olur (`---` arasında). Yorum satırı, flow mapping, derin YAML yok. | avenoxbeyin sınırlı bir parser kullanıyor; brief'teki yorumlu `properties: {}` satırı reddedildi, derin YAML notu dışlıyor. Nested properties yalnızca tam JSON header'da kabul ediliyor. |
| D2 | Mirror dosyaları `"kind": "untrusted"` taşır (yapılandırılabilir: `mirror_trust`, varsayılan `untrusted`). | `kind: untrusted` avenoxbeyin'in otomatik bağlamına girmeyi engelleyen gerçek kapı; `readonly`/`source` işaretleri güvenlik sınırı değil. Notion içeriği (web kırpıntıları, paylaşılan sayfalar) prompt-injection taşıyabilir; her istemde otomatik enjekte edilmesin, **yalnızca `brainext search` ile bilinçli çekilsin**. Çekirdek profil avenoxbeyin'in kendi Companion dosyalarında kalır. |
| D3 | Arşivlenen sayfalar `notion/_arsiv/`'e taşınır **ve** `"status": "archived"` yazılır. Yalnızca `archived: true`'ya güvenme. | Ölçüm: `_arsiv/` + `archived: true` normal bağlamda geliyor; `status: archived` varsayılan retrieval'da gelmiyor. |
| D4 | `agent-out/` varsayılan aramada **dahil edilmez** (`--path-prefix agent-out/` veya `--include-drafts` ile aranır). Faz B'de avenoxbeyin tarafı için `preferences --index-exclude-dir agent-out` önerilir. | Ölçüm: `agent-out/` ve `status: draft` normal bağlamda geliyor; onaylanmamış taslak hafıza kirliliği yaratır. |
| D5 | brain-ext indeksi **izin listesiyle (allowlist)** çalışır: `notion/`, `notes/`, `knowledge/`, `tasks/` ve Companion klasörü (A1'deki adıyla). Ek olarak avenoxbeyin'in gizlilik süzgeçlerini **birebir uygula**: gizli yollar, `node_modules`, `receipts`, `daily`, symlink, hassas klasör adları, yönerge dosyaları (`AGENTS.md`, `CLAUDE.md`, `SKILL.md`, `INSTRUCTIONS.md`), `visibility: private`, `kind: receipt`, `generated: true`. Hiçbir zaman: `.brain-ext/`, `.beyin-note-write/`, `.claude/`, `.agents/`, `.opencode/`. | Brief'in `**/*.md` glob'u avenoxbeyin'in gizlilik filtreleriyle eşdeğer değil. |
| D6 | Skill tek kaynaktan: `<vault>/.opencode/skills/notion-brain/SKILL.md`. Kural metni: `<vault>/.brain/notion-brain/RULES.md`, OpenCode `instructions` ile yüklenir. `.agents/skills`'e **koyma**, `skill-import`/`skill-sync` **çalıştırma**. | `skill-sync` mirror'ları uzlaştırıp çakışma üretebilir; kullanıcı yalnızca OpenCode kullanıyor. `.opencode/skills` yönetilen adaptörden ayrı. |
| D7 | Oturum başı senkron için yönetilen hook'a **dokunma**. Kural metnindeki talimat (ajan `brainext sync --if-stale 30m` çalıştırır) birincil yol; isteğe bağlı olarak işletim sistemi zamanlayıcısı Faz B'de önerilir. | Hook'u değiştirmeden keyfi callback API'si doğrulanmadı. |
| D8 | OpenCode **V2** biçimi kullanılır (Bölüm 3.8). Notion yazma araçları yalnızca **tek seferlik** onayla; "Allow always" riski kullanıcıya açıkça anlatılır. | V2: `mcp.servers`, `permissions` dizisi, son eşleşen kural kazanır. `ask` bir sandbox değil. |
| D9 | Embedding modeli **yapılandırılabilir ve eval ile seçilir**. İlk deneme adayları: `paraphrase-multilingual-mpnet-base-v2` (512 token, 768 boyut, ~1.0 GB), hafif alternatif MiniLM (128 token, 384 boyut, ~0.22 GB), kalite alternatifi `multilingual-e5-large` (512 token, ~2.24 GB, `query: `/`passage: ` öneki zorunlu). `config.example.toml` varsayılanı: mpnet. Chunk bütçesi **karakter değil, seçili modelin tokenizer'ına göre** (başlık dahil, modelin sınırının altında bir pay bırakarak) hesaplanır; sessiz kırpma yasak. | MiniLM 128 token ile sınırlı; Türkçe'de 2000 karakter bunu rahatça aşar. Bölünmez kod bloğu bütçeyi aşarsa FTS'de tam saklanır, embedding için satır sınırlarında bölünür ve bu durum raporlanır. Nihai seçim kullanıcının gerçek `eval` sonucuna göre. |
| D10 | Gizlilik ifadesi yeniden yazılır (README ve RULES.md): "İndeks ve embedding yerelde üretilir. Ancak ajan bağlamına alınan parçalar OpenCode'daki model sağlayıcısına gider; Notion MCP `mcp.notion.com`'a bağlanır." Mutlak gizlilik garantisi verilmez. Kullanıcı ajana hiç gösterilmeyecek notları `visibility: private` ile işaretler. | Yerel embedding, içeriğin hiçbir üçüncü tarafa gitmediği anlamına gelmez. |
| D11 | Üzerine yazma politikası: tek bir `pull` çalıştırması için alınan onay, araca ait ve hash'i eşleşen mirror dosyalarının **rutin güncellemelerini** kapsar. Kullanıcının elle değiştirdiği dosya çakışma sayılır; `--force` her seferinde ayrı açık onay ister. | Her dosya için ayrı onay pratik değil; kullanıcı düzenlemesini korumak şart. |
| D12 | Ağ kapsamı: veri düzleminde yalnızca `api.notion.com` (+ ilk model indirmesi). Kurulum/güncelleme için GitHub/PyPI, hosted MCP için `mcp.notion.com` ve OAuth uçları ayrıca anılır. Mirror varsayılan olarak **yalnızca metin**; ekleri/medyayı kendiliğinden indirme. avenoxbeyin'in sürüm bildirimleri (GitHub) için `preferences --update-notifications off` seçeneğini Faz B'de kullanıcıya sun. | Keşif Bölüm 10.2. |
| D13 | Windows UTF-8: CLI başlangıcında stdout/stderr'i UTF-8'e ayarla (`reconfigure(encoding="utf-8")`), dosyaları açıkça `encoding="utf-8"` ile oku/yaz. Testlerde Türkçe karakterli çıktı olsun. | Keşifte terminal Türkçe satırı bozuk gösterdi. |
| D14 | Python: brain-ext kendi venv'inde, yalnızca bağımlılıklar çalıştığı sürece 3.14 kullanır; fastembed/onnxruntime/sqlite-vec 3.14'te kurulmazsa **3.12 veya 3.13** venv'ine geç ve bunu `DECISIONS.md`'ye yaz. avenoxbeyin'in sabitlenmiş yorumlayıcısına dokunma. sqlite-vec yüklenemezse numpy yedeği kullanılır. | Keşif: bağımlılıkların 3.14'te çalıştığı test edilmedi. |

---

## 3. Ana Brief'te Düzeltilecek Yerler

### 3.1 Bölüm 0.3 (Gizlilik)
"Hiçbir not içeriği harici bir API'ye gönderilmez" cümlesini kaldır; D10 ifadesini kullan.

### 3.2 Bölüm 5.1 (Config)
- `markdown_version = "v2"` ekle (Notion `markdown_version=v2`; v1 deprecated).
- `mirror_trust = "untrusted"` ekle.
- `requests_per_second = 2.5` muhafazakâr başlangıç olarak kalsın; ancak limitin plana bağlı olduğunu (Business/Enterprise ortalama 10/s, diğerleri ortalama 3/s; data source query ayrıca ~3/s; paylaşılan workspace bütçesi nedeniyle limitin altında da 429 gelebilir) config yorumuna yaz. Kullanıcının planı Faz B'de sorulacak.
- "MCP için 180/dk, arama 30/dk" gibi sabit rakamları dokümanlardan **kaldır**.

### 3.3 Bölüm 6.1 (İstemci)
- GET: `?markdown_version=v2`; POST/PATCH gövdesinde `markdown_version: "v2"`.
- PATCH tipleri: tüm içerik için `replace_content` (`new_str`), hedefli düzenleme için `update_content` (`content_updates`). Yanıttaki `warnings` (özellikle `no_match`) **görmezden gelinmez**; uyarı varsa işlem başarısız/kısmi sayılıp raporlanır.
- `allow_deleting_content: true` **asla** gönderilmez.
- `unknown_block_ids`: kimlikler aynı GET uç noktasına `page_id` olarak verilir; **ziyaret edilmiş kimlik kümesi** tutulur (döngü/tekrar önlemi); içerik mümkünse yerindeki `<unknown .../>` yer tutucusunun yerine konur, sona eklenmez. `404 object_not_found` silinme kanıtı değildir. Tamamlanamayanlar brief'teki eksik-blok yorumuyla ve çıkış kodu `2` ile raporlanır.
- Yeniden deneme: `429` ve `529` için `Retry-After`'a uy. `429 public_api_request_blocked` **tekrar denenmez**. GET/okuma istekleri güvenle yeniden denenebilir. **POST/PATCH yazmalarında "tüm 5xx'i yeniden dene" kuralı geçersiz** (Bölüm 3.5).

### 3.4 Bölüm 6.2 (Pull)
- **Keşif her çalıştırmada yapılır:** Brain kökünden `GET /v1/blocks/{id}/children` ile (cursor/sayfalama dahil) `child_page`/`child_database` kimliklerini gez. `last_edited_time` değişmeyen sayfanın yalnızca **içerik indirmesi** atlanır; yeni çocukların keşfi atlanamaz (kökün zaman damgası torunların değişimini garanti etmez).
- Database'ler: `data_sources` listesini al, her data source'u `POST /v1/data_sources/{id}/query` ile sayfala. `request_status.type == "incomplete"` ise sonuç tam değildir; sessizce "tamam" sayma. Sorgu başına 10000 sonuç tavanına yaklaşılırsa zaman aralığıyla böl. Büyük relation/rollup değerleri için property pagination uygula. `last_edited_time` filtreli artımlı sorgu yalnızca data source'larda kullanılabilir.
- **Kaybolan sayfayı yalnızca eksiksiz ve başarılı bir tarama sonrası arşivle.** 403/404, eksik sayfalama, ağ hatası veya paylaşım değişikliği durumunda toplu arşivleme yapma.
- `POST /v1/search` envanter kaynağı olarak **kullanılmaz** (başlık araması, gecikmeli, eksiksiz değil).
- Linked database'lerin hedefi Brain altında değilse **otomatik çekme**.
- Mirror frontmatter (JSON, D1/D2/D3):

```
---
{
  "source": "notion-mirror",
  "kind": "untrusted",
  "readonly": true,
  "notion_id": "<uuid>",
  "notion_url": "<url>",
  "title": "<başlık>",
  "parent_id": "<uuid>",
  "last_edited_time": "<ISO-8601>",
  "synced_at": "<ISO-8601>",
  "content_hash": "sha256:<...>",
  "properties": {}
}
---
<Notion Markdown v2 içeriği>
```
  Arşivlenenlerde ayrıca `"status": "archived"`.
- `readonly: true` bir kilit değildir. İstenirse (`--lock-mirror`, varsayılan kapalı) mirror dosyalarına işletim sistemi salt-okunur özniteliği uygulanabilir; sync aracı yazarken geçici olarak kaldırır.
- Mirror'a yazılan Markdown, avenoxbeyin'in parser'ının sorun çıkarabileceği bir şey içermemeli: gövde Markdown'dur, yalnızca üstteki header kritik.

### 3.5 Bölüm 6.3 (Push) — idempotentlik yeniden tasarlanacak
`notion_id`'nin varlığını kontrol etmek tek başına yetmez; POST başarılı olup yanıt 5xx/zaman aşımı dönebilir. Tasarım:
1. Her taslak için gönderimden **önce** durum dosyasına `push_id` (istemci tarafı benzersiz kimlik) ile `pending` kaydı yaz.
2. `push_id`'yi oluşturulan sayfanın içeriğine veya başlığa gömülü bir işaretçi olarak ekle (biçimi sen seç ve `DECISIONS.md`'ye yaz).
3. POST sonucu belirsizse (zaman aşımı, 5xx): yanıtta `additional_data.retry_guidance` / `committed_resource_id` varsa ona bak; yoksa Agent Workspace altında işaretçiyi **ara**; bulunursa `notion_id`'yi kaydet; bulunamazsa ve hâlâ belirsizse taslağı `status: uncertain` yap ve kullanıcıya bildir. **Kör POST tekrarı yok.**
4. PATCH için de aynı ilke: yazma sonrası belirsiz durumda önce oku, sonra karar ver.
5. Hedef doğrulaması (sayfanın atası = Agent Workspace) **CLI'da kesin** yapılır; hosted MCP tarafında bu izolasyon sunucu tarafından garanti edilmez, bu yüzden RULES.md'de "her MCP yazma onayında hedef sayfayı kontrol et" kuralı olsun.
6. Agent Workspace bir database ise hedef **data source** ve title property'si şemadan belirlenir; database ID'yi data source ID yerine kullanma.

### 3.6 Bölüm 6.4 ve 9 (Testler)
Ekle: POST sonrası 503 (belirsiz oluşturma); eksik tarama sonrası arşivlememe; `request_status: incomplete`; `unknown_block_ids` (tekrar eden kimlik, 404 dahil); PATCH `no_match` uyarısı; markdown v2 fixture'ları; JSON frontmatter üretimi; Türkçe karakterli dosya adı ve UTF-8.
**K1'i şöyle düzelt:** "İkinci `pull` **içerik indirmez**; ancak keşif/metadata HTTP istekleri yapabilir."
**K5/K6:** hibrit aramanın her sorguda en iyi tek moddan iyi olması garanti değildir; sonuçlar gerçek eval'de **ölçülür**; kötüleşirse raporlanır, "geçti" sayılmaz.
**Yeni K13:** `truncated`/`unknown_block_ids` içeren büyük bir sayfa. **Yeni K14:** Notion'dan gerçek bir sayfa çekip Bölüm 3.7'deki bağlantı kapısını kapatma.

### 3.7 Bölüm 7.7 (Graf)
- Desteklenecek bağlantı biçimleri (resmî v2 sözdizimi; **canlı workspace çıktısı henüz görülmedi**): `[metin](url)`, `<mention url="...">`, `<page url="...">`, `<database url="..." data-source-url="...">`, `<folder url="...">` ve `[[wikilink]]`.
- Notion URL'leri `https://www.notion.so/{id}` ve (Haziran 2026'dan beri) `https://app.notion.com/p/{id}` biçimlerinde olabilir; **URL kararlı kimlik değildir**. Çözümleme için durum dosyasındaki `id ↔ url` eşlemesini kullan; tek bir regex'e güvenme. Bilinmeyen bağlantı çözülmemiş (`dst_doc = NULL`) kalır.
- Ayrıştırıcıyı belgelenmiş biçimlere göre yaz, ama **K14'te kullanıcının gerçek bir test sayfasının GET çıktısıyla doğrulanana kadar** "doğrulanmadı" olarak etiketle.

### 3.8 Bölüm 8.1 (OpenCode V2 yapılandırma taslağı)
Brief'teki tekil `permission` anahtarı V2'de yanlış. Aşağıdaki **taslak**, V2 şemasına göre ve OAuth sonrası gerçek araç kataloğuyla doğrulanmak üzere üretilsin (wildcard sözdizimi ve araç adları doğrulanmadan çalışan dosya olarak yazma; **yapılandırma dosyasını Faz B'ye kadar oluşturma**):

```jsonc
{
  "mcp": {
    "servers": {
      "notion": { "type": "remote", "url": "https://mcp.notion.com/mcp" }
    }
  },
  "permissions": [
    { "action": "notion_*",             "resource": "*", "effect": "ask"   },
    { "action": "notion_notion-search", "resource": "*", "effect": "allow" },
    { "action": "notion_notion-fetch",  "resource": "*", "effect": "allow" }
  ],
  "instructions": [".brain/notion-brain/RULES.md"]
}
```

Notlar: son eşleşen kural kazanır, bu yüzden geniş `ask` önce, dar `allow`'lar sonra gelir. OpenCode izin eylem adı normalize `<server>_<tool>` biçimindedir (örn. `notion_notion-create-pages`). OAuth OpenCode arayüzünden `/mcps` ile yapılır; integration token bu bağlantıya kopyalanmaz. Araç düzeltmesi: **`notion-update-database` yok, `notion-update-data-source` var.** Kullanılacak alt küme: `notion-search`, `notion-fetch`, `notion-create-pages`, `notion-update-page`, `notion-create-comment`, `notion-move-pages`, `notion-duplicate-page`, `notion-create-database`, `notion-update-data-source`. Silme, takvim, oturum, skill ve `notion-memory-search` araçları kapsam dışıdır; yeni yazma araçları geniş `ask` arkasında kalır.

### 3.9 Bölüm 11 (Faz B adımlarına ekle)
- Notion planını sor (rate limit için).
- avenoxbeyin güncelleme bildirimleri kararı (D12).
- Model indirme onayı (D9) ve eval sonrası model seçimi.
- OpenCode'da mevcut kalıcı ("Allow always") izinlerin gözden geçirilmesi.
- avenoxbeyin tarafı: `preferences --index-exclude-dir agent-out`; `notion/` için D2 kararına uygun kontrol.
- K14 için gerçek bir test sayfası.

---

## 4. Çalışma Talimatı

1. Bölüm 1'deki tek soruyu sor (depo konumu); cevaptan sonra Faz 1'e başla.
2. Faz 1 → Faz 4'ü sırayla, **yalnızca sentetik veriyle** tamamla. Her faz sonunda: testler geçsin, kısa özet, commit.
3. `DECISIONS.md`'yi D1-D14 ile güncelle; `DISCOVERY.md`'deki açık maddeleri (Bekleyen) listede tut.
4. Faz 4 sonunda dur ve teslim raporu ver. Faz B'ye **kullanıcı açıkça başlat diyene kadar** geçme.
5. Bir varsayım yanlış çıkarsa yine dur ve tek soru sor.
