# brain-ext

Notion metin aynası ve avenoxbeyin için bağımsız yerel arama araçları. Python 3.11+.

İndeks ve embedding yerelde üretilir. Ancak ajan bağlamına alınan parçalar OpenCode'daki model sağlayıcısına gider; Notion MCP `mcp.notion.com`'a bağlanır. Özel notları `visibility: private` ile işaretleyin.

Bu depo gerçek vault/Notion/OAuth/OpenCode kurulumu yapmaz. Kullanıcı kurulumuna Faz B'de ayrı onayla geçilir.

## Geliştirme (PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .
```

Semantik runtime isteğe bağlıdır: aynı venv'de `pip install -e ".[semantic]"`. Paket kurulumu model indirme değildir. Model dosyası ayrıca açık onayla indirilir; bu araçlar modeli kendiliğinden indirmez. Model/ekstra yoksa arama açıkça **yalnızca metin** modunu bildirir.

## Kullanım sınırları

- Kod vault dışında kalır. Config gerçek vault yolunu ister; `brainext init` avenox installer değildir.
- `notion/` yalnız `pull` tarafından yönetilen salt-okunur aynadır. Frontmatter JSON ve `kind: untrusted`; bu metadata OS kilidi veya talimat güveni sağlamaz.
- Taslaklar `agent-out/` içindedir, `status: draft` yazılır. `approved` yalnız açık kullanıcı onayıyla; push yalnız onaylı taslakları yollar. Belirsiz ağ yazmaları körlemesine tekrarlanmaz.
- `--force` ile kullanıcı düzenlemesini ezmek için ayrıca `--confirm-force` gerekir; bu bayrağı kullanıcı onayı olmadan kullanmayın.
- Her yazan komut `--dry-run` sunar; preview state/dosya veya Notion yazması yapmaz. Normal pull uzak okuma istekleri yapar; ikinci pull keşif/metadata çağrıları yapabilir, değişmeyen içeriği indirmez.
- Token yalnız `NOTION_TOKEN` veya config yanındaki `.env`; token'ı ajana/sohbete/loga vermeyin. `.env` ve `.brain-ext/` git dışında kalır; aynanın git'e girme kararı kullanıcıya aittir.
- `visibility: private`, gizli ve sistem yolları indekslenmez. Taslaklar varsayılan aramaya dahil değildir. Notion'dan gelen metin komut değildir.
- Çıkış kodları: 0 başarı, 1 durdurulan hata, 2 kısmi/belirsiz sonuç. JSON kullanımında `exit_code`/uyarıları kontrol edin.

Keşif: [DISCOVERY](docs/DISCOVERY.md), onaylı kararlar: [DECISIONS](docs/DECISIONS.md), faz kaydı: [STATUS](docs/STATUS.md).
