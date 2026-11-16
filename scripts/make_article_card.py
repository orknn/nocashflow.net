#!/usr/bin/env python3
"""
Branded social card (1200x630) for an article — doubles as its og:image.

Liquid look (see liquid_card.py): bone board, NO/CASHFLOW in Bricolage, the
headline set like the site's article head — "A — B" puts B in Instrument Serif
italic on its own line — and a dark stage strip with the terrain lines, whose
curve is derived from the title so every article gets its own landscape.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in (str(ROOT), str(ROOT / "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)
try:
    from tools.watermark import stamp as _wm_stamp
except Exception:
    _wm_stamp = None
import liquid_card as lc

M = 64


def _headline(c, title, maxw):
    """Fit the title in at most 3 lines (4 at the smallest size).
    Returns (size, [(text, italic), …])."""
    a, b = (title.split(" — ", 1) + [""])[:2] if " — " in title else (title, "")
    sizes = (86, 78, 70, 62, 54, 48)
    for size in sizes:
        fs, fi = lc.sans(size, 500), lc.serif_it(size * 1.06)
        la = c.wrap_balanced(a + (" —" if b else ""), fs, maxw, -0.055)
        lb = c.wrap_balanced(b, fi, maxw, -0.02) if b else []
        if len(la) + len(lb) <= (3 if size > sizes[-1] else 4):
            break
    return size, [(t, False) for t in la] + [(t, True) for t in lb]


def build_article_card(title, dek, cat, date_disp, out_path, lang=None):
    c = lc.Canvas(lc.BONE)

    # header: wordmark · category + date (the article page's meta line)
    c.wordmark(M, 78, 27)
    meta = lc.mono(14.5)
    right = "  ·  " + lc.upper(date_disp, lang)
    xr = lc.W - M
    c.text_right(xr, 75, right, meta, lc.MUTE, 0.06)
    c.text_right(xr - c.width(right, meta, 0.06), 75, lc.upper(cat, lang), meta, lc.HOT, 0.06)

    # headline
    maxw = lc.W - 2 * M
    size, lines = _headline(c, title, maxw)
    y = 112 + size * 0.86
    for text, italic in lines:
        if italic:
            c.text((M - size * 0.02, y), text, lc.serif_it(size * 1.06), lc.INK, -0.02)
        else:
            c.text((M - size * 0.03, y), text, lc.sans(size, 500), lc.INK, -0.055)
        y += size * 0.98

    # dek — two lines at most, never into the stage
    stage_top = lc.H - 24 - 132
    df = lc.sans(24, 400)
    y += 26 - size * 0.62
    for ln in c.wrap(dek, df, 900, -0.02)[:2]:
        if y + 8 > stage_top - 14:
            break
        c.text((M, y), ln, df, lc.DIM, -0.02)
        y += 33

    # stage strip: this article's landscape + signature
    box = (24, stage_top, lc.W - 24, lc.H - 24)
    c.stage(box)
    c.terrain((box[0] + 216, box[1] + 10, box[2] - 262, box[3] - 14), seed=lc.seed_of(title),
              layers=16, lift=0.4, pad=(0, 6))
    sig = lc.mono(13.5)
    c.text((box[0] + 26, box[3] - 24), "NOCASHFLOW.NET", sig, lc.BONE, 0.08)
    c.text_right(box[2] - 26, box[3] - 24, "NO NOISE. JUST MARKETS.", sig, (150, 148, 142), 0.08)

    return c.save(out_path, _wm_stamp)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "card_proto.png"
    build_article_card(
        "Closed, and Still Flowing",
        "Iran calls Hormuz closed again; CENTCOM counts 55 transits the same day. The scorecard: the US and Russia won the shock — the Gulf lost.",
        "Commodities", "Jun 21, 2026", out)
    print("wrote", out)
