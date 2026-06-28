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

  /* ---------- last-good cache (localStorage) ---------- */
  const CACHE_KEY = 'ncf-market-cache';
  function readCache() {
    try { return JSON.parse(localStorage.getItem(CACHE_KEY)) || {}; }
    catch (e) { return {}; }
  }
  function writeCache(obj) {
    try { localStorage.setItem(CACHE_KEY, JSON.stringify(obj)); } catch (e) {}
  }

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
    const cache = readCache();
    const updated = {};

    const apply = (key, price, pct, extra) => {
      if (price != null) {
        cache[key] = { price, pct, t: Date.now() };
        paint(key, price, pct, extra);
        updated[key] = true;
      } else if (cache[key]) {
        paint(key, cache[key].price, cache[key].pct, extra);
      }
    };

    /* crypto first (fast + reliable) */
    const cg = await fetchCrypto(['bitcoin', 'ethereum']);
    if (cg) {
      if (cg.bitcoin)  apply('btc', cg.bitcoin.usd, cg.bitcoin.usd_24h_change);
      if (cg.ethereum) apply('eth', cg.ethereum.usd, cg.ethereum.usd_24h_change);
    } else {
      apply('btc'); apply('eth');
    }

    /* Fear & Greed */
    const fg = await fetchFearGreed();
    if (fg) {
      cache.fg = { value: fg.value, label: fg.label, t: Date.now() };
      $$('[data-px="fg"]').forEach((el) => { el.textContent = fg.value; });
      $$('[data-chg="fg"]').forEach((el) => {
        el.textContent = fg.label;
        el.classList.remove('up', 'dn', 'neu');
        el.classList.add(fg.value > 55 ? 'up' : fg.value < 35 ? 'dn' : 'neu');
      });
    } else if (cache.fg) {
      $$('[data-px="fg"]').forEach((el) => { el.textContent = cache.fg.value; });
      $$('[data-chg="fg"]').forEach((el) => { el.textContent = cache.fg.label; });
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
        cache[key].closes = d.closes; // keep for sparklines
      } else {
        apply(key);
      }
    }

    writeCache(cache);
    if (typeof opts.onDone === 'function') opts.onDone(cache, updated);
    return cache;
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
      let mx = innerWidth / 2, my = innerHeight / 2;
      let rx = mx, ry = my;

      addEventListener('mousemove', e => {
        mx = e.clientX; my = e.clientY;
        dot.style.transform = `translate(${mx}px,${my}px) translate(-50%,-50%)`;
      });

      (function loop() {
        rx += (mx - rx) * 0.16;
        ry += (my - ry) * 0.16;
        ring.style.transform = `translate(${rx}px,${ry}px) translate(-50%,-50%)`;
        requestAnimationFrame(loop);
      })();

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
        pill.style.background = hot ? 'var(--red)' : 'var(--text)';
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
