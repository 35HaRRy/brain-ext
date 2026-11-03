# Uygulama Kaydı

Spec: `docs/spec/BRIEF-EK-1-KESIF-SONRASI.md` önceliklidir.

- [x] Faz 1: paket, config, init/doctor — 6 test geçti; ruff temiz; Python 3.14.6 venv kurulumu geçti.
- [x] Faz 2: Notion mock senkron — 71 toplam test geçti; ruff temiz. Kapsam keşfi, hash/rename/arşiv, belirsiz yazma uzlaştırması, created_time pencereleme ve CLI bağlantıları.
- [x] Faz 3: yerel arama/graf/eval — 168 test geçti, 3 atlama (gerçek model, Windows yetkisi olmayan iki symlink testi); junction testi geçti. Ruff temiz.
- [x] Faz 4: CLI, skill, kurallar, kurulum rehberi — bağımsız incelemenin iki önemli bulgusu ve kurulum yönergesi düzeltildi. Son tam suite: **180 geçti, 3 atlandı**; ruff temiz; wheel build ve pip check geçti.

Onay: kullanıcı `C:\Users\35.HaRRy\Desktop\Projects\brain-ext` konumunu ve Faz 1–4 sentetik uygulamasını onayladı.
Karar: yeni ayrı depo doğrudan `implementation` dalında; mevcut kullanıcı git deposu veya worktree'si yok. Ek plan onayı istenmez, brief ekinin yalnız konum sorusu talimatı önceliklidir.
Faz 1 RED: `pytest -q` paket olmadığı için collection hatası verdi; henüz üretim kodu yoktu.

Faz 2 ek güven kontrolleri: managed/generated klasörünü state olarak sahiplenme, bozuk config türü ve eksik config mesajı RED→GREEN. CLI pull/push bayrakları bağlandı. Testlerde autouse socket engeli gerçek ağı yasaklar; MockTransport kullanılır.
Bağımlılık kontrolü: semantik ekstra yalnız .venv'e kuruldu; FastEmbed/ONNX import ve sqlite-vec RAM uzantı yükleme geçti, model indirme/inference yapılmadı.

Faz 3: tokenizer bütçeli chunk/FTS tam kod, sahte embedding ile artımlı indeks ve sqlite-vec/numpy/RRF/eval; sorgu anında private/silinmiş/değişmiş kaynaklar fail-closed. Hassas isimlerde rakam/alt çizgi ayrımı ve yeni dosya stale doctor kontrolü ayrıca RED→GREEN düzeltildi. Unknown Markdown alt-ağaçları 128 güvenlik sınırında eksik-blok/kısmi sonucu verir; recursion taşması testi geçti. K14 gerçek bağlantı doğrulaması hâlâ yapılmadı.

Faz 4: eksik skill/kurallar/rehber testi RED→GREEN, insan CLI çıktısı testi RED→GREEN. Sentetik CLI uçtan uca sync→index→arama→graf→eval→draft/approved→idempotent push ve dry-run bayt koruması geçti. Gerçek OpenCode config dosyası yaratılmadı, yalnız rehber içi V2 taslağı yazıldı.

## Bağımsız son inceleme ve düzeltme kanıtı

İncelenen commit `9188ce0`. İncelemeci 171 geçen/3 atlanan testi bağımsız tekrar çalıştırdı; kritik bulgu yok, iki önemli hata var. Tek düzeltme geçişi yapıldı; tekrar inceleme iddiası yok, regresyon testleri kanıttır:

1. Windows `.git.`/`notes.`/son boşluk/device/ADS isimleri: `test_windows_ambiguous_region_names_are_rejected` RED→GREEN. Config artık taşınabilir tek Windows bileşeni ve belirsiz ad reddi uygular; korunan klasöre alias üzerinden yazamaz.
2. Ağ beklerken değişen taslağın uncertain dallarında ezilmesi: `test_uncertain_push_preserves_network_time_draft_edits` create ve recover yollarında RED→GREEN. Durum uncertain olarak kalıcı tutulur; değişen dosyanın ham baytları korunur.
3. Dev kurulumu tam suite'in optional test bağımlılıklarını kapsamıyordu. Kullanıcı açısından yönerge kırık olduğu için önem yükseltildi ve `test_documented_full_suite_install_includes_semantic_test_dependencies` RED→GREEN ile README `.[dev,semantic]` yapıldı. Runtime'ın semantic ekstrası hâlâ isteğe bağlıdır.

Son doğrulama: `python -m pytest -q --tb=short` → **180 passed, 3 skipped** (20.10s); `ruff check .` → temiz; `pip wheel --no-deps --no-build-isolation . --wheel-dir dist` → başarılı. Önceki `pip check` → broken requirement yok. Gerçek model ve iki Windows symlink-privilege testi atlandı; junction testi geçti. Kaynak/doküman UTF-8 ve yerel bağlantıları denetlendi.

## Kapsam kararları ve açık riskler (Rulings)

- Yeni ayrı repo kullanıcının konum/onay kapsamındadır; doğrudan `implementation` dalı korundu. Merge/push/PR istenmedi, başka depo/worktree'ye dokunulmadı. Yanlış entegrasyon hedefine merge riski alınmadı.
- Gerçek Notion/OAuth/vault/OpenCode/K14 bu teslimde denenmez; kullanıcı ayrı başlatana kadar Faz B kapalı. Maliyet: gerçek ortam uyumsuzlukları henüz bilinmiyor.
- Gerçek model yükleme/inference/tokenizer davranışı ve Türkçe kalite gerçek modelle ölçülmez; yalnız yerel sentetik tokenizer ve sahte embedding kanıtı vardır. Maliyet: gerçek kalite ve throughput garantisi yok.
- Prompt-injection senaryosu skill/kurallar açısından statik incelendi; ajan davranışı veya sandbox güvencesi olarak sunulmaz. Maliyet: talimat metni tek başına mutlak güvenlik sağlamaz.
- İşlem kilidi yalnız bu CLI'nın işbirlikçi yazarlarını koordine eder; harici editörlerle OS-transactional compare-and-swap yok. Uzun ağ beklemesinde kaybolan edit hatası düzeltildi; son kontrol ile atomik replace arasındaki dar harici yarış mutlak olarak çözülmüş sayılmaz.
- 128 Markdown alt-ağaç ve 32 seviye/1ms query-splitting limitleri kısmi sonuçla görünür kalır. Maliyet: uç boyuttaki sayfa/kaynaklarda tamlık kabul edilemez; sessiz başarı yok.
- Skill/rehber varlıkları repo tabanlı teslimdir; yalnız wheel kurmak entegrasyon rehberinin dağıtımı sayılmaz. Maliyet: kurulumda kaynak repo belgelerine erişim gerekir.

Ertelenen küçük review bulgusu yok. Faz 4 sonunda duruldu; Faz B başlamadı.
