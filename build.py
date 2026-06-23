#!/usr/bin/env python3
"""
NoCashFlow · static site builder (bilingual)

Single source of truth for the shared chrome (head, ticker, nav, footer,
scripts). Per-page pieces live in content/:

    content/<lang>/<page>.html   body (between nav and footer)        [required]
    content/foot/<page>.html     page-specific tail scripts           [optional, lang-shared]
    content/head/<page>.html     page-specific extra <head> (e.g. <style>)  [optional]

English is emitted at the site root; Turkish under /tr/. A language's page is
built only when its body partial exists, so the live site is never broken
mid-migration.

    python3 build.py            # build everything that has a content partial
    python3 build.py --clean    # remove the generated /tr/ tree first

This builder changes structure (templating + i18n + a normalized head), never
the visual design — page bodies are reproduced byte-for-byte.
"""
import json
import math
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote as _uq

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
SITE_URL = "https://nocashflow.net"
LANGS = ("en", "tr")

# Cloudflare Web Analytics is enabled via Cloudflare's Automatic Setup (the site
# is proxied through Cloudflare, which injects the beacon at the edge). No manual
# snippet here — adding one would double-count page views.

# One consolidated Google Fonts request (Fraunces display · Newsreader body ·
# IBM Plex Mono data) — replaces the extra render-blocking @import in site.css.
FONTS_URL = ("https://fonts.googleapis.com/css2"
             "?family=Fraunces:ital,opsz,wght@0,9..144,300..900;1,9..144,300..900"
             "&family=Newsreader:ital,opsz,wght@0,6..72,300..600;1,6..72,300..500"
             "&family=Libre+Caslon+Display"
             "&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,500;0,8..60,600;1,8..60,400"
             "&family=IBM+Plex+Mono:wght@400;500;600&display=swap")

# After Hours theme — pre-paint decision (no flash): stored preference wins;
# otherwise dark between 21:00–07:00 local. ?theme=dark|light overrides + persists.
THEME_SCRIPT = (
    "<script>(function(){var d=document.documentElement;try{"
    "var q=new URLSearchParams(location.search).get('theme');"
    "if(q==='dark'||q==='light'){try{localStorage.setItem('ncf_theme',q);}catch(e){}}"
    "var t=null;try{t=localStorage.getItem('ncf_theme');}catch(e){}"
    "if(!t){var h=new Date().getHours();t=(h>=21||h<7)?'dark':'light';}"
    "if(t==='dark')d.setAttribute('data-theme','dark');}catch(e){}})();</script>"
)


def _mood():
    """Market mood from the committed Fear & Greed snapshot: fear / neutral / greed."""
    try:
        v = int(MARKET["instruments"]["fg"]["px"])
        return "fear" if v < 35 else ("greed" if v > 55 else "neutral")
    except Exception:
        return "neutral"


def _fg_value():
    try:
        d = MARKET["instruments"]["fg"]
        return int(d["px"]), d.get("chg", "")
    except Exception:
        return None, ""


MOOD_LABEL = {
    "en": {"fear": "fearful", "neutral": "undecided", "greed": "greedy"},
    "tr": {"fear": "korkuyor", "neutral": "kararsız", "greed": "açgözlü"},
}


def _mood_line(lang):
    """One honest sentence in the footer: how the market feels today (real F&G)."""
    v, _ = _fg_value()
    if v is None:
        return ""
    m = _mood()
    if lang == "en":
        txt = f"Today the market is {MOOD_LABEL['en'][m]} — Fear &amp; Greed {v}/100."
    else:
        txt = f"Bugün piyasa {MOOD_LABEL['tr'][m]} — Fear &amp; Greed {v}/100."
    return f'<div class="mood-line"><span class="mood-dot"></span>{txt}</div>'


def _mood_pill(lang):
    """Compact badge above the hero title — real F&G, mood-coloured."""
    v, label = _fg_value()
    if v is None:
        return ""
    m = _mood()
    head = "Market mood" if lang == "en" else "Piyasa modu"
    word = MOOD_LABEL[lang][m]
    return (f'<div class="mood-pill" data-m="{m}"><span class="mp-dot"></span>'
            f'<span class="mp-k">{head}</span>'
            f'<span class="mp-w">{word}</span>'
            f'<span class="mp-v">F&amp;G {v}</span></div>')


# ── generative hero frieze: the real US yield curve, redrawn on every build ──
def hero_frieze(lang):
    curve = MACRO.get("curve") or []
    if len(curve) < 4:
        return ""
    W, H, PAD = 1200, 150, 46
    vals = [p["v"] for p in curve]
    mn, mx = min(vals), max(vals)
    rng = (mx - mn) or 1.0
    pts = []
    for i, p in enumerate(curve):
        x = PAD + i * (W - 2 * PAD) / (len(curve) - 1)
        y = H - 34 - ((p["v"] - mn) / rng) * (H - 70)
        pts.append((x, y, p["l"], p["v"]))

    # smooth path (Catmull-Rom → cubic bézier)
    def path_d(points):
        if len(points) < 3:
            return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y, *_ in points)
        d = f"M{points[0][0]:.1f},{points[0][1]:.1f}"
        for i in range(len(points) - 1):
            p0 = points[max(i - 1, 0)]; p1 = points[i]
            p2 = points[i + 1]; p3 = points[min(i + 2, len(points) - 1)]
            c1x = p1[0] + (p2[0] - p0[0]) / 6; c1y = p1[1] + (p2[1] - p0[1]) / 6
            c2x = p2[0] - (p3[0] - p1[0]) / 6; c2y = p2[1] - (p3[1] - p1[1]) / 6
            d += f" C{c1x:.1f},{c1y:.1f} {c2x:.1f},{c2y:.1f} {p2[0]:.1f},{p2[1]:.1f}"
        return d

    d = path_d(pts)
    area = d + f" L{pts[-1][0]:.1f},{H - 26} L{pts[0][0]:.1f},{H - 26} Z"
    ticks = "".join(
        f'<g><circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" class="hf-pt"/>'
        f'<text x="{x:.1f}" y="{H - 10}" class="hf-lbl">{l}</text>'
        f'<text x="{x:.1f}" y="{y - 9:.1f}" class="hf-val">{v:.2f}</text></g>'
        for x, y, l, v in pts)
    date = MACRO.get("us10y", {}).get("date", "")
    cap = (f"US Treasury yield curve · drawn {date} · FRED" if lang == "en"
           else f"ABD Hazine getiri eğrisi · {date} çizimi · FRED")
    return f"""
<!-- HERO FRIEZE — generated from data/macro.json at build time; the site redraws itself daily -->
<div class="hero-frieze" aria-hidden="true">
  <svg viewBox="0 0 {W} {H}" preserveAspectRatio="none">
    <line x1="{PAD}" y1="{H - 26}" x2="{W - PAD}" y2="{H - 26}" class="hf-base"/>
    <path d="{area}" class="hf-area"/>
    <path d="{d}" class="hf-line"/>
    {ticks}
  </svg>
  <div class="hf-cap">{cap}</div>
</div>
"""


# ── Market Pulse signature chart: the real yield curve with proper axes ──────
def pulse_chart(lang):
    """Analytical yield-curve chart for the Market Pulse board (home, Broadsheet).
    Real data from data/macro.json; redrawn on every build. No fabricated series."""
    curve = MACRO.get("curve") or []
    if len(curve) < 4:
        return ""
    W, H = 1000, 300
    PL, PR, PT, PB = 52, 20, 26, 40
    vals = [p["v"] for p in curve]
    lo = math.floor(min(vals) * 4) / 4 - 0.05
    hi = math.ceil(max(vals) * 4) / 4 + 0.05
    rng = (hi - lo) or 1.0
    xs = lambda i: PL + i * (W - PL - PR) / (len(curve) - 1)
    ys = lambda v: PT + (hi - v) / rng * (H - PT - PB)
    # y gridlines / ticks
    grid = []
    steps = 4
    for k in range(steps + 1):
        v = lo + (hi - lo) * k / steps
        y = ys(v)
        grid.append(f'<line class="pc-grid" x1="{PL}" x2="{W-PR}" y1="{y:.1f}" y2="{y:.1f}"/>'
                    f'<text class="pc-yl" x="{PL-10}" y="{y+3:.1f}">{v:.2f}</text>')
    # line + points + tenor labels
    d = "M" + " L".join(f"{xs(i):.1f} {ys(p['v']):.1f}" for i, p in enumerate(curve))
    pts, last = [], len(curve) - 1
    for i, p in enumerate(curve):
        emph = ' pc-pt-last' if i == last else ''
        pts.append(f'<circle class="pc-pt{emph}" cx="{xs(i):.1f}" cy="{ys(p["v"]):.1f}" r="{3.6 if i==last else 2.8:.1f}"/>'
                   f'<text class="pc-xl" x="{xs(i):.1f}" y="{H-PB+20}">{p["l"]}</text>')
    # 2s10s spread annotation, computed from the real curve
    by_l = {p["l"]: p["v"] for p in curve}
    spr_txt = ""
    if "2Y" in by_l and "10Y" in by_l:
        bps = round((by_l["10Y"] - by_l["2Y"]) * 100)
        sign = "+" if bps >= 0 else ""
        word = ("steepening at the long end" if bps >= 0 else "still inverted")
        if lang != "en":
            word = ("uzun vadede dikleşiyor" if bps >= 0 else "hâlâ ters")
        lab = "2s10s spread" if lang == "en" else "2s10s farkı"
        spr_txt = (f'<div class="pc-annot"><span class="pc-annot-v">{sign}{bps} bps</span>'
                   f'<span class="pc-annot-k">{lab} · {word}</span></div>')
    date = MACRO.get("us10y", {}).get("date", "")
    title = "US Treasury yield curve" if lang == "en" else "ABD Hazine getiri eğrisi"
    src = (f"Source: FRED · drawn {date}" if lang == "en" else f"Kaynak: FRED · {date} çizimi")
    return f"""
<figure class="pc-fig">
  <figcaption class="pc-head">
    <span class="pc-title">{title}</span>
    <span class="pc-src">{src}</span>
  </figcaption>
  <svg class="pc-svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="{title}">
    {''.join(grid)}
    <path class="pc-line" d="{d}" fill="none"/>
    {''.join(pts)}
  </svg>
  {spr_txt}
</figure>"""


# ── bulletin-page aside: next high-impact events from the real calendar ─────
def inject_cal_brief(html, lang):
    if "<!--NCF:CAL_BRIEF-->" not in html:
        return html
    evs = [e for e in CALENDAR.get("events", []) if e.get("impact") == "high"][:3]
    if len(evs) < 3:
        evs += [e for e in CALENDAR.get("events", []) if e.get("impact") == "medium"][: 3 - len(evs)]
    items = []
    imp_lbl = {"high": ("High impact ⭐", "Yüksek etki ⭐"), "medium": ("Medium", "Orta")}
    for e in evs:
        wd = WEEKDAYS[lang][e["wd"]] if 0 <= e.get("wd", -1) <= 6 else ""
        imp = imp_lbl.get(e.get("impact"), ("", ""))[0 if lang == "en" else 1]
        sub = ""
        if e.get("prev", "—") != "—" or e.get("est", "—") != "—":
            pv = "Prev" if lang == "en" else "Önceki"
            cs = "Cons" if lang == "en" else "Beklenti"
            sub = f'<p>{pv} {e.get("prev", "—")} · {cs} {e.get("est", "—")}</p>'
        items.append(f'<div class="brief-item"><div class="t">{wd} {e.get("time", "")} · {imp}</div>'
                     f'<h4>{e.get("event", "")}</h4>{sub}</div>')
    return html.replace("<!--NCF:CAL_BRIEF-->", "\n          ".join(items))


# ── bulletin-page sample: honest auto note from the snapshot ─────────────────
def inject_snapshot_note(html, lang):
    if "<!--NCF:SNAP_NOTE-->" not in html:
        return html
    v, label = _fg_value()
    stamp = _fmt_stamp(MARKET.get("asof", ""), lang)
    if lang == "en":
        txt = (f"Live snapshot as of {stamp}. Crypto Fear &amp; Greed at {v}/100 ({label}). "
               f'The full picture — calendar, Fed watch and the desk note — is in '
               f'<a href="/bulletins/daily/latest.en.html" target="_blank" rel="noopener">today\'s issue →</a>')
    else:
        txt = (f"Canlı görüntü, {stamp} itibarıyla. Kripto Fear &amp; Greed {v}/100 ({label}). "
               f'Tam resim — takvim, Fed takibi ve masa notu — '
               f'<a href="/bulletins/daily/latest.tr.html" target="_blank" rel="noopener">bugünkü sayıda →</a>')
    return html.replace("<!--NCF:SNAP_NOTE-->", txt)


# ── bulletin archive: every dated issue the pipeline has pushed ──────────────
def inject_archive(html, lang):
    if "<!--NCF:ARCHIVE-->" not in html:
        return html
    import glob as _g
    out = []
    for kind, title_en, title_tr in (("weekly", "Weekly Deep Dive", "Haftalık Derin Analiz"),
                                     ("daily", "Daily Pulse", "Günlük Nabız")):
        files = sorted(_g.glob(str(ROOT / "bulletins" / kind / "*.[et][nr].html")), reverse=True)
        dates = sorted({Path(f).name.rsplit(".", 2)[0] for f in files
                        if not Path(f).name.startswith("latest")}, reverse=True)
        if not dates:
            continue
        rows = []
        for ds in dates:
            other = "en" if lang == "tr" else "tr"
            rows.append(
                f'<li class="arch-row"><span class="arch-date">{ds}</span>'
                f'<span class="arch-links"><a href="/bulletins/{kind}/{ds}.{lang}.html" target="_blank" rel="noopener">'
                f'{"Read" if lang == "en" else "Oku"} →</a>'
                f'<a class="arch-alt" href="/bulletins/{kind}/{ds}.{other}.html" target="_blank" rel="noopener">{other.upper()}</a></span></li>')
        t = title_en if lang == "en" else title_tr
        out.append(f'<div class="section-header" style="margin-top:40px"><div class="section-title" style="font-size:22px">{t}</div>'
                   f'<div class="section-meta">{len(dates)} {"issues" if lang == "en" else "sayı"}</div></div>'
                   f'<ul class="arch-list">{"".join(rows)}</ul>')
    if not out:
        msg = "The archive starts filling up as issues are published." if lang == "en" \
            else "Arşiv, sayılar yayımlandıkça dolmaya başlayacak."
        out.append(f'<p class="muted" style="font-family:var(--mono);font-size:13px">{msg}</p>')
    return html.replace("<!--NCF:ARCHIVE-->", "\n".join(out))


# ── glossary tooltips: terms from sozluk, dotted-underlined in article prose ─
def _glossary_terms(lang):
    src = _read(f"{lang}/sozluk.html")
    return re.findall(r'<h3>(.*?)</h3><p>(.*?)</p>', src)


def gloss_wrap(prose, lang):
    """Wrap the first plain-text occurrence of each glossary term in a CSS-tooltip
    span. Operates on text tokens only (never inside tags/attributes/links)."""
    terms = sorted(_glossary_terms(lang), key=lambda t: -len(t[0]))
    if not terms:
        return prose
    tokens = re.split(r'(<[^>]+>)', prose)
    in_skip = 0
    done = set()
    for i, tok in enumerate(tokens):
        if tok.startswith("<"):
            low = tok.lower()
            if re.match(r'<(a|h\d|code)[\s>]', low):
                in_skip += 1
            elif re.match(r'</(a|h\d|code)>', low):
                in_skip = max(0, in_skip - 1)
            continue
        if in_skip or not tok.strip():
            continue
        for term, desc in terms:
            t_plain = re.sub(r'&amp;', '&', term)
            if t_plain in done:
                continue
            pat = re.compile(r'(?<![\w&])(' + re.escape(t_plain) + r')(?![\w;])')
            if pat.search(tok):
                d_attr = re.sub(r'<[^>]+>', '', desc).replace('"', '&quot;')
                tokens[i] = pat.sub(
                    lambda m: f'<span class="gloss" tabindex="0" data-gd="{d_attr}">{m.group(1)}</span>',
                    tok, count=1)
                tok = tokens[i]
                done.add(t_plain)
    return "".join(tokens)

# ── shared navigation (key, label_en, label_tr, href_en, href_tr) ────────────
NAV = [
    ("home",      "Home",      "Ana Sayfa", "/",                   "/tr/"),
    ("articles",  "Articles",  "Yazılar",   "/yazilar.html",       "/tr/yazilar.html"),
    ("macro",     "Macro",     "Makro",     "/macro.html",         "/tr/macro.html"),
    ("calendar",  "Calendar",  "Takvim",    "/calendar.html",      "/tr/takvim.html"),
    ("dashboard", "Dashboard", "Panel",     "/dashboard.html",     "/tr/dashboard.html"),
    ("bulletin",  "Bulletin",  "Bülten",    "/bulletin_page.html", "/tr/bulletin_page.html"),
    ("finance-eng", "Finance Engineering", "Finance Engineering", "/finance-engineering.html", "/tr/finance-engineering.html"),
    ("about",     "About",     "Hakkında",  "/hakkinda.html",      "/tr/hakkinda.html"),
]

SUBSCRIBE = {"en": ("Subscribe", "/bulletin_page.html"),
             "tr": ("Abone Ol",  "/tr/bulletin_page.html")}

FOOTER = {
    "en": {
        "brand_desc": "Independent macro &amp; markets, published daily. Sourced data, no fabrication.",
        "col_pages": "Pages", "col_content": "Content", "col_social": "Social",
        "l_home": "Home", "l_articles": "Articles", "l_macro": "Macro", "l_dashboard": "Dashboard",
        "l_bulletin": "Bulletin", "l_about": "About", "l_glossary": "Glossary",
        "l_email": "Email", "bottom_about": "About", "bottom_subscribe": "Subscribe",
        "l_privacy": "Privacy", "l_legal": "Legal Notice", "l_disclaimer": "Disclaimer",
        "l_archive": "Archive", "l_rss": "RSS", "l_indicators": "Live Indicators",
        "l_calendar": "Economic Calendar", "l_widget": "Embed Widget",
        "disclaimer": "This site is for information only and does not provide investment advice.",
    },
    "tr": {
        "brand_desc": "Bağımsız makro &amp; piyasa, her gün yayımlanır. Kaynaklı veri, uydurma yok.",
        "col_pages": "Sayfalar", "col_content": "İçerik", "col_social": "Sosyal",
        "l_home": "Ana Sayfa", "l_articles": "Yazılar", "l_macro": "Makro", "l_dashboard": "Panel",
        "l_bulletin": "Bülten", "l_about": "Hakkında", "l_glossary": "Sözlük",
        "l_email": "E-posta", "bottom_about": "Hakkında", "bottom_subscribe": "Abone Ol",
        "l_privacy": "Gizlilik", "l_legal": "Yasal Bildirim", "l_disclaimer": "Feragatname",
        "l_archive": "Arşiv", "l_rss": "RSS", "l_indicators": "Canlı Göstergeler",
        "l_calendar": "Ekonomik Takvim", "l_widget": "Widget Göm",
        "disclaimer": "Bu site yalnızca bilgilendirme amaçlıdır ve yatırım tavsiyesi içermez.",
    },
}

def _flink(lang, en_href, tr_href):
    return en_href if lang == "en" else tr_href

# ── page registry ─────────────────────────────────────────────────────────────
# title/desc are reproduced verbatim from each live page. hakkinda & sozluk are
# still Turkish at root; the translation phase produces proper EN root + TR /tr/.
PAGES = {
    "index": {
        "nav_key": "home", "splash": True, "cursor": True,
        "paths": {"en": "/", "tr": "/tr/"},
        "out":   {"en": "index.html", "tr": "tr/index.html"},
        "title": {"en": "NoCashFlow — Macro &amp; Market Analysis",
                  "tr": "NoCashFlow — Makro &amp; Piyasa Analizi"},
        "desc":  {"en": "Data-driven macro analysis every morning, with a deep dive every Sunday — oil shocks, smart money, nuclear energy, Fed policy. From Barcelona.",
                  "tr": "Her sabah veri odaklı makro analiz, her pazar derin bir analiz — petrol şokları, akıllı para, nükleer enerji, Fed politikası. Barcelona'dan."},
        "og_desc": {"en": "Data-driven macro analysis every morning, plus a deep dive every Sunday. Macro, crypto and commodities — primary source, always linked.",
                    "tr": "Her sabah veri odaklı makro analiz, her pazar derin analiz. Makro, kripto ve emtia — birincil kaynak, her zaman bağlantılı."},
    },
    "macro": {
        "nav_key": "macro",
        "paths": {"en": "/macro.html", "tr": "/tr/macro.html"},
        "out":   {"en": "macro.html", "tr": "tr/macro.html"},
        "title": {"en": "Macro — NoCashFlow | Global Macro Indicators",
                  "tr": "Makro — NoCashFlow | Küresel Makro Göstergeler"},
        "desc":  {"en": "Live global macro dashboard — VIX, DXY, US yields, the yield curve, commodities and the economic calendar.",
                  "tr": "Canlı küresel makro panosu — VIX, DXY, ABD getirileri, getiri eğrisi, emtia ve ekonomik takvim."},
    },
    "calendar": {
        "nav_key": "calendar",
        "paths": {"en": "/calendar.html", "tr": "/tr/takvim.html"},
        "out":   {"en": "calendar.html", "tr": "tr/takvim.html"},
        "title": {"en": "Economic Calendar This Week — NoCashFlow | CPI, Fed, Jobs",
                  "tr": "Bu Hafta Ekonomik Takvim — NoCashFlow | TÜFE, Fed, İstihdam"},
        "desc":  {"en": "This week's economic calendar — every key US and euro-area release with date, time (CET), previous and consensus. High-impact events flagged.",
                  "tr": "Bu haftanın ekonomik takvimi — her önemli ABD ve euro bölgesi verisi; tarih, saat (CET), önceki ve beklenti ile. Yüksek etkili olaylar işaretli."},
    },
    "embed": {
        "nav_key": None,  # utility/tools page — footer only, not under Macro
        "paths": {"en": "/embed.html", "tr": "/tr/embed.html"},
        "out":   {"en": "embed.html", "tr": "tr/embed.html"},
        "title": {"en": "Free Market Data Widget — NoCashFlow | Embed Live Macro",
                  "tr": "Ücretsiz Piyasa Verisi Widget'ı — NoCashFlow | Canlı Makro Göm"},
        "desc":  {"en": "Embed a free live market widget on your site — Crypto Fear & Greed, Bitcoin, gold and US yields, updated daily. One line of HTML.",
                  "tr": "Sitene ücretsiz canlı piyasa widget'ı göm — Kripto Korku & Açgözlülük, Bitcoin, altın ve ABD getirileri, her gün güncel. Tek satır HTML."},
    },
    "yazilar": {
        "nav_key": "articles",
        "paths": {"en": "/yazilar.html", "tr": "/tr/yazilar.html"},
        "out":   {"en": "yazilar.html", "tr": "tr/yazilar.html"},
        "title": {"en": "Articles — NoCashFlow | Macro &amp; Market Essays",
                  "tr": "Yazılar — NoCashFlow | Makro &amp; Piyasa Yazıları"},
        "desc":  {"en": "Macro analysis essays — oil, copper, nuclear energy, Fed policy, smart money. Sharp macro &amp; market takes, published regularly.",
                  "tr": "Makro analiz yazıları — petrol, bakır, nükleer enerji, Fed politikası, akıllı para. Keskin makro &amp; piyasa yorumları, düzenli yayımlanır."},
        "og_desc": {"en": "Data-driven macro analysis essays. Sharp macro &amp; market takes, published regularly.",
                    "tr": "Veri odaklı makro analiz yazıları. Keskin makro &amp; piyasa yorumları, düzenli yayımlanır."},
    },
    "dashboard": {
        "nav_key": "dashboard",
        "paths": {"en": "/dashboard.html", "tr": "/tr/dashboard.html"},
        "out":   {"en": "dashboard.html", "tr": "tr/dashboard.html"},
        "title": {"en": "Dashboard — NoCashFlow | Live Markets",
                  "tr": "Panel — NoCashFlow | Canlı Piyasalar"},
        "desc":  {"en": "Live market dashboard — crypto, indices, commodities and FX in one view, refreshed automatically.",
                  "tr": "Canlı piyasa paneli — kripto, endeksler, emtia ve döviz tek ekranda, otomatik yenilenir."},
    },
    "bulletin_page": {
        "nav_key": "bulletin",
        "paths": {"en": "/bulletin_page.html", "tr": "/tr/bulletin_page.html"},
        "out":   {"en": "bulletin_page.html", "tr": "tr/bulletin_page.html"},
        "title": {"en": "Bulletin — NoCashFlow | The Daily Macro Brief",
                  "tr": "Bülten — NoCashFlow | Günlük Makro Özet"},
        "desc":  {"en": "The NoCashFlow Bulletin — a morning macro snapshot, crypto signals, Fed watch and the economic calendar. Free, every morning.",
                  "tr": "NoCashFlow Bülteni — sabah makro özeti, kripto sinyalleri, Fed takibi ve ekonomik takvim. Ücretsiz, her sabah."},
    },
    "hakkinda": {
        "nav_key": "about",
        "paths": {"en": "/hakkinda.html", "tr": "/tr/hakkinda.html"},
        "out":   {"en": "hakkinda.html", "tr": "tr/hakkinda.html"},
        "title": {"en": "About — NoCashFlow | Orkun Biçen",
                  "tr": "Hakkında — NoCashFlow | Orkun Biçen"},
        "desc":  {"en": "Orkun Biçen — supply chain and operations manager, MBA, macro analyst. Founder of NoCashFlow.",
                  "tr": "Orkun Biçen — tedarik zinciri yöneticisi, MBA, makro analist. NoCashFlow'un kurucusu."},
    },
    "sozluk": {
        "nav_key": None,  # glossary lives in the footer, not the primary nav
        "paths": {"en": "/sozluk.html", "tr": "/tr/sozluk.html"},
        "out":   {"en": "sozluk.html", "tr": "tr/sozluk.html"},
        "title": {"en": "Glossary — NoCashFlow | Financial Terms",
                  "tr": "Sözlük — NoCashFlow | Finansal Terimler"},
        "desc":  {"en": "Plain explanations of macro, market and crypto terms — the NoCashFlow financial glossary.",
                  "tr": "Makro ekonomi, piyasa ve kripto terimlerinin sade açıklamaları — NoCashFlow finansal sözlüğü."},
    },
    "finance-eng": {
        "nav_key": "finance-eng",
        "paths": {"en": "/finance-engineering.html", "tr": "/tr/finance-engineering.html"},
        "out":   {"en": "finance-engineering.html", "tr": "tr/finance-engineering.html"},
        "title": {"en": "Finance Engineering — NoCashFlow | How this is built",
                  "tr": "Finance Engineering — NoCashFlow | Nasıl kuruldu"},
        "desc":  {"en": "How NoCashFlow is engineered — the data pipeline, the automation, and the rule that every number is sourced, never fabricated.",
                  "tr": "NoCashFlow nasıl mühendislik edildi — veri pipeline'ı, otomasyon ve her rakamın kaynaklı, asla uydurma olmaması ilkesi."},
    },
    "disclaimer": {
        "nav_key": None,
        "paths": {"en": "/disclaimer.html", "tr": "/tr/disclaimer.html"},
        "out":   {"en": "disclaimer.html", "tr": "tr/disclaimer.html"},
        "title": {"en": "Disclaimer — NoCashFlow", "tr": "Feragatname — NoCashFlow"},
        "desc":  {"en": "NoCashFlow is for information only and does not provide investment advice.",
                  "tr": "NoCashFlow yalnızca bilgilendirme amaçlıdır ve yatırım tavsiyesi içermez."},
    },
    "privacy": {
        "nav_key": None,
        "paths": {"en": "/privacy.html", "tr": "/tr/privacy.html"},
        "out":   {"en": "privacy.html", "tr": "tr/privacy.html"},
        "title": {"en": "Privacy Policy — NoCashFlow", "tr": "Gizlilik Politikası — NoCashFlow"},
        "desc":  {"en": "How NoCashFlow handles your data, in line with the EU GDPR.",
                  "tr": "NoCashFlow verilerini AB GDPR'ına uygun olarak nasıl işler."},
    },
    "legal": {
        "nav_key": None,
        "paths": {"en": "/legal.html", "tr": "/tr/legal.html"},
        "out":   {"en": "legal.html", "tr": "tr/legal.html"},
        "title": {"en": "Legal Notice — NoCashFlow", "tr": "Yasal Bildirim — NoCashFlow"},
        "desc":  {"en": "Aviso Legal — site ownership and terms of use.",
                  "tr": "Aviso Legal — site sahipliği ve kullanım koşulları."},
    },
    "archive": {
        "nav_key": "bulletin",
        "paths": {"en": "/archive.html", "tr": "/tr/arsiv.html"},
        "out":   {"en": "archive.html", "tr": "tr/arsiv.html"},
        "title": {"en": "Archive — NoCashFlow Bulletins", "tr": "Arşiv — NoCashFlow Bültenleri"},
        "desc":  {"en": "Every published issue of the NoCashFlow daily and weekly bulletins, in chronological order.",
                  "tr": "NoCashFlow günlük ve haftalık bültenlerinin yayımlanmış tüm sayıları, kronolojik sırayla."},
    },
}

# ── helpers ──────────────────────────────────────────────────────────────────
def _exists(lang, page):
    return (CONTENT / lang / f"{page}.html").exists()

def _read(rel):
    p = CONTENT / rel
    return p.read_text(encoding="utf-8").rstrip("\n") if p.exists() else ""


# ── data snapshots (written by scripts/fetch_data.py) ────────────────────────
def _load_data(name):
    p = ROOT / "data" / name
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

MARKET = _load_data("market.json")
CALENDAR = _load_data("calendar.json")
MACRO = _load_data("macro.json")
MARKETS = _load_data("markets.json")        # dashboard "the tape" feed (Phase 1)
MACRO2 = _load_data("macro2.json")           # macro "the regime" page feed (Phase 2)
MACRO_NOTES = _load_data("macro-notes.json")  # human-authored read/notes (Phase 2)

WEEKDAYS = {"en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "tr": ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]}
MONTHS = {"en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
          "tr": ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]}
COUNTRY = {
    "US": ("🇺🇸", "USD"), "EA": ("🇪🇺", "EUR"), "EU": ("🇪🇺", "EUR"),
    "DE": ("🇩🇪", "EUR"), "FR": ("🇫🇷", "EUR"), "IT": ("🇮🇹", "EUR"),
    "ES": ("🇪🇸", "EUR"), "NL": ("🇳🇱", "EUR"), "BE": ("🇧🇪", "EUR"),
    "AT": ("🇦🇹", "EUR"), "PT": ("🇵🇹", "EUR"), "IE": ("🇮🇪", "EUR"),
    "FI": ("🇫🇮", "EUR"), "GR": ("🇬🇷", "EUR"),
}
CAL_STALE = {"en": "Calendar data is more than 48 hours old — refresh pending.",
             "tr": "Takvim verisi 48 saatten eski — güncelleme bekleniyor."}
CAL_MAX_ROWS = 12  # keep the table readable; calendar.json keeps the full set


def inject_market(html):
    """Fill data-px / data-chg placeholders with the build-time snapshot so the
    page is never blank if client-side JS or live APIs fail. app.js refreshes."""
    for key, d in MARKET.get("instruments", {}).items():
        px, chg, dirc = d.get("px", "—"), d.get("chg", "—"), d.get("dir", "neu")
        html = re.sub(r'(data-px="' + re.escape(key) + r'"\s*>)—',
                      lambda m, px=px: m.group(1) + px, html)
        html = re.sub(r'class="([^"]*?) neu"(\s+data-chg="' + re.escape(key) + r'"\s*>)—',
                      lambda m, chg=chg, dirc=dirc: f'class="{m.group(1)} {dirc}"{m.group(2)}{chg}',
                      html)
    # Fed funds target (real, FRED DFEDTARU) — fills the data-fed cell on Articles
    fed = MACRO.get("fed_rate", {}).get("value")
    if fed is not None:
        html = re.sub(r'(data-fed\s*>)[^<]*',
                      lambda m, fed=fed: m.group(1) + f"{fed:.2f}%", html)
    # Funding rate (real, Deribit) — build-time fill of the dashboard card
    fund = MACRO.get("funding", {}).get("value")
    if fund is not None:
        html = re.sub(r'(id="funding"[^>]*>)—',
                      lambda m, fund=fund: m.group(1) + f'{"+" if fund >= 0 else ""}{fund:.4f}%', html)
    return html


def _set_id(html, id_, text):
    return re.sub(r'(\sid="' + re.escape(id_) + r'"[^>]*>)[^<]*(<)',
                  lambda m, text=text: m.group(1) + text + m.group(2), html, count=1)


def _set_chg_id(html, id_, text, dirc):
    return re.sub(r'class="([^"]*?) neu"([^>]*\sid="' + re.escape(id_) + r'"[^>]*>)[^<]*(<)',
                  lambda m, text=text, dirc=dirc: f'class="{m.group(1)} {dirc}"{m.group(2)}{text}{m.group(3)}',
                  html, count=1)


def inject_macro(html, lang):
    """Build-time fill of the macro page's id-based KPIs (so no-JS / failed-API
    still shows real numbers). loadSnapshot()/loadLive() then refresh them."""
    if 'id="yield-chart"' not in html:
        return html
    inst = MARKET.get("instruments", {})
    if "vix" in inst:
        html = _set_id(html, "m-vix", inst["vix"]["px"])
        html = _set_chg_id(html, "m-vix-c", inst["vix"]["chg"], inst["vix"]["dir"])
    if "dxy" in inst:
        html = _set_id(html, "m-dxy", inst["dxy"]["px"])
        html = _set_chg_id(html, "m-dxy-c", inst["dxy"]["chg"], inst["dxy"]["dir"])
        html = _set_id(html, "sb-dxy", inst["dxy"]["px"])
    if "fg" in inst:
        html = _set_id(html, "m-fg", inst["fg"]["px"])
    if MACRO.get("us2y"):
        html = _set_id(html, "m-2y", f'{MACRO["us2y"]["value"]:.2f}%')
        html = _set_chg_id(html, "m-2y-c", MACRO["us2y"]["chg"], MACRO["us2y"]["dir"])
    if MACRO.get("us10y"):
        html = _set_id(html, "m-10y", f'{MACRO["us10y"]["value"]:.2f}%')
        html = _set_chg_id(html, "m-10y-c", MACRO["us10y"]["chg"], MACRO["us10y"]["dir"])
    if MACRO.get("spread") is not None:
        sp = MACRO["spread"]
        lbl = ("Normal curve" if lang == "en" else "Normal eğri") if sp >= 0 \
            else ("Inverted ⚠" if lang == "en" else "Ters ⚠")
        html = _set_id(html, "m-spread", f'{"+" if sp >= 0 else ""}{sp:.2f}%')
        html = _set_chg_id(html, "m-spread-c", lbl, "up" if sp >= 0 else "dn")
    if MACRO.get("m2"):
        html = _set_id(html, "sb-m2", f'${MACRO["m2"]["value"]:.1f}T')
    if MACRO.get("mfg"):
        v = MACRO["mfg"]["value"]
        html = _set_id(html, "sb-pmi", f"{v:.1f}")
        lbl = ("Expansion" if lang == "en" else "Genişleme") if v >= 0 \
            else ("Contraction" if lang == "en" else "Daralma")
        html = _set_id(html, "sb-pmi-c", lbl)
    return html


def _fmt_stamp(iso, lang):
    try:
        dt = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return "—"
    try:
        from zoneinfo import ZoneInfo
        dt = dt.astimezone(ZoneInfo("Europe/Berlin"))
    except Exception:
        dt = dt.astimezone(timezone(timedelta(hours=1)))
    return f"{dt.day} {MONTHS[lang][dt.month - 1]} {dt.year}, {dt:%H:%M} CET"


def _is_stale(iso, hours=48):
    try:
        dt = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return False
    return (datetime.now(timezone.utc) - dt) > timedelta(hours=hours)


def _cal_day_label(cet_date, lang):
    """'2026-06-10' -> 'Tue · Jun 10' / 'Sal · 10 Haz'."""
    try:
        y, m, d = (int(x) for x in cet_date.split("-"))
        wd = datetime(y, m, d).weekday()
        mon = MONTHS[lang][m - 1]
        wlabel = WEEKDAYS[lang][wd]
        return f"{wlabel} · {mon} {d}" if lang == "en" else f"{wlabel} · {d} {mon}"
    except Exception:
        return cet_date


def inject_calendar_full(html, lang):
    """Standalone /calendar page: the full week, grouped by day, nothing capped."""
    if "<!--NCF:CAL_FULL-->" not in html:
        return html
    events = CALENDAR.get("events", [])
    high_n = sum(1 for e in events if e.get("impact") == "high")
    groups = {}
    order = []
    for e in events:
        k = e.get("cet_date", "")
        if k not in groups:
            groups[k] = []
            order.append(k)
        groups[k].append(e)

    blocks = []
    for day in order:
        rows = []
        for e in groups[day]:
            flag, ccy = COUNTRY.get(e.get("country", ""), ("🏳️", e.get("country", "")))
            name = e.get("event", "")
            if e.get("impact") == "high":
                ev = f'<span class="impact high"></span><strong>{name} ⭐</strong>'
            else:
                ev = f'<span class="impact med"></span>{name}'
            act = e.get("act", "—")
            act_cell = (f'<td class="mono cal-actual"><strong>{act}</strong></td>'
                        if act != "—" else '<td class="mono">—</td>')
            rows.append(
                f'<tr class="cal-row"><td class="mono">{e.get("time", "")}</td>'
                f'<td>{ev}</td><td>{flag} {ccy}</td>'
                f'<td class="mono">{e.get("prev", "—")}</td>'
                f'<td class="mono">{e.get("est", "—")}</td>'
                f'{act_cell}</tr>')
        blocks.append(
            f'<div class="cal-day">'
            f'<div class="cal-day-head">{_cal_day_label(day, lang)}</div>'
            f'<table class="dtable cal-full">'
            f'<thead><tr><th>{"Time (CET)" if lang == "en" else "Saat (CET)"}</th>'
            f'<th>{"Event" if lang == "en" else "Veri"}</th>'
            f'<th>{"Country" if lang == "en" else "Ülke"}</th>'
            f'<th>{"Prev." if lang == "en" else "Önceki"}</th>'
            f'<th>{"Cons." if lang == "en" else "Beklenti"}</th>'
            f'<th>{"Actual" if lang == "en" else "Gerçekleşen"}</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')
    body = "\n".join(blocks) or \
        f'<p class="muted" style="text-align:center;padding:30px">{"No releases scheduled." if lang == "en" else "Planlı veri yok."}</p>'

    asof = CALENDAR.get("asof")
    stamp = _fmt_stamp(asof, lang) if asof else "—"
    stale = ""
    if asof and _is_stale(asof):
        stale = (f'<div class="callout" style="border-left-color:var(--red);margin-bottom:20px">'
                 f'<p style="font-family:var(--mono);font-size:12px;color:var(--red)">⚠ {CAL_STALE[lang]}</p></div>')
    summary = (f"{len(events)} releases this week · {high_n} high-impact ⭐"
               if lang == "en" else
               f"Bu hafta {len(events)} veri · {high_n} yüksek etkili ⭐")

    html = html.replace("<!--NCF:CAL_FULL-->", body)
    html = html.replace("<!--NCF:CAL_UPDATED-->", stamp)
    html = html.replace("<!--NCF:CAL_STALE-->", stale)
    html = html.replace("<!--NCF:CAL_SUMMARY-->", summary)
    return html


def inject_calendar(html, lang):
    if "<!--NCF:CALENDAR-->" not in html:
        return html
    events = CALENDAR.get("events", [])[:CAL_MAX_ROWS]
    rows = []
    for e in events:
        wd = WEEKDAYS[lang][e["wd"]] if 0 <= e.get("wd", -1) <= 6 else ""
        flag, ccy = COUNTRY.get(e.get("country", ""), ("🏳️", e.get("country", "")))
        name = e.get("event", "")
        if e.get("impact") == "high":
            ev = f'<span class="impact high"></span><strong>{name} ⭐</strong>'
        else:
            ev = f'<span class="impact med"></span>{name}'
        act = e.get("act", "—")
        act_cell = (f'<td class="mono cal-actual"><strong>{act}</strong></td>'
                    if act != "—" else '<td class="mono">—</td>')
        rows.append(
            f'<tr class="cal-row"><td class="mono">{wd}</td>'
            f'<td class="mono">{e.get("time", "")}</td><td>{ev}</td>'
            f'<td>{flag} {ccy}</td><td class="mono">{e.get("prev", "—")}</td>'
            f'<td class="mono">{e.get("est", "—")}</td>{act_cell}</tr>')
    body = "\n      ".join(rows) or \
        '<tr><td colspan="7" class="muted" style="text-align:center;padding:20px">—</td></tr>'

    asof = CALENDAR.get("asof")
    stamp = _fmt_stamp(asof, lang) if asof else "—"
    stale = ""
    if asof and _is_stale(asof):
        stale = (f'<div class="callout" style="border-left-color:var(--red);margin-bottom:16px">'
                 f'<p style="font-family:var(--mono);font-size:12px;color:var(--red)">⚠ {CAL_STALE[lang]}</p></div>')

    html = html.replace("<!--NCF:CALENDAR-->", body)
    html = html.replace("<!--NCF:CAL_UPDATED-->", stamp)
    html = html.replace("<!--NCF:CAL_STALE-->", stale)
    return html

# ── chrome fragments ─────────────────────────────────────────────────────────
def head(page, lang):
    p = PAGES[page]
    canonical = SITE_URL + p["paths"][lang]
    alt_en = SITE_URL + p["paths"]["en"]
    alt_tr = SITE_URL + p["paths"]["tr"]

    alts = [f'<link rel="alternate" hreflang="en" href="{alt_en}"/>']
    if _exists("tr", page):  # only advertise tr once it actually exists
        alts.append(f'<link rel="alternate" hreflang="tr" href="{alt_tr}"/>')
    alts.append(f'<link rel="alternate" hreflang="x-default" href="{alt_en}"/>')
    alt_html = "\n".join(alts)

    og_desc = p.get("og_desc", p["desc"])[lang]
    feed = "/feed-en.xml" if lang == "en" else "/feed-tr.xml"
    head_extra = _read(f"head/{page}.html")
    head_extra = (head_extra + "\n") if head_extra else ""
    if page == "hakkinda":
        site_schema = json.dumps({
            "@context": "https://schema.org", "@type": "Person", "name": "Orkun Biçen",
            "url": canonical, "jobTitle": "Macro analyst",
            "worksFor": {"@type": "Organization", "name": "NoCashFlow", "url": SITE_URL},
            "sameAs": ["https://twitter.com/No_CashFlow", "https://www.linkedin.com/in/orkunbicen/"],
        }, ensure_ascii=False)
    else:
        site_schema = json.dumps({
            "@context": "https://schema.org", "@type": "WebSite", "name": "NoCashFlow",
            "url": SITE_URL, "inLanguage": lang,
            "publisher": {"@type": "Organization", "name": "NoCashFlow", "url": SITE_URL},
        }, ensure_ascii=False)
    splash_css = '<link rel="stylesheet" href="/splash.css"/>\n' if (p.get("splash") and lang == "en") else ""
    early = _early_script(page, lang) if (p.get("splash") or lang == "tr") else ""
    # Broadsheet redesign — now applied site-wide
    bs_css = '<link rel="stylesheet" href="/broadsheet.css"/>\n'
    body_cls = ' class="bs"'

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{p["title"][lang]}</title>
<meta name="description" content="{p["desc"][lang]}"/>
<link rel="canonical" href="{canonical}"/>
{alt_html}
<meta property="og:title" content="{p["title"][lang]}"/>
<meta property="og:description" content="{og_desc}"/>
<meta property="og:type" content="website"/>
<meta property="og:url" content="{canonical}"/>
<meta property="og:image" content="{OG_IMAGE}"/>
<meta property="og:site_name" content="NoCashFlow"/>
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:image" content="{OG_IMAGE}"/>
<meta name="twitter:site" content="@No_CashFlow"/>
<link rel="icon" href="/favicon.svg?v=2" type="image/svg+xml"/>
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png?v=2"/>
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16.png?v=2"/>
<link rel="apple-touch-icon" href="/apple-touch-icon.png?v=2"/>
<link rel="shortcut icon" href="/favicon.ico?v=2"/>
<link rel="alternate" type="application/rss+xml" title="NoCashFlow" href="{feed}"/>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<meta name="theme-color" content="#ffffff"/>
{THEME_SCRIPT}
<link href="{FONTS_URL}" rel="stylesheet"/>
<link rel="stylesheet" href="/site.css"/>
<link rel="stylesheet" href="/components.css"/>
<script type="application/ld+json">{site_schema}</script>
{head_extra}{splash_css}{bs_css}{early}</head>
<body data-mood="{_mood()}"{body_cls}>"""


def _early_script(page, lang):
    if lang == "en":  # root splash page
        return (
            "<script>(function(){var d=document.documentElement;try{"
            "var q=new URLSearchParams(location.search).get('lang');"
            "if(q==='tr'||q==='en'){try{localStorage.setItem('ncf_lang',q);}catch(e){}"
            "if(q==='tr'){location.replace('/tr/');return;}return;}"
            "var p=null;try{p=localStorage.getItem('ncf_lang');}catch(e){}"
            "if(p==='tr'){location.replace('/tr/');return;}if(p==='en'){return;}"
            "d.setAttribute('data-ncf-splash','on');}"
            "catch(e){d.setAttribute('data-ncf-splash','on');}})();</script>\n"
        )
    return (
        "<script>(function(){try{"
        "var q=new URLSearchParams(location.search).get('lang');"
        "if(q==='en'){try{localStorage.setItem('ncf_lang','en');}catch(e){}location.replace('/');return;}"
        "if(q==='tr'){try{localStorage.setItem('ncf_lang','tr');}catch(e){}return;}"
        "var p=null;try{p=localStorage.getItem('ncf_lang');}catch(e){}"
        "if(p==='en'){location.replace('/');return;}}catch(e){}})();</script>\n"
    )


def splash_overlay():
    return """<!-- LANGUAGE GATE (hidden unless the head script reveals it) -->
<div id="ncf-splash" role="dialog" aria-label="Language / Dil">
  <a href="?lang=en" class="ncf-splash-skip">Skip &rarr;</a>
  <div class="ncf-splash-word" dir="ltr">Hoş geldiniz</div>
  <div class="ncf-splash-choices">
    <button type="button" class="ncf-splash-btn" data-lang="tr">Türkçe</button>
    <button type="button" class="ncf-splash-btn" data-lang="en">English</button>
  </div>
</div>
"""


CURSOR_HTML = ('<div class="cursor-ring"><span class="c-label">Read</span></div>\n'
               '<div class="cursor-dot"></div>\n\n')

MONTHS_LONG = {"en": ["January", "February", "March", "April", "May", "June", "July",
                      "August", "September", "October", "November", "December"],
               "tr": ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
                      "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]}
WEEKDAYS_LONG = {"en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                 "tr": ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]}


def masthead(page, lang):
    """Broadsheet nameplate on the home page; thin dateline elsewhere.
    Re-typeset on every build (the dateline is the live build date)."""
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("Europe/Madrid"))
    except Exception:
        now = datetime.now()
    wd = WEEKDAYS_LONG[lang][now.weekday()]
    mo = MONTHS_LONG[lang][now.month - 1]
    if lang == "en":
        datestr = f"{wd}, {mo} {now.day}, {now.year}"
        edition = "Morning Edition"
        kicker = "Macro &amp; Markets, every morning"
        tagline = "Make sense of the macro. Start your morning with data."
    else:
        datestr = f"{wd}, {now.day} {mo} {now.year}"
        edition = "Sabah Baskısı"
        kicker = "Makro &amp; Piyasalar, her sabah"
        tagline = "Makroyu anlamlandır. Gününe veriyle başla."
    home = "/" if lang == "en" else "/tr/"
    if page == "index":
        return (f'\n<div class="bs-mast">'
                f'<div class="bs-mast-top"><span>{edition}</span>'
                f'<span class="bs-mast-mid">{kicker}</span>'
                f'<span>Barcelona · {datestr}</span></div>'
                f'<a class="bs-wordmark" href="{home}">NoCashFlow</a>'
                f'<div class="bs-mast-tag">{tagline}</div>'
                f'</div>\n')
    return (f'\n<div class="masthead"><div class="masthead-inner">'
            f'<span>{edition}</span><span class="mh-date">{datestr}</span>'
            f'<span>Barcelona</span></div></div>\n')


# Global ticker — dark bar, mounted directly under the header (demo position).
# Data source unchanged: app.js fills #ticker-track from the existing feed.
TICKER_HTML = ('<!-- TICKER -->\n<div class="ticker">\n'
               '  <div class="ticker-label"><span class="dot"></span> Live</div>\n'
               '  <div class="ticker-track" id="ticker-track"></div>\n</div>\n')


def chrome_top(page=None):
    return CURSOR_HTML + '<div id="page-sweep"></div>\n'


def _nav_html(active_key, lang, sw_href):
    home_href = "/" if lang == "en" else "/tr/"
    links = []
    for key, en_l, tr_l, en_h, tr_h in NAV:
        label = en_l if lang == "en" else tr_l
        href = en_h if lang == "en" else tr_h
        cls = ' class="active"' if key == active_key else ""
        links.append(f'      <a href="{href}"{cls}>{label}</a>')
    links_html = "\n".join(links)
    sub_label, sub_href = SUBSCRIBE[lang]
    if lang == "en":
        sw_label, sw_set, sw_aria = "TR", "tr", "Türkçe'ye geç"
    else:
        sw_label, sw_set, sw_aria = "EN", "en", "Switch to English"
    return f"""
<!-- NAV -->
<nav class="nav">
  <div class="nav-inner">
    <a href="{home_href}" class="logo">NO<span class="slash">/</span>CASHFLOW<span class="tag">MACRO × MARKETS</span></a>
    <div class="nav-links" id="nav-links">
{links_html}
    </div>
    <div class="nav-right">
      <a class="lang-switch" href="{sw_href}" data-set-lang="{sw_set}" aria-label="{sw_aria}">{sw_label}</a>
      <button class="nav-btn theme-toggle" data-theme-toggle aria-label="After Hours" title="After Hours">◐</button>
      <a href="{sub_href}" class="subscribe">{sub_label}</a>
      <button class="menu-toggle" id="menu-toggle" aria-label="Open menu"><span></span></button>
    </div>
  </div>
</nav>
"""


def nav(page, lang):
    p = PAGES[page]
    sw_href = p["paths"]["tr"] if lang == "en" else p["paths"]["en"]
    return _nav_html(p["nav_key"], lang, sw_href)


def footer(lang):
    f = FOOTER[lang]
    fl = lambda en_h, tr_h: _flink(lang, en_h, tr_h)
    return f"""
<!-- FOOTER -->
<footer>
  <div class="footer-inner">
    <div class="footer-top">
      <div>
        <div class="footer-brand-title">NO<span style="color:var(--amber)">/</span>CASHFLOW</div>
        <p class="footer-brand-desc">{f['brand_desc']}</p>
      </div>
      <div class="footer-col">
        <h4>{f['col_pages']}</h4>
        <ul>
          <li><a href="{fl('/', '/tr/')}">{f['l_home']}</a></li>
          <li><a href="{fl('/yazilar.html', '/tr/yazilar.html')}">{f['l_articles']}</a></li>
          <li><a href="{fl('/macro.html', '/tr/macro.html')}">{f['l_macro']}</a></li>
          <li><a href="{fl('/now/', '/tr/simdi/')}">{f['l_indicators']}</a></li>
          <li><a href="{fl('/calendar.html', '/tr/takvim.html')}">{f['l_calendar']}</a></li>
          <li><a href="{fl('/dashboard.html', '/tr/dashboard.html')}">{f['l_dashboard']}</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h4>{f['col_content']}</h4>
        <ul>
          <li><a href="{fl('/bulletin_page.html', '/tr/bulletin_page.html')}">{f['l_bulletin']}</a></li>
          <li><a href="{fl('/archive.html', '/tr/arsiv.html')}">{f['l_archive']}</a></li>
          <li><a href="{fl('/embed.html', '/tr/embed.html')}">{f['l_widget']}</a></li>
          <li><a href="{fl('/hakkinda.html', '/tr/hakkinda.html')}">{f['l_about']}</a></li>
          <li><a href="{fl('/sozluk.html', '/tr/sozluk.html')}">{f['l_glossary']}</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h4>{f['col_social']}</h4>
        <ul>
          <li><a href="https://twitter.com/No_CashFlow" target="_blank" rel="noopener">Twitter / X</a></li>
          <li><a href="https://www.linkedin.com/in/orkunbicen/" target="_blank" rel="noopener">LinkedIn</a></li>
          <li><a href="{fl('/feed-en.xml', '/feed-tr.xml')}">{f['l_rss']}</a></li>
          <li><a href="mailto:orkun@nocashflow.net">{f['l_email']}</a></li>
        </ul>
      </div>
    </div>
    <div class="footer-bot">
      <span>© <span data-year>2026</span> NoCashFlow.net · Barcelona</span>
      <span><a href="{fl('/hakkinda.html', '/tr/hakkinda.html')}">{f['bottom_about']}</a> · <a href="{fl('/bulletin_page.html', '/tr/bulletin_page.html')}">{f['bottom_subscribe']}</a></span>
    </div>
    {_mood_line(lang)}
    <div class="disclaimer">
      {f['disclaimer']}<br/>
      <a href="{fl('/privacy.html', '/tr/privacy.html')}">{f['l_privacy']}</a> · <a href="{fl('/legal.html', '/tr/legal.html')}">{f['l_legal']}</a> · <a href="{fl('/disclaimer.html', '/tr/disclaimer.html')}">{f['l_disclaimer']}</a>
    </div>
  </div>
</footer>
"""


def scripts(page, lang):
    p = PAGES[page]
    out = ['<script src="/app.js"></script>']
    foot = _read(f"foot/{page}.html")          # page-specific NCF.init + JS (verbatim)
    if foot:
        out.append(foot)
    else:                                       # default ticker init (e.g. legal pages)
        out.append("<script>window.NCF.init({ ticker: ['btc','eth','gold','brent','dxy','us10y','vix','spx'] });</script>")
    out.append(
        "<script>document.querySelectorAll('[data-set-lang]').forEach(function(a){"
        "a.addEventListener('click',function(){try{localStorage.setItem('ncf_lang',"
        "a.getAttribute('data-set-lang'));}catch(e){}});});</script>"
    )
    if p.get("splash") and lang == "en":       # splash lives only on the en root
        out.append('<script src="/splash.js"></script>')
    return "\n".join(out)


# ── assembly ─────────────────────────────────────────────────────────────────
def inject_article_list(html, lang):
    """Replace the placeholder in yazilar with teaser cards generated from the
    ARTICLES registry, each linking to its own article page."""
    if "<!--NCF:ARTICLE_LIST-->" not in html:
        return html
    rows = []
    for slug in ARTICLE_ORDER:
        a = ARTICLES[slug]
        rows.append(
            '    <div class="art-row">\n'
            f'      <div class="n">{a["num"]}</div>\n'
            '      <div class="body">\n'
            f'        <div class="tag-line">{a["cat"][lang]} · {a["date_disp"][lang]} · {a["read"][lang]}</div>\n'
            f'        <h3><a href="{article_path(slug, lang)}">{a["title"][lang]}</a></h3>\n'
            f'        <p>{a["dek"][lang]}</p>\n'
            '      </div>\n'
            '      <div class="arrow">→</div>\n'
            '    </div>')
    list_html = '<div class="art-list">\n' + "\n".join(rows) + "\n  </div>"
    return html.replace("<!--NCF:ARTICLE_LIST-->", list_html)


# ── dashboard "the tape" (data/markets.json → build-time render) ─────────────
DASH_HERO_LABELS = {
    "en": ["Bitcoin", "Ethereum", "S&amp;P 500", "Gold", "Crypto F&amp;G", "BTC Dominance"],
    "tr": ["Bitcoin", "Ethereum", "S&amp;P 500", "Altın", "Kripto K&amp;A", "BTC Hakimiyeti"],
}


def _fmt_price(v):
    if v is None:
        return "—"
    if v >= 1000:
        return f"{v:,.0f}"
    if v >= 100:
        return f"{v:,.1f}"
    if v >= 1:
        return f"{v:.2f}"
    return f"{v:.3f}"


def _signed_pct(v, dp=2):
    sign = "+" if v > 0 else ("−" if v < 0 else "")
    return f"{sign}{abs(v):.{dp}f}%"


def _ud(v):
    return "up" if v >= 0 else "down"


def _pp(v):
    return ("+" if v >= 0 else "−") + f"{abs(v):.1f}pp"


def _pc_cell(v):
    """Perf table cell: sign, ≥100% no-decimal formatting, and direction tint."""
    if v is None:
        return '<td class="pc">—</td>'
    av = abs(v)
    txt = f"{round(av):,}" if av >= 100 else f"{av:.1f}"
    sign = "+" if v > 0 else ("−" if v < 0 else "")
    label = f"{sign}{txt}%"
    if v == 0:
        return f'<td class="pc" style="color:var(--text-mute)">{label}</td>'
    pos = v > 0
    a = min(0.24, 0.045 + av * 0.017)
    rgb = "26,127,60" if pos else "179,18,43"
    color = "var(--green)" if pos else "var(--red)"
    return f'<td class="pc" style="color:{color};background:rgba({rgb},{a:.3f})">{label}</td>'


def _spark_svg(closes, up):
    if not closes:
        return ""
    lo, hi = min(closes), max(closes)
    rng = (hi - lo) or 1.0
    n = len(closes)
    W, H, pad = 264, 44, 4
    pts = " ".join(
        f"{round(i * W / (n - 1), 1)},{round(H - pad - (c - lo) / rng * (H - 2 * pad), 1)}"
        for i, c in enumerate(closes))
    stroke = "var(--green)" if up else "var(--red)"
    return (f'<svg class="dsh-spark" viewBox="0 0 {W} {H}"><polyline fill="none" '
            f'stroke="{stroke}" stroke-width="1.4" points="{pts}"/></svg>')


def _heat_color(d1):
    m = max(-1.6, min(1.6, d1)) / 1.6
    base = (116, 120, 127)
    end = (26, 127, 60) if m >= 0 else (179, 18, 43)
    t = abs(m)
    r, g, b = (int(base[i] + (end[i] - base[i]) * t) for i in range(3))
    return f"#{r:02X}{g:02X}{b:02X}"


def _dash_tile(it):
    chg = it["d1"]
    return (f'<div class="dsh-tile"><div class="sym">{it["sym"]}</div>'
            f'<div class="name">{it["name"]}</div>'
            f'<div class="px">{_fmt_price(it["price"])}</div>'
            f'<div class="chg {_ud(chg)}">{_signed_pct(chg)}</div>'
            f'{_spark_svg(it.get("spark30"), chg >= 0)}</div>')


def _dash_leader_row(a):
    p = a["perf"]
    cells = "".join(_pc_cell(p.get(k)) for k in ("d1", "d7", "d30", "d180", "y1", "y5"))
    return (f'<tr><td class="nm">{a["sym"]} <span class="full">{a["name"]}</span></td>'
            f'<td class="num">{_fmt_price(a["price"])}</td>{cells}'
            f'<td class="num">{a["mcap"]}</td></tr>')


def _dash_perf_row(a, horizons):
    cells = "".join(_pc_cell(a["perf"].get(k)) for k in horizons)
    return (f'<tr><td class="nm">{a["name"]}</td>'
            f'<td class="num">{_fmt_price(a["price"])}</td>{cells}</tr>')


def inject_dashboard(html, lang):
    if "<!--NCF:DASH_HERO-->" not in html:
        return html
    m = MARKETS or {}
    html = html.replace("<!--NCF:DASH_UPD-->",
                        _fmt_stamp(m.get("updated", ""), lang) if m.get("updated") else "—")

    def hcell(label, v, d, cls):
        return (f'<div class="dsh-hcell"><div class="k">{label}</div>'
                f'<div class="v">{v}</div><div class="d {cls}">{d}</div></div>')

    h = m.get("hero", {})
    L = DASH_HERO_LABELS[lang]
    btc, eth, spx, gold = h.get("btc", {}), h.get("eth", {}), h.get("spx", {}), h.get("gold", {})
    fng, dom = h.get("fng", {}), h.get("btc_dom", {})
    fv = fng.get("v")
    fcls = "up" if (fv or 0) > 55 else ("down" if (fv or 0) < 35 else "neu")
    hero = "".join([
        hcell(L[0], f"${_fmt_price(btc.get('px'))}", _signed_pct(btc.get('chg', 0)), _ud(btc.get('chg', 0))),
        hcell(L[1], f"${_fmt_price(eth.get('px'))}", _signed_pct(eth.get('chg', 0)), _ud(eth.get('chg', 0))),
        hcell(L[2], _fmt_price(spx.get('px')), _signed_pct(spx.get('chg', 0)), _ud(spx.get('chg', 0))),
        hcell(L[3], f"${_fmt_price(gold.get('px'))}", _signed_pct(gold.get('chg', 0)), _ud(gold.get('chg', 0))),
        hcell(L[4], fv if fv is not None else "—", fng.get("label", "—"), fcls),
        hcell(L[5], f"{dom.get('v', '—')}%", _pp(dom.get('chg_pp', 0)), _ud(dom.get('chg_pp', 0))),
    ])
    html = html.replace("<!--NCF:DASH_HERO-->", hero)

    html = html.replace("<!--NCF:DASH_INDICES-->", "".join(_dash_tile(x) for x in m.get("indices", [])))
    html = html.replace("<!--NCF:DASH_THEMATICS-->", "".join(_dash_tile(x) for x in m.get("thematics", [])))

    html = html.replace("<!--NCF:DASH_FRONTIER-->", "".join(
        f'<span class="dsh-chip"><b>{f["sym"]}</b>'
        f'<span class="x {_ud(f["d1"])}">{_signed_pct(f["d1"], 1)}</span></span>'
        for f in m.get("frontier", [])))

    html = html.replace("<!--NCF:DASH_HEAT-->", "".join(
        f'<div class="dsh-hc" style="background:{_heat_color(s["d1"])}">'
        f'<div><div class="s">{s["sym"]}</div><div class="n">{s["name"]}</div></div>'
        f'<div class="p">{_signed_pct(s["d1"], 1)}</div></div>'
        for s in m.get("sectors", [])))

    cb = m.get("crypto_board", {})
    en = lang == "en"

    def btile(sym, name, val, chg_txt, cls):
        return (f'<div class="dsh-tile"><div class="sym">{sym}</div><div class="name">{name}</div>'
                f'<div class="px">{val}</div><div class="chg {cls}">{chg_txt}</div></div>')

    tot, bd, st, uc, fu = (cb.get("total_mcap", {}), cb.get("btc_dom", {}),
                           cb.get("stables", {}), cb.get("usdc_share", {}), cb.get("funding", {}))
    board = "".join([
        btile("TOTAL", "Market cap" if en else "Piyasa değeri", f"${tot.get('v', '—')}",
              _signed_pct(tot.get('chg', 0), 1), _ud(tot.get('chg', 0))),
        btile("BTC.D", "BTC dominance" if en else "BTC hakimiyeti", f"{bd.get('v', '—')}%",
              _pp(bd.get('chg_pp', 0)), _ud(bd.get('chg_pp', 0))),
        btile("STABLES", "Stablecoin supply" if en else "Stablecoin arzı", f"${st.get('v', '—')}",
              _signed_pct(st.get('chg', 0), 1), _ud(st.get('chg', 0))),
        btile("USDC.D", "USDC share" if en else "USDC payı", f"{uc.get('v', '—')}%",
              _pp(uc.get('chg_pp', 0)), _ud(uc.get('chg_pp', 0))),
        btile("FUND", "BTC funding", f"{'+' if fu.get('v', 0) >= 0 else ''}{fu.get('v', '—')}%",
              "neutral" if en else "nötr", "neu"),
    ])
    html = html.replace("<!--NCF:DASH_CRYPTO-->", board)

    html = html.replace("<!--NCF:DASH_LEADERS_EQ-->", "".join(_dash_leader_row(a) for a in m.get("leaders_equity", [])))
    html = html.replace("<!--NCF:DASH_LEADERS_CRYPTO-->", "".join(_dash_leader_row(a) for a in m.get("leaders_crypto", [])))
    html = html.replace("<!--NCF:DASH_COMMODITIES-->", "".join(_dash_perf_row(a, ("d1", "d7", "d30", "y1")) for a in m.get("commodities", [])))
    fx_rows = "".join(_dash_perf_row(a, ("d1", "d7", "d30", "y1")) for a in m.get("fx", []))
    html = html.replace("<!--NCF:DASH_FX-->", fx_rows or
                        '<tr><td colspan="6" class="num" style="color:var(--text-mute);'
                        'text-align:center;padding:18px">—</td></tr>')

    # editorial "read" notes — human-committed markets-notes.json (empty in Phase 1)
    for key in ("indices", "sectors", "crypto", "leaders"):
        html = html.replace(f"<!--NCF:DASH_NOTE_{key}-->", "")
    return html


# ── macro "the regime" (data/macro2.json + human macro-notes.json) ───────────
MACRO2_LABELS = {
    "inflation": {"en": ["Headline CPI · YoY", "Core CPI · YoY", "Core PCE · YoY", "5y5y Breakeven"],
                  "tr": ["Manşet TÜFE · YY", "Çekirdek TÜFE · YY", "Çekirdek PCE · YY", "5y5y Başabaş"]},
    "fed": {"en": ["Target range", "Balance sheet", "Reverse repo", "Dot plot '26"],
            "tr": ["Hedef aralık", "Bilanço", "Ters repo", "Nokta grafik '26"]},
    "liquidity": {"en": ["M2 supply", "Net liquidity", "Stablecoin supply"],
                  "tr": ["M2 arzı", "Net likidite", "Stablecoin arzı"]},
    "growth": {"en": ["Empire State Mfg", "Nonfarm payrolls", "Jobless claims", "GDPNow · Q2"],
               "tr": ["Empire State İmalat", "Tarım dışı istihdam", "İşsizlik başvuruları", "GDPNow · Ç2"]},
    "rates": {"en": ["US 2Y", "US 10Y", "2s10s spread", "HY spread"],
              "tr": ["ABD 2Y", "ABD 10Y", "2s10s farkı", "HY farkı"]},
}


def _mstat(label, s, note=""):
    sub = s.get("sub", "")
    sub_html = f'<div class="sub {s.get("dir", "neu")}">{sub}</div>' if sub else ""
    note_html = f'<div class="note">{note}</div>' if note else ""
    return (f'<div class="mcr-stat"><div class="lab">{label}</div>'
            f'<div class="big">{s.get("v", "—")}</div>{sub_html}{note_html}</div>')


def _mstats(section, lang):
    labels = MACRO2_LABELS[section][lang]
    stats = MACRO2.get(section) if section in ("inflation", "growth") else MACRO2.get(section, {}).get("stats", [])
    notes = (MACRO_NOTES.get("stat_notes", {}) or {}).get(section, [])
    out = []
    for i, s in enumerate(stats):
        note = notes[i] if i < len(notes) else ""
        out.append(_mstat(labels[i] if i < len(labels) else "", s, note))
    return "".join(out)


def _mread(key):
    note = (MACRO_NOTES.get("notes", {}) or {}).get(key, {}) or {}
    body = note.get("body", "")
    if not body:
        return ""
    by = note.get("by", "")
    by_html = f'<div class="by">{by}</div>' if by else ""
    return (f'<div class="mcr-read"><div class="tag">{note.get("tag", "The read")}</div>'
            f'<p>{body}</p>{by_html}</div>')


def _curve_svg(curve):
    if not curve:
        return ""
    ys = [c["y"] for c in curve]
    lo, hi = min(ys) - 0.3, max(ys) + 0.3
    n = len(curve)
    xs = [70, 134, 198, 304, 370, 440, 524] if n == 7 else \
         [round(44 + i * 504 / (n - 1)) for i in range(n)]

    def yy(v):
        return round(24 + (hi - v) / (hi - lo) * 164, 1)

    pts = " ".join(f"{xs[i]},{yy(c['y'])}" for i, c in enumerate(curve))
    circles = "".join(f'<circle cx="{xs[i]}" cy="{yy(c["y"])}" r="3"/>' for i, c in enumerate(curve))
    tlabels = "".join(f'<text x="{xs[i]}" y="204">{c["tenor"]}</text>' for i, c in enumerate(curve))
    g1, g2, g3 = hi, (hi + lo) / 2, lo
    return (f'<svg viewBox="0 0 560 230" role="img" aria-label="US Treasury yield curve">'
            f'<line x1="44" y1="24" x2="44" y2="188" stroke="var(--border)"/>'
            f'<line x1="44" y1="188" x2="548" y2="188" stroke="var(--border)"/>'
            f'<g class="mono" font-size="10" fill="var(--text-mute)">'
            f'<text x="8" y="{yy(g1)+4}">{g1:.1f}</text><text x="8" y="{yy(g2)+4}">{g2:.1f}</text>'
            f'<text x="8" y="{yy(g3)+4}">{g3:.1f}</text></g>'
            f'<polyline fill="none" stroke="var(--amber)" stroke-width="2.5" points="{pts}"/>'
            f'<g fill="var(--amber)">{circles}</g>'
            f'<g class="mono" font-size="9.5" fill="var(--text-mute)" text-anchor="middle">{tlabels}</g>'
            f'</svg>')


def _liq_svg(series, ymin, ymax):
    if not series:
        return ""
    n = len(series)
    ymin = ymin if ymin is not None else min(series)
    ymax = ymax if ymax is not None else max(series)
    rng = (ymax - ymin) or 1.0

    def yy(v):
        return round(186 - (v - ymin) / rng * 166, 1)

    xs = [round(44 + i * 504 / (n - 1)) for i in range(n)]
    pts = " ".join(f"{xs[i]},{yy(v)}" for i, v in enumerate(series))
    lx, ly = xs[-1], yy(series[-1])
    g1, g2, g3 = ymax, (ymax + ymin) / 2, ymin
    return (f'<svg viewBox="0 0 560 220" role="img" aria-label="Net liquidity">'
            f'<line x1="44" y1="20" x2="44" y2="186" stroke="var(--border)"/>'
            f'<line x1="44" y1="186" x2="548" y2="186" stroke="var(--border)"/>'
            f'<g class="mono" font-size="10" fill="var(--text-mute)">'
            f'<text x="8" y="{yy(g1)+4}">{g1:.1f}</text><text x="8" y="{yy(g2)+4}">{g2:.1f}</text>'
            f'<text x="8" y="{yy(g3)+4}">{g3:.1f}</text></g>'
            f'<polyline fill="none" stroke="var(--amber)" stroke-width="2.5" points="{pts}"/>'
            f'<circle cx="{lx}" cy="{ly}" r="3.5" fill="var(--amber)"/></svg>')


def inject_macro2(html, lang):
    if "<!--NCF:MACRO2_TAPE-->" not in html:
        return html
    M = MACRO2 or {}

    rr = (MACRO_NOTES.get("regime_read", "") or "")
    regime = (f'<div class="mcr-regime">{"Current read:" if lang == "en" else "Mevcut okuma:"} '
              f'<b>{rr}</b></div>') if rr else ""
    html = html.replace("<!--NCF:MACRO2_REGIME-->", regime)

    html = html.replace("<!--NCF:MACRO2_TAPE-->", "".join(
        f'<div class="mcr-tcell"><div class="k">{c["k"]}</div><div class="v">{c["v"]}</div>'
        f'<div class="d {c.get("dir", "neu")}">{c.get("d", "")}</div></div>'
        for c in M.get("regime_tape", [])))

    html = html.replace("<!--NCF:MACRO2_INFLATION-->", _mstats("inflation", lang))
    html = html.replace("<!--NCF:MACRO2_FED_STATS-->", _mstats("fed", lang))
    html = html.replace("<!--NCF:MACRO2_LIQ_STATS-->", _mstats("liquidity", lang))
    html = html.replace("<!--NCF:MACRO2_GROWTH-->", _mstats("growth", lang))
    html = html.replace("<!--NCF:MACRO2_RATES_STATS-->", _mstats("rates", lang))

    odds_rows = "".join(
        f'<div class="row"><span class="lbl">{o["m"]}</span>'
        f'<span class="track"><span class="fill" style="width:{o["p"]}%"></span></span>'
        f'<span class="pct">{o["p"]}%</span></div>'
        for o in M.get("fed", {}).get("cut_odds", []))
    html = html.replace("<!--NCF:MACRO2_FED_ODDS-->", odds_rows or
                        '<p class="cap" style="margin:10px 0 0">Awaiting a live source.</p>')

    liq = M.get("liquidity", {})
    html = html.replace("<!--NCF:MACRO2_LIQ_CHART-->", _liq_svg(liq.get("net_liq_series"), liq.get("y_min"), liq.get("y_max")))
    html = html.replace("<!--NCF:MACRO2_RATES_CHART-->", _curve_svg(M.get("rates", {}).get("curve")))

    for key in ("inflation", "fed", "liquidity", "growth", "rates", "calendar"):
        html = html.replace(f"<!--NCF:MACRO2_READ_{key}-->", _mread(key))

    wr = (MACRO_NOTES.get("weekly_read", "") or "")
    closing = (f'<div class="mcr-closing"><div class="page-eyebrow">'
               f'{"The week’s read" if lang == "en" else "Haftanın okuması"}</div>'
               f'<p>{wr}</p><div class="sign">NoCashFlow · Macro desk · Barcelona</div></div>') if wr else ""
    html = html.replace("<!--NCF:MACRO2_CLOSING-->", closing)
    return html


def render(page, lang):
    p = PAGES[page]
    body = _read(f"{lang}/{page}.html")
    splash_html = splash_overlay() if (p.get("splash") and lang == "en") else ""
    html = "\n".join([
        head(page, lang),
        splash_html + chrome_top(page),
        nav(page, lang),
        TICKER_HTML,
        masthead(page, lang),
        body,
        footer(lang),
        scripts(page, lang),
        "</body>",
        "</html>",
        "",
    ])
    # fill build-time snapshots (market values + macro KPIs + economic calendar)
    html = html.replace("<!--NCF:HERO-->", hero_frieze(lang))
    html = html.replace("<!--NCF:MOOD-->", _mood_pill(lang))
    html = html.replace("<!--NCF:PULSECHART-->", pulse_chart(lang))
    html = inject_calendar(html, lang)
    html = inject_calendar_full(html, lang)
    html = inject_cal_brief(html, lang)
    html = inject_snapshot_note(html, lang)
    html = inject_archive(html, lang)
    html = inject_macro(html, lang)
    html = inject_macro2(html, lang)
    html = inject_article_list(html, lang)
    html = inject_dashboard(html, lang)
    html = inject_market(html)
    return html


# ── articles (own pages: /articles/<slug>.html en, /tr/yazilar/<slug>.html tr) ─
OG_IMAGE = SITE_URL + "/og.png"

ARTICLES = {
    "warsh": {
        "num": "#07", "date": "2026-06-22",
        "cat": {"en": "Macro", "tr": "Makro"},
        "date_disp": {"en": "Jun 22, 2026", "tr": "22 Haz 2026"},
        "read": {"en": "8 min read", "tr": "8 dk okuma"},
        "title": {"en": "Powell Left. The Dots Went Up.",
                  "tr": "Powell Gitti. Noktalar Yükseldi."},
        "dek": {"en": "The June meeting wasn't about the hold. A new chair, a shorter statement, and a dot plot that quietly priced out this year's cuts.",
                "tr": "Haziran toplantısı faizin sabit tutulmasıyla ilgili değildi. Yeni bir başkan, daha kısa bir metin ve bu yılın indirimlerini sessizce fiyatlardan çıkaran bir dot plot."},
    },
    "hormuz": {
        "num": "#06", "date": "2026-06-21",
        "cat": {"en": "Commodities", "tr": "Emtia"},
        "date_disp": {"en": "Jun 21, 2026", "tr": "21 Haz 2026"},
        "read": {"en": "9 min read", "tr": "9 dk okuma"},
        "title": {"en": "Closed, and Still Flowing",
                  "tr": "Kapalı, Ama Hâlâ Akıyor"},
        "dek": {"en": "In March we argued the 1970s oil analogy was misleading. Three months on, Iran calls the Strait of Hormuz closed again — and the crude is still moving. Time for the scorecard.",
                "tr": "Mart'ta 1970'ler petrol analojisinin yanıltıcı olduğunu savunmuştuk. Üç ay sonra İran Hürmüz Boğazı'nı yine kapalı ilan ediyor — ve ham petrol hâlâ akıyor. Karne zamanı."},
    },
    "circle": {
        "num": "#05", "date": "2026-06-18",
        "cat": {"en": "Crypto", "tr": "Kripto"},
        "date_disp": {"en": "Jun 18, 2026", "tr": "18 Haz 2026"},
        "read": {"en": "7 min read", "tr": "7 dk okuma"},
        "title": {"en": "Circle Keeps Half. Coinbase Takes the Rest.",
                  "tr": "Circle Yarısını Tutuyor. Gerisini Coinbase Alıyor."},
        "dek": {"en": "USDC is a $77B business. Circle only keeps the half its distributors let it. The most important number at Circle isn't circulation — it's the split.",
                "tr": "USDC 77 milyar dolarlık bir iş. Circle yalnızca dağıtımcılarının bıraktığı yarıyı elinde tutuyor. Circle'da en önemli rakam dolaşım değil — paylaşım."},
    },
    "smart-money": {
        "num": "#04", "date": "2026-04-06",
        "cat": {"en": "Smart Money", "tr": "Smart Money"},
        "date_disp": {"en": "Apr 6, 2026", "tr": "6 Nis 2026"},
        "read": {"en": "9 min read", "tr": "9 dk okuma"},
        "title": {"en": "What Is Smart Money, and Where Is It Going?",
                  "tr": "Smart Money Nedir ve Nereye Gidiyor?"},
        "dek": {"en": "JPMorgan said institutions would dominate 2026 crypto flows. Q1 came in at one-third of the estimate.",
                "tr": "JPMorgan kurumların 2026 kripto akışlarını domine edeceğini söyledi. Q1 tahminin üçte biri geldi."},
    },
    "nukleer": {
        "num": "#03", "date": "2026-03-30",
        "cat": {"en": "Energy", "tr": "Enerji"},
        "date_disp": {"en": "Mar 30, 2026", "tr": "30 Mar 2026"},
        "read": {"en": "6 min read", "tr": "6 dk okuma"},
        "title": {"en": "AI Needs Electricity — The Answer Is Nuclear",
                  "tr": "Yapay Zekânın Elektriğe İhtiyacı Var — Cevap Nükleer"},
        "dek": {"en": "Data centers will consume 945 TWh by 2030 — equal to Japan's entire annual electricity use.",
                "tr": "Veri merkezleri 2030'a kadar 945 TWh tüketecek — Japonya'nın tüm yıllık elektrik kullanımına eşit."},
    },
    "bakir": {
        "num": "#02", "date": "2026-03-23",
        "cat": {"en": "Commodities", "tr": "Emtia"},
        "date_disp": {"en": "Mar 23, 2026", "tr": "23 Mar 2026"},
        "read": {"en": "6 min read", "tr": "6 dk okuma"},
        "title": {"en": "Dr. Copper — Wrong Diagnosis?", "tr": "Dr. Bakır — Yanlış Teşhis mi?"},
        "dek": {"en": "Copper as a recession indicator is broken — AI data centers, EVs and renewables all demand it at once.",
                "tr": "Resesyon göstergesi olarak bakır bozuldu — yapay zekâ, elektrikli araçlar ve yenilenebilir enerji onu aynı anda talep ediyor."},
    },
    "petrol": {
        "num": "#01", "date": "2026-03-16",
        "cat": {"en": "Macro", "tr": "Makro"},
        "date_disp": {"en": "Mar 16, 2026", "tr": "16 Mar 2026"},
        "read": {"en": "7 min read", "tr": "7 dk okuma"},
        "title": {"en": "Why the 1970s Comparison Is Misleading", "tr": "1970'ler Karşılaştırması Neden Yanıltıcı"},
        "dek": {"en": "Brent up 40%, Hormuz closed — but oil intensity has more than halved since 1973.",
                "tr": "Brent %40 yukarıda, Hürmüz kapalı — ama petrol yoğunluğu 1973'ten beri yarıdan fazla düştü."},
    },
}
ARTICLE_ORDER = ["warsh", "hormuz", "circle", "smart-money", "nukleer", "bakir", "petrol"]  # newest first


def article_path(slug, lang):
    return f"/articles/{slug}.html" if lang == "en" else f"/tr/yazilar/{slug}.html"


def article_out(slug, lang):
    return f"articles/{slug}.html" if lang == "en" else f"tr/yazilar/{slug}.html"


def render_article(slug, lang):
    a = ARTICLES[slug]
    title, dek = a["title"][lang], a["dek"][lang]
    canonical = SITE_URL + article_path(slug, lang)
    alt_en, alt_tr = SITE_URL + article_path(slug, "en"), SITE_URL + article_path(slug, "tr")
    prose = _read(f"articles/{slug}/{lang}.html")
    feed = "/feed-en.xml" if lang == "en" else "/feed-tr.xml"
    yazilar_url = "/yazilar.html" if lang == "en" else "/tr/yazilar.html"
    back = "← All articles" if lang == "en" else "← Tüm yazılar"
    sw_href = article_path(slug, "tr") if lang == "en" else article_path(slug, "en")

    schema = json.dumps({
        "@context": "https://schema.org", "@type": "Article",
        "headline": title, "description": dek, "datePublished": a["date"], "inLanguage": lang,
        "author": {"@type": "Person", "name": "Orkun Biçen"},
        "publisher": {"@type": "Organization", "name": "NoCashFlow", "url": SITE_URL},
        "mainEntityOfPage": canonical, "image": OG_IMAGE,
    }, ensure_ascii=False)

    head_html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{title} — NoCashFlow</title>
<meta name="description" content="{dek}"/>
<link rel="canonical" href="{canonical}"/>
<link rel="alternate" hreflang="en" href="{alt_en}"/>
<link rel="alternate" hreflang="tr" href="{alt_tr}"/>
<link rel="alternate" hreflang="x-default" href="{alt_en}"/>
<meta property="og:title" content="{title}"/>
<meta property="og:description" content="{dek}"/>
<meta property="og:type" content="article"/>
<meta property="og:url" content="{canonical}"/>
<meta property="og:image" content="{OG_IMAGE}"/>
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:image" content="{OG_IMAGE}"/>
<link rel="icon" href="/favicon.svg?v=2" type="image/svg+xml"/>
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png?v=2"/>
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16.png?v=2"/>
<link rel="apple-touch-icon" href="/apple-touch-icon.png?v=2"/>
<link rel="shortcut icon" href="/favicon.ico?v=2"/>
<link rel="alternate" type="application/rss+xml" title="NoCashFlow" href="{feed}"/>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<meta name="theme-color" content="#ffffff"/>
{THEME_SCRIPT}
<link href="{FONTS_URL}" rel="stylesheet"/>
<link rel="stylesheet" href="/site.css"/>
<link rel="stylesheet" href="/components.css"/>
<link rel="stylesheet" href="/broadsheet.css"/>
<script type="application/ld+json">{schema}</script>
</head>
<body data-mood="{_mood()}" class="bs">"""

    overlays = (CURSOR_HTML +
                '<div id="page-sweep"></div>\n'
                '<div id="read-progress" aria-hidden="true"></div>\n')

    # glossary tooltips (terms from sozluk, defined per language)
    prose = gloss_wrap(prose, lang)

    # prev / next within the series (ARTICLE_ORDER is newest-first)
    idx = ARTICLE_ORDER.index(slug)
    newer = ARTICLE_ORDER[idx - 1] if idx > 0 else None
    older = ARTICLE_ORDER[idx + 1] if idx < len(ARTICLE_ORDER) - 1 else None
    lbl_new = "Newer" if lang == "en" else "Yeni"
    lbl_old = "Older" if lang == "en" else "Eski"

    def _pn_card(s, label, arrow_left):
        if not s:
            return '<div class="pn-card pn-empty"></div>'
        t = ARTICLES[s]["title"][lang]
        arr = "←" if arrow_left else "→"
        inner = (f'<span class="pn-k">{arr} {label}</span><span class="pn-t">{t}</span>'
                 if arrow_left else
                 f'<span class="pn-k">{label} {arr}</span><span class="pn-t">{t}</span>')
        return f'<a class="pn-card{"" if arrow_left else " pn-right"}" href="{article_path(s, lang)}">{inner}</a>'

    share_lbl = "Share" if lang == "en" else "Paylaş"
    copy_lbl = "Copy link" if lang == "en" else "Bağlantıyı kopyala"
    share_html = f"""
  <div class="share-row">
    <span class="share-k">{share_lbl}</span>
    <a href="https://twitter.com/intent/tweet?text={_uq(title)}&url={_uq(canonical)}" target="_blank" rel="noopener">X / Twitter</a>
    <a href="https://www.linkedin.com/sharing/share-offsite/?url={_uq(canonical)}" target="_blank" rel="noopener">LinkedIn</a>
    <button type="button" data-copy="{canonical}">{copy_lbl}</button>
  </div>"""

    body = f"""
<header class="page-head" data-read>
  <div class="page-eyebrow">{a['cat'][lang]} · {a['num']} <span class="divider"></span> <span class="muted">{a['date_disp'][lang]} · {a['read'][lang]}</span></div>
  <h1 class="page-title">{title}</h1>
  <p class="page-dek">{dek}</p>
</header>
<div class="section">
  <div class="prose article-prose" style="max-width:760px">
{prose}
  </div>
{share_html}
  <div class="pn-grid">
    {_pn_card(newer, lbl_new, True)}
    {_pn_card(older, lbl_old, False)}
  </div>
  <a href="{yazilar_url}" class="section-link" style="display:inline-block;margin-top:28px">{back}</a>
</div>
"""

    scripts_html = (
        '<script src="/app.js"></script>\n'
        "<script>window.NCF.init({ ticker: ['btc','eth','gold','brent','dxy','us10y','vix','spx'] });</script>\n"
        "<script>document.querySelectorAll('[data-set-lang]').forEach(function(a){"
        "a.addEventListener('click',function(){try{localStorage.setItem('ncf_lang',"
        "a.getAttribute('data-set-lang'));}catch(e){}});});</script>"
    )

    html = "\n".join([head_html, overlays, _nav_html("articles", lang, sw_href),
                      TICKER_HTML, masthead("article", lang), body, footer(lang), scripts_html,
                      "</body>", "</html>", ""])
    return inject_market(html)


# ── SEO artefacts: sitemap, RSS feeds, robots ────────────────────────────────
def _xml_escape(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def _indexable_pairs():
    """(en_url, tr_url) for every indexable page + article + indicator."""
    out = [(SITE_URL + p["paths"]["en"], SITE_URL + p["paths"]["tr"]) for p in PAGES.values()]
    out += [(SITE_URL + article_path(s, "en"), SITE_URL + article_path(s, "tr")) for s in ARTICLE_ORDER]
    out += [(SITE_URL + "/now/", SITE_URL + "/tr/simdi/")]
    out += [(SITE_URL + indicator_path(s, "en"), SITE_URL + indicator_path(s, "tr")) for s in INDICATOR_ORDER]
    return out


def generate_sitemap():
    rows = []
    for en_url, tr_url in _indexable_pairs():
        alts = (f'    <xhtml:link rel="alternate" hreflang="en" href="{en_url}"/>\n'
                f'    <xhtml:link rel="alternate" hreflang="tr" href="{tr_url}"/>\n'
                f'    <xhtml:link rel="alternate" hreflang="x-default" href="{en_url}"/>')
        for url in (en_url, tr_url):
            rows.append(f"  <url>\n    <loc>{url}</loc>\n{alts}\n  </url>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
           'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + "\n".join(rows) + "\n</urlset>\n")
    (ROOT / "sitemap.xml").write_text(xml, encoding="utf-8")


def _rfc822(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%a, %d %b %Y 08:00:00 +0000")
    except Exception:
        return ""


def generate_feeds():
    for lang, fname, title, desc in (
        ("en", "feed-en.xml", "NoCashFlow — Articles", "Daily macro &amp; market analysis from nocashflow.net"),
        ("tr", "feed-tr.xml", "NoCashFlow — Yazılar", "nocashflow.net'ten günlük makro &amp; piyasa analizi"),
    ):
        items = []
        for slug in ARTICLE_ORDER:
            a = ARTICLES[slug]
            link = SITE_URL + article_path(slug, lang)
            items.append(
                "    <item>\n"
                f"      <title>{_xml_escape(a['title'][lang])}</title>\n"
                f"      <link>{link}</link>\n      <guid>{link}</guid>\n"
                f"      <pubDate>{_rfc822(a['date'])}</pubDate>\n"
                f"      <description>{_xml_escape(a['dek'][lang])}</description>\n    </item>")
        self_url = f"{SITE_URL}/{fname}"
        home = SITE_URL + ("/" if lang == "en" else "/tr/")
        xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n  <channel>\n'
               f"    <title>{title}</title>\n    <link>{home}</link>\n"
               f"    <description>{desc}</description>\n    <language>{lang}</language>\n"
               f'    <atom:link href="{self_url}" rel="self" type="application/rss+xml"/>\n'
               + "\n".join(items) + "\n  </channel>\n</rss>\n")
        (ROOT / fname).write_text(xml, encoding="utf-8")


def generate_robots():
    (ROOT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8")


# ── programmatic SEO: live single-indicator pages (/now/, /tr/simdi/) ────────
INDICATORS = {
    "crypto-fear-greed": {
        "tr_slug": "kripto-korku-acgozluluk-endeksi", "src": ("market", "fg"),
        "short": {"en": "Crypto Fear &amp; Greed", "tr": "Kripto Korku &amp; Açgözlülük"},
        "title": {"en": "Crypto Fear &amp; Greed Index — Today",
                  "tr": "Kripto Korku &amp; Açgözlülük Endeksi — Bugün"},
        "lead": {"en": "The live Crypto Fear &amp; Greed Index — what the number is right now and what it means.",
                 "tr": "Canlı Kripto Korku &amp; Açgözlülük Endeksi — sayı şu an kaç ve ne anlama geliyor."},
        "explain": {
            "en": ["The Fear &amp; Greed Index scores crypto-market sentiment on a 0–100 scale. 0–25 is extreme fear, 25–45 fear, 45–55 neutral, 55–75 greed and 75–100 extreme greed.",
                   "It blends volatility, momentum, social signals and Bitcoin dominance into a single reading. Many investors treat it as a contrarian gauge — deep fear can mark capitulation lows, extreme greed can flag froth."],
            "tr": ["Korku &amp; Açgözlülük Endeksi, kripto piyasası duyarlılığını 0–100 ölçeğinde puanlar. 0–25 aşırı korku, 25–45 korku, 45–55 nötr, 55–75 açgözlülük, 75–100 aşırı açgözlülük.",
                   "Volatilite, momentum, sosyal sinyaller ve Bitcoin dominansını tek bir okumada birleştirir. Çoğu yatırımcı bunu tersine bir gösterge olarak kullanır — derin korku dip, aşırı açgözlülük köpük işareti olabilir."]},
    },
    "vix-volatility-index": {
        "tr_slug": "vix-volatilite-endeksi", "src": ("market", "vix"),
        "short": {"en": "VIX · Volatility", "tr": "VIX · Volatilite"},
        "title": {"en": "VIX — Volatility Index Today", "tr": "VIX — Volatilite Endeksi Bugün"},
        "lead": {"en": "The CBOE VIX, the market's 30-day expected volatility — live, with what today's level signals.",
                 "tr": "CBOE VIX, piyasanın 30 günlük beklenen volatilitesi — canlı, bugünkü seviyenin anlamıyla."},
        "explain": {
            "en": ["VIX measures the 30-day expected volatility of the S&amp;P 500, derived from options prices. It is widely called the market's 'fear gauge'.",
                   "Below 15 is calm, 15–25 is normal, 25–35 is elevated stress and above 35 signals serious risk-off. Spikes usually coincide with sharp equity sell-offs."],
            "tr": ["VIX, S&amp;P 500'ün opsiyon fiyatlarından türetilen 30 günlük beklenen volatilitesini ölçer. Yaygın olarak piyasanın 'korku göstergesi' denir.",
                   "15 altı sakin, 15–25 normal, 25–35 yükselen stres, 35 üstü ciddi risk-off demektir. Ani sıçramalar genelde sert hisse satışlarıyla çakışır."]},
    },
    "dxy-dollar-index": {
        "tr_slug": "dxy-dolar-endeksi", "src": ("market", "dxy"),
        "short": {"en": "DXY · Dollar Index", "tr": "DXY · Dolar Endeksi"},
        "title": {"en": "DXY — US Dollar Index Today", "tr": "DXY — Dolar Endeksi Bugün"},
        "lead": {"en": "The US Dollar Index (DXY) live — the dollar against six major currencies, and why it matters.",
                 "tr": "ABD Dolar Endeksi (DXY) canlı — doların altı büyük para birimine karşı seviyesi ve neden önemli."},
        "explain": {
            "en": ["DXY tracks the US dollar against a basket of six major currencies (euro, yen, pound, Canadian dollar, krona, franc).",
                   "A strong dollar (104+) tends to pressure commodities, emerging-market assets and risk markets; a soft dollar (below 100) eases that pressure. It's one of the cleanest read-throughs for global liquidity."],
            "tr": ["DXY, ABD dolarını altı büyük para biriminden oluşan bir sepete (euro, yen, sterlin, Kanada doları, kron, frank) karşı izler.",
                   "Güçlü dolar (104+) emtia, gelişen piyasa varlıkları ve risk piyasaları üzerinde baskı kurar; zayıf dolar (100 altı) bu baskıyı hafifletir. Küresel likidite için en net okumalardan biridir."]},
    },
    "us-10y-2y-yield-spread": {
        "tr_slug": "abd-10y-2y-getiri-farki", "src": ("spread", None),
        "short": {"en": "10Y–2Y Spread", "tr": "10Y–2Y Farkı"},
        "title": {"en": "US 10Y–2Y Yield Spread Today (Curve Inversion)",
                  "tr": "ABD 10Y–2Y Getiri Farkı Bugün (Eğri Tersine Dönmesi)"},
        "lead": {"en": "The US Treasury 10-year minus 2-year spread — the classic recession signal, live from FRED.",
                 "tr": "ABD Hazinesi 10 yıllık eksi 2 yıllık farkı — klasik resesyon sinyali, FRED'den canlı."},
        "explain": {
            "en": ["The spread is the 10-year Treasury yield minus the 2-year. When it is positive the curve is normal; when it turns negative the curve is 'inverted'.",
                   "An inverted 10Y–2Y has preceded every US recession of the last half-century, usually by 6–18 months, which is why markets watch it so closely. Source: FRED (DGS10, DGS2)."],
            "tr": ["Fark, 10 yıllık Hazine getirisi eksi 2 yıllıktır. Pozitifken eğri normaldir; negatife dönünce eğri 'tersine dönmüş' olur.",
                   "Tersine dönmüş 10Y–2Y, son yarım yüzyıldaki her ABD resesyonunu (genelde 6–18 ay önceden) öncelemiştir; bu yüzden piyasalar yakından izler. Kaynak: FRED (DGS10, DGS2)."]},
    },
    "btc-funding-rate": {
        "tr_slug": "btc-funding-rate", "src": ("funding", None),
        "short": {"en": "BTC Funding Rate", "tr": "BTC Funding Rate"},
        "title": {"en": "Bitcoin Funding Rate Today", "tr": "Bitcoin Funding Rate Bugün"},
        "lead": {"en": "The live BTC perpetual funding rate (Deribit) — what leverage is paying right now.",
                 "tr": "Canlı BTC perpetual funding rate (Deribit) — kaldıracın şu an ne ödediği."},
        "explain": {
            "en": ["Funding rate is the periodic payment exchanged between long and short positions on perpetual futures, keeping the contract tethered to spot.",
                   "Positive funding means longs pay shorts — leveraged traders are net bullish; negative means shorts pay longs. Persistently high funding often precedes long squeezes. Source: Deribit BTC-PERPETUAL (8h)."],
            "tr": ["Funding rate, perpetual vadelilerde long ve short pozisyonlar arasında dönemsel olarak el değiştiren ödemedir; sözleşmeyi spota bağlı tutar.",
                   "Pozitif funding, long'ların short'lara ödediği — kaldıraçlı işlemciler net yükseliş yönlü; negatif ise short'lar öder. Sürekli yüksek funding genelde long squeeze öncesidir. Kaynak: Deribit BTC-PERPETUAL (8s)."]},
    },
    "fed-funds-rate": {
        "tr_slug": "fed-faiz-orani", "src": ("fed", None),
        "short": {"en": "Fed Funds Rate", "tr": "Fed Faiz Oranı"},
        "title": {"en": "Fed Funds Rate Today", "tr": "Fed Faiz Oranı Bugün"},
        "lead": {"en": "The current Federal Reserve target rate (upper bound), live from FRED.",
                 "tr": "Güncel Fed politika faizi (üst bant), FRED'den canlı."},
        "explain": {
            "en": ["This is the upper bound of the Federal Funds target range set by the FOMC — the policy rate that anchors short-term US interest rates.",
                   "It drives borrowing costs across the economy and is the single most-watched number for risk assets, the dollar and the yield curve. Source: FRED (DFEDTARU)."],
            "tr": ["Bu, FOMC tarafından belirlenen Federal Fon hedef aralığının üst bandıdır — kısa vadeli ABD faizlerini çıpalayan politika faizi.",
                   "Ekonomi genelinde borçlanma maliyetlerini belirler ve risk varlıkları, dolar ve getiri eğrisi için en çok izlenen tek rakamdır. Kaynak: FRED (DFEDTARU)."]},
    },
}
INDICATOR_ORDER = list(INDICATORS.keys())


def indicator_path(slug, lang):
    return f"/now/{slug}.html" if lang == "en" else f"/tr/simdi/{INDICATORS[slug]['tr_slug']}.html"


def indicator_out(slug, lang):
    return f"now/{slug}.html" if lang == "en" else f"tr/simdi/{INDICATORS[slug]['tr_slug']}.html"


def _ind_reading(slug, lang):
    """(value, interpretation, dir, data-px-key-or-None) from the snapshot."""
    kind, key = INDICATORS[slug]["src"]
    inst = MARKET.get("instruments", {})
    if kind == "market" and key in inst:
        d = inst[key]
        val, dirc = d["px"], d.get("dir", "neu")
        if key == "vix":
            v = float(val)
            interp = ("Calm" if v < 15 else "Normal" if v < 25 else "Elevated" if v < 35 else "High stress") if lang == "en" \
                else ("Sakin" if v < 15 else "Normal" if v < 25 else "Yüksek" if v < 35 else "Ciddi stres")
        elif key == "dxy":
            v = float(val)
            interp = ("Strong dollar" if v >= 104 else "Neutral" if v >= 100 else "Soft dollar") if lang == "en" \
                else ("Güçlü dolar" if v >= 104 else "Nötr" if v >= 100 else "Zayıf dolar")
        else:
            interp = d.get("chg", "")
        return val, interp, dirc, key
    if kind == "spread":
        sp = MACRO.get("spread")
        if sp is None:
            return "—", "", "neu", None
        val = f'{"+" if sp >= 0 else ""}{sp:.2f}%'
        interp = ("Normal curve" if sp >= 0 else "Inverted ⚠") if lang == "en" else ("Normal eğri" if sp >= 0 else "Ters ⚠")
        return val, interp, ("up" if sp >= 0 else "dn"), None
    if kind == "funding":
        f = MACRO.get("funding", {}).get("value")
        if f is None:
            return "—", "", "neu", None
        val = f'{"+" if f >= 0 else ""}{f:.4f}%'
        interp = ("Longs pay" if f > 0 else "Shorts pay" if f < 0 else "Flat") if lang == "en" \
            else ("Long'lar öder" if f > 0 else "Short'lar öder" if f < 0 else "Düz")
        return val, interp, ("up" if f > 0 else "dn" if f < 0 else "neu"), None
    if kind == "fed":
        v = MACRO.get("fed_rate", {}).get("value")
        return (f"{v:.2f}%" if v is not None else "—"), ("Target upper bound" if lang == "en" else "Hedef üst bant"), "neu", None
    return "—", "", "neu", None


def _ind_head(lang, title, desc, canonical, alt_en, alt_tr, schema):
    feed = "/feed-en.xml" if lang == "en" else "/feed-tr.xml"
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{title} — NoCashFlow</title>
<meta name="description" content="{desc}"/>
<link rel="canonical" href="{canonical}"/>
<link rel="alternate" hreflang="en" href="{alt_en}"/>
<link rel="alternate" hreflang="tr" href="{alt_tr}"/>
<link rel="alternate" hreflang="x-default" href="{alt_en}"/>
<meta property="og:title" content="{title}"/>
<meta property="og:description" content="{desc}"/>
<meta property="og:type" content="website"/>
<meta property="og:url" content="{canonical}"/>
<meta property="og:image" content="{OG_IMAGE}"/>
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:image" content="{OG_IMAGE}"/>
<meta name="twitter:site" content="@No_CashFlow"/>
<link rel="icon" href="/favicon.svg?v=2" type="image/svg+xml"/>
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png?v=2"/>
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16.png?v=2"/>
<link rel="apple-touch-icon" href="/apple-touch-icon.png?v=2"/>
<link rel="shortcut icon" href="/favicon.ico?v=2"/>
<link rel="alternate" type="application/rss+xml" title="NoCashFlow" href="{feed}"/>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<meta name="theme-color" content="#ffffff"/>
{THEME_SCRIPT}
<link href="{FONTS_URL}" rel="stylesheet"/>
<link rel="stylesheet" href="/site.css"/>
<link rel="stylesheet" href="/components.css"/>
<link rel="stylesheet" href="/broadsheet.css"/>
<script type="application/ld+json">{schema}</script>
</head>
<body data-mood="{_mood()}" class="bs">"""


def _ind_chrome_ticker():
    return CURSOR_HTML + '<div id="page-sweep"></div>\n'


def _ind_scripts():
    return (
        '<script src="/app.js"></script>\n'
        "<script>window.NCF.init({ ticker: ['btc','eth','gold','brent','dxy','us10y','vix','spx'] });</script>\n"
        "<script>document.querySelectorAll('[data-set-lang]').forEach(function(a){"
        "a.addEventListener('click',function(){try{localStorage.setItem('ncf_lang',"
        "a.getAttribute('data-set-lang'));}catch(e){}});});</script>"
    )


def render_indicator(slug, lang):
    ind = INDICATORS[slug]
    title, lead = ind["title"][lang], ind["lead"][lang]
    canonical = SITE_URL + indicator_path(slug, lang)
    alt_en, alt_tr = SITE_URL + indicator_path(slug, "en"), SITE_URL + indicator_path(slug, "tr")
    sw_href = indicator_path(slug, "tr") if lang == "en" else indicator_path(slug, "en")
    plain_title = re.sub(r"&amp;", "&", re.sub(r"<[^>]+>", "", title))
    plain_lead = re.sub(r"&amp;", "&", re.sub(r"<[^>]+>", "", lead))
    val, interp, dirc, px = _ind_reading(slug, lang)
    stamp = _fmt_stamp(MARKET.get("asof", "") or MACRO.get("asof", ""), lang)
    hub = "/now/" if lang == "en" else "/tr/simdi/"
    hub_lbl = "All indicators" if lang == "en" else "Tüm göstergeler"
    upd = "Updated" if lang == "en" else "Güncellendi"
    src_lbl = "Live indicator" if lang == "en" else "Canlı gösterge"
    explain = "".join(f"<p>{para}</p>\n" for para in ind["explain"][lang])
    px_attr = f' data-px="{px}"' if px else ""
    schema = json.dumps({"@context": "https://schema.org", "@type": "WebPage", "name": plain_title,
                         "description": plain_lead, "url": canonical, "inLanguage": lang,
                         "dateModified": (MARKET.get("asof") or ""),
                         "isPartOf": {"@type": "WebSite", "name": "NoCashFlow", "url": SITE_URL}}, ensure_ascii=False)
    head_html = _ind_head(lang, plain_title, plain_lead, canonical, alt_en, alt_tr, schema)
    vcls = f" {dirc}" if dirc in ("up", "dn") else ""
    body = f"""
<header class="page-head" data-read>
  <div class="page-eyebrow">{src_lbl} <span class="divider"></span> <span class="muted">{upd}: {stamp}</span></div>
  <h1 class="page-title">{title}</h1>
  <p class="page-dek">{lead}</p>
</header>
<div class="section">
  <div class="ind-now">
    <div class="ind-value{vcls}"{px_attr}>{val}</div>
    <div class="ind-interp">{interp}</div>
  </div>
  <div class="prose" style="max-width:720px">
{explain}  </div>
  <a href="{hub}" class="section-link" style="display:inline-block;margin-top:30px">{hub_lbl} →</a>
</div>
"""
    html = "\n".join([head_html, _ind_chrome_ticker(), _nav_html(None, lang, sw_href),
                      TICKER_HTML, masthead("indicator", lang), body, footer(lang), _ind_scripts(),
                      "</body>", "</html>", ""])
    return inject_market(html)


def render_indicator_hub(lang):
    canonical = SITE_URL + ("/now/" if lang == "en" else "/tr/simdi/")
    alt_en, alt_tr = SITE_URL + "/now/", SITE_URL + "/tr/simdi/"
    sw_href = "/tr/simdi/" if lang == "en" else "/now/"
    title = "Live Market Indicators" if lang == "en" else "Canlı Piyasa Göstergeleri"
    lead = ("Key macro &amp; crypto indicators, updated every day from primary sources — each with a plain explanation."
            if lang == "en" else
            "Önemli makro &amp; kripto göstergeleri, her gün birincil kaynaklardan güncellenir — her biri sade açıklamayla.")
    cards = []
    for s in INDICATOR_ORDER:
        val, interp, dirc, _ = _ind_reading(s, lang)
        t = INDICATORS[s].get("short", {}).get(lang) or re.sub(r"\s—.*$", "", INDICATORS[s]["title"][lang])
        cls = f" {dirc}" if dirc in ("up", "dn") else ""
        cards.append(f'<a class="ind-card" href="{indicator_path(s, lang)}">'
                     f'<div class="ic-k">{t}</div><div class="ic-v{cls}">{val}</div>'
                     f'<div class="ic-i">{interp}</div></a>')
    grid = '<div class="ind-grid">' + "".join(cards) + "</div>"
    schema = json.dumps({"@context": "https://schema.org", "@type": "CollectionPage",
                         "name": title, "url": canonical, "inLanguage": lang}, ensure_ascii=False)
    head_html = _ind_head(lang, title, re.sub(r"&amp;", "&", re.sub(r"<[^>]+>", "", lead)),
                          canonical, alt_en, alt_tr, schema)
    body = f"""
<header class="page-head" data-read>
  <div class="page-eyebrow">{'Live data' if lang == 'en' else 'Canlı veri'} <span class="divider"></span> <span class="muted">{'Updated daily' if lang == 'en' else 'Her gün güncellenir'}</span></div>
  <h1 class="page-title">{title}</h1>
  <p class="page-dek">{lead}</p>
</header>
<div class="section">
  {grid}
</div>
"""
    html = "\n".join([head_html, _ind_chrome_ticker(), _nav_html(None, lang, sw_href),
                      TICKER_HTML, masthead("indicator", lang), body, footer(lang), _ind_scripts(),
                      "</body>", "</html>", ""])
    return inject_market(html)


def build():
    written = []
    for page, p in PAGES.items():
        for lang in LANGS:
            if not _exists(lang, page):
                continue
            out_path = ROOT / p["out"][lang]
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(render(page, lang), encoding="utf-8")
            written.append(p["out"][lang])
            print(f"  build {p['out'][lang]:28} [{lang}]")
    for slug in ARTICLES:
        for lang in LANGS:
            if not (CONTENT / "articles" / slug / f"{lang}.html").exists():
                continue
            out_path = ROOT / article_out(slug, lang)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(render_article(slug, lang), encoding="utf-8")
            written.append(article_out(slug, lang))
            print(f"  build {article_out(slug, lang):28} [{lang}]")
    for lang in LANGS:                                  # live indicator hub + pages
        hub_out = "now/index.html" if lang == "en" else "tr/simdi/index.html"
        (ROOT / hub_out).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / hub_out).write_text(render_indicator_hub(lang), encoding="utf-8")
        written.append(hub_out)
        for slug in INDICATOR_ORDER:
            op = ROOT / indicator_out(slug, lang)
            op.parent.mkdir(parents=True, exist_ok=True)
            op.write_text(render_indicator(slug, lang), encoding="utf-8")
            written.append(indicator_out(slug, lang))
        print(f"  build now/ hub + {len(INDICATOR_ORDER)} indicators   [{lang}]")
    generate_sitemap()
    generate_feeds()
    generate_robots()
    print("  + sitemap.xml · feed-en.xml · feed-tr.xml · robots.txt")
    # JSONP snapshot for the embeddable widget (cross-origin friendly)
    (ROOT / "data" / "market.js").write_text(
        "window.NCFMarket&&window.NCFMarket(" + json.dumps(MARKET, ensure_ascii=False) + ");",
        encoding="utf-8")
    print("  + data/market.js (widget JSONP)")
    _render_share_image()
    print(f"\n✓ {len(written)} page(s) + SEO artefacts written.")


def _render_share_image():
    """Refresh the daily share card. Guarded: a missing Pillow never breaks build."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "make_share_image", ROOT / "scripts" / "make_share_image.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.build_card()
    except Exception as e:
        print(f"  (share image skipped: {e})")


if __name__ == "__main__":
    if "--clean" in sys.argv:
        tr = ROOT / "tr"
        if tr.exists():
            import shutil
            shutil.rmtree(tr)
            print("cleaned /tr/")
    build()
