#!/usr/bin/env python3
"""NoCashFlow · dashboard "the tape" snapshot → data/markets.json

Free, server-side, no API key:
  · equities / ETFs → Nasdaq historical API (daily 5y history → multi-horizon
    perf + 30-day sparkline). Keyless; replaces Yahoo, which blocks Actions IPs.
  · crypto top-10 + dominance + total mcap → CoinGecko (free; 1d/7d/30d/180d/1y).
    5Y comes from Kraken's public weekly OHLC instead (CoinGecko's free tier
    caps history at 365d; Binance has it but 451s from Actions IPs) — "—" if
    a coin has no Kraken pair or under ~5y of listed history.
  · stablecoin supply + USDC share          → DefiLlama.
  · FX (EUR/USD, USD/JPY, GBP/USD, USD/CHF, USD/TRY) → frankfurter.app (ECB,
    keyless, with history → perf). DXY is dropped (no keyless ICE-DXY history).
  · commodities: Brent/WTI/NatGas → FRED spot; Gold/Silver → gold-api.com spot
    (perf from GLD/SLV ETF history); Copper/Cocoa/Coffee read from the daily
    bulletin's committed output (it already fetches HG=F/CC=F/KC=F) — 1D/1W/30D.

Resilience: every section falls back to the last-good markets.json on failure.
Run: python3 scripts/fetch_markets.py
"""
import csv
import io
import json
import re
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
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"
# FRED's graph-CSV endpoint stalls on a full browser UA (the Nasdaq one); it
# serves a plain custom UA fine — same UA fetch_macro2 uses successfully in CI.
FRED_UA = {"User-Agent": "Mozilla/5.0 (NoCashFlow data fetcher)"}
# FX: display name, frankfurter currency (base USD), invert? (True → X/USD)
FX_PAIRS = [("EUR/USD", "EUR", True), ("USD/JPY", "JPY", False),
            ("GBP/USD", "GBP", True), ("USD/CHF", "CHF", False),
            ("USD/TRY", "TRY", False)]
CRYPTO_IDS = ["bitcoin", "ethereum", "tether", "binancecoin", "solana",
              "usd-coin", "ripple", "dogecoin", "cardano", "tron"]
# 5Y crypto perf: CoinGecko's free tier caps history at 365 days. Binance has
# the full history but 451s from GitHub Actions IPs (geo-restricted, same
# issue Yahoo had). Kraken's public OHLC endpoint is keyless, unrestricted
# from Actions, and returns enough weekly history in one call.
KRAKEN_PAIR = {"bitcoin": "XBTUSD", "ethereum": "ETHUSD", "tether": "USDTZUSD",
               "binancecoin": "BNBUSD", "solana": "SOLUSD", "usd-coin": "USDCUSD",
               "ripple": "XRPUSD", "dogecoin": "DOGEUSD", "cardano": "ADAUSD",
               "tron": "TRXUSD"}
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


def kraken_5y_pct(coin_id):
    """Real 5Y % change for a crypto id via Kraken's public (keyless) weekly
    OHLC — None if the pair is unknown, unreachable, or has under ~5y of
    history (no fabricated numbers)."""
    pair = KRAKEN_PAIR.get(coin_id)
    if not pair:
        return None
    try:
        r = requests.get("https://api.kraken.com/0/public/OHLC",
                          params={"pair": pair, "interval": 10080}, timeout=TIMEOUT)
        r.raise_for_status()
        j = r.json()
        if j.get("error"):
            return None
        series = next((v for k, v in j.get("result", {}).items() if k != "last"), None)
        if not series or len(series) < 261:  # ~5y of weekly candles
            return None
        old, last = float(series[-261][4]), float(series[-1][4])
        return round((last - old) / old * 100, 2) if old else None
    except Exception:
        return None


def fred_closes(series_id, days=460):
    """Daily observations oldest→newest from FRED ('.' gaps dropped), or None.
    Retries once — FRED can be slow to first-byte."""
    frm = (date.today() - timedelta(days=days)).isoformat()
    for attempt in (1, 2, 3):
        try:
            r = requests.get(FRED_CSV, params={"id": series_id, "cosd": frm},
                             headers=FRED_UA, timeout=TIMEOUT)
            r.raise_for_status()
            out = []
            for row in csv.reader(io.StringIO(r.text)):
                if len(row) < 2:
                    continue
                try:
                    out.append(float(row[1]))   # header's 2nd cell isn't a float → skipped
                except ValueError:
                    pass
            return out or None
        except Exception as e:
            if attempt == 3:
                print(f"  ⚠️  FRED {series_id}: {e}")
                return None
            time.sleep(2 * attempt)


def gold_api(metal):
    """Current spot ($/oz) from gold-api.com (XAU/XAG), or None."""
    try:
        r = requests.get(f"https://api.gold-api.com/price/{metal}", headers=UA, timeout=TIMEOUT)
        r.raise_for_status()
        return float(r.json()["price"])
    except Exception as e:
        print(f"  ⚠️  gold-api {metal}: {e}")
        return None


def _fx_round(v):
    return round(v, 4) if v < 10 else round(v, 2)


def build_fx():
    """EUR/USD, USD/JPY, GBP/USD, USD/CHF, USD/TRY from frankfurter.app (ECB),
    native symbols, perf computed from ~1y of business-day history."""
    frm = (date.today() - timedelta(days=460)).isoformat()
    try:
        r = requests.get(f"https://api.frankfurter.app/{frm}..{date.today().isoformat()}",
                         params={"from": "USD", "to": ",".join(c for _, c, _ in FX_PAIRS)},
                         headers=UA, timeout=TIMEOUT)
        r.raise_for_status()
        rates = r.json().get("rates", {})          # {date: {CUR: rate}}
    except Exception as e:
        print(f"  ⚠️  frankfurter FX: {e}")
        return None
    days = sorted(rates)
    rows = []
    for name, cur, inv in FX_PAIRS:
        series = []
        for d in days:
            v = rates[d].get(cur)
            if v:
                series.append(1.0 / v if inv else v)
        if len(series) < 30:
            continue
        p = perf(series)
        rows.append({"name": name, "price": _fx_round(series[-1]),
                     "perf": {k: p[k] for k in ("d1", "d7", "d30", "y1")}})
    return rows or None


def bulletin_commodities():
    """Copper / Cocoa / Coffee from the latest daily bulletin. The bulletin's own
    pipeline already fetches HG=F/CC=F/KC=F (Yahoo); we read its committed output
    rather than re-fetch — robust and offline. Price + 1D/1W/30D, no 1Y."""
    f = DATA.parent / "bulletins" / "daily" / "latest.en.html"
    try:
        html = f.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  ⚠️  bulletin read: {e}")
        return {}
    out = {}
    # row: <strong …>CODE</strong> … <td …>$price</td> + three <td>↕ ±x%</td>
    cell = r'<td class="mono[^"]*"[^>]*>[^<]*?(-?\d[\d,]*\.?\d*)%</td>\s*'
    for code, label in (("HG", "Copper · HG"), ("CC", "Cocoa · CC"), ("KC", "Coffee · KC")):
        m = re.search(
            r'<strong[^>]*>' + code + r'</strong>.*?'
            r'<td class="mono"[^>]*>\$?([\d,]+\.?\d*)</td>\s*' + cell + cell + cell,
            html, re.DOTALL)
        if not m:
            continue
        price = float(m.group(1).replace(",", ""))
        d1, d7, d30 = (float(m.group(i).replace(",", "")) for i in (2, 3, 4))
        out[label] = {"name": label, "price": _round_price(price),
                      "perf": {"d1": d1, "d7": d7, "d30": d30, "y1": None}}
    return out


def build_markets():
    prev = load_json("markets.json", {})
    pmap = {a["sym"]: a for a in prev.get("leaders_equity", [])}
    out = dict(prev)
    out["_note"] = "Live: equities/ETFs Nasdaq, crypto CoinGecko (5Y→—), " \
                   "stablecoins DefiLlama, oil/gas FRED, metals gold-api, " \
                   "copper/cocoa/coffee via daily bulletin, FX frankfurter (ECB)."
    out["updated"] = now_iso()

    # FRED commodity spot up front, on fresh connections — the graph-CSV endpoint
    # gets flaky deep into a long run of Nasdaq calls.
    fred_spot = {}
    for _nm, _sid in (("Brent", "DCOILBRENTEU"), ("WTI", "DCOILWTICO"), ("NatGas", "DHHNGSP")):
        fred_spot[_nm] = fred_closes(_sid)
        time.sleep(0.5)

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

    # ── commodities: real spot, native labels (last-good per row on failure) ──
    com = []
    prev_com = {r.get("name"): r for r in prev.get("commodities", [])}

    def _add(name, price, closes):
        """price=spot, closes=history for perf. Falls back to last-good row."""
        if price is None or not closes:
            if name in prev_com:
                com.append(prev_com[name])
            return
        p = perf(closes)
        com.append({"name": name, "price": _round_price(price),
                    "perf": {k: p[k] for k in ("d1", "d7", "d30", "y1")}})

    brent = fred_spot.get("Brent")
    _add("Brent", brent[-1] if brent else None, brent)
    wti = fred_spot.get("WTI")
    _add("WTI", wti[-1] if wti else None, wti)
    ng = fred_spot.get("NatGas")
    _add("NatGas", ng[-1] if ng else None, ng)
    gld = nasdaq_hist("GLD", "etf"); time.sleep(0.4)
    _add("XAU/USD", gold_api("XAU"), gld)            # real spot price, perf via GLD
    slv = nasdaq_hist("SLV", "etf"); time.sleep(0.4)
    _add("XAG/USD", gold_api("XAG"), slv)            # real spot price, perf via SLV
    # Copper / Cocoa / Coffee — read from the daily bulletin (it already fetches
    # HG=F/CC=F/KC=F via Yahoo). Real HG replaces the CPER ETF; 1D/1W/30D, no 1Y.
    bull = bulletin_commodities()
    for label in ("Copper · HG", "Cocoa · CC", "Coffee · KC"):
        if label in bull:
            com.append(bull[label])
        elif label in prev_com:
            com.append(prev_com[label])
    if com:
        out["commodities"] = com

    # ── FX: frankfurter.app (ECB), native symbols, perf from history ──────────
    fx = build_fx()
    if fx:
        out["fx"] = fx
    elif prev.get("fx"):
        out["fx"] = prev["fx"]

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
                                     "y5": kraken_5y_pct(cid)}})
            time.sleep(0.3)
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
    gold_t = next((r for r in out.get("commodities", []) if r["name"] == "XAU/USD"), None)
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
