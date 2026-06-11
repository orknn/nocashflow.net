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
import re
import sys
from datetime import datetime, timezone, timedelta
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
        rows.append(
            f'<tr class="cal-row"><td class="mono">{wd}</td>'
            f'<td class="mono">{e.get("time", "")}</td><td>{ev}</td>'
            f'<td>{flag} {ccy}</td><td class="mono">{e.get("prev", "—")}</td>'
            f'<td class="mono">{e.get("est", "—")}</td></tr>')
    body = "\n      ".join(rows) or \
        '<tr><td colspan="6" class="muted" style="text-align:center;padding:20px">—</td></tr>'

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


def render(page, lang):
    p = PAGES[page]
    body = _read(f"{lang}/{page}.html")
    splash_html = splash_overlay() if (p.get("splash") and lang == "en") else ""
    html = "\n".join([
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
    # fill build-time snapshots (market values + macro KPIs + economic calendar)
    html = inject_calendar(html, lang)
    html = inject_macro(html, lang)
    html = inject_article_list(html, lang)
    html = inject_market(html)
    return html


# ── articles (own pages: /articles/<slug>.html en, /tr/yazilar/<slug>.html tr) ─
OG_IMAGE = SITE_URL + "/images/featured_story.png"

ARTICLES = {
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
ARTICLE_ORDER = ["smart-money", "nukleer", "bakir", "petrol"]  # newest first


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
<link rel="icon" href="/favicon.svg" type="image/svg+xml"/>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<meta name="theme-color" content="#ffffff"/>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300..900;1,9..144,300..900&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet"/>
<link rel="stylesheet" href="/site.css"/>
<link rel="stylesheet" href="/components.css"/>
<script type="application/ld+json">{schema}</script>
</head>
<body>"""

    ticker = ('<!-- TICKER -->\n<div class="ticker">\n'
              '  <div class="ticker-label"><span class="dot"></span> Live</div>\n'
              '  <div class="ticker-track" id="ticker-track"></div>\n</div>\n')

    body = f"""
<header class="page-head" data-read>
  <div class="page-eyebrow">{a['cat'][lang]} · {a['num']} <span class="divider"></span> <span class="muted">{a['date_disp'][lang]} · {a['read'][lang]}</span></div>
  <h1 class="page-title">{title}</h1>
  <p class="page-dek">{dek}</p>
</header>
<div class="section">
  <div class="prose" style="max-width:760px">
{prose}
  </div>
  <a href="{yazilar_url}" class="section-link" style="display:inline-block;margin-top:36px">{back}</a>
</div>
"""

    scripts_html = (
        '<script src="/app.js"></script>\n'
        "<script>window.NCF.init({ ticker: ['btc','eth','gold','brent','dxy','us10y','vix','spx'] });</script>\n"
        "<script>document.querySelectorAll('[data-set-lang]').forEach(function(a){"
        "a.addEventListener('click',function(){try{localStorage.setItem('ncf_lang',"
        "a.getAttribute('data-set-lang'));}catch(e){}});});</script>"
    )

    html = "\n".join([head_html, ticker, _nav_html("articles", lang, sw_href),
                      body, footer(lang), scripts_html, "</body>", "</html>", ""])
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
    print(f"\n✓ {len(written)} page(s) written.")


if __name__ == "__main__":
    if "--clean" in sys.argv:
        tr = ROOT / "tr"
        if tr.exists():
            import shutil
            shutil.rmtree(tr)
            print("cleaned /tr/")
    build()
