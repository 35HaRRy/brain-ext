# Shared Memory / Project Mapping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bütün yerel OpenCode oturumlarında ortak vault'un genel tercihlerini ve yalnız doğrulanmış etkin projenin hafızasını kullanmak.

**Architecture:** `brain-ext` içinde bağımsız bir Python entegrasyonu yerel eşlemeleri ve mevcut Beyin runtime erişimini yönetir. İnce OpenCode V2 eklentisi oturum konumunu doğrular, bu yardımcıyla JSON/stdin üzerinden konuşur, kapsamlı bağlam ve araçlar sunar. Yönetilen Beyin dosyaları değişmez; tek bağlam üreticisi doğrulanmadan global etkinleştirme yapılmaz.

**Tech Stack:** Python >=3.11, kurulu PyYAML, pytest/Ruff; Node.js yerleşik modülleri ve OpenCode V2 plugin API. Yeni servis, model, veritabanı veya npm runtime bağımlılığı yok.

**Spec:** `docs/superpowers/specs/2026-11-13-shared-memory-project-mapping-design.md` (kullanıcı onaylı).

## Global Constraints

- Global OpenCode adaptörü kullanılacak; bütün oturumlarda etkin olacak. Diskin tamamı taranmayacak.
- Proje tanımlanmasa da genel tercihler kullanılacak; proje kayıtları yüklenmeyecek.
- Bir Git deposunun frontend/backend dahil bütün alt klasörleri tek proje hafızasını kullanacak.
- Başka projelerin içeriği yalnız açık kullanıcı isteğiyle aranacak.
- Makine eşlemeleri `%LOCALAPPDATA%\brain-ext\shared-memory\` altında sürümlü JSON dosyasında tutulur.
- Yönetilen dosya onaysız değiştirilmez. Desteklenen konfigürasyonla tek üretici sağlanamıyorsa global etkinleştirme durur.
- Yeni görev ve görev durum değişikliği için doğrudan talimat veya öneriye onay gerekecek.
- Hata loglarında not gövdesi, ilk kullanıcı mesajı, token veya `.env` içeriği bulunmaz.
- Proje depolarına, global AGENTS.md'ye veya yönetilen vault dosyalarına zorunlu yazma yapılmaz.
- Mevcut `brainext` Notion CLI/config semantiği korunur. `.env`, OAuth ve model ayarları bu işte okunmaz/değiştirilmez.
- Kullanıcının untracked `docs/BRIEF-EK-1-KESIF-SONRASI.md` ve `docs/NOTION-BRAIN-AGENT-BRIEF.md` dosyalarına dokunma/stage etme.

## Review Focus

- Yeniden açılan veya başka dizine taşınan oturum önceki projenin enjekte edilmiş katmanını taşımamalı; geçmiş transkriptin kalması ayrıca bildirilmeli (Task 5).
- İki OpenCode instance'ı aynı kökü farklı projeye eşlerken yalnız biri başarılı olmalı, diğerinin yazması eski kaydı ezmemeli (Task 2).
- Etiketsiz eski Companion/knowledge/receipt içeriği genel tercihler diye sızmamalı; eksik metadata sorgu kapsamını genişletmemeli (Task 3).
- Project.md oluşup eşleme yazması başarısız olduğunda yeniden deneme aynı projeyi tamamlamalı, yeni proje üretmemeli (Task 4).
- Yerel yönetilen eklenti global adaptörle birlikte yüklenince çift bağlam oluşmamalı; sessiz hook hatası başarılı kurulum sayılmamalı (Task 1 ve 6).

---

## Dosya sınırları ve ortak protokol

Yeni kod `src/brainext/shared_memory/` altında: `registry.py` yol/eşleme, `runtime.py` Beyin uyum katmanı ve kapsamlı erişim, `service.py` oturum bağlamlı işlemler, `__main__.py` tek JSON isteği/yanıtı. `__init__.py` paket işaretidir. Eklenti `integrations/opencode/shared-memory/index.js`, testleri aynı dizindeki `index.test.mjs`; kurulum rehberi `docs/SHARED_MEMORY_SETUP.md`.

`pyproject.toml` ve mevcut `cli.py` için yeni entry point gerekmez. Eklenti kurulu venv Python'unu `-m brainext.shared_memory` ile çağırır; yollar config options'tan gelir. Kaynak repo içindeki eklenti dizini OpenCode config'e mutlak yol olarak eklenir; wheel'in JS dosyasını içerdiği iddia edilmez.

Tek istek: `{version:1, action, session:{id,directory,parent_id}, payload:{...}}`. Vault/registry/Python yolları güvenilir kurulum seçeneklerinden, oturum bilgisi plugin API'den gelir; model araç argümanları bunları değiştiremez. Yanıt: `{version:1,status,mode,project,context,records,warnings,result}`; `status=ok|conflict|unavailable|invalid`, `mode=project|general|disabled`. `project` kimlik veya null; boş alanlar tutarlı kalır. stdout yalnız JSON; hata mesajları sabit ve hassas verisiz. Protokol/şema uyumsuzluğu fail-closed hafıza, fail-open kodlama demektir.

### Task 1: Uyumluluk kapısı ve sentetik runtime fixture

**Files:** Create `tests/shared_memory/conftest.py`, `tests/shared_memory/test_contract.py`, `docs/SHARED_MEMORY_SETUP.md`.

**Interfaces:** Sentetik fixture `memory_fixture(tmp_path)` vault, dış runtime ve A/B projesi yollarını döndürür. Fixture kayıtları belirgin `GENERAL_ONLY`, `A_ONLY`, `B_ONLY`, `LEGACY_ONLY` işaretleri taşır; gerçek notları kopyalamaz.

- [ ] **Step 1 — RED:** Kurulu Beyin runtime'ının bir temp kopyasında `MemoryStore`, `source_snapshot`, `_eligible`, `retrieve`, `record_scope` ve not/görev CLI sözleşmelerini doğrulayan test yaz. İç sözleşmeler bulunmadığında adaptörün `unavailable` döndürmesini bekle; uyumsuz bir fake ile testin önce kırıldığını göster.
- [ ] **Step 2 — Kontrol:** `opencode --version` ve salt okunur OpenCode V2 dokümanlarıyla session directory/parent/hook/tool/plugin devre dışı bırakma sözleşmelerini belirle. V2 plugin control dokümanındaki `-beyin-v3` davranışını yalnız izole temp config ve sentetik plugin'lerle dene; global ayara dokunma. Gerçek kullanıcı oturumuna prompt/model çağrısı yapma.
- [ ] **Step 3 — Fixture:** Temp vault/runtime oluştur; gerçek runtime Python modülleri testte bulunamadığında ilgili uyum testi açıkça skip olsun, başarılı kabul edilmesin. Saf unit testler küçük fake runtime ile her makinede çalışmalı. Orijinal yönetilen dosyaların hash'leri korunmalı.
- [ ] **Step 4 — GREEN:** `.\.venv\Scripts\python.exe -m pytest tests/shared_memory/test_contract.py -q` çalıştır. Uyum sonuçlarını, kullanılan runtime sürümünü ve plugin deneyini rehbere yaz. Tek üretici yolu kanıtlanamazsa global etkinleştirme bloke; sentetik geliştirme devam edebilir, sınır değişikliği için kullanıcıya dön.
- [ ] **Step 5 — Commit:** Yalnız bu task'ın dosyalarını ekle; `test: pin shared memory runtime and plugin contracts`.

### Task 2: Merkezi eşleme ve güvenli kök çözümleme

**Files:** Create `src/brainext/shared_memory/__init__.py`, `registry.py`, `tests/shared_memory/test_registry.py`.

**Interfaces:**
- `canonical_directory(path: str | Path) -> Path`: var olan dizin, canonical Windows kimliği; güvenli bileşen sınırı.
- `candidate_root(directory: Path) -> tuple[Path, str]`: Git için `rev-parse --show-toplevel`, yoksa verilen dizin; tür `git|folder`. Shell string birleştirme yok, argv ve timeout var.
- `Registry(path: Path, vault: Path)`: JSON `{version:1,vault,revision,roots:[{root,project}],ignored:[root]}`. Dosya yokluğu boş kayıt; bozuk dosya `RegistryError`.
- `resolve(directory: Path) -> dict`: `mapped|unknown|ignored|conflict`, kök ve opsiyonel proje. Git kökü, başka deponun içindeki daha geniş klasör eşlemesini devralmaz.
- `bind(root: Path, project: str, expected_revision: int) -> dict`, `ignore(root: Path, expected_revision: int) -> dict`: kilit içinde yeniden oku; revision uyuşmazsa `conflict`; aynı eşleme idempotent.

- [ ] **Step 1 — RED:** `test_repo_and_frontend_share_mapping`, `test_non_git_descendant_uses_confirmed_root`, `test_sibling_prefix_is_not_child`, `test_nested_repo_is_independent`, `test_clone_and_worktree_need_binding` yaz; önce import/eksik davranış nedeniyle fail göster.
- [ ] **Step 2 — RED:** `test_corrupt_or_foreign_vault_registry_is_not_replaced`, `test_two_processes_cannot_rebind_same_revision`, `test_case_and_unicode_paths`, `test_ambiguous_roots_do_not_choose_project`, `test_redirected_registry_is_rejected` ekle. Hiçbiri `.env`, uzak Git veya disk çapında tarama yapmasın.
- [ ] **Step 3 — Implement:** Yukarıdaki arayüzleri Python stdlib ile uygula. Kilit için yalnız bu dosyaya ait kilit; atomik replace için aynı dizinde benzersiz temp dosya. Timeout'ta kilidi otomatik silme. Kullanıcıya ait mevcut JSON alanlarını yanlışlıkla kaybetmek yerine bilinmeyen şemayı reddet. Root Windows device/ADS/UNC belirsizliklerini ve path traversal'ı reddet.
- [ ] **Step 4 — GREEN:** `.\.venv\Scripts\python.exe -m pytest tests/shared_memory/test_registry.py -q`. Windows junction izinleri gerektiren test atlanırsa açıkça raporla; sıradan path testlerini atlama.
- [ ] **Step 5 — Commit:** Yalnız ilgili dosyalar; `feat: add vault-bound local project registry`.

### Task 3: Dar kapsamlı Beyin erişim katmanı

**Files:** Create `src/brainext/shared_memory/runtime.py`, `tests/shared_memory/test_runtime.py`.

**Interfaces:** `VaultRuntime(vault: Path)` mevcut `.beyin-runtime.json` pinini ve motor modüllerini doğrular. `project_catalog() -> list[dict]`; `general_context(budget: int) -> dict`; `project_context(project: str, query: str, budget: int) -> dict`; `beyin(command: str, payload: dict) -> dict` yalnız izinli mevcut CLI komutlarını JSON/stdin ile çağırır. Runtime/CLI hatalarında sabit kodlu `RuntimeUnavailable`.

- [ ] **Step 1 — RED:** `test_general_context_contains_only_identity_and_general_rules`: Core/Soul ve genel kural görünür; A/B scoped kural, Last-Session/Threads/Journal, kişi, knowledge/index, receipt ve LEGACY_ONLY görünmez. Companion seçimi belirsizse sonuç `unavailable`.
- [ ] **Step 2 — RED:** `test_a_context_excludes_b_and_unassigned_before_ranking`: çok sayıdaki B ve etiketsiz not A sonuçlarını bütçeden düşürmez. A klasöründe B metadata'lı kayıt, çok projeli receipt ve değişmiş kaynak da alınmaz. `test_private_untrusted_rejected_and_missing_sources_remain_excluded` mevcut tüm gizlilik kapılarını sınar.
- [ ] **Step 3 — Implement:** Kaynak okuma/hash/trust için mevcut motoru kullan. İzinli kayıt kümesini mevcut `_eligible` ve açık proje/folder tutarlılığı ile sıralama öncesinde daralt. Gerekli bir `MemoryStore` alt sınıfı yalnız uygunluk kapısını güçlendirebilir; snapshot/strict passage yolunun bu kapıyı atlamadığını test et; atlıyorsa mevcut note-level aramayı seç. Global Companion formatter'ını çağırma. Yeni hafıza DB veya managed modül monkeypatch'i ekleme.
- [ ] **Step 4 — Implement:** Project.md kimliği `^[a-z][a-z0-9-]{0,63}$` ve dosya yolu ile tutarlı; görünen ad/amaç Unicode olabilir. Proje klasörü `projects/<id>/` ve açık metadata uyuşmalı. Proje catalog'u gövde değil yalnız ID/ad/amaç taşır. Kaynak çıktısında metin, source ve tazelik/citation bilgisi bütçeyle korunur.
- [ ] **Step 5 — GREEN:** `.\.venv\Scripts\python.exe -m pytest tests/shared_memory/test_runtime.py tests/shared_memory/test_contract.py -q`. Gerçek runtime temp fixture ve fake test sonuçlarını ayrı raporla.
- [ ] **Step 6 — Commit:** `feat: retrieve only general preferences and active project memory`.

### Task 4: Oturum bağlamlı kayıt, arama ve yazma işlemleri

**Files:** Create `src/brainext/shared_memory/service.py`, `__main__.py`, `tests/shared_memory/test_service.py`.

**Interfaces:** `MemoryService(vault: Path, registry: Path).handle(request: dict) -> dict`; `main(argv: list[str] | None = None) -> int` accepts `--vault`, `--registry`; tek sınırlı JSON isteğini stdin'den alır. Boyut sınırı 1 MiB; versiyon 1. İstek şemasındaki `session` plugin tarafında doldurulur.

**Actions:** `context`, `catalog`, `register`, `bind`, `ignore`, `search`, `note-read`, `note-create`, `note-edit`, `task-create`, `task-update`, `receipt`. Kısa oturumluk skip JS'te tutulur; disk işlemi değildir. `register` payload `id,title,purpose,root,expected_revision,confirmed`; bind/ignore aynı onay ve revision kapısını kullanır. `search` hedef proje verilmediyse etkin proje; farklı hedefte `cross_project_confirmed` gerekir. `confirmed` alanı doğrulanmış insan onayının kriptografik kanıtı değildir; UI/ajan protokolü ve normal OpenCode izinleriyle birlikte kullanılır.

- [ ] **Step 1 — RED:** `test_unknown_context_does_not_create_files`, `test_register_requires_confirmed_root_and_identity`, `test_root_must_contain_session_directory`, `test_bind_uses_existing_project`, `test_ignore_keeps_general_preferences`.
- [ ] **Step 2 — RED:** `test_register_retry_finishes_same_project_after_registry_failure`: Project.md başarıyla oluşur, registry yazması hata verir; tekrar aynı içerik/ID ile tamamlanır. Farklı içerikte mevcut dosya korunur ve conflict. Makine yolları Project.md'ye yazılmaz.
- [ ] **Step 3 — RED:** `test_general_or_unavailable_session_cannot_write_project`, `test_task_update_checks_project_and_revision`, `test_task_create_update_require_confirmation`, `test_note_edit_keeps_hash_conflict`, `test_receipt_rejects_other_project_refs`, `test_cross_project_search_needs_explicit_scope_and_does_not_rebind`.
- [ ] **Step 4 — Implement:** Runtime'ın güvenli komutlarını kullan; proje kararı/devir kaynaklarını `projects/<id>/`, görevleri `tasks/` ve doğru metadata ile sınırla. Genel tercih yazması yalnız Core/Soul veya genel Kurallar'a hash kontrollü düzenleme olsun. Araçlar tahmini kayıtları olgu yapmaz; içerik/onay politikası ayrıca plugin yönergesinde açıklanır. Başarılı receipt refs ve gerçek oturum kimliğini taşır; CLI başarı kodu ve geri okunan kaynak karşılaştırılır.
- [ ] **Step 5 — RED/GREEN CLI:** `test_cli_invalid_version_oversize_and_runtime_failure_return_safe_json`, `test_cli_never_logs_prompt_or_note_text` ekle. `.\.venv\Scripts\python.exe -m pytest tests/shared_memory/test_service.py -q`; sonra tüm `tests/shared_memory` testleri.
- [ ] **Step 6 — Commit:** `feat: add session-scoped memory actions and project onboarding`.

### Task 5: OpenCode V2 global adaptörü

**Files:** Create `integrations/opencode/shared-memory/index.js`, `index.test.mjs`; extend `tests/shared_memory/test_contract.py` only if packaging/protocol assertions need it.

**Interfaces:** Default export `{id:"brainext.shared-memory",setup}`; `setup(ctx)` returns cleanup. Test için named `createAdapter(ctx, {invoke})` kullan; `invoke(request)` Task 4 protokolünü uygular. Kurulum seçenekleri `python`, `vault`, `registry`; model bunları araç argümanı olarak veremez. Eklenti directory olarak yüklenir; yerel Node testleri `.js` modülünü temp `.mjs` olarak import edebilir, npm/package ekleme zorunlu değil.

- [ ] **Step 1 — RED:** `node --test integrations/opencode/shared-memory/index.test.mjs`; mock ctx ile `first prompt queues onboarding once`, `known project loads scoped context`, `tool continuation does not repeat question`, `skip lasts only session`, `ignore survives fresh session` testleri önce fail.
- [ ] **Step 2 — Implement:** V2 prompt/context hook'ları ve Task 4 işlemlerini sunan dar araçları kaydet. Modelden yalnız payload al; `session.id/directory/parent_id` API'den doğrula. Her hafıza erişiminde dizini tekrar kontrol et; plugin instance konumunu oturum yerine varsayma. Instance dışı event'leri işlemeden geç. Yeni projeye geçişte kendi context katmanını değiştir; eski transkriptin kalabileceğini bildir.
- [ ] **Step 3 — Implement:** Onboarding bağlam yönergesi ilk mesajdan sonra tek kısa soru ister; cevap beklerken proje yazması yok. Kayıt onayından sonra aynı araç döngüsünün sonraki context çağrısı güncel projeyi alır. Alt ajanlar soru sormaz; yalnız doğrulanmış ana oturum kapsamı ve uygun konumla devralır, aksi durumda genel bağlamda kalır.
- [ ] **Step 4 — RED/GREEN:** `moved session drops previous context`, `unrelated session events ignored`, `child does not register twice`, `python timeout clears context and shows warning`, `malformed output fails closed`, `output budget is bounded`, `source text cannot supply approval`, `cleanup releases hooks and processes`.
- [ ] **Step 5 — Implement:** Kaynak metinleri ayrı veri bloğunda, sabit kayıt/izin protokolü ayrı yönergede. Görev onayı, genel/proje not hedefleri ve no-memory/no-tools isteğine uyma açık olsun. Subprocess argv/stdin, timeout, maxBuffer ve Windows gizli pencere kullanır; prompt/not gövdesini hata loguna yazmaz. Ek lifecycle receipt/worker üretme; anlamlı sonuçları ajan mevcut receipt yolu ile yazar.
- [ ] **Step 6 — GREEN:** Node testleri ve `.\.venv\Scripts\python.exe -m pytest tests/shared_memory -q`; ardından `ruff check .`, `pytest -q --tb=short`, `git diff --check`. Atlamaları ayrı belirt.
- [ ] **Step 7 — Commit:** `feat: connect OpenCode sessions to scoped shared memory`.

### Task 6: İnceleme, güvenli global etkinleştirme ve canlı kabul

**Files:** Modify `docs/SHARED_MEMORY_SETUP.md`, `README.md`, bu plan ve onaylı spec'in kabul checklist'i. Machine-only değişiklik: mevcut global OpenCode config'in yalnız plugin girdileri; önce yedek/diff. Config yolu aktif config keşfiyle doğrulanır, tahminen ikinci config oluşturulmaz.

- [ ] **Step 1 — İnceleme:** Uygulamayı bağlı runtime koduyla birlikte taze incelemeye ver. Kapsam filtresi ve onay kapılarındaki bulguları testle düzelt; sadece talimat metninin güvenlik garantisi olmadığını raporla.
- [ ] **Step 2 — Ön kontrol:** Mevcut config'in secret olabilecek değerlerini çıktıya vermeden ilgili plugin alanlarını incele. Task 1'de doğrulanan sürüme uygun plugin array dar düzenlemesini göster. Beyin üreticisini config control ile devre dışı bırakma sırası yeni adaptörün etkin kalmasını sağlamalı; farklı `id` kullan. Local plugin kaynaklarını silme/taşıma. Başarı doğrulanamıyorsa burada dur, etkinleştirme yapılmadığını bildir.
- [ ] **Step 3 — Yedek ve aktivasyon:** Onaylı kurulum kapsamındaki config'in byte-exact yedeğini onaylı temp/local alanda sakla; yalnız dar plugin girdilerini patch et, ilgisiz değerleri koru. Model/provider/permissions/MCP alanlarını değiştirme. `/reload` veya desteklenen otomatik reload kullan; sağlıklı servisi sebepsiz restart etme. Geri alma yalnız kendi girdilerini kaldırmalı; sonradan gelen kullanıcı değişikliklerini ezmemeli.
- [ ] **Step 4 — Sentetik canlı kabul:** İki temp Git projesi, bir non-Git proje ve temp vault/runtime ile A/B/genel/etiketsiz senaryoları gerçek plugin lifecycle üzerinden çalıştır. Mevcut özel notları model testine gönderme. Canlı model çağrısı veya interaktif iki oturum testi gerekiyorsa kullanıcıyla yürüt; otomatik test yapılmış gibi sunma. İlk kayıt sorusu, seçim, onay, sonraki oturumda hatırlama ve görev onayı gözlenmeli.
- [ ] **Step 5 — Gerçek kurulum doğrulaması:** Kullanıcıya gerçek bir kod klasöründe yeni oturum açtır; doğru vault, genel bağlam, kayıt sorusu ve kullanıcı onaylı proje kaydını doğrula. Vault içindeki mevcut eklentiyle çift context/receipt olmadığını ayrıca gözle. Kullanıcının ilk proje adı/amacını tahmin ederek oluşturma.
- [ ] **Step 6 — Arıza ve geri alma:** Temp eşlemeyi bozarak uyarı + genel/disabled davranışını kanıtla. Plugin'in yüklenmemesi halinde log/sağlık kontrolünün bunu saptamasını dene. Gerçek vault/runtime dosyalarını bozma. Kurulumdan bağımsız geri alma testini temp config'te gerçekleştir.
- [ ] **Step 7 — Son doğrulama ve rapor:** Tam Python/Node testlerini, Ruff ve diff check'i tekrar çalıştır. Spec'te yalnız kanıtlanan kabul kutularını işaretle. Sentetik kanıt, kullanıcı teyidi ve doğrulanmayanları ayrı yaz. Sadece kendi kod/belgelerini commit et; yerel config, registry, vault kullanıcı notları ve diğer brief'leri bu depoya ekleme.

## Plan self-review

- Tasarımın bütün bölümleri Task 1–6'ya dağıtıldı; kayıt/okuma kapsamı, no-Git, skip/ignore, arıza, paralellik ve mevcut eklenti kapıları dahil.
- Task 2'nin Registry, Task 3'ün VaultRuntime ve Task 4'ün version=1 protokolü Task 5 tarafından aynı adlarla kullanılır.
- Beş Review Focus maddesinin her biri ilgili task'ta adlandırılmış test veya canlı kontrol içerir.
- Yeni Notion erişimi, Hermes kurulumu, orchestration, eski arşiv migrasyonu ve otomatik worktree kimliği kapsam dışında kalır.
- Plan durum raporudur; test/kurulum adımlarının hiçbirinin henüz çalıştığı anlamına gelmez.
