# nocashflow.net — Değişen metinler ve davranışlar

Her fazda değiştirilen kullanıcıya görünen metinler: dosya, eski, yeni.

---

## Faz 1 — Kritik veri tutarlılığı (2026-08-07)

### 1.1 Canlı metrikler: tek kaynak + zaman damgası

Metin değişikliği değil, **davranış** değişikliği. Aşağıdaki değerler artık HTML'e gömülmüyor:

| Öğe | Eski davranış | Yeni davranış |
|---|---|---|
| Footer "market mood" cümlesi (`_mood_line`, 52 sayfa) | Build anında düz metin: `Today the market is fearful — Fear &amp; Greed 29/100.` Hiçbir canlı bağlaması yok, kendini düzeltemiyordu. | Boş render ediliyor, `app.js` snapshot'tan dolduruyor; **cümlenin sonuna kendi zaman damgası** ekleniyor. Değer gelmezse satır tamamen gizli (`.mood-line:empty`). |
| Hero "market mood" rozeti (`_mood_pill`) | Build anında `F&amp;G 29` + mood kelimesi | Değer `data-px="fg"`'ye bağlı, gelene kadar `—`. Mood kelimesi ve rengi canlı değerden. |
| `data-px` / `data-chg` bağlı tüm enstrümanlar | `inject_market()` build anında dolduruyordu | Doldurulmuyor. `app.js` aynı snapshot'ı same-origin `/data/market.json`'dan çekip boyuyor — değer yine anında geliyor, ama **damgasıyla birlikte**. |
| `body[data-mood]` (aksan rengi) | Build anında | Build anında kalıyor (yalnızca renk, sayı iddiası yok), canlı değer gelince JS güncelliyor — yükleme anında renk sıçraması olmuyor. |
| Fed faizi (`data-fed`) ve funding (`#funding`) | Build anında | Build anında **kalıyor**. Tarayıcıdan erişilebilir kaynağı yok (FRED CSV / Deribit sunucu tarafında çekiliyor); istemciye bırakmak kalıcı `—` demek olurdu. Bloğun altına damga eklendi. |
| Ticker "Live" rozeti | Her sayfada koşulsuz | Yalnızca gerçekten veri boyandıktan sonra görünüyor; fetch düşerse gizleniyor. |

**Hata durumu:** `localStorage`'daki "son iyi değer"e sessizce düşme kaldırıldı (`app.js` `ncf-market-cache`). Artık: canlı çağrı düşerse damgalı snapshot değeri ekranda kalır; snapshot da düşerse sayı `—` olur ve blok "veri şu an alınamıyor" notunu gösterir.

**Bayatlık:** snapshot 24 saatten eskiyse damga `· stale` / `· bayat` etiketi ve `.is-stale` (kırmızı) sınıfı alıyor.

**Şema:** `data/market.json`'a `generated_at` ve `source_map` eklendi (`scripts/fetch_data.py`). Enstrüman başına `asof` zaten vardı, artık ekranda görünüyor. Mevcut alanlar korundu — `app.js`, `build.py`, `embed.js` ve widget JSONP kırılmadı.

> **Sapma:** görevde `assets/js/market-ticker.js` adında yeni bir dosya isteniyordu. Bu işi `app.js` zaten yapıyor (`fetchSnapshot` + `paintSnapshotAll`); ikinci bir script aynı JSON'u çekip aynı DOM düğümlerini boyayacağı için yarış durumu ve çift bakım maliyeti doğuracaktı. İstenen davranış `app.js` içine uygulandı.

### 1.2 "Live" rozeti + donmuş tarihler

Sayfalar ikiye ayrıldı (`build.py:LIVE_PAGES`).

| Sayfa tipi | Eski masthead | Yeni masthead |
|---|---|---|
| Canlı (index, macro, dashboard, calendar) | `Morning Edition · Friday, August 7, 2026 · Barcelona` | Değişmedi |
| Evergreen (about, FE hub, sözlük, arşiv, bülten, embed, yasal sayfalar) | `Morning Edition · <bugünün tarihi> · Barcelona` | `Barcelona` |
| Makaleler | `Morning Edition · <bugünün tarihi> · Barcelona` | `Published Jul 14, 2026 · Barcelona` / `Yayımlandı 14 Tem 2026 · Barcelona` |
| FE denemeleri | `Morning Edition · <bugünün tarihi> · Barcelona` | `Published Jun 24, 2026 · Barcelona` |

`updated` alanı olan ve yayın tarihinden farklı olan makalelerde ortada `Updated <tarih>` / `Güncellendi <tarih>` görünür. Şu an hiçbir kayıtta `updated` yok, o yüzden alan boş.

**Gösterge sayfaları (`/now/`, `/tr/simdi/`):** görevdeki iki listede de yoktu. Evergreen tarafına alındı — çünkü canlılık iddiası zaten okumanın yanında, kendi damgasıyla yapılıyor (`Updated: 7 Aug 2026, 08:11 CET`). Masthead'de ikinci bir tarih beyanına gerek yok.

### 1.3 Yayın sıklığı vaatleri

Arşiv sayımı: günlük bülten **son 30 günde eksiksiz** (56 sayı), haftalık **W24→W31 kesintisiz**. Bülten kadans vaatleri doğrulandı ve **korundu**. Yalnızca makale tarafındaki ve siteyi bütün olarak niteleyen iddialar düzeltildi.

| Dosya | Eski | Yeni |
|---|---|---|
| `build.py` `FOOTER["en"]["brand_desc"]` | `Independent macro & markets, published daily. Sourced data, no fabrication.` | `Independent macro & markets. Sourced data, no fabrication.` |
| `build.py` `FOOTER["tr"]["brand_desc"]` | `Bağımsız makro & piyasa, her gün yayımlanır. Kaynaklı veri, uydurma yok.` | `Bağımsız makro & piyasa. Kaynaklı veri, uydurma yok.` |
| `build.py` `PAGES["yazilar"]["desc"]` + `["og_desc"]` (EN) | `Sharp macro & market takes, published regularly.` | `Sharp macro & market takes, sourced from primary data.` |
| `build.py` `PAGES["yazilar"]["desc"]` + `["og_desc"]` (TR) | `Keskin makro & piyasa yorumları, düzenli yayımlanır.` | `Keskin makro & piyasa yorumları, birincil kaynaklardan.` |
| `content/en/yazilar.html` eyebrow | `Published regularly` | `9 essays · latest Jul 14, 2026` (registry'den üretiliyor — `_article_meta`) |
| `content/tr/yazilar.html` eyebrow | `Düzenli yayımlanır` | `9 yazı · son 14 Tem 2026` (aynı) |
| `content/en/yazilar.html` Fed hücresi | `<div class="v" data-fed>3.75%</div>` | `<div class="v" data-fed>—</div>` (veri yoksa artık uydurma sayı kalmıyor) |
| `content/tr/yazilar.html` Fed hücresi | `<div class="v" data-fed>3.75%</div>` | `<div class="v" data-fed>—</div>` |

Eyebrow artık yazılmış bir söz değil, registry'den türeyen bir olgu — bir daha bayatlayamaz.

**Dokunulmayanlar (doğrulanmış şekilde doğru):** `content/*/bulletin_page.html` içindeki tüm "every morning / her sabah / 07:45 CET / Daily Pulse" ifadeleri, `content/*/index.html:139,154` newsletter blokları, `content/*/hakkinda.html:16,33` bülten kadansı, `content/*/calendar.html` "updated daily", `content/*/index.html:102-117` `01–04 · Daily` bülten bölüm etiketleri.

### Yeni CSS

`components.css`: `.mood-line:empty`, `.mood-line .mood-asof`, `.mood-line.is-stale`, `.live-stamp`, `.live-stamp:empty`, `.live-stamp.is-stale`. Mevcut hiçbir kural değiştirilmedi, tipografi/renk değişkenleri aynen kullanıldı.

### Doğrulama

- `python3 build.py` → 66 çıktı, hata yok
- Tarayıcı (localhost:8899): mood satırı `Today the market is fearful — Fear & Greed 29/100. · as of 2026-08-07 11:00 UTC`; hero damgası `as of 2026-08-07 06:11 UTC` — iki farklı sayı, iki farklı damga, ikisi de doğru
- Hata yolu (`fetch` reddedilerek): mood satırı ve damga `Live data unavailable right now.`, ticker "Live" rozeti gizlendi, eski değere düşülmedi
- Bayat yolu (3 gün eski `generated_at` ile): `as of 2026-08-04 11:01 UTC · stale` + `.is-stale`
- Konsol hatası yok
- Yatay taşma kontrolü: yeni öğelerin hiçbiri taşmıyor (mevcut `.nav-right` ve `.ticker-track` taşması Faz 1 öncesinden var, dokunulmadı)
- Gömülü F&G taraması: hiçbir sayfada kalmadı
