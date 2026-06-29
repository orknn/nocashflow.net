#!/usr/bin/env python3
"""
NoCashFlow image watermark stamper.

Stamps any raster image with the brand so re-use elsewhere credits the site:
  • a faint repeated "nocashflow.net" tile, ~6% opacity, set on a 30° diagonal
    across the whole frame (doesn't fight the data, but tags the image);
  • a clear "nocashflow.net" wordmark in the bottom-right corner (attribution).

Ink auto-contrasts: dark mark on light images, light mark on dark images.

Library use:
    from tools.watermark import stamp
    out = stamp(pil_image)                 # diagonal + corner
    out = stamp(pil_image, corner=False)   # diagonal only (image already branded)

CLI:
    python tools/watermark.py a.png b.png            # writes a-wm.png, b-wm.png
    python tools/watermark.py *.png --inplace        # overwrite originals
    python tools/watermark.py a.png --no-diagonal    # corner only
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT_MONO = ROOT / "assets" / "fonts" / "IBMPlexMono-SemiBold.ttf"
TEXT = "nocashflow.net"


def _font(size):
    try:
        return ImageFont.truetype(str(FONT_MONO), max(8, int(size)))
    except Exception:
        return ImageFont.load_default()


def _is_light(img):
    """Average luminance > mid → treat as a light image."""
    g = img.convert("L").resize((16, 16))
    px = list(g.getdata())
    return (sum(px) / len(px)) > 128


BRAND_RED = (176, 68, 43)  # #B0442B — same oxide-red as the chart "Headline CPI"


def stamp(img, *, diagonal=True, corner=True, opacity=0.08, ink=None,
          corner_color=BRAND_RED):
    """Return a watermarked copy of a PIL image. Original is not mutated."""
    base = img.convert("RGBA")
    W, H = base.size
    if ink is None:
        ink = (22, 24, 28) if _is_light(base) else (243, 238, 227)  # brand ink / cream
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    if diagonal:
        # one single faint horizontal wordmark, centered
        fsize = max(11, W // 36)
        tfont = _font(fsize)
        td = ImageDraw.Draw(overlay)
        bb = td.textbbox((0, 0), TEXT, font=tfont)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        a = max(1, int(255 * opacity))
        x = (W - tw) // 2 - bb[0]
        y = (H - th) // 2 - bb[1]
        td.text((x, y), TEXT, font=tfont, fill=(ink[0], ink[1], ink[2], a))

    if corner:
        cfont = _font(max(11, round(W / 90)))   # ~40% of the earlier size (−60%)
        cd = ImageDraw.Draw(overlay)
        bb = cd.textbbox((0, 0), TEXT, font=cfont)
        cw, ch = bb[2] - bb[0], bb[3] - bb[1]
        pad = max(10, W // 70)
        x, y = W - cw - pad, H - ch - pad - bb[1]
        # brand oxide-red, IBM Plex Mono SemiBold — matches the chart's "Headline CPI"
        cd.text((x, y), TEXT, font=cfont, fill=corner_color + (255,))

    out = Image.alpha_composite(base, overlay)
    return out if img.mode == "RGBA" else out.convert("RGB")


def stamp_file(path, inplace=False, **kw):
    path = Path(path)
    out_path = path if inplace else path.with_name(f"{path.stem}-wm{path.suffix}")
    with Image.open(path) as im:
        res = stamp(im, **kw)
    res.save(out_path)
    return out_path


def _main(argv):
    files = [a for a in argv if not a.startswith("--")]
    flags = {a for a in argv if a.startswith("--")}
    if not files:
        print(__doc__)
        return 1
    kw = dict(diagonal="--no-diagonal" not in flags,
              corner="--no-corner" not in flags)
    inplace = "--inplace" in flags
    for f in files:
        out = stamp_file(f, inplace=inplace, **kw)
        print(f"  ✓ {f} → {out}")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv[1:]))
