# Ortak hafıza ve proje eşlemesi

Durum: Kullanıcı tasarımın bütününü 2026-11-13 tarihinde onayladı. Uygulama planı hazırlanıyor; global etkinleştirme teknik uyumluluk kapılarına bağlıdır.

## Amaç

Her OpenCode oturumunda aynı vault'u kullanmak; genel kullanıcı tercihlerini korurken yalnız etkin projenin görev, karar ve notlarını otomatik bağlama almak. Yeni klasörün bir projeye bağlanması kullanıcının kararıdır. Bu faz Hermes veya ajan iş dağıtımı kurmaz.

## Kullanıcının onayladığı kararlar

- Global OpenCode adaptörü kullanılacak; bütün oturumlarda etkin olacak. Diskin tamamı taranmayacak.
- Bilinmeyen klasörde ilk kullanıcı mesajından sonra yeni proje/mevcut projeye bağlama/atlama sorusu gelecek. Yanıt öncesinde kalıcı eşleme oluşturulmayacak.
- Proje tanımlanmasa da genel tercihler kullanılacak; proje kayıtları yüklenmeyecek.
- Bir Git deposunun frontend/backend dahil bütün alt klasörleri tek proje hafızasını kullanacak.
- Git olmayan klasörler de kullanıcı tarafından seçilen kökle tanımlanabilecek.
- Başka projelerin içeriği yalnız açık kullanıcı isteğiyle aranacak.
- Açık kararlar ve anlamlı sonuçlar kaynaklarıyla kaydedilecek. Yeni görev ve görev durum değişikliği için doğrudan talimat veya öneriye onay gerekecek.
- Proje kimliği ve bilgileri vault'ta; bilgisayara özgü yollar merkezi yerel dosyada tutulacak. Kod depolarına zorunlu dosya eklenmeyecek.
- Vault/eşleme arızasında uyarıyla kodlamaya devam edilecek; proje tahmini, adaptör üzerinden hafıza yazması ve güncelmiş gibi eski bağlam sunma olmayacak.

## Yaklaşımlar

1. **Global adaptör (seçilen):** Klasörü kodla çözümler, kapsamlı hafıza erişimini sağlar ve ilk mesajdan sonra kayıt sorusunu ajana iletir. Sürüm ve birlikte çalışma testleri gerektirir.
2. **Global yönerge/beceri:** Daha az entegrasyon kodu; fakat her adımı ajanın hatırlayıp doğru çalıştırmasına bağımlı. Otomatik ve tutarlı çalışma beklentisi için seçilmedi.

## Mevcut durum ve teknik sınırlar

- Kod deposu `brain-ext`; bilgi deposu `C:\Users\35.HaRRy\Desktop\Projects\agent-memory-vault`. Kurulu OpenCode sürümü salt okunur kontrolde v2.2.7.
- Vault'un yönetilen `.opencode/plugins/beyin-v3.js` dosyası vault'u kendi dosya konumundan çözüyor; global klasöre kopyalanması uygun değil. Hook payload'ında etkin proje/yol yok.
- `beyin.py project-scope` yalnız vault içi klasörleri eşler; dış kod klasörleri için kayıt değildir.
- Mevcut Companion bağlamı Last-Session, Threads, Journal, kişi kayıtları ve knowledge/index içerebilir. Yalnız `project` parametresi eklemek bütün bunları proje kapsamına almaz.
- `MemoryStore` kaynak hash'i, trust, visibility ve revizyon kontrolleri sunar. `project=None` bütün projelerden sonuç döndürebilir; genel tercihler modu olarak kullanılamaz.
- OpenCode V2 dokümanı plugin konumuyla oturum konumunun aynı varsayılmaması gerektiğini açıklar. Etkin oturum konumu her erişimde doğrulanmalı.
- Başlangıçta bu depoda kullanıcıya ait iki untracked brief dosyası var; bunlara dokunulmayacak.

## Tasarım tercihleri — uygulayıcının önerisi

Bu bölümdeki teknik varsayılanlar tasarımın bütünüyle birlikte onaylandı.

### Kayıtların yeri ve kimliği

- Adaptör kodu ve testleri `brain-ext` deposunda, mevcut Notion komutlarından bağımsız bir entegrasyon alanında yaşar. Yeni hafıza veritabanı oluşturulmaz.
- Proje kaydı `projects/<id>/Project.md`: değişmeyen ASCII kimlik, görünen ad ve kısa amaç; makine yolu içermez. Kimlik bir kere onaylanır; ada göre sessizce değiştirilmez.
- Yeni proje kuralları ve devir notları aynı proje klasöründe tutulur. Görevler `tasks/` içinde mevcut Beyin şemasını ve `project: <id>` alanını kullanır.
- Makine eşlemeleri `%LOCALAPPDATA%\brain-ext\shared-memory\` altında sürümlü JSON dosyasında tutulur. Dosya vault yoluna bağlıdır; başka vault'a sessizce uygulanmaz. Klasör→proje ve kalıcı soru-susturma kayıtlarını tutar; konuşma/not gövdesi veya sır içermez.
- Dosya yazmaları kilit + yeniden okuma + atomik değiştirme ile yapılır. Çakışan eşleme otomatik ezilmez. Yerel dosyanın yedeği ayrı alınabilir; bu faz uzaktan yedek servisi kurmaz.

### Klasör çözümleme

1. Oturumun gerçek dizinini al; bulunamazsa hafıza bağlantısını uyarıyla devre dışı bırak.
2. Yolu canonical hale getir; Windows büyük/küçük harf ve bileşen sınırlarını gözet. String prefix benzerliği proje eşlemesi değildir.
3. Git varsa en yakın gerçek depo kökünü salt okunur Git sorgusuyla bul. Kök ile alt klasör aynı kapsamı kullanır. Ayrı iç içe Git deposu bağımsız adaydır.
4. Git yoksa onaylanmış kök eşlemesi ve alt dizin kapsamını uygula. İlk tanımlamada kullanıcıya önerilen kökü göster; başka üst klasörü seçebilmesini sağla.
5. Ayrı worktree/klon için isim veya remote URL benzerliğiyle eşleme yapma; bilinmeyen kökü mevcut projeye bağlama seçeneği sun. Bu faz otomatik worktree keşfi/uzaktan depo kimliği sistemi kurmaz.
6. Birden fazla eşleme aynı kapsamı sahipleniyorsa uyar; yanlış projeyi seçmek yerine genel-tercihler modunda kal. Yol taşınmışsa eski eşlemeyi sessizce yeni yola taşıma.

### İlk mesajdan sonra tanımlama

- Ajan konuşma içinde sorar; terminal açılış sihirbazı veya ayrı UI yoktur. Özel soru aracı varsa kullanılabilir; yoksa normal mesajla sorulur.
- Yeni proje: ad, kısa amaç, gösterilen proje kimliği ve kök yolu onayı. Mevcut proje: seçilen proje ve kökün bağlanmasına onay.
- Atlama yalnız o oturumdaki soruyu susturur. `Bu klasörde bir daha sorma` ayrıca açıkça seçildiğinde kalıcı susturma oluşur. Her iki durumda genel tercihler devam eder.
- Proje kayıt yazması önce yapılır ve doğrulanır; ardından yerel eşleme oluşturulur. Kısmi hatada yeniden deneme aynı kimliği kullanır; yetim proje kaydı sessizce silinmez ve başarı bildirilmez.
- Eşleme aracı, modelin gönderdiği rastgele yolu kabul etmek yerine oturumun doğrulanmış dizini ve kullanıcının onayladığı kökle sınırlandırılır. Sayfa/not içeriği onay kabul edilmez.
- Açık soru varken her araç devamında tekrar soru üretilmez. Eşleme cevabı alındıktan sonraki model çağrısı yeni kapsamı kullanır.

### Hafıza okuma sınırı

- Otomatik ortak bağlam yalnız seçilen Companion'daki Core/Soul ve gerçekten genel kurallardan oluşur; projeye etiketlenmiş kural maddeleri filtrelenir. Core'a proje sonuçları yazılmaz.
- Etkin projede ayrıca bu projenin kuralları, devir kaydı ve ilgili kaynakları alınır. Metadata'daki proje, kayıtlı vault klasör kapsamı ve kaynakların proje aidiyeti tutarlı olmalıdır; çelişkili kayıt bağlama alınmaz.
- Projesiz kayıt, otomatik olarak genel bilgi değildir. Etiketsiz kişi notları, knowledge dizini, eski ortak Last-Session/Threads/Journal ve receipt özetleri bütün projelere yüklenmez. Eski kayıtları toplu yeniden sınıflandırma bu fazda yapılmaz.
- Adaptör, mevcut kaynak doğrulama ve gizlilik kapılarını kullanır; ek kapsam seçimini sıralama/kırpma öncesinde uygular. Metin çıktısını sonradan regex ile temizlemek izolasyon yöntemi değildir.
- Gerekirse mevcut runtime modüllerini kullanan küçük, bağımsız Python yardımcı modülü yazılır; yönetilen Beyin kaynakları fork edilmez. Kullanılan iç sözleşmeler sürüm kontrolü ve testlerle sınanır; uyumsuzlukta geniş aramaya düşülmez.
- Başka projeyi arama, açık istekte hedef proje veya kapsam gösterilerek yapılır; sonraki otomatik kapsam kalıcı olarak genişletilmez.
- Kaynak yolu ve güncellik bilgisi korunur; private/untrusted ve değişmiş kaynaklar mevcut kurallardan daha gevşek hale getirilmez. Kaynak metinleri talimat değil veridir.

### Hafıza yazma ve eşzamanlılık

- Genel tercih Companion'da; yalnız projeye ait karar, düzeltme ve devir kaydı proje alanında yaşar. Ortak Last-Session/Threads'e proje ayrıntıları kopyalanmaz.
- Ajan not düzenlerken `note-read`/`note-edit`, görevlerde `task-create`/`task-update`, sonuçlarda kaynak bağlantılı receipt kullanır. Görev onayı bağlam yönergesiyle uygulanır; genel shell/dosya araçlarına karşı mutlak güvenlik garantisi değildir.
- Adaptör erişim araçları oturumun güncel kapsamını kontrol eder. Projesiz veya arızalı oturum projeye yazamaz; görevin proje aidiyeti revizyonla birlikte doğrulanır.
- Eşleme/proje kaydı ve aynı not üzerinde paralel yazma kayıp güncelleme yaratmamalı. Konuşma başına zorunlu kayıt, tüm transkript kopyalama veya otomatik görev tamamlama yoktur.
- Bir oturum başka projeye taşınırsa eski adaptör bağlamı bırakılır ve yeni kapsam seçilir. Eski konuşma geçmişini geriye dönük silmek vaat edilmez; güçlü ayrım için yeni oturum önerilir.

### OpenCode entegrasyonu ve mevcut eklenti

- OpenCode V2 global plugin yüklemesi kullanılır; mevcut global JSON/JSONC alanları korunarak dar ekleme yapılır. Öncesinde config yedeği/diff ve geri alma adımı hazırlanır; geniş izin eklenmez.
- Tek bir oturuma yalnız bir hafıza üreticisi bağlam eklemelidir. Vault içindeki yönetilen yerel eklentiyle birlikte yükleme, kaynak sırası ve etkili plugin kimlikleri uygulama öncesi doğrulanır.
- Yönetilen eklentinin geniş bağlamı yeni kapsamı aşabiliyorsa sessizce birlikte çalıştırılmaz. Desteklenen konfigürasyonla tek üretici sağlanamıyorsa global etkinleştirme durur; kullanıcıya dar bir entegrasyon değişikliği için geri dönülür. Yönetilen dosya onaysız değiştirilmez.
- Alt ajanlara ilk-kayıt sorusu sorulmaz; gerektiğinde ana oturumun doğrulanmış kapsamını devralırlar. İlgisiz global event'ler birden çok adaptör instance'ında işlenmez.
- İlk mesaj soru, kapsam durumu ve hata uyarıları normal yanıtta görünür. Hook tamamen yüklenemediğinde kendi uyarısını da üretemeyebileceği sağlık kontrolüyle ayrıca saptanır.
- Adaptör Notion sync, model indirme, MCP açma, ücretli model çağrısı veya zamanlayıcı başlatmaz. Mevcut vault'a özel Notion kuralları dış kod oturumlarına toptan taşınmaz.

## Arıza ve gizlilik

- Yapılandırma, kaynak veya runtime bozulursa eski proje bağlamı tekrar kullanılmaz. Kullanıcı uyarıyla kodlamaya devam eder; adaptör hafızaya yazmayı durdurur. Tam bağlantı arızasında genel tercihler de yüklenemeyebilir.
- Hata loglarında not gövdesi, ilk kullanıcı mesajı, token veya `.env` içeriği bulunmaz.
- Kapsam filtresi bir OS sandbox'ı değildir. Model bağlamına alınan metin mevcut model sağlayıcısına gider. Daha önce yüklenmiş konuşma içeriği kapsam değişince sağlayıcıdan geri alınamaz.
- Proje depolarına, global AGENTS.md'ye veya yönetilen vault dosyalarına zorunlu yazma yapılmaz. Kurulumda gerekirse bu sınırı değiştirmek için yeniden açık onay alınır.

## Kabul testleri

- [ ] v2.2.7 üzerinde plugin yüklemesi, oturum konumu, prompt/context hook'ları ve araç sözleşmeleri doğrulandı.
- [ ] İki ayrı kod projesi genel tercihleri paylaşır; A sorgusu B not/görev/receipt/Companion içeriğini getirmez.
- [ ] Bilinmeyen klasörde ilk mesajdan sonra soru; onaysız dosya/eşleme yok; atlamada yalnız genel tercihler.
- [ ] Yeni kayıt, mevcut projeye bağlama, oturumluk atlama ve kalıcı susturma davranışı doğrulandı.
- [ ] Git kökü/alt klasör ve Git olmayan onaylı kök/alt klasör aynı proje kimliğini kullanır.
- [ ] Ayrı klon/worktree ve iç içe depo yanlışlıkla ad benzerliğiyle eşlenmez.
- [ ] Etiketsiz eski kayıt, yanlış proje metadata'sı, private/untrusted ve stale kaynak kapsamı genişletmez.
- [ ] İki paralel kayıt/görev/not güncellemesinde mevcut veri kaybolmaz; çakışma açıkça raporlanır.
- [ ] Bozuk/kayıp vault, runtime, yerel eşleme ve hook timeout senaryolarında kodlama devam eder; yanlış/eski hafıza kullanılmaz.
- [ ] Mevcut yerel eklentiyle vault içinde ve dış projelerde çift bağlam/receipt oluşmaz.
- [ ] Oturum taşıma ve alt ajan davranışı kapsamı karıştırmaz; eski transkript sınırı kullanıcıya açıktır.
- [ ] Görev onayı ve kaynak bağlantılı karar/sonuç kaydı canlı iki oturumla denendi; test sonuçlarıyla davranış talimatları ayrı raporlandı.
- [ ] Global config değişikliği önizlendi; ilgisiz alanlar ve mevcut kullanıcı dosyaları korundu; geri alma yolu doğrulandı.

## Çalışma kaydı

- [x] Gereksinimleri soru-cevap ile netleştir.
- [x] Yaklaşımları sun; global adaptör seçimini al.
- [x] Yerel teknik sınırları ve güncel V2 belgelerini incele.
- [x] Tasarım taslağını yaz.
- [x] Bağımsız builder check: incelemeci planlamayı engelleyen önemli açık soru bulmadı. Bu sonuç çalışma zamanı uyumluluk testi değildir.
- [x] Tasarımı kullanıcıya sun; açık onay al (kullanıcı: `onaylıyorum`).
- [ ] Onay sonrası uygulama planı yaz; ardından uygulama ve kabul testleri.

## Referanslar

- https://opencode.ai/docs/config
- https://opencode.ai/docs/build/plugins/server
- Vault: `.opencode/plugins/beyin-v3.js`, `.claude/scripts/beyin_v3_companion.py`, `beyin_v3_projects.py`, `beyin_v3.py`.
- Kurulu runtime ve global config için etkinleştirmeden önce tekrar uyum kontrolü yapılır; bu doküman tamamlanmış kurulum kanıtı değildir.
