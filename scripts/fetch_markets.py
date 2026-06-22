#!/usr/bin/env python3
"""NoCashFlow · dashboard "the tape" snapshot → data/markets.json

Free, server-side, no API key:
  · equities / ETFs / commodities / FX  → Yahoo chart API (daily history →
    multi-horizon perf + 30-day sparkline). Replaces Stooq (now JS-gated).
  · crypto top-10 + dominance + total mcap → CoinGecko (free).
  · stablecoin supply + USDC share         → DefiLlama.
  · Crypto 5Y is unavailable on CoinGecko's free tier (365-day cap) → "—".

Resilience: every section falls back to the last-good markets.json on failure,
so a flaky source never blanks the page. Run: python3 scripts/fetch_markets.py
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

DATA = Path(__file__).resolve().parent.parent / "data"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}
TIMEOUT = 15
CG = "https://api.coingecko.com/api/v3"

INDICES = [("SPY", "SPY", "S&P 500"), ("QQQ", "QQQ", "Nasdaq 100"),
           ("DIA", "DIA", "Dow Jones"), ("IWM", "IWM", "Russell 2000"),
           ("^VIX", "VIX", "Volatility")]
THEMATICS = [("SMH", "Semiconductors"), ("IGV", "Software"), ("QTUM", "Quantum / compute"),
             ("BOTZ", "AI & Robotics"), ("CIBR", "Cybersecurity"), ("XBI", "Biotech")]
FRONTIER = ["IONQ", "RGTI", "QBTS", "QUBT"]
SECTORS = [("XLK", "Technology"), ("XLC", "Comms"), ("XLY", "Discretionary"),
           ("XLI", "Industrials"), ("XLB", "Materials"), ("XLRE", "Real Estate"),
           ("XLP", "Staples"), ("XLV", "Health Care"), ("XLF", "Financials"),
           ("XLU", "Utilities"), ("XLE", "Energy")]
LEADERS_EQ = [("MSFT", "Microsoft"), ("AAPL", "Apple"), ("NVDA", "Nvidia"),
              ("GOOGL", "Alphabet"), ("AMZN", "Amazon"), ("META", "Meta"),
              ("AVGO", "Broadcom"), ("TSLA", "Tesla"), ("COST", "Costco"), ("NFLX", "Netflix")]
COMMODITIES = [("BZ=F", "Brent"), ("CL=F", "WTI"), ("GC=F", "Gold"),
               ("SI=F", "Silver"), ("HG=F", "Copper"), ("NG=F", "Nat Gas")]
FX = [("DX-Y.NYB", "DXY"), ("EURUSD=X", "EUR/USD"), ("JPY=X", "USD/JPY"),
      ("GBPUSD=X", "GBP/USD"), ("TRY=X", "USD/TRY"), ("CHF=X", "USD/CHF")]
CRYPTO_IDS = ["bitcoin", "ethereum", "tether", "binancecoin", "solana",
              "usd-coin", "ripple", "dogecoin", "cardano", "tron"]
# trading-day offsets for each horizon (Yahoo daily closes skip weekends/holidays)
HORIZON = {"d1": 1, "d7": 5, "d30": 21, "d180": 126, "y1": 252, "y5": 1260}


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(name, default):
    p = DATA / name
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default


def write_json(name, obj):
    (DATA / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")


def yahoo_hist(symbol, rng="5y", retries=4):
    """Daily closes oldest→newest, or None. Retries with backoff on 429 — Yahoo
    rate-limits bursts per IP, so we back off rather than give up."""
    for attempt in range(retries):
        try:
            r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                             params={"interval": "1d", "range": rng}, headers=UA, timeout=TIMEOUT)
            if r.status_code == 429:
                time.sleep(10 * (attempt + 1))  # 10, 20, 30, 40s
                continue
            r.raise_for_status()
            q = r.json()["chart"]["result"][0]["indicators"]["quote"][0]["close"]
            closes = [c for c in q if c is not None]
            return closes or None
        except Exception as e:
            if attempt == retries - 1:
                print(f"  ⚠️  Yahoo {symbol}: {e}")
                return None
            time.sleep(5)
    print(f"  ⚠️  Yahoo {symbol}: still 429 after {retries} tries")
    return None


def _pct(last, old):
    return round((last / old - 1) * 100, 2) if (old and last) else None


def perf(closes):
    last = closes[-1]
    out = {}
    for k, n in HORIZON.items():
        out[k] = _pct(last, closes[-1 - n]) if len(closes) > n else None
    return out


def _round_price(v):
    if v >= 1000:
        return round(v)
    if v >= 1:
        return round(v, 2)
    return round(v, 4)


def yahoo_mcap(symbols):
    """Best-effort market caps via Yahoo quoteSummary; missing → None (keep last-good)."""
    out = {}
    for s in symbols:
        try:
            r = requests.get(f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{s}",
                             params={"modules": "price"}, headers=UA, timeout=TIMEOUT)
            mc = r.json()["quoteSummary"]["result"][0]["price"]["marketCap"]["raw"]
            out[s] = f"{mc / 1e12:.2f}T" if mc >= 1e12 else f"{mc / 1e9:.0f}B"
        except Exception:
            out[s] = None
        time.sleep(0.2)
    return out


def build_markets():
    prev = load_json("markets.json", {})
    pmap = {}  # last-good helpers keyed by symbol/name for graceful fallback
    for a in prev.get("leaders_equity", []):
        pmap[a["sym"]] = a

    def tile(ysym, dsym, name, rng="6mo"):
        closes = yahoo_hist(ysym, rng)
        time.sleep(0.3)
        if not closes:
            return None
        return {"sym": dsym, "name": name, "price": _round_price(closes[-1]),
                "d1": _pct(closes[-1], closes[-2]) if len(closes) > 1 else None,
                "spark30": [round(c, 2) for c in closes[-30:]]}

    out = dict(prev)  # start from last-good; overwrite what we successfully fetch
    out["_note"] = "Live snapshot. Equities/ETFs/commodities/FX: Yahoo. " \
                   "Crypto: CoinGecko (5Y unavailable on free tier → —). Stablecoins: DefiLlama."
    out["updated"] = now_iso()

    # indices + thematics (tiles with sparkline)
    idx = [tile(y, d, n) for y, d, n in INDICES]
    if any(idx):
        out["indices"] = [t for t in idx if t]
    thm = [tile(y, y, n) for y, n in THEMATICS]
    if any(thm):
        out["thematics"] = [{**t, "note_key": t["sym"].lower()} for t in thm if t]

    # frontier + sectors (1-day move only)
    fr = []
    for s in FRONTIER:
        c = yahoo_hist(s, "5d"); time.sleep(0.25)
        if c and len(c) > 1:
            fr.append({"sym": s, "d1": _pct(c[-1], c[-2])})
    if fr:
        out["frontier"] = fr
    sec = []
    for s, n in SECTORS:
        c = yahoo_hist(s, "5d"); time.sleep(0.25)
        if c and len(c) > 1:
            sec.append({"sym": s, "name": n, "d1": _pct(c[-1], c[-2])})
    if sec:
        out["sectors"] = sec

    # equity leaders (full perf; mcap carried from last-good — slow-moving, and
    # it spares 10 Yahoo calls that would trip the rate limit)
    eq = []
    for s, name in LEADERS_EQ:
        c = yahoo_hist(s, "5y"); time.sleep(0.5)
        if not c:
            if s in pmap:
                eq.append(pmap[s])  # keep last-good row
            continue
        eq.append({"sym": s, "name": name, "price": _round_price(c[-1]),
                   "mcap": pmap.get(s, {}).get("mcap", "—"), "perf": perf(c)})
    if eq:
        out["leaders_equity"] = eq

    # commodities + fx
    def perf_row(ysym, name):
        c = yahoo_hist(ysym, "1y"); time.sleep(0.3)
        if not c:
            return None
        p = perf(c)
        return {"name": name, "price": _round_price(c[-1]),
                "perf": {k: p[k] for k in ("d1", "d7", "d30", "y1")}}

    com = [perf_row(y, n) for y, n in COMMODITIES]
    if any(com):
        out["commodities"] = [r for r in com if r]
    fx = [perf_row(y, n) for y, n in FX]
    if any(fx):
        out["fx"] = [r for r in fx if r]

    # crypto: CoinGecko markets (1d/7d/30d/200d≈180d/1y; 5Y unavailable free → None)
    try:
        r = requests.get(f"{CG}/coins/markets", params={
            "vs_currency": "usd", "ids": ",".join(CRYPTO_IDS), "order": "market_cap_desc",
            "per_page": 20, "page": 1,
            "price_change_percentage": "24h,7d,30d,200d,1y"}, headers=UA, timeout=TIMEOUT)
        r.raise_for_status()
        byid = {c["id"]: c for c in r.json()}
        leaders = []
        for cid in CRYPTO_IDS:
            c = byid.get(cid)
            if not c:
                continue
            mc = c.get("market_cap") or 0
            leaders.append({
                "sym": c["symbol"].upper(), "name": c["name"],
                "price": _round_price(c["current_price"]),
                "mcap": f"{mc / 1e12:.2f}T" if mc >= 1e12 else f"{mc / 1e9:.0f}B",
                "perf": {
                    "d1": _r(c.get("price_change_percentage_24h_in_currency")),
                    "d7": _r(c.get("price_change_percentage_7d_in_currency")),
                    "d30": _r(c.get("price_change_percentage_30d_in_currency")),
                    "d180": _r(c.get("price_change_percentage_200d_in_currency")),
                    "y1": _r(c.get("price_change_percentage_1y_in_currency")),
                    "y5": None}})
        if leaders:
            out["leaders_crypto"] = leaders
        # hero crypto + F&G + dominance pulled below from the same data
        btc, eth = byid.get("bitcoin"), byid.get("ethereum")
    except Exception as e:
        print(f"  ⚠️  CoinGecko markets: {e}")
        btc = eth = None

    # /global dominance + total mcap
    dom = tot = None
    try:
        g = requests.get(f"{CG}/global", headers=UA, timeout=TIMEOUT).json()["data"]
        dom = round(g["market_cap_percentage"]["btc"], 1)
        tot = f"{g['total_market_cap']['usd'] / 1e12:.2f}T"
    except Exception as e:
        print(f"  ⚠️  CoinGecko global: {e}")

    # Fear & Greed
    fng = None
    try:
        d = requests.get("https://api.alternative.me/fng/", params={"limit": 1},
                         headers=UA, timeout=TIMEOUT).json()["data"][0]
        fng = {"v": int(d["value"]), "label": d["value_classification"]}
    except Exception as e:
        print(f"  ⚠️  Fear&Greed: {e}")

    # stablecoins (DefiLlama)
    stables = usdc_share = None
    try:
        pa = requests.get("https://stablecoins.llama.fi/stablecoins?includePrices=false",
                          headers=UA, timeout=20).json()["peggedAssets"]
        def circ(a):
            return (a.get("circulating", {}) or {}).get("peggedUSD", 0) or 0
        total = sum(circ(a) for a in pa)
        usdc = next((circ(a) for a in pa if a.get("symbol") == "USDC"), 0)
        if total:
            stables = f"{total / 1e9:.0f}B"
            usdc_share = round(usdc / total * 100, 1)
    except Exception as e:
        print(f"  ⚠️  DefiLlama: {e}")

    # hero (carry last-good for any missing piece)
    ph = prev.get("hero", {})
    hero = dict(ph)
    if btc:
        hero["btc"] = {"px": _round_price(btc["current_price"]),
                       "chg": _r(btc.get("price_change_percentage_24h_in_currency")) or 0}
    if eth:
        hero["eth"] = {"px": _round_price(eth["current_price"]),
                       "chg": _r(eth.get("price_change_percentage_24h_in_currency")) or 0}
    spx_t = next((t for t in out.get("indices", []) if t["sym"] == "SPY"), None)
    if spx_t:
        hero["spx"] = {"px": spx_t["price"], "chg": spx_t["d1"] or 0}
    gold_t = next((r for r in out.get("commodities", []) if r["name"] == "Gold"), None)
    if gold_t:
        hero["gold"] = {"px": gold_t["price"], "chg": gold_t["perf"]["d1"] or 0}
    if fng:
        hero["fng"] = fng
    if dom is not None:
        pd = (ph.get("btc_dom", {}) or {}).get("v")
        hero["btc_dom"] = {"v": dom, "chg_pp": round(dom - pd, 1) if pd else 0}
    out["hero"] = hero

    # crypto board
    pcb = prev.get("crypto_board", {})
    board = dict(pcb)
    if tot:
        pv = (pcb.get("total_mcap", {}) or {}).get("v")
        board["total_mcap"] = {"v": tot, "chg": pcb.get("total_mcap", {}).get("chg", 0)}
    if dom is not None:
        board["btc_dom"] = hero.get("btc_dom", board.get("btc_dom", {}))
    if stables:
        board["stables"] = {"v": stables, "chg": pcb.get("stables", {}).get("chg", 0)}
    if usdc_share is not None:
        board["usdc_share"] = {"v": usdc_share, "chg_pp": 0}
    out["crypto_board"] = board

    return out


def _r(v):
    return round(v, 2) if isinstance(v, (int, float)) else None


if __name__ == "__main__":
    print("Fetching dashboard markets snapshot…")
    data = build_markets()
    write_json("markets.json", data)
    print(f"• markets: {len(data.get('leaders_equity', []))} equity, "
          f"{len(data.get('leaders_crypto', []))} crypto, "
          f"{len(data.get('sectors', []))} sectors written")
