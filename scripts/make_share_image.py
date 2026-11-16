#!/usr/bin/env python3
"""
Render the daily market snapshot to a 1200x630 share card (share/daily.png).

Reads the same committed snapshots the site is built from (data/market.json,
data/macro.json) — so the image never shows anything the pages don't. No
fabricated numbers: every value is copied verbatim from the snapshot, and if a
field is missing it renders "—". The landscape in the stage is the real US
Treasury curve from macro.json; without that data the stage stays empty.
Run after fetch_data.py / build.py in the cron.

Liquid look (see liquid_card.py): the home page in one frame — dark stage with
the mood reading and the curve, then the eight instruments as bone tiles.
"""
import json
import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "share"
for p in (str(ROOT), str(ROOT / "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

# Brand watermark (faint, centred). The card already carries the wordmark, so
# corner=False avoids a duplicate. Never breaks the build if the tool moves.
try:
    from tools.watermark import stamp as _wm_stamp
except Exception:
    _wm_stamp = None
import liquid_card as lc

M = 48
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def _load(name):
    try:
        return json.loads((DATA / name).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _chg_color(chg):
    """Colour by the literal sign of the change — clearest for a standalone card."""
    s = chg.strip()
    if s.startswith("+"):
        return lc.UP_T
    if s.startswith("-") or s.startswith("−"):
        return lc.DN_T
    return lc.MUTE


def _mood_color(val):
    """Same buckets as the site's body[data-mood]: fear / neutral / greed."""
    try:
        v = int(val)
    except Exception:
        return lc.BONE
    return lc.MOOD if v < 35 else lc.BONE if v < 55 else lc.UP


def build_card():
    market = _load("market.json")
    macro = _load("macro.json")
    inst = market.get("instruments", {})
    c = lc.Canvas(lc.BONE)

    # ── header ───────────────────────────────────────────────────────────────
    c.wordmark(M, 66, 27)
    asof = market.get("asof") or macro.get("asof") or ""
    try:
        dt = datetime.datetime.fromisoformat(asof.replace("Z", "+00:00"))
        datestr = f"{dt.day:02d} {MONTHS[dt.month - 1]} {dt.year}"
    except Exception:
        datestr = ""
    meta = lc.mono(14.5)
    right = ("  ·  " + datestr) if datestr else ""
    c.text_right(lc.W - M, 63, right, meta, lc.MUTE, 0.06)
    c.text_right(lc.W - M - c.width(right, meta, 0.06), 63, "DAILY MARKET SNAPSHOT", meta, lc.HOT, 0.06)

    # ── stage: Crypto Fear & Greed + the real Treasury curve ──────────────────
    fg = inst.get("fg", {})
    fgval = str(fg.get("px", "—"))
    fglabel = str(fg.get("chg", "")).strip()
    mood = _mood_color(fg.get("px"))
    box = (24, 92, lc.W - 24, 330)
    c.stage(box, mood=mood if mood != lc.BONE else lc.MOOD)

    curve = [p for p in (macro.get("curve") or []) if isinstance(p.get("v"), (int, float))]
    if len(curve) >= 2:
        tb = (box[0] + 470, box[1] + 40, box[2] - 70, box[3] - 44)
        pts = c.terrain(tb, values=[p["v"] for p in curve], layers=20, lift=0.42, pad=(0, 4))
        lab = lc.mono(11.5)
        n = len(curve)
        for j in (0, n - 1):                              # label the two ends only
            x, y = pts[round(j / (n - 1) * (len(pts) - 1))]
            txt = f'{curve[j]["l"]}  {curve[j]["v"]:.2f}%'
            if j == 0:
                c.text((x - 6, y + 24), txt, lab, (190, 188, 182), 0.04)
            else:
                c.text_right(x + 8, y - 16, txt, lab, lc.BONE, 0.04)
        c.text_right(box[2] - 28, box[1] + 34, "US TREASURY CURVE", lc.mono(12.5), (150, 148, 142), 0.08)

    c.text((box[0] + 30, box[1] + 34), "CRYPTO FEAR & GREED INDEX", lc.mono(12.5), (150, 148, 142), 0.08)
    big = lc.sans(150, 300)
    xe = c.text((box[0] + 22, box[3] - 36), fgval, big, lc.BONE, -0.07)
    if fglabel:
        c.text((xe + 26, box[3] - 40), fglabel, lc.serif_it(54), mood, -0.015)

    # ── instruments: 4 x 2 bone tiles ─────────────────────────────────────────
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
    cols, gap = 4, 10
    gx0, gy0 = 24, 340
    cw = (lc.W - 2 * gx0 - gap * (cols - 1)) / cols
    rh = 112
    klab, vfont, cfont = lc.mono(12.5), lc.sans(38, 400), lc.mono(15, 500)
    for i, (label, dd) in enumerate(cells):
        r, col = divmod(i, cols)
        x = gx0 + col * (cw + gap)
        y = gy0 + r * (rh + gap)
        c.rrect((x, y, x + cw, y + rh), 18, fill=lc.BONE_2)
        c.text((x + 20, y + 30), label, klab, lc.MUTE, 0.08)
        c.text((x + 18, y + 86), str(dd.get("px", "—")), vfont, lc.INK, -0.055)
        chg = str(dd.get("chg", ""))
        if chg:
            c.text_right(x + cw - 20, y + 84, chg, cfont, _chg_color(chg), 0)

    # ── footer ────────────────────────────────────────────────────────────────
    ft = lc.mono(12.5)
    c.text((M, lc.H - 22), "NOCASHFLOW.NET", ft, lc.INK, 0.1)
    c.text_right(lc.W - M, lc.H - 22, "LIVE MACRO & MARKET DATA · UPDATED DAILY", ft, lc.MUTE, 0.1)

    path = OUT / "daily.png"
    c.save(path, _wm_stamp)
    print(f"  + {path.relative_to(ROOT)}  ({fgval} {fglabel.upper()})")
    return path


if __name__ == "__main__":
    build_card()
