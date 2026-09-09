#!/usr/bin/env python3
"""Watchlists + chart series for the dashboard.

Two artefacts, both keyless and sourced — nothing here is synthesised:

  data/watchlists.json  the 12 curated lists, one quote row per ticker
                        (price, 1D/1W/1M/YTD/1Y, volume, day range, 52w range,
                        30-day spark), plus gainers/losers/most-active ranked
                        over that same universe.
  data/charts.json      the seven instruments behind the dashboard's main
                        chart — 1y of daily closes (1M/3M/YTD/1Y) and 5y of
                        weekly closes (5Y), so the page can switch range
                        client-side without another request.

Equities/ETFs come from the same Nasdaq historical endpoint fetch_markets.py
already uses; Bitcoin comes from Kraken's public OHLC. A ticker that fails is
carried over from the previous snapshot rather than dropped or invented.
"""
import time
from datetime import date, datetime, timedelta, timezone

import requests

from fetch_markets import (NH, TIMEOUT, _pct, _round_price, load_json,
                           nasdaq_hist, now_iso, write_json)

# ── the curated lists ────────────────────────────────────────────────────────
# key, display name, [(ticker, company)]
WATCHLISTS = [
    ("main", "Main", [
        ("NVDA", "NVIDIA"), ("VRT", "Vertiv"), ("RKLB", "Rocket Lab"),
        ("MP", "MP Materials"), ("CRWD", "CrowdStrike")]),
    ("ai-infrastructure", "AI Infrastructure", [
        ("NVDA", "NVIDIA"), ("AVGO", "Broadcom"), ("AMD", "AMD"),
        ("MRVL", "Marvell Technology"), ("ANET", "Arista Networks"),
        ("DELL", "Dell Technologies"), ("SMCI", "Super Micro Computer")]),
    ("memory-dram", "Memory / DRAM", [
        ("MU", "Micron Technology"), ("SNDK", "SanDisk"),
        ("WDC", "Western Digital"), ("STX", "Seagate Technology"),
        ("TSM", "TSMC")]),
    ("ai-power-cooling", "AI Power & Cooling", [
        ("VRT", "Vertiv"), ("GEV", "GE Vernova"), ("ETN", "Eaton"),
        ("PWR", "Quanta Services"), ("MOD", "Modine"),
        ("CEG", "Constellation Energy")]),
    ("space-defense", "Space & Defense", [
        ("RKLB", "Rocket Lab"), ("ASTS", "AST SpaceMobile"),
        ("LUNR", "Intuitive Machines"), ("KTOS", "Kratos Defense"),
        ("AVAV", "AeroVironment"), ("PL", "Planet Labs")]),
    ("rare-earths", "Rare Earths / Magnets", [
        ("MP", "MP Materials"), ("UUUU", "Energy Fuels"),
        ("USAR", "USA Rare Earth")]),
    ("nuclear-uranium", "Nuclear / Uranium", [
        ("CCJ", "Cameco"), ("UEC", "Uranium Energy"), ("DNN", "Denison Mines"),
        ("LEU", "Centrus Energy"), ("SMR", "NuScale Power"), ("OKLO", "Oklo")]),
    ("cybersecurity", "Cybersecurity", [
        ("CRWD", "CrowdStrike"), ("PANW", "Palo Alto Networks"),
        ("ZS", "Zscaler"), ("FTNT", "Fortinet"), ("NET", "Cloudflare")]),
    ("robotics", "Robotics & Automation", [
        ("SYM", "Symbotic"), ("TER", "Teradyne"), ("ROK", "Rockwell Automation"),
        ("ISRG", "Intuitive Surgical"), ("PATH", "UiPath")]),
    ("ai-software", "AI Software", [
        ("PLTR", "Palantir"), ("SNOW", "Snowflake"), ("DDOG", "Datadog"),
        ("DT", "Dynatrace"), ("NOW", "ServiceNow")]),
    ("fintech-digital", "Fintech / Digital Assets", [
        ("COIN", "Coinbase"), ("HOOD", "Robinhood"), ("SOFI", "SoFi"),
        ("NU", "Nu Holdings"), ("CRCL", "Circle")]),
    ("us-china", "US-listed China", [
        ("BABA", "Alibaba"), ("PDD", "PDD Holdings"), ("BIDU", "Baidu"),
        ("NIO", "NIO"), ("XPEV", "XPeng")]),
]

# ── main-chart instruments: key, label, symbol, assetclass, source note ───────
# Index levels are not free; the site's existing convention is an ETF proxy,
# labelled as one (dashboard already reads "ETF proxies · last close").
CHART_INSTRUMENTS = [
    ("spx",   "S&P 500",        "SPY", "etf",    "SPY · ETF proxy"),
    ("ndx",   "Nasdaq 100",     "QQQ", "etf",    "QQQ · ETF proxy"),
    ("dax",   "DAX",            "EWG", "etf",    "EWG · Germany ETF proxy"),
    ("sx5e",  "Euro Stoxx 50",  "FEZ", "etf",    "FEZ · ETF proxy"),
    ("btc",   "Bitcoin",        "BTC", "kraken", "Kraken · XBT/USD spot"),
    ("gold",  "Gold",           "GLD", "etf",    "GLD · ETF proxy"),
    ("brent", "Brent Oil",      "BNO", "etf",    "BNO · ETF proxy"),
]

PAUSE = 0.4          # same courtesy delay fetch_markets uses
SPARK_N = 30
DAILY_N = 252        # ~1 trading year, enough for 1M/3M/YTD/1Y
WEEKLY_N = 261       # ~5y of weekly candles


def _f(v):
    """'$1,234.56' → 1234.56, or None."""
    try:
        return float(str(v).replace("$", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


def nasdaq_ohlcv(symbol, assetclass, years=5):
    """[(date, close, volume, high, low)] oldest→newest, or None.

    fetch_markets.nasdaq_hist keeps only closes; the same response already
    carries volume and the daily high/low the dashboard needs for its
    day-range and most-active columns, so read them here in one pass.
    """
    frm = (date.today() - timedelta(days=365 * years + 12)).isoformat()
    try:
        r = requests.get(f"https://api.nasdaq.com/api/quote/{symbol}/historical",
                         params={"assetclass": assetclass, "fromdate": frm,
                                 "todate": date.today().isoformat(), "limit": 99999},
                         headers=NH, timeout=TIMEOUT)
        r.raise_for_status()
        rows = ((r.json().get("data") or {}).get("tradesTable") or {}).get("rows") or []
        out = []
        for row in reversed(rows):                       # API is newest→oldest
            c = _f(row.get("close"))
            if c is None:
                continue
            try:
                d = datetime.strptime(row.get("date", ""), "%m/%d/%Y").date().isoformat()
            except ValueError:
                continue
            out.append((d, c, _f(row.get("volume")), _f(row.get("high")), _f(row.get("low"))))
        return out or None
    except Exception as e:
        print(f"  ⚠️  Nasdaq {symbol}: {e}")
        return None


def kraken_ohlc(pair="XBTUSD", interval=1440):
    """[(date, close)] oldest→newest from Kraken's keyless OHLC, or None."""
    try:
        r = requests.get("https://api.kraken.com/0/public/OHLC",
                         params={"pair": pair, "interval": interval}, timeout=TIMEOUT)
        r.raise_for_status()
        j = r.json()
        if j.get("error"):
            return None
        series = next((v for k, v in j.get("result", {}).items() if k != "last"), None)
        if not series:
            return None
        return [(datetime.fromtimestamp(int(c[0]), timezone.utc).date().isoformat(),
                 float(c[4])) for c in series]
    except Exception as e:
        print(f"  ⚠️  Kraken {pair}: {e}")
        return None


def _ytd_pct(dates, closes):
    """% from the last close of the previous year — None if no such close."""
    if not dates or not closes:
        return None
    yr = dates[-1][:4]
    base = None
    for d, c in zip(dates, closes):
        if d[:4] < yr:
            base = c
        else:
            break
    return _pct(closes[-1], base) if base else None


def _quote(sym, name, rows):
    """One watchlist row from an OHLCV series."""
    dates = [r[0] for r in rows]
    closes = [r[1] for r in rows]
    last = closes[-1]
    win52 = [r for r in rows if r[0] >= (date.today() - timedelta(days=365)).isoformat()]
    highs = [r[3] for r in win52 if r[3] is not None] or [max(closes[-252:])]
    lows = [r[4] for r in win52 if r[4] is not None] or [min(closes[-252:])]
    return {
        "sym": sym, "name": name,
        "price": _round_price(last),
        "d1": _pct(last, closes[-2]) if len(closes) > 1 else None,
        "d7": _pct(last, closes[-6]) if len(closes) > 5 else None,
        "d30": _pct(last, closes[-22]) if len(closes) > 21 else None,
        "ytd": _ytd_pct(dates, closes),
        "y1": _pct(last, closes[-253]) if len(closes) > 252 else None,
        "vol": int(rows[-1][2]) if rows[-1][2] else None,
        "day_lo": _round_price(rows[-1][4]) if rows[-1][4] else None,
        "day_hi": _round_price(rows[-1][3]) if rows[-1][3] else None,
        "w52_lo": _round_price(min(lows)),
        "w52_hi": _round_price(max(highs)),
        "asof": dates[-1],
        "spark30": [round(c, 2) for c in closes[-SPARK_N:]],
    }


def build_watchlists():
    prev = load_json("watchlists.json", {})
    prev_q = prev.get("quotes", {})

    universe = {}                     # ticker → display name (first list wins)
    for _k, _n, members in WATCHLISTS:
        for sym, company in members:
            universe.setdefault(sym, company)

    quotes, stale = {}, []
    for i, (sym, company) in enumerate(sorted(universe.items()), 1):
        rows = nasdaq_ohlcv(sym, "stocks", years=2)
        time.sleep(PAUSE)
        if not rows:
            if sym in prev_q:                     # last good, flagged as stale
                quotes[sym] = {**prev_q[sym], "stale": True}
                stale.append(sym)
            continue
        quotes[sym] = _quote(sym, company, rows)
        if i % 10 == 0:
            print(f"  … {i}/{len(universe)}")

    def rank(key, reverse=True, need=None):
        pool = [q for q in quotes.values()
                if q.get(key) is not None and not q.get("stale")]
        pool.sort(key=lambda q: q[key], reverse=reverse)
        return [{"sym": q["sym"], "name": q["name"], "price": q["price"],
                 "d1": q["d1"], "vol": q.get("vol")} for q in pool[:8]]

    return {
        "_note": "Curated watchlists. Quotes: Nasdaq historical (last close, "
                 "daily). Movers are ranked over this list universe only — not "
                 "the whole market.",
        "updated": now_iso(),
        "lists": [{"key": k, "name": n, "tickers": [s for s, _ in m]}
                  for k, n, m in WATCHLISTS],
        "quotes": quotes,
        "stale": stale,
        "movers": {
            "gainers": rank("d1", True),
            "losers": rank("d1", False),
            "active": rank("vol", True),
        },
    }


def build_charts():
    prev = load_json("charts.json", {})
    prev_i = {i["key"]: i for i in prev.get("instruments", [])}

    out = []
    for key, label, sym, ac, note in CHART_INSTRUMENTS:
        daily = weekly = None
        stats = {}
        if ac == "kraken":
            d = kraken_ohlc("XBTUSD", 1440)
            w = kraken_ohlc("XBTUSD", 10080)
            if d:
                daily = {"dates": [x[0] for x in d[-DAILY_N:]],
                         "closes": [round(x[1], 2) for x in d[-DAILY_N:]]}
                closes = [x[1] for x in d]
                stats = {"price": _round_price(closes[-1]),
                         "d1": _pct(closes[-1], closes[-2]) if len(closes) > 1 else None,
                         "day_lo": None, "day_hi": None,
                         "w52_lo": _round_price(min(closes[-365:])),
                         "w52_hi": _round_price(max(closes[-365:])),
                         "vol": None, "asof": d[-1][0]}
            if w:
                weekly = {"dates": [x[0] for x in w[-WEEKLY_N:]],
                          "closes": [round(x[1], 2) for x in w[-WEEKLY_N:]]}
        else:
            rows = nasdaq_ohlcv(sym, ac, years=5)
            time.sleep(PAUSE)
            if rows:
                q = _quote(sym, label, rows)
                daily = {"dates": [r[0] for r in rows[-DAILY_N:]],
                         "closes": [round(r[1], 2) for r in rows[-DAILY_N:]]}
                weekly = {"dates": [r[0] for r in rows[::-5][::-1][-WEEKLY_N:]],
                          "closes": [round(r[1], 2) for r in rows[::-5][::-1][-WEEKLY_N:]]}
                stats = {k: q[k] for k in ("price", "d1", "day_lo", "day_hi",
                                           "w52_lo", "w52_hi", "vol", "asof")}

        if daily:
            out.append({"key": key, "label": label, "proxy": sym, "note": note,
                        "stats": stats, "daily": daily, "weekly": weekly})
        elif key in prev_i:
            out.append({**prev_i[key], "stale": True})

    return {"_note": "Main-chart series. Equity/ETF: Nasdaq historical daily "
                     "closes. Bitcoin: Kraken XBT/USD. Index instruments are "
                     "ETF proxies, labelled as such — no synthetic index level.",
            "updated": now_iso(), "instruments": out}


if __name__ == "__main__":
    print("Fetching watchlists…")
    wl = build_watchlists()
    write_json("watchlists.json", wl)
    print(f"• watchlists: {len(wl['lists'])} lists, {len(wl['quotes'])} quotes"
          + (f", {len(wl['stale'])} stale" if wl["stale"] else ""))

    print("Fetching chart series…")
    ch = build_charts()
    write_json("charts.json", ch)
    print(f"• charts: {len(ch['instruments'])} instruments")
