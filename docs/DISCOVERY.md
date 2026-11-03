# brain-ext — Faz 0 Keşif Raporu

## Ek-1 sonrası durum — 2026-11-03

Kullanıcı D1–D14'ü ve yalnız sentetik veriyle Faz 1–4 uygulamasını onayladı; depo `C:\Users\35.HaRRy\Desktop\Projects\brain-ext`. Aşağıdaki Faz 0 bulguları tarihsel kanıttır; eski “onay bekliyor”, MiniLM varsayılanı ve ortak skill önerileri güncel karar sayılmaz. Güncel kaynak `docs/spec/BRIEF-EK-1-KESIF-SONRASI.md` ve DECISIONS D1–D14 tablosudur.

**Bekleyen (sentetik testle kapatılamaz):** gerçek kullanıcı vault'u uyumu/doctor/update/rollback; OAuth ve gerçek MCP araç kataloğu/izinler; gerçek model indirme ve Türkçe eval; K14 gerçek Notion Markdown/link çıktısı; gerçek workspace planı ve paylaşım sınırları. Gerçek OpenCode yapılandırması okunmayacak/oluşturulmayacak; doküman taslağı ayrı kalacak.

Tarih: 2026-11-03. Durum: **Keşif bulguları; uygulama için kullanıcı onayı bekleniyor. Faz 1 başlamadı.**

## 1. Kapsam ve kanıt standardı

`../NOTION-BRAIN-AGENT-BRIEF.md` dosyasının 516 satırı baştan sona okundu. Bu rapor Bölüm 4'ün çıktısıdır. Kod deposu, Python paketi, CLI, kullanıcı vault'u, Notion bağlantısı veya OpenCode ayarı kurulmadı. Keşif belgeleri mevcut çalışma dizininin `docs/` klasöründedir; gelecekteki `brain-ext/` deposunun yeri henüz belirlenmedi.

Kaynak türleri birbirinden ayrılır:

- **Belge/kaynak doğrulaması:** resmî yayımlanmış sözleşme veya kaynak kodu.
- **Yerel test:** bu Windows makinesinde gerçekten çalıştırılan kontrol.
- **Bekliyor:** gerçek vault, OAuth, Notion sayfası veya model gerektiren ve yapılmamış kontrol. Belgeden çıkarılan sonuç uçtan uca test sayılmaz.

Keşif kontrol listesi:

- [x] Brief'in tamamını oku; Faz 1 sınırını koru.
- [x] avenoxbeyin belge envanteri, release ve A1–A3 kanıtlarını tamamla.
- [x] OpenCode V2 yapılandırma ve izin sözleşmesini doğrula.
- [x] Notion Markdown, data source ve hız sınırı sözleşmelerini doğrula.
- [x] FastEmbed model adaylarını karşılaştır; gerekçeyi `DECISIONS.md`'ye kaydet.
- [x] Yerel Python/SQLite FTS5 ve uzantı açma kontrolünü çalıştır.
- [x] Son özeti ve açık varsayımları raporla; onay kapısını kapalı tut.

## 2. avenoxbeyin: A1–A3

Sürüm sabiti: resmî son release `v3.12.0`, 2026-10-20; hedef commit `0be8f9961e3bef7a312735cd7461c66ecdca760a`.

Release varlıkları:

- `beyin-v3-3.12.0.zip` — 443079 bayt.
- `beyin-v3-3.12.0.zip.sha256`.
- Release API'de ZIP digest: `d8dbf97a38a50046d3f48205ae08ff65364b92292999fef611f882839d6e9696`.
- Release notları açıkça **GitHub “Source code” arşivini kullanmayın** diyor. Kurulum yapılacaksa release ZIP ve yanındaki checksum kullanılmalı; kaynak dosyalarını araştırmak kurulum değildir.

Kaynak: [release](https://github.com/avenoxai/avenoxbeyin/releases/tag/v3.12.0), [release API](https://api.github.com/repos/avenoxai/avenoxbeyin/releases/latest).

ZIP indirildi ve checksum dosyasıyla karşılaştırıldı: eşleşti. İç manifestteki 46/46 ürün dosyasının SHA-256 değeri ve pinned commit'teki Git blob kimliği doğrulandı. Installer veya `update --check` dahi çalıştırılmadı; bu doğrulama kurulum/preflight testi değildir.

Araştırma kanıt dizini: `C:\Users\35.HaRRy\AppData\Local\Temp\opencode\avenox-research-ae8ff6000a3b4d2093b023f46cc341c7`. İçinde doğrulanmış `release/`, `pinned/`, `main/`, API yanıtları, `document-read-inventory.json`, `evidence-json-inventory.json`, `fixture_probe.py`, `fixture-results.json`, `metadata_edge_probe.py` ve `metadata-edge-results.json` bulunur. Test verisi sentetiktir, kullanıcı notu değildir. Tam alt araştırma raporu aynı Temp kökünde `avenox-discovery-research.md` dosyasındadır; aşağıdaki kalıcı özet bu dosya olmadan da okunabilir.

### A1 — Vault, sahiplik ve yerel indeks

Aşağıdaki kaynak satırları aksi belirtilmedikçe commit `0be8f9961e3bef7a312735cd7461c66ecdca760a` içindir. Kalıcı GitHub bağlantısı: `https://github.com/avenoxai/avenoxbeyin/blob/<commit>/<dosya>#L<satır>`.

Doğrudan başvuru: [RUNTIME](https://github.com/avenoxai/avenoxbeyin/blob/0be8f9961e3bef7a312735cd7461c66ecdca760a/docs/v3/RUNTIME.md), [MARKDOWN](https://github.com/avenoxai/avenoxbeyin/blob/0be8f9961e3bef7a312735cd7461c66ecdca760a/docs/v3/MARKDOWN.md), [SETUP-V3](https://github.com/avenoxai/avenoxbeyin/blob/0be8f9961e3bef7a312735cd7461c66ecdca760a/SETUP-V3.md), [MIGRATION](https://github.com/avenoxai/avenoxbeyin/blob/0be8f9961e3bef7a312735cd7461c66ecdca760a/docs/v3/MIGRATION.md), [PREFERENCES](https://github.com/avenoxai/avenoxbeyin/blob/0be8f9961e3bef7a312735cd7461c66ecdca760a/docs/v3/PREFERENCES.md), [UPDATE](https://github.com/avenoxai/avenoxbeyin/blob/0be8f9961e3bef7a312735cd7461c66ecdca760a/docs/v3/UPDATE.md).

```text
<vault>/
  beyin.py, .beyin-runtime.json, .beyin-version  # yönetilen giriş/pin/sürüm
  .claude/scripts/beyin_v3*.py                 # yönetilen motor ve CLI
  .agents/skills/<ad>/SKILL.md                 # ortak skill kökü
  .claude/skills/, .kiro/skills/               # skill mirror'ları
  .opencode/plugins/beyin-v3.js                # yönetilen OpenCode adaptörü
  receipts/                                   # kaynak receipt kayıtları
  daily/v3/YYYY-MM-DD.md                       # üretilen görünüm
  knowledge/v3/outcomes.md                     # üretilen receipt indeksi
  notes/, knowledge/, tasks/                  # not kaynakları; zorunlu taksonomi değil
  🔮 850-Companion/                            # mevcut Companion/Echo/Core/Soul düzeni öncelikli
    Core.md, Kurallar.md, Last-Session.md, Threads.md, Journal.md, Arşiv/
  .brain/, custom/                            # unmanaged kullanıcı alanları
  .beyin-note-write/                          # yerel kilit/istek/yedek; git ve bulut dışında
  notion/, agent-out/, .brain-ext/             # bizim önerimiz; avenox otomatik oluşturmaz
```

Obsidian zorunlu değil; kurulum mevcut notları taşımadan yapılabiliyor (`SETUP-V3.md:7–15`). `daily/v3/` insan günlüğü değil receipt projeksiyonudur; `preferences --daily-layout flat` ile `daily/` seçilebilir, insan notunu ezmez (`docs/v3/PREFERENCES.md:11–58`). `Arşiv/` adı tek başına gizlilik veya indeks dışlama sağlamaz. Companion arşivinin `visibility: private` metadatası anlamlıdır (`docs/v3/COMPANION-PARITY.md:121–150`).

Kesin yönetilen dosya listesi kurulu sistemde vault dışındaki `<state>/v3-install.json` içindeki `files` alanıdır. ZIP'teki `manifest.json` farklıdır: ürün payload'ını doğrular. Yönetilen kapsam giriş/motor dosyaları, `beyin`, `beyin-doktor`, `beyin-guncelle` adlı üç çekirdek skill, platform başlatıcıları, `.opencode/plugins/beyin-v3.js`, OMP adaptörü ve desteklenen istemci hook/config'lerinin ilgili bölgeleridir. AGENTS/CLAUDE yönetilen blokları da bu kapsamdadır. Kullanıcının JSON/TOML/blok dışı bölümleri özel merge kurallarıyla korunur; bütün dosyayı serbestçe değiştirmek güvenli değildir (`scripts/install_v3.py:455–456,567–610,751–827`; `docs/v3/RUNTIME.md:57–68`).

Değiştirilmiş yönetilen içerik `Reinstall conflict: managed file changed`; aynı hedefte yabancı içerik `Unmanaged file conflict` üretir. LF/CRLF için istisna var, keyfî düzenlemeler için yok. `.brain/` ve `custom/` updater dışıdır; fakat unmanaged olmak indeks dışı olmak değildir (`docs/v3/UPDATE.md:71–73`; `scripts/install_v3.py:751–769`).

avenox indeksi **vault dışında** `<state>/memory.sqlite3`; Windows varsayılanı `%LOCALAPPDATA%/beyin-v3/<kanonik-vault-yolunun-sha256-ilk16>/`. `.beyin-runtime.json` state pinini taşır. Markdown otoritedir; SQLite kayıt/projeksiyon/audit deposudur, FTS5/embedding hibrit arama değildir. Strict pasaj cache'i `<state>/passages.json`, ayarı `<state>/retrieval.json`; strict bağlamdan `daily/` ve `receipts/` çıkarılır (`template/.claude/scripts/beyin_v3.py:43–52`; `docs/v3/RUNTIME.md:3–5,27–35,45–55`; `docs/v3/PREFERENCES.md:303–326`). Bizim `.brain-ext/index.db` ayrı kalmalı; avenox state'i vault içine taşınmamalı.

### A2 — Tarama, frontmatter ve ölçülen uyumluluk

`--index-exclude-dir NAME` dışlanan **çıplak klasör adına** ekler; `--index-include-dir NAME` bu adı dışlama listesinden çıkarır. Include allowlist/glob değildir, gizli klasörü zorla dahil etmez. Liste `<state>/index.json` içindeki `excluded_dirs`; en fazla 64 ad, yol ayırıcı kabul edilmez. Eşleşme her derinlikte klasör parçasına ve Türkçe harfler dahil case/NFC normalizasyonuna göredir. `notes`, `knowledge`, `tasks` ve companion dışlanamaz. Sonraki sync kayıtları budar, kaynakları silmez. Bozuk exclusion ayarı standart taramaya döner (**fail-open**), privacy sınırı değildir (`docs/v3/PREFERENCES.md:355–375`; `template/.claude/scripts/beyin_v3_index.py:77–192`).

Varsayılan tarama `.md` dosyalarıdır. Gizli yollar, `node_modules`, `receipts`, `__pycache__`, symlink'ler, hassas klasör isimleri ve `AGENTS.md`, `CLAUDE.md`, `SKILL.md`, `INSTRUCTIONS.md` gibi yönerge dosyaları atlanır. Boolean `generated: true` ve `kind: receipt` kaynak not değildir. Sıradan `notion/`, `agent-out/`, `custom/`, `vendor/`, `external/` ve arşiv adları kendiliğinden dışlanmaz (`template/.claude/scripts/beyin_v3_sync.py:283–286,777–869`; `docs/v3/PREFERENCES.md:136–140`). brain-ext'in geniş glob'u avenox'un gizlilik filtreleriyle eşdeğer değildir; kaynak notları indekslerken bu fark açıkça ele alınmalı.

Kanonik frontmatter `---` arasında **JSON object**tir; geçerli YAML da sayılır. Motor tam YAML kütüphanesi değil sınırlı parser kullanır: düz scalar/list ve tek düzey mapping desteklenir; derin YAML, JSON olmayan flow mapping, anchor/tag/multiline gibi biçimler notun dışlanmasına yol açabilir. Bütün header JSON olduğunda nested properties kabul edilir. Pinned `MARKDOWN.md:30` genellemesi tek düzey mapping desteğinin gerisindedir; pinned parser ve 3.7.0 notları bu desteği doğrular (`template/.claude/scripts/beyin_v3_sync.py:97–276`; `docs/v3/releases/3.7.0.md:42–44`).

Unknown not metadata alanları genel olarak korunur; config unknown-key kurallarıyla karıştırılmamalı. Ancak indeks kaydının `source` alanı **vault-relative dosya yoluyla**, `text` gövdeyle değiştirilir. Dosyadaki `source: notion-mirror` marker'ı avenox indeksindeki `record.source` değerinden doğrulanamaz. `last_edited_time` korunur ama `updated_at` recency alias'ı olduğu doğrulanmadı; arbitrary `properties` de otomatik tam arama alanı sayılmaz (`beyin_v3_sync.py:853–856`; `beyin_v3.py:761–828`; `docs/v3/PREFERENCES.md:307`).

**Gerçek v3.12.0 SyncEngine/MemoryStore ile izole Windows fixture sonucu:**

| Vaka | Sonuç |
|---|---|
| `notion/`, scalar mirror metadata, yorumsuz `properties: {}` | İndeksleniyor, bilinmeyen alanlar korunuyor, Türkçe canary bulunuyor |
| Kanonik JSON header ve iç içe Notion properties | Kabul ediliyor, nested veri korunuyor |
| Tek düzey YAML mapping | Kabul ediliyor |
| Derin YAML / `{Durum: Açık}` flow mapping | `unsupported YAML metadata; use JSON frontmatter`; dosya dışlanıyor, sync degraded |
| Brief'teki tam `properties: {}            # veritabanı satırları için` satırı | **Reddediliyor** |
| `.brain-ext/hidden.md`, `notion/AGENTS.md` | İndekslenmiyor |
| `notion/_arsiv/` ve yalnız `archived: true` | **Normal internal bağlamda geliyor** |
| `status: archived` | İndekste var, varsayılan retrieval'da gelmiyor |
| `kind: untrusted` | İndekste var, ordinary context'te gelmiyor |
| Yalnız `untrusted: true` | **Bağlamda geliyor; güven kapısı değil** |
| `visibility: private` | Internal context'te gelmiyor |
| `agent-out/` ve `status: draft` | İndeksleniyor ve normal bağlamda geliyor |
| `exclude NOTİON`, ardından include notion | Kök/nested notion birlikte budanıyor, include sonrası geri geliyor |
| Exclude `notion/subdir`, `notes`, `knowledge`, `tasks` | Beklenen doğrulama hataları |

İlk fixture'da 9 kayıt indekslendi; iki desteklenmeyen YAML uyarısı diğer sağlıklı notları engellemedi. 13 kaynak dosyasının test öncesi/sonrası hash'leri aynı. Bu kaynak koruması ölçümüdür, gerçek kullanıcı vault'u kabul testi değildir.

**A2 hükmü: koşulsuz varsayım yanlış; JSON frontmatter ile koşullu uyum ölçüldü.** `readonly: true` saklanır ama OS veya note-edit yazma kilidi değildir (`template/.claude/scripts/beyin_v3_notes.py:122–127,235–280`). Arşivler için `status: archived` eklemek veya `_arsiv` exclusion'ı seçmek gerekir; ikincisi aynı adlı bütün klasörleri etkiler. Mirror'ın otomatik avenox bağlamına girip girmeyeceği ayrı güven kararıdır. `kind: untrusted` motorun kullandığı bir kapıdır; sıradan `source`/`readonly` marker'ları değildir. `remote_allowed: false` Jev'e aktarımı sınırlar, ana bulut LLM'ini yerel yapmaz; Jev pinned sürümde varsayılan kapalıdır (`beyin_v3.py:210–213,1185–1205`; `docs/v3/JEV.md:62–70,269–288`). Bu keşifte politika uygulanmadı.

### A3 — Kişisel skill, hook ve updater

avenox ortak skill kökü `.agents/skills/<ad>/SKILL.md`; `skill-import --source <seçili-skill-dizini>` yalnız açıkça seçilmiş skill'i alır. Üç skill kökünden birinde aynı isim varsa reddeder; symlink denetimi yapar. `skill-sync` Windows'ta tracked copy, POSIX'te varsayılan symlink kullanır; `<state>/skills.sqlite3` hash state'idir. Aynı anda farklı mirror düzenlemeleri conflict oluşturabilir (`docs/v3/QUICKSTART.md:209–235`; `template/.claude/scripts/beyin_v3_skills.py:87–171`).

**Kişisel `notion-brain` resmî üç skill'le çakışmazsa updater tarafından ürün dosyası olarak değiştirilmez.** Ama `skill-sync` mirror'ları uzlaştırabilir; “hiçbir bileşen dokunmaz” denemez. Tek kaynak ve tek sahiplik yolu seçilmeli. OpenCode V2 `.agents/skills` uyumluluk kökünü de keşfeder; ortak kök seçilirse ayrıca bağımsız `.opencode/skills` kopyası yaratmak zorunlu değildir. Alternatif OpenCode'a özel `.opencode/skills/notion-brain/` da yönetilen beyin adaptöründen ayrıdır. Kural metni için `.brain/notion-brain/RULES.md` unmanaged adaydır, `instructions` ile açıkça yüklenebilir. Şimdilik kopyalama/kurulum yapılmadı.

OpenCode adaptörü `.opencode/plugins/beyin-v3.js` yönetilendir; vault'ta açılınca yüklenir, ayrıca link/enable gerekmez. Vault'u eklenti konumundan, runtime'ı `.beyin-runtime.json`dan bulur; interpreter kurulumda pinlenir, `BEYIN_PYTHON` override'ı vardır. Pinned destek 1.3.4+ 1.x ve 2.x'tir. 2.x prompt/context/tool/compaction hook'ları kullanır; tur başına ilk succeeded/failed/interrupted Stop sayılır. `parentID` taşıyan alt ajanlar atlanır. TUI kapanması tek başına SessionEnd değildir (`docs/v3/OPENCODE.md:3–27`). Gerçek yerel v2.2.5 teslim testi yapılmadı.

Lifecycle adaptörü metadata kuyruğu ve opportunistic detached sync worker kullanır; sürekli genel zamanlayıcı değildir. **Yönetilen hook'u değiştirmeden keyfî `brainext sync` callback API'si doğrulanmadı.** Brief §8.3'teki kural metninden ajan çağrısı fallback'i kullanılabilir; yönetilen `beyin-v3.js` veya beyin skill'i düzenlenmemeli. OpenCode için ayrıca belgelenmiş global bridge varsayılmamalı; global bridge belgesi Claude/Codex/Antigravity içindir (`docs/v3/QUICKSTART.md:244–259`; `docs/v3/GLOBAL-BRIDGE.md:14–34,78–114`).

### doctor ve update

- Kurulu tanı komutu Windows'ta `py -3 <vault>/beyin.py doctor --json`; bu keşifte kullanıcı vault'unda çalıştırılmadı. Kuyruk/lifecycle/hook health, receipt gaps/coverage, runtime pin/yollar, preferences, instruction/skill conflict, companion boyutları, view conflict, strict/hygiene/review/index tanıları raporlanır. Otomatik tamir veya gerçek istemci teslim testi değildir. `observed_metadata` genel “tam sağlıklı” demek değildir; harici OS zamanlayıcılarını denetlemez. Her managed dosyanın hash'ini doğrulayan mekanizmayla karıştırılmamalı (`scripts/beyin_v3.py:1389–1602`).
- `update` varsayılan resmî stable release'i alır, main'i değil. `update --package <zip>` açık paket seçer. `update --check` indirip doğrular ve sentetik paket kodu çalıştırabilir; “sadece metadata” değildir. `--check --metadata-only` paket kodu çalıştırmaz, kurulabilirlik kanıtlamaz.
- Archive path/allowlist/symlink/duplicate/size, schema/runtime/Python, ürün hash'leri, Python derleme ve sentetik preflight kontrol edilir. Uygulamada kilit/backup/journal/managed hash kontrolü vardır, sürüm damgası en son yazılır. Aynı sürüm no-op; downgrade rollback ile olur. Rollback kullanıcı notu geçmişini geri almaz. Hook değişirse istemci güven incelemesi istenir, updater güven onayı üretmez (`docs/v3/UPDATE.md:25–46,60–73,232–277`).
- avenox sürüm bildirimi varsayılan GitHub metadata ağı kullanır. Bütün deneyim için Notion/model-only ağ sözü verilemez; resmî kapatma yolu `preferences --update-notifications off` veya `BEYIN_UPDATES_OFF=1`. Bu keşifte uygulanmadı.

### Okunan belgeler ve sürüm ayrımı

Pinned `docs/v3/` altındaki **49 md/txt belgenin tamamı**, kök `README.md` (1–167) ve `SETUP-V3.md` (1–34) okundu. `SETUP-V3.md` `docs/v3/` altında değil repo kökündedir. Pinned tam envanter, parantez içinde son satır:

```text
BASELINE.md (49)                      COMPANION-PARITY.md (191)
decision-quality/PLAN.md (28)         decision-quality/REVIEW.md (144)
GLOBAL-BRIDGE.md (181)                HERMES.md (134)
INGEST-SERVER.md (120)                issue-validation.md (51)
JEV.md (374)                         KIRO.md (60)
LIVE-CLIENTS.md (54)                  local-runtime-architecture.md (41)
MARKDOWN.md (74)                     MIGRATION.md (249)
MULTI-MACHINE.md (326)                OMP.md (55)
OPENCODE.md (27)                     parity-and-migration.md (45)
PLATFORM-TESTS.md (124)               PREFERENCES.md (406)
PRODUCTIZATION-PLAN.md (62)           public-architecture.md (21)
QUICKSTART.md (299)                  README.md (42)
releases/3.1.0.md (50)                releases/3.2.0.md (74)
releases/3.2.1.md (31)                releases/3.3.0.md (57)
releases/3.4.0.md (70)                releases/3.5.0.md (90)
releases/3.5.1.md (36)                releases/3.6.0.md (92)
releases/3.7.0.md (76)                releases/3.7.1.md (36)
releases/3.8.0.md (89)                releases/3.8.1.md (53)
releases/3.9.0.md (56)                releases/3.10.0.md (73)
releases/3.11.0.md (144)              releases/3.12.0.md (85)
RUNTIME.md (111)                     SEMANTIC-TEST-CONTRACT.md (9)
SERAI-PATTERNS.md (27)                THIRD-PARTY-JEV.txt (26)
UPDATE.md (277)                      USAGE-REPORT.md (31)
WINDOWS-CAPTURE-ABI.md (378)          YAKALA-GUVENLIK-299.md (39)
YAKALA.md (550)
```

Araştırma anındaki main `36f8a75b0981be7de4f607b6cf9584c608a1750c`, pinned'den 189 commit ileride. Main'deki iki yeni belge `CHAT-TRACE.md` (84 satır), `MODULE-BOUNDARIES.md` (71 satır) tam okundu. Değişen dokuz metnin diff'leri incelendi: `COMPANION-PARITY`, `INGEST-SERVER`, `MARKDOWN`, `MIGRATION`, `PREFERENCES`, `QUICKSTART`, `README`, `RUNTIME`, `YAKALA`; diğer 40 belge aynı blob. Main'deki chat-trace, ortak note-write kilidi genişlemeleri ve sync sağlamlaştırmaları v3.12.0 özelliği diye sunulmadı; main motoruyla test yapılmadı. Eski issue-validation dokümanındaki “OpenCode desteklenmiyor” ifadesi tarihsel tabana aittir, pinned OPENCODE/release kanıtının yerine geçmez.

Ayrıca aynı 20 JSON kanıt dosyası envanterlendi ve JSON sözdizimi doğrulandı; içerdiği tarihsel deneyler tekrar çalıştırılmış sayılmadı:

```text
decision-quality/evidence/review-baseline.json
decision-quality/evidence/review-changed.json
decision-quality/evidence/review-frozen-retrieval.json
evidence/desktop-workflow.json
evidence/live-clients.json
evidence/native-ci.json
evidence/offline-final.json
evidence/preferences-20260917.json
evidence/product-acceptance-contract.json
evidence/product-live-clients.json
evidence/product-native-ci.json
evidence/product-offline-final.json
evidence/product-release-fixes-final.json
evidence/product-windows-path-fix.json
evidence/release-asset.json
evidence/semantic-evaluation.json
evidence/verification.json
issue-evidence.json
pr20-health-evidence.json
receipt-conflict-evidence.json
```

Yollar `docs/v3/` görelidir. Dosya başına hash/satır/bayt bilgileri kanıt dizinindeki iki envanter JSON'undadır; indirilen belge blob'ları GitHub tree hash'leriyle doğrulandı.

## 3. OpenCode V2: A4

Kaynaklar: [Config](https://opencode.ai/v2/docs/config), [MCP servers](https://opencode.ai/v2/docs/mcp-servers), [Permissions](https://opencode.ai/v2/docs/permissions), [Instructions](https://opencode.ai/v2/docs/instructions), [Skills](https://opencode.ai/v2/docs/skills). Context7 üzerinden de V2 MCP izin eşlemesi doğrulandı.

Yerel sürüm kontrolü: `opencode --version` → `opencode v2.2.5`. Dolayısıyla bu makine için V2 sözleşmesi seçildi; V1 belgeleriyle karıştırılmadı.

| Konu | Doğrulanmış V2 biçimi |
|---|---|
| Dosya | Proje `opencode.json` / `opencode.jsonc` veya `.opencode/opencode.json(c)`; kullanıcı `~/.config/opencode/opencode.json(c)` |
| MCP | `mcp.servers.<server>`; doğrudan `mcp.<server>` değil |
| Uzak sunucu | `type: "remote"`, `url`; OAuth varsayılan açık |
| Yerel sunucu | `type: "local"`, `command` dizisi; isteğe bağlı `cwd`, `environment` |
| Devre dışı bırakma | `disabled: true`; yeni V2 örneğinde `enabled` kullanılmaz |
| İzinler | `permissions` dizisi; her öğe `action`, `resource`, `effect` içerir |
| Etkiler | `allow`, `ask`, `deny`; son eşleşen kural kazanır |
| MCP izin adı | Normalize edilmiş `<server>_<tool>`; resource `*` |
| Kurallar | `instructions` dosya/glob/URL dizisi; `AGENTS.md` yanında yüklenir |
| Skill | `<vault>/.opencode/skills/notion-brain/SKILL.md`; avenox ortak kökü `.agents/skills/notion-brain/SKILL.md` de V2 uyumluluk keşfinde; tek kaynak seçilmeli |
| Ek skill kaynakları | `skills` dizisi; göreli yollar aktif çalışma dizinine göre çözülür |
| Shell/alt ajan | V2 eylemleri `shell`, `subagent`; V1 `bash`, `task` değil |

**A4 hükmü: brief'teki tekil `permission` anahtarı V2 için yanlış/eski.** Yeni taslak V2 yerel biçimini kullanmalı. V1 uyumluluğunun bulunması, yeni yapılandırmayı V1 biçiminde üretme gerekçesi değildir.

Sunucu `notion` adını alırsa izin eylemleri örneğin `notion_notion-search`, `notion_notion-fetch`, `notion_notion-create-pages` olur. MCP'nin ham `notion-search` adıyla OpenCode izin eylemini karıştırmamak gerekir; OAuth sonrası gerçek katalog doğrulanmalı. Code Mode içindeki çağrılar da alt aracın izin kontrolüne tabidir.

Gelecekteki güvenli izin yaklaşımı: önce `notion_*` için `ask`; sonra yalnızca doğrulanmış `notion_notion-search` ve `notion_notion-fetch` için `allow`. Böylece yeni eklenen yazma araçları onaysız açılmaz. **Bu rapor çalışan yapılandırma dosyası oluşturmaz.**

`ask` bir sandbox veya değişmez “her seferinde onay” garantisi değildir: OpenCode'da kullanıcı “Allow always” seçerse proje kapsamlı kalıcı izin oluşabilir. Yazma araçlarında yalnız tek seferlik onay kullanılmalı; mevcut geniş izinler/saklı onaylar entegrasyon testi sırasında gözden geçirilmeli. Bu keşifte mevcut izin dosyaları veya onay kayıtları okunmadı/değiştirilmedi.

Notion adresi `https://mcp.notion.com/mcp`. Yetkilendirme kullanıcı arayüzünde `/mcps` üzerinden yapılmalı; integration token bu bağlantıya kopyalanmaz. Bu oturumda OAuth başlatılmadı.

## 4. Notion Markdown API: A5

Kaynaklar: [Markdown kılavuzu](https://developers.notion.com/guides/data-apis/working-with-markdown-content.md), [Retrieve page markdown](https://developers.notion.com/reference/retrieve-page-markdown.md), [Versioning](https://developers.notion.com/reference/versioning.md), [Notion-flavored Markdown](https://developers.notion.com/guides/data-apis/notion-flavored-markdown.md).

**A5'in temel uç noktaları doğrulandı:**

- `GET /v1/pages/{page_id}/markdown`.
- `PATCH /v1/pages/{page_id}/markdown`.
- `POST /v1/pages`, gövdede `markdown`; `children`/`content` ile birlikte gönderilmez.
- Doğrulanan başlık `Notion-Version: 2026-03-11`. Retrieve endpoint'in yayımlanmış OpenAPI parametresi bu değeri açıkça listeliyor. Genel versioning sayfasındaki `{latestApiVersion}` şablonu tek başına kanıt alınmadı.
- GET yanıt alanları: `object: "page_markdown"`, `id`, `markdown`, `truncated`, `unknown_block_ids`.
- Senkron PATCH yanıtı ayrıca opsiyonel `warnings: [{code, message}]` taşıyabilir. Kısmen eşleşmeyen düzenlemeler HTTP başarısına rağmen `no_match` uyarısı üretebilir; görmezden gelinmemeli.
- PATCH tüm içeriği değiştirmek için `type: "replace_content"`, `replace_content.new_str`; hedefli düzenleme için `type: "update_content"`, `update_content.content_updates` kullanır. Sadece ham `markdown` gönderileceği varsayılmamalı.
- Çocuk sayfa/database silmeye yol açan değişiklik varsayılan olarak reddedilir. `allow_deleting_content: true` açmak bu korumayı kaldırır; bu projenin varsayılan senkron/yazma akışında açılmamalı.

### Markdown sürümü ve eksik içerik

`Notion-Version` ile **Markdown sözdizimi sürümü aynı şey değildir**. Şu anda Markdown `v1` varsayılan ama deprecated; resmî öneri `v2`.

- GET: `?markdown_version=v2`.
- POST ve PATCH: gövdede `markdown_version: "v2"`.
- Brief'te olmayan bu seçim açıkça sabitlenmeli; parser v1/v2 biçimlerini karıştırmamalı.

Yaklaşık 20 bin blok/record sınırı veya erişim eksikliği `<unknown .../>` ve `unknown_block_ids` üretebilir. Kimlikleri aynı GET endpoint'ine `page_id` olarak vererek alt ağaç okunabilir. Erişilemeyen kimlik `404 object_not_found` dönebilir; bu yanıt silinme kanıtı değildir. Tekrarlanan kimlikler ziyaret kümesiyle sınırlanmalı; içerik mümkünse yerindeki placeholder'a konmalı, körlemesine sona eklenip sıra/tekrar bozulmamalı. Tamamlanamayan içerik brief'teki eksik-blok yorumu ve kısmi başarıyla raporlanmalı. Desteklenmeyen bloklar için block API fallback'i gerekebilir. Görüşme transcript'i varsayılan olarak dahil değildir; “tam içerik” denirken bu sınır belirtilmeli.

### Bağlantı biçimleri: belge örneği, canlı workspace çıktısı değil

Aşağıdakiler resmî v2 sözdizimi referansından alınmış şekillerdir; gerçek kullanıcı sayfasından çekilmiş veri değildir:

```text
[text](url)
<mention url="...">Label</mention>
<page url="..." color="...">Title</page>
<database url="..." data-source-url="...">Title</database>
<folder url="...">Title</folder>
```

Versioning belgesi üretilen URL'lerin Haziran 2026'da `https://www.notion.so/{page-id}` biçiminden `https://app.notion.com/p/{page-id}` biçimine geçtiğini, URL yapısının kararlı kimlik olmadığını söylüyor. Kimlik kaynağı page/data source nesnesinin `id` alanıdır. Grafik parser'ı yalnız eski `notion.so` URL regex'ine dayanmamalı; kayıtlı `id`–`url` eşlemesi kullanılmalı, bilinmeyen link çözülmemiş bırakılmalı. XML mention ve child-page etiketleri de hesaba katılmalı.

**Bekleyen:** token ve test workspace kullanılmadığı için gerçek Markdown/link fixture'ı yok. Graf ayrıştırıcısının uygulamasından önce kullanıcı onaylı test sayfasının gerçek GET çıktısıyla bu kapı kapatılmalı.

## 5. Notion ağaç ve data source modeli: A6

Kaynaklar: [Working with databases](https://developers.notion.com/guides/data-apis/working-with-databases.md), [Query a data source](https://developers.notion.com/reference/query-a-data-source.md), [Block children](https://developers.notion.com/reference/get-block-children.md), [Search limitations](https://developers.notion.com/reference/search-optimizations-and-limitations.md).

**Model doğrulandı:** database bir kapsayıcıdır; `data_sources` dizisindeki her kaynak ayrı ID ve şemaya sahiptir. Satırlar page nesneleridir; üstleri `parent.type: "data_source_id"` taşır. Bir database ID'yi doğrudan data source ID yerine kullanmak yanlış olur. `POST /v1/data_sources/{id}/query` ile satırlar sayfalanır. Agent Workspace database olacaksa hedef data source seçimi ve title property'si şemadan belirlenmelidir.

Önerilen sınırlı keşif yöntemi (henüz uygulanmadı):

1. Brain kökünden başlayıp `GET /v1/blocks/{id}/children` ile çocukları, gerektiğinde iç içe kapsayıcıları ve cursor'ları gez; `child_page` ve `child_database` kimliklerini kaydet.
2. Database için `data_sources` listesini al; her data source'u sayfala. Wiki sonuçları page **veya** data source olabilir; tür kontrolü gerekir.
3. İçerik Markdown endpoint'inden; metadata/properties sayfa nesnesinden alınır. `last_edited_time` değişmeyen sayfanın içeriği atlanabilir ama yeni çocukların keşfi atlanamaz.
4. Data source için `last_edited_time` filtreli artımlı sorgu kullanılabilir. Normal sayfa ağacını kapsayan garantili bir delta/list-all endpoint'i doğrulanmadı; kökün zaman damgası bütün torunların değişimini garantilemez.
5. Sadece eksiksiz ve başarılı kapsam taramasından sonra kaybolan sayfaları değerlendir. 403/404, eksik sayfalama, ağ hatası veya değişen paylaşım durumunda toplu arşivleme yapma.

`POST /v1/search` başlık aramasıdır, indeks gecikmelidir ve erişilebilir içeriğin eksiksiz envanterini garanti etmez. Ne Brain alt ağacının güvenilir listesi ne de “yalnız bu iki köke paylaşılmış” iddiasının kesin kanıtıdır. `doctor` görünür beklenmeyen içerik için **uyarı** verebilir; paylaşımın tamlığını garanti edemez. Linked database'e erişmek için özgün database'in paylaşılması gerekir; linki takip etmek içeriğin Brain altında sahiplenildiği anlamına gelmez. Kapsam dışı hedefler otomatik çekilmemeli.

Query yanıtında `results`, `next_cursor`, `has_more` okunur; `request_status.type: "incomplete"` varsa sonuç tam değildir. Güncel belge sorgu başına 10000 sonuç tavanı bildiriyor. Sessizce “tamamlandı” sayılmaz; bu büyüklükte zaman aralığıyla bölme gerekir. Büyük relation/rollup değerleri ayrıca property pagination isteyebilir; ilk page nesnesindeki properties her durumda eksiksiz değildir.

**A6 hükmü:** data source modeli doğru; tek ucuz genel aramayla eksiksiz artımlı senkron varsayımı desteklenmiyor. K1'de “ikinci pull hiçbir şey indirmez”, **içerik indirmez ama keşif/metadata HTTP istekleri yapabilir** diye açıklanmalı.

## 6. Hız sınırları ve güvenli retry: A7

Kaynaklar: [Request limits](https://developers.notion.com/reference/request-limits.md), [MCP rate limits](https://developers.notion.com/guides/mcp/rate-limits.md).

**A7 kısmen doğru, evrensel hali yanlış:**

- Business/Enterprise: bağlantı başına 600 istek/dakika, ortalama 10/s.
- Diğer planlar: 180 istek/dakika, ortalama 3/s.
- Data source query ayrıca yaklaşık 3/s/connection sınırına sahip.
- Paylaşılan workspace bütçesi de var; tek istemci sınırın altında olsa bile 429 alabilir.
- `Retry-After` tam saniye; gerçek değer izlenmeli. `additional_data.rate_limit_reason` sınır türünü bildirir.
- 529 `service_overload` için de Retry-After uygulanır. 429 `public_api_request_blocked` tekrar denenmemeli.

Brief'teki 2.5/s muhafazakâr başlangıç olarak kalabilir. “Bütün 5xx yanıtlarını aynı biçimde yeniden dene” kuralı ise **güvenli değil**: POST oluşturma başarılı olup yanıt 503 dönebilir. `additional_data.retry_guidance`, varsa `committed_resource_id` okunmalı; tekrar yazmadan önce durum doğrulanmalı. Yerel `notion_id` henüz kaydedilmeden bağlantı kesilirse yalnızca bu alanın varlığını kontrol etmek push idempotentliği sağlamaz. Belirsiz oluşturma sonucunda kör POST tekrarı yerine uzlaştırma veya kullanıcıya açık belirsiz durum gerekir.

Hosted MCP güncel belgesi standart API sınırlarına gönderme yapıyor. Brief'teki sabit “180/dakika; arama 30/dakika” sözü güncel resmî sayfada doğrulanamadı; sabit SLA gibi yazılmamalı. MCP 2 saniye veya daha kısa beklemeyi bir kere deneyebilir, aksi durumda `structuredContent.error` içinde `rate_limited`, `retry_after_seconds`, `rate_limit_reason` döndürür. Paralel aramayı sınırlama kuralı korunmalı.

## 7. Hosted MCP araçları

Kaynak: [tam resmî araç tablosu](https://developers.notion.com/guides/mcp/tools-faqs.md), [bağlantı/OAuth](https://developers.notion.com/guides/mcp/get-started-with-mcp.md).

Brief'teki `notion-search`, `notion-fetch`, `notion-create-pages`, `notion-update-page`, `notion-create-comment`, `notion-move-pages`, `notion-duplicate-page`, `notion-create-database` doğrulandı. **`notion-update-database` güncel tabloda yok; `notion-update-data-source` var.** Araç erişimi plan, connection capability ve yönetici ayarına bağlı; OAuth sonrası gerçek `tools/list` ayrıca kontrol edilmeli. Resmî tablo bazı OpenAI istemcilerinde search/fetch adlarının değişebildiğini de bildiriyor; yalnız model sağlayıcısından hareketle bu OpenCode oturumundaki ad tahmin edilmemeli.

Güncel resmî envanter (bu proje yalnız gerekli alt kümeyi kullanacak):

```text
notion-ai-search
notion-calendar-cancel-events
notion-calendar-create-events
notion-calendar-list-calendar-resources
notion-calendar-list-calendars
notion-calendar-list-contacts
notion-calendar-list-coworkers-events
notion-calendar-list-events
notion-calendar-update-events
notion-connector-search
notion-convert-page-to-skill
notion-create-attachment
notion-create-comment
notion-create-database
notion-create-file-upload
notion-create-folder
notion-create-pages
notion-create-suggested-edit
notion-create-view
notion-delete-comment
notion-delete-databases
notion-delete-pages
notion-download-attachment
notion-download-skill
notion-duplicate-page
notion-fetch
notion-get-async-task
notion-get-comments
notion-get-enabled-skills
notion-get-file-download-urls
notion-get-groups
notion-get-self
notion-get-session-status
notion-get-suggested-edit
notion-get-teams
notion-get-tool-access
notion-get-users
notion-get-version-changes
notion-list-favorite-pages
notion-list-page-backlinks
notion-list-private-pages
notion-list-recent-pages
notion-list-session-events
notion-list-shared-pages
notion-memory-search
notion-move-pages
notion-query-data-sources
notion-query-meeting-notes
notion-query-multiple-data-sources
notion-query-sessions
notion-read-session-event
notion-resolve-suggested-edit
notion-restore-pages
notion-search
notion-search-agents
notion-search-sessions
notion-send-message-to-session
notion-set-comment-reaction
notion-set-discussion-resolved
notion-spawn-session
notion-stop-session
notion-update-comment
notion-update-data-source
notion-update-enabled-skills
notion-update-folder
notion-update-page
notion-update-view
notion-upload-skill
notion-view-version
notion-wait-session
```

Yeni araçları eklemek kapsam değildir. Özellikle `notion-memory-search` ile ikinci bir kalıcı hafıza sistemi, custom agent, takvim veya skill import akışı kurulmayacak. Yeni yazma araçları broad `ask` kuralı arkasında kalmalı. İzin modeli araç düzeyindedir; `ask` veya kural metni tek başına Agent Workspace'e sunucu taraflı yazma izolasyonu sağlamaz. Kesin hedef doğrulaması CLI'da gerekir; hosted MCP tarafında kullanıcı her yazma onayında hedefi kontrol etmelidir.

## 8. FastEmbed ve Türkçe: A8

Kaynaklar: [Supported Models](https://qdrant.github.io/fastembed/examples/Supported_Models/), [v0.9.1 pooled model kayıtları](https://github.com/qdrant/fastembed/blob/v0.9.1/fastembed/text/pooled_embedding.py), [v0.9.1 temel embed uygulaması](https://github.com/qdrant/fastembed/blob/v0.9.1/fastembed/text/text_embedding_base.py), [MiniLM model kartı](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2), [E5 model kartı](https://huggingface.co/intfloat/multilingual-e5-large).

| Desteklenen model kimliği | Kayıtlı boyut | Vektör boyutu | Kayıtlı giriş sınırı | Önek | Lisans |
|---|---:|---:|---:|---|---|
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | 0.22 GB | 384 | 128 token | Gerekmiyor | Apache-2.0 |
| `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` | 1.00 GB | 768 | 512 token | Gerekmiyor | Apache-2.0 |
| `intfloat/multilingual-e5-large` | 2.24 GB | 1024 | 512 token | `query: ` / `passage: ` | MIT |

Boyutlar FastEmbed'in `size_in_GB` metadatasıdır, bu makinede ölçülmüş indirme/RAM miktarı veya hız değildir. Model/tokenizer ek dosyaları ve cache disk alanı değişebilir. Türkçe MiniLM model kartında açıkça `tr` dilidir; E5 yaklaşık 100 dili kapsar ve Türkçe sonuçları model kartında bulunur. Bu, kullanıcının notlarında Türkçe retrieval kalitesinin ölçüldüğü anlamına gelmez.

E5-small/base gibi aile üyelerinin varlığı onların FastEmbed'de hazır destekli olduğunu kanıtlamaz; burada doğrulanan hazır E5 adayı `intfloat/multilingual-e5-large`dır. E5 önekleri İngilizce olmayan metinlerde de aynen gerekir. Pooled uygulamanın `query_embed`/`passage_embed` temel metotları sadece `embed`e yönlendirir; bunları çağırmak otomatik önek eklendiği anlamına gelmez.

**Başlangıç seçimi:** küçük yerel CPU kullanımı için MiniLM, 384 boyut, yaklaşık 0.22 GB; gerekçe ve sınırlar [DECISIONS.md](DECISIONS.md)'de. Kullanıcı onayı ve gerçek eval sonrasına kadar geçici öneridir. Brief'teki 2000 karakter sınırı 128 token garantilemez: başlık dahil tokenizer bütçesi gözetilmeli; sessiz kırpılma kabul edilmemeli. Token bütçesini aşan bölünmez kod bloğunun FTS'de tam saklanıp semantik kapsamının eksik olduğunun raporlanması gerekir; “kod bloğunu bölme” kuralıyla çelişki gizlenmemeli.

Bu makinede `fastembed` kurulu değil; `TextEmbedding.list_supported_models()` yerelde çağrılmadı. Resmî tablo ve sabit sürüm kayıtları incelendi; model indirilmedi, embedding üretilmedi, Türkçe recall/MRR ölçülmedi.

## 9. Yerel Python ve SQLite: A9

Gerçek çalıştırma: Windows PowerShell, `py -3`.

```text
Python: 3.14.6 (64 bit, AMD64)
Executable: C:\Python314\python.exe
Platform: Windows-11-10.0.26300-SP0
SQLite: 3.50.4
CREATE VIRTUAL TABLE fts_probe USING fts5(text): başarılı
INSERT ve MATCH 'bilgi': 1 satır döndü
hasattr(connection, 'enable_load_extension'): true
enable_load_extension(True): OK
enable_load_extension(False): OK
fastembed: kurulu değil
sqlite_vec: kurulu değil
numpy: kurulu
```

Çalıştırılan temel kontrolün eşdeğer, kopyalanabilir biçimi (yalnız RAM'de DB oluşturur):

```powershell
@'
import sqlite3, sys
connection = sqlite3.connect(':memory:')
connection.execute('CREATE VIRTUAL TABLE probe USING fts5(text)')
connection.execute('INSERT INTO probe VALUES (?)', ('bilgi',))
assert connection.execute("SELECT count(*) FROM probe WHERE probe MATCH 'bilgi'").fetchone()[0] == 1
print(sys.version)
print(sqlite3.sqlite_version)
connection.enable_load_extension(True)
connection.enable_load_extension(False)
print('FTS5 ve extension toggle: OK')
'@ | py -3 -
```

İlk testte terminal Türkçe satırı bozuk kodlamayla gösterdi; FTS sonucu döndü. Bu bir Türkçe arama kalite/normalizasyon testi olarak sayılmadı.

**A9 hükmü:** seçili Python yorumlayıcısında FTS5 mevcut, extension loading açılabiliyor. Ancak gerçek sqlite-vec DLL yükleme/sorgulama **denenmedi**; “sqlite-vec backend çalışıyor” sonucu çıkarılamaz. Paket kurulumu onayı sonrası izole proje ortamında yükleme, `vec_version()` ve küçük vektör sorgusu test edilmeli; başarısızsa brief'teki numpy yedeği kullanılmalı.

Ek ön kontrol: PyPI JSON metadatasından FastEmbed 0.9.1 (`>=3.10`), ONNX Runtime 1.31.1 (`>=3.11`, cp314 Windows AMD64 wheel mevcut), sqlite-vec 0.1.9 (Windows AMD64 wheel mevcut), tokenizers 0.23.3 görüldü. Bu sadece dağıtım metadatasıdır; tüm bağımlılıkların Python 3.14'te kurulup çalışacağı test edilmedi. Kaynaklar: `https://pypi.org/pypi/<paket>/json`. Hiçbiri bu keşifte kurulmadı.

## 10. Tarifte ayrıca açıklığa kavuşturulması gereken sınırlar

1. **Gizlilik çelişkisi:** yerel embedding ile “hiçbir not içeriği üçüncü tarafa gönderilmez” aynı güvence değildir. `brainext search` snippet'leri veya MCP fetch sonuçları bu bulut LLM oturumuna alındığında model sağlayıcısına gider. Hosted MCP de `mcp.notion.com`a bağlanır. Kullanıcının “yerel toplu indeks/embedding, yalnız seçilmiş kaynak parçaları ajan bağlamına” sınırını açıkça kabul etmesi veya tümüyle yerel model kullanması gerekir. Mutlak gizlilik garantisi uydurulmamalı.
2. **Ağ kapsamı:** `api.notion.com` + ilk model indirmesi CLI veri düzlemi için hedef olabilir; kurulum/güncellemede GitHub/PyPI, hosted MCP'de `mcp.notion.com` ve OAuth uçları da gerekir. Ayna içindeki dosya/medya URL'lerini kendiliğinden indirmek ayrıca kapsam/ağ izni gerektirir; varsayılan metin aynasıyla sınırlı kalınmalı.
3. **Üzerine yazma:** genel “her overwrite öncesi onay” ile pull'ın rutin güncellemeleri arasında sınır belirlenmeli. Yalnız araca ait, hash'i eşleşen mirror dosyalarını güncelleme açık kapsamlı senkron onayına dayanmalı; kullanıcı düzenlemesini `--force` ile ezmek ayrıca açık onay ister. Brief bu keşifte değiştirilmedi.
4. **Salt okunur frontmatter izin değildir:** `readonly: true` ve `source: notion-mirror` kaynak metadatasıdır, prompt injection'a karşı güvenlik sınırı değildir. Okunan içerik talimat olarak izlenmemeli; indeksleme kapsamı ile ajan bağlamına otomatik alınabilirlik ayrı değerlendirilmelidir.
5. **Hibrit kabul ölçütü:** RRF'nin her sorguda en iyi tek moddan kötü olmaması matematiksel garanti değildir. K6 sonuçları gerçek eval setinde ölçülmeli; kötüleşirse raporlanmalı, varsayımla “geçti” sayılmamalı.

### Keşif çıktısının doğrulaması

- Ana oturumda fixture'lar yeni ve tekil sentetik vault/state adlarıyla yeniden çalıştırıldı; tüm assert'ler geçti. `fixture-results-verify-d411777c47.json`: 46 manifest hash'i, 46 pinned blob eşleşmesi, 0 fark, kaynak baytları değişmedi. `metadata-edge-results-verify-d411777c47.json`: brief'in yorumlu properties satırı reddedildi, nested JSON kabul edildi, yalnız `untrusted: true` taşıyan içerik bağlamda geldi. Kanıt dosyaları Bölüm 2'deki Temp dizinindedir.
- Aynı doğrulamada recursive GitHub tree envanterine karşı her belge blob'u tekrar denetlendi: pinned 49 metin + 20 JSON, main 51 metin + 20 JSON; UTF-8/JSON ve hash kontrolleri geçti. Resmî ZIP SHA-256 yeniden doğrulandı. Bunlar tam proje test paketi/installer/update kabul testi değildir.
- Resmî MCP FAQ tablosu programatik olarak okundu; bu rapordaki 70 ham araç adıyla küme eşitliği kontrolü geçti (`Official hosted MCP inventory: 70 names; report exact set match: OK`). Bu, OAuth yapılmış bağlantının aynı araçlara erişebildiği anlamına gelmez.
- Raporların UTF-8 okunabilirliği, yerel Markdown bağlantıları ve kod bloğu çitlerinin dengesi denetlendi.
- RAM içi FTS5 INSERT/MATCH ve extension aç/kapat assert kontrolü çıkış kodu 0 ile geçti; proje test paketi henüz yok ve çalıştırılmış sayılmadı.

## 11. Keşif Özeti

| Varsayım | Sonuç | Uygulamaya etkisi |
|---|---|---|
| A1 | Pinned release, manifest, vault/runtime ve 49 belge doğrulandı | Kaynaklar, üretilen görünümler ve yönetilen dosyalar ayrı; kod vault dışında |
| A2 | Koşulsuz varsayım yanlış; JSON metadata ile fixture uyumu geçti | Yorumlu/derin YAML'dan kaçın; arşiv/güven politikasını düzelt; gerçek vault testi bekliyor |
| A3 | Kişisel skill updater'dan ayrı; keyfî callback doğrulanmadı | Tek skill kaynağı; yönetilen hook'a dokunma; oturum çağrısını kural fallback'iyle tasarla |
| A4 | V2 anahtarları doğrulandı; brief'teki `permission` yanlış/eski | `permissions`, `mcp.servers`, gerçek tool action adları |
| A5 | Temel endpoint/sürüm/alanlar doğru; Markdown v2 ek ayrım gerekli | `markdown_version=v2`, unknown/warnings işleme; gerçek link fixture bekliyor |
| A6 | Data source modeli doğru; eksiksiz search/delta varsayımı geçersiz | Kökten kapsamlı keşif, pagination; eksik taramada arşivleme yok |
| A7 | 3/s evrensel değil; Retry-After doğru | Plana/endpoint'e bağlı limit, 529, güvenli yazma retry/uzlaştırma |
| A8 | Çok dilli adaylar resmî listede doğrulandı | Geçici MiniLM seçimi; 128 token bütçesi; eval bekliyor |
| A9 | FTS5 ve extension toggle yerelde geçti | Gerçek sqlite-vec yükleme ve semantik kurulum bekliyor |

**Faz kapısı:** Yanlış/eski varsayımlara dayanarak kod yazılmadı. Faz 1, entegrasyon kurulumu ve kullanıcı verisine erişim başlamadı. Kullanıcı onayı gelmeden başlamayacak. Açık canlı kontroller tamamlanmış gibi sunulmayacak.
