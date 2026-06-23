#!/usr/bin/env python3
"""
Render the default Open Graph / Twitter share card to og.png (1200x630).

Static brand card (not the daily snapshot — that's make_share_image.py). Same
broadsheet design language: warm off-white ground, amber accent on the "/",
dark serif wordmark. The tagline is the one line that changes over time, so
the card is regenerated from this script rather than kept as an opaque PNG.

Run:  python3 scripts/make_og_image.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"

# ── design tokens (mirror the current og.png / site palette) ─────────────────
BG      = (247, 244, 237)        # warm off-white
INK     = (24, 21, 16)           # near-black
AMBER   = (179, 18, 43)          # crimson accent (the "/") — matches the live site (#B3122B)
MUTED   = (122, 114, 104)        # eyebrow / Barcelona
DEK     = (74, 70, 60)           # tagline
LINE    = (215, 210, 197)        # hairlines

W, H = 1200, 630
M = 80                            # outer margin

TAGLINE = "No noise. Just markets."


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


def _w(d, text, font):
    return d.textbbox((0, 0), text, font=font)[2]


def draw_spaced(d, xy, text, font, fill, spacing):
    """Letter-spaced text (PIL has no tracking) — left to right."""
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill)
        x += d.textbbox((0, 0), ch, font=font)[2] + spacing
    return x


def paste_italic(img, xy, text, font, fill, slant=0.18):
    """Faux-italic: render upright to a layer, shear it, paste. (No italic in
    the Fraunces.ttf we ship.)"""
    d0 = ImageDraw.Draw(img)
    bb = d0.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] + 8
    extra = int(th * slant) + 6
    tmp = Image.new("RGBA", (tw + extra + 6, th + 6), (0, 0, 0, 0))
    ImageDraw.Draw(tmp).text((extra, 0), text, font=font, fill=fill)
    sheared = tmp.transform(tmp.size, Image.AFFINE, (1, slant, 0, 0, 1, 0),
                            resample=Image.BICUBIC)
    img.paste(sheared, (xy[0] - extra, xy[1]), sheared)


def build():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # top hairline + eyebrow
    d.line([M, 86, W - M, 86], fill=LINE, width=2)
    draw_spaced(d, (M, 104), "MACRO × MARKETS", mono(21), MUTED, 7)

    # wordmark — NO / CASHFLOW, amber slash
    wm = fra(120, "Black")
    wy = 232
    x = M
    d.text((x, wy), "NO", font=wm, fill=INK); x += _w(d, "NO", wm)
    d.text((x, wy), "/", font=wm, fill=AMBER); x += _w(d, "/", wm)
    d.text((x, wy), "CASHFLOW", font=wm, fill=INK)

    # tagline (faux-italic serif)
    paste_italic(img, (M, 392), TAGLINE, fra(44, "Regular"), DEK, slant=0.16)

    # bottom hairline + footer
    d.line([M, 540, W - M, 540], fill=LINE, width=2)
    foot = fra(26, "SemiBold")
    d.text((M, 560), "nocashflow.net", font=foot, fill=INK)
    bcn = mono(22)
    d.text((W - M - _w(d, "Barcelona", bcn), 566), "Barcelona", font=bcn, fill=MUTED)

    out = ROOT / "og.png"
    img.save(out, "PNG")
    print(f"  + {out.name}  ({W}x{H})  tagline: \"{TAGLINE}\"")
    return out


if __name__ == "__main__":
    build()
