#!/usr/bin/env python3
"""
Render the default Open Graph / Twitter share card to og.png (1200x630).

Static brand card (not the daily snapshot — that's make_share_image.py). It is
the home page's stage in one frame: ink ground with the mood glow, the terrain
landscape, the NO/CASHFLOW wordmark and the tagline set the way the site sets
it — sans, then Instrument Serif italic.

Run:  python3 scripts/make_og_image.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
import liquid_card as lc

M = 72
TAGLINE = ("No noise.", "Just markets.")        # sans · serif italic

# A calm, rising landscape — a shape, not data (no numbers are shown on it).
CURVE = [0.08, 0.16, 0.14, 0.30, 0.42, 0.40, 0.56, 0.62, 0.78, 0.92]


def build():
    c = lc.Canvas(lc.INK)
    c.stage((0, 0, lc.W, lc.H), radius=0, strength=0.5)
    c.terrain((-40, 300, lc.W + 40, lc.H - 64), values=CURVE, layers=30, lift=0.52, dots=False)

    # eyebrow row
    eb = lc.mono(15)
    c.text((M, 84), "MACRO × MARKETS", eb, (236, 234, 227), 0.12)
    c.text_right(lc.W - M, 84, "BARCELONA", eb, (150, 148, 142), 0.12)

    # wordmark — as wide as the margins allow, like the site footer
    size = 100
    while c.wordmark_width(size + 2) <= lc.W - 2 * M and size < 190:
        size += 2
    c.wordmark(M - size * 0.03, 96 + size * 0.92, size, ink=lc.BONE)

    # tagline
    ty = 96 + size * 0.92 + 74
    x = c.text((M, ty), TAGLINE[0], lc.sans(46, 400), lc.BONE, -0.045)
    c.text((x + 14, ty), TAGLINE[1], lc.serif_it(50), lc.BONE, -0.015)

    # footer
    ft = lc.mono(15)
    c.text((M, lc.H - 34), "NOCASHFLOW.NET", ft, lc.BONE, 0.1)
    c.text_right(lc.W - M, lc.H - 34, "MACRO · CRYPTO · COMMODITIES", ft, (150, 148, 142), 0.1)

    out = ROOT / "og.png"
    c.save(out)
    print(f"  + {out.name}  ({lc.W}x{lc.H})  tagline: \"{' '.join(TAGLINE)}\"")
    return out


if __name__ == "__main__":
    build()
