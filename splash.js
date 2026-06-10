/* ============================================================
   NoCashFlow · Language splash gate logic (index only)
   - Cycles "Welcome" through 11 languages (TR first, EN last)
   - Two choice boxes write localStorage 'ncf_lang' and route
   - prefers-reduced-motion: static, no cycling
   The pre-paint decision (show / skip / redirect) is made by the
   inline <head> script; this file only animates + handles clicks.
   ============================================================ */
(function () {
  'use strict';

  var splash = document.getElementById('ncf-splash');
  if (!splash) return;

  var wordEl = splash.querySelector('.ncf-splash-word');

  /* TR first ... EN last (per spec). dir flags RTL scripts. */
  var WORDS = [
    { t: 'Hoş geldiniz',        dir: 'ltr' }, // Türkçe
    { t: 'Bienvenido',          dir: 'ltr' }, // İspanyolca
    { t: '欢迎',                 dir: 'ltr' }, // Çince
    { t: 'स्वागत है',             dir: 'ltr' }, // Hintçe
    { t: 'أهلاً وسهلاً',           dir: 'rtl' }, // Arapça
    { t: 'Bem-vindo',           dir: 'ltr' }, // Portekizce
    { t: 'Добро пожаловать',    dir: 'ltr' }, // Rusça
    { t: 'ようこそ',             dir: 'ltr' }, // Japonca
    { t: 'Bienvenue',           dir: 'ltr' }, // Fransızca
    { t: 'Willkommen',          dir: 'ltr' }, // Almanca
    { t: 'Welcome',             dir: 'ltr' }  // İngilizce (last)
  ];

  var reduce = false;
  try { reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) {}

  function choose(lang) {
    try { localStorage.setItem('ncf_lang', lang); } catch (e) {}
    splash.classList.add('ncf-splash-out');
    setTimeout(function () {
      if (lang === 'tr') {
        window.location.href = '/tr/';
      } else {
        splash.parentNode && splash.parentNode.removeChild(splash);
        document.documentElement.removeAttribute('data-ncf-splash');
      }
    }, 460);
  }

  splash.querySelectorAll('[data-lang]').forEach(function (btn) {
    btn.addEventListener('click', function () { choose(btn.getAttribute('data-lang')); });
  });
  var skip = splash.querySelector('.ncf-splash-skip');
  if (skip) skip.addEventListener('click', function (e) { e.preventDefault(); choose('en'); });

  function render(i) {
    var w = WORDS[i];
    wordEl.textContent = w.t;
    wordEl.setAttribute('dir', w.dir);
  }

  if (reduce) {
    render(WORDS.length - 1); // static "Welcome"
    return;
  }

  var i = 0;
  render(0);
  var STEP = 600; // ms per word; 11 words ≈ 6.6s total, under the 7s cap

  function tick() {
    i++;
    if (i >= WORDS.length) { render(WORDS.length - 1); return; } // settle on last word
    wordEl.style.opacity = '0';
    setTimeout(function () {
      render(i);
      wordEl.style.opacity = '1';
    }, 110);
    setTimeout(tick, STEP);
  }
  setTimeout(tick, STEP);
})();
