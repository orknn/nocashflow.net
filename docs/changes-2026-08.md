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

---

## Faz 2 — Kimlik: ürün + yazar (2026-08-07)

### Yeni tek kaynaklar

| Dosya | İçerik |
|---|---|
| `data/site.json` | Kanonik konumlandırma cümlesi (uzun + kısa, TR/EN), site adı, URL, sosyal hesaplar, e-posta |
| `data/author.json` | Yazar adı, unvan, biyografi, sayfa deki, byline, masa adı, `same_as`, `knows_about`, konum |

İkisi de elle yazılır, fetcher'lar dokunmaz. `build.py` bunları sayfa registry'sinden **önce** yüklüyor (`_load_json`), böylece `PAGES` ve `FOOTER` literal'leri içinden çağrılabiliyor.

### 2.1 Ürün konumlandırma

Kanonik cümle — artık yalnızca `data/site.json`'da yazılı:

- **EN:** `Macro, markets and finance engineering — written by a finance engineer, sourced from primary data.`
- **TR:** `Makro, piyasalar ve finance engineering — bir finance engineer tarafından, birincil kaynaklardan.`

| Yüzey | Eski | Yeni |
|---|---|---|
| `<title>` (ana sayfa) | `NoCashFlow — Macro & Market Analysis` / `— Makro & Piyasa Analizi` | `NoCashFlow — Macro, Markets & Finance Engineering` / `— Makro, Piyasalar & Finance Engineering` |
| Ana sayfa `meta description` | `Data-driven macro analysis every morning, with a deep dive every Sunday — oil shocks, smart money, nuclear energy, Fed policy. From Barcelona.` | kanonik cümle |
| Ana sayfa `og:description` | `Data-driven macro analysis every morning, plus a deep dive every Sunday. Macro, crypto and commodities — primary source, always linked.` | kanonik cümle |
| `twitter:description` | (ayrı tanımlı değildi, `og:description`'dan geliyor) | kanonik cümle |
| Ana sayfa masthead kicker | `Macro & Markets, every morning` / `Makro & Piyasalar, her sabah` | kanonik kısa cümle |
| Ana sayfa masthead tagline | `Make sense of the macro. Start your morning with data.` / `Makroyu anlamlandır. Gününe veriyle başla.` | kanonik cümle |
| Footer tagline | `Independent macro & markets. Sourced data, no fabrication.` (Faz 1'de yazılmıştı) | kanonik cümle |
| Abone formu üst metni (index + bülten sayfası, TR/EN) | yoktu | kanonik cümle (`.newsletter-positioning`) |

**`<title>` suffix'i:** 28 başlığın tamamı denetlendi — hepsi zaten `— NoCashFlow` taşıyor, sapma yok. Site adını 28 literal'e template'lemek gürültü katacağı için başlıklar olduğu gibi bırakıldı; değişen tek başlık ana sayfanınki (konumlandırmayı yansıtsın diye).

> **Sapma:** görev "meta description / og:description" için tek kaynak istiyordu. Bunu **site düzeyindeki** yüzeylere uyguladım. 52 sayfanın hepsine aynı cümleyi basmak, her sayfanın kendi açıklamasını (`Live global macro dashboard — VIX, DXY…` gibi) tek bir cümleye indirger ve aramada zarar verir. Sayfa açıklamaları zaten `PAGES` registry'sinde tek yerde toplu; sorun olan site tanımı tekleştirildi.

### 2.2 Yazar kimliği

| Dosya | Eski | Yeni |
|---|---|---|
| `content/{en,tr}/yazilar.html` yazar kutusu | `Supply-chain executive by day, macro analyst the rest of the time. Writing to make sense of the world's capital flows.` / `Gündüz tedarik zinciri yöneticisi, geri kalan zamanda makro analist…` | `author.json` → `bio` |
| `content/{en,tr}/hakkinda.html` `page-dek` | `Finance Business Partner by day, macro analyst the rest of the time. NoCashFlow is the desk where the two meet.` / `Gündüz Finance Business Partner, kalan zamanda makro analist…` | `author.json` → `dek` |
| `build.py` `PAGES["hakkinda"]["desc"]` | `Orkun Biçen — Finance Business Partner (FP&A & controlling), macro analyst and trader. Founder of NoCashFlow.` | `author.json` → `bio` |
| `content/tr/finance-eng.html` lede | `Bu bölüm, bir "finans mühendisi"nin defteri.` | `Bu bölüm, bir finance engineer'ın defteri.` |

**about.html gövde metni değiştirilmedi** — yalnızca açılış deki hizalandı. EN FE hub lede'si (`a finance engineer's notebook`) kanonikle zaten uyumlu, dokunulmadı; TR'si terimi çevirdiği için hizalandı.

### 2.3 Byline ve schema

**Byline** — `byline_html()`, `author.json`'dan besleniyor:
- Makaleler: dek'in altında `By Orkun Biçen · NoCashFlow Research` / `Yazan Orkun Biçen · NoCashFlow Research` (`.byline.art-byline`, mevcut `.who`/`.role` stilleri)
- FE denemeleri: mevcut byline şeridinin sol hücresi `nocashflow.net · Finance Engineering` yerine aynı byline'ı taşıyor (sayfa zaten nocashflow.net'te ve Finance Engineering altında — o etiket bilgi taşımıyordu). Sağ hücre (okuma süresi) korundu.

**Schema** — üç düğüm, `@id` ile birbirine bağlı, **her sayfada** aynı `@graph` içinde:
- `WebSite` `#website` → `publisher` = `#organization`
- `Organization` `#organization` → `founder` = `#orkun`, `sameAs` = site.json sosyal hesapları
- `Person` `#orkun` → `jobTitle`, `description`, `worksFor` = `#organization`, `sameAs` (LinkedIn + X + GitHub), `knowsAbout`, `address` (Barcelona)

Makale JSON-LD'si artık yazarı tekrar tanımlamıyor, `{"@id": "…#orkun"}` ile referans veriyor; `publisher` de `#organization`'a. FE denemeleri `NewsArticle` yerine `TechArticle`.

**Doğrulama scripti:** `scripts/check_jsonld.py` — her `<script type="application/ld+json">` bloğunu ayrıştırır, tipe göre zorunlu alanları kontrol eder ve **dangling `@id` referansı** arar. `python3 scripts/check_jsonld.py` (hata varsa exit 1, CI'a takılabilir).

> Script yazılır yazılmaz gerçek bir hata yakaladı: ilk uygulamada `Organization` düğümü yalnızca ana sayfada tanımlıydı, ama 28 sayfa ona `@id` ile referans veriyordu — arama motorları yayıncıyı çözemezdi. Üç düğüm artık her sayfada birlikte gidiyor.

### 2.4 "Coming next"

`content/{en,tr}/yazilar.html` içindeki blok **silinmedi**, `<!--NCF:COMING_NEXT_START/END-->` işaretleri arasına alındı ve `build.py:FLAGS["COMING_NEXT"] = False` ile render dışı bırakıldı. Kartlar kaynakta harfi harfine duruyor; her karta gerçek hedef tarih girildiğinde bayrak `True` yapılıp geri açılır.

Gizlenme sebebi kaynakta yorum olarak yazılı: bir kart Ağustos'ta hâlâ *"Coming after March CPI"* diyordu, ikisi Mart'tan beri *"Drafting"*.

### Yeni CSS

`components.css`: `.byline.art-byline` (+ `.role::before` ayracı), `.newsletter-positioning`, `.newsletter-positioning:empty`. Mevcut kurallar değiştirilmedi.

### Doğrulama

- `python3 build.py` → 66 çıktı; iki ardışık build byte-eş (HTML deterministik)
- `python3 scripts/check_jsonld.py` → 66 blok, sorun yok
- Tarayıcı: makale byline'ı broadsheet tipografisiyle uyumlu render ediyor; abone formu konumlandırma satırı 460×31px, taşma yok
- Eski kimlik ifadeleri taraması (`Supply-chain executive`, `Finance Business Partner by day`, TR karşılıkları) → sıfır kalıntı
- Çözülmemiş `NCF:` marker'ı → yok
- `Coming next` üretilen sayfalarda → yok; `content/` içinde → duruyor
