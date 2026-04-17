#!/usr/bin/env python3
"""
NoCashFlow site builder.
Generates all pages with shared nav/ticker/footer from a single source of truth.
Run: python3 build.py
Output: HTML files written to ./
"""
import os, sys, textwrap
from pathlib import Path

OUT = Path(__file__).parent

# ============================================================
# SHARED CHROME
# ============================================================

HEAD = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{title}</title>
<meta name="description" content="{desc}" />
<meta property="og:title" content="{title}" />
<meta property="og:description" content="{desc}" />
<meta property="og:type" content="website" />
<meta property="og:site_name" content="NoCashFlow" />
<meta property="og:image" content="https://nocashflow.net/assets/og.png" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:site" content="@No_CashFlow" />
<meta name="theme-color" content="#0b0b0d" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300..900;1,9..144,300..900&family=IBM+Plex+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="assets/site.css" />
</head>
<body>'''

TICKER = '''
<div class="ticker" data-ticker-live>
  <div class="ticker-label"><span class="dot"></span> LIVE</div>
  <div class="ticker-track">
    <div class="tick" data-sym="BTC"><span class="sym">BTC</span><span class="px">$67,420</span><span class="chg dn">-1.82%</span></div>
    <div class="tick" data-sym="ETH"><span class="sym">ETH</span><span class="px">$3,284</span><span class="chg dn">-2.41%</span></div>
    <div class="tick"><span class="sym">GOLD</span><span class="px">$2,614</span><span class="chg up">+0.74%</span></div>
    <div class="tick"><span class="sym">BRENT</span><span class="px">$106.12</span><span class="chg up">+3.12%</span></div>
    <div class="tick"><span class="sym">DXY</span><span class="px">104.28</span><span class="chg up">+0.46%</span></div>
    <div class="tick"><span class="sym">US10Y</span><span class="px">4.38%</span><span class="chg up">+4bp</span></div>
    <div class="tick"><span class="sym">VIX</span><span class="px">26.8</span><span class="chg up">+2.1%</span></div>
    <div class="tick"><span class="sym">F&amp;G</span><span class="px">18</span><span class="chg dn">EXTREME FEAR</span></div>
    <div class="tick"><span class="sym">COPPER</span><span class="px">$4.28</span><span class="chg up">+0.38%</span></div>
    <div class="tick"><span class="sym">SPX</span><span class="px">5,684</span><span class="chg dn">-0.62%</span></div>
    <div class="tick"><span class="sym">EUR/USD</span><span class="px">1.0684</span><span class="chg dn">-0.21%</span></div>
    <div class="tick"><span class="sym">USD/TRY</span><span class="px">34.82</span><span class="chg up">+0.11%</span></div>
    <div class="tick" data-sym="BTC"><span class="sym">BTC</span><span class="px">$67,420</span><span class="chg dn">-1.82%</span></div>
    <div class="tick" data-sym="ETH"><span class="sym">ETH</span><span class="px">$3,284</span><span class="chg dn">-2.41%</span></div>
    <div class="tick"><span class="sym">GOLD</span><span class="px">$2,614</span><span class="chg up">+0.74%</span></div>
    <div class="tick"><span class="sym">BRENT</span><span class="px">$106.12</span><span class="chg up">+3.12%</span></div>
    <div class="tick"><span class="sym">DXY</span><span class="px">104.28</span><span class="chg up">+0.46%</span></div>
    <div class="tick"><span class="sym">US10Y</span><span class="px">4.38%</span><span class="chg up">+4bp</span></div>
    <div class="tick"><span class="sym">VIX</span><span class="px">26.8</span><span class="chg up">+2.1%</span></div>
    <div class="tick"><span class="sym">F&amp;G</span><span class="px">18</span><span class="chg dn">EXTREME FEAR</span></div>
    <div class="tick"><span class="sym">COPPER</span><span class="px">$4.28</span><span class="chg up">+0.38%</span></div>
    <div class="tick"><span class="sym">SPX</span><span class="px">5,684</span><span class="chg dn">-0.62%</span></div>
    <div class="tick"><span class="sym">EUR/USD</span><span class="px">1.0684</span><span class="chg dn">-0.21%</span></div>
    <div class="tick"><span class="sym">USD/TRY</span><span class="px">34.82</span><span class="chg up">+0.11%</span></div>
  </div>
</div>
'''

NAV = '''
<nav class="nav">
  <div class="nav-inner">
    <a href="index.html" class="logo">NO<span class="slash">/</span>CASHFLOW<span class="tag">MACRO &times; MARKETS</span></a>
    <div class="nav-links">
      <a href="index.html">Home</a>
      <a href="yazilar.html">Sunday</a>
      <a href="bulletin.html">Bulletin</a>
      <a href="macro.html">Macro</a>
      <a href="crypto.html">Crypto</a>
      <a href="dashboard.html">Dashboard</a>
    </div>
    <div class="nav-right">
      <button class="nav-btn menu-toggle" aria-label="Menu">&#9776;</button>
      <button class="nav-btn" aria-label="Language" onclick="alert('TR version coming')">TR</button>
      <a href="#newsletter" class="subscribe">Subscribe</a>
    </div>
  </div>
</nav>
'''

NEWSLETTER = '''
<section class="newsletter" id="newsletter">
  <div class="newsletter-inner">
    <div class="newsletter-label">THE BULLETIN</div>
    <h2 class="newsletter-title">One email. Every morning. <em>Zero noise.</em></h2>
    <p class="newsletter-dek">Daily macro bulletin and the Sunday Morning Series, delivered before the market opens. No sponsored picks. No affiliate crypto shills. Just the signal.</p>
    <form class="newsletter-form">
      <input class="newsletter-input" type="email" placeholder="your@email.com" required />
      <button class="newsletter-submit" type="submit">Subscribe</button>
    </form>
    <div class="newsletter-note">FREE &middot; UNSUBSCRIBE ANYTIME &middot; TR + EN EDITIONS</div>
    <div class="newsletter-stats">
      <div class="nl-stat"><div class="v">4,200+</div><div class="k">Subscribers</div></div>
      <div class="nl-stat"><div class="v">68%</div><div class="k">Open Rate</div></div>
      <div class="nl-stat"><div class="v">47</div><div class="k">Issues Sent</div></div>
    </div>
  </div>
</section>
'''

FOOTER = '''
<footer>
  <div class="footer-inner">
    <div class="footer-top">
      <div>
        <div class="footer-brand-title">No<em>/</em>Cashflow</div>
        <p class="footer-brand-desc">Macro, markets, and the signal in the noise. Written in Barcelona. Read worldwide. Every Sunday morning, with data.</p>
      </div>
      <div class="footer-col">
        <h4>Read</h4>
        <ul>
          <li><a href="yazilar.html">Sunday Series</a></li>
          <li><a href="bulletin.html">Daily Bulletin</a></li>
          <li><a href="macro.html">Macro</a></li>
          <li><a href="crypto.html">Crypto</a></li>
          <li><a href="dashboard.html">Dashboard</a></li>
          <li><a href="sozluk.html">Glossary</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h4>About</h4>
        <ul>
          <li><a href="hakkinda.html">Orkun Bi&ccedil;en</a></li>
          <li><a href="hakkinda.html#methodology">Methodology</a></li>
          <li><a href="hakkinda.html#sources">Sources</a></li>
          <li><a href="mailto:orkun@nocashflow.net">Contact</a></li>
          <li><a href="mailto:orkun@nocashflow.net">Advertise</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h4>Follow</h4>
        <ul>
          <li><a href="https://twitter.com/No_CashFlow">Twitter &middot; @No_CashFlow</a></li>
          <li><a href="https://www.linkedin.com/in/orkunbicen/">LinkedIn</a></li>
          <li><a href="#">RSS Feed</a></li>
          <li><a href="#">Telegram</a></li>
          <li><a href="#">Privacy</a></li>
          <li><a href="#">Terms</a></li>
        </ul>
      </div>
    </div>
    <div class="footer-bot">
      <span>&copy; 2026 NoCashFlow &middot; Barcelona</span>
      <span>Built with obsession &middot; <a href="#">Colophon</a></span>
    </div>
    <div class="disclaimer">
      This site does not provide investment advice. All content is for informational purposes. The author may hold positions in instruments mentioned. Always do your own research.
    </div>
  </div>
</footer>
<script src="assets/site.js"></script>
</body>
</html>
'''

def page(title, desc, body):
  return HEAD.format(title=title, desc=desc) + TICKER + NAV + body + NEWSLETTER + FOOTER

# ============================================================
# INDEX
# ============================================================
INDEX_BODY = '''
<section class="container" style="padding:56px var(--pad) 40px;">
  <div class="page-eyebrow">
    <span>ISSUE &#8470;47</span>
    <span class="divider"></span>
    <span>Sunday, April 14, 2026</span>
    <span class="divider"></span>
    <span class="muted">Week 16 &middot; Barcelona</span>
  </div>
  <div style="display:grid;grid-template-columns:1fr 380px;gap:56px;align-items:start;">
    <div>
      <div class="page-eyebrow"><span class="tag filled">LEAD STORY</span><span>Smart Money &middot; Sunday Series #4</span><span class="muted">7 MIN READ</span></div>
      <h1 style="font-family:var(--serif);font-weight:350;font-size:clamp(42px,6vw,88px);line-height:0.96;letter-spacing:-0.025em;margin-bottom:28px;">Smart money didn&#8217;t <em style="font-style:italic;color:var(--amber);">lead</em>.<br/>It <em style="font-style:italic;color:var(--amber);">retreated</em>.</h1>
      <p style="font-family:var(--serif);font-weight:300;font-size:22px;line-height:1.4;color:var(--text-dim);max-width:720px;margin-bottom:36px;font-style:italic;">JPMorgan called Q1 2026 the year institutions would dominate crypto flows. The data tells a different story: Iran war, VIX at 26, Fear &amp; Greed at 12. The Coinbase Premium Index shows exactly where the real money went &mdash; and it wasn&#8217;t in.</p>
      <div style="display:flex;align-items:center;gap:16px;padding:18px 0;border-top:1px solid var(--border);border-bottom:1px solid var(--border);margin-bottom:28px;">
        <div style="width:44px;height:44px;border-radius:50%;background:linear-gradient(135deg,var(--amber) 0%,#b87f1f 100%);display:grid;place-items:center;color:#0b0b0d;font-weight:700;font-family:var(--mono);font-size:14px;">OB</div>
        <div style="flex:1;">
          <div style="font-size:13px;color:var(--text);font-weight:500;">Orkun Bi&ccedil;en</div>
          <div style="font-family:var(--mono);font-size:10px;letter-spacing:0.1em;color:var(--text-mute);text-transform:uppercase;margin-top:2px;">Zone EUR MCS Controller &middot; Nestl&eacute; Barcelona</div>
        </div>
        <div style="font-family:var(--mono);font-size:10px;letter-spacing:0.14em;text-transform:uppercase;color:var(--text-mute);">APR 14 &middot; 2,847 reads</div>
      </div>
      <a href="yazilar.html#smart-money" class="btn">Read the full analysis <span class="arrow">&rarr;</span></a>
    </div>
    <aside class="card" style="position:sticky;top:80px;">
      <div style="aspect-ratio:4/5;background:radial-gradient(ellipse at 30% 20%,rgba(245,165,36,0.18) 0%,transparent 55%),radial-gradient(ellipse at 80% 80%,rgba(239,68,68,0.10) 0%,transparent 55%),linear-gradient(180deg,#1a1a1f 0%,#0d0d10 100%);border-bottom:1px solid var(--border);overflow:hidden;">
        <svg viewBox="0 0 400 500" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%;">
          <defs><linearGradient id="fr" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#ef4444" stop-opacity="0"/><stop offset="1" stop-color="#ef4444" stop-opacity="0.28"/></linearGradient></defs>
          <g stroke="#26262b" stroke-width="0.5" opacity="0.7"><line x1="0" y1="100" x2="400" y2="100"/><line x1="0" y1="200" x2="400" y2="200"/><line x1="0" y1="300" x2="400" y2="300"/><line x1="0" y1="400" x2="400" y2="400"/></g>
          <path d="M0,150 L30,130 L60,160 L90,140 L120,200 L150,180 L180,240 L210,220 L240,280 L270,260 L300,320 L330,300 L360,360 L400,340 L400,500 L0,500 Z" fill="url(#fr)"/>
          <g>
            <rect x="16" y="120" width="10" height="20" fill="#22c55e"/><line x1="21" y1="105" x2="21" y2="150" stroke="#22c55e"/>
            <rect x="46" y="135" width="10" height="18" fill="#22c55e"/><line x1="51" y1="120" x2="51" y2="160" stroke="#22c55e"/>
            <rect x="76" y="145" width="10" height="16" fill="#ef4444"/><line x1="81" y1="130" x2="81" y2="170" stroke="#ef4444"/>
            <rect x="106" y="158" width="10" height="30" fill="#ef4444"/><line x1="111" y1="145" x2="111" y2="200" stroke="#ef4444"/>
            <rect x="136" y="175" width="10" height="22" fill="#ef4444"/><line x1="141" y1="160" x2="141" y2="210" stroke="#ef4444"/>
            <rect x="166" y="190" width="10" height="18" fill="#22c55e"/><line x1="171" y1="178" x2="171" y2="220" stroke="#22c55e"/>
            <rect x="196" y="210" width="10" height="30" fill="#ef4444"/><line x1="201" y1="195" x2="201" y2="250" stroke="#ef4444"/>
            <rect x="226" y="235" width="10" height="22" fill="#ef4444"/><line x1="231" y1="220" x2="231" y2="270" stroke="#ef4444"/>
            <rect x="256" y="255" width="10" height="32" fill="#ef4444"/><line x1="261" y1="240" x2="261" y2="295" stroke="#ef4444"/>
            <rect x="286" y="280" width="10" height="24" fill="#ef4444"/><line x1="291" y1="265" x2="291" y2="315" stroke="#ef4444"/>
            <rect x="316" y="300" width="10" height="38" fill="#ef4444"/><line x1="321" y1="285" x2="321" y2="350" stroke="#ef4444"/>
            <rect x="346" y="325" width="10" height="26" fill="#ef4444"/><line x1="351" y1="310" x2="351" y2="365" stroke="#ef4444"/>
            <rect x="376" y="345" width="10" height="28" fill="#f5a524"/><line x1="381" y1="330" x2="381" y2="385" stroke="#f5a524"/>
          </g>
          <circle cx="381" cy="359" r="4" fill="#f5a524"/><circle cx="381" cy="359" r="8" fill="#f5a524" opacity="0.3"/>
        </svg>
      </div>
      <div style="padding:14px 18px;display:flex;justify-content:space-between;font-family:var(--mono);font-size:10px;letter-spacing:0.16em;text-transform:uppercase;"><span style="color:var(--text-mute);">COINBASE PREMIUM &middot; 8H</span><span style="color:var(--amber);">&darr; BEARISH</span></div>
      <div style="padding:18px;display:grid;grid-template-columns:1fr 1fr;gap:16px 20px;border-top:1px solid var(--border);">
        <div><div style="font-family:var(--mono);font-size:9px;letter-spacing:0.2em;text-transform:uppercase;color:var(--text-mute);margin-bottom:4px;">Premium</div><div style="font-family:var(--mono);font-size:18px;font-weight:500;color:var(--red);">&minus;0.18</div></div>
        <div><div style="font-family:var(--mono);font-size:9px;letter-spacing:0.2em;text-transform:uppercase;color:var(--text-mute);margin-bottom:4px;">30D &Delta;</div><div style="font-family:var(--mono);font-size:18px;font-weight:500;color:var(--red);">&minus;142%</div></div>
        <div><div style="font-family:var(--mono);font-size:9px;letter-spacing:0.2em;text-transform:uppercase;color:var(--text-mute);margin-bottom:4px;">JPM Est.</div><div style="font-family:var(--mono);font-size:18px;font-weight:500;">$33B</div></div>
        <div><div style="font-family:var(--mono);font-size:9px;letter-spacing:0.2em;text-transform:uppercase;color:var(--text-mute);margin-bottom:4px;">Q1 Actual</div><div style="font-family:var(--mono);font-size:18px;font-weight:500;color:var(--red);">$11B</div></div>
      </div>
    </aside>
  </div>
</section>

<section class="section">
  <div class="section-header">
    <h2 class="section-title"><span class="num">&sect; 01</span> Market Pulse</h2>
    <div class="section-meta"><span class="live">&#9679; LIVE</span> &middot; UPDATED 14:32 CET</div>
  </div>
  <div class="stat-grid" style="grid-template-columns:repeat(5,1fr);">
    <div class="stat">
      <div class="stat-k">Crypto Fear &amp; Greed</div>
      <div><div class="stat-v" style="color:var(--red);">18</div><div class="stat-chg dn">EXTREME FEAR</div></div>
      <svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line dn" points="0,6 20,10 40,14 60,18 80,22 100,25"/></svg>
    </div>
    <div class="stat">
      <div class="stat-k">Fed Funds Rate</div>
      <div><div class="stat-v">3.75<small>%</small></div><div class="stat-chg">HOLD &middot; 1 CUT 2026</div></div>
      <svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line amber" points="0,20 20,22 40,25 60,10 80,10 100,10"/></svg>
    </div>
    <div class="stat">
      <div class="stat-k">CPI YoY</div>
      <div><div class="stat-v">2.4<small>%</small></div><div class="stat-chg dn">PRE-WAR &middot; MAR HOTTER</div></div>
      <svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line dn" points="0,5 20,10 40,8 60,12 80,15 100,10"/></svg>
    </div>
    <div class="stat">
      <div class="stat-k">PPI YoY</div>
      <div><div class="stat-v">3.4<small>%</small></div><div class="stat-chg dn">&uarr; 2&times; EXPECTATIONS</div></div>
      <svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line dn" points="0,22 20,20 40,18 60,12 80,8 100,4"/></svg>
    </div>
    <div class="stat">
      <div class="stat-k">VIX</div>
      <div><div class="stat-v">26.8</div><div class="stat-chg dn">ELEVATED FEAR</div></div>
      <svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line dn" points="0,25 15,22 30,18 45,12 60,14 75,6 100,8"/></svg>
    </div>
  </div>
</section>

<section class="section">
  <div class="section-header">
    <h2 class="section-title"><span class="num">&sect; 02</span> Daily Bulletin</h2>
    <div class="section-meta"><a href="bulletin.html">FULL BULLETIN &rarr;</a></div>
  </div>
  <div style="border-top:1px solid var(--border);">''' + ''.join([
f'''
    <article style="display:grid;grid-template-columns:90px 1fr auto;gap:28px;padding:22px 0;border-bottom:1px solid var(--border);align-items:baseline;cursor:pointer;" onmouseover="this.style.paddingLeft='14px'" onmouseout="this.style.paddingLeft='0'">
      <div style="font-family:var(--mono);font-size:11px;letter-spacing:0.12em;color:var(--text-mute);"><span style="color:var(--amber);display:block;font-size:14px;font-weight:600;">{t}</span>CET</div>
      <div>
        <span class="tag {cls}" style="margin-bottom:8px;display:inline-block;">{tag}</span>
        <h3 style="font-family:var(--serif);font-weight:400;font-size:20px;line-height:1.3;margin-bottom:6px;">{title}</h3>
        <p style="font-size:14px;color:var(--text-dim);line-height:1.55;max-width:620px;">{excerpt}</p>
      </div>
      <div style="font-family:var(--mono);font-size:10px;letter-spacing:0.16em;color:var(--text-mute);text-transform:uppercase;">{mins} MIN</div>
    </article>'''
for t, cls, tag, title, excerpt, mins in [
  ('09:12','hot','BREAKING','JPMorgan revises 2026 crypto flow estimate: Q1 came in at $11B &mdash; one-third of forecast','Institutional flows turned net-negative for the first time since Q3 2023. Dimon memo circulated to private clients this morning. Bitcoin ETF outflows 8 consecutive days.','3'),
  ('08:45','alert','FED','Powell presser: &ldquo;we just don&#8217;t know&rdquo; said 17 times','Dot plot shows 1 cut in 2026, down from 3. Fed holds at 3.50&ndash;3.75%. 2Y Treasury +12bp intraday.','4'),
  ('07:30','','MACRO','Feb PPI prints 0.7% &mdash; exactly double consensus (0.35%)','Wholesale prices pre-war. March reading (April 11) will be the first full oil-shock data.','3'),
  ('06:58','hot','ENERGY','Brent above $106 &mdash; up 41% since Hormuz closure','IEA announces largest-ever coordinated SPR release: 180M barrels over 60 days.','5'),
  ('06:15','','CRYPTO','Circle (CRCL) tops $42B market cap as MiCA compliance deadline passes','USDC now the only top-5 stablecoin with full EU MiCA compliance. Tether delisted from Binance EU.','4'),
]
]) + '''
  </div>
</section>

<section class="section">
  <div class="section-header">
    <h2 class="section-title"><span class="num">&sect; 03</span> Sunday Morning Series</h2>
    <div class="section-meta"><a href="yazilar.html">ALL ISSUES &rarr;</a></div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid var(--border);border-bottom:1px solid var(--border);">''' + ''.join([
f'''
    <a href="yazilar.html#{slug}" style="padding:28px 24px;border-right:1px solid var(--border);display:flex;flex-direction:column;min-height:340px;position:relative;">
      <div style="font-family:var(--serif);font-size:68px;font-weight:300;line-height:1;color:var(--border);margin-bottom:18px;letter-spacing:-0.04em;">{num}</div>
      <div style="font-family:var(--mono);font-size:10px;letter-spacing:0.22em;text-transform:uppercase;color:var(--amber);margin-bottom:12px;">{cat}</div>
      <h3 style="font-family:var(--serif);font-weight:400;font-size:22px;line-height:1.25;margin-bottom:14px;flex:1;">{title}</h3>
      <p style="font-size:13px;color:var(--text-dim);line-height:1.55;margin-bottom:18px;">{excerpt}</p>
      <div style="font-family:var(--mono);font-size:10px;letter-spacing:0.12em;color:var(--text-mute);text-transform:uppercase;padding-top:14px;border-top:1px solid var(--border-soft);display:flex;justify-content:space-between;"><span>{date}</span><span>{mins} MIN</span></div>
    </a>'''
for num, cat, title, excerpt, date, mins, slug in [
  ('04','Crypto &middot; Smart Money','Smart Money didn&#8217;t lead. It retreated.','JPM January expectation vs Q1 reality. The Coinbase Premium Index tells the real story about institutional crypto flows.','APR 14 &middot; 2026','7','smart-money'),
  ('03','Energy &middot; Infrastructure','AI needs electricity. The answer is nuclear.','IEA: data centers will consume 945 TWh by 2030 &mdash; all of Japan&#8217;s annual electricity. Microsoft $16B, Amazon $20B+, Google 500MW.','APR 06 &middot; 2026','9','nukleer'),
  ('02','Commodities &middot; Macro','Dr. Copper &mdash; wrong diagnosis?','Historically the economy&#8217;s thermometer. But AI data centers, EVs, and renewables all demand it simultaneously. S&amp;P projects 10M tonne deficit by 2040.','MAR 30 &middot; 2026','8','bakir'),
  ('01','Macro &middot; Inflation','Why the 1970s comparison is misleading.','Brent up 40%, Hormuz closed, 1970s analogies everywhere. But in 1973 it took 1 barrel per $1,000 GDP. Today: 0.43.','MAR 23 &middot; 2026','10','petrol'),
]
]) + '''
  </div>
</section>
'''

# ============================================================
# BULLETIN
# ============================================================
BULLETIN_BODY = '''
<header class="page-head">
  <div class="page-eyebrow"><span class="tag filled">DAILY</span><span>Market intelligence, before the open</span><span class="divider"></span><span class="muted">Updated 14:32 CET</span></div>
  <h1 class="page-title">The <em>Daily</em> Bulletin.</h1>
  <p class="page-dek">Everything you need to know before markets open, curated from Bloomberg, Reuters, FT, and primary sources. Six stories, four minutes. No filler.</p>
</header>

<section class="section" style="padding-top:48px;">
  <div class="section-header">
    <h2 class="section-title"><span class="num">TODAY</span> April 14, 2026</h2>
    <div class="section-meta"><span class="live">&#9679; LIVE</span> &middot; Issue &#8470;147</div>
  </div>
  <div style="display:grid;grid-template-columns:1fr 320px;gap:48px;">
    <div style="border-top:1px solid var(--border);">''' + ''.join([
f'''
      <article style="display:grid;grid-template-columns:90px 1fr auto;gap:28px;padding:24px 0;border-bottom:1px solid var(--border);align-items:baseline;">
        <div style="font-family:var(--mono);font-size:11px;letter-spacing:0.12em;color:var(--text-mute);"><span style="color:var(--amber);display:block;font-size:14px;font-weight:600;">{t}</span>CET</div>
        <div>
          <span class="tag {cls}" style="margin-bottom:10px;display:inline-block;">{tag}</span>
          <h3 style="font-family:var(--serif);font-weight:400;font-size:22px;line-height:1.3;margin-bottom:10px;">{title}</h3>
          <p style="font-size:14.5px;color:var(--text-dim);line-height:1.6;max-width:640px;margin-bottom:12px;">{excerpt}</p>
          <div style="font-family:var(--mono);font-size:10px;letter-spacing:0.14em;color:var(--text-mute);text-transform:uppercase;">SRC: {src}</div>
        </div>
        <div style="font-family:var(--mono);font-size:10px;letter-spacing:0.16em;color:var(--text-mute);text-transform:uppercase;">{mins} MIN</div>
      </article>'''
for t, cls, tag, title, excerpt, src, mins in [
  ('09:12','hot','BREAKING','JPMorgan revises 2026 crypto flow estimate: Q1 came in at $11B &mdash; one-third of forecast','Institutional flows turned net-negative for the first time since Q3 2023. Dimon memo circulated to private clients this morning cites &ldquo;geopolitical risk recalibration.&rdquo; Bitcoin ETF outflows 8 consecutive days. Coinbase Premium Index signals US institutions are not buying the dip.','Bloomberg, JPM internal memo','3'),
  ('08:45','alert','FED','Powell presser: &ldquo;we just don&#8217;t know&rdquo; said 17 times &mdash; transcript count','Dot plot shows 1 cut in 2026, down from 3. Fed holds at 3.50&ndash;3.75%. Markets priced in dovish surprise; none delivered. 2Y Treasury +12bp intraday. Powell explicitly refused to commit to a cutting cadence until data clears.','Reuters, FT','4'),
  ('07:30','','MACRO','Feb PPI prints 0.7% &mdash; exactly double consensus (0.35%)','Wholesale prices pre-war. March reading (April 11) will be the first full oil-shock data. Morgan Stanley sees PPI 0.9&ndash;1.1%, CPI above 3% by June. Services inflation sticky at 4.2%.','BLS, Morgan Stanley Research','3'),
  ('06:58','hot','ENERGY','Brent above $106 &mdash; up 41% since Hormuz closure','IEA announces largest-ever coordinated SPR release: 180M barrels over 60 days. US, UK, Japan, Korea participating. Reuters: Saudi Arabia in &ldquo;quiet coordination&rdquo; despite public silence. Brent-WTI spread at widest since 2011.','IEA press release, Reuters','5'),
  ('06:15','','CRYPTO','Circle (CRCL) tops $42B market cap as MiCA compliance deadline passes','USDC now the only top-5 stablecoin with full EU MiCA compliance. Tether (USDT) delisted from Binance EU at 00:01 UTC. CRCL +8.2% pre-market. Circle announces Euro Coin expansion to 14 new EU markets.','FT, CoinGecko','4'),
  ('05:50','','RATES','ECB Lagarde: &ldquo;patience is our friend, but so is data&rdquo;','No hint at June cut timing. Two hawkish dissents (Germany, Netherlands). EUR/USD 1.0684, lowest since January. European PMI Tuesday first war-era reading.','ECB statement','3'),
  ('Yesterday','','COMMODITIES','Copper hits $4.28/lb &mdash; 18-month high','Chile strike enters week 3. Codelco supply 400K tonnes at risk. LME inventories at 2019 lows. Goldman target $5.00 by Q3.','LME, Goldman Sachs','4'),
  ('Yesterday','','MACRO','US jobless claims 218K &mdash; below estimate','Labor market still tight despite rate hold. Continuing claims 1.84M. Tech layoffs not yet reflected in data.','DoL, Bloomberg','2'),
]
]) + '''
    </div>
    <aside style="display:flex;flex-direction:column;gap:24px;">
      <div class="card">
        <div class="card-title"><span>This Week &middot; W16</span><span style="color:var(--text-mute);">CAL</span></div>
        <div style="padding:14px 16px;border-bottom:1px solid var(--border-soft);display:grid;grid-template-columns:42px 1fr;gap:14px;align-items:center;">
          <div style="text-align:center;"><div style="font-family:var(--serif);font-size:22px;">07</div><div style="font-family:var(--mono);font-size:9px;letter-spacing:0.2em;color:var(--amber);text-transform:uppercase;">Tue</div></div>
          <div style="font-size:13px;"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--red);margin-right:6px;"></span>Flash PMI &middot; March<div style="font-family:var(--mono);font-size:10px;color:var(--text-mute);margin-top:3px;">FIRST WAR-ERA READING</div></div>
        </div>
        <div style="padding:14px 16px;border-bottom:1px solid var(--border-soft);display:grid;grid-template-columns:42px 1fr;gap:14px;align-items:center;">
          <div style="text-align:center;"><div style="font-family:var(--serif);font-size:22px;">09</div><div style="font-family:var(--mono);font-size:9px;letter-spacing:0.2em;color:var(--amber);text-transform:uppercase;">Thu</div></div>
          <div style="font-size:13px;"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--amber);margin-right:6px;"></span>ECB Lagarde + Jobless Claims<div style="font-family:var(--mono);font-size:10px;color:var(--text-mute);margin-top:3px;">RATE PATH SIGNAL</div></div>
        </div>
        <div style="padding:14px 16px;border-bottom:1px solid var(--border-soft);display:grid;grid-template-columns:42px 1fr;gap:14px;align-items:center;">
          <div style="text-align:center;"><div style="font-family:var(--serif);font-size:22px;">11</div><div style="font-family:var(--mono);font-size:9px;letter-spacing:0.2em;color:var(--amber);text-transform:uppercase;">Fri</div></div>
          <div style="font-size:13px;"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--amber);margin-right:6px;"></span>Eurozone HICP<div style="font-family:var(--mono);font-size:10px;color:var(--text-mute);margin-top:3px;">WAR-IMPACT INFLATION</div></div>
        </div>
        <div style="padding:14px 16px;display:grid;grid-template-columns:42px 1fr;gap:14px;align-items:center;">
          <div style="text-align:center;"><div style="font-family:var(--serif);font-size:22px;">14</div><div style="font-family:var(--mono);font-size:9px;letter-spacing:0.2em;color:var(--amber);text-transform:uppercase;">Mon</div></div>
          <div style="font-size:13px;"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--red);margin-right:6px;"></span>US CPI + PPI &middot; March &#9733;<div style="font-family:var(--mono);font-size:10px;color:var(--text-mute);margin-top:3px;">MAIN EVENT</div></div>
        </div>
      </div>
      <div class="card">
        <div class="card-title"><span>Full PDF Bulletin</span><span style="color:var(--text-mute);">PDF</span></div>
        <div class="card-body">
          <p style="font-size:13px;color:var(--text-dim);line-height:1.55;margin-bottom:14px;">Today&#8217;s full bulletin as a printable PDF with all charts and annotations.</p>
          <a href="daily_bulletin.pdf" class="btn" style="padding:10px 18px;font-size:10px;">Download PDF &darr;</a>
        </div>
      </div>
      <div class="card">
        <div class="card-title"><span>Partner</span><span style="color:var(--text-mute);">AD</span></div>
        <div style="padding:32px 20px;text-align:center;font-family:var(--mono);font-size:10px;letter-spacing:0.2em;text-transform:uppercase;color:var(--text-mute);border-top:1px solid var(--border-soft);">
          <span style="color:var(--amber);display:block;margin-bottom:18px;">300 &times; 250</span>
          <div style="padding:40px 0;border-top:1px solid var(--border-soft);border-bottom:1px solid var(--border-soft);color:var(--text-dim);">Premium ad slot<br/>reserved for finance partners</div>
        </div>
      </div>
    </aside>
  </div>
</section>

<section class="section">
  <div class="section-header">
    <h2 class="section-title"><span class="num">ARCHIVE</span> Previous Issues</h2>
    <div class="section-meta">146 ISSUES &middot; SEARCHABLE</div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--border);border:1px solid var(--border);">''' + ''.join([
f'''
    <a href="#" style="padding:22px 20px;background:var(--bg-elev);display:flex;flex-direction:column;min-height:160px;">
      <div style="font-family:var(--mono);font-size:10px;letter-spacing:0.2em;color:var(--amber);text-transform:uppercase;margin-bottom:10px;">&#8470;{n} &middot; {date}</div>
      <h4 style="font-family:var(--serif);font-weight:400;font-size:17px;line-height:1.35;margin-bottom:10px;flex:1;">{title}</h4>
      <div style="font-family:var(--mono);font-size:10px;color:var(--text-mute);">{tag}</div>
    </a>'''
for n, date, title, tag in [
  ('146','APR 13','Sunday quiet: Fed minutes leaked early, euro falls','PRE-MARKET'),
  ('145','APR 12','Brent crosses $105, gold at ATH, BTC tests 60K','COMMODITIES'),
  ('144','APR 11','CPI week preview: what to watch across 4 datasets','MACRO PREVIEW'),
  ('143','APR 10','ECB leaves rates: hawks win, doves regroup for June','RATES'),
  ('142','APR 09','Jobless claims tick up, yield curve flattens','LABOR'),
  ('141','APR 08','Circle IPO filing details: MiCA as moat','CRYPTO'),
]
]) + '''
  </div>
</section>
'''

# ============================================================
# MACRO
# ============================================================
MACRO_BODY = '''
<header class="page-head">
  <div class="page-eyebrow"><span class="tag filled">MACRO</span><span>Rates &middot; Inflation &middot; Growth</span><span class="divider"></span><span class="muted">LIVE &middot; 14:32 CET</span></div>
  <h1 class="page-title">The <em>macro</em> dashboard.</h1>
  <p class="page-dek">Central bank rates, yield curves, inflation prints, and FX. What institutional macro desks actually watch, consolidated into one page.</p>
</header>

<section class="section" style="padding-top:48px;">
  <div class="section-header">
    <h2 class="section-title"><span class="num">&sect; 01</span> Central Bank Rates</h2>
    <div class="section-meta">NEXT MEETING DATES &middot; UPDATED DAILY</div>
  </div>
  <div class="stat-grid" style="grid-template-columns:repeat(4,1fr);">
    <div class="stat">
      <div class="stat-k">Federal Reserve</div>
      <div><div class="stat-v">3.75<small>%</small></div><div class="stat-chg">HOLD &middot; NEXT APR 30</div></div>
      <svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line amber" points="0,28 15,25 30,15 45,10 60,8 75,8 100,10"/></svg>
    </div>
    <div class="stat">
      <div class="stat-k">ECB</div>
      <div><div class="stat-v">3.50<small>%</small></div><div class="stat-chg">HOLD &middot; NEXT JUN 05</div></div>
      <svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line amber" points="0,28 20,25 40,14 60,6 80,8 100,12"/></svg>
    </div>
    <div class="stat">
      <div class="stat-k">Bank of England</div>
      <div><div class="stat-v">4.25<small>%</small></div><div class="stat-chg up">&darr; 25BP &middot; NEXT MAY 08</div></div>
      <svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line amber" points="0,26 20,22 40,10 60,8 80,10 100,12"/></svg>
    </div>
    <div class="stat">
      <div class="stat-k">Bank of Japan</div>
      <div><div class="stat-v">0.50<small>%</small></div><div class="stat-chg">HOLD &middot; NEXT APR 28</div></div>
      <svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line amber" points="0,28 20,28 40,26 60,22 80,20 100,18"/></svg>
    </div>
  </div>
</section>

<section class="section">
  <div class="section-header">
    <h2 class="section-title"><span class="num">&sect; 02</span> US Yield Curve</h2>
    <div class="section-meta">SRC: US TREASURY &middot; 14:00 CET</div>
  </div>
  <div style="display:grid;grid-template-columns:2fr 1fr;gap:32px;">
    <div class="card" style="padding:28px;">
      <svg viewBox="0 0 600 260" preserveAspectRatio="none" style="width:100%;height:280px;">
        <defs><linearGradient id="yf" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#f5a524" stop-opacity="0.2"/><stop offset="1" stop-color="#f5a524" stop-opacity="0"/></linearGradient></defs>
        <g stroke="#26262b" stroke-width="0.5"><line x1="40" y1="40" x2="600" y2="40"/><line x1="40" y1="100" x2="600" y2="100"/><line x1="40" y1="160" x2="600" y2="160"/><line x1="40" y1="220" x2="600" y2="220"/></g>
        <g fill="#6d6760" font-family="JetBrains Mono" font-size="10"><text x="5" y="44">5.0%</text><text x="5" y="104">4.5%</text><text x="5" y="164">4.0%</text><text x="5" y="224">3.5%</text></g>
        <g fill="#6d6760" font-family="JetBrains Mono" font-size="10" text-anchor="middle"><text x="80" y="250">1M</text><text x="160" y="250">3M</text><text x="240" y="250">6M</text><text x="320" y="250">2Y</text><text x="400" y="250">5Y</text><text x="480" y="250">10Y</text><text x="560" y="250">30Y</text></g>
        <path d="M80,110 L160,105 L240,108 L320,135 L400,130 L480,105 L560,80" stroke="#f5a524" stroke-width="2.5" fill="none"/>
        <path d="M80,110 L160,105 L240,108 L320,135 L400,130 L480,105 L560,80 L560,240 L80,240 Z" fill="url(#yf)"/>
        <g fill="#f5a524"><circle cx="80" cy="110" r="4"/><circle cx="160" cy="105" r="4"/><circle cx="240" cy="108" r="4"/><circle cx="320" cy="135" r="4"/><circle cx="400" cy="130" r="4"/><circle cx="480" cy="105" r="4"/><circle cx="560" cy="80" r="4"/></g>
        <line x1="320" y1="140" x2="320" y2="220" stroke="#ef4444" stroke-width="0.5" stroke-dasharray="3,3"/>
        <text x="325" y="218" font-family="JetBrains Mono" font-size="10" fill="#ef4444">INVERSION ZONE</text>
      </svg>
    </div>
    <div style="display:flex;flex-direction:column;gap:16px;">
      <div class="card" style="padding:20px;"><div style="font-family:var(--mono);font-size:10px;letter-spacing:0.18em;color:var(--text-mute);text-transform:uppercase;margin-bottom:6px;">2Y / 10Y Spread</div><div style="font-family:var(--mono);font-size:28px;color:var(--red);">&minus;25bp</div><div style="font-family:var(--mono);font-size:11px;color:var(--text-mute);margin-top:4px;">INVERTED &middot; 21 MONTHS</div></div>
      <div class="card" style="padding:20px;"><div style="font-family:var(--mono);font-size:10px;letter-spacing:0.18em;color:var(--text-mute);text-transform:uppercase;margin-bottom:6px;">3M / 10Y Spread</div><div style="font-family:var(--mono);font-size:28px;color:var(--red);">&minus;78bp</div><div style="font-family:var(--mono);font-size:11px;color:var(--text-mute);margin-top:4px;">NY FED RECESSION SIGNAL: 42%</div></div>
      <div class="card" style="padding:20px;"><div style="font-family:var(--mono);font-size:10px;letter-spacing:0.18em;color:var(--text-mute);text-transform:uppercase;margin-bottom:6px;">10Y Yield</div><div style="font-family:var(--mono);font-size:28px;">4.38<small style="color:var(--text-mute);font-size:18px;">%</small></div><div style="font-family:var(--mono);font-size:11px;color:var(--green);margin-top:4px;">+4BP TODAY</div></div>
    </div>
  </div>
</section>

<section class="section">
  <div class="section-header">
    <h2 class="section-title"><span class="num">&sect; 03</span> Inflation Tracker</h2>
    <div class="section-meta">MONTHLY PRINTS &middot; YoY</div>
  </div>
  <div class="stat-grid" style="grid-template-columns:repeat(4,1fr);">
    <div class="stat"><div class="stat-k">US CPI</div><div><div class="stat-v">2.4<small>%</small></div><div class="stat-chg dn">&darr; FROM 2.8% &middot; FEB</div></div><svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line dn" points="0,10 15,8 30,12 45,14 60,12 75,8 100,6"/></svg></div>
    <div class="stat"><div class="stat-k">US PPI</div><div><div class="stat-v">3.4<small>%</small></div><div class="stat-chg dn">&uarr; 2&times; EXPECTATIONS</div></div><svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line dn" points="0,22 20,20 40,18 60,12 80,8 100,4"/></svg></div>
    <div class="stat"><div class="stat-k">Eurozone HICP</div><div><div class="stat-v">2.6<small>%</small></div><div class="stat-chg">FLAT &middot; MAR PRINT FRI</div></div><svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line amber" points="0,18 20,14 40,12 60,14 80,12 100,12"/></svg></div>
    <div class="stat"><div class="stat-k">UK CPI</div><div><div class="stat-v">3.2<small>%</small></div><div class="stat-chg dn">&uarr; FROM 2.9%</div></div><svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line dn" points="0,18 20,14 40,14 60,10 80,6 100,4"/></svg></div>
  </div>
</section>

<section class="section">
  <div class="section-header">
    <h2 class="section-title"><span class="num">&sect; 04</span> FX &amp; Commodities</h2>
    <div class="section-meta">LIVE</div>
  </div>
  <div class="stat-grid" style="grid-template-columns:repeat(6,1fr);">
    <div class="stat"><div class="stat-k">DXY</div><div><div class="stat-v">104.28</div><div class="stat-chg up">+0.46%</div></div><svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line up" points="0,22 20,20 40,14 60,12 80,10 100,8"/></svg></div>
    <div class="stat"><div class="stat-k">EUR/USD</div><div><div class="stat-v">1.0684</div><div class="stat-chg dn">&minus;0.21%</div></div><svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line dn" points="0,10 20,12 40,16 60,20 80,22 100,24"/></svg></div>
    <div class="stat"><div class="stat-k">USD/JPY</div><div><div class="stat-v">154.82</div><div class="stat-chg up">+0.32%</div></div><svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line up" points="0,24 20,22 40,18 60,14 80,12 100,10"/></svg></div>
    <div class="stat"><div class="stat-k">Brent</div><div><div class="stat-v">$106</div><div class="stat-chg up">+3.12%</div></div><svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line up" points="0,26 20,22 40,16 60,12 80,8 100,4"/></svg></div>
    <div class="stat"><div class="stat-k">Gold</div><div><div class="stat-v">$2,614</div><div class="stat-chg up">+0.74%</div></div><svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line up" points="0,22 20,20 40,16 60,14 80,10 100,8"/></svg></div>
    <div class="stat"><div class="stat-k">Copper</div><div><div class="stat-v">$4.28</div><div class="stat-chg up">+0.38%</div></div><svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line up" points="0,20 20,18 40,16 60,12 80,10 100,6"/></svg></div>
  </div>
</section>
'''

# ============================================================
# CRYPTO
# ============================================================
CRYPTO_BODY = '''
<header class="page-head">
  <div class="page-eyebrow"><span class="tag filled">CRYPTO</span><span>BTC &middot; ETH &middot; Stablecoins &middot; Flows</span><span class="divider"></span><span class="muted">LIVE</span></div>
  <h1 class="page-title">Crypto, <em>through a macro lens.</em></h1>
  <p class="page-dek">Not price predictions. What&#8217;s actually happening with institutional flows, stablecoin supply, regulatory infrastructure, and the data that tells the truth.</p>
</header>

<section class="section" style="padding-top:48px;">
  <div class="section-header">
    <h2 class="section-title"><span class="num">&sect; 01</span> Top Assets</h2>
    <div class="section-meta"><span class="live">&#9679; LIVE</span> &middot; SRC: COINGECKO</div>
  </div>
  <div class="card" style="padding:0;">
    <div style="display:grid;grid-template-columns:40px 1fr 120px 120px 120px 140px 120px;gap:0;padding:14px 20px;border-bottom:1px solid var(--border);font-family:var(--mono);font-size:10px;letter-spacing:0.18em;text-transform:uppercase;color:var(--text-mute);">
      <div>#</div><div>Asset</div><div style="text-align:right;">Price</div><div style="text-align:right;">24H</div><div style="text-align:right;">7D</div><div style="text-align:right;">Mkt Cap</div><div style="text-align:right;">Vol 24H</div>
    </div>''' + ''.join([
f'''
    <div style="display:grid;grid-template-columns:40px 1fr 120px 120px 120px 140px 120px;gap:0;padding:16px 20px;border-bottom:1px solid var(--border-soft);font-family:var(--mono);font-size:13px;align-items:center;" onmouseover="this.style.background='var(--bg-elev-2)'" onmouseout="this.style.background='transparent'">
      <div style="color:var(--text-mute);">{n}</div>
      <div><span style="color:var(--amber);font-weight:600;">{sym}</span> <span style="color:var(--text-dim);font-family:var(--sans);font-size:13px;margin-left:8px;">{name}</span></div>
      <div style="text-align:right;">{price}</div>
      <div style="text-align:right;color:var(--{c24});">{d24}</div>
      <div style="text-align:right;color:var(--{c7d});">{d7d}</div>
      <div style="text-align:right;color:var(--text-dim);">{cap}</div>
      <div style="text-align:right;color:var(--text-dim);">{vol}</div>
    </div>'''
for n, sym, name, price, c24, d24, c7d, d7d, cap, vol in [
  ('1','BTC','Bitcoin','$67,420','red','-1.82%','red','-4.20%','$1.33T','$38B'),
  ('2','ETH','Ethereum','$3,284','red','-2.41%','red','-6.10%','$394B','$18B'),
  ('3','USDT','Tether','$1.000','text-mute','0.00%','text-mute','0.01%','$118B','$64B'),
  ('4','USDC','USD Coin','$1.000','text-mute','0.00%','green','+0.02%','$42B','$9B'),
  ('5','SOL','Solana','$142','red','-3.10%','red','-8.40%','$66B','$3.2B'),
  ('6','XRP','XRP','$0.58','red','-0.80%','green','+1.20%','$31B','$1.8B'),
  ('7','BNB','BNB','$586','red','-1.40%','red','-3.80%','$87B','$1.5B'),
  ('8','HYPE','Hyperliquid','$28.40','green','+2.10%','green','+8.30%','$9.6B','$420M'),
  ('9','LINK','Chainlink','$14.80','red','-1.20%','red','-2.80%','$9.2B','$380M'),
  ('10','CRCL','Circle','$42.80','green','+8.20%','green','+14.60%','$42B','$1.1B'),
]
]) + '''
  </div>
</section>

<section class="section">
  <div class="section-header">
    <h2 class="section-title"><span class="num">&sect; 02</span> Coinbase Premium Index</h2>
    <div class="section-meta">US INSTITUTIONAL DEMAND PROXY &middot; 90D</div>
  </div>
  <div class="card" style="padding:28px;">
    <div style="font-family:var(--mono);font-size:10px;letter-spacing:0.22em;text-transform:uppercase;color:var(--amber);margin-bottom:14px;">CRYPTO &times; MACRO &middot; 90D</div>
    <h3 style="font-family:var(--serif);font-weight:300;font-size:32px;line-height:1.1;letter-spacing:-0.02em;margin-bottom:10px;">When BTC rallies but Premium stays negative, US institutions are absent.</h3>
    <p style="font-size:14px;color:var(--text-dim);margin-bottom:24px;">That&#8217;s what we&#8217;re watching right now. Divergence extended to 28 days &mdash; longest streak since late 2022.</p>
    <svg viewBox="0 0 800 280" preserveAspectRatio="none" style="width:100%;height:300px;">
      <defs><linearGradient id="btcFade2" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#f5a524" stop-opacity="0.22"/><stop offset="1" stop-color="#f5a524" stop-opacity="0"/></linearGradient></defs>
      <g stroke="#26262b" stroke-width="0.5" opacity="0.5"><line x1="0" y1="70" x2="800" y2="70"/><line x1="0" y1="140" x2="800" y2="140"/><line x1="0" y1="210" x2="800" y2="210"/></g>
      <g fill="#6d6760" font-family="JetBrains Mono" font-size="10"><text x="8" y="20">$72K</text><text x="8" y="90">$68K</text><text x="8" y="160">$64K</text><text x="8" y="230">$60K</text></g>
      <path d="M 60,180 Q 140,70 220,110 T 380,60 T 520,80 T 680,140 L 760,170" stroke="#f5a524" stroke-width="2" fill="none"/>
      <path d="M 60,180 Q 140,70 220,110 T 380,60 T 520,80 T 680,140 L 760,170 L 760,280 L 60,280 Z" fill="url(#btcFade2)"/>
      <g>
        <rect x="70" y="220" width="10" height="14" fill="#22c55e"/><rect x="90" y="225" width="10" height="10" fill="#22c55e"/><rect x="110" y="230" width="10" height="6" fill="#22c55e"/><rect x="130" y="232" width="10" height="8" fill="#22c55e"/>
        <rect x="150" y="240" width="10" height="6" fill="#ef4444"/><rect x="170" y="240" width="10" height="10" fill="#ef4444"/><rect x="190" y="240" width="10" height="14" fill="#ef4444"/><rect x="210" y="240" width="10" height="18" fill="#ef4444"/>
        <rect x="230" y="240" width="10" height="22" fill="#ef4444"/><rect x="250" y="240" width="10" height="20" fill="#ef4444"/><rect x="270" y="240" width="10" height="24" fill="#ef4444"/><rect x="290" y="240" width="10" height="16" fill="#ef4444"/>
        <rect x="310" y="240" width="10" height="22" fill="#ef4444"/><rect x="330" y="240" width="10" height="28" fill="#ef4444"/><rect x="350" y="240" width="10" height="20" fill="#ef4444"/><rect x="370" y="240" width="10" height="14" fill="#ef4444"/>
        <rect x="390" y="240" width="10" height="8" fill="#ef4444"/><rect x="410" y="238" width="10" height="4" fill="#ef4444"/><rect x="430" y="236" width="10" height="4" fill="#22c55e"/><rect x="450" y="240" width="10" height="8" fill="#ef4444"/>
        <rect x="470" y="240" width="10" height="14" fill="#ef4444"/><rect x="490" y="240" width="10" height="18" fill="#ef4444"/><rect x="510" y="240" width="10" height="16" fill="#ef4444"/><rect x="530" y="240" width="10" height="20" fill="#ef4444"/>
        <rect x="550" y="240" width="10" height="26" fill="#ef4444"/><rect x="570" y="240" width="10" height="22" fill="#ef4444"/><rect x="590" y="240" width="10" height="28" fill="#ef4444"/><rect x="610" y="240" width="10" height="32" fill="#ef4444"/>
        <rect x="630" y="240" width="10" height="34" fill="#ef4444"/><rect x="650" y="240" width="10" height="30" fill="#ef4444"/><rect x="670" y="240" width="10" height="36" fill="#ef4444"/><rect x="690" y="240" width="10" height="30" fill="#ef4444"/>
        <rect x="710" y="240" width="10" height="26" fill="#ef4444"/><rect x="730" y="240" width="10" height="30" fill="#ef4444"/>
      </g>
      <line x1="580" y1="80" x2="580" y2="240" stroke="#ebe7e1" stroke-width="0.5" stroke-dasharray="3,3" opacity="0.5"/>
      <text x="585" y="95" fill="#ebe7e1" font-family="JetBrains Mono" font-size="10" opacity="0.8">HORMUZ CLOSED</text>
      <text x="585" y="108" fill="#6d6760" font-family="JetBrains Mono" font-size="9">MAR 21</text>
    </svg>
    <div style="display:flex;gap:28px;padding-top:18px;border-top:1px solid var(--border);font-family:var(--mono);font-size:11px;margin-top:20px;">
      <div style="display:flex;align-items:center;gap:8px;color:var(--text-dim);"><span style="width:10px;height:2px;background:#f5a524;"></span>BTC/USD</div>
      <div style="display:flex;align-items:center;gap:8px;color:var(--text-dim);"><span style="width:10px;height:2px;background:#22c55e;"></span>Premium (+)</div>
      <div style="display:flex;align-items:center;gap:8px;color:var(--text-dim);"><span style="width:10px;height:2px;background:#ef4444;"></span>Premium (&minus;)</div>
    </div>
  </div>
</section>

<section class="section">
  <div class="section-header">
    <h2 class="section-title"><span class="num">&sect; 03</span> Stablecoin Market</h2>
    <div class="section-meta">TOTAL SUPPLY &middot; MiCA FOCUS</div>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:32px;">
    <div class="card" style="padding:28px;">
      <div style="font-family:var(--mono);font-size:10px;letter-spacing:0.22em;text-transform:uppercase;color:var(--amber);margin-bottom:8px;">TOTAL SUPPLY</div>
      <div style="font-family:var(--serif);font-weight:300;font-size:52px;letter-spacing:-0.02em;line-height:1;margin-bottom:8px;">$167<span style="color:var(--text-mute);font-size:32px;">B</span></div>
      <div style="font-family:var(--mono);font-size:11px;color:var(--green);margin-bottom:24px;">+14.2% YTD &middot; ALL-TIME HIGH</div>
      <div style="display:grid;grid-template-columns:1fr;gap:14px;">
        <div style="display:grid;grid-template-columns:80px 1fr 90px;gap:12px;align-items:center;"><span style="font-family:var(--mono);font-size:13px;color:var(--amber);font-weight:600;">USDT</span><div style="background:var(--border);height:8px;position:relative;"><div style="position:absolute;inset:0;width:70%;background:var(--amber);"></div></div><span style="font-family:var(--mono);font-size:12px;text-align:right;">$118B</span></div>
        <div style="display:grid;grid-template-columns:80px 1fr 90px;gap:12px;align-items:center;"><span style="font-family:var(--mono);font-size:13px;color:var(--green);font-weight:600;">USDC</span><div style="background:var(--border);height:8px;position:relative;"><div style="position:absolute;inset:0;width:25%;background:var(--green);"></div></div><span style="font-family:var(--mono);font-size:12px;text-align:right;">$42B</span></div>
        <div style="display:grid;grid-template-columns:80px 1fr 90px;gap:12px;align-items:center;"><span style="font-family:var(--mono);font-size:13px;color:var(--text-dim);">DAI</span><div style="background:var(--border);height:8px;position:relative;"><div style="position:absolute;inset:0;width:3%;background:var(--text-dim);"></div></div><span style="font-family:var(--mono);font-size:12px;text-align:right;">$5.2B</span></div>
        <div style="display:grid;grid-template-columns:80px 1fr 90px;gap:12px;align-items:center;"><span style="font-family:var(--mono);font-size:13px;color:var(--text-dim);">FDUSD</span><div style="background:var(--border);height:8px;position:relative;"><div style="position:absolute;inset:0;width:1.5%;background:var(--text-dim);"></div></div><span style="font-family:var(--mono);font-size:12px;text-align:right;">$1.8B</span></div>
      </div>
    </div>
    <div class="card" style="padding:28px;">
      <div style="font-family:var(--mono);font-size:10px;letter-spacing:0.22em;text-transform:uppercase;color:var(--amber);margin-bottom:8px;">MiCA COMPLIANCE (EU)</div>
      <div style="font-family:var(--serif);font-weight:300;font-size:32px;line-height:1.15;margin-bottom:18px;">USDC is the only top-5 stablecoin <em style="color:var(--amber);">fully compliant.</em></div>
      <p style="font-size:14px;color:var(--text-dim);line-height:1.55;margin-bottom:20px;">As of April 1, 2026, MiCA (Markets in Crypto-Assets) requires all stablecoins offered to EU residents to have a licensed issuer and reserve audits. Tether missed the deadline; Binance EU delisted USDT pairs at 00:01 UTC April 1.</p>
      <div style="padding:18px;background:var(--bg);border:1px solid var(--amber);">
        <div style="font-family:var(--mono);font-size:10px;letter-spacing:0.2em;text-transform:uppercase;color:var(--amber);margin-bottom:8px;">THE IMPLICATION</div>
        <p style="font-size:14px;line-height:1.5;">Circle (CRCL) inherits an EU-shaped moat. Expect USDC market share in Europe to 3&times; in 12 months.</p>
      </div>
    </div>
  </div>
</section>

<section class="section">
  <div class="section-header">
    <h2 class="section-title"><span class="num">&sect; 04</span> ETF Flows</h2>
    <div class="section-meta">SPOT BTC + ETH ETFs &middot; 30D</div>
  </div>
  <div class="stat-grid" style="grid-template-columns:repeat(4,1fr);">
    <div class="stat"><div class="stat-k">Spot BTC ETFs &middot; 30D Net</div><div><div class="stat-v" style="color:var(--red);">&minus;$1.8B</div><div class="stat-chg dn">8 CONSECUTIVE OUTFLOW DAYS</div></div><svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line dn" points="0,15 15,10 30,18 45,22 60,24 75,26 100,28"/></svg></div>
    <div class="stat"><div class="stat-k">IBIT (BlackRock)</div><div><div class="stat-v" style="color:var(--red);">&minus;$620M</div><div class="stat-chg dn">&minus;1.4% AUM</div></div></div>
    <div class="stat"><div class="stat-k">Spot ETH ETFs &middot; 30D Net</div><div><div class="stat-v" style="color:var(--red);">&minus;$410M</div><div class="stat-chg dn">RETAIL-DRIVEN</div></div></div>
    <div class="stat"><div class="stat-k">Grayscale GBTC</div><div><div class="stat-v" style="color:var(--red);">&minus;$180M</div><div class="stat-chg dn">LEGACY UNWIND CONT.</div></div></div>
  </div>
</section>
'''

# ============================================================
# DASHBOARD
# ============================================================
DASHBOARD_BODY = '''
<header class="page-head">
  <div class="page-eyebrow"><span class="tag filled">DASHBOARD</span><span>Everything, one screen</span><span class="divider"></span><span class="muted">LIVE &middot; 14:32 CET</span></div>
  <h1 class="page-title">The <em>whole market,</em> at a glance.</h1>
  <p class="page-dek">Every datapoint I check before 09:00, every morning. Equity, rates, FX, crypto, commodities, sentiment. Densely packed, ruthlessly prioritized.</p>
</header>

<section class="section" style="padding-top:48px;">
  <div class="section-header">
    <h2 class="section-title"><span class="num">&sect; 01</span> Equities</h2>
    <div class="section-meta">MAJOR INDICES</div>
  </div>
  <div class="stat-grid" style="grid-template-columns:repeat(6,1fr);">
    <div class="stat"><div class="stat-k">S&amp;P 500</div><div><div class="stat-v">5,684</div><div class="stat-chg dn">&minus;0.62%</div></div><svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line dn" points="0,10 20,8 40,12 60,15 80,18 100,22"/></svg></div>
    <div class="stat"><div class="stat-k">Nasdaq 100</div><div><div class="stat-v">19,832</div><div class="stat-chg dn">&minus;0.81%</div></div><svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line dn" points="0,8 20,10 40,14 60,18 80,22 100,26"/></svg></div>
    <div class="stat"><div class="stat-k">Dow 30</div><div><div class="stat-v">42,518</div><div class="stat-chg dn">&minus;0.38%</div></div><svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line dn" points="0,14 20,12 40,14 60,16 80,18 100,20"/></svg></div>
    <div class="stat"><div class="stat-k">STOXX 600</div><div><div class="stat-v">512</div><div class="stat-chg dn">&minus;0.24%</div></div><svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line dn" points="0,16 20,14 40,16 60,18 80,20 100,22"/></svg></div>
    <div class="stat"><div class="stat-k">Nikkei 225</div><div><div class="stat-v">38,812</div><div class="stat-chg up">+0.42%</div></div><svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line up" points="0,22 20,20 40,18 60,16 80,14 100,12"/></svg></div>
    <div class="stat"><div class="stat-k">BIST 100</div><div><div class="stat-v">10,284</div><div class="stat-chg up">+1.20%</div></div><svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line up" points="0,24 20,20 40,16 60,14 80,10 100,6"/></svg></div>
  </div>
</section>

<section class="section">
  <div class="section-header">
    <h2 class="section-title"><span class="num">&sect; 02</span> Rates &amp; FX</h2>
    <div class="section-meta">BENCHMARK YIELDS + G10</div>
  </div>
  <div class="stat-grid" style="grid-template-columns:repeat(6,1fr);">
    <div class="stat"><div class="stat-k">US 2Y</div><div><div class="stat-v">4.63<small>%</small></div><div class="stat-chg up">+12bp</div></div></div>
    <div class="stat"><div class="stat-k">US 10Y</div><div><div class="stat-v">4.38<small>%</small></div><div class="stat-chg up">+4bp</div></div></div>
    <div class="stat"><div class="stat-k">German 10Y</div><div><div class="stat-v">2.52<small>%</small></div><div class="stat-chg up">+2bp</div></div></div>
    <div class="stat"><div class="stat-k">UK 10Y</div><div><div class="stat-v">4.12<small>%</small></div><div class="stat-chg up">+3bp</div></div></div>
    <div class="stat"><div class="stat-k">EUR/USD</div><div><div class="stat-v">1.0684</div><div class="stat-chg dn">&minus;0.21%</div></div></div>
    <div class="stat"><div class="stat-k">USD/TRY</div><div><div class="stat-v">34.82</div><div class="stat-chg up">+0.11%</div></div></div>
  </div>
</section>

<section class="section">
  <div class="section-header">
    <h2 class="section-title"><span class="num">&sect; 03</span> Crypto</h2>
    <div class="section-meta"><a href="crypto.html">FULL CRYPTO &rarr;</a></div>
  </div>
  <div class="stat-grid" style="grid-template-columns:repeat(6,1fr);">
    <div class="stat"><div class="stat-k">BTC</div><div><div class="stat-v">$67.4K</div><div class="stat-chg dn">&minus;1.82%</div></div><svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line dn" points="0,8 20,12 40,14 60,18 80,22 100,26"/></svg></div>
    <div class="stat"><div class="stat-k">ETH</div><div><div class="stat-v">$3,284</div><div class="stat-chg dn">&minus;2.41%</div></div><svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line dn" points="0,6 20,10 40,14 60,18 80,22 100,28"/></svg></div>
    <div class="stat"><div class="stat-k">SOL</div><div><div class="stat-v">$142</div><div class="stat-chg dn">&minus;3.10%</div></div><svg class="stat-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline class="spark-line dn" points="0,8 20,12 40,16 60,20 80,24 100,28"/></svg></div>
    <div class="stat"><div class="stat-k">BTC Dominance</div><div><div class="stat-v">54.2<small>%</small></div><div class="stat-chg up">+0.8pp</div></div></div>
    <div class="stat"><div class="stat-k">Total MCap</div><div><div class="stat-v">$2.4<small>T</small></div><div class="stat-chg dn">&minus;1.9%</div></div></div>
    <div class="stat"><div class="stat-k">F&amp;G Index</div><div><div class="stat-v" style="color:var(--red);">18</div><div class="stat-chg dn">EXTREME FEAR</div></div></div>
  </div>
</section>

<section class="section">
  <div class="section-header">
    <h2 class="section-title"><span class="num">&sect; 04</span> Commodities &amp; Volatility</h2>
    <div class="section-meta">KEY INPUTS</div>
  </div>
  <div class="stat-grid" style="grid-template-columns:repeat(6,1fr);">
    <div class="stat"><div class="stat-k">Brent</div><div><div class="stat-v">$106</div><div class="stat-chg up">+3.12%</div></div></div>
    <div class="stat"><div class="stat-k">WTI</div><div><div class="stat-v">$101</div><div class="stat-chg up">+2.84%</div></div></div>
    <div class="stat"><div class="stat-k">Gold</div><div><div class="stat-v">$2,614</div><div class="stat-chg up">+0.74%</div></div></div>
    <div class="stat"><div class="stat-k">Copper</div><div><div class="stat-v">$4.28</div><div class="stat-chg up">+0.38%</div></div></div>
    <div class="stat"><div class="stat-k">VIX</div><div><div class="stat-v">26.8</div><div class="stat-chg dn">ELEVATED</div></div></div>
    <div class="stat"><div class="stat-k">MOVE</div><div><div class="stat-v">118</div><div class="stat-chg dn">BOND VOL HIGH</div></div></div>
  </div>
</section>

<section class="section">
  <div class="section-header">
    <h2 class="section-title"><span class="num">&sect; 05</span> This Week</h2>
    <div class="section-meta">W16 &middot; APR 07 &rarr; 14</div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:1px;background:var(--border);border:1px solid var(--border);">''' + ''.join([
f'''
    <div style="padding:22px;background:var(--bg-elev);">
      <div style="font-family:var(--serif);font-size:32px;line-height:1;margin-bottom:4px;">{d}</div>
      <div style="font-family:var(--mono);font-size:10px;letter-spacing:0.2em;color:var(--amber);text-transform:uppercase;margin-bottom:14px;">{day}</div>
      <div style="font-size:13px;line-height:1.4;margin-bottom:6px;"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--{ic});margin-right:6px;"></span>{ev}</div>
      <div style="font-family:var(--mono);font-size:10px;color:var(--text-mute);letter-spacing:0.06em;">{note}</div>
    </div>'''
for d, day, ic, ev, note in [
  ('07','Tue','red','Flash PMI &middot; March','FIRST WAR-ERA READING'),
  ('08','Wed','text-mute','FOMC Minutes','MARCH MEETING'),
  ('09','Thu','amber','ECB Lagarde + Claims','RATE PATH SIGNAL'),
  ('11','Fri','amber','Eurozone HICP','WAR-IMPACT INFLATION'),
  ('14','Mon','red','US CPI + PPI &#9733;','MAIN EVENT'),
]
]) + '''
  </div>
</section>
'''

# ============================================================
# ARTICLES
# ============================================================
ARTICLES_BODY = '''
<header class="page-head">
  <div class="page-eyebrow"><span class="tag filled">SUNDAY</span><span>Weekly deep dives, one idea fully thought through</span><span class="divider"></span><span class="muted">47 ISSUES PUBLISHED</span></div>
  <h1 class="page-title">The <em>Sunday Morning</em> Series.</h1>
  <p class="page-dek">Every Sunday I try to answer one macro question &mdash; not what the headlines are saying, but what the data actually shows. No recycled hot takes. No crypto maximalism. Just the work.</p>
</header>

<section class="section" style="padding-top:48px;">
  <div class="section-header">
    <h2 class="section-title"><span class="num">LATEST</span> Issue &#8470;47</h2>
    <div class="section-meta">APR 14, 2026 &middot; 7 MIN READ</div>
  </div>
  <article id="smart-money" style="display:grid;grid-template-columns:1fr 2fr;gap:48px;padding-bottom:48px;border-bottom:1px solid var(--border);">
    <div style="font-family:var(--serif);font-size:180px;font-weight:300;line-height:0.85;color:var(--amber);letter-spacing:-0.04em;">04</div>
    <div>
      <div style="font-family:var(--mono);font-size:10px;letter-spacing:0.22em;color:var(--amber);text-transform:uppercase;margin-bottom:16px;">Crypto &middot; Smart Money</div>
      <h2 style="font-family:var(--serif);font-weight:300;font-size:52px;line-height:1.05;letter-spacing:-0.02em;margin-bottom:20px;">Smart money didn&#8217;t <em style="color:var(--amber);">lead</em>. It <em style="color:var(--amber);">retreated</em>.</h2>
      <p style="font-size:17px;line-height:1.65;color:var(--text-dim);margin-bottom:24px;">JPMorgan called Q1 2026 the year institutions would dominate crypto flows. The data tells a different story: Iran war, VIX at 26, Fear &amp; Greed at 12. The Coinbase Premium Index shows exactly where the real money went &mdash; and it wasn&#8217;t in. Here&#8217;s what 90 days of flow data reveals about how institutions actually behave in risk-off regimes.</p>
      <a href="#" class="btn">Read the full issue <span class="arrow">&rarr;</span></a>
    </div>
  </article>
</section>

<section class="section">
  <div class="section-header">
    <h2 class="section-title"><span class="num">ARCHIVE</span> All Issues</h2>
    <div class="section-meta">FILTER: ALL &middot; MACRO &middot; CRYPTO &middot; ENERGY &middot; COMMODITIES</div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:1px;background:var(--border);border:1px solid var(--border);">''' + ''.join([
f'''
    <article id="{slug}" style="padding:32px 28px;background:var(--bg-elev);display:flex;flex-direction:column;min-height:260px;">
      <div style="display:flex;justify-content:space-between;margin-bottom:18px;">
        <div style="font-family:var(--mono);font-size:10px;letter-spacing:0.22em;color:var(--amber);text-transform:uppercase;">{cat}</div>
        <div style="font-family:var(--serif);font-size:42px;font-weight:300;line-height:1;color:var(--border);">{num}</div>
      </div>
      <h3 style="font-family:var(--serif);font-weight:400;font-size:28px;line-height:1.2;margin-bottom:14px;flex:1;">{title}</h3>
      <p style="font-size:14px;color:var(--text-dim);line-height:1.6;margin-bottom:18px;">{excerpt}</p>
      <div style="font-family:var(--mono);font-size:10px;letter-spacing:0.14em;color:var(--text-mute);text-transform:uppercase;padding-top:14px;border-top:1px solid var(--border);display:flex;justify-content:space-between;"><span>{date}</span><span>{mins} MIN READ</span></div>
    </article>'''
for num, cat, title, excerpt, date, mins, slug in [
  ('03','Energy &middot; Infrastructure','AI needs electricity. The answer is nuclear.','IEA: data centers will consume 945 TWh by 2030 &mdash; all of Japan&#8217;s annual electricity. Microsoft $16B, Amazon $20B+, Google 500MW. This is not an energy story, it&#8217;s a capital allocation story.','APR 06, 2026','9','nukleer'),
  ('02','Commodities &middot; Macro','Dr. Copper &mdash; wrong diagnosis?','Historically the economy&#8217;s thermometer. But AI data centers, EVs, and renewables all demand it simultaneously. S&amp;P Global projects a 10M tonne deficit by 2040. Dr. Copper may have a new disease.','MAR 30, 2026','8','bakir'),
  ('01','Macro &middot; Inflation','Why the 1970s comparison is misleading.','Brent up 40%, Hormuz closed, 1970s analogies everywhere. But in 1973 it took 1 barrel per $1,000 GDP. Today: 0.43. PPI came in double expectations. Powell said &ldquo;we don&#8217;t know&rdquo; 17 times.','MAR 23, 2026','10','petrol'),
  ('00','Preview','&ldquo;Too Late Powell&rdquo; &mdash; or was he right?','Trump called him &ldquo;Too Late Powell.&rdquo; But by not cutting rates, he may have protected the economy from shocks. Coming after March CPI &mdash; all scenarios on the table.','COMING SOON','&mdash;','powell'),
]
]) + '''
  </div>
</section>
'''

# ============================================================
# ABOUT
# ============================================================
ABOUT_BODY = '''
<header class="page-head">
  <div class="page-eyebrow"><span class="tag filled">ABOUT</span><span>Who writes this &middot; why &middot; methodology</span></div>
  <h1 class="page-title">One finance person.<br/><em>A real job.</em><br/>A point of view.</h1>
</header>

<section class="section" style="padding-top:48px;">
  <div style="display:grid;grid-template-columns:1fr 2fr;gap:56px;max-width:1100px;margin:0 auto;">
    <aside style="position:sticky;top:80px;height:fit-content;">
      <div style="width:200px;height:200px;border-radius:50%;background:linear-gradient(135deg,var(--amber) 0%,#b87f1f 100%);display:grid;place-items:center;color:#0b0b0d;font-weight:700;font-family:var(--mono);font-size:72px;letter-spacing:0.05em;margin-bottom:24px;">OB</div>
      <div style="font-family:var(--mono);font-size:11px;letter-spacing:0.14em;color:var(--text-mute);text-transform:uppercase;margin-bottom:6px;">Contact</div>
      <div style="display:flex;flex-direction:column;gap:8px;font-size:14px;">
        <a href="mailto:orkun@nocashflow.net" style="color:var(--amber);">orkun@nocashflow.net</a>
        <a href="https://twitter.com/No_CashFlow" style="color:var(--text-dim);">@No_CashFlow</a>
        <a href="https://www.linkedin.com/in/orkunbicen/" style="color:var(--text-dim);">LinkedIn</a>
      </div>
    </aside>
    <div>
      <h2 style="font-family:var(--serif);font-weight:300;font-size:48px;line-height:1.1;letter-spacing:-0.02em;margin-bottom:24px;">Orkun Bi&ccedil;en</h2>
      <p style="font-family:var(--serif);font-size:22px;line-height:1.5;color:var(--text-dim);font-style:italic;margin-bottom:36px;">Senior finance professional. Zone EUR MCS Controller at Nestl&eacute; Barcelona. Writing about macro in my spare time because the market deserves better signal.</p>
      
      <h3 style="font-family:var(--mono);font-size:12px;letter-spacing:0.24em;color:var(--amber);text-transform:uppercase;margin-bottom:14px;">Background</h3>
      <p style="font-size:16px;line-height:1.7;margin-bottom:24px;">Ten years in corporate finance at multinationals (Schneider Electric, Nestl&eacute; Waters Istanbul, now Nestl&eacute; Barcelona). P&amp;L ownership, dynamic forecasting, transfer pricing, cost allocation models. Master&#8217;s in Finance.</p>
      <p style="font-size:16px;line-height:1.7;margin-bottom:36px;">What that means for this site: I build financial models for a living. I know how to read a balance sheet. I know when a forecast is wishful thinking dressed as analysis.</p>

      <h3 id="methodology" style="font-family:var(--mono);font-size:12px;letter-spacing:0.24em;color:var(--amber);text-transform:uppercase;margin-bottom:14px;">Methodology</h3>
      <p style="font-size:16px;line-height:1.7;margin-bottom:14px;">Three rules:</p>
      <ol style="font-size:16px;line-height:1.7;margin-bottom:36px;padding-left:24px;display:flex;flex-direction:column;gap:14px;">
        <li><strong style="color:var(--amber);">Primary sources over secondary.</strong> I read the Fed minutes, not a Bloomberg summary of them. I look at the JPM memo, not the tweet thread about it.</li>
        <li><strong style="color:var(--amber);">Data beats narrative.</strong> If the CPI print contradicts the story, the story is wrong. Not the print.</li>
        <li><strong style="color:var(--amber);">I tell you when I&#8217;m wrong.</strong> Every Sunday issue has a &ldquo;what could kill this thesis&rdquo; section. I mean it.</li>
      </ol>

      <h3 id="sources" style="font-family:var(--mono);font-size:12px;letter-spacing:0.24em;color:var(--amber);text-transform:uppercase;margin-bottom:14px;">Sources I use</h3>
      <p style="font-size:16px;line-height:1.7;margin-bottom:24px;">Bloomberg, Refinitiv, FT, Reuters, ECB, Fed, BIS, IEA, EIA, BLS, JPM Research, Goldman Research, Morgan Stanley, S&amp;P Global, Kaiko, CryptoQuant, CoinGecko, Glassnode, TradingView. Always cited inline.</p>

      <h3 style="font-family:var(--mono);font-size:12px;letter-spacing:0.24em;color:var(--amber);text-transform:uppercase;margin-bottom:14px;">Disclaimer</h3>
      <p style="font-size:14px;line-height:1.65;color:var(--text-dim);">This site does not provide investment advice. All content is for informational purposes. I may hold positions in instruments I discuss. I always disclose when it matters. Always do your own research.</p>
    </div>
  </div>
</section>
'''

# ============================================================
# GLOSSARY
# ============================================================
GLOSSARY_BODY = '''
<header class="page-head">
  <div class="page-eyebrow"><span class="tag filled">GLOSSARY</span><span>TR + EN &middot; 247 terms and counting</span></div>
  <h1 class="page-title">The <em>vocabulary</em>.</h1>
  <p class="page-dek">Every term used on this site, defined simply. Not like a textbook &mdash; like how a colleague would explain it to you in a meeting.</p>
</header>

<section class="section" style="padding-top:48px;">
  <input type="text" placeholder="Search terms..." style="width:100%;max-width:500px;padding:16px 20px;background:var(--bg-elev);border:1px solid var(--border);color:var(--text);font-family:var(--mono);font-size:14px;margin-bottom:40px;" oninput="Array.from(document.querySelectorAll('.glossary-item')).forEach(el=>el.style.display=el.textContent.toLowerCase().includes(this.value.toLowerCase())?'':'none')" />

  <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:1px;background:var(--border);border:1px solid var(--border);">''' + ''.join([
f'''
    <div class="glossary-item" style="padding:28px 24px;background:var(--bg-elev);">
      <div style="font-family:var(--mono);font-size:10px;letter-spacing:0.2em;color:var(--amber);text-transform:uppercase;margin-bottom:8px;">{cat}</div>
      <h3 style="font-family:var(--serif);font-style:italic;font-weight:400;font-size:26px;color:var(--amber);margin-bottom:12px;">{term}</h3>
      <p style="font-size:14px;line-height:1.6;color:var(--text-dim);">{defn}</p>
    </div>'''
for cat, term, defn in [
  ('CRYPTO','Coinbase Premium Index','The difference between BTC price on Coinbase (USD-based, US institutional) and Binance (USDT-based, global retail). Positive = US buying pressure. Negative = offshore flows dominate. A leading indicator for institutional behavior.'),
  ('MACRO','DXY','US Dollar Index. Measures USD strength against a basket of six currencies (EUR, JPY, GBP, CAD, SEK, CHF). Rises when dollar strengthens. Negatively correlated with most risk assets and commodities priced in dollars.'),
  ('CRYPTO','Fear &amp; Greed Index','A 0&ndash;100 sentiment gauge for crypto markets from Alternative.me. Combines volatility, momentum, social, survey, dominance, and trends. Below 20 = extreme fear, historically a contrarian buy signal. Above 80 = extreme greed, a warning sign.'),
  ('RATES','Yield Curve','A plot of Treasury yields across maturities (3M, 2Y, 10Y, 30Y). Normal = upward sloping. Inverted (short yields above long) = recession signal historically. The 2Y/10Y spread is the most-watched.'),
  ('MACRO','CPI vs PPI','CPI = Consumer Price Index, what households pay. PPI = Producer Price Index, what businesses pay. PPI leads CPI by 1&ndash;3 months. A hot PPI print is a warning that CPI is coming.'),
  ('VOL','VIX','CBOE Volatility Index. Measures 30-day implied volatility on S&amp;P 500 options. Below 15 = calm. 20&ndash;25 = worried. Above 30 = panic. &ldquo;The fear gauge.&rdquo;'),
  ('CRYPTO','MiCA','Markets in Crypto-Assets Regulation. EU framework for crypto, fully in effect April 2026. Requires stablecoin issuers to be licensed and reserve-audited. Created regulatory moats: USDC compliant, USDT not.'),
  ('RATES','Dot Plot','Federal Reserve&#8217;s quarterly projection of where each FOMC member sees the fed funds rate at year-end, one year out, two years out, long-run. The median dot is what markets price.'),
  ('CRYPTO','BTC Dominance','Bitcoin&#8217;s share of total crypto market cap. Rising dominance in selloffs = flight to quality within crypto. Rising in rallies = institutions are in. Falling dominance = alt season.'),
  ('COMMODITIES','Contango vs Backwardation','Contango: futures priced above spot (storage costs, expected price rise). Backwardation: futures below spot (immediate demand, supply tight). Backwardation in oil = a bullish signal.'),
]
]) + '''
  </div>
</section>
'''

# ============================================================
# 404
# ============================================================
NOT_FOUND_BODY = '''
<section class="section" style="padding:160px var(--pad);text-align:center;max-width:800px;margin:0 auto;">
  <div style="font-family:var(--serif);font-weight:300;font-size:200px;line-height:1;color:var(--amber);letter-spacing:-0.05em;margin-bottom:20px;">404</div>
  <h1 style="font-family:var(--serif);font-weight:300;font-size:48px;line-height:1.1;margin-bottom:20px;">This page <em style="color:var(--amber);">doesn&#8217;t exist.</em></h1>
  <p style="font-size:17px;color:var(--text-dim);line-height:1.6;margin-bottom:36px;">Either something moved, or you mistyped the URL, or I broke the link. Head back home and you&#8217;ll find what you need.</p>
  <a href="index.html" class="btn-amber">Go home <span class="arrow">&rarr;</span></a>
</section>
'''

# ============================================================
# GENERATE ALL PAGES
# ============================================================
pages = {
  'index.html': ('NoCashFlow — Macro, Markets & the Signal in the Noise', 'Sunday morning macro analysis, daily market bulletin, and the data institutional investors actually watch. By Orkun Biçen, from Barcelona.', INDEX_BODY),
  'bulletin.html': ('Daily Bulletin — NoCashFlow', 'Market intelligence before the open. Macro, rates, crypto, commodities — six stories, four minutes. No filler.', BULLETIN_BODY),
  'macro.html': ('Macro Dashboard — NoCashFlow', 'Central bank rates, yield curves, inflation prints, FX. What institutional macro desks actually watch.', MACRO_BODY),
  'crypto.html': ('Crypto — NoCashFlow', 'Crypto through a macro lens. Institutional flows, stablecoin supply, regulatory infrastructure, and the data that tells the truth.', CRYPTO_BODY),
  'dashboard.html': ('Dashboard — NoCashFlow', 'Equity, rates, FX, crypto, commodities, sentiment. Everything, one screen.', DASHBOARD_BODY),
  'yazilar.html': ('Sunday Morning Series — NoCashFlow', 'Every Sunday, one macro question, fully thought through. Archive of all issues.', ARTICLES_BODY),
  'hakkinda.html': ('About — NoCashFlow', 'Orkun Biçen — Zone EUR MCS Controller at Nestlé. Writing about macro because the market deserves better signal.', ABOUT_BODY),
  'sozluk.html': ('Glossary — NoCashFlow', 'Every financial term used on this site, defined simply. TR + EN, 247 terms and counting.', GLOSSARY_BODY),
  '404.html': ('404 — NoCashFlow', 'Page not found.', NOT_FOUND_BODY),
}

for fname, (title, desc, body) in pages.items():
  html = page(title, desc, body)
  (OUT / fname).write_text(html, encoding='utf-8')
  print(f'wrote {fname}  ({len(html)/1024:.1f} KB)')

print('\nDone.')
