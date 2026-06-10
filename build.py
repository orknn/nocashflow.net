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
import sys
from pathlib import Path

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
SITE_URL = "https://nocashflow.net"
LANGS = ("en", "tr")

# ── shared navigation (key, label_en, label_tr, href_en, href_tr) ────────────
NAV = [
    ("home",      "Home",      "Ana Sayfa", "/",                   "/tr/"),
    ("articles",  "Articles",  "Yazılar",   "/yazilar.html",       "/tr/yazilar.html"),
    ("macro",     "Macro",     "Makro",     "/macro.html",         "/tr/macro.html"),
    ("dashboard", "Dashboard", "Panel",     "/dashboard.html",     "/tr/dashboard.html"),
    ("bulletin",  "Bulletin",  "Bülten",    "/bulletin_page.html", "/tr/bulletin_page.html"),
    ("about",     "About",     "Hakkında",  "/hakkinda.html",      "/tr/hakkinda.html"),
]

SUBSCRIBE = {"en": ("Subscribe", "/bulletin_page.html"),
             "tr": ("Abone Ol",  "/tr/bulletin_page.html")}

FOOTER = {
    "en": {
        "brand_desc": "Macro economics, crypto and market analysis. Every Sunday morning, with data — from Barcelona.",
        "col_pages": "Pages", "col_content": "Content", "col_social": "Social",
        "l_home": "Home", "l_articles": "Articles", "l_macro": "Macro", "l_dashboard": "Dashboard",
        "l_bulletin": "Bulletin", "l_about": "About", "l_glossary": "Glossary",
        "l_email": "Email", "bottom_about": "About", "bottom_subscribe": "Subscribe",
        "disclaimer": "This site is for information only and does not provide investment advice.",
    },
    "tr": {
        "brand_desc": "Makro ekonomi, kripto ve piyasa analizi. Her pazar sabahı, veriyle — Barcelona'dan.",
        "col_pages": "Sayfalar", "col_content": "İçerik", "col_social": "Sosyal",
        "l_home": "Ana Sayfa", "l_articles": "Yazılar", "l_macro": "Makro", "l_dashboard": "Panel",
        "l_bulletin": "Bülten", "l_about": "Hakkında", "l_glossary": "Sözlük",
        "l_email": "E-posta", "bottom_about": "Hakkında", "bottom_subscribe": "Abone Ol",
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
        "desc":  {"en": "Data-driven macro analysis every Sunday — oil shocks, smart money, nuclear energy, Fed policy. From Barcelona.",
                  "tr": "Her pazar veri odaklı makro analiz — petrol şokları, akıllı para, nükleer enerji, Fed politikası. Barcelona'dan."},
        "og_desc": {"en": "Data-driven macro analysis every Sunday. Macro, crypto and commodities — primary source, always linked.",
                    "tr": "Her pazar veri odaklı makro analiz. Makro, kripto ve emtia — birincil kaynak, her zaman bağlantılı."},
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
    "yazilar": {
        "nav_key": "articles",
        "paths": {"en": "/yazilar.html", "tr": "/tr/yazilar.html"},
        "out":   {"en": "yazilar.html", "tr": "tr/yazilar.html"},
        "title": {"en": "Articles — NoCashFlow | Sunday Morning Series",
                  "tr": "Yazılar — NoCashFlow | Pazar Sabahı Serisi"},
        "desc":  {"en": "Macro analysis essays — oil, copper, nuclear energy, Fed policy, smart money. One sharp take every Sunday.",
                  "tr": "Makro analiz yazıları — petrol, bakır, nükleer enerji, Fed politikası, akıllı para. Her pazar tek keskin yorum."},
        "og_desc": {"en": "Data-driven macro analysis essays. One sharp take every Sunday.",
                    "tr": "Veri odaklı makro analiz yazıları. Her pazar tek keskin yorum."},
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
}

# ── helpers ──────────────────────────────────────────────────────────────────
def _exists(lang, page):
    return (CONTENT / lang / f"{page}.html").exists()

def _read(rel):
    p = CONTENT / rel
    return p.read_text(encoding="utf-8").rstrip("\n") if p.exists() else ""

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
    head_extra = _read(f"head/{page}.html")
    head_extra = (head_extra + "\n") if head_extra else ""
    splash_css = '<link rel="stylesheet" href="/splash.css"/>\n' if (p.get("splash") and lang == "en") else ""
    early = _early_script(page, lang) if (p.get("splash") or lang == "tr") else ""

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
<meta name="twitter:card" content="summary_large_image"/>
<link rel="icon" href="/favicon.svg" type="image/svg+xml"/>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<meta name="theme-color" content="#ffffff"/>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300..900;1,9..144,300..900&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet"/>
<link rel="stylesheet" href="/site.css"/>
<link rel="stylesheet" href="/components.css"/>
{head_extra}{splash_css}{early}</head>
<body>"""


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


def chrome_top(page):
    cursor = ""
    if PAGES[page].get("cursor"):
        cursor = ('<div class="cursor-ring"><span class="c-label">Read</span></div>\n'
                  '<div class="cursor-dot"></div>\n\n')
    return cursor + """<!-- TICKER -->
<div class="ticker">
  <div class="ticker-label"><span class="dot"></span> Live</div>
  <div class="ticker-track" id="ticker-track"></div>
</div>
"""


def nav(page, lang):
    active = PAGES[page]["nav_key"]
    home_href = "/" if lang == "en" else "/tr/"
    links = []
    for key, en_l, tr_l, en_h, tr_h in NAV:
        label = en_l if lang == "en" else tr_l
        href = en_h if lang == "en" else tr_h
        cls = ' class="active"' if key == active else ""
        links.append(f'      <a href="{href}"{cls}>{label}</a>')
    links_html = "\n".join(links)

    sub_label, sub_href = SUBSCRIBE[lang]
    p = PAGES[page]
    if lang == "en":
        sw_label, sw_href, sw_set, sw_aria = "TR", p["paths"]["tr"], "tr", "Türkçe'ye geç"
    else:
        sw_label, sw_href, sw_set, sw_aria = "EN", p["paths"]["en"], "en", "Switch to English"

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
      <a href="{sub_href}" class="subscribe">{sub_label}</a>
      <button class="menu-toggle" id="menu-toggle" aria-label="Open menu"><span></span></button>
    </div>
  </div>
</nav>
"""


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
          <li><a href="{fl('/dashboard.html', '/tr/dashboard.html')}">{f['l_dashboard']}</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h4>{f['col_content']}</h4>
        <ul>
          <li><a href="{fl('/bulletin_page.html', '/tr/bulletin_page.html')}">{f['l_bulletin']}</a></li>
          <li><a href="{fl('/hakkinda.html', '/tr/hakkinda.html')}">{f['l_about']}</a></li>
          <li><a href="{fl('/sozluk.html', '/tr/sozluk.html')}">{f['l_glossary']}</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h4>{f['col_social']}</h4>
        <ul>
          <li><a href="https://twitter.com/No_CashFlow" target="_blank" rel="noopener">Twitter / X</a></li>
          <li><a href="https://www.linkedin.com/in/orkunbicen/" target="_blank" rel="noopener">LinkedIn</a></li>
          <li><a href="mailto:orkun@nocashflow.net">{f['l_email']}</a></li>
        </ul>
      </div>
    </div>
    <div class="footer-bot">
      <span>© <span data-year>2026</span> NoCashFlow.net · Barcelona</span>
      <span><a href="{fl('/hakkinda.html', '/tr/hakkinda.html')}">{f['bottom_about']}</a> · <a href="{fl('/bulletin_page.html', '/tr/bulletin_page.html')}">{f['bottom_subscribe']}</a></span>
    </div>
    <div class="disclaimer">{f['disclaimer']}</div>
  </div>
</footer>
"""


def scripts(page, lang):
    p = PAGES[page]
    out = ['<script src="/app.js"></script>']
    foot = _read(f"foot/{page}.html")          # page-specific NCF.init + JS (verbatim)
    if foot:
        out.append(foot)
    out.append(
        "<script>document.querySelectorAll('[data-set-lang]').forEach(function(a){"
        "a.addEventListener('click',function(){try{localStorage.setItem('ncf_lang',"
        "a.getAttribute('data-set-lang'));}catch(e){}});});</script>"
    )
    if p.get("splash") and lang == "en":       # splash lives only on the en root
        out.append('<script src="/splash.js"></script>')
    return "\n".join(out)


# ── assembly ─────────────────────────────────────────────────────────────────
def render(page, lang):
    p = PAGES[page]
    body = _read(f"{lang}/{page}.html")
    splash_html = splash_overlay() if (p.get("splash") and lang == "en") else ""
    return "\n".join([
        head(page, lang),
        splash_html + chrome_top(page),
        nav(page, lang),
        body,
        footer(lang),
        scripts(page, lang),
        "</body>",
        "</html>",
        "",
    ])


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
            print(f"  build {p['out'][lang]:24} [{lang}]")
    print(f"\n✓ {len(written)} page(s) written.")


if __name__ == "__main__":
    if "--clean" in sys.argv:
        tr = ROOT / "tr"
        if tr.exists():
            import shutil
            shutil.rmtree(tr)
            print("cleaned /tr/")
    build()
