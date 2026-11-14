# Notion ana kaynaklı hafıza ve değişiklik kuyruğu

## Politika

- Me ve Carrier ağaçları yerel hafızaya çekilir; Notion asıl çalışma alanıdır.
- Yeni sayfa, entegrasyonun erişebildiği herhangi bir hedef altında onaysız
  oluşturulabilir. Hedef açık bir page/database/data-source kimliği olmalıdır.
- Mevcut sayfanın metnini değiştirmek veya sayfayı çöp kutusuna taşımak için
  kullanıcının belirli işlemleri toplu olarak onaylaması gerekir.
- Notion sürümü, hedef veya gönderilecek içerik değişirse eski onay kullanılamaz.
- Brain/Agent Workspace görevleri ve eski `agent-out/` → `push` akışı korunur.
  İnsan-okunur not değişikliklerinde aşağıdaki `changes` akışını kullanın.

## Kapsam ayarı ve geçiş

Me/Carrier kimlikleri bu geliştirmede tahmin edilmedi; gerçek config değiştirilmedi.
Mevcut config'in `[notion]` bölümüne gerçek kimlikler ayrıca girilmelidir:

```toml
memory_root_page_ids = ["<Me-page-id>", "<Carrier-page-id>"]
```

Alan yoksa eski Brain pull kapsamı geçerlidir. Yeni ayar **ekleme değil kapsam
değişimidir**. İç içe kökler Notion kimliğiyle tekilleştirilir. Bir dış sayfaya
verilen bağlantı o sayfanın içeriğini kapsama katmaz.

Me/Carrier keşfi tam Notion v2 Markdown'daki fiziksel alt sayfa/veritabanı
etiketlerini kullanır; her içerik bloğunu ayrı ayrı dolaşmaz. Eksik/uyarılı
Markdown, bozuk etiket veya folder için eski blok taramasına döner. Veritabanı
satırları yine tam sayfalanır ve uzak ebeveyn zincirleri doğrulanır. Keşifte
indirilen Markdown aynı çalışmada mirror gövdesi için tekrar indirilmez.

Notion bazen `link_to_page` bloklarını `<unknown>` olarak verirken
`unknown_block_ids` listesini boş bırakır. Bu biçimde yalnız blok kimliği,
aktif/alt öğesiz oluşu, mevcut sayfaya aidiyeti ve page/database bağlantı türü
doğrulanırsa işaretçi normal bağlantıya çevrilir; hedef içerik okunmaz. Diğer
bilinmeyen bloklar hızlı keşfin tam sayılmasına izin vermez.

Başarılı gerçek pull, alt sayfa kimliklerini mevcut notion state'inde sayfanın
`last_edited_time` değeriyle önbellekler. Yalnız aynı uzak sürümde ve yerel dosya
hash'i doğrulanıyorsa kullanılır; `pull --full` bu önbelleği atlar. Dry-run keşif
önbelleği yazmaz. Silme öncesi alt ağaç denetimi bu hızlı yolu kullanmaz.
İlk taramada her notun içeriği yine okunmalıdır; çok sayfalı kapsamda bu API
istek alt sınırı nedeniyle ilk aktarım uzun sürebilir.

Önce `pull --dry-run`, sonra `pull` ve `index` ile gerçek kurulum doğrulanmalıdır.
Eski kapsamın dosyaları sessizce silinmez; yeni kapsamla eşleşmeyen mirror'lar
brain-ext arama sonuçlarından çıkarılır. Eski sayfaların kaybolması çöp kutusu
kanıtı değildir; pull bunları koruyup uyarı verebilir. Eski aynanın taşınması veya
kaldırılması ayrı, yedekli bir geçiş kararıdır.

Doğrulanmış kapsam dışı taşınma, mirror baytlarını değiştirmeden
`.brain-ext/scope/<page-id>.json` kaydıyla arama erişimini kapatır. Sayfa kapsama
geri döndüğünde bu kısıtlama kaldırılır. Silme kanıtı şartı eski Brain config'inde
de geçerlidir; yalnız ağaçtan kaybolma artık otomatik arşiv nedeni değildir.

Kapsam/gizlilik kontrolü brain-ext indeksine aittir. Ayrı avenox indeksi veya
shared-memory adaptörü yeniden yapılandırılmış sayılmaz; yönetilen vault
dosyaları bu geliştirmede değiştirilmez. Ajan bu kaynakları `brainext search`
ile bilinçli olarak çağırır; tüm notları oturum başlangıcında modele yüklemez.

## Komutlar

Her örneğe kuruluma ait **mutlak executable** ve `--config "<mutlak-config>"`
ekleyin. JSON çıktıdaki `exit_code` ve hata listelerini kontrol edin.

### Yeni sayfa

Gövde, vault içindeki izinli bir Markdown dosyasından alınır; frontmatter uzak
sayfa gövdesine taşınmaz. `visibility: private`, generated/receipt, gizli,
symlink/junction ve kapsam dışı dosyalar kaynak olarak kabul edilmez.

```text
brainext changes create --target <parent-id> --title "Yeni not" --body-file agent-out/yeni-not.md --reason "Kaynak özeti" --json
brainext changes apply --dry-run --json
brainext changes apply --json
```

`create` yalnız kuyruğa ekler; `apply` veya `sync` uygun oluşturmayı onaysız uygular.
Oluşturulan sayfanın sonunda kurtarma için görünür `brainext-push-id: <UUID>`
satırı bulunur. Bu satır silinirse belirsiz gönderimin uzlaştırılması zorlaşabilir.
Okuma kapsamı dışındaki oluşturma, hafıza kapsamını genişletmez.

### Metin değişikliği

```text
brainext changes update --target <page-id> --old-text "Eski tekil metin" --new-text "Yeni metin" --reason "Kararın güncellenmesi" --json
```

Eski metin sayfada tam bir kez bulunmalıdır. İlk sürüm bir işlemde bir metin
aralığını değiştirir; birden çok işlem topluca onaylanabilir. Aynı sayfaya karşı
aynı eski sürümden hazırlanan işlemlerden ilki uygulanınca diğerleri çakışabilir;
son sürümü çekip yeni öneri hazırlayın. Yapısal Notion etiketlerini/özniteliklerini
değiştirme ve eksik Markdown üzerine yazma engellenir. Sayfa başlığı, veritabanı
özellikleri, medya ve tüm belgeyi yeniden yazma bu komutun kapsamı dışındadır.

### Silme

```text
brainext changes delete --target <page-id> --reason "Artık gerekli değil" --json
```

Bu yalnız bir silme önerisidir. Hedef ve alt sayfaların sürümleri kaydedilir.
Alt sayfa/veritabanı şeması veya içerik değişirse onay geçersiz olur. Başka bekleyen
işlemle örtüşen silme uygulanmaz. Me/Carrier/Brain/Agent Workspace için config'te
tanımlı köklerin kendileri ve onları içeren üst ağaçlar korunur.

Onaylı işlem Notion'da `in_trash: true` uygular; **kalıcı silme yapmaz**.

### Toplu inceleme, onay ve iptal

```text
brainext changes list --json
brainext changes approve --item <operation-id>=<request_hash> --item <other-id>=<other-hash> --json
brainext changes apply --id <operation-id> --dry-run --json
brainext changes apply --id <operation-id> --json
brainext changes cancel --id <operation-id> --id <other-id> --json
```

Liste, işlem kimliğini, Notion hedefini, gerekçeyi, diff'i, etkilenen sayfa
kimliklerini, durumu ve `request_hash` değerini verir. Onayda **incelenen listeden**
alınan kimlik/özet çiftleri kullanılmalıdır. Kullanıcı onayı olmadan ajan
`approve` çalıştırmaz. Günlüğün elle değiştirilmesi desteklenen bir düzenleme yolu
değildir. Bir toplu onaydaki tek geçersiz kayıt, tüm onay grubunu durdurur.

`apply` için `--id` verilmezse tüm uygun oluşturma/onaylı işlemler değerlendirilir.
Onaysız güncelleme/silmeler bekler. `conflict` için öneriyi iptal edip güncel
sürümden yeniden hazırlayın. `pending`/`uncertain` iptal edilmez veya başka UUID
altında yeniden gönderilmez; önce gerçek sonuç salt okunur olarak araştırılır.
Liste/onay/iptal ağ veya token gerektirmez; diğer komutlar normal CLI token
yükleyicisini kullanır. `--dry-run` hiçbir yerel/uzak yazma yapmaz.

### Rutin senkronizasyon

```text
brainext sync --if-stale 30m --json
```

Akış: uygun kuyruk işlemleri → Notion pull → yerel indeks. Aktif kuyruk varsa
tazelik damgası kuyruk işlemlerini atlatmaz. Çakışmalar raporlanır; diğer bağımsız
işlemler ilerleyebilir. Eski `push` taslakları sync ile kendiliğinden gönderilmez.
Zamanlayıcı/webhook kurulmaz; komut gerektiğinde veya ayrıca kurulacak zamanlayıcıyla
çalıştırılır. Sync artık uygun kuyruk varsa **uzak yazma yapabilir**.

## Silme geçmişi ve kurtarma

Notion'da normal silme için ayrıca özel bir liste sayfası doldurmanız gerekmez:
senkron aracı sayfanın veya üst sayfasının doğrulanmış `in_trash` durumunu kullanır.
Yalnız kaybolma, 403/404 veya eksik tarama silme sayılmaz. Yerel mirror dosyasının
silinmesi de Notion'dan silme talebi değildir.

Yerel journal, her silme olayına UUID, sayfa kimliği, kaynak, gözlem ve alındı
zamanını kaydeder. Gelen silmede yerel düzenleme/bekleyen öneri varsa çakışma olur.
Uygulanabilen silme mirror'ı `_arsiv/` altına taşır; aktif indeksten çıkarır.
Onaylanan tombstone geçmişte kalır; ilk sürüm otomatik temizlemez. Notion'da geri
yüklenen sayfa yeniden çekilir; eski silme olayı geçmişte tutulur.

Uzak yazmadan önce `pending` kalıcılaştırılır. Ağ hatası/çökme sonrasında yalnız
okuyarak sonuç uzlaştırılır; kör POST/PATCH tekrarı yapılmaz. Notion'un Markdown
normalizasyonu beklenen sonuçtan farklıysa işlem `uncertain` kalabilir; bu durumda
otomatik yeniden gönderim yerine inceleme gerekir.

`.brain-ext/state/changes_state.json`, `.brain-ext/scope/`, diğer senkron state dosyaları ve mirror
birlikte yedeklenmelidir. Journal, önerilen içerikleri ve eski sürümleri içerir:
hassas veri olarak saklayın; sohbete/loglara topluca dökmeyin. Mevcut Git ignore
kuralları nedeniyle vault Git geçmişi tek başına bu kurtarma verisini kapsamaz.

İşlem öncesi kontrol Notion tarafında atomik compare-and-swap değildir. Son kontrol
ile API yazması arasında eşzamanlı insan düzenlemesi için dar yarış aralığı kalır;
özellikle silme uygulanırken aynı alt ağaçta düzenleme yapmayın. Hash/onay mekanizması
ajan politikası ve yerel bütünlük kontrolüdür; keyfî yerel dosya/komut erişimine
karşı OS yetkilendirme sınırı değildir.
