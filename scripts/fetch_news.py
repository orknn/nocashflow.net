#!/usr/bin/env python3
"""What's Moving Markets — retrieve, score and shortlist real stories.

Nothing here writes a headline. Every title, summary, source name, link and
timestamp is copied verbatim from the feed that published it; the pipeline only
decides which of the retrieved stories are worth showing and in what order.
When nothing clears the relevance bar the file is written with zero stories and
the dashboard falls back to its authored empty state — an empty section is a
valid outcome, a fabricated one is not.

    RSS (primary, 6 feeds) ─┐
    GDELT DOC (best effort) ├→ dedupe → classify → score → top 5 → news.json
    Alpha Vantage (opt-in) ─┘

Alpha Vantage runs only when ALPHAVANTAGE_API_KEY is set; it is a supplement,
never the only source. GDELT rate-limits hard (one request per 5s, and it
429s for long stretches from shared CI ranges), so it is retried with backoff
and then skipped — RSS alone still fills the section.
"""
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import requests

DATA = Path(__file__).resolve().parent.parent / "data"
UA = {"User-Agent": "Mozilla/5.0 (NoCashFlow news fetcher; +https://nocashflow.net)"}
TIMEOUT = 20
MAX_STORIES = 5
MIN_SCORE = 3.0          # below this a story is not worth the reader's time
LOOKBACK_H = 48

# name, url, weight, fallback category — weight reflects how directly the
# publisher moves markets, not how much we like them.
FEEDS = [
    ("Federal Reserve", "https://www.federalreserve.gov/feeds/press_all.xml", 3.0, "rates"),
    ("ECB", "https://www.ecb.europa.eu/rss/press.html", 2.6, "rates"),
    ("SEC", "https://www.sec.gov/news/pressreleases.rss", 2.2, "policy"),
    ("EIA", "https://www.eia.gov/rss/todayinenergy.xml", 2.0, "energy"),
    ("CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258", 1.6, None),
    ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex", 1.2, None),
]

GDELT_QUERY = ('(inflation OR "federal reserve" OR "interest rates" OR '
               '"stock market" OR earnings OR OPEC) sourcelang:english')

# category → the words that put a story in it, most specific first
CATEGORIES = [
    ("rates",       ["federal reserve", "fomc", "interest rate", "rate cut", "rate hike",
                     "treasury yield", "bond market", "ecb", "central bank", "monetary policy",
                     "inflation", "cpi", "pce"]),
    ("energy",      ["oil", "crude", "brent", "wti", "opec", "natural gas", "refinery",
                     "petroleum", "lng", "diesel"]),
    ("crypto",      ["bitcoin", "ethereum", "crypto", "stablecoin", "digital asset", "token"]),
    ("fx",          ["dollar", "euro", "yen", "currency", "forex", "exchange rate", "dxy"]),
    ("technology",  ["chip", "semiconductor", "artificial intelligence", " ai ", "data center",
                     "cloud", "nvidia", "software"]),
    ("policy",      ["sec ", "regulator", "antitrust", "tariff", "sanction", "trade deal"]),
    ("equities",    ["earnings", "guidance", "shares", "stock", "buyback", "ipo", "revenue"]),
]

# words that mark a story as market-moving rather than merely financial
SIGNAL = {
    3.0: ["rate cut", "rate hike", "fomc", "emergency", "default", "downgrade",
          "opec+ cut", "recession"],
    2.0: ["inflation", "cpi", "payrolls", "gdp", "guidance cut", "profit warning",
          "tariff", "sanction", "supply cut"],
    1.0: ["earnings", "forecast", "outlook", "merger", "acquisition", "buyback",
          "production", "demand"],
}
# stories that are financial-adjacent but not market news
NOISE = ["how to", "best deals", "review:", "recipe", "renovated", "celebrity",
         "horoscope", "gift guide", "sweepstakes", "obituary"]


def _load(name, default):
    p = DATA / name
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default


def _universe():
    """Tickers and company names the dashboard already tracks, for tagging."""
    wl = _load("dashboard-mock.json", {}).get("watchlists", {}).get("quotes", {})
    out = {}
    for sym, q in wl.items():
        out[sym] = q.get("name", sym)
    out.update({"BTC": "Bitcoin", "ETH": "Ethereum", "DXY": "Dollar",
                "BRN": "Brent", "XAU": "Gold", "US10Y": "Treasury"})
    return out


def canon(url):
    """Strip tracking parameters so the same story from two feeds collapses."""
    try:
        s = urlsplit(url)
        return urlunsplit((s.scheme, s.netloc.lower().replace("www.", ""), s.path.rstrip("/"), "", ""))
    except Exception:
        return url


def clean(text, limit=240):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "…"
    return text


def parse_when(raw):
    if not raw:
        return None
    for fn in (parsedate_to_datetime,
               lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))):
        try:
            dt = fn(raw.strip())
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None


def from_rss():
    ns = "{http://www.w3.org/2005/Atom}"
    items = []
    for name, url, weight, cat in FEEDS:
        try:
            r = requests.get(url, headers=UA, timeout=TIMEOUT)
            r.raise_for_status()
            root = ET.fromstring(r.content)
        except Exception as e:
            print(f"  ⚠️  {name}: {type(e).__name__}")
            continue
        entries = root.findall(".//item") or root.findall(f".//{ns}entry")
        for e in entries[:25]:
            title = e.findtext("title") or e.findtext(f"{ns}title") or ""
            link = e.findtext("link") or ""
            if not link:
                node = e.find(f"{ns}link")
                link = node.get("href", "") if node is not None else ""
            when = parse_when(e.findtext("pubDate") or e.findtext("published")
                              or e.findtext(f"{ns}updated"))
            summary = (e.findtext("description") or e.findtext("summary")
                       or e.findtext(f"{ns}summary") or "")
            if title and link:
                items.append({"title": clean(title, 160), "url": link, "source": name,
                              "weight": weight, "hint": cat, "when": when,
                              "summary": clean(summary)})
        print(f"  · {name}: {len(entries)} öğe")
    return items


def from_gdelt(attempts=3):
    """Best effort. GDELT 429s aggressively; a miss is not a failure."""
    for i in range(attempts):
        try:
            r = requests.get("https://api.gdeltproject.org/api/v2/doc/doc",
                             params={"query": GDELT_QUERY, "mode": "ArtList",
                                     "format": "json", "maxrecords": 40,
                                     "timespan": f"{LOOKBACK_H}h"},
                             headers=UA, timeout=30)
            if r.status_code == 429 or not r.text.lstrip().startswith("{"):
                raise RuntimeError("rate limited")
            arts = r.json().get("articles", [])
            out = []
            for a in arts:
                out.append({"title": clean(a.get("title", ""), 160),
                            "url": a.get("url", ""), "source": a.get("domain", "GDELT"),
                            "weight": 1.0, "hint": None,
                            "when": parse_when(a.get("seendate", "")),
                            "summary": ""})
            print(f"  · GDELT: {len(out)} makale")
            return [x for x in out if x["title"] and x["url"]]
        except Exception as e:
            if i == attempts - 1:
                print(f"  ⚠️  GDELT atlandı ({type(e).__name__}) — RSS yeterli")
                return []
            time.sleep(6 * (i + 1))
    return []


def from_alpha_vantage():
    """Supplement, never the sole source. Skipped without a key."""
    key = os.environ.get("ALPHAVANTAGE_API_KEY")
    if not key:
        return []
    try:
        r = requests.get("https://www.alphavantage.co/query",
                         params={"function": "NEWS_SENTIMENT", "topics":
                                 "financial_markets,economy_monetary,energy_transportation",
                                 "limit": 50, "apikey": key},
                         headers=UA, timeout=TIMEOUT)
        feed = r.json().get("feed", []) or []
        out = [{"title": clean(a.get("title", ""), 160), "url": a.get("url", ""),
                "source": a.get("source", "Alpha Vantage"), "weight": 1.4, "hint": None,
                "when": parse_when(a.get("time_published", "")),
                "summary": clean(a.get("summary", ""))} for a in feed]
        print(f"  · Alpha Vantage: {len(out)} makale")
        return [x for x in out if x["title"] and x["url"]]
    except Exception as e:
        print(f"  ⚠️  Alpha Vantage: {type(e).__name__}")
        return []


def classify(item):
    blob = f" {item['title'].lower()} {item['summary'].lower()} "
    for cat, words in CATEGORIES:
        if any(w in blob for w in words):
            return cat
    return item["hint"] or "markets"


def score(item, universe):
    blob = f" {item['title'].lower()} {item['summary'].lower()} "
    if any(n in blob for n in NOISE):
        return 0.0, []
    s = item["weight"]
    signal = 0.0
    for pts, words in SIGNAL.items():
        if any(w in blob for w in words):
            signal += pts
    assets = [sym for sym, name in universe.items()
              if re.search(rf"\b{re.escape(sym)}\b", item["title"])
              or (len(name) > 4 and name.lower() in blob)]
    # a trusted publisher is not itself news: without a market signal or a
    # tracked asset, an ECB fireside chat outranks nothing and is dropped
    if signal == 0 and not assets:
        return 0.0, []
    s += signal + min(1.5, 0.5 * len(assets))
    if item["when"]:
        age = (datetime.now(timezone.utc) - item["when"]).total_seconds() / 3600
        s += 1.2 if age <= 12 else (0.6 if age <= 24 else 0.0)
        if age > LOOKBACK_H:
            return 0.0, assets
    return round(s, 2), assets[:4]


def dedupe(items):
    seen, out = {}, []
    for it in sorted(items, key=lambda x: -x["weight"]):
        key = canon(it["url"])
        if key in seen:
            continue
        if any(SequenceMatcher(None, it["title"].lower(), o["title"].lower()).ratio() > 0.82
               for o in out):
            continue
        seen[key] = True
        out.append(it)
    return out


def build():
    universe = _universe()
    print("Kaynaklar:")
    items = from_rss() + from_gdelt() + from_alpha_vantage()
    print(f"  toplam ham: {len(items)}")
    items = dedupe(items)
    print(f"  tekilleştirme sonrası: {len(items)}")

    ranked = []
    for it in items:
        s, assets = score(it, universe)
        if s < MIN_SCORE:
            continue
        it.update({"score": s, "assets": assets, "category": classify(it)})
        ranked.append(it)
    ranked.sort(key=lambda x: -x["score"])
    top = ranked[:MAX_STORIES]

    hi = top[0]["score"] if top else 0
    stories = []
    for it in top:
        rel = it["score"] / hi if hi else 0
        stories.append({
            "headline": it["title"],
            "summary": it["summary"],
            "category": it["category"],
            "importance": "high" if rel >= 0.85 else ("medium" if rel >= 0.6 else "low"),
            "assets": it["assets"],
            "source": it["source"],
            "url": it["url"],
            "published": it["when"].isoformat().replace("+00:00", "Z") if it["when"] else None,
            "score": it["score"],
        })

    return {
        "_note": "Retrieved stories only. Headline, summary, source and link are "
                 "copied verbatim from the publisher; this pipeline ranks, it "
                 "does not write. Zero stories is a valid state — the dashboard "
                 "then shows its authored empty state rather than filler.",
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": sorted({s["source"] for s in stories}),
        "considered": len(items),
        "stories": stories,
    }


if __name__ == "__main__":
    out = build()
    (DATA / "news.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\n• news.json: {len(out['stories'])} hikâye "
          f"({out['considered']} değerlendirildi) · kaynak: {', '.join(out['sources']) or '—'}")
    for s in out["stories"]:
        print(f"    [{s['importance']:6s}] {s['category']:10s} {s['score']:5.1f}  "
              f"{s['headline'][:64]}  — {s['source']}")
