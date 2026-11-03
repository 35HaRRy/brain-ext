# Uygulama Kaydı

Spec: `docs/spec/BRIEF-EK-1-KESIF-SONRASI.md` önceliklidir.

- [x] Faz 1: paket, config, init/doctor — 6 test geçti; ruff temiz; Python 3.14.6 venv kurulumu geçti.
- [x] Faz 2: Notion mock senkron — 71 toplam test geçti; ruff temiz. Kapsam keşfi, hash/rename/arşiv, belirsiz yazma uzlaştırması, created_time pencereleme ve CLI bağlantıları.
- [x] Faz 3: yerel arama/graf/eval — 168 test geçti, 3 atlama (gerçek model, Windows yetkisi olmayan iki symlink testi); junction testi geçti. Ruff temiz.
- [ ] Faz 4: CLI, skill, kurallar, kurulum rehberi — uygulama ve sentetik teslim testi hazır; bağımsız son inceleme bekleniyor. 171 test geçti, 3 atlandı; ruff temiz.

Onay: kullanıcı `C:\Users\35.HaRRy\Desktop\Projects\brain-ext` konumunu ve Faz 1–4 sentetik uygulamasını onayladı.
Karar: yeni ayrı depo doğrudan `implementation` dalında; mevcut kullanıcı git deposu veya worktree'si yok. Ek plan onayı istenmez, brief ekinin yalnız konum sorusu talimatı önceliklidir.
Faz 1 RED: `pytest -q` paket olmadığı için collection hatası verdi; henüz üretim kodu yoktu.

Faz 2 ek güven kontrolleri: managed/generated klasörünü state olarak sahiplenme, bozuk config türü ve eksik config mesajı RED→GREEN. CLI pull/push bayrakları bağlandı. Testlerde autouse socket engeli gerçek ağı yasaklar; MockTransport kullanılır.
Bağımlılık kontrolü: semantik ekstra yalnız .venv'e kuruldu; FastEmbed/ONNX import ve sqlite-vec RAM uzantı yükleme geçti, model indirme/inference yapılmadı.

Faz 3: tokenizer bütçeli chunk/FTS tam kod, sahte embedding ile artımlı indeks ve sqlite-vec/numpy/RRF/eval; sorgu anında private/silinmiş/değişmiş kaynaklar fail-closed. Hassas isimlerde rakam/alt çizgi ayrımı ve yeni dosya stale doctor kontrolü ayrıca RED→GREEN düzeltildi. Unknown Markdown alt-ağaçları 128 güvenlik sınırında eksik-blok/kısmi sonucu verir; recursion taşması testi geçti. K14 gerçek bağlantı doğrulaması hâlâ yapılmadı.

Faz 4: eksik skill/kurallar/rehber testi RED→GREEN, insan CLI çıktısı testi RED→GREEN. Sentetik CLI uçtan uca sync→index→arama→graf→eval→draft/approved→idempotent push ve dry-run bayt koruması geçti. Gerçek OpenCode config dosyası yaratılmadı, yalnız rehber içi V2 taslağı yazıldı.
