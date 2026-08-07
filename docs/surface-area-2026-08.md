# nocashflow.net — Yüzey Alanı Envanteri

**Tarih:** 2026-08-07 · **Kapsam:** hiçbir sayfa silinmedi, bu bir öneri belgesidir
**Toplam:** 72 üretilen sayfa (36 EN + 36 TR) — 16 statik sayfa, 9 makale, 3 FE denemesi, 1 gösterge hub'ı + 6 gösterge, 1 Reference hub'ı

---

## ⚠ Trafik verisi bu raporda yok

Görevde her sayfa için trafik isteniyordu. **Sitede analytics hiç kurulu olmadığı için trafik verisi mevcut değil.** Uydurmadım.

Faz 4.2'de Cloudflare Web Analytics kuruldu ama **henüz veri toplamıyor**: `data/site.json` içindeki `analytics.token` boş. Token girildiği andan itibaren veri birikmeye başlar; bu tablo trafik sütunuyla ancak birkaç hafta sonra anlamlı biçimde doldurulabilir.

Trafik yerine, **erişilebilirlik** ölçtüm: bir sayfaya nav'dan mı, footer'dan mı, yoksa bir içeriğin gövdesinden mi (editoryal link) gidiliyor. Editoryal link sayısı 0 olan bir sayfa, yalnızca menüden bulunabiliyor demektir — trafik ölçülene kadar en iyi vekil gösterge bu.

---

## Sayfa envanteri

`GÜNCEL` = ilgili içerik partial'ının son commit tarihi (üretilen HTML her gün yeniden yazıldığı için dosya tarihi anlamsız).
`EDİT.` = içerik gövdelerinden gelen link sayısı (nav/footer hariç).

| Sayfa | Yol | Güncel | Veri bağımlılığı | İstemci canlı | Nav | Footer | Edit. | Öneri |
|---|---|---|---|---|---|---|---|---|
| Ana sayfa | `/` | 08-07 | macro.json, market.json | — | ✓ | ✓ | 0 | **Koru** |
| Makro | `/macro.html` | 07-26 | calendar.json, macro2.json | ✓ | ✓ | ✓ | 1 | **Koru** |
| Takvim | `/calendar.html` | 06-14 | calendar.json | — | ✓ | ✓ | 1 | **Koru** |
| Panel | `/dashboard.html` | 06-23 | markets.json | ✓ | ✓ | ✓ | 0 | **Birleştir** → Makro |
| Canlı göstergeler | `/now/` + 6 sayfa | — | market.json, macro.json | — | — | ✓ | 0 | **Koru** (SEO) |
| Widget | `/embed.html` | 06-14 | market.js (JSONP) | — | — | ✓ | 0 | **Koru** — ama bkz. B1 |
| Yazılar | `/articles.html` | 08-07 | market.json | — | ✓ | ✓ | 1 | **Koru** |
| Bülten | `/bulletin_page.html` | 08-07 | calendar.json, market.json | — | ✓ | ✓ | 2 | **Koru** |
| Arşiv | `/archive.html` | 06-13 | bulletins/ | — | — | ✓ | 0 | **Koru** |
| Hakkında | `/about.html` | 08-07 | — | — | ✓ | ✓ | 0 | **Koru** |
| Sözlük | `/glossary.html` | 06-28 | — | — | — | ✓ | 0 | **Koru** (bkz. bölüm 3) |
| Finance Engineering | `/finance-engineering.html` | 08-07 | repos.json | — | ✓ | — | 0 | **Koru** — footer'a ekle |
| Reference hub | `/finance-engineering/reference/` | 08-07 | — | — | — | — | 0 | İskelet — madde canlıya alınınca linkle |
| Governance checklist | `…/governance-checklist.html` | 08-07 | — | — | — | — | 0 | İskelet — `noindex` |
| Toolkit | `…/toolkit/` | 08-07 | — | — | — | — | 0 | İskelet — `noindex` |
| Feragatname | `/disclaimer.html` | 06-11 | — | — | — | ✓ | 1 | **Koru** (yasal) |
| Gizlilik | `/privacy.html` | 06-11 | — | — | — | ✓ | 2 | **Koru** (yasal) |
| Yasal bildirim | `/legal.html` | 06-11 | — | — | — | ✓ | 0 | **Koru** (yasal, ES mukimi zorunluluğu) |

### Bakım maliyeti nerede yoğunlaşıyor

Beş sayfa canlı veriye bağlı ve bir besleme düştüğünde görünür şekilde bozulur: **Ana sayfa, Makro, Panel, Takvim, göstergeler**. Diğer 11 statik sayfanın bakım maliyeti pratik olarak sıfır — metin değişmedikçe hiçbir şey bozulmuyor. Yani "12+ sayfa çok" endişesi, maliyetin doğru yerde olmadığını gösteriyor: sorun sayfa **sayısı** değil, beş sayfadaki **veri bağımlılığı**.

---

## 1. Birleştirme önerisi: Panel → Makro

Tek gerçek örtüşme burada.

- **Panel** (`/dashboard.html`, 06-23'ten beri dokunulmamış): `markets.json` → kripto, endeks, emtia, döviz tablosu.
- **Makro** (`/macro.html`): `macro2.json` + takvim → rejim şeridi, getiri eğrisi, enflasyon, Fed.

İkisi de "canlı piyasa ekranı" vaadi veriyor, ikisi de nav'da, ikisine de içerikten link yok. Ziyaretçinin hangisine gitmesi gerektiğini ayırt etmesi için bir sebep yok.

**Öneri:** Panel'in "the tape" tablosunu Makro'nun altına bir bölüm olarak taşı, `/dashboard.html`'i Makro'ya 301 yönlendir (Cloudflare Bulk Redirects zaten kullanılıyor). Nav bir madde kısalır, bakım yükü tek sayfada toplanır.

**Karar senin** — uygulamadım, çünkü bu bir ürün kararı ve iki sayfanın da tasarımı sağlam.

---

## 2. Kırık veri ve sessiz hatalar

Tüm üretilen sayfalar tarandı.

**Sessiz build hatası: yok.** Çözülmemiş tek bir `<!--NCF:*-->` marker'ı kalmamış — yani hiçbir enjeksiyon sessizce atlanmıyor. Build iki ardışık koşuda byte-eş.

**Kırık veri gösteren sayfa: yok.** Faz 1 sonrası her `—`, değeri olmayan bir alanın dürüst gösterimi; yanlış sayı basan yer kalmadı.

Bulunan iki açık madde:

### B1 · Gömülebilir widget zaman damgası basmıyor ⚠

`embed.js` sayıları başka sitelerde yayımlıyor ama **hiçbir zaman damgası göstermiyor** (`asof`/`updated` geçmiyor). `data/market.js` JSONP'si `asof` alanını taşıyor, yani veri elde — sadece render edilmiyor.

Bu, Faz 1'de sitede düzeltilen sorunun aynısı: kaynağına ve saatine bağlı olmayan bir sayı. Üstelik burada daha kötü, çünkü **başkasının sitesinde** görünüyor ve orada kimse tazeliğini denetleyemiyor. Widget'ın kendi sayfası "her gün güncellenir" diyor; damga bunu doğrulanabilir kılar.

**Öneri:** `embed.js`'e Faz 1'deki `.live-stamp` mantığının küçük bir sürümü. Faz 1 kapsamında değildi, ayrı bir iş olarak öneriyorum.

### B2 · `macro2.json`'da elle doldurulan alanlar

Dosyanın kendi notu: *"Manual (no free API): dot plot, ISM, global M2."* Bu alanlar bir cron tarafından tazelenmiyor; elle güncellenmezse sessizce eskirler. Şu an dolular ve makul görünüyorlar, ama **bayatlama sinyali yok** — Faz 1'de market verisine eklenen `stale` etiketinin karşılığı burada yok.

**Öneri:** bu üç alana kendi `updated` damgasını koy ve Makro sayfasında 30 günden eskiyse işaretle. Küçük bir iş, veri güvenilirliği açısından değerli.

---

## 3. Sözlük ↔ Reference: çakışma **yok**

Görevde "Glossary'nin Reference'a devredilip devredilemeyeceğini değerlendir" deniyordu. İkisinin içeriğini karşılaştırdım:

| | Sözlük (15 terim) | Controlling Reference (8 madde) |
|---|---|---|
| **Alan** | Piyasa / makro / kripto | Kurumsal kontrolörlük |
| **Terimler** | Cash Flow, Yield Curve, Inverted Curve, VIX, DXY, Fear &amp; Greed, Coinbase Premium, BTC Dominance, DeFi, PMI, Basis Point, Quantitative Tightening, Smart Money, Oil Intensity, Funding Rate | Standard Cost, Purchase Price Variance, Working Capital, Cash Conversion Cycle, Inventory Accounting, Factory Controlling, Absorption vs Variable Costing, Overhead Allocation |
| **Biçim** | Tek paragraf, tooltip olarak makale içinde kullanılıyor | 8 bölümlü madde: tanım, formül, örnek, SAP, FP&amp;A, hatalar, KPI, çapraz link |
| **Okur** | Bülteni/makaleyi okuyan yatırımcı | FP&amp;A / kontrolör |

**Kesişim sıfır.** Tek bir terim bile ortak değil, ve iki farklı okur kitlesine iki farklı derinlikte hizmet ediyorlar. Sözlük ayrıca makale gövdesinde tooltip olarak **işlevsel** bir rol taşıyor (`gloss_wrap`); Reference'a devredilse o işlev kaybolur.

**Öneri: ikisini de koru, birleştirme.** Temas ettikleri yerde çapraz link kur — örneğin Reference'taki `working-capital` ile Sözlük'teki `Cash Flow`. Reference kayıtlarındaki `related[]`/`articles[]` alanları bunu zaten destekliyor; sözlük terimine link için küçük bir ekleme gerekir.

---

## 4. Öneri özeti

| Öneri | Sayfa | Gerekçe |
|---|---|---|
| **Birleştir** | Panel → Makro | Aynı vaat, iki ekran; Panel 06-23'ten beri dokunulmamış |
| **Koru + iyileştir** | Widget (`embed.html`) | B1: damga yok, sayı başkasının sitesinde damgasız duruyor |
| **Koru + iyileştir** | Makro | B2: elle doldurulan üç alan için bayatlık sinyali yok |
| **Koru** | Sözlük ve Reference ayrı | Sıfır kesişim, farklı okur, sözlük ayrıca tooltip motoru |
| **Koru** | FE hub | Footer'da linki yok — nav'da var ama footer "İçerik" sütununa da eklenmeli |
| **Arşivle** | — | **Arşivlenmesi önerilen sayfa yok.** Yasal üçlü zorunlu, göstergeler SEO taşıyor, geri kalanı aktif. |

**Silinmesi önerilen sayfa yok.** Tek yapısal öneri Panel'in Makro'ya birleştirilmesi; o da bir ürün kararı olduğu için uygulanmadı.
