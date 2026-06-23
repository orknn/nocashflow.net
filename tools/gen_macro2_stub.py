#!/usr/bin/env python3
"""Phase-2 WIRING STUB for data/macro2.json (the macro "regime" page feed).

Values carried over from macro-demo.html — clearly sample, local wiring proof
only. Real data (FRED / Atlanta Fed GDPNow / manual ISM + cut-odds) lands in
Phase 4. Stat labels live in build.py (translated); this file carries only the
values, short sub-descriptors and a colour direction per stat. Editorial read /
note text lives in the human-committed macro-notes.json, NOT here.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def st(v, sub="", dir="neu"):
    return {"v": v, "sub": sub, "dir": dir}


data = {
    "_note": "PHASE-2 WIRING STUB — sample values from macro-demo.html. Not real, "
             "not for live deploy. Replaced by automation in Phase 4.",
    "updated": "2026-06-23T08:00:00Z",
    "regime_tape": [
        {"k": "Fed Funds", "v": "4.25–4.50", "d": "held", "dir": "neu"},
        {"k": "Next FOMC", "v": "Jul 29", "d": "37d", "dir": "neu"},
        {"k": "Cut odds (Jul)", "v": "22%", "d": "▲ from 14%", "dir": "up"},
        {"k": "Core CPI", "v": "3.1%", "d": "▲ sticky", "dir": "down"},
        {"k": "US 10Y", "v": "4.51", "d": "+1.30%", "dir": "up"},
        {"k": "2s10s", "v": "+27", "d": "steepening", "dir": "up"},
        {"k": "DXY", "v": "101.0", "d": "+0.16%", "dir": "up"},
        {"k": "F&amp;G", "v": "20", "d": "Extreme Fear", "dir": "down"},
    ],
    # §01 Inflation — 4 stats (labels in template, order fixed)
    "inflation": [
        st("2.6%", "▼ from 2.8%", "up"), st("3.1%", "▲ flat 3m", "down"),
        st("2.8%", "→ unchanged", "neu"), st("2.34%", "▲ +6bp", "up"),
    ],
    # §02 Fed — cut-odds bars + 4 stats
    "fed": {
        "cut_odds": [
            {"m": "Jul 29", "p": 22}, {"m": "Sep 16", "p": 48},
            {"m": "Oct 28", "p": 61}, {"m": "Dec 9", "p": 74},
        ],
        "stats": [
            st("4.25–4.50", "held 4 mtgs", "neu"), st("$6.6T", "▼ QT ongoing", "down"),
            st("$148B", "▼ draining", "down"), st("2 cuts", "median", "neu"),
        ],
    },
    # §03 Liquidity — net-liquidity weekly series (trn) + 4 stats
    "liquidity": {
        "net_liq_series": [6.32, 6.26, 6.14, 6.18, 6.02, 5.88, 5.92, 5.80, 5.76, 5.82, 5.84],
        "y_min": 5.5, "y_max": 6.5,
        "stats": [
            st("$22.0T", "▲ +1.8% YoY", "up"), st("$5.84T", "▼ −3.1% 3m", "down"),
            st("$248B", "▲ +2.4% 30d", "up"),
        ],
    },
    # §04 Growth & Labor — 4 stats
    "growth": [
        st("49.5", "contraction", "down"), st("+139K", "→ cooling", "neu"),
        st("242K", "▲ +14K", "down"), st("1.9%", "Atlanta Fed", "up"),
    ],
    # §05 Rates — yield curve + 4 stats
    "rates": {
        "curve": [
            {"tenor": "1M", "y": 3.69}, {"tenor": "3M", "y": 3.83}, {"tenor": "6M", "y": 3.92},
            {"tenor": "2Y", "y": 4.19}, {"tenor": "5Y", "y": 4.23}, {"tenor": "10Y", "y": 4.46},
            {"tenor": "30Y", "y": 4.90},
        ],
        "stats": [
            st("4.19", "+0.8%", "up"), st("4.51", "+1.3%", "up"),
            st("+27bp", "steepening", "up"), st("312bp", "→ calm", "neu"),
        ],
    },
}

out = ROOT / "data" / "macro2.json"
out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"wrote {out} (regime {len(data['regime_tape'])}, curve {len(data['rates']['curve'])}, "
      f"series {len(data['liquidity']['net_liq_series'])})")
