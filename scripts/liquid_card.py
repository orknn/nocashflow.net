#!/usr/bin/env python3
"""
Shared drawing kit for the Liquid social cards (1200x630).

Used by make_article_card.py, make_og_image.py and make_share_image.py so the
three cards speak the site's language: bone / ink, the #FF4B26 accent,
Bricolage Grotesque + Instrument Serif italic + Geist Mono, and the layered
"terrain" lines of the site's charts.

Everything is drawn at 2x and downsampled once (Canvas.save), so thin lines and
tight tracking stay crisp. Coordinates and sizes in the callers are 1x pixels.
"""
import math
import random
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"

# tokens — mirror liquid.css :root
BONE   = (236, 234, 227)
BONE_2 = (225, 222, 213)
INK    = (11, 12, 15)
INK_2  = (27, 29, 34)
DIM    = (69, 66, 61)
MUTE   = (95, 93, 88)
HOT    = (255, 75, 38)
MOOD   = (111, 178, 255)
UP     = (47, 191, 113)       # on dark
UP_T   = (20, 113, 63)        # on bone (AA)
DN_T   = (173, 43, 17)        # on bone (AA)
DN     = (255, 122, 92)       # on dark

W, H = 1200, 630
S = 2                         # supersampling factor

_TR_UP = str.maketrans({"i": "İ", "ı": "I"})


def upper(text, lang=None):
    """Uppercase that respects Turkish dotted/dotless i when lang == 'tr'."""
    return text.translate(_TR_UP).upper() if lang == "tr" else text.upper()


def sans(size, wght=500):
    f = ImageFont.truetype(str(FONTS / "BricolageGrotesque.ttf"), int(size * S))
    try:                                   # axes: optical size, weight, width
        f.set_variation_by_axes([max(12, min(96, size)), wght, 100])
    except Exception:
        pass
    return f


def serif_it(size):
    return ImageFont.truetype(str(FONTS / "InstrumentSerif-Italic.ttf"), int(size * S))


def mono(size, wght=400):
    f = ImageFont.truetype(str(FONTS / "GeistMono.ttf"), int(size * S))
    try:
        f.set_variation_by_axes([wght])
    except Exception:
        pass
    return f


class Canvas:
    """A 2x RGB canvas addressed in 1x coordinates."""

    def __init__(self, bg):
        self.img = Image.new("RGB", (W * S, H * S), bg)
        self.d = ImageDraw.Draw(self.img)

    # ── text ────────────────────────────────────────────────────────────────
    def width(self, text, font, track=0.0):
        """1x width of text with `track` em of letter-spacing."""
        if not text:
            return 0
        if not track:
            return self.d.textlength(text, font=font) / S
        adv = sum(self.d.textlength(ch, font=font) for ch in text)
        return (adv + track * font.size * (len(text) - 1)) / S

    def text(self, xy, text, font, fill, track=0.0, anchor="ls"):
        """Draw on the baseline (anchor 'ls') with letter-spacing; returns end x (1x)."""
        x, y = xy[0] * S, xy[1] * S
        if not track:
            self.d.text((x, y), text, font=font, fill=fill, anchor=anchor)
            return (x + self.d.textlength(text, font=font)) / S
        step = track * font.size
        for ch in text:
            self.d.text((x, y), ch, font=font, fill=fill, anchor=anchor)
            x += self.d.textlength(ch, font=font) + step
        return (x - step) / S

    def text_right(self, xr, y, text, font, fill, track=0.0):
        return self.text((xr - self.width(text, font, track), y), text, font, fill, track)

    def wrap(self, text, font, maxw, track=0.0):
        out, cur = [], ""
        for word in text.split():
            t = (cur + " " + word).strip()
            if self.width(t, font, track) <= maxw or not cur:
                cur = t
            else:
                out.append(cur)
                cur = word
        if cur:
            out.append(cur)
        return out

    def wrap_balanced(self, text, font, maxw, track=0.0):
        """Same line count as wrap(), but the narrowest width that keeps it —
        so a headline never ends on a one-word orphan line."""
        lines = self.wrap(text, font, maxw, track)
        if len(lines) < 2:
            return lines
        lo, hi = maxw * 0.4, maxw
        for _ in range(12):
            mid = (lo + hi) / 2
            if len(self.wrap(text, font, mid, track)) <= len(lines):
                hi = mid
            else:
                lo = mid
        return self.wrap(text, font, hi, track)

    # ── shapes ──────────────────────────────────────────────────────────────
    def line(self, x0, y0, x1, y1, fill, width=1):
        self.d.line([x0 * S, y0 * S, x1 * S, y1 * S], fill=fill, width=max(1, int(width * S)))

    def rrect(self, box, radius, fill=None, outline=None, width=1):
        self.d.rounded_rectangle([v * S for v in box], radius=radius * S, fill=fill,
                                 outline=outline, width=max(1, int(width * S)))

    def dot(self, x, y, r, fill):
        self.d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=fill)

    def wordmark(self, x, y, size, ink=INK, wght=800):
        """NO/CASHFLOW on the baseline, orange slash; returns end x."""
        f = sans(size, wght)
        x = self.text((x, y), "NO", f, ink, -0.045)
        x = self.text((x - size * 0.01, y), "/", f, HOT, 0)
        return self.text((x - size * 0.03, y), "CASHFLOW", f, ink, -0.045)

    def wordmark_width(self, size, wght=800):
        f = sans(size, wght)
        return (self.width("NO", f, -0.045) + self.width("/", f) + self.width("CASHFLOW", f, -0.045)
                - size * 0.04)

    # ── dark stage + terrain ────────────────────────────────────────────────
    def stage(self, box, radius=28, mood=MOOD, glow=True, strength=1.0):
        """Dark rounded panel with the site's mood glow (top right) and a warm
        ember (bottom left). Returns the box for chaining."""
        x0, y0, x1, y1 = [int(v * S) for v in box]
        w, h = x1 - x0, y1 - y0
        panel = Image.new("RGB", (w, h), INK)
        if glow:
            # radii follow the short side, so a wide strip is not flooded with colour
            m = min(w, h)
            for colour, cx, cy, rx, ry, a in ((mood, .84, 0.0, 2.2, 1.0, .20), (HOT, 0.0, 1.0, 1.1, .8, .13)):
                g = Image.new("L", (w, h), 0)
                gd = ImageDraw.Draw(g)
                ex, ey = int(m * rx), int(m * ry)
                gd.ellipse([int(w * cx) - ex, int(h * cy) - ey, int(w * cx) + ex, int(h * cy) + ey],
                           fill=int(255 * a * strength))
                g = g.filter(ImageFilter.GaussianBlur(m * 0.3))
                panel = Image.composite(Image.new("RGB", (w, h), colour), panel, g)
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius * S, fill=255)
        self.img.paste(panel, (x0, y0), mask)
        self.d = ImageDraw.Draw(self.img)
        return box

    def terrain(self, box, values=None, seed=0, layers=18, lift=0.55, dots=True, pad=(0, 0)):
        """The site's chart landscape inside `box` (1x): a glowing orange front
        line with the same curve receding behind it in fading blue.

        values  real series to draw (e.g. the yield curve); when None a smooth
                deterministic curve is made from `seed`
        lift    how far the back layers climb, as a share of the box height
        """
        x0, y0, x1, y1 = [v * S for v in box]
        px, py = pad[0] * S, pad[1] * S
        w, h = x1 - x0, y1 - y0
        n = 160
        if values and len(values) >= 2:
            lo, hi = min(values), max(values)
            span = (hi - lo) or 1.0
            ctrl = [(v - lo) / span for v in values]
        else:
            rnd = random.Random(seed)
            ph = [rnd.uniform(0, math.tau) for _ in range(3)]
            amp = [rnd.uniform(.5, 1), rnd.uniform(.25, .6), rnd.uniform(.1, .3)]
            drift = rnd.uniform(.25, .75) * rnd.choice((-1, 1))
            raw = [amp[0] * math.sin(1.1 * math.tau * t + ph[0]) + amp[1] * math.sin(2.3 * math.tau * t + ph[1])
                   + amp[2] * math.sin(4.1 * math.tau * t + ph[2]) + drift * 2.2 * t
                   for t in (i / 9 for i in range(10))]
            lo, hi = min(raw), max(raw)
            ctrl = [(v - lo) / ((hi - lo) or 1.0) for v in raw]

        def at(t):                                       # smooth (cosine) interpolation
            p = t * (len(ctrl) - 1)
            i = min(int(p), len(ctrl) - 2)
            f = (1 - math.cos((p - i) * math.pi)) / 2
            return ctrl[i] * (1 - f) + ctrl[i + 1] * f

        front_h = h * (1 - lift) - 2 * py
        base_y = y1 - py
        pts = [(x0 + px + (w - 2 * px) * i / (n - 1), base_y - at(i / (n - 1)) * front_h) for i in range(n)]

        layer = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        for k in range(layers, 0, -1):                   # back to front
            f = k / layers
            dy = f * h * lift
            shrink = 1 - 0.16 * f                        # perspective: far lines are narrower
            cx = (x0 + x1) / 2 + w * 0.05 * f
            poly = [(cx + (x - (x0 + x1) / 2) * shrink, y - dy) for x, y in pts]
            a = int(150 * (1 - f) ** 1.4 + 22)
            ld.line(poly, fill=MOOD + (a,), width=max(1, int(S * 0.7)), joint="curve")
        self.img.paste(layer, (0, 0), layer)

        glow = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        ImageDraw.Draw(glow).line(pts, fill=HOT + (210,), width=5 * S, joint="curve")
        glow = glow.filter(ImageFilter.GaussianBlur(7 * S))
        self.img.paste(glow, (0, 0), glow)
        self.d = ImageDraw.Draw(self.img)
        self.d.line(pts, fill=HOT, width=int(1.6 * S), joint="curve")
        if dots:
            marks = range(len(ctrl)) if values else (1, 3, 5, 7, 9)
            for j in marks:
                i = round(j / (len(ctrl) - 1) * (n - 1))
                x, y = pts[i]
                r = 3.6 * S
                self.d.ellipse([x - r, y - r, x + r, y + r], fill=INK, outline=BONE, width=int(1.3 * S))
        return [(x / S, y / S) for x, y in pts]

    # ── output ──────────────────────────────────────────────────────────────
    def save(self, path, stamp=None):
        out = self.img.resize((W, H), Image.LANCZOS)
        if stamp:
            out = stamp(out, corner=False).convert("RGB")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        out.save(path, "PNG", optimize=True)
        return path


def seed_of(text):
    """Stable seed from a string (hash() is salted per process)."""
    s = 0
    for ch in text:
        s = (s * 131 + ord(ch)) % 2147483647
    return s
