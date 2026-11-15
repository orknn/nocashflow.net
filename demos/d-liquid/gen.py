#!/usr/bin/env python3
"""Generate the Faz 4 design demos from REAL site data and content.

    python3 demos/d-liquid/gen.py        (from the repo root)

Writes demos/d-liquid/article.html, article-2.html and data.html. They load the
real /liquid.css + /liquid.js plus the three Faz 4 stylesheets next to this file
(inner.css, article.css, data.css). Chrome comes from build.py's own Liquid
functions, prose from content/articles/, numbers from data/*.json — nothing is
typed in by hand. The markup below is the reference for Faz 5/6.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
import build as B  # noqa: E402

LANG = "en"


def page(title, css, active, body, sw="/tr/"):
    html = f"""<!doctype html>
<html lang="{LANG}">
<head>
<meta charset="utf-8">
<script>document.documentElement.classList.add('js')</script>
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>{title} — Liquid demo</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{B.LIQUID_FONTS_URL}" rel="stylesheet">
<link rel="stylesheet" href="../../liquid.css">
<link rel="stylesheet" href="inner.css">
<link rel="stylesheet" href="{css}">
</head>
<body data-mood="{B._mood()}" class="lq">
<div class="progress" aria-hidden="true"></div>
{B._lq_nav(active, LANG, sw)}
{B._lq_tape(LANG)}
{body}
{B._lq_footer(LANG)}
<script src="../../liquid.js"></script>
</body>
</html>
"""
    return B.inject_market(html)


def split_title(t):
    """'A — B' → A in sans, B in serif italic on its own line."""
    if " — " in t:
        a, b = t.split(" — ", 1)
        return (f'<span class="ln"><span>{a} —</span></span>'
                f'<span class="ln" style="--i:1"><span><em>{b}</em></span></span>')
    return f'<span class="ln"><span>{t}</span></span>'


# ── article ──────────────────────────────────────────────────────────────────
def article(slug):
    a = B.ARTICLES[slug]
    prose = B.gloss_wrap((B.CONTENT / "articles" / slug / f"{LANG}.html").read_text(encoding="utf-8"), LANG)
    prose = prose.replace('src="/', 'src="../../')            # demo is opened from a sub-folder
    idx = B.ARTICLE_ORDER.index(slug)
    newer = B.ARTICLE_ORDER[idx - 1] if idx > 0 else None
    older = B.ARTICLE_ORDER[idx + 1] if idx < len(B.ARTICLE_ORDER) - 1 else None

    def pn(s, label, left):
        if not s:
            return '<div class="pn-card pn-empty"></div>'
        k = f"← {label}" if left else f"{label} →"
        return (f'<a class="pn-card{"" if left else " pn-right"}" href="{B.article_path(s, LANG)}">'
                f'<span class="pn-k">{k}</span><span class="pn-t">{B.ARTICLES[s]["title"][LANG]}</span></a>')

    body = f"""
<header class="p-hero rv" data-rv-now>
  <div class="p-meta mono fade"><span><b>{a['cat'][LANG]}</b> · {a['num']}</span><span>{a['date_disp'][LANG]} · {a['read'][LANG]}</span></div>
  <h1 class="p-title">{split_title(a['title'][LANG])}</h1>
  <div class="p-sub"><p class="p-dek fade" style="--i:4">{a['dek'][LANG]}</p></div>
</header>
<div class="a-wrap">
  <aside class="a-rail mono" data-lq-read aria-hidden="true">
    <span class="pct"><span data-read-pct>0</span><sup>%</sup></span>
    <span class="track"><i></i></span>
    <span>{a['read'][LANG]}</span>
  </aside>
  <div class="a-main">
    <div class="prose article-prose">
{prose}
    </div>
    <div class="share-row">
      <span class="share-k">Share</span>
      <a href="#">X / Twitter</a><a href="#">LinkedIn</a><button type="button">Copy link</button>
    </div>
    <div class="pn-grid">
      {pn(newer, "Newer", True)}
      {pn(older, "Older", False)}
    </div>
    <a class="lk a-back" href="/articles.html">← All articles</a>
  </div>
</div>
"""
    return page(a["title"][LANG], "article.css", "articles", body, B.article_path(slug, "tr"))


# ── charts: stretched SVG (0–100 box) + HTML labels ──────────────────────────
def _smooth(pts):
    d = f"M{pts[0][0]:.2f} {pts[0][1]:.2f}"
    for i in range(len(pts) - 1):
        p0, p1, p2, p3 = pts[max(0, i - 1)], pts[i], pts[i + 1], pts[min(len(pts) - 1, i + 2)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.2f} {c1[1]:.2f} {c2[0]:.2f} {c2[1]:.2f} {p2[0]:.2f} {p2[1]:.2f}"
    return d


def chart(vals, lo, hi, yfmt, xlabels=None, label_all=False, vfmt="{:.2f}", smooth=False):
    n = len(vals)
    pts = [(i / (n - 1) * 100, (1 - (v - lo) / (hi - lo)) * 100) for i, v in enumerate(vals)]
    line = _smooth(pts) if smooth else "M" + " L".join(f"{x:.2f} {y:.2f}" for x, y in pts)
    grid = "".join(f'<line class="grid" x1="0" x2="100" y1="{y}" y2="{y}"/>' for y in (0, 50, 100))
    yl = "".join(f'<span class="yl" style="top:{y}%">{yfmt.format(hi - (hi - lo) * y / 100)}</span>' for y in (0, 50, 100))
    xl = "".join(f'<span class="xl" style="left:{pts[i][0]:.2f}%">{t}</span>' for i, t in enumerate(xlabels or []))
    dots = ""
    for i, (x, y) in enumerate(pts):
        last = i == n - 1
        if label_all or last:
            dots += (f'<span class="pt{" last" if last else ""}" style="left:{x:.2f}%;top:{y:.2f}%"></span>'
                     f'<span class="vl{" alt" if (label_all and i % 2 and not last) else ""}" style="left:{x:.2f}%;top:{y:.2f}%">{vfmt.format(vals[i])}</span>')
    return (f'<div class="ch"><svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">'
            '<defs><linearGradient id="lq-area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="rgba(255,75,38,.28)"/>'
            '<stop offset="1" stop-color="rgba(255,75,38,0)"/></linearGradient></defs>'
            f'{grid}<path class="area" d="{line} L100 100 L0 100 Z"/><path class="line" pathLength="1" d="{line}"/></svg>'
            f'{yl}{xl}{dots}</div>')


def terrain(vals, labels, fallback, pre="", suf="%", dec=2, key=False):
    """Terrain canvas (liquid.js) with the plain line chart as the no-JS fallback."""
    import html as _h, json as _j
    pts = _h.escape(_j.dumps([{"l": l, "v": v} for l, v in zip(labels, vals)], separators=(",", ":")), quote=True)
    lab = ' data-labels="key"' if key else ""
    return (f'<div class="tr"><canvas data-curve="{pts}" data-pre="{pre}" data-suf="{suf}" data-dec="{dec}"'
            f'{lab} aria-hidden="true"></canvas>{fallback}</div>')


def spark(vals, up):
    lo, hi = min(vals), max(vals)
    pts = " L".join(f"{i / (len(vals) - 1) * 100:.1f} {28 - (v - lo) / ((hi - lo) or 1) * 26:.1f}" for i, v in enumerate(vals))
    return f'<svg viewBox="0 0 100 30" preserveAspectRatio="none" aria-hidden="true"><path class="{"up" if up else "dn"}" d="M{pts}"/></svg>'


def pct(v):
    if v is None:
        return '<td class="num">—</td>'
    return f'<td class="num"><span class="pc {"up" if v >= 0 else "dn"}">{"+" if v >= 0 else "−"}{abs(v):.2f}%</span></td>'


# ── data page (macro layout + dashboard component sheet) ─────────────────────
def kpis(section, cls=""):
    M = B.MACRO2
    labels = B.MACRO2_LABELS[section][LANG]
    stats = M.get(section) if section in ("inflation", "growth") else M.get(section, {}).get("stats", [])
    return f'<div class="kpis{cls} rv">' + "".join(
        f'<div class="kpi fade" style="--i:{i}"><div class="lab">{labels[i]}</div>'
        f'<div><div class="big" data-scr>{s.get("v", "—")}</div>'
        + (f'<div class="sub {s.get("dir", "neu")}">{s["sub"]}</div>' if s.get("sub") else "")
        + "</div></div>" for i, s in enumerate(stats)) + "</div>"


def sec(num, title, meta):
    return (f'<div class="sec-h sm rv"><span class="mono">§ {num}</span>'
            f'<h2><span class="ln"><span>{title}</span></span></h2><span class="meta mono">{meta}</span></div>')


def data():
    M, MK = B.MACRO2, B.MARKETS
    odds = B._lq_upcoming_odds(M["fed"]["cut_odds"], M.get("updated", ""))
    top = max([o["p"] for o in odds] + [10])
    odds_html = "".join(
        f'<div class="odd"><span class="mono">{o["m"]}</span><span class="bar"><i data-w="{o["p"] / top * 100:.1f}" style="--w:{o["p"] / top * 100:.1f}%"></i></span>'
        f'<span class="p">{o["p"]}%</span><span class="mv">{o["d"] if o.get("d") and o["d"] != "implied" else ""}</span></div>' for o in odds)

    liq = M["liquidity"]
    liq_chart = chart(liq["net_liq_series"], liq["y_min"], liq["y_max"], "${:.1f}T", vfmt="${:.2f}T")
    ls = liq["net_liq_series"]
    liq_chart = terrain(ls, [""] * len(ls), liq_chart, pre="$", suf="T", key=True)
    cv = M["rates"]["curve"]
    ys = [c["y"] for c in cv]
    curve_chart = chart(ys, min(ys) - .2, max(ys) + .2, "{:.1f}%", [c["tenor"] for c in cv], True, "{:.2f}", True)

    curve_chart = terrain(ys, [c["tenor"] for c in cv], curve_chart)

    rows, prev = [], None
    for e in B.CALENDAR.get("events", [])[:B.CAL_MAX_ROWS]:
        flag, ccy = B.COUNTRY.get(e.get("country", ""), ("", e.get("country", "")))
        hi = e.get("impact") == "high"
        first = e.get("wd") != prev
        prev = e.get("wd")
        act = e.get("act", "—")
        rows.append(
            f'<tr{" class=d0" if first else ""}><td class="day">{B.WEEKDAYS[LANG][e["wd"]] if first else ""}</td><td>{e.get("time", "")}</td>'
            f'<td class="ev{" hi" if hi else ""}"><span class="imp{" hi" if hi else ""}"></span>{e.get("event", "")}</td>'
            f'<td>{flag} {ccy}</td><td class="num">{e.get("prev", "—")}</td><td class="num">{e.get("est", "—")}</td>'
            f'<td class="num{" act" if act != "—" else ""}">{act}</td></tr>')

    tiles = "".join(
        f'<div class="tile fade" style="--i:{i}"><div class="top"><span class="nm">{q["name"]}</span><span class="sym">{q["sym"]}</span></div>'
        f'<div class="px" data-scr>{q["price"]:,.2f}</div><div class="d {"up" if q["d1"] >= 0 else "dn"}">{"+" if q["d1"] >= 0 else "−"}{abs(q["d1"]):.2f}%</div>'
        f'{spark(q["spark30"], q["spark30"][-1] >= q["spark30"][0])}</div>' for i, q in enumerate(MK["indices"][:8]))
    mx = max(abs(s["d1"]) for s in MK["sectors"]) or 1
    heat = "".join(
        f'<div class="hc {"up" if s["d1"] >= 0 else "dn"}" style="--a:{min(1, abs(s["d1"]) / mx):.2f}"><span class="nm">{s["name"]}</span>'
        f'<span class="v">{"+" if s["d1"] >= 0 else "−"}{abs(s["d1"]):.2f}%</span></div>' for s in sorted(MK["sectors"], key=lambda s: -s["d1"]))
    leaders = "".join(
        f'<tr><td class="nm">{q["sym"]}<small>{q["name"]}</small></td><td class="num">{q["price"]:,.2f}</td><td class="num">{q["mcap"]}</td>'
        + "".join(pct(q["perf"].get(k)) for k in ("d1", "d7", "d30", "d180", "y1", "y5")) + "</tr>" for q in MK["leaders_equity"][:8])
    cb = MK["crypto_board"]
    facts = "".join(f'<div><div class="k">{k}</div><div class="v" data-scr>{v}</div><div class="s">{s}</div></div>' for k, v, s in [
        ("Total market cap", "$" + cb["total_mcap"]["v"], f'{cb["total_mcap"]["chg"]:+.1f}% 24h'),
        ("BTC dominance", f'{cb["btc_dom"]["v"]}%', f'{cb["btc_dom"]["chg_pp"]:+.1f} pp'),
        ("Stablecoins", "$" + cb["stables"]["v"], f'{cb["stables"]["chg"]:+.1f}% 30d'),
        ("USDC share", f'{cb["usdc_share"]["v"]}%', f'{cb["usdc_share"]["chg_pp"]:+.1f} pp'),
        ("BTC funding", f'{cb["funding"]["v"]:+.3f}%', "8h · Deribit")])

    regime = "".join(
        f'<div class="rg fade" style="--i:{i}"><span class="k mono">{c["k"]}</span><div><div class="v" data-scr>{c["v"]}</div>'
        f'<div class="d mono">{c.get("d") or "&nbsp;"}</div></div></div>' for i, c in enumerate(M["regime_tape"]))

    body = f"""
<header class="p-hero rv" data-rv-now>
  <div class="p-meta mono fade"><span><b>Macro</b> · The Regime</span></div>
  <h1 class="p-title"><span class="ln"><span>Where the economy</span></span><span class="ln" style="--i:1"><span><em>actually</em> stands.</span></span></h1>
  <div class="p-sub">
    <p class="p-dek fade" style="--i:4">Not a price board — the readings that set the regime. Inflation, the Fed, liquidity and the curve, each with the read that matters. Updated as the data prints.</p>
    <div class="p-aside mono fade" style="--i:5">Updated<br>{B._lq_date(M.get("updated"), LANG, True)}</div>
  </div>
</header>

<section class="sec tight nt"><div class="regime rv">{regime}</div></section>

<section class="sec tight">
  {sec("01", "Inflation &amp; <em>prices</em>", "FRED · last print")}
  {kpis("inflation")}
</section>

<section class="sec tight">
  {sec("02", "Fed &amp; <em>policy</em>", "prediction-market implied")}
  <div class="split rv">
    <div class="panel"><h4>Rate-cut odds — next FOMC meetings</h4><div class="cap">Polymarket · probability of a cut at each meeting</div><div class="odds">{odds_html}</div></div>
    {kpis("fed", " c2")}
  </div>
</section>

<section class="sec tight">
  {sec("03", "<em>Liquidity</em>", "the tide under every risk asset")}
  <div class="split rv">
    <div class="panel"><h4>Net liquidity — Fed balance sheet − TGA − RRP</h4><div class="cap">weekly · USD trn</div>{liq_chart}</div>
    {kpis("liquidity", " c2")}
  </div>
</section>

<section class="sec tight">
  {sec("04", "Growth &amp; <em>labor</em>", "is the landing soft?")}
  {kpis("growth")}
</section>

<section class="sec tight">
  {sec("05", "Rates &amp; <em>the dollar</em>", "FRED · the curve")}
  <div class="split rv">
    <div class="panel"><h4>US Treasury yield curve</h4><div class="cap">tenor vs. yield · the desk's signature read</div>{curve_chart}</div>
    {kpis("rates", " c2")}
  </div>
</section>

<section class="sec tight">
  {sec("06", "This <em>week</em>", '<a class="lk" href="/calendar.html">Full week →</a>')}
  <div class="dt-wrap rv"><table class="dt">
    <thead><tr><th>Day</th><th>Time (CET)</th><th>Event</th><th>Country</th><th class="num">Prev.</th><th class="num">Cons.</th><th class="num">Actual</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
</section>

<div class="demo-div mono">Demo only ↓ dashboard component sheet — same system, real data/markets.json</div>

<section class="sec tight">
  {sec("A", "Instrument <em>tiles</em>", "price · 1D · 30-day sparkline")}
  <div class="tiles rv">{tiles}</div>
</section>
<section class="sec tight">
  {sec("B", "Sector <em>heatmap</em>", "1D · tint = size of the move")}
  <div class="heat rv">{heat}</div>
</section>
<section class="sec tight">
  {sec("C", "Leaders <em>table</em>", "multi-horizon")}
  <div class="dt-wrap rv"><table class="dt">
    <thead><tr><th>Name</th><th class="num">Price</th><th class="num">Mkt cap</th><th class="num">1D</th><th class="num">7D</th><th class="num">30D</th><th class="num">180D</th><th class="num">1Y</th><th class="num">5Y</th></tr></thead>
    <tbody>{leaders}</tbody>
  </table></div>
</section>
<section class="sec tight">
  {sec("D", "Fact <em>row</em>", "crypto board")}
  <div class="facts rv">{facts}</div>
</section>
"""
    return page("Macro", "data.css", "macro", body, "/tr/macro.html")


if __name__ == "__main__":
    (HERE / "article.html").write_text(article("cekirdek"), encoding="utf-8")
    (HERE / "article-2.html").write_text(article("enflasyon"), encoding="utf-8")
    (HERE / "data.html").write_text(data(), encoding="utf-8")
    print("wrote article.html, article-2.html, data.html")
