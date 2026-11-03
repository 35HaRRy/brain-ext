# Kurulum Rehberi — Faz B İçin Bekleyen Adımlar

**Bu rehber komutları şimdi çalıştırma talimatı değildir.** Faz 1–4 yalnız sentetik veriyle doğrulandı. Kullanıcı açıkça “Faz B'yi başlat” demeden dur. Faz B'de her seferinde yalnız bir adım göster; kullanıcı sonucunu onaylayana kadar sonrakine geçme. Gerçek vault, Notion/OAuth, model indirme ve OpenCode ayarları için ayrı açık onay al.

## 1. Ortamı ve yolları doğrula

Bu makinede Windows PowerShell, OpenCode v2.2.5, Python 3.14.6 ve SQLite 3.50.4 keşifte görüldü. Yeni makinede yeniden doğrula:

```powershell
py -3 --version
git --version
opencode --version
```

Kod deposu: `C:\Users\35.HaRRy\Desktop\Projects\brain-ext`. Gerçek vault yolu henüz seçilmedi. İki konum ayrı olmalı. Kod yorumlayıcısı `.venv\Scripts\python.exe`; avenoxbeyin'in pinlenmiş yorumlayıcısına dokunma. Temel ve semantik bağımlılıklar bu proje venv'inde kuruldu; model indirilmedi. Yeni makinede yalnız bu venv'e `pip install -e ".[dev,semantic]"` yapılır.

Kontrol: test için `python -m pytest -q`, lint için `ruff check .` komutlarını **venv içinden** çalıştır. Paket kurulmazsa Python 3.12/3.13 venv'ine geçişi ayrıca kaydet; global Python paketlerini değiştirme.

## 2. avenoxbeyin'i resmî paketten kur (ayrı onay)

[Releases](https://github.com/avenoxai/avenoxbeyin/releases) içinden release ZIP ve yanındaki `.sha256` indir. **Source code arşivini kullanma.** Keşifte v3.12.0 ürün ZIP'i doğrulandı; kurulum gününde seçilen sürümün hash'ini tekrar denetle.

```powershell
Get-FileHash "<indirilen-release.zip>" -Algorithm SHA256
```

Checksum dosyasındaki ilk değerle birebir eşleşmesini göster. Boş hedef vault'u ve [resmî SETUP-V3.md](https://github.com/avenoxai/avenoxbeyin/blob/0be8f9961e3bef7a312735cd7461c66ecdca760a/SETUP-V3.md) adımlarını birlikte incele; installer'ın yazacağı kapsamı anlat ve ayrıca onay al. Installer/update/doctor bu uygulamada kullanıcı vault'unda çalıştırılmadı.

Kurulumdan sonra kullanıcının onayıyla `py -3 "<vault>\beyin.py" doctor --json`. `observed_metadata` bütün kabul testleri geçti demek değildir. Vault git yedeğini kur; `notion/`ın git'e girip girmemesine kullanıcı karar versin. `.env`, `.brain-ext/`, `.beyin-note-write/` dışarıda kalsın. `preferences --index-exclude-dir agent-out` ve `preferences --update-notifications off` seçeneklerini kullanıcıya sun; otomatik uygulama.

## 3. Notion erişim bölgeleri ve plan (ayrı onay)

Brain ve Agent Workspace'i belirle. Kullanıcının planını sor; hız sınırları plan/endpoint/workspace bütçesine bağlıdır. 2.5/s muhafazakâr başlangıçtır. Üst sayfa paylaşımının alt ağacı da açabileceğini anlat. Linked database başka yerdeyse Brain kapsamı kabul etme.

Internal integration için gerekli read/insert/update yeteneklerini kullanıcı ayarlasın; yalnız seçilen bölgeler paylaşılsın. Token'ı **sohbete yapıştırmasını isteme**. MCP OAuth ayrı erişimdir; internal token'ı MCP'ye kopyalama. Tam paylaşımın yalnız API taramasıyla kanıtlanamayacağını belirt ve portalda denetle.

Agent Workspace page, database veya açık data source ID olabilir. Çok data source'lu database'de doğrudan hedef data source ID seç; ilkini kendiliğinden seçme. Title property'si şemadan doğrulanır.

## 4. Config ve sırlar (ayrı onay)

Rehberdeki `<vault>` yerini kullanıcının onayladığı mutlak yolla değiştir; aşağıdaki örneklerde placeholder bırakıp komut çalıştırma.

```powershell
Set-Location "C:\Users\35.HaRRy\Desktop\Projects\brain-ext"
.\.venv\Scripts\brainext.exe init --vault "<vault>" --dry-run --json
.\.venv\Scripts\brainext.exe init --vault "<vault>" --mirror-git exclude
```

`exclude` örnektir; kullanıcı git kararına göre `include` seçilir. Mevcut config korunur, üzerine yazılmaz. Vault mevcut olmalıdır; `init` vault installer değildir.

Kullanıcı `.env.example` dosyasını `.env`ye kendisi kopyalayıp token'ı kendisi yazsın. Ajan `.env`yi okumasın/yazdırmasın. `config.toml` içinde vault yolu, Brain/Workspace ID ve model seçimi ayarlansın; token config'e yazılmaz. CLI `.env`yi yalnız gerekli komutta kendi okur; offline arama sır okumaz.

`config.example.toml` varsayılanı mpnet; Markdown v2 ve mirror trust untrusted. Mirror dosyaları tam JSON header taşır. Kullanıcı düzenlemesiyle hash uyuşmazsa normal pull korur; force için ayrı onay ve `--confirm-force` gerekir.

## 5. İlk erişim, pull ve güven kontrolleri

```powershell
.\.venv\Scripts\brainext.exe doctor --config config.toml --json
.\.venv\Scripts\brainext.exe pull --config config.toml --dry-run --json
```

Doctor çıktısını birlikte oku; 401/403/404'te kapsam ve yetenekleri düzelt, otomatik silme/arşivleme yapma. İlk gerçek pull için ayrı çalıştırma onayı al. 5–10 test sayfasıyla K1–K4: JSON/trust metadata, ikinci çalıştırmada içerik atlama, rename, elle değişen dosyada conflict ve arşiv `status: archived` doğrula. İkinci pull yine keşif/metadata istekleri yapar.

K13: büyük/truncated sayfada `unknown_block_ids`, yerinde replacement ve erişilemeyen blok yorumlarını denetle. 128 subtree güvenlik limiti veya ayrıştırılamayan içerikte sonuç kısmi kalır, başarı diye sunma. Data source limitinde created_time pencereleri kullanılır; tek zaman damgasındaki aşırı kayıtlar kısmi raporlanabilir. 403/404/eksik taramada arşivleme engellenmelidir.

## 6. Model onayı ve yerel arama

Önce boyutu ve bağlantıya göre değişen süreyi söyle: mpnet ~1.0 GB, MiniLM ~0.22 GB, E5-large ~2.24 GB; tokenizer/ek dosyalar disk ihtiyacını artırabilir. **İndirmeden önce ayrıca onay al.** Kullanıcı seçilen FastEmbed ONNX artifact'ini yerel klasöre indirsin; `model_path` o dizini göstersin. `tokenizer.json` ve seçilen modelin kayıtlı ONNX dosyaları gerekir. Doğrulanmamış bir model indirme komutunu uydurma; resmî FastEmbed model kaydındaki `sources`/`model_file` bilgilerini kullan. Bu sürüm otomatik model indirme komutu sağlamaz.

Model yokken FTS araması çalışır; vector/hybrid istekleri açık text fallback verir. E5 önekleri araç tarafından uygulanır. Model/boyut değişiminde `index --reembed` gerekir; mevcut vektörler karıştırılmaz. Token bütçesinde başlık da sayılır. Uzun kod FTS'de tam, embedding'de satır sınırlarında tutulur; sığmayan tek satır kısmi kapsam olarak bildirilir.

```powershell
.\.venv\Scripts\brainext.exe index --config config.toml --dry-run --json
.\.venv\Scripts\brainext.exe index --config config.toml --json
.\.venv\Scripts\brainext.exe search "hosting kararımız" --config config.toml --json
```

Kullanıcı gerçek notlarından 15–20 query/expected kaydı hazırlasın; `eval/queries.example.yaml` yalnız örnektir. `brainext eval eval/queries.yaml --config config.toml --json` ile recall@5/MRR karşılaştır; fallback_count varken onu gerçek semantik ölçüm sayma. RRF her sorguda en iyi tek modu geçmek zorunda değildir; kötüleşmeyi raporla.

## 7. K14 — gerçek Markdown bağlantı kapısı

Gerçek test sayfasının GET Markdown v2 çıktısını kullanıcı onayıyla al; `[metin](url)`, mention/page/database/folder XML, wikilink ve id↔url eşlemesini doğrula. Tarihsel notion.so ve app.notion.com/p adreslerini karıştırma; URL kararlı kimlik değildir. K14 tamamlanana kadar rapordaki `live_fixture_verified: false` bir uyarı olarak kalır; kod bunu sentetik testten hareketle true yapmaz.

## 8. Skill ve kurallar (ayrı kurulum onayı)

Tek skill hedefi `<vault>/.opencode/skills/notion-brain/SKILL.md`; tek kural hedefi `<vault>/.brain/notion-brain/RULES.md`. Repo `skills/` ve `rules/` dosyalarını yalnız hedefler yoksa kopyala; varsa önce diff göster ve açık üzerine-yazma onayı al. `.agents/skills`e koyma; `skill-import`/`skill-sync` çalıştırma. Yönetilen `.opencode/plugins/beyin-v3.js`, çekirdek beyin skill'leri ve AGENTS blokları değişmez.

Executable ve config mutlak yollarını kurulum kaydına yaz; OpenCode shell'inin venv PATH'ini miras alacağını varsayma. Gerekirse skill komutlarında `.venv\Scripts\brainext.exe` mutlak yolunu kullan; global PATH'i onaysız değiştirme.

## 9. OpenCode V2 taslağı — çalışan yapılandırma değildir

**Mevcut OpenCode ayarları/kalıcı izinler bu fazlarda okunmadı veya değiştirilmedi.** Aşağıdaki JSON yalnız rehber taslağıdır; Faz B onayı, V2 sözleşme ve OAuth sonrası gerçek araç kataloğu kontrolü yapılmadan dosyaya dönüştürme. Var olan ayarları koruyarak merge gerekir.

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "servers": {
      "notion": { "type": "remote", "url": "https://mcp.notion.com/mcp" }
    }
  },
  "permissions": [
    { "action": "notion_*", "resource": "*", "effect": "ask" },
    { "action": "notion_notion-search", "resource": "*", "effect": "allow" },
    { "action": "notion_notion-fetch", "resource": "*", "effect": "allow" }
  ],
  "instructions": [".brain/notion-brain/RULES.md"]
}
```

Son eşleşen kural kazanır; broad ask önce, dar read allow sonra. Gerçek normalize ad `<server>_<tool>`dur. OAuth kullanıcı arayüzünde `/mcps` ile tamamlanır; ajan token istemez. Yazma için **Allow always kullanma**, yalnız tek seferlik onay seç. Önceden kaydedilmiş geniş izinler ayrıca onayla gözden geçirilir. Hosted MCP, Agent Workspace ata sınırını sunucu tarafında garanti etmez; her yazma onayında hedefi göster.

İlgili araçlar: search/fetch, create-pages/update-page/create-comment, move-pages/duplicate-page/create-database/**update-data-source**. `notion-update-database` adı kullanılmaz. Silme/takvim/session/skill/notion-memory-search bu projenin kapsamı dışıdır.

## 10. Kabul, otomasyon ve bakım

K7–K12'yi gerçek onaylı test taslaklarıyla uygula: draft gönderilmez, approved bir kere oluşturulur, ikinci push kopya yaratmaz, kapsam dışı hedef reddedilir, yeni OpenCode oturumu arama kullanır, MCP yazması tek-seferlik onay ister. K13/K14 ve gerçek eval tamamlanmadan gerçek sistemin kabulü geçti deme.

İsteğe bağlı scheduler: `brainext sync --if-stale 30m` için Windows Görev Zamanlayıcı yalnız ayrı onayla; gerçek executable/config mutlak yolları gerekir. Hook düzenleme yok.

| Sorun | Yapılacak |
|---|---|
| 401/403/404 | Token/yetenek/paylaşım ve hedefi kullanıcıyla doğrula; token yazdırma, silinme varsayma |
| 429/529 | Retry-After ve hata sonucunu izle, paralelliği azalt |
| POST/PATCH uncertain | Aynı dosyayla read/reconcile; yeni POST veya pending state silme yok |
| Aynada conflict | Dosyayı koru/diff göster; force her seferinde ayrı onay |
| İndeks/model uyuşmazlığı | Config'i denetle; model değiştiyse onayla --reembed |
| Model yok | Text fallback; indirme öncesi boyut ve onay |
| operation.lock kaldı | İşlem gerçekten bitmiş mi denetle; otomatik silme yok |
| avenox update conflict | Yönetilen dosya diff/backup'ını göster; çekirdeği brain-ext için düzenleme |

Geri alma: kullanıcı notları vault git yedeğinden, kod kendi git geçmişinden; ayna güvenli tam pull ile yeniden üretilebilir ama elle değişen dosya korunur. İndeks yeniden üretilebilir; state özellikle pending/uncertain push kayıtları körlemesine silinemez. avenox güncellemesinden sonra onayla her iki doctor'ı çalıştır; sistem rollback'inin kullanıcı notu geçmişini geri almadığını anlat.
