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

  /* ---------- newsletter (graceful no-backend stub) ---------- */
  function initForms() {
    $$('form[data-newsletter]').forEach((form) => {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        const btn = form.querySelector('button');
        const input = form.querySelector('input');
        if (!btn) return;
        const orig = btn.textContent;
        btn.textContent = '✓ Subscribed';
        btn.disabled = true;
        if (input) input.value = '';
        setTimeout(() => { btn.textContent = orig; btn.disabled = false; }, 3000);
      });
    });
  }

  /* ---------- year stamp ---------- */
  function initYear() {
    $$('[data-year]').forEach((el) => { el.textContent = new Date().getFullYear(); });
  }

  /* ---------- boot ---------- */
  function init(opts = {}) {
    initMenu();
    initForms();
    initYear();
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
})();
