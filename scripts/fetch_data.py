#!/usr/bin/env python3
"""
NoCashFlow · data snapshot fetcher

Writes server-side snapshots that build.py injects into pages so the site is
never blank ("—") even if the live client-side APIs fail:

    data/market.json    market instruments, pre-formatted to match app.js
    data/calendar.json  Finnhub economic calendar, next 7 days, CET

Resilience: each source has a timeout; on failure the previous value in the
existing JSON is kept (last-good), and every record carries an `asof` stamp.

Run locally:  FINNHUB_API_KEY=... python3 scripts/fetch_data.py
In CI:        the workflow exports FINNHUB_API_KEY from repo secrets.
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("requests is required: pip install requests")

try:
    from zoneinfo import ZoneInfo
    CET = ZoneInfo("Europe/Berlin")
except Exception:  # pragma: no cover
    CET = timezone(timedelta(hours=1))

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TIMEOUT = 12
UA = {"User-Agent": "Mozilla/5.0 (NoCashFlow data fetcher)"}


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
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")


# ── display formatting (mirrors app.js INSTRUMENTS so build-time == client) ──
def fmt_num(n, dec=2, prefix=""):
    if n is None:
        return "—"
    if n >= 1000:
        return prefix + f"{n:,.0f}"
    return prefix + f"{n:.{dec}f}"


def fmt_pct(n):
    if n is None:
        return "—"
    return ("+" if n >= 0 else "") + f"{n:.2f}%"


FMT = {
    "btc":    lambda v: fmt_num(v, 0, "$"),
    "eth":    lambda v: fmt_num(v, 0, "$"),
    "gold":   lambda v: "$" + f"{v:.0f}",
    "brent":  lambda v: "$" + f"{v:.1f}",
    "dxy":    lambda v: f"{v:.2f}",
    "us10y":  lambda v: f"{v:.2f}%",
    "vix":    lambda v: f"{v:.2f}",
    "spx":    lambda v: fmt_num(v, 0),
    "eurusd": lambda v: f"{v:.4f}",
}


def direction(key, pct):
    if pct is None:
        return "neu"
    if key == "vix":           # inverted: down VIX = risk-on = "up"/green
        return "up" if pct <= 0 else "dn"
    return "up" if pct >= 0 else "dn"


# ── market sources ───────────────────────────────────────────────────────────
def fetch_crypto():
    """CoinGecko spot + 24h change for BTC, ETH."""
    out = {}
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin,ethereum", "vs_currencies": "usd",
                    "include_24hr_change": "true"},
            headers=UA, timeout=TIMEOUT)
        r.raise_for_status()
        j = r.json()
        if "bitcoin" in j:
            out["btc"] = (j["bitcoin"]["usd"], j["bitcoin"].get("usd_24h_change"))
        if "ethereum" in j:
            out["eth"] = (j["ethereum"]["usd"], j["ethereum"].get("usd_24h_change"))
    except Exception as e:
        print(f"  ⚠️  CoinGecko failed: {e}")
    return out


def fetch_yahoo(symbol):
    """Yahoo chart API → (last, pct vs prior close). Server-side: no CORS proxy."""
    try:
        r = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            params={"interval": "1d", "range": "10d"}, headers=UA, timeout=TIMEOUT)
        r.raise_for_status()
        res = r.json()["chart"]["result"][0]
        closes = [c for c in res["indicators"]["quote"][0]["close"] if c is not None]
        last, prev = closes[-1], closes[-2]
        pct = ((last - prev) / prev) * 100 if prev else 0.0
        return last, pct
    except Exception as e:
        print(f"  ⚠️  Yahoo {symbol} failed: {e}")
        return None


YAHOO = {"gold": "GC=F", "brent": "BZ=F", "dxy": "DX-Y.NYB", "us10y": "^TNX",
         "vix": "^VIX", "spx": "^GSPC", "eurusd": "EURUSD=X"}


def fetch_fear_greed():
    try:
        r = requests.get("https://api.alternative.me/fng/", params={"limit": 1},
                         headers=UA, timeout=TIMEOUT)
        r.raise_for_status()
        d = r.json()["data"][0]
        return int(d["value"]), d["value_classification"]
    except Exception as e:
        print(f"  ⚠️  Fear&Greed failed: {e}")
        return None


def build_market():
    prev = load_json("market.json", {"instruments": {}})
    inst = dict(prev.get("instruments", {}))  # start from last-good
    stamp = now_iso()

    def put(key, value, pct):
        if value is None:
            return  # keep last-good already in `inst`
        inst[key] = {"px": FMT[key](value), "chg": fmt_pct(pct),
                     "dir": direction(key, pct), "asof": stamp}

    print("• crypto (CoinGecko)…")
    cg = fetch_crypto()
    for k in ("btc", "eth"):
        if k in cg:
            put(k, cg[k][0], cg[k][1])

    print("• instruments (Yahoo)…")
    for key, sym in YAHOO.items():
        d = fetch_yahoo(sym)
        if d:
            put(key, d[0], d[1])

    print("• fear & greed…")
    fg = fetch_fear_greed()
    if fg:
        val, label = fg
        d = "up" if val > 55 else "dn" if val < 35 else "neu"
        inst["fg"] = {"px": str(val), "chg": label, "dir": d, "asof": stamp}

    return {"asof": stamp, "instruments": inst}


# ── economic calendar (Finnhub) ──────────────────────────────────────────────
# US + Eurozone priority; high + medium impact.
EUROZONE = {"EA", "EU", "DE", "FR", "IT", "ES", "NL", "BE", "AT", "PT", "IE",
            "FI", "GR"}
PRIORITY = {"US"} | EUROZONE


def _fmt_value(v, unit):
    if v is None or v == "":
        return "—"
    try:
        f = float(v)
        s = f"{f:g}"
    except (TypeError, ValueError):
        s = str(v)
    return s + (unit or "")


def build_calendar():
    key = os.environ.get("FINNHUB_API_KEY")
    if not key:
        print("  ⚠️  FINNHUB_API_KEY not set — keeping existing calendar.json")
        return load_json("calendar.json", {"asof": None, "events": []})

    frm = datetime.now(timezone.utc).date()
    to = frm + timedelta(days=7)
    try:
        r = requests.get("https://finnhub.io/api/v1/calendar/economic",
                         params={"from": frm.isoformat(), "to": to.isoformat(),
                                 "token": key}, headers=UA, timeout=TIMEOUT)
        r.raise_for_status()
        raw = r.json().get("economicCalendar", [])
    except Exception as e:
        print(f"  ⚠️  Finnhub calendar failed: {e} — keeping existing")
        return load_json("calendar.json", {"asof": None, "events": []})

    events = []
    for ev in raw:
        impact = (ev.get("impact") or "").lower()
        country = (ev.get("country") or "").upper()
        if impact not in ("high", "medium"):
            continue
        if country not in PRIORITY:
            continue
        try:
            dt_utc = datetime.strptime(ev["time"], "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc)
        except Exception:
            continue
        dt_cet = dt_utc.astimezone(CET)
        events.append({
            "dt_utc": ev["time"],
            "cet_date": dt_cet.strftime("%Y-%m-%d"),
            "wd": dt_cet.weekday(),            # 0=Mon
            "time": dt_cet.strftime("%H:%M"),
            "event": ev.get("event", "").strip(),
            "country": country,
            "impact": impact,
            "prev": _fmt_value(ev.get("prev"), ev.get("unit")),
            "est": _fmt_value(ev.get("estimate"), ev.get("unit")),
        })

    # sort chronologically; high-impact first within the same slot
    events.sort(key=lambda e: (e["cet_date"], e["time"], e["impact"] != "high"))
    print(f"• calendar: {len(events)} priority events (of {len(raw)} total)")
    return {"asof": now_iso(), "events": events}


# ── macro series (FRED, real) + funding (Deribit) ────────────────────────────
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"


def fred_latest(series, start="2025-01-01"):
    """Return (last, prev, date) for a FRED series, skipping '.' gaps. None on error."""
    try:
        r = requests.get(FRED_CSV, params={"id": series, "cosd": start},
                         headers=UA, timeout=25)  # FRED CSV can be slow
        r.raise_for_status()
        vals = []
        for line in r.text.strip().splitlines()[1:]:
            parts = line.split(",")
            if len(parts) < 2 or parts[1] in (".", ""):
                continue
            try:
                vals.append((parts[0], float(parts[1])))
            except ValueError:
                continue
        if not vals:
            return None
        last = vals[-1]
        prev = vals[-2][1] if len(vals) > 1 else None
        return last[1], prev, last[0]
    except Exception as e:
        print(f"  ⚠️  FRED {series} failed: {e}")
        return None


def build_macro():
    prev = load_json("macro.json", {})
    out = dict(prev)                       # start from last-good
    stamp = now_iso()

    print("• FRED yields (DGS2, DGS10) + curve…")
    for key, series in (("us2y", "DGS2"), ("us10y", "DGS10")):
        d = fred_latest(series)
        if d:
            pct = ((d[0] - d[1]) / d[1] * 100) if d[1] else None
            out[key] = {"value": d[0], "chg": fmt_pct(pct), "dir": ("up" if (pct or 0) >= 0 else "dn"),
                        "date": d[2], "asof": stamp}
    if out.get("us10y") and out.get("us2y"):
        out["spread"] = round(out["us10y"]["value"] - out["us2y"]["value"], 2)

    curve = []
    for label, series in (("1M", "DGS1MO"), ("3M", "DGS3MO"), ("6M", "DGS6MO"),
                          ("2Y", "DGS2"), ("5Y", "DGS5"), ("10Y", "DGS10"), ("30Y", "DGS30")):
        d = fred_latest(series)
        if d:
            curve.append({"l": label, "v": d[0]})
    if curve:
        out["curve"] = curve

    print("• FRED M2 + Fed funds target…")
    d = fred_latest("M2SL")
    if d:
        out["m2"] = {"value": round(d[0] / 1000, 2),
                     "prev": round(d[1] / 1000, 2) if d[1] else None, "asof": stamp}
    d = fred_latest("DFEDTARU")              # Fed funds target range, upper — daily, real
    if d:
        out["fed_rate"] = {"value": d[0], "asof": stamp, "date": d[2]}

    print("• funding rate (Deribit BTC-PERPETUAL)…")
    try:
        r = requests.get("https://www.deribit.com/api/v2/public/ticker",
                         params={"instrument_name": "BTC-PERPETUAL"}, headers=UA, timeout=TIMEOUT)
        r.raise_for_status()
        fr = r.json().get("result", {}).get("funding_8h")
        if fr is not None:
            out["funding"] = {"value": round(fr * 100, 4), "asof": stamp}  # percent, 8h
    except Exception as e:
        print(f"  ⚠️  Deribit funding failed: {e}")

    # NOTE: ISM Manufacturing PMI (NAPM) is discontinued on FRED and has no free
    # real-time source — intentionally NOT fabricated here. Handled separately.
    out["asof"] = stamp
    return out


def main():
    print("Fetching market snapshot…")
    write_json("market.json", build_market())
    print("Fetching macro series…")
    write_json("macro.json", build_macro())
    print("Fetching economic calendar…")
    write_json("calendar.json", build_calendar())
    print("✓ snapshots written to data/")


if __name__ == "__main__":
    main()
