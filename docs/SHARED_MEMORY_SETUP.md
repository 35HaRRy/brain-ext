# Ortak hafıza — kurulum ve kabul kaydı

Bu entegrasyon geliştirme aşamasındadır; aşağıdaki kanıt global kurulumun yapıldığı anlamına gelmez.

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
```

Test runtime'ı varsayılan kardeş `agent-memory-vault` klasöründen yalnız kod alır. Başka konum için `BEYIN_TEST_VAULT` belirtin. Kod bulunmuyorsa entegrasyon testleri açıkça skip olur; geçerli kurulum kanıtı değildir.
