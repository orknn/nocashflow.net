/* ============================================================
   NoCashFlow · Shared front-end engine
   - Robust market data (CoinGecko + Yahoo via proxy fallback)
   - Last-good caching so a failed fetch shows the previous value
   - Ticker rendering, mobile menu, newsletter handler
   Author: Orkun Biçen
   ============================================================ */
(function () {
  'use strict';

  const NCF = (window.NCF = window.NCF || {});

  /* ---------- helpers ---------- */
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function fmtPct(n) {
    if (n == null || isNaN(n)) return '—';
    return (n >= 0 ? '+' : '') + n.toFixed(2) + '%';
  }
  function fmtNum(n, dec = 2, prefix = '') {
    if (n == null || isNaN(n)) return '—';
    const v = n >= 1000 ? n.toLocaleString('en-US', { maximumFractionDigits: 0 })
                        : n.toFixed(dec);
    return prefix + v;
  }
  NCF.fmtPct = fmtPct;
  NCF.fmtNum = fmtNum;

  /* ---------- in-session store ----------
     Holds close series for sparklines within the page's lifetime. It is NOT
     persisted and is NOT a display fallback: a value from an earlier visit has
     no timestamp on screen, so painting it would state a number the page
     cannot stand behind. When a live source fails we keep whatever the stamped
     snapshot painted, and when that fails too we show em dashes. */
  const store = {};

  /* ---------- proxy fallback for Yahoo Finance ---------- */
  const PROXIES = [
    (u) => 'https://corsproxy.io/?url=' + encodeURIComponent(u),
    (u) => 'https://api.allorigins.win/raw?url=' + encodeURIComponent(u),
    (u) => 'https://api.codetabs.com/v1/proxy?quest=' + encodeURIComponent(u),
  ];

  async function fetchWithProxies(targetUrl, timeoutMs = 8000) {
    for (const wrap of PROXIES) {
      const ctrl = new AbortController();
      const t = setTimeout(() => ctrl.abort(), timeoutMs);
      try {
        const res = await fetch(wrap(targetUrl), { signal: ctrl.signal });
        clearTimeout(t);
        if (!res.ok) continue;
        const text = await res.text();
        return JSON.parse(text);
      } catch (e) {
        clearTimeout(t);
      }
    }
    return null;
  }

  /* Fetch one Yahoo chart symbol -> {last, prev, pct, closes} */
  async function fetchYahoo(sym, range = '10d') {
    const url = 'https://query1.finance.yahoo.com/v8/finance/chart/' +
      encodeURIComponent(sym) + '?interval=1d&range=' + range;
    const data = await fetchWithProxies(url);
    const ch = data && data.chart && data.chart.result && data.chart.result[0];
    if (!ch) return null;
    try {
      const closes = ch.indicators.quote[0].close.filter((x) => x != null);
      const last = closes[closes.length - 1];
      const prev = closes[closes.length - 2];
      return { last, prev, pct: prev ? ((last - prev) / prev) * 100 : 0, closes };
    } catch (e) { return null; }
  }
  NCF.fetchYahoo = fetchYahoo;

  /* CoinGecko crypto (direct, CORS-friendly) */
  async function fetchCrypto(ids) {
    try {
      const res = await fetch(
        'https://api.coingecko.com/api/v3/simple/price?ids=' +
        ids.join(',') + '&vs_currencies=usd&include_24hr_change=true'
      );
      if (!res.ok) return null;
      return await res.json();
    } catch (e) { return null; }
  }

  /* Same-origin daily snapshot (data/market.json, written by the server-side
     cron) — fetched first so the ticker paints instantly instead of sitting
     on "—" while the Yahoo/CORS-proxy chain below churns in the background. */
  async function fetchSnapshot() {
    try {
      const res = await fetch('/data/market.json', { cache: 'no-store' });
      if (!res.ok) return null;
      return await res.json();
    } catch (e) { return null; }
  }

  function paintSnapshot(key, val) {
    $$('[data-px="' + key + '"]').forEach((el) => { el.textContent = val.px; });
    $$('[data-chg="' + key + '"]').forEach((el) => {
      el.textContent = val.chg;
      el.classList.remove('up', 'dn', 'neu');
      el.classList.add(val.dir || 'neu');
    });
  }

  /* ---------- provenance: every painted number carries its timestamp ----------
     The page ships with no numbers baked in, so nothing on screen can be older
     than the snapshot these stamps describe. */
  const STALE_AFTER_MS = 24 * 60 * 60 * 1000;
  const MOOD_INDEX = { fear: 0, neutral: 1, greed: 2 };

  /* ISO -> "2026-08-07 06:11 UTC". UTC on purpose: unambiguous year-round, and
     it matches the timestamp the pipeline writes. */
  function fmtStamp(iso) {
    const d = new Date(iso);
    if (!iso || isNaN(d.getTime())) return null;
    const p = (n) => String(n).padStart(2, '0');
    return d.getUTCFullYear() + '-' + p(d.getUTCMonth() + 1) + '-' + p(d.getUTCDate()) +
      ' ' + p(d.getUTCHours()) + ':' + p(d.getUTCMinutes()) + ' UTC';
  }

  function isStale(iso) {
    const d = new Date(iso);
    if (!iso || isNaN(d.getTime())) return false;
    return (Date.now() - d.getTime()) > STALE_AFTER_MS;
  }

  /* Text for a stamp slot, e.g. "as of 2026-08-07 06:11 UTC · stale".
     `attr` names the template to use: standalone stamps carry it on data-tpl,
     while the footer sentence keeps data-tpl for its own copy and puts the
     timestamp template on data-asof. */
  function stampText(el, iso, attr) {
    const stamp = fmtStamp(iso);
    if (!stamp) return '';
    const tpl = el.getAttribute(attr || 'data-tpl') || '{stamp}';
    let out = tpl.replace('{stamp}', stamp);
    if (isStale(iso)) {
      const word = el.getAttribute('data-stale');
      if (word) out += ' · ' + word;
    }
    return out;
  }

  function paintStamps(iso) {
    $$('[data-live-stamp]').forEach((el) => {
      const txt = stampText(el, iso);
      el.textContent = txt;
      el.classList.toggle('is-stale', !!txt && isStale(iso));
    });
  }

  /* Footer sentence + hero badge. Both are composed here from copy the build
     put on data-attributes, so no user-visible string is hardcoded in JS. */
  function paintMood(value, iso) {
    const v = parseInt(value, 10);
    if (isNaN(v)) return;
    const mood = v < 35 ? 'fear' : v > 55 ? 'greed' : 'neutral';
    const i = MOOD_INDEX[mood];
    document.body.setAttribute('data-mood', mood);

    $$('[data-mood-pill]').forEach((el) => {
      el.setAttribute('data-m', mood === 'neutral' ? 'neu' : mood);
      const words = (el.getAttribute('data-words') || '').split('|');
      const w = el.querySelector('[data-mood-word]');
      if (w && words.length === 3) w.textContent = words[i];
    });

    $$('[data-mood-line]').forEach((el) => {
      const words = (el.getAttribute('data-words') || '').split('|');
      const tpl = el.getAttribute('data-tpl');
      if (!tpl || words.length !== 3) return;
      const sentence = tpl.replace('{mood}', words[i]).replace('{v}', v);
      const stamp = stampText(el, iso, 'data-asof');
      el.innerHTML = '<span class="mood-dot"></span>' +
        sentence + (stamp ? ' <span class="mood-asof">· ' + stamp + '</span>' : '');
      el.classList.toggle('is-stale', isStale(iso));
    });
  }

  /* Nothing reached us: say so rather than leaving a bare dash the reader has
     to interpret, and drop the "Live" claim on the ticker. */
  function markLiveUnavailable() {
    $$('[data-live-label]').forEach((el) => { el.hidden = true; });
    $$('[data-mood-line]').forEach((el) => {
      const msg = el.getAttribute('data-fail');
      if (msg) el.innerHTML = '<span class="mood-dot"></span>' + msg;
    });
    $$('[data-live-stamp]').forEach((el) => {
      const msg = el.getAttribute('data-fail');
      if (msg) el.textContent = msg;
    });
  }

  /* Paint every instrument the snapshot carries. Pages that opt out of the
     live loader (market:false — macro, dashboard) still call this, otherwise
     their ticker would sit on "—" forever. */
  async function paintSnapshotAll() {
    const snap = await fetchSnapshot();
    if (!snap || !snap.instruments) {
      markLiveUnavailable();
      return null;
    }
    Object.keys(snap.instruments).forEach((key) => {
      if (INSTRUMENTS[key]) paintSnapshot(key, snap.instruments[key]);
    });
    const iso = snap.generated_at || snap.asof;
    paintStamps(iso);
    if (snap.instruments.fg) {
      /* the Fear & Greed reading carries its own asof when the source was
         reachable on the last run; fall back to the snapshot's */
      paintSnapshot('fg', snap.instruments.fg);
      paintMood(snap.instruments.fg.px, snap.instruments.fg.asof || iso);
    }
    $$('[data-live-label]').forEach((el) => { el.hidden = false; });
    return snap;
  }
  NCF.paintSnapshotAll = paintSnapshotAll;

  /* Fear & Greed (direct) */
  async function fetchFearGreed() {
    try {
      const res = await fetch('https://api.alternative.me/fng/?limit=1');
      const j = await res.json();
      const d = j.data[0];
      return { value: parseInt(d.value, 10), label: d.value_classification };
    } catch (e) { return null; }
  }
  NCF.fetchFearGreed = fetchFearGreed;

  /* Coinbase Premium = Coinbase BTC − Binance BTC.
     Computed client-side on purpose: Binance is reachable from browsers but
     blocked from GitHub Actions US IPs, so this can't live in the server
     snapshot. Returns { coinbase, binance, premium, pct } or null. */
  async function fetchCoinbasePremium() {
    try {
      const [cb, bn] = await Promise.all([
        fetch('https://api.coinbase.com/v2/prices/BTC-USD/spot').then((r) => r.json()),
        fetch('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT').then((r) => r.json()),
      ]);
      const c = parseFloat(cb && cb.data && cb.data.amount);
      const b = parseFloat(bn && bn.price);
      if (!c || !b) return null;
      const premium = c - b;
      return { coinbase: c, binance: b, premium, pct: (premium / b) * 100 };
    } catch (e) {
      return null;
    }
  }
  NCF.fetchCoinbasePremium = fetchCoinbasePremium;

  /* ---------- the canonical instrument set ---------- */
  /* key -> {label, fmt(price)->string}. Drives ticker + data-px/data-chg */
  const INSTRUMENTS = {
    btc:    { label: 'BTC',     fmt: (v) => fmtNum(v, 0, '$') },
    eth:    { label: 'ETH',     fmt: (v) => fmtNum(v, 0, '$') },
    gold:   { label: 'GOLD',    fmt: (v) => '$' + v.toFixed(0) },
    brent:  { label: 'BRENT',   fmt: (v) => '$' + v.toFixed(1) },
    dxy:    { label: 'DXY',     fmt: (v) => v.toFixed(2) },
    us10y:  { label: 'US10Y',   fmt: (v) => v.toFixed(2) + '%' },
    vix:    { label: 'VIX',     fmt: (v) => v.toFixed(2) },
    spx:    { label: 'S&P 500', fmt: (v) => fmtNum(v, 0) },
    eurusd: { label: 'EUR/USD', fmt: (v) => v.toFixed(4) },
  };

  /* apply a {price, pct} to all DOM nodes bound to a key */
  function paint(key, price, pct, opts = {}) {
    const inst = INSTRUMENTS[key];
    const priceStr = inst && price != null ? inst.fmt(price) : (opts.priceStr || '—');
    const dir = pct == null ? 'neu' : (opts.invert ? (pct <= 0 ? 'up' : 'dn')
                                                    : (pct >= 0 ? 'up' : 'dn'));
    $$('[data-px="' + key + '"]').forEach((el) => { el.textContent = priceStr; });
    $$('[data-chg="' + key + '"]').forEach((el) => {
      el.textContent = opts.chgStr || fmtPct(pct);
      el.classList.remove('up', 'dn', 'neu');
      el.classList.add(dir);
    });
  }
  NCF.paint = paint;

  /* ---------- ticker rendering ---------- */
  /* Build the scrolling ticker into #ticker-track from a list of keys */
  function buildTicker(keys) {
    const track = $('#ticker-track');
    if (!track) return;
    const row = keys.map((k) => {
      const inst = INSTRUMENTS[k] || { label: k.toUpperCase() };
      return '<div class="tick"><span class="sym">' + inst.label +
        '</span><span class="px" data-px="' + k + '">—</span>' +
        '<span class="chg neu" data-chg="' + k + '">—</span></div>';
    }).join('');
    /* duplicate for seamless scroll */
    track.innerHTML = row + row;
  }
  NCF.buildTicker = buildTicker;

  /* paint also updates duplicated ticker nodes automatically (querySelectorAll) */

  /* ---------- master loader ---------- */
  /* Fetches everything needed and paints any present nodes. Resilient:
     uses cached last-good value when a source fails. */
  async function loadMarket(opts = {}) {
    const updated = {};

    /* instant paint from this morning's snapshot — same-origin, no proxy
       chain, so the ticker never sits on "—" while the rest of this
       function fetches live values in the background */
    await paintSnapshotAll();

    /* A failed live call is a no-op: the stamped snapshot value stays on
       screen with its timestamp intact. Repainting an older reading here
       would put a number on the page that no visible stamp accounts for. */
    const apply = (key, price, pct, extra) => {
      if (price == null) return;
      store[key] = { price, pct, t: Date.now() };
      paint(key, price, pct, extra);
      updated[key] = true;
    };

    /* crypto first (fast + reliable) */
    const cg = await fetchCrypto(['bitcoin', 'ethereum']);
    if (cg) {
      if (cg.bitcoin)  apply('btc', cg.bitcoin.usd, cg.bitcoin.usd_24h_change);
      if (cg.ethereum) apply('eth', cg.ethereum.usd, cg.ethereum.usd_24h_change);
    }

    /* Fear & Greed — also re-stamps the footer sentence and the hero badge to
       now, since this reading came in live rather than from the snapshot. */
    const fg = await fetchFearGreed();
    if (fg) {
      store.fg = { value: fg.value, label: fg.label, t: Date.now() };
      $$('[data-px="fg"]').forEach((el) => { el.textContent = fg.value; });
      $$('[data-chg="fg"]').forEach((el) => {
        el.textContent = fg.label;
        el.classList.remove('up', 'dn', 'neu');
        el.classList.add(fg.value > 55 ? 'up' : fg.value < 35 ? 'dn' : 'neu');
      });
      paintMood(fg.value, new Date().toISOString());
    }

    /* Yahoo instruments (sequential to be gentle on proxies) */
    const yahooMap = {
      gold:  'GC=F',
      brent: 'BZ=F',
      dxy:   'DX-Y.NYB',
      us10y: '^TNX',
      vix:   '^VIX',
      spx:   '^GSPC',
      eurusd:'EURUSD=X',
    };
    const wanted = opts.yahoo || Object.keys(yahooMap);
    for (const key of wanted) {
      const sym = yahooMap[key];
      if (!sym) continue;
      const d = await fetchYahoo(sym, '10d');
      if (d) {
        apply(key, d.last, d.pct, key === 'vix' ? { invert: true } : {});
        store[key].closes = d.closes; // keep for sparklines
      }
    }

    if (typeof opts.onDone === 'function') opts.onDone(store, updated);
    return store;
  }
  NCF.loadMarket = loadMarket;

  /* ---------- sparkline ---------- */
  function sparkline(values, up) {
    if (!values || values.length < 2) return '';
    const W = 90, H = 28;
    const mn = Math.min(...values), mx = Math.max(...values), rng = (mx - mn) || 1;
    const pts = values.map((v, i) =>
      (i / (values.length - 1)) * W + ',' + (H - ((v - mn) / rng) * (H - 4) - 2)
    ).join(' ');
    const cls = up ? 'up' : 'dn';
    return '<svg viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="none">' +
      '<polyline class="spark-line ' + cls + '" points="' + pts + '"/></svg>';
  }
  NCF.sparkline = sparkline;

  /* ---------- mobile menu ---------- */
  function initMenu() {
    const toggle = $('#menu-toggle');
    const links = $('#nav-links');
    if (toggle && links) {
      toggle.addEventListener('click', () => links.classList.toggle('open'));
    }
  }

  /* ---------- newsletter ----------
     Double opt-in: POSTs {email, lang, hp} to the Cloudflare Worker at
     /api/subscribe (source + deploy in /workers/). The worker stores a pending
     row in D1 and emails a confirm link — so success here means "check your
     inbox", not "subscribed". Honest UX: real messages only, never pretend.
     `hp` is a honeypot; bots fill it and the worker drops them silently. */
  function initForms() {
    const pageTR = document.documentElement.lang === 'tr';
    const MSG = pageTR ? {
      busy: 'Gönderiliyor…',
      pending: '✓ Mailini kontrol et — onay linki yolda',
      already: '✓ Zaten abonesin',
      invalid: 'Geçerli bir e-posta gir',
      err: 'Olmadı — tekrar dene',
    } : {
      busy: 'Subscribing…',
      pending: '✓ Check your inbox — we sent a confirm link',
      already: '✓ You’re already subscribed',
      invalid: 'Enter a valid email',
      err: 'Failed — try again',
    };

    $$('form[data-newsletter]').forEach((form) => {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = form.querySelector('button[type="submit"], .newsletter-submit');
        const input = form.querySelector('input[type="email"]');
        if (!btn || !input || btn.disabled) return;
        const email = input.value.trim();
        // Bulletin language is the user's explicit choice (radio), NOT the page
        // language. Fall back to the form's data-lang / page lang if absent.
        const picked = form.querySelector('input[name="lang"]:checked');
        const lang = picked ? (picked.value === 'tr' ? 'tr' : 'en')
                   : form.dataset.lang === 'tr' ? 'tr'
                   : form.dataset.lang === 'en' ? 'en'
                   : (pageTR ? 'tr' : 'en');
        const hp = (form.querySelector('.nl-hp, input[name="hp"]') || {}).value || '';
        const scope = form.closest('section') || form.parentElement || document;
        const msgEl = scope.querySelector('[data-newsletter-msg]');
        const setMsg = (text, kind) => {
          if (msgEl) { msgEl.textContent = text; msgEl.dataset.kind = kind || ''; }
          else { btn.textContent = text; }
        };

        if (!email) { setMsg(MSG.invalid, 'err'); return; }
        const orig = btn.textContent;
        btn.textContent = MSG.busy;
        btn.disabled = true;
        if (msgEl) { msgEl.textContent = ''; msgEl.dataset.kind = ''; }

        let outcome = 'err';
        try {
          // nocashflow.net is DNS-only (unproxied), so /api/* must hit the
          // Worker on its workers.dev host, not the site origin.
          const r = await fetch('https://ncf-subscribe.bicenorkun.workers.dev/api/subscribe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, lang, hp }),
          });
          if (r.ok) {
            let data = {};
            try { data = await r.json(); } catch (_) {}
            outcome = data.status === 'already_confirmed' ? 'already' : 'pending';
          } else if (r.status === 400) {
            outcome = 'invalid';
          }
        } catch (err) { outcome = 'err'; }

        const ok = outcome === 'pending' || outcome === 'already';
        btn.textContent = orig;
        btn.disabled = false;
        if (ok) input.value = '';            // keep the address on failure for retry
        setMsg(MSG[outcome] || MSG.err, ok ? 'ok' : 'err');
      });
    });
  }

  /* ---------- year stamp ---------- */
  function initYear() {
    $$('[data-year]').forEach((el) => { el.textContent = new Date().getFullYear(); });
  }

  /* ---------- After Hours toggle (pre-paint decision lives in <head>) ------ */
  function initTheme() {
    $$('[data-theme-toggle]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const dark = document.documentElement.getAttribute('data-theme') === 'dark';
        if (dark) document.documentElement.removeAttribute('data-theme');
        else document.documentElement.setAttribute('data-theme', 'dark');
        try { localStorage.setItem('ncf_theme', dark ? 'light' : 'dark'); } catch (e) {}
      });
    });
  }

  /* ---------- reading progress (article pages) ---------- */
  function initProgress() {
    const bar = document.getElementById('read-progress');
    if (!bar) return;
    const update = () => {
      const h = document.documentElement;
      const max = h.scrollHeight - h.clientHeight;
      bar.style.width = (max > 0 ? (h.scrollTop / max) * 100 : 0) + '%';
    };
    addEventListener('scroll', update, { passive: true });
    update();
  }

  /* ---------- copy link (article share row) ---------- */
  function initCopy() {
    $$('[data-copy]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const orig = btn.textContent;
        try {
          await navigator.clipboard.writeText(btn.getAttribute('data-copy'));
          btn.textContent = '✓';
        } catch (e) { btn.textContent = '✗'; }
        setTimeout(() => { btn.textContent = orig; }, 1600);
      });
    });
  }

  /* ---------- page transitions: a quick "page turn" on internal nav ------- */
  function initPageTransitions() {
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
    // a restored (back/forward) page must never stay faded out
    addEventListener('pageshow', () => document.documentElement.classList.remove('is-leaving'));
    if (reduce) return;
    document.addEventListener('click', (e) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const a = e.target.closest('a');
      if (!a) return;
      const href = a.getAttribute('href');
      if (!href || a.target || a.hasAttribute('download')) return;
      if (/^(#|mailto:|tel:|javascript:)/i.test(href)) return;
      let url;
      try { url = new URL(a.href); } catch (err) { return; }
      if (url.origin !== location.origin) return;            // external → let it go
      if (url.pathname === location.pathname && url.hash) return; // same-page anchor
      e.preventDefault();
      document.documentElement.classList.add('is-leaving');
      setTimeout(() => { location.href = a.href; }, 270);
    });
  }

  /* ---------- section headers: draw the rule when scrolled into view ------ */
  function initSectionRules() {
    const heads = $$('.section-header');
    if (!heads.length || !('IntersectionObserver' in window)) {
      heads.forEach((h) => h.classList.add('ruled'));
      return;
    }
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => {
        if (en.isIntersecting) { en.target.classList.add('ruled'); io.unobserve(en.target); }
      });
    }, { threshold: 0.6 });
    heads.forEach((h) => io.observe(h));
  }

  /* ---------- boot ---------- */
  function init(opts = {}) {
    initMenu();
    initForms();
    initYear();
    initTheme();
    initProgress();
    initCopy();
    initPageTransitions();
    initSectionRules();
    if (opts.ticker) buildTicker(opts.ticker);
    if (opts.market !== false) {
      loadMarket(opts).catch(() => {});
      const mins = opts.refresh || 5;
      setInterval(() => loadMarket(opts).catch(() => {}), mins * 60 * 1000);
    } else {
      /* server-rendered pages (macro, dashboard) — no live loader, but the
         ticker still needs this morning's snapshot */
      paintSnapshotAll().catch(() => {});
    }
  }
  NCF.init = init;

  document.addEventListener('DOMContentLoaded', () => {
    if (window.NCF_AUTO) NCF.init(window.NCF_AUTO);
  });

  /* ==========================================================
     MOUSE EFFECTS — cursor, nav pill, 3D card tilt
     ========================================================== */
  document.addEventListener('DOMContentLoaded', () => {
    if (!window.matchMedia('(hover: hover)').matches) return;

    /* ---- Custom cursor ---- */
    const dot  = document.querySelector('.cursor-dot');
    const ring = document.querySelector('.cursor-ring');
    if (dot && ring) {
      let mx = 0, my = 0, rx = 0, ry = 0, live = false;

      addEventListener('mousemove', e => {
        mx = e.clientX; my = e.clientY;
        if (!live) {
          /* first move: drop both nodes straight onto the pointer, then reveal
             — no slide-in from a parked position */
          live = true;
          rx = mx; ry = my;
          ring.style.transform = `translate(${rx}px,${ry}px) translate(-50%,-50%)`;
          document.body.classList.add('cursor-live');
          requestAnimationFrame(function loop() {
            rx += (mx - rx) * 0.16;
            ry += (my - ry) * 0.16;
            ring.style.transform = `translate(${rx}px,${ry}px) translate(-50%,-50%)`;
            requestAnimationFrame(loop);
          });
        }
        dot.style.transform = `translate(${mx}px,${my}px) translate(-50%,-50%)`;
      });

      /* read cursor on articles / content */
      $$('article, .acard, .art-row, .card, .lead, [data-read]').forEach(el => {
        el.addEventListener('mouseenter', () => document.body.classList.add('hovering-read'));
        el.addEventListener('mouseleave', () => document.body.classList.remove('hovering-read'));
      });

      /* link cursor on interactive elements */
      $$('a, button, input, .subscribe, .menu-toggle, .filter-btn').forEach(el => {
        el.addEventListener('mouseenter', () => {
          document.body.classList.remove('hovering-read');
          document.body.classList.add('hovering-link');
        });
        el.addEventListener('mouseleave', () => document.body.classList.remove('hovering-link'));
      });
    }

    /* ---- Gliding nav pill ---- */
    const navLinks = document.querySelector('.nav-links');
    if (navLinks) {
      let pill = navLinks.querySelector('.nav-pill');
      if (!pill) {
        pill = document.createElement('span');
        pill.className = 'nav-pill';
        navLinks.prepend(pill);
      }
      const anchors = Array.from(navLinks.querySelectorAll('a'));
      const activeA = navLinks.querySelector('a.active') || anchors[0];

      function movePill(target, hot) {
        const nr = navLinks.getBoundingClientRect();
        const r  = target.getBoundingClientRect();
        pill.style.left  = (r.left - nr.left) + 'px';
        pill.style.width = r.width + 'px';
        pill.classList.toggle('hot', hot);   /* colour lives in CSS, not inline */
      }

      if (activeA) setTimeout(() => movePill(activeA, false), 60);

      anchors.forEach(a => {
        a.addEventListener('mouseenter', () => movePill(a, a !== activeA));
      });
      navLinks.addEventListener('mouseleave', () => {
        if (activeA) movePill(activeA, false);
      });
      window.addEventListener('resize', () => { if (activeA) movePill(activeA, false); });
    }

    /* ---- 3D tilt on cards ---- */
    function bindTilt() {
      $$('.card, .acard, .lead-aside, .stat').forEach(card => {
        card.style.transition = 'border-color .3s, box-shadow .3s, transform .12s ease-out';
        card.style.transformStyle = 'preserve-3d';
        card.addEventListener('mousemove', e => {
          const r  = card.getBoundingClientRect();
          const px = (e.clientX - r.left) / r.width;
          const py = (e.clientY - r.top)  / r.height;
          card.style.transform = `perspective(1100px) rotateX(${(0.5-py)*7}deg) rotateY(${(px-0.5)*7}deg) translateZ(3px)`;
          card.style.setProperty('--gx', px * 100 + '%');
          card.style.setProperty('--gy', py * 100 + '%');
        });
        card.addEventListener('mouseleave', () => { card.style.transform = ''; });
      });
    }
    bindTilt();

    /* ---- Scroll reveal ---- */
    const io = new IntersectionObserver(entries => {
      entries.forEach((en, i) => {
        if (en.isIntersecting) {
          en.target.style.transition = `opacity .75s ${i * 0.05}s cubic-bezier(.2,.7,.2,1), transform .75s ${i * 0.05}s cubic-bezier(.2,.7,.2,1)`;
          en.target.style.opacity  = '1';
          en.target.style.transform = 'translateY(0)';
          io.unobserve(en.target);
        }
      });
    }, { threshold: 0.10 });

    $$('.section, .lead, .stat, .acard, .art-row').forEach(el => {
      el.style.opacity  = '0';
      el.style.transform = 'translateY(20px)';
      io.observe(el);
    });
  });

})();

/* ============================================================
   Easter egg · Konami code (↑↑↓↓←→←→BA)
   Five seconds of digital rain over whatever page you're on,
   then back to the broadsheet like nothing happened.
   ============================================================ */
(function () {
  'use strict';
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  var SEQ = ['ArrowUp','ArrowUp','ArrowDown','ArrowDown','ArrowLeft','ArrowRight','ArrowLeft','ArrowRight','b','a'];
  var pos = 0, active = false;

  document.addEventListener('keydown', function (e) {
    if (active) return;
    var tag = (e.target && e.target.tagName) || '';
    if (tag === 'INPUT' || tag === 'TEXTAREA') return;
    var k = e.key.length === 1 ? e.key.toLowerCase() : e.key;
    pos = (k === SEQ[pos]) ? pos + 1 : (k === SEQ[0] ? 1 : 0);
    if (pos === SEQ.length) { pos = 0; trigger(); }
  });

  function trigger() {
    active = true;
    var overlay = document.createElement('div');
    overlay.setAttribute('aria-hidden', 'true');
    overlay.style.cssText = 'position:fixed;inset:0;z-index:99999;background:#000;opacity:0;transition:opacity .6s ease;cursor:pointer;';
    var canvas = document.createElement('canvas');
    canvas.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;';
    var msg = document.createElement('div');
    msg.textContent = 'wake up, trader — the market has you';
    msg.style.cssText = 'position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);' +
      'font-family:"IBM Plex Mono",monospace;font-size:clamp(13px,2.4vw,19px);letter-spacing:.18em;' +
      'text-transform:uppercase;color:rgba(190,255,210,.9);text-shadow:0 0 18px rgba(60,220,110,.6);' +
      'opacity:0;transition:opacity 1.2s ease .8s;white-space:nowrap;';
    overlay.appendChild(canvas);
    overlay.appendChild(msg);
    document.body.appendChild(overlay);

    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    var ctx = canvas.getContext('2d');
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    var GLYPHS = 'アイウエオカキクケコサシスセソタチツテト0123456789$€₺₿%Δ↑↓';
    var FONT = 16, cols = Math.ceil(canvas.width / FONT);
    var drops = [];
    for (var i = 0; i < cols; i++) drops.push(Math.random() * -canvas.height / FONT);

    var raf, last = 0;
    function frame(t) {
      raf = requestAnimationFrame(frame);
      if (t - last < 50) return;
      last = t;
      ctx.fillStyle = 'rgba(0,0,0,0.08)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.font = FONT + 'px "IBM Plex Mono", monospace';
      for (var i = 0; i < cols; i++) {
        var y = drops[i] * FONT;
        ctx.fillStyle = Math.random() < 0.02 ? '#C98A2B' : 'rgba(60,220,110,0.85)';
        ctx.fillText(GLYPHS.charAt(Math.floor(Math.random() * GLYPHS.length)), i * FONT, y);
        if (y > canvas.height && Math.random() > 0.975) drops[i] = 0;
        else drops[i]++;
      }
    }
    raf = requestAnimationFrame(frame);
    requestAnimationFrame(function () { overlay.style.opacity = '1'; msg.style.opacity = '1'; });

    function dismiss() {
      overlay.style.opacity = '0';
      setTimeout(function () {
        cancelAnimationFrame(raf);
        overlay.remove();
        active = false;
      }, 650);
    }
    overlay.addEventListener('click', dismiss);
    setTimeout(dismiss, 5200);
  }
})();

/* ============================================================
   Finance Engineering · white-rabbit door
   Clicking the FE tab first types "follow the white rabbit…"
   on black, then walks through. Plain left-clicks only —
   cmd/ctrl/middle clicks and reduced-motion go straight in.
   Click or Escape skips the theatre.
   ============================================================ */
(function () {
  'use strict';
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  var busy = false;

  document.addEventListener('click', function (e) {
    if (busy) return;
    var a = e.target && e.target.closest && e.target.closest('.nav a[href$="finance-engineering.html"]');
    if (!a) return;
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
    var href = a.getAttribute('href');
    if (location.pathname === href) return;        // already there
    e.preventDefault();
    busy = true;

    // warm the cache while the line types out
    var pf = document.createElement('link');
    pf.rel = 'prefetch'; pf.href = href;
    document.head.appendChild(pf);

    var overlay = document.createElement('div');
    overlay.setAttribute('aria-hidden', 'true');
    overlay.style.cssText = 'position:fixed;inset:0;z-index:99999;background:#000;opacity:0;' +
      'transition:opacity .35s ease;display:flex;align-items:center;justify-content:center;cursor:pointer;';
    var line = document.createElement('div');
    line.style.cssText = 'font-family:"IBM Plex Mono",monospace;font-size:clamp(14px,2.6vw,20px);' +
      'letter-spacing:.14em;color:rgba(80,255,140,.85);text-shadow:0 0 14px rgba(60,220,110,.45);white-space:pre;';
    overlay.appendChild(line);
    document.body.appendChild(overlay);
    requestAnimationFrame(function () { overlay.style.opacity = '1'; });

    var TEXT = 'follow the white rabbit...';
    var i = 0, done = false;
    var typer = setInterval(function () {
      i++;
      line.textContent = '> ' + TEXT.slice(0, i) + (i % 2 ? '█' : ' ');
      if (i >= TEXT.length) {
        clearInterval(typer);
        line.textContent = '> ' + TEXT;
        setTimeout(go, 450);
      }
    }, 38);

    function go() {
      if (done) return;
      done = true;
      clearInterval(typer);
      window.location.href = href;
    }
    overlay.addEventListener('click', go);
    document.addEventListener('keydown', function esc(ev) {
      if (ev.key === 'Escape') { document.removeEventListener('keydown', esc); go(); }
    });
    setTimeout(go, 3500);                          // hard failsafe
  });
})();

/* ============================================================
   Finance Engineering hub · machine-room rain
   A whisper of falling glyphs behind the manifesto — paper-ink
   glyphs with the section's oxide accent, not film green. Reads
   the live CSS vars so After Hours dark mode adapts. Pauses when
   the hero scrolls away or the tab hides; gone under
   reduced-motion (CSS hides the canvas, JS never starts).
   ============================================================ */
(function () {
  'use strict';
  var head = document.querySelector('.fe-page .fe-head');
  if (!head) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  // Two registers: full Matrix inside the machine room (body.fe-matrix),
  // whisper-quiet paper-ink rain anywhere else.
  var MX = document.body.classList.contains('fe-matrix');

  var canvas = document.createElement('canvas');
  canvas.className = 'fe-rain';
  canvas.setAttribute('aria-hidden', 'true');
  head.prepend(canvas);
  var ctx = canvas.getContext('2d');

  var GLYPHS = MX ? 'アイウエオカキクケコサシスセソタチツテト01$€₺₿%Δ↑↓' : '01$€₺₿%Δ↑↓·';
  var FONT = 15, TRAIL = MX ? 13 : 9, SPACING = MX ? 1.5 : 2;
  var AMAX = MX ? 0.5 : 0.14, STEP = MX ? 80 : 110;
  var cols = 0, drops = [];
  var inkRGB = MX ? '59,245,127' : '25,21,18';
  var spark = MX ? '#E3A63D' : '#B0442B';

  function palette() {
    if (MX) return;                                // machine room is phosphor, fixed
    var cs = getComputedStyle(head);
    var ink = cs.getPropertyValue('--text').trim();
    var m = ink.match(/^#([0-9a-f]{6})$/i);
    if (m) {
      inkRGB = parseInt(m[1].slice(0,2),16) + ',' + parseInt(m[1].slice(2,4),16) + ',' + parseInt(m[1].slice(4,6),16);
    }
    spark = cs.getPropertyValue('--fe-oxide').trim() || spark;
  }

  function resize() {
    canvas.width = head.clientWidth;
    canvas.height = head.clientHeight;
    cols = Math.ceil(canvas.width / (FONT * SPACING));
    drops = [];
    for (var i = 0; i < cols; i++) drops.push(Math.random() * -2 * canvas.height / FONT);
    palette();
  }
  resize();
  window.addEventListener('resize', resize);

  var visible = !document.hidden, onscreen = true;
  document.addEventListener('visibilitychange', function () { visible = !document.hidden; });
  new IntersectionObserver(function (entries) { onscreen = entries[0].isIntersecting; },
    { threshold: 0 }).observe(head);
  new MutationObserver(palette).observe(document.documentElement, { attributes: true });

  var last = 0;
  function frame(t) {
    requestAnimationFrame(frame);
    if (!visible || !onscreen) return;
    if (t - last < STEP) return;
    last = t;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.font = FONT + 'px "IBM Plex Mono", monospace';
    for (var i = 0; i < cols; i++) {
      var x = i * FONT * SPACING;
      for (var j = 0; j < TRAIL; j++) {
        var y = (drops[i] - j) * FONT;
        if (y < 0 || y > canvas.height + FONT) continue;
        var a = (1 - j / TRAIL) * AMAX;
        if (j === 0) {
          // head glyph: amber = the human spark; bright white-green = phosphor flare
          ctx.fillStyle = Math.random() < 0.03 ? spark
                        : (MX && Math.random() < 0.2) ? 'rgba(185,255,204,0.95)'
                        : (MX ? 'rgba(59,245,127,0.9)' : 'rgba(' + inkRGB + ',' + AMAX + ')');
        } else {
          ctx.fillStyle = 'rgba(' + inkRGB + ',' + a.toFixed(3) + ')';
        }
        ctx.fillText(GLYPHS.charAt((i * 7 + j * 3 + (drops[i] | 0)) % GLYPHS.length), x, y);
      }
      drops[i] += 1;
      if ((drops[i] - TRAIL) * FONT > canvas.height && Math.random() > 0.96) {
        drops[i] = Math.random() * -6;
      }
    }
  }
  requestAnimationFrame(frame);
})();
