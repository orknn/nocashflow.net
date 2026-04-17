# nocashflow.net — Redesigned

Full redesign of the NoCashFlow site. All pages share a single stylesheet and JS so changes propagate site-wide.

---

## What changed

- **New unified design system** — anthracite + amber, Fraunces (editorial serif) + IBM Plex Sans + JetBrains Mono
- **All 4 tabs fully functional**: Bulletin, Macro, Crypto, Dashboard
- **Shared chrome** — one stylesheet (`assets/site.css`), one JS (`assets/site.js`). Edit the ticker once, it updates everywhere.
- **Live ticker** with CoinGecko integration (BTC/ETH real prices; others stay static for now)
- **SEO + social meta tags** per page (Open Graph, Twitter cards, theme color)
- **Mobile responsive** — tested down to 360px width
- **404 page** — Google Pages needs one
- **Preserved**: `CNAME`, `daily_bulletin.html`, `daily_bulletin.pdf`

---

## File map

```
/
├── assets/
│   ├── site.css          ← design system (edit this to change everything)
│   └── site.js           ← ticker + forms + nav logic
├── index.html            ← homepage
├── bulletin.html         ← NEW: daily bulletin feed (replaces bulletin_page.html)
├── macro.html            ← macro dashboard: rates, yield curve, inflation, FX
├── crypto.html           ← NEW: top assets, Coinbase Premium, stablecoins, ETF flows
├── dashboard.html        ← unified one-screen data view
├── yazilar.html          ← Sunday Morning Series archive
├── hakkinda.html         ← About
├── sozluk.html           ← Glossary (searchable)
├── 404.html              ← Page not found
├── daily_bulletin.html   ← preserved from old site
├── daily_bulletin.pdf    ← preserved from old site
├── CNAME                 ← nocashflow.net (preserved)
└── build.py              ← source that generated all HTML (keep for future edits)
```

---

## Deploy in 3 commands

From the `Web_Sitesi` folder:

```bash
# 1) Test locally first (Python 3 has a built-in server)
python3 -m http.server 8000
# Open http://localhost:8000 — check every page

# 2) Once you're happy, commit and push
git add -A
git commit -m "Full site redesign: unified design system + functional tabs"
git push
```

GitHub Pages picks up the changes in ~30 seconds. nocashflow.net will be live.

---

## If you want to edit the site later

**Small change (text, a price, a date):** edit the relevant `.html` file directly.

**Design change (color, font, spacing):** edit `assets/site.css`. One file, whole site updates.

**Structural change (add a new page, change nav):** edit `build.py`, then run:
```bash
python3 build.py
```
It regenerates every HTML file with your new nav / footer / ticker. This is the right way to keep everything consistent.

---

## Next steps I'd recommend

### Immediately
- [ ] Replace the static ticker values with real data (CoinGecko is already wired for BTC/ETH — extend to gold/brent/etc via free APIs)
- [ ] Hook up the newsletter form to Mailerlite or Substack (search for `TODO: POST to Mailerlite` in `assets/site.js`)
- [ ] Add a favicon (`favicon.ico` at root)
- [ ] Generate an OG preview image (`assets/og.png`, 1200×630) for link previews on Twitter/LinkedIn

### Growth (week 1)
- [ ] Set up Plausible or Fathom analytics (GDPR-friendly, no cookie banner needed)
- [ ] Submit sitemap to Google Search Console (`sitemap.xml` generator: github.com/sitemap-generators)
- [ ] Write first 5 glossary entries as standalone articles for SEO (e.g. `sozluk/dxy-nedir.html`, `sozluk/coinbase-premium-index-nedir.html`)

### Monetization (month 2+)
- [ ] Apply to Ezoic or Mediavine once monthly visitors > 10k
- [ ] Affiliate signups: Interactive Brokers, Trading212, Ledger, Bitpanda
- [ ] Launch "NoCashFlow Pro" paid tier via Substack or Ghost (€9/mo, weekly deep-dive + private Discord)

---

## A few things worth knowing

**The ticker auto-refreshes BTC/ETH** via CoinGecko's public API (no key needed). If the API blocks you or goes down, the static fallback values still display — nothing breaks.

**The newsletter form is a placeholder.** Right now it just shows a "Subscribed ✓" confirmation but doesn't actually store the email. Wire it to your provider of choice:
- **Mailerlite** (recommended, free up to 1k subscribers): https://www.mailerlite.com/features/forms
- **Substack**: create a Substack, then embed their form code
- **Buttondown** (nerdy, simple): https://buttondown.email

**All data shown is illustrative.** Prices, percentages, bulletin entries are sample content. When you have real daily bulletin data, either edit the HTML directly or (better) wire the Antigravity agent you spec'd to populate them.

**CNAME is preserved** so your custom domain keeps working. Don't delete that file.

---

Built in Barcelona. Ship it when you're ready.
