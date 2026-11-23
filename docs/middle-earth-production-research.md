# Orta Dünya video serisi — montaj ve karakter araştırması

2026-11-22 · Kaynak incelemesi ve pilot önerisi. Onaylanmış tasarım, bölüm senaryosu veya render değildir. Genel motor araştırması: [Video serisi araştırması](video-series-asset-research.md). Harita ve stok kayıtları: [Varlık kataloğu](middle-earth-asset-catalog.md).

## Referanslardan doğrulananlar

- **[Nerdoloji: Orta Dünya 1. Çağ Haritalı Anlatım](https://www.youtube.com/watch?v=n5n4d3xVgao).** Yayıncı açıklaması, *Silmarillion*'un Birinci Çağ olaylarını harita üzerinden anlatan bölümlerin derlemesi olduğunu söylüyor. Açıklamadaki zaman kodları arasında Silmaril ve Feanor (`05:52`), Ani Alev Savaşı (`14:14`), Sayısız Gözyaşı Savaşı (`27:40`) ve Öfke Savaşı (`1:01:57`) var. Buradan alınabilecek doğrulanmış yaklaşım **olay bazında bölümleme ve haritalı anlatım**. Kamera, animasyon, ses ve kesme analizi yapılmadı.
- **[Moli | Kıssadan Hisse: Kimse kendi kirli elini görmek istemez](https://www.instagram.com/reel/Df44pISih4Y/).** Gönderi başlığı/hesabı doğrulandı; hareketli içerik kare kare incelenmedi. Bu yüzden kısa illüstrasyonlu anlatım için aday referans, belirli bir montaj tekniğinin kanıtı değil. Daha ayrıntılı inceleme için izlenebilir kopya veya kullanıcının işaretlediği zaman aralığı faydalı.

İki referans da **inceleme amaçlı**. Açıklamadan bölüm kopyalamak, görsel, ses, müzik, karakter tasarımı veya metin aktarmak önerilmiyor.

## Montaj ve animasyon

| Biçim | Uygulama ve getirisi | Sınırı |
| --- | --- | --- |
| **Hareketli ambiyans** | Uzak arazi, orta planda sis, önde silüet gibi bağımsız katmanlara küçük, farklı hızlarda hareket ver. Açılışta mekânı hissettirir; anlatımın bir sonraki fikrine yer açar. | İzleyici bu sahneden savaşın yönünü ya da kronolojisini çıkarmamalı. Stok manzarayı “Beleriand'ın gerçek görüntüsü” gibi sunma. Sis ve görüntü hareketi etiket/altyazıyla yarışmasın. |
| **Didaktik hareketli grafik** | Tek karede tek soru. Ekrandaki kısa yer adı, zaman veya sonuç kartı, anlatıcı o kavramı söylediğinde belirir. Önce/sonra karesi ayrıca okunur bir infografiğe dönüşebilir. | Çok sayıda özel ad ve altyazı aynı yerde okunmaz. Özellikle Türkçe karakter, Tolkien adlarının yazımı ve yer etiketleri küçük ekran boyutunda kontrol edilmeli. |
| **Hareketli harita** | Aynı koordinat alanında coğrafya, yer adları, olay göstergeleri ve karakter simgeleri ayrı katmanlar. Önce konum, sonra tek görünür değişim, ardından sonucu okumak için durak. Tarafları renkle birlikte şekil/simgeyle ayır. | Edebi kaynak kesin rota, ölçek veya sayı vermiyorsa animasyon bunları icat etmesin. Açıklayıcı veya tahmini ilişkiyi lejantta işaretle. Kamera hareketi ve yeni bilgi mümkünse aynı anda gelmesin. |

**Önerilen iş sırası:** Kaynak notu ve özgün Türkçe anlatım metni → geçici ses kaydı → cümle/sahne eşleşmesi → basit zamanlamalı taslak → görsel/animasyon → harita, ses ve altyazı kontrolü → onaylı video ve aynı sahneden ayrı statik infografik. Ses, kesme ve animasyonu belirler; kesin süreyi kayıttan önce dayatma. Ambiyans, anlatım ve müzik ayrı ses katmanları olsun. Özel adlar için telaffuz listesi tut; otomatik altyazıyı elle düzelt. Film müziği ve referans videonun sesi kullanılmasın.

İlk taslakta sahne başına **anlatım cümlesi / ekrandaki değişim / bilgi kaynağı / varlık sürümü** yeterli. Bölüm için yatay harita ana kadraj olabilir; dikey bir kesit gerekiyorsa tüm haritayı otomatik kırpmak yerine yalnız ilgili bölge, başlık ve lejantla yeniden kadrajla. Statik özet, animasyonla kaybolan öğelere bağımlı olmadan bağlamı, sonucu ve kaynak notunu göstermeli.

- **HyperFrames + SVG/GSAP:** Aynı tabandan birden fazla bölüm üretmek için ilk tercih. Harita ve işaretçiyi birlikte hareket ettirirken zaman çizgisi belirli bir kareye sıçrayabilmeli; dekoratif döngüler de sahne süresine bağlı olmalı. Kamera durduğunda okunur bir infografik karesi planla. `hyperframes` sahne/render sözleşmesi, `hyperframes-cli` önizleme ve kontrol, `hyperframes-registry` hazır düzenlenebilir bloklar, `media-use` yerel medya ve ses girdileri için. [Animasyon rehberi](https://hyperframes.heygen.com/guides/gsap-animation.md) · [Ses ve altyazı](https://hyperframes.heygen.com/guides/voice-and-audio.md).
- **Kdenlive:** El ile farklı kurgu ritimlerini denemek veya ambiyans görüntüleri baskınsa mantıklı; ana kareli konum, büyütme ve katman kompozisyonu var. Harita adları, durumlar ve işaretçiler her yeni bölümde tek tek taşınmaya başlarsa HyperFrames daha az tekrar gerektirir. Hibrit kullanımda harita kaynağı HyperFrames'te, son kesme ve ses kurgusu editörde kalır; aynı ana zaman çizgisini iki yerde sürdürme. [Kdenlive Transform](https://docs.kdenlive.org/en/effects_and_filters/video_effects/transform_distort_perspective/transform.html).
- **Blender:** Çok katmanlı illüstrasyon, gerçek kamera değişimi veya tekrar kullanılan karmaşık karakter hareketi sonraki bölümlerde darboğaz olursa değerlendir. Grease Pencil ile 3B sahne içinde çizim mümkün; başlangıçta rig, ışık, kaynak dosya ve ayrı render yükü getirir. [Grease Pencil](https://docs.blender.org/manual/en/latest/grease_pencil/introduction.html).

## Karakter ve avatar: üç ayrı rol

| Rol | En küçük işe yarayan çözüm | Ne zaman büyütülür? |
| --- | --- | --- |
| **Haritadaki kişi veya topluluk** | Okunur silüetli özgün SVG simgeleri; renk + şekil + kısa isim. Bir simgenin konum değiştirmesi, çok sayıda oynayan figürden daha rahat okunur. | Aynı figürler büyüyüp sahne içinde jest/oyunculuk sergilemeye başladığında eklemli çizime geç. |
| **Yakın plan kurmaca karakter** | Özgün portre, iki-üç poz ve ayrı yüz/pelerin katmanları. Hareket gerekiyorsa nefes, ışık veya kumaş hareketi; ilk turda diyalog ve dudak eşleme yok. | Kimlik bölümler arasında tutuyorsa ön/yan/üç çeyrek referansı, palet ve poz setini sabitle. Tam figür/çok açı gerekiyorsa Blender veya bir 2D rig üretim aracı. |
| **Sunucu avatarı** | Pilot için ekrana çıkmayan özgün Türkçe insan sesi. Sonradan farklı bir format gerekirse evrenin içinden biri olmayan özgün 2D anlatıcı. | Kamera karşısı sunum gerçekten tercih edilirse ve Türkçe numune ikna ederse HeyGen; yüz/ses izni, yükleme, ücret ve saklama koşulları baştan onaylanır. Film oyuncusunun yüzü, sesi, kostümü veya ayırt edici tasarımı taklit edilmez. |

Karakter kartında sabit kimlik/sürüm, silüet, palet, pozlar, ses/telaffuz, kaynak ve izin kaydı bulunmalı. Bölümde yeniden üretmek yerine onaylı çizim kullanılır. Üretken görsel araçları gerekirse tekil atmosfer planlarında denenebilir; bölümden bölüme aynı yüzü veya kanonik coğrafyayı koruyan ana kaynak olarak kullanılmamalı.

**Üretim sınırı:** Yalnız konum, pelerin salınımı veya baş dönüşü için katmanlara ayrılmış SVG yeterli. Aynı figür defalarca yürüyecek veya jest yapacaksa [Synfig iskelet katmanı](https://wiki.synfig.org/Skeleton_Layer) gibi yerel 2D rig araçları değerlendirilebilir; bu aşamada düzenlenebilir ana dosya ve şeffaf çıktı birlikte saklanır. Çizimi tekrar üretmekten daha maliyetli ilk kurulum, ancak hareket gerçekten tekrar kullanılacaksa karşılığını verir. Final seçimi Windows'ta şeffaf çıktı ve içe aktarma denemesine bağlıdır.

**Türkçe ses:** Pilot için gerçek kayıt en az belirsizlikli seçenek. Yerel sentetik ses araştırılırsa [Piper Türkçe `dfki` model kartı](https://huggingface.co/rhasspy/piper-voices/blob/main/tr/tr_TR/dfki/medium/MODEL_CARD) eğitim verisini CC BY-NC-SA olarak listeliyor; bu nedenle modeli veya çıktıyı ayrıca incelemeden ticari yayın için onaylı sayma. İnsan ve sentetik seçenekleri aynı kısa özel adlar metniyle dinleyerek kıyasla.

## İlk seri önerisi ve pilot

**Çalışma adı: “Beleriand: Birinci Çağ'ın Kırılma Noktaları”.** Önce dar bir sorulu **Ani Alev Savaşı** pilotu: *Bu olay Beleriand'daki dengeyi nasıl değiştirdi?* Bir atmosfer sahnesi, bir kaynaklı harita anlatımı ve bir önce/sonra özeti; **60–90 saniye ve tek eşlikçi infografik** ilk öneri. Devam adayı **Sayısız Gözyaşı Savaşı**; ikinci bölüm aynı görsel sistemi kullanarak daha sonraki kırılmayı anlatır, iki olay arasındaki zamanı atladığını saklamaz.

Animatikten önce *Silmarillion*'un kullanılan baskısındaki **“Of the Ruin of Beleriand and the Fall of Fingolfin”** bölümünden yer, sıra ve sonuç kontrolü yapılmalı; ikinci pilot için **“Of the Fifth Battle: Nirnaeth Arnoediad”**. [Yayınevi kitap kaydı](https://www.harpercollins.com/products/the-silmarillion-j-r-r-tolkien) metnin yerine geçmez. Senaryonun her maddesi “metinde açık / editoryal yorum / belirtilmemiş” diye ayrılmalı; eser metni okunmayacak veya kopyalanmayacak.

Pilotun başarısı: harita ilk bakışta okunuyor, karakter simgesi küçük boyutta ayırt ediliyor, Türkçe ad ve altyazı doğru, özet karesi ses olmadan iş görüyor ve ikinci bölüm aynı onaylı varlıkları yeniden ürettirmiyor. **Pilot ile yayın kararı ayrı.** [Tolkien Estate SSS](https://www.tolkienestate.com/frequently-asked-questions-and-links/) orijinal harita ve görsellerin telifli olduğunu; uyarlamalar konusunda hak sahibinin kısıtlayıcı tutumunu bildiriyor. Kendi grafiklerimiz üçüncü taraf dosya bağımlılığını azaltır, fakat uyarlama veya ticari kullanım izinlerini kendiliğinden sağlamaz. Yayın öncesi seçilen anlatımın, haritanın, başlığın ve varlıkların hakları kullanım bağlamına göre incelenmeli. Şimdilik yerel araştırma ve taslak; araç kurulumu, varlık indirme, render veya yayın yapılmadı.
