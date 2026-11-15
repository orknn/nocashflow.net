/* ==========================================================================
   NoCashFlow — "Liquid" behaviour layer
   Source of truth: demos/d-liquid/index.html (approved 2026-11-15).

   Purely presentational. Data refresh + forms stay in app.js; this file
   never fetches. Every module is opt-in by markup and no-ops when its
   element is absent, so one script serves every page.

   Markup hooks
     .rv                 reveal container (adds .in when scrolled into view)
     [data-rv-now]       reveal on load instead of on scroll (hero)
     [data-scr]          digits scramble into place when revealed
     .bar i[data-w]      odds bar width (%) set on reveal
     .gauge[data-value]  0–100 needle + arc on reveal
     .nav                hides on scroll down
     .progress           scroll progress line
     [data-lq-clock]     live UTC clock
     .stage + canvas[data-curve]   yield-curve terrain; data-curve = JSON [{l,v}]
     .strip              mouse drag-to-scroll
     [data-magnet]       magnetic hover
     [data-cur] / [data-cur-label="Read"]   cursor states (cursor is injected)

   ?static           settle everything immediately (screenshots / QA)
   reduced motion    no cursor, no magnet, no scramble, frozen canvas
   ========================================================================== */
(function () {
  'use strict';
  var d = document, root = d.documentElement;
  var $ = function (s, r) { return (r || d).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || d).querySelectorAll(s)); };
  var RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var STATIC = /[?&]static\b/.test(location.search);
  if (STATIC) root.classList.add('lq-static');

  /* ── number scramble ─────────────────────────────────────────────────── */
  function scramble(el) {
    if (RM || STATIC || el._lqs) return;
    el._lqs = 1;
    var fin = el.textContent, t0 = performance.now(), dur = 900 + Math.random() * 500;
    if (!/\d/.test(fin)) return;
    (function f(t) {
      var p = Math.min(1, (t - t0) / dur), keep = Math.floor(p * fin.length);
      el.textContent = fin.split('').map(function (c, i) {
        return i < keep || !/\d/.test(c) ? c : Math.floor(Math.random() * 10);
      }).join('');
      if (p < 1) requestAnimationFrame(f); else el.textContent = fin;
    })(t0);
  }

  /* ── reveal ──────────────────────────────────────────────────────────── */
  function reveal(el) {
    el.classList.add('in');
    $$('[data-scr]', el).forEach(scramble);
    $$('.bar i[data-w]', el).forEach(function (b) { b.style.width = b.getAttribute('data-w') + '%'; });
    $$('.gauge[data-value]', el).concat(el.matches('.gauge[data-value]') ? [el] : []).forEach(function (g) {
      var v = Math.max(0, Math.min(100, +g.getAttribute('data-value') || 0));
      var n = $('.needle', g), a = $('.arc-val', g);
      if (n) n.style.transform = 'rotate(' + (-90 + v * 1.8) + 'deg)';
      if (a) a.style.strokeDasharray = v + ' 100';
    });
  }
  // gauges ship at their real value (no-JS); with motion on, start empty and sweep in
  if (!RM && !STATIC) $$('.gauge .arc-val').forEach(function (a) { a.style.strokeDasharray = '0 100'; });
  var rvs = $$('.rv');
  if (STATIC || !('IntersectionObserver' in window)) {
    rvs.forEach(reveal);
  } else {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { reveal(e.target); io.unobserve(e.target); } });
    }, { threshold: 0.18 });
    rvs.forEach(function (el) {
      if (el.hasAttribute('data-rv-now')) requestAnimationFrame(function () { reveal(el); });
      else io.observe(el);
    });
  }

  /* ── clock (real UTC) ────────────────────────────────────────────────── */
  var clocks = $$('[data-lq-clock]');
  if (clocks.length) {
    var tick = function () { var s = new Date().toISOString().slice(11, 19) + ' UTC'; clocks.forEach(function (c) { c.textContent = s; }); };
    tick(); setInterval(tick, 1000);
  }

  /* ── scroll: progress, nav hide, stage growth ────────────────────────── */
  var prog = $('.progress'), nav = $('.nav'), stages = $$('.stage'), ly = 0;
  function onScroll() {
    var y = window.scrollY, h = root.scrollHeight - innerHeight;
    if (prog) prog.style.transform = 'scaleX(' + (h > 0 ? y / h : 0) + ')';
    if (nav && !nav.classList.contains('open')) nav.classList.toggle('hide', y > ly && y > 300);
    ly = y;
    stages.forEach(function (s) {
      var r = s.getBoundingClientRect();
      var p = Math.max(0, Math.min(1, (innerHeight - r.top) / (innerHeight * 0.85)));
      s.style.setProperty('--p', STATIC ? 1 : p.toFixed(3));
    });
  }
  addEventListener('scroll', onScroll, { passive: true }); onScroll();

  /* ── cursor + magnets (fine pointers only) ───────────────────────────── */
  if (matchMedia('(hover: hover) and (pointer: fine)').matches && !RM && !STATIC) {
    var cur = d.createElement('div'); cur.className = 'cur'; cur.setAttribute('aria-hidden', 'true');
    cur.innerHTML = '<span></span>'; d.body.appendChild(cur); root.classList.add('has-cur');
    var lab = $('span', cur), x = innerWidth / 2, y = innerHeight / 2, cx = x, cy = y;
    addEventListener('mousemove', function (e) { x = e.clientX; y = e.clientY; });
    (function f() { cx += (x - cx) * 0.2; cy += (y - cy) * 0.2; cur.style.transform = 'translate(' + cx + 'px,' + cy + 'px)'; requestAnimationFrame(f); })();
    d.addEventListener('mouseover', function (e) {
      var t = e.target.closest ? e.target : e.target.parentElement;
      var l = t && t.closest('[data-cur-label]'), k = t && t.closest('[data-cur],a,button,input,label');
      cur.classList.toggle('label', !!l); cur.classList.toggle('link', !l && !!k);
      if (l) lab.textContent = l.getAttribute('data-cur-label');
    });
    $$('[data-magnet]').forEach(function (b) {
      b.addEventListener('mousemove', function (e) {
        var r = b.getBoundingClientRect();
        b.style.transition = 'transform .1s';
        b.style.transform = 'translate(' + (e.clientX - r.left - r.width / 2) * 0.3 + 'px,' + (e.clientY - r.top - r.height / 2) * 0.4 + 'px)';
      });
      b.addEventListener('mouseleave', function () { b.style.transition = 'transform .7s cubic-bezier(.34,1.56,.64,1)'; b.style.transform = ''; });
    });
  }

  /* ── full-screen menu (< 1100px) ─────────────────────────────────────── */
  var mbtn = $('.nav-menu'), menu = $('#lq-menu');
  if (mbtn && menu) {
    var setMenu = function (open) {
      menu.hidden = !open;
      mbtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      mbtn.textContent = mbtn.getAttribute(open ? 'data-close' : 'data-open');
      root.classList.toggle('lq-menu-open', open);
      if (nav) { nav.classList.toggle('open', open); if (open) nav.classList.remove('hide'); }
      if (open) { var first = $('a', menu); if (first) first.focus({ preventScroll: true }); } else mbtn.focus({ preventScroll: true });
    };
    mbtn.addEventListener('click', function () { setMenu(menu.hidden); });
    d.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !menu.hidden) setMenu(false); });
    $$('a', menu).forEach(function (a) { a.addEventListener('click', function () { setMenu(false); }); });
    matchMedia('(min-width: 1101px)').addEventListener('change', function (e) { if (e.matches && !menu.hidden) setMenu(false); });
  }

  /* ── drag-to-scroll strips (mouse only; touch scrolls natively) ──────── */
  $$('.strip').forEach(function (s) {
    var down = 0, sx = 0, sl = 0;
    s.addEventListener('pointerdown', function (e) { if (e.pointerType !== 'mouse') return; down = 1; sx = e.clientX; sl = s.scrollLeft; s.classList.add('drag'); s.setPointerCapture(e.pointerId); });
    s.addEventListener('pointermove', function (e) { if (down) s.scrollLeft = sl - (e.clientX - sx); });
    ['pointerup', 'pointercancel'].forEach(function (ev) { s.addEventListener(ev, function () { down = 0; s.classList.remove('drag'); }); });
  });

  /* ── stage: real yield curve drawn as a living terrain ───────────────── */
  $$('.stage canvas[data-curve]').forEach(function (cv) {
    var pts;
    try { pts = JSON.parse(cv.getAttribute('data-curve')); } catch (e) { return; }
    if (!pts || pts.length < 2) return;
    var ctx = cv.getContext('2d'), stage = cv.closest('.stage');
    var C = pts.map(function (p) { return +p.v; }), T = pts.map(function (p) { return p.l; }), n = C.length - 1;
    var lo = Math.min.apply(null, C), hi = Math.max.apply(null, C), span = (hi - lo) || 1;
    function yAt(t) { // Catmull-Rom through the real tenor points
      var f = Math.min(n - 1e-6, Math.max(0, t * n)), i = Math.floor(f), u = f - i;
      var a = C[Math.max(0, i - 1)], b = C[i], c = C[i + 1], dd = C[Math.min(n, i + 2)];
      return 0.5 * (2 * b + (c - a) * u + (2 * a - 5 * b + 4 * c - dd) * u * u + (3 * b - a - 3 * c + dd) * u * u * u);
    }
    function N(t) { return (yAt(t) - lo) / span; }
    var mood = (getComputedStyle(stage).getPropertyValue('--mood') || '#6FB2FF').trim();
    var mc = /^#[0-9a-f]{6}$/i.test(mood) ? [1, 3, 5].map(function (i) { return parseInt(mood.slice(i, i + 2), 16); }) : [111, 178, 255];
    var W = 0, H = 0, mx = 0.5, my = 0.5, hov = 0, hovT = 0, vis = true, frozen = RM || STATIC;
    function size() { var dpr = Math.min(2, devicePixelRatio || 1); W = cv.clientWidth; H = cv.clientHeight; cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); if (frozen) draw(3000); }
    if ('ResizeObserver' in window) new ResizeObserver(size).observe(cv); else addEventListener('resize', size);
    if (!frozen) {
      stage.addEventListener('mousemove', function (e) { var r = cv.getBoundingClientRect(); mx = (e.clientX - r.left) / r.width; my = (e.clientY - r.top) / r.height; hovT = 1; });
      stage.addEventListener('mouseleave', function () { hovT = 0; });
    }
    if ('IntersectionObserver' in window) new IntersectionObserver(function (e) { vis = e[0].isIntersecting; }).observe(cv);
    var LAY = 34, STEP = 110, parts = [];
    for (var q = 0; q < 26; q++) parts.push({ t: Math.random(), s: 0.0006 + Math.random() * 0.0012 });
    var monoFont = '"Geist Mono",ui-monospace,monospace';

    function draw(ms) {
      var t = frozen ? 3 : ms / 1000; hov += (hovT - hov) * 0.06;
      ctx.clearRect(0, 0, W, H);
      var small = W < 700, padX = W * (small ? 0.14 : 0.09), frontY = H * (small ? 0.74 : 0.76), depthH = H * 0.44, ampF = H * (small ? 0.2 : 0.27);
      var dm = Math.max(0, Math.min(1, (frontY - my * H) / depthH));
      function geom(dd) { return { l: padX + dd * W * 0.13, r: W - padX - dd * W * 0.13, by: frontY - dd * depthH, amp: ampF * (1 - dd * 0.5) }; }
      function pt(i, s) {
        var dd = i / (LAY - 1), g = geom(dd);
        var wave = Math.sin(s * 5.2 + t * 0.7 + i * 0.33) * 0.075 * dd + Math.sin(s * 11 - t * 0.45 + i * 0.9) * 0.03 * dd;
        var bump = Math.exp(-Math.pow(s - mx, 2) / 0.006) * Math.exp(-Math.pow(dd - dm, 2) / 0.03) * 0.2 * hov;
        return [g.l + (g.r - g.l) * s, g.by - (N(s) + wave + bump) * g.amp];
      }
      function path(i) { ctx.beginPath(); for (var k = 0; k <= STEP; k++) { var p = pt(i, k / STEP); if (k) ctx.lineTo(p[0], p[1]); else ctx.moveTo(p[0], p[1]); } }
      for (var i = LAY - 1; i >= 0; i--) {
        var dd = i / (LAY - 1), g = geom(dd);
        path(i); ctx.lineTo(g.r, H + 4); ctx.lineTo(g.l, H + 4); ctx.closePath();
        ctx.fillStyle = 'rgba(11,12,15,' + (i ? 0.86 : 0.55) + ')'; ctx.fill();
        path(i);
        if (i) { ctx.strokeStyle = 'rgba(' + mc[0] + ',' + mc[1] + ',' + mc[2] + ',' + (0.07 + Math.pow(1 - dd, 1.6) * 0.5) + ')'; ctx.lineWidth = 1; ctx.stroke(); }
        else { ctx.shadowColor = '#FF4B26'; ctx.shadowBlur = 22; ctx.strokeStyle = '#FF4B26'; ctx.lineWidth = 2.4; ctx.stroke(); ctx.shadowBlur = 0; }
      }
      parts.forEach(function (p) {
        if (!frozen) p.t = (p.t + p.s) % 1;
        var w = pt(0, p.t); ctx.fillStyle = 'rgba(236,234,227,' + (0.25 + Math.sin(p.t * Math.PI) * 0.7) + ')';
        ctx.beginPath(); ctx.arc(w[0], w[1], 1.6, 0, 7); ctx.fill();
      });
      ctx.textAlign = 'center';
      C.forEach(function (v, i) {
        var s = i / n, w = pt(0, s), near = hov * Math.exp(-Math.pow(s - mx, 2) / 0.004);
        ctx.fillStyle = '#0B0C0F'; ctx.strokeStyle = '#ECEAE3'; ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.arc(w[0], w[1], 4 + near * 4, 0, 7); ctx.fill(); ctx.stroke();
        if (small && i % 2) return;
        ctx.font = '500 ' + (small ? 11 : 13 + near * 5) + 'px ' + monoFont; ctx.fillStyle = '#ECEAE3';
        ctx.fillText(v.toFixed(2) + '%', w[0], w[1] - 16 - near * 8);
        ctx.font = '400 10.5px ' + monoFont; ctx.fillStyle = 'rgba(236,234,227,.5)';
        ctx.fillText(T[i], w[0], w[1] + 24);
      });
    }
    size();
    if (frozen) { (d.fonts && d.fonts.ready ? d.fonts.ready : Promise.resolve()).then(function () { draw(3000); }); return; }
    (function loop(ms) { requestAnimationFrame(loop); if (vis) draw(ms || 0); })();
  });
})();
