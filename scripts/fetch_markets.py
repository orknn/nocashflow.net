#!/usr/bin/env python3
"""NoCashFlow · dashboard "the tape" snapshot → data/markets.json

Free, server-side, no API key:
  · equities / ETFs / commodities → Nasdaq historical API (daily 5y history →
    multi-horizon perf + 30-day sparkline). Keyless; replaces Yahoo, which
    blocks GitHub Actions IPs on bulk requests.
  · crypto top-10 + dominance + total mcap → CoinGecko (free; 5Y → "—").
  · stablecoin supply + USDC share          → DefiLlama.
  · FX is frozen (kept from last-good) — no reliable keyless spot+history source.
  · commodities use liquid ETF proxies (USO/BNO/GLD/SLV/CPER/UNG): the move is
    accurate, the printed price is the proxy's.

Resilience: every section falls back to the last-good markets.json on failure.
Run: python3 scripts/fetch_markets.py
"""
import json
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

DATA = Path(__file__).resolve().parent.parent / "data"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}
NH = dict(UA, **{"Accept": "application/json", "Origin": "https://www.nasdaq.com",
                 "Referer": "https://www.nasdaq.com/"})
TIMEOUT = 20
CG = "https://api.coingecko.com/api/v3"

# (yahoo-free) symbol, assetclass, display sym, name
INDICES = [("SPY", "etf", "SPY", "S&P 500"), ("QQQ", "etf", "QQQ", "Nasdaq 100"),
           ("DIA", "etf", "DIA", "Dow Jones"), ("IWM", "etf", "IWM", "Russell 2000"),
           ("VIXY", "etf", "VIX", "Volatility")]
THEMATICS = [("SMH", "Semiconductors"), ("IGV", "Software"), ("QTUM", "Quantum / compute"),
             ("BOTZ", "AI & Robotics"), ("CIBR", "Cybersecurity"), ("XBI", "Biotech")]
FRONTIER = ["IONQ", "RGTI", "QBTS", "QUBT"]                       # stocks
SECTORS = [("XLK", "Technology"), ("XLC", "Comms"), ("XLY", "Discretionary"),
           ("XLI", "Industrials"), ("XLB", "Materials"), ("XLRE", "Real Estate"),
           ("XLP", "Staples"), ("XLV", "Health Care"), ("XLF", "Financials"),
           ("XLU", "Utilities"), ("XLE", "Energy")]
LEADERS_EQ = [("MSFT", "Microsoft"), ("AAPL", "Apple"), ("NVDA", "Nvidia"),
              ("GOOGL", "Alphabet"), ("AMZN", "Amazon"), ("META", "Meta"),
              ("AVGO", "Broadcom"), ("TSLA", "Tesla"), ("COST", "Costco"), ("NFLX", "Netflix")]
COMMODITIES = [("BNO", "Brent"), ("USO", "WTI"), ("GLD", "Gold"),
               ("SLV", "Silver"), ("CPER", "Copper"), ("UNG", "Nat Gas")]
CRYPTO_IDS = ["bitcoin", "ethereum", "tether", "binancecoin", "solana",
              "usd-coin", "ripple", "dogecoin", "cardano", "tron"]
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


def nasdaq_hist(symbol, assetclass, years=5):
    """Daily closes oldest→newest from the Nasdaq historical API, or None."""
    frm = (date.today() - timedelta(days=365 * years + 12)).isoformat()
    try:
        r = requests.get(f"https://api.nasdaq.com/api/quote/{symbol}/historical",
                         params={"assetclass": assetclass, "fromdate": frm,
                                 "todate": date.today().isoformat(), "limit": 99999},
                         headers=NH, timeout=TIMEOUT)
        r.raise_for_status()
        rows = ((r.json().get("data") or {}).get("tradesTable") or {}).get("rows") or []
        closes = []
        for row in reversed(rows):                       # API is newest→oldest
            try:
                closes.append(float(str(row.get("close", "")).replace("$", "").replace(",", "")))
            except ValueError:
                pass
        return closes or None
    except Exception as e:
        print(f"  ⚠️  Nasdaq {symbol}: {e}")
        return None


def _pct(last, old):
    return round((last / old - 1) * 100, 2) if (old and last) else None


def perf(closes):
    last = closes[-1]
    return {k: (_pct(last, closes[-1 - n]) if len(closes) > n else None)
            for k, n in HORIZON.items()}


def _round_price(v):
    if v >= 1000:
        return round(v)
    if v >= 1:
        return round(v, 2)
    return round(v, 4)


def _r(v):
    return round(v, 2) if isinstance(v, (int, float)) else None


def build_markets():
    prev = load_json("markets.json", {})
    pmap = {a["sym"]: a for a in prev.get("leaders_equity", [])}
    out = dict(prev)
    out["_note"] = "Live: equities/ETFs/commodities Nasdaq, crypto CoinGecko " \
                   "(5Y→—), stablecoins DefiLlama. FX frozen; commodities via ETF proxy."
    out["updated"] = now_iso()

    def tile(sym, ac, dsym, name):
        c = nasdaq_hist(sym, ac); time.sleep(0.4)
        if not c:
            return None
        return {"sym": dsym, "name": name, "price": _round_price(c[-1]),
                "d1": _pct(c[-1], c[-2]) if len(c) > 1 else None,
                "spark30": [round(x, 2) for x in c[-30:]]}

    idx = [tile(s, ac, d, n) for s, ac, d, n in INDICES]
    if any(idx):
        out["indices"] = [t for t in idx if t]
    thm = [tile(s, "etf", s, n) for s, n in THEMATICS]
    if any(thm):
        out["thematics"] = [{**t, "note_key": t["sym"].lower()} for t in thm if t]

    fr = []
    for s in FRONTIER:
        c = nasdaq_hist(s, "stocks", years=1); time.sleep(0.4)
        if c and len(c) > 1:
            fr.append({"sym": s, "d1": _pct(c[-1], c[-2])})
    if fr:
        out["frontier"] = fr
    sec = []
    for s, n in SECTORS:
        c = nasdaq_hist(s, "etf", years=1); time.sleep(0.4)
        if c and len(c) > 1:
            sec.append({"sym": s, "name": n, "d1": _pct(c[-1], c[-2])})
    if sec:
        out["sectors"] = sec

    eq = []
    for s, name in LEADERS_EQ:
        c = nasdaq_hist(s, "stocks"); time.sleep(0.4)
        if not c:
            if s in pmap:
                eq.append(pmap[s])
            continue
        eq.append({"sym": s, "name": name, "price": _round_price(c[-1]),
                   "mcap": pmap.get(s, {}).get("mcap", "—"), "perf": perf(c)})
    if eq:
        out["leaders_equity"] = eq

    com = []
    for s, name in COMMODITIES:
        c = nasdaq_hist(s, "etf"); time.sleep(0.4)
        if not c:
            continue
        p = perf(c)
        com.append({"name": name, "price": _round_price(c[-1]),
                    "perf": {k: p[k] for k in ("d1", "d7", "d30", "y1")}})
    if com:
        out["commodities"] = com
    # FX: frozen (kept from last-good) — see module docstring

    # ── crypto (CoinGecko: 1d/7d/30d/200d≈180d/1y; 5Y unavailable free → None) ─
    btc = eth = None
    try:
        r = requests.get(f"{CG}/coins/markets", params={
            "vs_currency": "usd", "ids": ",".join(CRYPTO_IDS), "order": "market_cap_desc",
            "per_page": 20, "page": 1, "price_change_percentage": "24h,7d,30d,200d,1y"},
            headers=UA, timeout=TIMEOUT)
        r.raise_for_status()
        byid = {c["id"]: c for c in r.json()}
        leaders = []
        for cid in CRYPTO_IDS:
            c = byid.get(cid)
            if not c:
                continue
            mc = c.get("market_cap") or 0
            leaders.append({"sym": c["symbol"].upper(), "name": c["name"],
                            "price": _round_price(c["current_price"]),
                            "mcap": f"{mc / 1e12:.2f}T" if mc >= 1e12 else f"{mc / 1e9:.0f}B",
                            "perf": {"d1": _r(c.get("price_change_percentage_24h_in_currency")),
                                     "d7": _r(c.get("price_change_percentage_7d_in_currency")),
                                     "d30": _r(c.get("price_change_percentage_30d_in_currency")),
                                     "d180": _r(c.get("price_change_percentage_200d_in_currency")),
                                     "y1": _r(c.get("price_change_percentage_1y_in_currency")),
                                     "y5": None}})
        if leaders:
            out["leaders_crypto"] = leaders
        btc, eth = byid.get("bitcoin"), byid.get("ethereum")
    except Exception as e:
        print(f"  ⚠️  CoinGecko markets: {e}")

    dom = tot = None
    try:
        g = requests.get(f"{CG}/global", headers=UA, timeout=TIMEOUT).json()["data"]
        dom = round(g["market_cap_percentage"]["btc"], 1)
        tot = f"{g['total_market_cap']['usd'] / 1e12:.2f}T"
    except Exception as e:
        print(f"  ⚠️  CoinGecko global: {e}")

    fng = None
    try:
        d = requests.get("https://api.alternative.me/fng/", params={"limit": 1},
                         headers=UA, timeout=TIMEOUT).json()["data"][0]
        fng = {"v": int(d["value"]), "label": d["value_classification"]}
    except Exception as e:
        print(f"  ⚠️  Fear&Greed: {e}")

    stables = usdc_share = None
    try:
        pa = requests.get("https://stablecoins.llama.fi/stablecoins?includePrices=false",
                          headers=UA, timeout=TIMEOUT).json()["peggedAssets"]
        total = sum((a.get("circulating", {}) or {}).get("peggedUSD", 0) or 0 for a in pa)
        usdc = next(((a.get("circulating", {}) or {}).get("peggedUSD", 0) for a in pa if a.get("symbol") == "USDC"), 0)
        if total:
            stables, usdc_share = f"{total / 1e9:.0f}B", round(usdc / total * 100, 1)
    except Exception as e:
        print(f"  ⚠️  DefiLlama: {e}")

    # hero + crypto board (carry last-good for any missing piece)
    ph = prev.get("hero", {})
    hero = dict(ph)
    if btc:
        hero["btc"] = {"px": _round_price(btc["current_price"]), "chg": _r(btc.get("price_change_percentage_24h_in_currency")) or 0}
    if eth:
        hero["eth"] = {"px": _round_price(eth["current_price"]), "chg": _r(eth.get("price_change_percentage_24h_in_currency")) or 0}
    spx_t = next((t for t in out.get("indices", []) if t["sym"] == "SPY"), None)
    if spx_t:
        hero["spx"] = {"px": spx_t["price"], "chg": spx_t["d1"] or 0}
    gold_t = next((r for r in out.get("commodities", []) if r["name"] == "Gold"), None)
    if gold_t:
        hero["gold"] = {"px": gold_t["price"], "chg": gold_t["perf"]["d1"] or 0}
    if fng:
        hero["fng"] = fng
    if dom is not None:
        pdv = (ph.get("btc_dom", {}) or {}).get("v")
        hero["btc_dom"] = {"v": dom, "chg_pp": round(dom - pdv, 1) if pdv else 0}
    out["hero"] = hero

    pcb = prev.get("crypto_board", {})
    board = dict(pcb)
    if tot:
        board["total_mcap"] = {"v": tot, "chg": pcb.get("total_mcap", {}).get("chg", 0)}
    if dom is not None:
        board["btc_dom"] = hero.get("btc_dom", board.get("btc_dom", {}))
    if stables:
        board["stables"] = {"v": stables, "chg": pcb.get("stables", {}).get("chg", 0)}
    if usdc_share is not None:
        board["usdc_share"] = {"v": usdc_share, "chg_pp": 0}
    out["crypto_board"] = board
    return out


if __name__ == "__main__":
    print("Fetching dashboard markets snapshot…")
    data = build_markets()
    write_json("markets.json", data)
    print(f"• markets: {len(data.get('leaders_equity', []))} equity, "
          f"{len(data.get('leaders_crypto', []))} crypto, {len(data.get('sectors', []))} sectors, "
          f"{len(data.get('commodities', []))} commodities")
