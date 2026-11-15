# NoCashFlow — "Liquid" yeniden tasarım planı

Durum (2026-11-15): **Faz 0–6b tamam** (`feat-liquid`). `embed` widget'ı dışında bütün sayfalar (EN+TR) Liquid'de. Sıradaki: **Faz 7 `[OPUS]`** (kalite turu), sonra Faz 8 (yayın, onayla). Bölüm 6'daki kararların hepsi 2026-11-15'te kullanıcı tarafından önerildiği gibi onaylandı.

## 0. Eski tasarımın yedeği (Broadsheet)

| Ne | Nerede |
|---|---|
| Dal | `backup/pre-liquid` (origin'de) |
| Etiket | `pre-liquid-2026-11-15` (origin'de) |
| Ekran görüntüleri | `demos/before/` — 17 sayfa tipi × 1440/390px, JPEG |

Geri dönüş: `git checkout pre-liquid-2026-11-15 -- <dosyalar>` ya da `main`'i o etikete sıfırlamak (kullanıcı onayıyla).

## 1. Hedef

Onaylanan `demos/d-liquid/index.html` demosundaki görsel dili tüm siteye taşımak.
Yalnızca görünüm ve etkileşim değişir. URL'ler, içerik metinleri, veri pipeline'ı,
iki dilli yapı ve SEO çıktıları aynı kalır.

**Tasarımın doğruluk kaynağı demodur.** Bir şey bu planda yazmıyorsa demoya bak;
demoda da yoksa uydurma, "Açık kararlar"a ekle ve sor.

## 2. Kim ne yapar

| Etiket | İş türü | Model |
|---|---|---|
| `[FABLE]` | Yeni tasarım kararı gerektiren işler (henüz demosu olmayan sayfa tipleri) | Fable |
| `[OPUS]` | Demoyu koda taşıma, build.py, veri bağlama, çeviri yapısı, test, deploy | Opus |

Fable işi (Faz 4) bitti. Kalan fazların tamamı Opus işi.

## 3. Tasarım sistemi (demodan, birebir alınacak)

**Renkler** (`:root` değişkenleri)
- `--bone #ECEAE3` zemin, `--bone-2 #E1DED5` ikincil zemin
- `--ink #0B0C0F` metin ve koyu paneller, `--mute #6E6C66` ikincil metin
- `--hot #FF4B26` tek vurgu rengi
- `--mood`: Fear & Greed'e göre — <40 `#6FB2FF`, 40–60 `#E8B04A`, >60 `#2FBF71`
- `--up #2FBF71`, `--dn #FF4B26`

**Yazı tipleri** (Google Fonts)
- Başlık ve gövde: Bricolage Grotesque (300–700, opsz 12–96), başlıklarda ağırlık 400, harf aralığı −0.05em civarı
- Vurgu kelimeleri: Instrument Serif italic (`<em>`)
- Veri ve etiketler: Geist Mono, 11.5px, büyük harf, +0.06em
- Türkçe için `latin-ext` alt kümesi yüklenmeli (ğ, ş, ı, İ kontrol edilecek)

**Boyutlar:** demodaki `clamp()` değerleri küçültülmüş son hâlidir, değiştirme.

**Bileşenler** (demodaki sınıf adlarıyla)
- `.nav` yüzen hap menü, aşağı kaydırınca gizlenir
- `.btn` içten dolan vurgu rengiyle buton, `data-magnet` ile mıknatıs etkisi
- `.ln > span` satır maskeli başlık açılışı, `.fade` yumuşak giriş, `.rv` gözlemlenen kapsayıcı
- `.stage` siyah yuvarlak panel + canvas getiri eğrisi, kaydırmayla genişler (`--p`)
- `.chip` cam veri çipi, `.mq` büyük kayan şerit
- `.regime/.rg` yedi hücreli rejim şeridi (üzerine gelince siyaha döner)
- `.lead` manşet, `.row` makale satırı (alttan siyah dolgu)
- `.dark` koyu yuvarlak bölüm, `.gauge` Fear & Greed göstergesi, `.odd` olasılık çubukları, `.stat` kartları
- `.strip/.card` sürüklenebilir kart şeridi
- `.wm` footer'da harf harf yükselen dev logo
- `.cur` özel imleç (`data-cur`, `data-cur-label`), `.progress` kaydırma çizgisi, gövdede grain dokusu
- `[data-scr]` rakam karıştırma efekti

## 4. Kilitli kurallar

1. **Uydurma veri yok.** Tüm rakamlar `data/*.json`'dan; kaynak yoksa "—".
2. **Metinlere dokunma.** Mevcut EN/TR metinler aynen taşınır. Çeviri ≠ revizyon.
3. **Kök HTML'ler üretilmiş dosyadır.** Yalnızca `content/`, `build.py`, CSS ve JS düzenlenir, sonra `python3 build.py`.
4. **URL, hreflang, canonical, JSON-LD, sitemap, RSS değişmez.** Faz 7'de diff ile kanıtlanır.
5. **Client-side veri zinciri** (`app.js` `fetchWithProxies` + snapshot) bilerek böyle; değiştirme, raporlama.
6. **`git clean` yasak** (untracked `demos/`, `files/` var).
7. **Abonelik formu işlevi korunur:** `data-newsletter`, dil radyoları, `.nl-hp` honeypot, `app.js initForms`.
8. **Tüm iş `feat-liquid` dalında.** `main`'e yalnızca Faz 8'de, kullanıcı onayıyla.
9. **JS'siz de okunur olmalı:** giriş animasyonları içeriği yalnızca `html.js` sınıfı varken gizler.
10. **`prefers-reduced-motion`** her animasyonda uygulanır; imleç ve mıknatıs dokunmatik cihazda kapalı.
11. Her faz sonunda: commit, kısa özet, ekran görüntüleri, **dur ve onay bekle**.

## 5. Fazlar

### Faz 0 — Hazırlık `[OPUS]`
- `main`'i güncelle, `backup/pre-liquid` dalı aç ve push'la, `feat-liquid` dalı aç.
- `demos/d-liquid/` ve bu planı dala commit'le. (`demos/` `main`'e girerse Pages yayınlar; yalnızca dalda kalsın, Faz 8'de `main`'e taşınmaz.)
- Mevcut sitenin her sayfa tipinden 1440px ve 390px referans ekran görüntüsü al.

### Faz 1 — Temel katman `[OPUS]`
- `liquid.css`: demodaki `:root` değişkenleri ve bileşen stilleri birebir. Eski `site.css → components.css → broadsheet.css` zinciri bu fazda silinmez; yeni sayfalar `body.lq` ile yalnızca `liquid.css` yükler.
- `liquid.js`: imleç, mıknatıs, reveal, rakam karıştırma, nav gizleme, ilerleme çizgisi, şerit sürükleme, canvas sahnesi. `app.js`'in veri ve form mantığı ayrı kalır.
- `build.py`: `FONTS_URL` güncellemesi, sayfa başına `design: "liquid"` bayrağı (PAGES kaydında), `head()` buna göre CSS/JS seçer.
- Kabul: bayrak kapalıyken build çıktısı byte-byte aynı.

#### Faz 0–1 sonucu ve sonraki fazlar için notlar
- **Bayrak:** `PAGES[key]["design"] = "liquid"`; sayfa ailesi için `DESIGN_KINDS` (`article`, `fe-essay`, `indicator`). Önizleme: `NCF_LIQUID=index python3 build.py` veya `NCF_LIQUID=all`. **Önizleme build'inden sonra mutlaka bayraksız `python3 build.py` çalıştır**, yoksa diskteki çıktılar Liquid kalır.
- **Mekanizma:** `_apply_design(html, kind)` bitmiş HTML'e son geçiş olarak uygulanır (fontlar, `liquid.css`, `html.js`, `body.lq`, theme-color, `liquid.js`). Dört farklı `head()` kopyasına dokunulmadı. Sayfaya özel CSS'ler (macro/dashboard/finance-eng) hâlâ yükleniyor; Faz 6 değiştirir.
- **Doğrulama:** bayrak kapalıyken 371 çıktı (html/xml/txt) baseline ile byte-byte aynı. Bayrak açıkken 68 sayfa doğru dönüşüyor, JS hatası yok.
- **Build'in üretmediği 5 statik sayfa** `404.html`, `subscribed.html`, `unsubscribed.html`, `tr/subscribed.html`, `tr/unsubscribed.html`: bayraktan etkilenmez. 404 → açık karar #5; diğer 4'ü Faz 5'te elle Liquid'e çevrilir.
- **Port doğruluğu:** demonun DOM'u gerçek `liquid.css` + `liquid.js` ile render edildi; fark %0,012 (yalnızca rastgele parçacıklar ve nabız animasyonu).
- **Mood rengi** demodaki 40/60 eşiği yerine sitenin mevcut `_mood()` kovalarını kullanır (`body[data-mood=fear|neutral|greed]`, eşikler 35/55). Tek tanım kalsın diye bilinçli.
- **Markup sözleşmesi** (`liquid.js` başlığında tam liste): demo id'leri yerine data kancaları — hero `.rv[data-rv-now]`, gösterge `.gauge[data-value]` + yay `path.arc.arc-val`, eğri `canvas[data-curve='[{"l":"1M","v":4.12},…]']`, saat `[data-lq-clock]`, footer `footer.lq-foot`. İmleç JS ile eklenir, markup'a konmaz.
- `?static` artık kayan şeridi ve nabzı da durdurur (demo durdurmuyordu).
- **Ekran görüntüsü:** `python3 tools/shoot.py <klasör> [--static]` — yerel sunucu + Playwright, 17 sayfa × 2 genişlik, ~80 sn. Animasyonları son hâline zorlar. Faz 7 "sonra" görüntüleri `demos/after/`'a.

### Faz 2 — Ortak çerçeve `[OPUS]`
- `_nav_html`, `footer`, `masthead`, `ticker_html`, `chrome_top` için liquid sürümleri.
- Menüde mevcut tüm öğeler kalır (Finance Engineering dahil), TR/EN değiştirici ve mobil menü eklenir (demoda mobil menü yok: basit tam ekran açılır liste, aynı tipografi).
- Splash dil ekranı yeni renk ve yazı tipleriyle.
- Kabul: tüm linkler çalışır, klavye ile gezilebilir, odak halkası görünür.

### Faz 3 — Ana sayfa `[OPUS]`
- Demo → `content/{en,tr}/index.html` + build-time enjeksiyon:
  - eğri ve tarih: `MACRO.curve`, `MACRO.us10y.date`; spread: `MACRO.spread`
  - çipler, şerit, istatistikler: `MARKET.instruments`
  - rejim şeridi ve cut-odds: `MACRO2.regime_tape`, `MACRO2.fed.cut_odds` (geçmiş toplantılar gösterilmez)
  - **manşet ve makale satırları `ARTICLES` + `ARTICLE_ORDER`'dan otomatik** (bugün elle yazılı; bu faz o sorunu da kapatır). Manşetin iki satırlık kısa başlığı için registry'ye opsiyonel `lead` alanı; yoksa tam başlık.
- Veri build'de HTML'e gömülür; `app.js` yalnızca tazeler (`data-px`, `data-chg` kancaları korunur).
- Abonelik formu gerçek işaretlemeyle bağlanır.
- TR sürümü: mevcut TR metinler; "Make sense of the macro." için mevcut TR manifesto metni kullanılır.
- Kabul: EN ve TR, 390/768/1440px ekran görüntüleri demoyla eşleşir; yatay taşma yok.

#### Faz 2–3 sonucu ve sonraki fazlar için notlar
- **Çerçeve:** `_chrome_top/_chrome_nav/_chrome_ticker/_chrome_mast/_chrome_foot(kind, …)` dört birleştirme noktasının hepsinde (sayfa, makale, FE, gösterge). Broadsheet dalı eski fonksiyonları aynen çağırır.
- **Menü:** pill'de 7 bölüm, "Home" = logo (`aria-current`). <1100px tam ekran menüde 8 bölümün hepsi. After Hours düğmesi Liquid'de yok (karar #1 bekliyor). İç sayfalarda koyu ticker yerine ince "Market board" satırı (`_lq_tape`, karar #3 varsayılanı).
- **app.js:** `body.lq`'da Broadsheet fare efektlerini (imleç, nav pill, 3D eğme, kaydırma animasyonu) atlar; Liquid sayfalar `app.js?v=lq1` yükler. Form, veri tazeleme, dil, easter egg aynen çalışır.
- **Ana sayfa:** `content/{en,tr}/index.liquid.html` (Broadsheet `index.html` partial'ı yedek olarak duruyor) + `inject_liquid_home()`. Manşet ve 4 satır artık `ARTICLE_ORDER`'dan otomatik; iki satırlık manşet için registry'de opsiyonel `lead: {"en": (satır1, satır2), "tr": …}`. Yeni makale eklerken `lead` verilmezse tam başlık tek satır çıkar.
- **Geçmiş FOMC toplantıları** cut-odds listesinden elenir (`_lq_upcoming_odds`); liste boşsa "—".
- **Türkçe büyük harf:** `text-transform:uppercase` TR sayfada İngilizce kelimeye noktalı İ basar (`BİTCOİN`). İngilizce etiketlere `lang="en"` ver.
- **Metin istisnaları (bilinçli):** demodaki "Scroll — the curve is live" → "Scroll — the real yield curve" (eğri günlük FRED snapshot'ı, canlı değil; sitenin "Live" → "Market board" kararıyla aynı gerekçe). Abonelik metni demodaki kısaltılmış hâli değil, sitenin mevcut metni ("every morning" dahil).
- **Doğrulama:** ana sayfa dışındaki tüm çıktılar byte-byte aynı; ana sayfanın SEO etiketleri aynı; 1440/768/390'da yatay taşma 0; form sahte worker'a doğru gövdeyi yolluyor; reduced-motion ve JS-kapalı görünüm çalışıyor.
- **Faz 7'ye not:** JS kapalıyken getiri eğrisi tuvali boş kalıyor (diğer her şey görünür). İstenirse build-time SVG fallback (`hero_frieze` benzeri) eklenebilir.

### Faz 4 — Eksik şablonların tasarımı `[FABLE]` ✅
Önce Faz 0–3 denetlendi. Tek gerçek hata: `liquid.js` `scramble()` animasyon sonunda eski değeri geri yazıyordu ve `app.js`'in canlı fiyat güncellemesini ezebiliyordu; artık metin dışarıdan değiştiyse bırakıyor.

Demolar (`demos/d-liquid/`, hepsi `python3 demos/d-liquid/gen.py` ile gerçek içerik ve veriden üretilir, elle yazılmış rakam yok):
- `article.html` (`cekirdek`: tablo, data-point, alıntı), `article-2.html` (`enflasyon`: ok listesi, figür).
- `data.html`: macro sayfasının tamamı (`MACRO2`, `CALENDAR`, metinler `content/en/macro.html`'den) + altında dashboard bileşen sayfası (`data/markets.json`).

Yeni dosyalar ve rolleri:
**Grafik kuralı (kullanıcı isteği, 2026-11-15):** kullanıcı ana sayfadaki arazi grafiğini çok beğendi ve "grafiklerin bu şekilde olmasını" istedi. Koyu paneldeki her çizgi grafik artık arazi olarak çizilir:
- İşaretleme: `<div class="tr"><canvas data-curve='[{"l","v"}…]' data-pre data-suf data-dec [data-labels="key"]></canvas> + .ch yedeği</div>` (`gen.py: terrain()`). `liquid.js` aynı çiziciyi `.stage` ve `.panel` için kullanır.
- Az noktalı seri (getiri eğrisi): her nokta etiketli. Uzun seri (net likidite): `data-labels="key"` ile yalnızca ilk/son/en yüksek/en düşük etiketlenir, fare diğer noktaları okur.
- Uzun seride eğri düz parçalara yakın tutulur (veride olmayan tepe üretilmez). İlk görünüşte sırt yerden yükselir.
- JS kapalıyken canvas gizlenir, aynı kutudaki `.ch` SVG çizgi grafiği görünür.
- Faz 6'da `/now/` gösterge grafikleri ve `pulse_chart` da bu bileşene geçer. Küçük kutulardaki sparkline'lar ve ısı haritası olduğu gibi kalır.

| Dosya | İçerik |
|---|---|
| `inner.css` | İç sayfa başlığı `.p-hero/.p-meta/.p-title/.p-sub/.p-dek/.p-aside`, küçük bölüm başlığı `.sec-h.sm`, `.sec.tight`, link `.lk` |
| `article.css` | **Mevcut içerik sınıflarını** stiller (makaleler yeniden yazılmaz): `.article-prose`, `.a-table(.hit)`, `.data-point`, `blockquote`, `.arrow-list`, `.article-figure`, `.source-box`, `.gloss`, `.share-row`, `.pn-grid`. Yeni tek parça: `.a-wrap/.a-main/.a-rail` |
| `data.css` | `.kpis/.kpi`, `.split`, `.panel`, `.ch` (çizgi grafik), `.read`, `.dt-wrap/.dt` (+`.pc`, `.imp`, `.act`, `tr.d0`), `.tiles/.tile`, `.heat/.hc`, `.facts` |
| `gen.py` | **İşaretleme referansı.** Faz 5/6'da üretilecek HTML'in birebir örneği |

`liquid.js`'e eklenen kanca: `[data-lq-read]` (`.article-prose`'u izler, `--rp` ve `[data-read-pct]` yazar).

Tasarım kuralları (demoda uygulanmış, taşırken korunacak):
- Başlıkta " — " sonrası kısım serif italik ve ayrı satır (`gen.py: split_title`). " — " yoksa düz.
- `h2`'lerin "§ 01" numarası CSS sayacıdır, içeriğe dokunulmaz.
- Grafik: SVG `preserveAspectRatio="none"` ile esner, çizgi `vector-effect:non-scaling-stroke`, etiketler HTML (yüzde konumlu). Çizgi `pathLength="1"` ile görünürken çizilir.
- Isı haritası: renk yoğunluğu `--a` (0–1) = hareketin büyüklüğü.
- Sözlük ipucu: masaüstünde terimin üstünde, 1000px altında ekranın altına sabitlenir (taşma olmasın diye).
- `.demo-div` yalnızca demo ayracıdır, siteye taşınmaz.

Doğrulandı: üç demo 1440 ve 390'da yatay taşma 0, JS hatası yok; okuma sayacı 0→100; ipucu görünür. Fare/animasyon hissi kullanıcı tarafından gerçek tarayıcıda onaylanacak.

### Faz 5 — Yazı sayfaları `[OPUS]` ✅
- `inner.css` + `article.css` + yeni "legacy içerik sınıfları" katmanı `liquid.css`'e eklendi (reduced-motion bloğundan önce). `LIQUID_ASSET_V = "2"`.
- `DESIGN_KINDS["article"] = "liquid"`; `render_article` Liquid gövdesi = `gen.py: article()` (okuma rayı, § numaralı h2, paylaşım, prev/next). Başlık kuralı `_lq_title()`.
- `yazilar`, `archive`, `sozluk`, `hakkinda`, `privacy`, `legal`, `disclaimer` → `PAGES[...]["design"]="liquid"`. **İçerik dosyaları çoğaltılmadı:** `_lq_page_head()` Broadsheet `page-head` bloğunu build sırasında `.p-hero`'ya çevirir (aynı metinler), geri kalan mevcut sınıflar (`.with-aside`, `.brief`, `.minidata`, `.filters`, `.card-grid/.acard`, `.callout`, `.newsletter-form`, `section.newsletter`, `.glossary-grid/.term`, `.arch-*`) CSS ile giydirildi. Faz 6'da aynı yöntem kullanılabilir.
- Yazılar listesi Liquid'de ana sayfanın `.row` satırı (+ özet) olarak üretilir (`inject_article_list(..., liquid=True)`).
- Elle yazılmış 4 sayfa (`subscribed`, `unsubscribed`, TR'leri): yalnızca `<style>`, font linki ve theme-color değişti; `<body>` byte-byte aynı.
- Doğrulandı: SEO etiketleri (title, description, canonical, hreflang, og/twitter, JSON-LD) değişen her sayfada öncekiyle aynı; sitemap/RSS değişmedi; Liquid dışı sayfalar byte-identical; 9 sayfa × 1440/390 taşma 0, JS hatası 0; okuma sayacı çalışıyor; yazılar sayfasındaki form sahte worker'a `{"email","lang","hp"}` gönderdi ve onay mesajını gösterdi; sözlük ipucu sayıları önceki build ile aynı.
- Not: makale figürleri hâlâ eski crimson (Faz 6b, karar #4).

### Faz 6 — Veri sayfaları `[OPUS]` ✅
- **Değişken köprüsü** (`liquid.css`, `body.lq{...}`): eski sayfa-özel CSS'lerin ve içerikteki inline stillerin okuduğu `--bg/--text/--amber/--border/...` adları Liquid paletine bağlandı. `--serif` burada eski gövde fontu anlamına gelir → Bricolage; Liquid'in kendi serif italiği artık `--it` (liquid.css'teki tüm `var(--serif)` → `var(--it)`). Yeni CSS yazarken `--it` kullan.
- `data.css` (demo ayracı hariç) + veri sayfası giydirme katmanı `liquid.css`'e eklendi. `LIQUID_ASSET_V = "3"`.
- `macro`: `inject_macro2(..., liquid=True)` → `_lq_macro2()` kapları yeniden adlandırır (kpis/split/panel/odds/regime), § başlıklarını `.sec-h` yapar, KPI'lar `data-scr` ile; iki grafik **arazi** (`_lq_terrain` + `_lq_chart` JS'siz yedek). Oran olasılıkları ana sayfadaki gibi yalnızca gelecek toplantılar (`_lq_upcoming_odds`). `macro.css` Liquid'de yüklenmez.
- `calendar`, `bulletin_page`, `/now/` hub + 6 gösterge (EN+TR): içerik/üretici aynı, CSS ile giydirildi. Gösterge sayfalarında grafik yok (geçmiş seri verisi yok — uydurulmadı); büyük değer koyu panelde.
- `_apply_design` artık her Liquid sayfada `_lq_page_head()` çalıştırır (başlıktaki ek içerik `.p-extra`'ya, `id` korunur) ve tüm `.dtable`'ları `.dt-wrap/.dt`'ye sarar.
- `dashboard`: prototip (mock veri) kendi düzeniyle `dashboard.css` + köprüyle çalışır; "bölüme atla" düğmesi 1420px altında sağ alta yüzen hap oldu. Sekmeler, TOC, grafik düğmeleri test edildi.
- **Finance Engineering** (hub + 4 deneme): karar #2 gereği Matrix odası aynen; gövde sınıfı `lq bs fe-matrix` (finance-eng.css `body.bs.fe-matrix`'e bağlı), `body.lq.fe-matrix` Liquid token'larını fosfor paletine çevirir → menü/footer odaya uyar. Yağmur efekti hub'da çalışıyor.
- `embed` Broadsheet'te kaldı (kapsam dışı). `pulse_chart`/`hero_frieze` yalnızca eski ana sayfada kullanılıyor; Liquid'de çağrılmıyor.
- Doğrulandı: SEO etiketleri değişen her sayfada aynı; sitemap/RSS/embed değişmedi; 8 veri sayfası × 1440/390 taşma 0, JS hatası 0; macro'daki iki tuval çiziliyor; JS kapalıyken yedek grafikler ve KPI'lar görünüyor.

### Faz 6b — Onaylanan küçük işler `[OPUS]` ✅
- Vurgu `#FF4B26`: `make_article_card.py`, `tools/watermark.py`, `make_og_image.py`, `make_share_image.py` (ruh hâli renkleri aynı). `og.png`, `assets/cards/*`, `share/daily.png` yeniden üretildi; `warsh-inflation-{en,tr}.png` piksel karışımıyla yeniden renklendi. **Not:** tarayıcı/CDN eski görselleri önbellekte tutabilir.
- TR etiketleri: `build.py` `TR_FG`, `_TR_LABEL`, `_trl()`; `app.js` canlı F&G etiketi için `FG_TR`. Yeni TR metinler kullanıcıya gösterildi ("Fed faizi", "4 toplantıdır sabit", "eriyor", "dikleşiyor", "Aşırı Korku"…).
- After Hours: nav'da `.nav-theme` (app.js `initTheme`), `html[data-theme=dark] body.lq` token'ları; her zaman koyu yüzeyler aynı kalır; FE Matrix'te düğme gizli. LIQUID_ASSET_V=4.
- Mailer bu fazda **değiştirilmedi** (başka repo, kirli ağaç, `main`'den koşuyor) → Faz 8'e taşındı.

### Faz 7 — Kalite turu `[OPUS]`
- Her sayfa tipi × 2 dil × 3 genişlik ekran görüntüsü.
- Önce/sonra diff: URL listesi, `sitemap.xml`, `feed-*.xml`, her sayfanın `<link rel=canonical|alternate>` ve JSON-LD'si.
- Lighthouse (performans, erişilebilirlik), kontrast (`--mute` zemin üzerinde AA), JS kapalı görünüm, reduced-motion.
- Eski CSS (`site.css`, `components.css`, `broadsheet.css`) artık yüklenmiyorsa silinir; `finance-eng.css` kalır.

### Faz 8 — Yayın `[OPUS]`, kullanıcı onayıyla
- Merge değil: kaynak dosyalar `main`'e `git checkout feat-liquid -- <dosyalar>` ile alınır, fetcher'lar + `build.py` taze veriyle çalıştırılır, commit, push.
- CI botu üretilmiş HTML'leri de commit'lediği için çakışma normal: rebase + yeniden build.
- Canlı doğrulama: ana sayfa, bir makale, macro, dashboard, `/tr/`, abonelik formu.
- Geri dönüş: `backup/pre-liquid`.
- **Mailer (karar #4, ayrı repo `~/Sikik_Sikik_Fikirler/Crypto_Macro_Newsletter`, `main`):** `send_article.py` satır ~44 `CRIMSON = "#FF4B26"`; satır ~150 buton metni `color:{PAPER}` → `INK` (turuncu üstünde kontrast). Site yayınıyla aynı gün.

## 6. Kararlar (2026-11-15: kullanıcı hepsini öneri sütunundaki gibi onayladı)

| # | Karar | Varsayılan öneri |
|---|---|---|
| 1 | After Hours koyu modu kalsın mı? | Kalsın; bone ↔ ink ters çevrilir, `--hot` aynı |
| 2 | Finance Engineering "Machine Room" Matrix teması | Aynen kalsın (yalnızca menü ve footer yeni çerçeveye uyar) |
| 3 | Üstteki koyu ticker çubuğu | Kaldırılsın; yerini ana sayfadaki büyük şerit alır, iç sayfalarda ince tek satır |
| 4 | Vurgu rengi crimson `#B3122B` → `#FF4B26` | Sosyal kartlar (`make_article_card.py`), watermark ve makale maili (`send_article.py`) de güncellenmeli; ayrı küçük iş |
| 5 | 404 Matrix sayfası ve easter egg'ler | Kalsın |
| 6 | Faz 3'teki iki metin sapması: hero altı "Scroll — the real yield curve"; bülten kutusu açıklaması sitenin mevcut cümlesi | Böyle kalsın |
| 7 | TR sayfalarda İngilizce kalan rejim etiketleri / "Extreme Fear" | Ayrı küçük iş olarak Türkçeleştirilsin |

## 7. Demodan taşırken bilinen noktalar

- Demo veriyi `const D = {...}` olarak gömülü taşır; gerçek sitede build-time enjeksiyon.
- `?static` parametresi animasyonları kapatır; ekran görüntüsü almak için kullan.
- Headless Chrome en az 500px genişlikte çizer: 390px testi için sayfayı 390px'lik iframe içinde aç.
- Headless'ta animasyon ve fare etkileşimi doğrulanamaz; bunları kullanıcı gerçek tarayıcıda onaylar.
- Demodaki #05 makale linki yer tutucudur (`articles.html`); gerçek yol `article_path()` ile gelir.
- Canvas etiketleri mobilde seyrekleştirilir (`small` dalı); 1M etiketinin sol kenarda kesilmediğini kontrol et.

## 8. Opus oturumu nasıl başlatılır

Claude Code'da `/model opus`, ardından:

> `~/nocashflow.net/LIQUID-REDESIGN-PLAN.md` dosyasını oku ve Faz N'i uygula. Kilitli kurallara uy, faz sonunda dur ve özetle.

Her faz ayrı oturumda yapılabilir; plan ve dal durumu yeterli bağlamı taşır.
