#!/usr/bin/env python3
"""
Render the daily market snapshot to a 1200x630 share card (share/daily.png).

Reads the same committed snapshots the site is built from (data/market.json,
data/macro.json) — so the image never shows anything the pages don't. No
fabricated numbers: every value is copied verbatim from the snapshot, and if a
field is missing it renders "—". Run after fetch_data.py / build.py in the cron.
"""
import json
import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
FONTS = ROOT / "assets" / "fonts"
OUT = ROOT / "share"

# ── design tokens (mirror site.css :root) ────────────────────────────────────
BG        = (255, 255, 255)
BG_ELEV   = (250, 249, 246)
INK       = (25, 21, 18)
AMBER     = (201, 138, 43)
GREEN     = (21, 128, 61)
RED       = (216, 58, 30)
LINE      = (232, 227, 216)
MUTED     = (122, 114, 104)

W, H = 1200, 630
M = 64                      # outer margin

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def _load(name):
    try:
        return json.loads((DATA / name).read_text(encoding="utf-8"))
    except Exception:
        return {}


def fra(size, weight="SemiBold"):
    f = ImageFont.truetype(str(FONTS / "Fraunces.ttf"), size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


def mono(size, bold=False):
    name = "IBMPlexMono-SemiBold.ttf" if bold else "IBMPlexMono-Regular.ttf"
    return ImageFont.truetype(str(FONTS / name), size)


def _w(draw, text, font):
    return draw.textbbox((0, 0), text, font=font)[2]


def _chg_color(chg):
    """Colour by the literal sign of the change — clearest for a standalone card."""
    s = chg.strip()
    if s.startswith("+"):
        return GREEN
    if s.startswith("-") or s.startswith("−"):
        return RED
    return INK


def _fg_color(val):
    try:
        v = int(val)
    except Exception:
        return AMBER
    return RED if v < 25 else AMBER if v < 55 else GREEN


def build_card():
    market = _load("market.json")
    macro = _load("macro.json")
    inst = market.get("instruments", {})

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # warm top band for a touch of depth
    d.rectangle([0, 0, W, 8], fill=AMBER)

    # ── header ───────────────────────────────────────────────────────────────
    by = 54
    wm = fra(38, "Black")
    x = M
    d.text((x, by), "NO", font=wm, fill=INK)
    x += _w(d, "NO", wm)
    d.text((x, by), "/", font=wm, fill=AMBER)
    x += _w(d, "/", wm)
    d.text((x, by), "CASHFLOW", font=wm, fill=INK)

    # date + label, right-aligned
    asof = market.get("asof") or macro.get("asof") or ""
    try:
        dt = datetime.datetime.fromisoformat(asof.replace("Z", "+00:00"))
        datestr = f"{dt.day:02d} {MONTHS[dt.month - 1]} {dt.year}"
    except Exception:
        datestr = ""
    lab = mono(17, bold=True)
    sub = mono(14)
    d.text((W - M - _w(d, datestr, lab), by + 2), datestr, font=lab, fill=INK)
    tag = "DAILY MARKET SNAPSHOT"
    d.text((W - M - _w(d, tag, sub), by + 30), tag, font=sub, fill=AMBER)

    d.line([M, 120, W - M, 120], fill=LINE, width=2)

    # ── hero: Crypto Fear & Greed ─────────────────────────────────────────────
    fg = inst.get("fg", {})
    fgval = str(fg.get("px", "—"))
    fglabel = str(fg.get("chg", "")).upper()
    big = fra(132, "Black")
    hy = 150
    d.text((M, hy), fgval, font=big, fill=_fg_color(fg.get("px")))
    hx = M + _w(d, fgval, big) + 34
    d.text((hx, hy + 36), fglabel or "—", font=fra(46, "SemiBold"), fill=INK)
    d.text((hx, hy + 100), "CRYPTO FEAR & GREED INDEX", font=mono(17), fill=AMBER)

    # ── stat grid: 4 cols x 2 rows ────────────────────────────────────────────
    cells = [
        ("BITCOIN",   inst.get("btc", {})),
        ("ETHEREUM",  inst.get("eth", {})),
        ("GOLD",      inst.get("gold", {})),
        ("BRENT",     inst.get("brent", {})),
        ("DOLLAR · DXY", inst.get("dxy", {})),
        ("US 10Y",    inst.get("us10y", {})),
        ("VIX",       inst.get("vix", {})),
        ("S&P 500",   inst.get("spx", {})),
    ]
    cols = 4
    cw = (W - 2 * M) / cols
    gy0 = 348
    rh = 122
    klab = mono(15, bold=True)
    vfont = fra(36, "SemiBold")
    cfont = mono(18, bold=True)
    for i, (label, dd) in enumerate(cells):
        r, c = divmod(i, cols)
        cx = M + c * cw
        cy = gy0 + r * rh
        d.text((cx, cy), label, font=klab, fill=AMBER)
        val = str(dd.get("px", "—"))
        d.text((cx, cy + 26), val, font=vfont, fill=INK)
        chg = str(dd.get("chg", ""))
        if chg:
            d.text((cx, cy + 78), chg, font=cfont, fill=_chg_color(chg))
        # thin column separators
        if c > 0:
            d.line([cx - 18, cy - 4, cx - 18, cy + rh - 28], fill=LINE, width=1)

    # ── footer ────────────────────────────────────────────────────────────────
    fy = 588
    d.line([M, fy - 16, W - M, fy - 16], fill=LINE, width=2)
    d.text((M, fy), "nocashflow.net", font=fra(24, "SemiBold"), fill=INK)
    foot = "Live macro & market data · updated daily"
    ff = mono(15)
    d.text((W - M - _w(d, foot, ff), fy + 6), foot, font=ff, fill=MUTED)

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "daily.png"
    img.save(path, "PNG")
    print(f"  + {path.relative_to(ROOT)}  ({fgval} {fglabel})")
    return path


if __name__ == "__main__":
    build_card()
