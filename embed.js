/* ============================================================================
   NoCashFlow · embeddable live-market widget
   Drop on any site:
     <script src="https://nocashflow.net/embed.js" data-ncf-widget async></script>
   or target a specific element:
     <div id="ncf"></div>
     <script src="https://nocashflow.net/embed.js" data-ncf-target="ncf" async></script>
   Self-contained: scoped styles, no globals, no dependencies. Pulls the same
   public snapshot the site is built from (no fabricated numbers).
   ============================================================================ */
(function () {
  "use strict";
  var script = document.currentScript;
  // data source origin — overridable for same-origin on-site previews
  var ORIGIN = "https://nocashflow.net";
  var o = script && script.getAttribute("data-ncf-origin");
  if (o !== null && o !== undefined) ORIGIN = o;
  var REF = "https://nocashflow.net/?utm_source=widget&utm_medium=embed";  // backlink stays absolute

  // resolve the mount point: explicit target, or a div inserted after the tag
  var mount;
  var targetId = script && script.getAttribute("data-ncf-target");
  if (targetId) {
    mount = document.getElementById(targetId);
  }
  if (!mount) {
    mount = document.createElement("div");
    if (script && script.parentNode) script.parentNode.insertBefore(mount, script.nextSibling);
    else document.body.appendChild(mount);
  }

  // inject scoped styles once
  if (!document.getElementById("ncfw-style")) {
    var css = document.createElement("style");
    css.id = "ncfw-style";
    css.textContent = [
      ".ncfw{all:initial;display:block;box-sizing:border-box;max-width:380px;",
      "font-family:Georgia,'Times New Roman',serif;color:#191512;background:#fff;",
      "border:1px solid #E8E3D8;border-top:3px solid #C98A2B;padding:18px 18px 14px;",
      "line-height:1.3}",
      ".ncfw *{box-sizing:border-box;margin:0;padding:0}",
      ".ncfw-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}",
      ".ncfw-brand{font-weight:700;font-size:15px;letter-spacing:.02em}",
      ".ncfw-brand i{color:#C98A2B;font-style:normal}",
      ".ncfw-live{font-family:ui-monospace,Menlo,monospace;font-size:9px;letter-spacing:.14em;",
      "text-transform:uppercase;color:#15803d;display:flex;align-items:center;gap:5px}",
      ".ncfw-dot{width:6px;height:6px;border-radius:50%;background:#15803d;display:inline-block}",
      ".ncfw-hero{display:flex;align-items:baseline;gap:10px;padding:6px 0 14px;",
      "border-bottom:1px solid #E8E3D8;margin-bottom:12px}",
      ".ncfw-hero b{font-size:44px;font-weight:700;line-height:1;font-variant-numeric:tabular-nums}",
      ".ncfw-hero span{font-family:ui-monospace,Menlo,monospace;font-size:10px;letter-spacing:.1em;",
      "text-transform:uppercase;color:#C98A2B}",
      ".ncfw-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px 16px}",
      ".ncfw-k{font-family:ui-monospace,Menlo,monospace;font-size:9px;letter-spacing:.1em;",
      "text-transform:uppercase;color:#C98A2B;margin-bottom:2px}",
      ".ncfw-v{font-size:19px;font-weight:700;font-variant-numeric:tabular-nums}",
      ".ncfw-c{font-family:ui-monospace,Menlo,monospace;font-size:11px;margin-left:6px}",
      ".ncfw-up{color:#15803d}.ncfw-dn{color:#D83A1E}",
      ".ncfw-foot{margin-top:14px;padding-top:10px;border-top:1px solid #E8E3D8;",
      "display:flex;justify-content:space-between;align-items:center;",
      "font-family:ui-monospace,Menlo,monospace;font-size:10px;color:#7a7268}",
      ".ncfw-foot a{color:#191512;text-decoration:none;border-bottom:1px solid #C98A2B}",
      ".ncfw-foot a:hover{color:#C98A2B}"
    ].join("");
    document.head.appendChild(css);
  }

  function esc(s) { return String(s == null ? "" : s).replace(/[<>&]/g, function (c) {
    return { "<": "&lt;", ">": "&gt;", "&": "&amp;" }[c]; }); }

  function dirClass(d) { return d === "up" ? "ncfw-up" : d === "dn" ? "ncfw-dn" : ""; }
  function signClass(chg) {
    var s = String(chg || "").trim();
    if (s.charAt(0) === "+") return "ncfw-up";
    if (s.charAt(0) === "-" || s.charAt(0) === "−") return "ncfw-dn";
    return "";
  }

  function cell(k, d) {
    d = d || {};
    return '<div><div class="ncfw-k">' + k + '</div><div class="ncfw-v">' +
      esc(d.px || "—") + '<span class="ncfw-c ' + signClass(d.chg) + '">' +
      esc(d.chg || "") + '</span></div></div>';
  }

  function render(m) {
    var inst = (m && m.instruments) || {};
    var fg = inst.fg || {};
    var fgcls = "";
    var n = parseInt(fg.px, 10);
    if (!isNaN(n)) fgcls = n < 25 ? "ncfw-dn" : n < 55 ? "" : "ncfw-up";
    mount.innerHTML =
      '<div class="ncfw" role="complementary" aria-label="NoCashFlow live market data">' +
        '<div class="ncfw-top">' +
          '<div class="ncfw-brand">NO<i>/</i>CASHFLOW</div>' +
          '<div class="ncfw-live"><span class="ncfw-dot"></span>Live</div>' +
        '</div>' +
        '<div class="ncfw-hero">' +
          '<b class="' + fgcls + '">' + esc(fg.px || "—") + '</b>' +
          '<span>' + esc(fg.chg || "Fear & Greed") + '<br>Crypto Fear &amp; Greed</span>' +
        '</div>' +
        '<div class="ncfw-grid">' +
          cell("Bitcoin", inst.btc) + cell("Ethereum", inst.eth) +
          cell("Gold", inst.gold) + cell("US 10Y", inst.us10y) +
        '</div>' +
        '<div class="ncfw-foot">' +
          '<span>Macro &amp; market data</span>' +
          '<a href="' + REF + '" target="_blank" rel="noopener">nocashflow.net ↗</a>' +
        '</div>' +
      '</div>';
  }

  // JSONP: a cross-origin fetch of /data/market.json would be CORS-blocked on
  // third-party sites, but a <script> load isn't. build.py emits data/market.js
  // which calls this global with the same snapshot.
  window.NCFMarket = function (m) { try { render(m || {}); } catch (e) { render({}); } };

  function load() {
    var s = document.createElement("script");
    s.src = ORIGIN + "/data/market.js?t=" + Date.now();
    s.async = true;
    s.onerror = function () { render({}); };
    s.onload = function () { if (s.parentNode) s.parentNode.removeChild(s); };
    document.head.appendChild(s);
  }

  render({});                          // instant skeleton, no empty box
  load();
  setInterval(load, 5 * 60 * 1000);    // refresh every 5 min
})();
