# Concat / Kdenlive / OpenCut — video motoruna entegrasyon araştırması

Tarih: 2026-11-22. Durum: **birincil kaynak incelemesi; kurulum, render veya Windows kabul testi yapılmadı.** Sürüm, yıldız ve katkıcı sayıları 22 Kasım 2026 anlık görüntüsüdür. Lisans özeti hukuki görüş değildir.

Kapsam: mevcut motor (AvenoxBeyin isteğe bağlı `video-motoru` skill'i + HyperFrames) ile üç ayrı editörün **içeride bileşen** mi, **yanında ayrı NLE adımı** mı olduğu. Önceki sonuçlar: [video serisi araştırması](video-series-asset-research.md), [Orta Dünya prodüksiyonu](middle-earth-production-research.md).

## Kısa cevap

Hiçbiri motorun **içine gömülmesin**. HyperFrames hareketin, haritanın ve zamanlamanın tek kaynağı kalsın. Bugünkü render yolu **FFmpeg** olsun; Concat yalnızca insan/ajan kurgu ve QC için **yanında** opsiyonel dursun; Kdenlive yalnız insan review'ı gerekiyorsa; OpenCut şimdilik hiç.

| Aday | Karar | Gerekçe (tek satır) |
| --- | --- | --- |
| **FFmpeg concat** | **Varsayılan** | Zaten kurulu (9.0.2), yeni bağımlılık yok; aynı parametreli kliplerde kayıpsız birleştirme. |
| **Concat** | **Yanında, opsiyonel** | `--mcp headless` Windows'ta gerçek ajan arayüzü; ama beta, yalnız MP4/H.264-HEVC-AV1, alfa yok, tek export. |
| **Kdenlive + MLT** | **Yanında, insan review** | `.kdenlive` = MLT XML; `melt` doğrudan render ediyor. Ama ikinci zaman çizgisi ve GPL. |
| **OpenCut** | **Şimdilik hayır** | Ana repo yazım aşamasında, klasik sürüm arşivli; CLI/API/MCP yok, proje tarayıcı deposunda. |

## Doğrulanan kimlikler

| | Concat | Kdenlive / MLT | OpenCut |
| --- | --- | --- | --- |
| Ne | Masaüstü NLE + JSON-RPC/MCP | NLE + MLT framework | Web tabanlı NLE |
| Lisans | **AGPL-3.0-or-later** + ticari seçenek ([LICENSE](https://github.com/jub0t/Concat/blob/main/LICENSE), [LICENSING](https://github.com/jub0t/Concat/blob/main/LICENSING.md)) | Kdenlive **GPL-3.0-only** ([COPYING](https://invent.kde.org/multimedia/kdenlive/-/blob/master/COPYING)); MLT **LGPL-2.1** ([repo](https://github.com/mltframework/mlt)) | **MIT** ([LICENSE](https://github.com/OpenCut-app/OpenCut/blob/main/LICENSE)) |
| Stack | Rust 1.93, Slint, wgpu, FFmpeg 7+, ONNX ([Cargo.toml](https://github.com/jub0t/Concat/blob/main/src/Cargo.toml)) | C++/Qt6/KF6, MLT, frei0r, LADSPA ([README](https://invent.kde.org/multimedia/kdenlive/-/blob/master/README.md)) | Klasik: Next.js 16, Bun, Rust/wgpu WASM; yeni: Vite/TanStack + Rust çekirdek |
| Sürüm / tarih | **0.2.12**, 19 Kas 2026, beta ([release](https://github.com/jub0t/Concat/releases/tag/v0.2.12)) | **26.08.3** ([indirme](https://kdenlive.org/download/)); MLT **7.42.0**, 3 Eki 2026 ([site](https://www.mltframework.org/)) | Editör sürümü yok; son commit 24 Eyl 2026 ([repo](https://github.com/OpenCut-app/OpenCut)) |
| Windows | x64 setup + MSI, imzasız ([README](https://github.com/jub0t/Concat/blob/main/README.md)) | Windows 10+, "standalone" kurulum ([indirme](https://kdenlive.org/download/)) | Tarayıcı; self-host Bun+Docker+Postgres+Redis ([README](https://github.com/opencut-app/opencut-classic/blob/main/README.md)) |
| Olgunluk | Beta; 19,6k yıldız, ~56 katkıcı, 300 açık issue | Olgun; KDE projesi, günlük aktivite | 99k yıldız ama **yeniden yazım**; klasik arşivli |

## 1. Concat

**Kimlik.** README kendini "beta" diye tanımlıyor; Windows x64 setup/MSI var, ARM duraklatılmış ([README](https://github.com/jub0t/Concat/blob/main/README.md)). Uygulama Rust + Slint; render/kompozit wgpu, kodlama FFmpeg ve donanım kodlayıcısı üzerinden ([sistem gereksinimleri](https://concat.standalones.org/guides/system-requirements/)).

**Otomasyon yüzeyi — asıl güçlü taraf.**

| Yüzey | Durum | Kaynak |
| --- | --- | --- |
| MCP (`concat --mcp`) | Her masaüstü sürümünde, 0.2.8'den beri | [MCP.md](https://github.com/jub0t/Concat/blob/main/docs/MCP.md) |
| JSON-RPC 2.0 satırları | Pencerenin Automation sayfası; `concat-cli` yalnız kaynaktan derlemede | [docs](https://concat.standalones.org/docs) |
| gRPC | Yalnız kaynaktan derleme (`grpc` feature) | [docs](https://concat.standalones.org/docs) |
| Proje biçimi | **Klasör**; her metot klasör yolu alır; iç JSON şeması interchange formatı olarak belgelenmemiş | [project.create](https://concat.standalones.org/docs/api/methods/project-create/) |
| API sürümü | `apiVersion 0.2`; `concat --schema` ile JSON Schema | [docs](https://concat.standalones.org/docs) |

MCP modları: `window` (açık pencereye bağlanır, ekrandaki projeyi ezmez), `headless` (pencere yok), `auto` varsayılan. Proje klasörleri `concat.lock` ile kilitlenir; ajan yalnız kendi projelerini düzenler ([MCP.md](https://github.com/jub0t/Concat/blob/main/docs/MCP.md)). Araçlar arasında `project.create`, `media.import`, `clips_add_sequence`, `clip_trim`, `keyframe_set`, `captions_add`, `preview_frame`, `export_wait` var — yani ajan kurguyu kurup kareyi görüp export'u bekleyebilir.

**Sınırlar.** Export **her zaman `.mp4`**, codec `h264|hevc|av1`; 4K60, 10-bit, HDR var; **alfa yok**, PNG dizisi yok ([export.run](https://concat.standalones.org/docs/api/methods/export-run/), [export rehberi](https://concat.standalones.org/guides/export/)). Aynı anda **tek export** (`busy`). Belgelerde EDL/XML/OTIO/FCPXML içe aktarma yok; giriş `media.import` ile FFmpeg'in çözebildiği dosyalar. Donanım kodlayıcı varsa kullanılır, yoksa CPU; bit düzeyinde determinizm vaadi yok.

**Alfa ve zaman çizgisi:** HyperFrames `webm` (VP9 alfa), `mov` (ProRes 4444) ve `png-sequence` verebiliyor ([CLI](https://github.com/heygen-com/hyperframes/blob/v0.9.77/docs/packages/cli.mdx)); Concat bunları girdi olarak çözebilir ama **çıktıda alfayı taşıyamaz**. Katmanlı overlay üretimi Concat'e devredilirse alfa kaybolur.

## 2. Kdenlive + MLT

**Kimlik.** Kdenlive 26.08.3, Windows 10+ standalone; C++/Qt6/KF6, çekirdek MLT ([README](https://invent.kde.org/multimedia/kdenlive/-/blob/master/README.md), [indirme](https://kdenlive.org/download/)). MLT 7.42.0, LGPL-2.1, C; `melt` "çok kanallı, komut satırı odaklı editör" ([melt](https://www.mltframework.org/docs/melt/)).

**Proje biçimi — buradaki tek gerçek interchange.** `.kdenlive` dosyası MLT XML tabanlı; Kdenlive'e özel property'ler MLT tarafından yok sayılır ve **MLT Kdenlive projesini doğrudan render eder** ([Project File Details](https://docs.kdenlive.org/en/project_and_asset_management/file_management/project_files.html)). Belge sürümü 1.1; sürümler geriye uyumlu değil. XML parser **doğrulayıcı değil**, DTD var ([MLT XML](https://www.mltframework.org/docs/mltxml/)). Render: `melt proje.kdenlive -consumer avformat:cikti.mp4 vcodec=libx264 ...`.

**Otomasyon.** Kdenlive'de JSON-RPC/MCP yok. Kaynakta **`--render`** var: "Directly render the project and exit", ayrıca `--render-preset`, `--render-async`, `--verify-file` ([src/main.cpp](https://invent.kde.org/multimedia/kdenlive/-/blob/master/src/main.cpp), ~352–373). Bu bayrak kullanım kılavuzunda belgeli değil; uygulama yine Qt GUI başlatıyor, **headless/sunucu modu belgelenmemiş**. Alternatif: manifest'ten MLT XML üretip `melt` ile render etmek; ama o zaman Kdenlive'in efekt/geçiş semantiğini yeniden üretmek gerekir.

**Sınırlar.** İki zaman çizgisi riski (HyperFrames + Kdenlive), MLT XML'i elle üretmek kırılgan, efekt eşlemesi bire bir değil, Windows'ta `melt` ikilisinin Kdenlive kurulumuyla gelip gelmediği doğrulanmadı. GPL: Kdenlive'i ayrı süreç olarak çalıştırmak sorun değil; kodunu bağlamak GPL yükümlülüğü getirir.

## 3. OpenCut

**Kimlik.** Ana repo 99k yıldıza rağmen **"being rewritten from the ground up"**: Editor API, plugin mimarisi, Rust çekirdek, MCP ve headless mod *gelecek* listesinde ([README](https://github.com/OpenCut-app/OpenCut/blob/main/README.md)). Klasik kod tabanı `opencut-classic` **arşivli ve bakımsız** ([README](https://github.com/opencut-app/opencut-classic/blob/main/README.md)); `opencut.app` hâlâ klasik sürümü çalıştırıyor ve "early beta" diyor ([site](https://opencut.app)).

Klasik sürüm: Next.js 16, Bun, Drizzle/Postgres, `mediabunny`, `opencut-wasm` (Rust/wgpu) ([package.json](https://github.com/opencut-app/opencut-classic/blob/main/apps/web/package.json)). Projeler **IndexedDB/OPFS**'te ([storage](https://github.com/opencut-app/opencut-classic/tree/main/apps/web/src/services/storage)); export tarayıcı içinde `ArrayBuffer` olarak mp4/webm ([export](https://github.com/opencut-app/opencut-classic/blob/main/apps/web/src/export/index.ts)). Yani: dosya tabanlı proje yok, CLI/API yok, headless yok, tarayıcı kotası ve WebCodecs sınırları geçerli. **Bugün bir otomasyon hedefi değil.**

## 4. İçeride mi, yanında mı? — lisans ayrımı

| Araç | İçeride (link/embed) | Yanında (ayrı süreç/dosya) |
| --- | --- | --- |
| **Concat** | AGPL: kapalı kaynak üründe gömülüyorsa kaynak açma yükümlülüğü; ticari lisans gerekir ([LICENSING](https://github.com/jub0t/Concat/blob/main/LICENSING.md)). | Belgeler açıkça "API üzerinden konuşan program **client**'tır" diyor; ayrı süreç + dosya/JSON-RPC sınırı AGPL bulaşmasını önler. Yine de hukuki görüş alın. |
| **Kdenlive** | GPL-3.0-only; kod bağlamak GPL. | Ayrı uygulama olarak çalıştırmak normal kullanım. |
| **MLT** | LGPL-2.1; dinamik link + yeniden linkleme koşuluyla kapalı kaynakta kullanılabilir; bazı modüller farklı lisansda olabilir. | `melt`/`libmlt` ayrı süreç veya sistem kütüphanesi olarak en temizi. |
| **OpenCut** | MIT; gömme serbest. | Ama gömülecek olgun bir çekirdek/API yok. |

**Sonuç:** Concat'i "motorun render kütüphanesi" yapmak hem lisans hem beta riski; "ajanın kurgu masası" yapmak makul. Kdenlive'i motora bağlamak GPL + ikinci kompozitör demek; yalnız insan review'ında tutulmalı.

## 5. Entegrasyon desenleri (efor/fayda sırasıyla)

| # | Desen | El değiştiren artefakt | Gereken | Tipik arıza |
| --- | --- | --- | --- | --- |
| **P0** | **FFmpeg concat demuxer** (baz çizgi) | `list.txt` (`ffconcat version 1.0`, `file ...`) + aynı parametreli MP4'ler | Tüm kliplerde aynı codec, timebase, çözünürlük, fps, ses layout ([FFmpeg](https://ffmpeg.org/ffmpeg-formats.html#concat-1)) | Parametre uyuşmazlığı, ses boşluğu, PTS kayması; `-c copy` bozuk çıktı |
| **P1** | **Manifest → FFmpeg filtergraph** | `sahne.json` (dosya, in/out, fps, overlay, ses stem'leri) → `filter_complex` | Sabitlenmiş FFmpeg, engine'in uniform render profili | Karmaşık graph okunaksız; hata mesajları zayıf; GPU'ya göre bit farkı |
| **P2** | **Concat MCP ile kurgu/QC** | Sahne MP4'leri + WAV stem + (varsa) SRT | Concat kurulumu, `--mcp headless`, `CONCAT_MCP_ROOTS`, proje klasörü | MP4-only, alfa yok, tek export, beta API, kilit/izin hataları |
| **P3** | **Manifest → MLT XML → `melt`** | `.mlt` XML (producer/playlist/tractor) | MLT + `melt`, codec'ler, doğru profil | XML doğrulanmıyor; efekt eşlemesi; Windows'ta `melt` yokluğu |
| **P4** | **Kdenlive `--render`** | İnsanın düzenlediği `.kdenlive` | Kdenlive, preset adı, GUI oturumu | Belgesiz CLI, sürüm formatı, render preset bağımlılığı |
| **P5** | **OpenCut review** | Tarayıcıya yüklenen medya | Tarayıcı veya self-host | Otomasyon yok, proje dışa aktarılamıyor, rewrite bitmemiş |

**P0 notu:** `-c copy` yalnız gerçekten aynı stream parametrelerinde güvenli; FFmpeg "All files must have the same streams (same codecs, same time base, etc.)" diyor. Farklı çözünürlük/fps varsa concat **filter** ile yeniden kodlamak gerekir; bu P1'dir.

**P2 notu:** Concat'e verilecek dosyalar tek tip olmalı: H.264/AAC MP4, sabit fps ve çözünürlük, harici WAV stem'ler. Alfa gereken overlay'ler Concat'e girmeden FFmpeg'de arka planla birleştirilmeli. `preview_frame` ajanın kareyi görmesini sağlar; `export_wait` ilerleme verir.

**P3 notu:** MLT XML elle üretilebilir ama parser non-validating; hatalı property sessizce yok sayılır. Kdenlive'e özel property'ler olmadan sade bir MLT timeline üretmek, `.kdenlive` üretmekten daha güvenli. Yine de HyperFrames'in GSAP/HTML kompozisyonunu MLT'de yeniden kurmak anlamlı değil; MLT yalnız **hazır klipleri** birleştirmeli.

## 6. Bu proje için önerilen mimari

**Tek zaman çizgisi kuralı:** Zamanlama, kamera, harita ve tipografi HyperFrames kompozisyonunda kalır. Hiçbir NLE ikinci bir "master timeline" olmaz.

1. **Kaynak:** `sahne.json`/`Senaryo.md` → HyperFrames kompozisyonları. Kare hızı ve çözünürlük manifestte sabit; `--fps` rasyonel (ör. `30000/1001`) ve `--docker` ile determinist render ([CLI](https://github.com/heygen-com/hyperframes/blob/v0.9.77/docs/packages/cli.mdx)).
2. **Motor çıktısı:** sahne başına H.264/AAC MP4 (aynı profil) + anlatı/müzik/SFX için ayrı WAV + gerekiyorsa alfalı WebM/ProRes 4444 overlay + PNG dizisi.
3. **Birleştirme:** varsayılan **P0**; parametreler karışıyorsa **P1**. Bu adım motorun render sözleşmesinin parçası; ayrı bir "kurgu aşaması" değil.
4. **İnsan review:** gerekirse Kdenlive'e **yalnız nihai MP4'ü** (veya P3 ile üretilmiş sade MLT XML'i) aç; kesme/ritim notları manifeste geri yazılır, `.kdenlive` master olmaz. Concat'i ajanla denemek istiyorsan **P2**: birleşmiş MP4 üzerinde trim/başlık/altyazı ve `preview_frame` ile QC; çıktı yine MP4.
5. **OpenCut:** rewrite Editor API/headless/MCP duyurulmadan değerlendirmeye alma.

**Neden Concat "içeride" değil:** AGPL + beta + MP4-only. **Neden Kdenlive "içeride" değil:** GPL + ikinci kompozitör + MLT XML bakımı. **Neden FFmpeg yeterli:** mevcut kurulum, tek süreç, determinist ve alfa/format sınırı yok; eksik olan tek şey insanın ritim denemesi, o da NLE'nin işi.

## 7. Windows deneme kontrol listesi

| Araç | Gerekli | Disk / hesap | Risk |
| --- | --- | --- | --- |
| **FFmpeg** | Kurulu 9.0.2; concat demuxer + libx264/AAC | — / yok | Seçili dağıtımda codec/font/alfa desteğini doğrula |
| **Concat** | Windows 10/11 x64; setup 97 MB veya MSI 113 MB; D3D12 GPU opsiyonel (yoksa CPU) | ~500 MB uygulama; opsiyonel modeller ~2,8 GB / hesap yok | İmzasız build → SmartScreen; AGPL; beta; tek export |
| **Kdenlive** | Windows 10+ standalone kurulum; MLT dahil | Boyut doğrulanmadı / hesap yok | GPL; `melt` ayrıca gerekebilir; `--render` belgesiz |
| **MLT/melt** | Ayrı kurulum veya Kdenlive içinden; FFmpeg modülleri | Doğrulanmadı / yok | Windows ikilisi resmî pakette yok; kaynaktan derleme |
| **OpenCut** | Güncel Chrome/Edge; self-host için Bun + Docker + Postgres + Redis | Tarayıcı kotası / self-host hesapsız | Arşivli klasik; rewrite bitmemiş; API yok |

## 8. Artı/eksi ve karar matrisi

| Ölçüt | FFmpeg | Concat | Kdenlive/MLT | OpenCut |
| --- | --- | --- | --- | --- |
| Headless Windows | **3** | **2** (MCP headless var, denenmedi) | 1 (`--render` GUI başlatır) | 0 |
| Ajan/CLI kontrolü | **3** | **3** (MCP/JSON-RPC) | 1 (`--render`, `melt`) | 0 |
| Zaman çizgisi kurma | 1 (elle graph) | **3** | 2 (XML üret) | 1 |
| Alfa/transparanlık | **3** | 0 | 2 | 1 |
| Format/codec özgürlüğü | **3** | 1 (MP4 only) | **3** | 1 |
| Determinizm | 2 | 1 (donanım encoder) | 2 | 1 |
| Olgunluk/bakım | **3** | 1 (beta) | **3** | 0 |
| Lisans rahatlığı | **3** | 1 (AGPL) | 1 (GPL/LGPL) | **3** (MIT) |
| Kurulum maliyeti | **3** | 2 | 1 | 1 |
| **Toplam (yaklaşık)** | **24** | **14** | **16** | **8** |

## 9. Pilotla doğrulanacaklar

1. **Concat headless:** Windows'ta `concat --mcp headless` ile proje oluştur, 3 MP4 + WAV içe al, `clips_add_sequence`, `preview_frame`, `export_wait`. Aynı girdiyle iki export'un kareleri aynı mı? Kesim gerçekten karede mi? Kilit/izin hataları nasıl?
2. **Alfa:** HyperFrames `webm`/`mov`/`png-sequence` çıktısını Concat ve Kdenlive'e al; alfanın korunup korunmadığını ölç. Concat'te beklenen: kayıp.
3. **FFmpeg P0/P1:** Aynı profilli 3 sahnede `-c copy` ile concat; ses senkronu, ilk kare, süre sapması. Farklı fps'te filter'a geçiş.
4. **MLT:** Elle yazılmış 3 producer'lı MLT XML'i Windows `melt` ile render et; Kdenlive kurulumunda `melt` var mı? `kdenlive --render proje.kdenlive cikti.mp4 --render-preset ...` çalışıyor mu?
5. **OpenCut:** Rewrite'ta Editor API/headless/MCP gerçekten çıktı mı? Klasik sürümde proje dışa aktarma var mı, export alfa taşıyor mu?
6. **Windows gerçekleri:** Türkçe karakterli yol, boşluk, uzun path, tek sürücü; her araçta aynı medya setiyle.

## Öneri

**Şimdi hiçbir NLE kurma.** Motorun render sözleşmesini (sabit fps/çözünürlük/codec, ayrı ses stem'leri, alfalı overlay) netleştir ve birleştirmeyi FFmpeg'de tut. Concat'i yalnız "ajanın kurgu masası" olarak, ayrı süreç ve ayrı proje klasörüyle dene; üretim render'ı ona bağlama. Kdenlive'i yalnız insan ritim/audio review'ı için, nihai MP4 üzerinden aç. OpenCut'i rewrite Editor API ve headless mod yayınlanana kadar listeye alma. İki timeline'dan biri mutlaka ölür; master HyperFrames kalsın.
