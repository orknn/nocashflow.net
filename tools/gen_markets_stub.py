#!/usr/bin/env python3
"""Phase-1 WIRING STUB generator for data/markets.json.

Values are carried over from dashboard-demo.html (clearly sample data, used
only to prove the dashboard wiring locally). Real data arrives in Phase 4
(Stooq / CoinGecko / DefiLlama / FRED). NOT for live deploy.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def spark(price, d1, n=30):
    """Synthesize n daily closes ending at `price`, trending per the sign of d1.
    Stub only — Phase 4 writes the real last-30 closes."""
    drift = (d1 / 100.0) * price * 0.9          # rough 30d drift in price terms
    start = price - drift
    out = []
    for i in range(n):
        t = i / (n - 1)
        base = start + (price - start) * t
        wobble = math.sin(i * 1.7) * price * 0.004
        out.append(round(base + wobble, 2))
    return out


def idx(sym, name, price, d1):
    return {"sym": sym, "name": name, "price": price, "d1": d1, "spark30": spark(price, d1)}


def thm(sym, name, price, d1, note_key):
    return {"sym": sym, "name": name, "price": price, "d1": d1,
            "spark30": spark(price, d1), "note_key": note_key}


def eq(sym, name, price, mcap, d1, d7, d30, d180, y1, y5):
    return {"sym": sym, "name": name, "price": price, "mcap": mcap,
            "perf": {"d1": d1, "d7": d7, "d30": d30, "d180": d180, "y1": y1, "y5": y5}}


data = {
    "_note": "PHASE-1 WIRING STUB — sample values from dashboard-demo.html. "
             "Not real, not for live deploy. Replaced by automation in Phase 4.",
    "updated": "2026-06-23T09:14:00Z",
    "hero": {
        "btc": {"px": 64398, "chg": 0.67}, "eth": {"px": 3402, "chg": 1.12},
        "spx": {"px": 5488, "chg": -0.41}, "gold": {"px": 2388, "chg": 0.31},
        "fng": {"v": 20, "label": "Ext. Fear"}, "btc_dom": {"v": 54.2, "chg_pp": 0.3},
    },
    "indices": [
        idx("SPY", "S&P 500", 548.0, -0.41), idx("QQQ", "Nasdaq 100", 478.6, -0.58),
        idx("DIA", "Dow Jones", 392.1, 0.12), idx("IWM", "Russell 2000", 201.4, -1.08),
        idx("VIX", "Volatility", 17.28, 5.37),
    ],
    "thematics": [
        thm("SMH", "Semiconductors", 262.4, 1.34, "smh"),
        thm("IGV", "Software", 92.1, -0.72, "igv"),
        thm("QTUM", "Quantum / compute", 88.6, 2.41, "qtum"),
        thm("BOTZ", "AI & Robotics", 34.8, 0.91, "botz"),
        thm("CIBR", "Cybersecurity", 68.2, 0.44, "cibr"),
        thm("XBI", "Biotech", 91.5, -0.83, "xbi"),
    ],
    "frontier": [
        {"sym": "IONQ", "d1": 4.2}, {"sym": "RGTI", "d1": 6.8},
        {"sym": "QBTS", "d1": -3.1}, {"sym": "QUBT", "d1": 5.5},
    ],
    "sectors": [
        {"sym": "XLK", "name": "Technology", "d1": 1.1}, {"sym": "XLC", "name": "Comms", "d1": 0.7},
        {"sym": "XLY", "name": "Discretionary", "d1": 0.3}, {"sym": "XLI", "name": "Industrials", "d1": 0.1},
        {"sym": "XLB", "name": "Materials", "d1": 0.0}, {"sym": "XLRE", "name": "Real Estate", "d1": -0.2},
        {"sym": "XLP", "name": "Staples", "d1": -0.3}, {"sym": "XLV", "name": "Health Care", "d1": -0.5},
        {"sym": "XLF", "name": "Financials", "d1": -0.6}, {"sym": "XLU", "name": "Utilities", "d1": -0.9},
        {"sym": "XLE", "name": "Energy", "d1": -1.6},
    ],
    "crypto_board": {
        "total_mcap": {"v": "2.28T", "chg": 0.8}, "btc_dom": {"v": 54.2, "chg_pp": 0.3},
        "stables": {"v": "248B", "chg": 2.4}, "usdc_share": {"v": 24.6, "chg_pp": 0.5},
        "funding": {"v": 0.009},
    },
    "leaders_equity": [
        eq("MSFT", "Microsoft", 478.2, "3.55T", 0.4, 2.1, 5.8, 14.2, 28.4, 142),
        eq("AAPL", "Apple", 224.6, "3.42T", -0.3, -1.2, 3.4, 9.1, 16.2, 108),
        eq("NVDA", "Nvidia", 134.8, "3.31T", 1.9, 6.4, 18.7, 52.3, 118.6, 1820),
        eq("GOOGL", "Alphabet", 178.4, "2.20T", -0.6, 1.8, 7.2, 21.4, 42.1, 124),
        eq("AMZN", "Amazon", 192.3, "2.01T", 0.2, 2.9, 6.1, 18.0, 34.7, 86),
        eq("META", "Meta", 512.7, "1.30T", -0.9, 0.4, 9.3, 27.6, 61.3, 178),
        eq("AVGO", "Broadcom", 168.5, "0.79T", 1.4, 4.7, 12.5, 38.9, 89.2, 540),
        eq("TSLA", "Tesla", 218.9, "0.70T", -1.7, -4.2, -8.6, -16.2, -24.8, 24),
        eq("COST", "Costco", 882.1, "0.39T", 0.1, 1.1, 3.2, 11.7, 29.5, 168),
        eq("NFLX", "Netflix", 685.3, "0.29T", -0.4, 2.3, 6.9, 24.1, 58.9, 96),
    ],
    "leaders_crypto": [
        eq("BTC", "Bitcoin", 64398, "1.27T", 0.7, 3.2, -4.1, 8.6, 12.4, 84),
        eq("ETH", "Ethereum", 3402, "410B", 1.1, 4.8, -2.3, 12.4, -2.1, 38),
        eq("USDT", "Tether", 1.000, "148B", 0, 0, 0, 0, 0, 0),
        eq("BNB", "BNB", 612.4, "89B", 0.5, 2.1, 6.4, 18.9, 8.6, 104),
        eq("SOL", "Solana", 148.2, "70B", 2.3, 8.7, -6.2, 34.1, 18.3, 292),
        eq("USDC", "USD Coin", 1.000, "61B", 0, 0, 0, 0, 0, 0),
        eq("XRP", "XRP", 0.624, "35B", -0.8, -3.4, -9.1, 5.2, 32.4, -31),
        eq("DOGE", "Dogecoin", 0.138, "20B", 1.1, 5.6, -12.3, -8.4, -28.6, -54),
        eq("ADA", "Cardano", 0.462, "16B", -0.5, -2.1, -7.8, -3.2, -15.2, -69),
        eq("TRX", "Tron", 0.162, "14B", 0.3, 1.2, 4.5, 14.7, 42.8, 128),
    ],
    "commodities": [
        {"name": "Brent", "price": 78.0, "perf": {"d1": -2.33, "d7": -4.1, "d30": 3.2, "y1": 18.2}},
        {"name": "WTI", "price": 74.6, "perf": {"d1": -2.51, "d7": -4.4, "d30": 2.9, "y1": 16.4}},
        {"name": "Gold", "price": 2388, "perf": {"d1": 0.31, "d7": 1.8, "d30": 4.2, "y1": 24.6}},
        {"name": "Silver", "price": 29.4, "perf": {"d1": 0.62, "d7": 3.1, "d30": 6.8, "y1": 31.2}},
        {"name": "Copper", "price": 4.42, "perf": {"d1": -0.44, "d7": -1.2, "d30": 2.1, "y1": 12.4}},
        {"name": "Nat Gas", "price": 2.78, "perf": {"d1": 1.20, "d7": -3.4, "d30": -8.2, "y1": -22.4}},
    ],
    "fx": [],   # frozen — no reliable keyless FX spot+history source yet
}

out = ROOT / "data" / "markets.json"
out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"wrote {out} ({len(data['indices'])} idx, {len(data['leaders_equity'])} eq, "
      f"{len(data['leaders_crypto'])} crypto)")
