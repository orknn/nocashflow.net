#!/usr/bin/env python3
"""
Branded social card (1200x630) for an article — doubles as its og:image.

NoCashFlow broadsheet look: cream board, oxide-red top band, NO/CASHFLOW header,
big Fraunces headline, dek, and the "nocashflow.net · No noise. Just markets."
signature footer. The faint diagonal watermark is baked in (tools/watermark.py).
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
try:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools.watermark import stamp as _wm_stamp
except Exception:
    _wm_stamp = None

# tokens (broadsheet palette)
BG    = (243, 238, 227)   # #F3EEE3 off-white board
INK   = (25, 21, 18)
DIM   = (87, 79, 71)
MUTED = (138, 130, 118)
RED   = (176, 68, 43)     # #B0442B oxide-red
AMBER = (201, 138, 43)
LINE  = (212, 207, 196)

W, H = 1200, 630
M = 72


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


def _w(d, t, f):
    return d.textbbox((0, 0), t, font=f)[2]


def _wrap(d, text, font, maxw):
    out, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if _w(d, t, font) <= maxw:
            cur = t
        else:
            if cur:
                out.append(cur)
            cur = word
    if cur:
        out.append(cur)
    return out


def build_article_card(title, dek, cat, date_disp, out_path):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 8], fill=RED)                       # brand top band

    # header — NO/CASHFLOW + section
    by = 48
    wm = fra(34, "Black")
    x = M
    d.text((x, by), "NO", font=wm, fill=INK); x += _w(d, "NO", wm)
    d.text((x, by), "/", font=wm, fill=RED);  x += _w(d, "/", wm)
    d.text((x, by), "CASHFLOW", font=wm, fill=INK)
    d.text((W - M - _w(d, cat.upper(), mono(16, bold=True)), by + 10),
           cat.upper(), font=mono(16, bold=True), fill=MUTED)
    d.line([M, 110, W - M, 110], fill=INK, width=2)

    # eyebrow
    eb = f"{cat.upper()}  ·  {date_disp.upper()}"
    d.text((M, 132), eb, font=mono(17, bold=True), fill=RED)

    # headline — shrink to fit within 3 lines
    maxw = W - 2 * M
    for ts in (78, 70, 62, 54, 48):
        tf = fra(ts, "SemiBold")
        lines = _wrap(d, title, tf, maxw)
        if len(lines) <= 3:
            break
    ty = 178
    for ln in lines:
        d.text((M, ty), ln, font=tf, fill=INK)
        ty += int(ts * 1.1)

    # dek (max 3 lines)
    ty += 18
    df = fra(25, "Regular")
    for ln in _wrap(d, dek, df, maxw)[:3]:
        d.text((M, ty), ln, font=df, fill=DIM)
        ty += 35

    # footer signature
    fy = H - 60
    d.line([M, fy - 18, W - M, fy - 18], fill=LINE, width=2)
    d.text((M, fy), "nocashflow.net", font=fra(25, "SemiBold"), fill=INK)
    sig = "No noise. Just markets."
    d.text((W - M - _w(d, sig, mono(16)), fy + 6), sig, font=mono(16), fill=MUTED)

    if _wm_stamp:
        img = _wm_stamp(img, corner=False)        # diagonal only; footer is branded
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG")
    return out_path


if __name__ == "__main__":
    # quick prototype render
    build_article_card(
        "Closed, and Still Flowing",
        "Iran calls Hormuz closed again; CENTCOM counts 55 transits the same day. The scorecard: the US and Russia won the shock — the Gulf lost.",
        "Commodities", "Jun 21, 2026",
        "/tmp/card_proto.png")
    print("wrote /tmp/card_proto.png")
