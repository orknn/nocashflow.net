#!/usr/bin/env python3
"""NoCashFlow publisher logo generator.

Builds the "N /" Fraunces monogram tile (the same family as favicon.svg) and
exports SVG masters + PNG rasters. Glyph outlines drive both SVG and PNG so the
two stay pixel-consistent. Self-contained: no font dependency in the SVG.
"""
import math, os
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "..", "assets", "fonts", "Fraunces.ttf")

# ---- brand ----
OXIDE = (0xB0, 0x44, 0x2B)   # #B0442B
CREAM = (0xF3, 0xEE, 0xE3)   # #F3EEE3
OXIDE_HEX = "#B0442B"
CREAM_HEX = "#F3EEE3"

SIZE = 512                    # design space / master size
CENTER = SIZE / 2
R_SAFE = 222                  # circular safe-zone radius (Google circle-crop)
GAP = 1640                    # slash x-origin rel. to N: clean channel, no collision
RULE_MIN_PX = 96              # baseline rule only on larger exports (mud at <=32px)

font = TTFont(FONT)
cmap = font.getBestCmap()
gs = font.getGlyphSet()

def flatten_quad(p0, c, p1, n=14):
    out = []
    for i in range(1, n + 1):
        t = i / n
        u = 1 - t
        x = u*u*p0[0] + 2*u*t*c[0] + t*t*p1[0]
        y = u*u*p0[1] + 2*u*t*c[1] + t*t*p1[1]
        out.append((x, y))
    return out

def flatten_cubic(p0, c1, c2, p1, n=18):
    out = []
    for i in range(1, n + 1):
        t = i / n; u = 1 - t
        x = u**3*p0[0] + 3*u*u*t*c1[0] + 3*u*t*t*c2[0] + t**3*p1[0]
        y = u**3*p0[1] + 3*u*u*t*c1[1] + 3*u*t*t*c2[1] + t**3*p1[1]
        out.append((x, y))
    return out

def glyph_contours(gname, dx=0.0, dy=0.0):
    """Return list of contours (each a list of (x,y) font-unit points, y-up)."""
    pen = RecordingPen()
    gs[gname].draw(pen)
    contours, cur, start = [], [], (0, 0)
    pt = (0, 0)
    for op, args in pen.value:
        if op == "moveTo":
            if cur: contours.append(cur)
            start = args[0]; pt = start; cur = [start]
        elif op == "lineTo":
            pt = args[0]; cur.append(pt)
        elif op == "qCurveTo":
            pts = list(args)
            on_end = pts[-1] if pts[-1] is not None else start
            offs = pts[:-1]
            prev = pt
            for i, off in enumerate(offs):
                on = on_end if i == len(offs)-1 else (
                    (off[0]+offs[i+1][0])/2, (off[1]+offs[i+1][1])/2)
                cur.extend(flatten_quad(prev, off, on)); prev = on
            pt = on_end
        elif op == "curveTo":
            prev = pt
            # generic cubic (handles n control pts pairwise; fonts rarely hit this)
            a = list(args); c1, c2, end = a[0], a[1], a[2]
            cur.extend(flatten_cubic(prev, c1, c2, end)); pt = end
        elif op == "closePath":
            if cur: contours.append(cur); cur = []
    if cur: contours.append(cur)
    return [[(x+dx, y+dy) for (x, y) in c] for c in contours]

def glyph_svg_d(gname):
    pen = SVGPathPen(gs)
    gs[gname].draw(pen)
    return pen.getCommands()

# ---- assemble monogram in font units (y-up) ----
contours = []
contours += glyph_contours(cmap[ord("N")], 0, 0)
contours += glyph_contours(cmap[ord("/")], GAP, 0)

# baseline rule (font units), centered under the monogram ink width
allx = [x for c in contours for x, y in c]
ally = [y for c in contours for x, y in c]
mono_xmin, mono_xmax = min(allx), max(allx)
mono_ymin, mono_ymax = min(ally), max(ally)
mono_cx = (mono_xmin + mono_xmax) / 2

rule_w = (mono_xmax - mono_xmin) * 0.52
rule_h = 78
rule_top = mono_ymin - 250          # gap below the slash descender
rule_bot = rule_top - rule_h
rule = [(mono_cx-rule_w/2, rule_bot), (mono_cx+rule_w/2, rule_bot),
        (mono_cx+rule_w/2, rule_top), (mono_cx-rule_w/2, rule_top)]
fit_shapes = list(contours) + [rule]   # rule always defines the master layout

# ---- fit composition into the safe circle, centered ----
fx = [x for c in fit_shapes for x, y in c]
fy = [y for c in fit_shapes for x, y in c]
bx0, bx1, by0, by1 = min(fx), max(fx), min(fy), max(fy)
cx, cy = (bx0+bx1)/2, (by0+by1)/2
half_diag = 0.5 * math.hypot(bx1-bx0, by1-by0)
s = R_SAFE / half_diag                       # font-units -> design px

def to_design(p):
    # center composition at tile center; flip y (font y-up -> svg y-down)
    return (CENTER + (p[0]-cx)*s, CENTER - (p[1]-cy)*s)

# ---- SVG emit ----
# build a single transform that maps font-unit glyph coords to design space
# design_x = CENTER + (X - cx)*s ; design_y = CENTER - (Y - cy)*s
#          = (s)*X + (CENTER - cx*s)         for x
#          = (-s)*Y + (CENTER + cy*s)        for y
A, E = s, -s
C_, F_ = CENTER - cx*s, CENTER + cy*s
TRANSFORM = f"matrix({A:.6f} 0 0 {E:.6f} {C_:.6f} {F_:.6f})"
N_D = glyph_svg_d(cmap[ord("N")])
SLASH_D = glyph_svg_d(cmap[ord("/")])

p = [to_design(pt) for pt in rule]
rx0 = min(q[0] for q in p); rx1 = max(q[0] for q in p)
ry0 = min(q[1] for q in p); ry1 = max(q[1] for q in p)
rh = ry1-ry0
rule_svg = (f'\n  <rect x="{rx0:.2f}" y="{ry0:.2f}" width="{rx1-rx0:.2f}" '
            f'height="{rh:.2f}" rx="{rh/2:.2f}" fill="{{fg}}"/>')

def svg(bg, fg, transparent_bg=False):
    if transparent_bg:
        bg_rect = ""
    else:
        bg_rect = f'\n  <rect width="{SIZE}" height="{SIZE}" fill="{bg}"/>'
    body = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE} {SIZE}" '
            f'width="{SIZE}" height="{SIZE}" role="img" aria-label="NoCashFlow">'
            f'{bg_rect}'
            f'\n  <g fill="{fg}" transform="{TRANSFORM}">'
            f'\n    <path d="{N_D}"/>'
            f'\n    <g transform="translate({GAP} 0)"><path d="{SLASH_D}"/></g>'
            f'\n  </g>'
            f'{rule_svg.format(fg=fg)}'
            f'\n</svg>\n')
    return body

with open(os.path.join(HERE, "logo.svg"), "w") as f:
    f.write(svg(OXIDE_HEX, CREAM_HEX))                     # solid red tile
with open(os.path.join(HERE, "logo-transparent.svg"), "w") as f:
    f.write(svg(OXIDE_HEX, OXIDE_HEX, transparent_bg=True))  # red mark, no bg

# ---- PNG raster (supersampled) ----
from PIL import ImageChops
def render_png(px, bg, fg, transparent=False, ss=4):
    W = px*ss
    img = Image.new("RGBA", (W, W), (0,0,0,0) if transparent else bg+(255,))
    k = (W / SIZE)
    def dp(p):
        q = to_design(p); return (q[0]*k, q[1]*k)
    draw_shapes = list(contours) + ([rule] if px >= RULE_MIN_PX else [])
    # even-odd fill via XOR mask (handles counters if glyphs ever have them)
    mask = Image.new("L", (W, W), 0)
    for c in draw_shapes:
        layer = Image.new("L", (W, W), 0)
        ImageDraw.Draw(layer).polygon([dp(pt) for pt in c], fill=255)
        mask = ImageChops.difference(mask, layer)  # XOR for binary masks
    fg_img = Image.new("RGBA", (W, W), fg+(255,))
    img = Image.composite(fg_img, img, mask)
    return img.resize((px, px), Image.LANCZOS)

# solid tile (PRIMARY): logo.png 512 + 256 + 112, plus favicon sizes
for px, name in [(512,"logo.png"), (256,"logo-256.png"), (112,"logo-112.png"),
                 (32,"logo-32.png"), (16,"logo-16.png")]:
    # flatten onto opaque oxide background -> true solid tile, no alpha
    flat = Image.new("RGB", (px, px), OXIDE)
    flat.paste(render_png(px, OXIDE, CREAM).convert("RGB"), (0,0))
    flat.save(os.path.join(HERE, name))
# transparent variant: red mark on transparency (512 + 256)
for px, name in [(512,"logo-transparent.png"), (256,"logo-transparent-256.png")]:
    render_png(px, OXIDE, OXIDE, transparent=True).save(os.path.join(HERE, name))

# ============================================================================
# BONUS: horizontal lockup  [tile] NO/CASHFLOW
# ============================================================================
INK = (0x16, 0x18, 0x1C); INK_HEX = "#16181C"
def layout(strng):
    x = 0; items = []
    for ch in strng:
        g = cmap[ord(ch)]; items.append((g, x)); x += font["hmtx"][g][0]
    return items, x

WORD = "NO/CASHFLOW"
items, adv = layout(WORD)
CAP = 1400
PAD = 46
TILE = 248
GAPLR = 56
word_cap_px = 150
sw = word_cap_px / CAP
word_w = adv * sw
LH = TILE + 2*PAD
LW = PAD + TILE + GAPLR + int(word_w) + PAD
By = PAD + TILE/2 + word_cap_px/2 - 8   # baseline (optical centre)
Bx = PAD + TILE + GAPLR

# --- lockup SVG ---
tile_scale = TILE / SIZE
tile_inner = (f'<g transform="translate({PAD} {PAD}) scale({tile_scale:.5f})">'
              f'<rect width="{SIZE}" height="{SIZE}" rx="96" fill="{OXIDE_HEX}"/>'
              f'<g fill="{CREAM_HEX}" transform="{TRANSFORM}">'
              f'<path d="{N_D}"/>'
              f'<g transform="translate({GAP} 0)"><path d="{SLASH_D}"/></g></g>'
              f'{rule_svg.format(fg=CREAM_HEX)}</g>')
word_paths = []
for g, gx in items:
    word_paths.append(f'<g transform="translate({gx} 0)"><path d="{glyph_svg_d(g)}"/></g>')
word_g = (f'<g fill="{INK_HEX}" '
          f'transform="matrix({sw:.6f} 0 0 {-sw:.6f} {Bx:.3f} {By:.3f})">'
          + "".join(word_paths) + "</g>")
lockup_svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {LW} {LH}" '
              f'width="{LW}" height="{LH}" role="img" aria-label="NO/CASHFLOW">'
              f'{tile_inner}{word_g}</svg>\n')
with open(os.path.join(HERE, "lockup-horizontal.svg"), "w") as f:
    f.write(lockup_svg)

# --- lockup PNG (transparent bg) ---
def render_lockup(scale_px_per_unit_ss, ss=4):
    W, H = LW*ss, LH*ss
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    tile = render_png(TILE*ss, OXIDE, CREAM).convert("RGBA")  # reuse tile raster
    # round the tile corners to match SVG rx=96
    rad = int(96*tile_scale*ss)
    m = Image.new("L", tile.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0,0,tile.size[0]-1,tile.size[1]-1], rad, fill=255)
    img.paste(tile, (PAD*ss, PAD*ss), m)
    # wordmark
    mask = Image.new("L", (W, H), 0)
    for g, gx in items:
        for c in glyph_contours(g, gx, 0):
            layer = Image.new("L", (W, H), 0)
            pts = [(Bx*ss + X*sw*ss, By*ss - Y*sw*ss) for (X, Y) in c]
            ImageDraw.Draw(layer).polygon(pts, fill=255)
            mask = ImageChops.difference(mask, layer)
    ink_img = Image.new("RGBA", (W, H), INK+(255,))
    img = Image.composite(ink_img, img, mask)
    return img.resize((LW, LH), Image.LANCZOS)
render_lockup(1).save(os.path.join(HERE, "lockup-horizontal.png"))

print("fit scale s = %.5f  -> cap height %.1f px, mono width %.1f px"
      % (s, 1400*s, (mono_xmax-mono_xmin)*s))
print("lockup: %dx%d" % (LW, LH))
print("wrote:", sorted(f for f in os.listdir(HERE) if not f.startswith("_")))
