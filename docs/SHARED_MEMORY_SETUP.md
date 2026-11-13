# Ortak hafıza — kurulum ve kabul kaydı

Global etkinleştirme ve kullanıcı kabulü aşağıdaki kayıtta ayrı belirtilir. Otomatik testler, ajanın doğal dilde her durumda doğru davranacağını kanıtlamaz.

## Uyumluluk kapısı

- Başlangıç: OpenCode v2.2.7, Node v26.13.0, 204 Python testi geçti / 3 atlandı.
- Beyin 3.12.0 motoru ve güvenli kaynak snapshot sözleşmesi kopyalanmış runtime kodu ve tamamen sentetik vault üzerinde denendi. Kullanıcı notları kopyalanmadı.
- İzole HOME/XDG config ve temp proje içinde OpenCode `--standalone api get /api/plugin` çalıştırıldı. Global `plugins: ["-beyin-v3", "<sentetik-adaptör-dizini>"]` ile sentetik adaptörün setup'ı çalıştı, yerel otomatik keşfedilen `beyin-v3` setup'ı çalışmadı. Model/prompt/Notion çağrısı yapılmadı.
- Dolayısıyla desteklenen plugin control ile yönetilen dosyayı değiştirmeden tek bağlam üreticisi seçme yolu var. Gerçek kurulumda aynı sonuç tekrar doğrulanacak; başka config'lerin sonradan yeniden etkinleştirmesi kabul edilmez.
- OpenCode V2 config plugin hedefi tek `.js` dosyası değil, **dizin** olmalıdır. Yerel kod reposu kurulumun parçasıdır; yalnız wheel dağıtımı JS entegrasyonunu içermez.

Kaynaklar: https://opencode.ai/docs/plugins ve https://opencode.ai/docs/build/plugins/server .

## Geliştirme doğrulaması

```powershell
.\.venv\Scripts\python.exe -m pytest tests/shared_memory -q
node --test integrations/opencode/shared-memory/index.test.mjs
```

Test runtime'ı varsayılan kardeş `agent-memory-vault` klasöründen yalnız kod alır. Başka konum için `BEYIN_TEST_VAULT` belirtin. Kod bulunmuyorsa entegrasyon testleri açıkça skip olur; geçerli kurulum kanıtı değildir.

## Global yapılandırma

Mevcut global `opencode.json(c)` dosyasının `plugins` listesi **korunarak** şu iki girdi eklenir. Bunlar makineye özgü örnektir; yedek/diff ve sürüm kontrolü olmadan dosyayı toptan değiştirmeyin:

```json
[
  "-beyin-v3",
  {
    "package": "C:/Users/35.HaRRy/Desktop/Projects/brain-ext/integrations/opencode/shared-memory",
    "options": {
      "python": "C:/Users/35.HaRRy/Desktop/Projects/brain-ext/.venv/Scripts/python.exe",
      "vault": "C:/Users/35.HaRRy/Desktop/Projects/agent-memory-vault",
      "registry": "C:/Users/35.HaRRy/AppData/Local/brain-ext/shared-memory/registry.json"
    }
  }
]
```

`-beyin-v3` önceki yönetilen **OpenCode** bağlam üreticisini kapatır; dosyasını silmez, diğer istemcilerin Beyin entegrasyonunu kapatmaz. Yeni eklenti `brainext.shared-memory` kimliğiyle yüklenir. Başka config'ler eski eklentiyi yeniden açıyorsa kurulum başarılı sayılmaz. Normalde config değişikliği otomatik yüklenir; gerekirse `/reload` kullanın.

## Kullanım

- Yeni klasörün ilk mesajında proje sorusu gelir. Yeni proje için ad, kısa amaç, kimlik ve kök yol onaylanır; mevcut projeye bağlamak da mümkündür.
- `Atla` yalnız o oturumda soru sormayı durdurur ve proje hafızasını kapatır; genel tercihler kalır. `Bu klasörde bir daha sorma` kökü kalıcı susturur; proje oluşturmaz.
- Git depolarında frontend/backend aynı köke bağlanır. Ayrı klon/worktree için kullanıcı mevcut projeye bağlama onayı verir. Git olmayan kök açıkça seçilir.
- Kalıcı proje kaydı `projects/<id>/Project.md`; kök yolları yalnız yerel registry'dedir. Depoya dosya yazılmaz.
- Ajan kayıtlar için `shared_memory` aracını kullanır. Görev oluşturma/değiştirme ve eşleme kullanıcı talimatı/onayı ister. Normal OpenCode izinleri ek olarak geçerlidir; araçtaki `confirmed` alanı insan onayının kriptografik kanıtı değildir.
- Yeni/elle değiştirilen Markdown kaynakları sonraki kullanıcı mesajında yerel Beyin sync ile tazelenir. Araç devamlarında kaynak hash'leri tekrar kontrol edilir; değişmiş kaynak servis edilmez.
- Tamamen etiketsiz eski notlar genel hafıza sayılmaz. Proje notları kendi klasörü veya tutarlı project metadata'sıyla tanımlanır. Otomatik genel bağlam Core/Soul ve yalnız genel Kurallar maddeleridir; eski ortak Last-Session/Threads/Journal ve knowledge dizini topluca yüklenmez.
- Başka projeyi aramak açık istek ve hedef proje gerektirir. Bu işlem oturumun proje eşlemesini değiştirmez.
- `no-memory`, `no-tools`, `hafızayı kullanma`, `hafıza kullanma` veya `araç kullanma` açık ifadeleri o tur otomatik bağlamı susturur. Serbest dildeki her mahremiyet isteğini kural tabanlı tanıyabildiği iddia edilmez; ajan da kullanıcı sınırlarına uymalıdır.

## Sağlık ve sınırlar

- Uyum hedefi Beyin **3.12.0**, OpenCode **v2.2.7**. Beyin sürümü değişirse adaptör uyum testi yenilenene kadar hafıza erişimini durdurur; geniş aramaya düşmez.
- Normal yanıtta `Proje: … · Mod: …` bilgisi istenir. Hata halinde hafıza kullanılamadığı bildirilir; kodlama devam edebilir.
- `opencode plugin list` ile yüklemeyi, OpenCode loglarıyla setup hatalarını kontrol edin. Plugin hiç yüklenemiyorsa kendi uyarısını da üretemez; sessizliği başarı saymayın.
- Kapsam seçimi dosya erişim sandbox'ı değildir. Genel shell/dosya araçları ayrıca izinlerle yönetilir. Model bağlamına verilen metin model sağlayıcısına gider.
- Aynı oturum başka projeye taşınırsa adaptörün bağlamı değişir; eski transkript silinmez. Kesin ayrım için yeni oturum kullanın.
- Eşleme dosyası vault yoluna bağlıdır. Taşınma/bozulmada elle sıfırlayıp rastgele bağlamak yerine mevcut dosyayı koruyarak onarılmalıdır. Kilit dosyaları çalışır işlem varken silinmez.
- İlk proje kimliği kullanıcıdan alınır; geliştirici kurulum sırasında adına proje uydurmaz.

## Geri alma

Global config'ten yalnız yukarıdaki `-beyin-v3` ve `brainext.shared-memory` paket girdisini kaldırın; diğer plugin/ayarları koruyun. Yeni kullanıcı değişikliği varsa eski yedeği toptan geri yazmayın. `/reload` sonrası eski yerel Beyin eklentisi vault içinde yeniden çalışabilir. Registry ve proje notları silinmez; yeni adaptörün durdurulması notları geri almaz.

## Canlı kabul kaydı

- İzole sentetik config/vault ile gerçek OpenCode context hook'u çalıştırıldı. Son kontrol hook'u sağlayıcı çağrısından önce kasıtlı olarak durdurdu; CLI çıkış 1 bu deneyde beklenen sonuçtur. Test sağlayıcısı yalnız loopback adrese ve sahte anahtara ayarlıydı.
- İlk bağlamda GENERAL_ONLY ve yeni proje sorusu görüldü; A_ONLY/B_ONLY/LEGACY_ONLY yoktu. Kullanıcı-onayı modelleyen bind sonrası yeni oturumda A_ONLY görüldü, B_ONLY ve kayıt sorusu yoktu. Gerçek araç kataloğunda `shared_memory` vardı; eski eklenti setup'ı çalışmadı.
- Bu deney, gerçek hook/araç yüklemesi ve kaynak seçimi kanıtıdır; gerçek modelin soru sorma, onay yorumlama veya kalıcı not yazma davranışını test etmez.
- Beta için ikinci gerçek sentetik OpenCode oturumu da çalıştırıldı: B_ONLY ve GENERAL_ONLY görüldü, A_ONLY yoktu. Kasıtlı provider-öncesi durdurma iki kapsamda da uygulandı; ücretli model çağrısı yapılmadı.
- Global gerçek kurulum etkinleştirildi. Mevcut beş plugin ve bütün diğer config alanları eşitlik kontrolüyle korundu. Birebir yedek: `C:\Users\35.HaRRy\AppData\Local\Temp\opencode\shared-memory-config-backup\opencode-525e525ff2fe7e1a.json`.
- Gerçek `brain-ext` ve `agent-memory-vault` konumlarının plugin API çıktısında `brainext.shared-memory` active; `beyin-v3` listede yok. API kontrolünde açık `location[directory]` query kullanıldı; CLI cwd'sini location varsaymak doğru değil.
- Bu oturumdaki gerçek `shared_memory context` çağrısı `status: ok`, `mode: general`, `project: null` döndürdü; doğru vault'un Core/Kurallar kaynaklarını getirdi. Bu kod klasörü için henüz kullanıcı-onaylı proje eşlemesi yok; registry oluşturulmadı.
- Kullanıcının gerçek ilk proje seçimi ve iki doğal dil oturumunun davranış kabulü ayrıca bekleniyor. Gerçek görev veya sahte onay kaydı oluşturulmadı.

### İnceleme ve son testler

Bağımsız incelemenin üç Important bulgusu gerçek runtime fixture'ları üzerinde RED→GREEN düzeltildi: kayıtlı vault klasör kapsamı, gizlenen proje kuralının yazmada korunması, Project.md yenilemesinin katalog kontrolünden önce yapılması. İlgisiz sorguda da proje kartı/kuralları/devir notunun gelmesi ayrıca sabitlendi.

Son tam Python paketi: **251 passed, 4 skipped**; Node **12/12**; Ruff ve diff kontrolü temiz. Atlananlar gerçek embedding modeli ve Windows symlink yetkisi senaryolarıdır. Bunlar çalışmış veya geçmiş sayılmaz.

### Uygulamada alınan teknik kararlar

- Windows helper script sınırlarında PowerShell doğrulaması ve eşdeğer ledger kaydı kullanıldı; ortam/PATH değiştirilmedi.
- Minimal runtime yükleyicisi Task 3 yerine negatif uyum testini çalıştırmak için Task 1'de eklendi.
- Geniş Companion/passage formatter yerine mevcut note-level sıralama kullanıldı; kapsam sıralamadan önce uygulanır. Maliyeti passage'e özel arama kalitesinin kullanılmamasıdır.
- Kullanıcı mesajında mevcut yerel sync çalışır; her araç devamında yalnız kaynak güncelliği tekrar doğrulanır. Maliyeti yerel tarama/okuma ve türetilmiş runtime/view yazmalarıdır; Notion/model isteği değildir.
- Yeni proje klasörü notları mevcut `note-edit` yeni-dosya yolu ile oluşturulur; `note-create` yalnız notes/knowledge destekler.
- Taşınan oturumun yeni konum instance'ı bağlamı üretir; transient oturum durumu modül düzeyinde paylaşılır. Süreç yeniden başlayınca kapsam gerçek konumdan tekrar çözülür; eski konuşma metni silinmez.
- İzole gerçek hook testi sağlayıcı çağrısından önce durduruldu. Modelin doğal dilde onay yorumlaması ayrı kullanıcı kabulüdür.
- Onay bayrakları ve OpenCode izinleri OS sandbox veya kriptografik kullanıcı niyeti kanıtı değildir; genel shell/dosya erişimi ayrıca yönetilir.

Sentetik dar geri alma deneyi sonradan eklenen kullanıcı alanını ve plugin'ini korudu; gerçek global config geri alınmadı. Son doğrulama tekrarında Python 251/4 (101.32s), Node 12/12, Ruff/diff temiz. Henüz gerçek görev/proje kaydı oluşturulmadı. Bu entegrasyon için işin tamamını yeniden geliştirmek yerine ilk gerçek proje tanımlaması ve doğal dil kabulünden devam edin.
