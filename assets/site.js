/* =============================================================
   NoCashFlow · Shared site JS
   - Live ticker with CoinGecko fallback
   - Mobile menu toggle
   - Newsletter form handler (Substack/Mailerlite swap target)
   ============================================================= */

(function () {
  'use strict';

  // --- Mobile menu toggle ---
  const toggle = document.querySelector('.menu-toggle');
  const links = document.querySelector('.nav-links');
  if (toggle && links) {
    toggle.addEventListener('click', () => links.classList.toggle('open'));
  }

  // --- Ticker: pause on hover ---
  const ticker = document.querySelector('.ticker');
  const track = document.querySelector('.ticker-track');
  if (ticker && track) {
    ticker.addEventListener('mouseenter', () => track.style.animationPlayState = 'paused');
    ticker.addEventListener('mouseleave', () => track.style.animationPlayState = 'running');
  }

  // --- Live price fetch (CoinGecko, public API, no key needed) ---
  // Only runs if the page has data-ticker-live attribute.
  // Gracefully falls back to static numbers if blocked or offline.
  const liveHost = document.querySelector('[data-ticker-live]');
  if (liveHost) {
    fetchLivePrices().catch(() => { /* silent: keep static fallback values */ });
  }

  async function fetchLivePrices() {
    const url = 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true';
    const res = await fetch(url, { cache: 'no-store' });
    if (!res.ok) return;
    const data = await res.json();
    updateTick('BTC', data.bitcoin);
    updateTick('ETH', data.ethereum);
  }

  function updateTick(sym, coin) {
    if (!coin) return;
    const ticks = document.querySelectorAll(`.tick[data-sym="${sym}"]`);
    ticks.forEach(t => {
      const px = t.querySelector('.px');
      const chg = t.querySelector('.chg');
      const price = coin.usd;
      const change = coin.usd_24h_change;
      if (px) px.textContent = '$' + Number(price).toLocaleString('en-US', { maximumFractionDigits: 0 });
      if (chg) {
        const sign = change >= 0 ? '+' : '';
        chg.textContent = sign + change.toFixed(2) + '%';
        chg.className = 'chg ' + (change >= 0 ? 'up' : 'dn');
      }
    });
  }

  // --- Newsletter form (placeholder until Mailerlite/Substack wired) ---
  const forms = document.querySelectorAll('.newsletter-form');
  forms.forEach(f => {
    f.addEventListener('submit', e => {
      e.preventDefault();
      const input = f.querySelector('input[type=email]');
      const btn = f.querySelector('button');
      if (!input || !input.value) return;
      if (btn) {
        btn.textContent = 'Subscribed ✓';
        btn.style.background = 'var(--green)';
        btn.style.borderColor = 'var(--green)';
      }
      input.disabled = true;
      // TODO: POST to Mailerlite or Substack endpoint
    });
  });

  // --- Mark nav links as active based on current pathname ---
  const path = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-links a').forEach(a => {
    const href = a.getAttribute('href');
    if (href === path || (path === '' && href === 'index.html') || (path === '/' && href === 'index.html')) {
      a.classList.add('active');
    }
  });
})();
