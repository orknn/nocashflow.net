#!/usr/bin/env python3
"""
NoCashFlow · static site builder (bilingual)

Source of truth for the shared chrome (head, ticker, nav, footer, scripts).
Per-page body content lives in content/<lang>/<page>.html and is wrapped in
the localized chrome. English is emitted at the site root; Turkish under /tr/.

    python3 build.py            # build all pages
    python3 build.py --clean    # remove generated /tr/ tree first

Design is reproduced faithfully from the current hand-authored pages — this
builder changes structure (templating + i18n), never the visual design.
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

SUBSCRIBE = {
    "en": ("Subscribe", "/bulletin_page.html"),
    "tr": ("Abone Ol",  "/tr/bulletin_page.html"),
}

# Footer chrome strings (structural UI — content translations are page-gated)
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

# per-lang footer link targets (en at root, tr under /tr/)
def _flink(lang, en_href, tr_href):
    return en_href if lang == "en" else tr_href

# ── page registry ────────────────────────────────────────────────────────────
# Only pages whose content partials exist are built. Others stay hand-authored
# until templatized, so the live site is never broken mid-migration.
PAGES = {
    "index": {
        "nav_key": "home",
        "splash": True,
        "ticker": "['btc','eth','gold','brent','dxy','us10y','vix','spx','eurusd']",
        "paths": {"en": "/", "tr": "/tr/"},
        "out":   {"en": "index.html", "tr": "tr/index.html"},
        "title": {
            "en": "NoCashFlow — Macro &amp; Market Analysis",
            "tr": "NoCashFlow — Makro &amp; Piyasa Analizi",
        },
        "desc": {
            "en": "Data-driven macro analysis every Sunday — oil shocks, smart money, nuclear energy, Fed policy. From Barcelona.",
            "tr": "Her pazar veri odaklı makro analiz — petrol şokları, akıllı para, nükleer enerji, Fed politikası. Barcelona'dan.",
        },
        # og:description was authored separately from meta description on the
        # live page — preserved verbatim so the build doesn't alter content.
        "og_desc": {
            "en": "Data-driven macro analysis every Sunday. Macro, crypto and commodities — primary source, always linked.",
            "tr": "Her pazar veri odaklı makro analiz. Makro, kripto ve emtia — birincil kaynak, her zaman bağlantılı.",
        },
    },
}

# ── chrome fragments ─────────────────────────────────────────────────────────
def head(page, lang):
    p = PAGES[page]
    canonical = SITE_URL + p["paths"][lang]
    alt_en = SITE_URL + p["paths"]["en"]
    alt_tr = SITE_URL + p["paths"]["tr"]
    splash_css = '<link rel="stylesheet" href="/splash.css"/>\n' if (p.get("splash") and lang == "en") else ""
    early = _early_script(page, lang) if (p.get("splash") or lang == "tr") else ""
    og_desc = p.get("og_desc", p["desc"])[lang]
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{p["title"][lang]}</title>
<meta name="description" content="{p["desc"][lang]}"/>
<link rel="canonical" href="{canonical}"/>
<link rel="alternate" hreflang="en" href="{alt_en}"/>
<link rel="alternate" hreflang="tr" href="{alt_tr}"/>
<link rel="alternate" hreflang="x-default" href="{alt_en}"/>
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
{splash_css}{early}</head>
<body>"""


def _early_script(page, lang):
    """Pre-paint language decision (runs in <head>, before body renders)."""
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
    # tr page: honor ?lang / stored 'en' preference, no splash
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


def ticker():
    return """<div class="cursor-ring"><span class="c-label">Read</span></div>
<div class="cursor-dot"></div>

<!-- TICKER -->
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

    sub_label, _ = SUBSCRIBE[lang]
    sub_href = SUBSCRIBE[lang][1]

    # language switcher: en page -> "TR" (go to tr path); tr page -> "EN" (go to en path)
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
    year_sep = ""
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
    out.append(f"<script>window.NCF.init({{ ticker: {p['ticker']} }});</script>")
    # language switcher: persist preference on click (all pages)
    out.append(
        "<script>document.querySelectorAll('[data-set-lang]').forEach(function(a){"
        "a.addEventListener('click',function(){try{localStorage.setItem('ncf_lang',"
        "a.getAttribute('data-set-lang'));}catch(e){}});});</script>"
    )
    if p.get("splash") and lang == "en":  # splash lives only on the en root
        out.append('<script src="/splash.js"></script>')
    return "\n".join(out)


# ── assembly ─────────────────────────────────────────────────────────────────
def render(page, lang):
    p = PAGES[page]
    body_partial = (CONTENT / lang / f"{page}.html").read_text(encoding="utf-8").rstrip("\n")
    splash_html = splash_overlay() if (p.get("splash") and lang == "en") else ""
    return "\n".join([
        head(page, lang),
        splash_html + ticker(),
        nav(page, lang),
        body_partial,
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
            partial = CONTENT / lang / f"{page}.html"
            if not partial.exists():
                print(f"  skip  {page} [{lang}] — no content/{lang}/{page}.html")
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
