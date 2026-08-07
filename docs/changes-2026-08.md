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

---

## Faz 3 — Finance Engineering: iki hat (2026-08-07)

Bu fazda **hiçbir metin yazılmadı** — istisna, mevcut hardcoded kartlardan registry'ye taşınan blurb'ler (harfi harfine aynı) ve iskeletlerin içindeki TODO/yorum satırları.

### Yayımlanmamış olanı yayımlamama disiplini

Bu fazda eklenen her şey iskelet. Boş bir sayfayı canlıymış gibi göstermemek için üç kademe kuruldu:

| Durum | Sayfa üretilir mi | Listelenir mi | Sitemap | robots |
|---|---|---|---|---|
| `status: "live"` (Reference, FE) | ✅ | ✅ | ✅ | index |
| `status: "draft"` | ❌ | ❌ | ❌ | — |
| `status: "planned"` + `target_date` yok | ❌ | ❌ | ❌ | — |
| `status: "planned"` + tarih var | ❌ | ✅ (`Planned · Eylül 2026`) | ❌ | — |
| `PAGES[...]["draft"]: True` (checklist, toolkit) | ✅ | ❌ | ❌ | **noindex, nofollow** |

Reference hub'ı da canlı madde yokken `noindex` ve sitemap dışı.

### 3.1 Placeholder repo linki

| Dosya | Eski | Yeni |
|---|---|---|
| `content/fe/mesele-hiz-degildi/{en,tr}.html:49` | `Code: <a href="https://github.com/orknn">github.com/&lt;repo&gt;</a> — …` | satır kaldırıldı, yerine `TODO(repo-link)` yorumu |

Metin var olmayan bir repoyu adlandırıp linki profil sayfasına götürüyordu. Tam FE yüzeyi tarandı (`<repo>`, `TODO`, `lorem`, `placeholder`, `Coming soon`) — başka kalıntı yok.

### 3.2 Repo vitrini

- `scripts/fetch_repos.py` → `data/repos.json` (build anı, GitHub API). Rate-limit (403) durumunda önceki snapshot korunur; 404/private → `status: "pending"`.
- `data.yml` cron'una eklendi (`continue-on-error`).
- `inject_repos()` kartları basar; blurb'ler `build.py:REPO_BLURB`'de **elle yazılı** (GitHub description'ı kısa ve habersiz değişebiliyor), metrikler API'den (yıldız, son commit tarihi, stack rozetleri).

> **Görevdeki varsayım hatalıydı.** Görev "Repolar public olmadığı için hepsi `data-status="pending"` ile gizli render edilsin" diyordu. API'ye sordum: **üçü public.** Şu an canlı ve görünür: `nocashflow.net`, `Crypto_Macro_Newsletter`, `Job-Hunter`. Yalnızca `stock-analyzer` public değil → `pending`, gizli. Kartlar artık varsayımdan değil API'den sürülüyor, yani repo public olduğu gün kart kendiliğinden görünür.

### 3.3 "Planned" kartları

FE hub index'i partial'da elle yazılmış 6 karttı; artık `FE_ESSAYS` registry'sinden üretiliyor (`<!--NCF:FE_INDEX-->` + `inject_fe_index`). Kayıtlara `status` ve `target_date` eklendi.

Üç "— Planned" kartı (`Anatomy of a Finance Agent`, `Newsletter Pipeline`, `Job-Hunter`) registry'ye taşındı ve **tarihsiz oldukları için render edilmiyor**. Metinleri kayıtlarda duruyor; `target_date` girildiği an `Planned · Sept 2026` biçiminde geri gelirler. Hub'da şu an yalnızca 3 canlı deneme var.

### 3.4 HAT A — teardown iskeletleri

Dört yeni kayıt (`status: "draft"`) + `content/fe/<key>/{en,tr}.html` iskeletleri:

`month-end-close-agent-architecture` · `variance-commentary-llm` · `forecast-data-quality-layer` · `excel-powerbi-llm-integration`

İskelet, mevcut teardown şeklini izliyor: hook → problem → what I built → where it breaks → principle → disclaimer. Her bölüm `<h2><!-- TODO: … --></h2>` + boş `<p>`. Byline mevcut `<!--NCF:BYLINE-->` marker'ından geliyor. Yayın öncesi doldurulacak registry alanları dosyanın başındaki yorumda listeli.

### 3.5 HAT B — Controlling Reference

Yeni bölüm: `/finance-engineering/reference/` · `/tr/finance-engineering/referans/`

- **Şablon bir kere yazıldı** (`REF_SECTIONS` + `render_reference`). Sekiz bölümün sırası, başlıkları ve numaralandırması burada; madde dosyası yalnızca 1–6'nın metnini verir.
- **Bölüm 7 (KPI) ve 8 (ilgili maddeler) registry'den üretilir** — çapraz linkler elle konmuyor, `related[]`/`articles[]` alanlarından türüyor, dolayısıyla registry ile asla tutarsızlaşamaz.
- Madde partial'ı `content/reference/<slug>/<lang>.html`, bölümler `<!--NCF:SEC <key>-->` yorumlarıyla ayrılır.
- Frontmatter alanları registry kaydında: `slug` (dile göre), `title`, `cat`, `status`, `updated`, `related[]`, `articles[]`, `kpis[]`, `sap_objects[]`, `audience[]`.
- **İndeks sayfası:** kategoriye göre gruplu, istemci tarafı arama kutusu (başlık + kategori üzerinde alt dizi eşleşmesi, boş sonuçta grup gizlenir), `draft` maddeler gizli.
- **Schema:** madde başına `DefinedTerm`, hub'da `DefinedTermSet` + `hasDefinedTerm` listesi.
- **Formül:** matematik kütüphanesi **yok**. `.rf-formula` + `<var>` ile düz metin; seçilebilir, çevrilebilir, ekran okuyucuya okunabilir. İskeletlerde örnek kalıp yorum olarak var.

Sekiz madde iskeleti (hepsi `draft`): `standard-cost`, `purchase-price-variance`, `working-capital`, `cash-conversion-cycle`, `inventory-accounting`, `factory-controlling`, `absorption-vs-variable-costing`, `overhead-allocation`.

> Şablon, canlı bir madde simüle edilerek uçtan uca test edildi (dosyaya dokunmadan). Test **gerçek bir hata yakaladı:** `related[]` taslak maddelere de link üretiyordu, o sayfalar üretilmediği için 404 olacaktı. Artık yalnızca canlı maddeler linklenir; taslaklar yayına girdiklerinde kendiliğinden görünür.

### 3.6 "Who should care"

`audience[]` alanı + `audience_html()`. Makale, FE denemesi ve Reference maddesi şablonlarının üçünde de başlığın altında render edilir; **`audience[]` boşsa blok hiç basılmaz**.

Etiketler tıklanabilir ve `/audience/<tag>.html` · `/tr/kitle/<tag>.html` filtrelenmiş liste sayfasına gider. Bu sayfalar **yalnızca en az bir içerik o etiketi taşıyorsa** üretilir.

Etiket kümesi: `investors`, `cfo`, `fpa`, `treasury`, `crypto`.

> **Şu an hiçbir içerik etiketli değil, dolayısıyla hiç kitle sayfası üretilmiyor ve hiçbir yerde blok görünmüyor.** Mevcut 9 makaleye kitle atamak editoryal bir karar — tahmin etmedim. Registry kayıtlarına `audience` alanı boş olarak eklendi; doldurduğun an sayfalar ve bloklar kendiliğinden çıkar. Mekanizma simüle edilmiş etiketle test edildi (çipler, filtre sayfası, schema).

### 3.7 Governance kontrol listesi

Yeni sayfa: `/finance-engineering/governance-checklist.html` · `/tr/finance-engineering/yonetisim-kontrol-listesi.html`

- Beş grup iskeleti (Veri ve erişim · Model davranışı · İnceleme ve onay · Denetim izi · Hata ve geri alma), maddeler `<!-- TODO -->`.
- Bileşen **tam çalışır durumda**: canlı sayaç + ilerleme çubuğu, sıfırlama, ve "Markdown olarak indir" (istemci tarafı `Blob`, backend yok, dosya tarayıcıdan çıkmaz).
- Script listeyi her seferinde DOM'dan okur → madde eklemek JS değişikliği gerektirmez.
- **Tik'ler saklanmıyor** (bilinçli): önceki oturumun işaretlerini sessizce geri yükleyen bir kontrol listesi, neyi iddia ettiğini gizler.
- Yazılmamış placeholder maddeler ve tamamen boş gruplar indirilen Markdown'a girmez.

### 3.8 Toolkit dizini

Yeni sayfa: `/finance-engineering/toolkit/` · `/tr/finance-engineering/arac-seti/`. Kart şablonu yorumda; kart yokken "henüz bir şey yok" notu görünür, ilk `.tk-card` eklendiğinde not `:has()` ile kendiliğinden çekilir. Kartlar üretilmiyor — yani var olmayan bir dosyayı ilan edemez.

### Diğer

- `PAGES` kayıtları artık `theme: "fe"` destekliyor (Machine Room teması yalnız hub'a değil, isteyen sayfaya).
- `_ind_head()` `extra_css`, `body_cls` ve `noindex` parametreleri aldı.
- RSS feed açıklamasındaki kadans iddiası düzeltildi (Faz 1'de gözden kaçmıştı): `Daily macro & market analysis…` → `Macro & market analysis…`, TR'de `günlük makro…` → `makro…`.
- `finance-eng.css` cache-bust sürümü `?v=mx1`/`?v=mx2` karışıklığından `?v=mx3`'e tekleştirildi.

### Doğrulama

- `python3 build.py` → 72 çıktı (68 → +4); iki ardışık build byte-eş
- `python3 scripts/check_jsonld.py` → 72 blok, sorun yok
- FE hub: 3 canlı kart, 0 tarihsiz "Planned" kartı, 3 görünür + 1 gizli repo kartı
- Governance: Markdown indirme tarayıcıda doğrulandı — grup başlıkları, `- [x]`/`- [ ]` durumu, kaynak URL doğru; boş gruplar çıktıya girmiyor
- Reference: canlı madde simülasyonuyla 8 bölüm, otomatik çapraz link, SAP nesneleri, KPI'lar, audience çipleri, metin-formül doğrulandı
- `noindex` üç iskelet sayfada var, gerçek sayfalarda yok; sitemap'te iskelet sayfa yok
- Yatay taşma: yeni öğelerin hiçbiri taşmıyor (mevcut `.nav-right` / `.ticker-track` taşması Faz 1 öncesinden)
