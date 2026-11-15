#!/usr/bin/env python3
"""Full-page screenshots of the built site, for design before/after review.

Serves the repo root on a local port and captures every page type at
desktop (1440) and phone (390) width with Playwright/Chromium.

    python3 tools/shoot.py OUT_DIR            # all page types
    python3 tools/shoot.py OUT_DIR --static   # append ?static (Liquid pages: no motion)
    python3 tools/shoot.py OUT_DIR --dark     # After Hours (default: light, pinned)

Animations are given time to settle; the language splash is suppressed by
seeding localStorage, so the root page renders as a returning EN visitor.
"""
import http.server
import socketserver
import sys
import threading
from functools import partial
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PORT = 8765

PAGES = [
    ("home-en", "/"),
    ("home-tr", "/tr/"),
    ("article-en", "/articles/core-inflation.html"),
    ("article-tr", "/tr/yazilar/cekirdek.html"),
    ("articles-en", "/articles.html"),
    ("macro-en", "/macro.html"),
    ("dashboard-en", "/dashboard.html"),
    ("calendar-en", "/calendar.html"),
    ("bulletin-en", "/bulletin_page.html"),
    ("archive-en", "/archive.html"),
    ("glossary-en", "/glossary.html"),
    ("about-en", "/about.html"),
    ("privacy-en", "/privacy.html"),
    ("indicator-en", "/now/dxy-dollar-index.html"),
    ("fe-hub-en", "/finance-engineering.html"),
    ("fe-essay-en", "/finance-engineering/when-data-lies.html"),
    ("404", "/404.html"),
    # Faz 7: the TR side of every page type
    ("articles-tr", "/tr/yazilar.html"),
    ("macro-tr", "/tr/macro.html"),
    ("dashboard-tr", "/tr/dashboard.html"),
    ("calendar-tr", "/tr/takvim.html"),
    ("bulletin-tr", "/tr/bulletin_page.html"),
    ("archive-tr", "/tr/arsiv.html"),
    ("glossary-tr", "/tr/sozluk.html"),
    ("about-tr", "/tr/hakkinda.html"),
    ("privacy-tr", "/tr/privacy.html"),
    ("indicators-tr", "/tr/simdi/"),
    ("indicator-tr", "/tr/simdi/dxy-dolar-endeksi.html"),
    ("fe-hub-tr", "/tr/finance-engineering.html"),
    ("subscribed-tr", "/tr/subscribed.html"),
    ("subscribed-en", "/subscribed.html"),
]
WIDTHS = [("desktop", 1440, 900), ("tablet", 834, 1112), ("phone", 390, 844)]
# QA: python3 tools/shoot.py OUT --only desktop  (comma list of width names)


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main():
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    q = "?static" if "--static" in sys.argv else ""
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.TCPServer(("127.0.0.1", PORT), partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as pw:
            br = pw.chromium.launch()
            only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
            for wname, w, h in WIDTHS:
                if only and wname not in only:
                    continue
                ctx = br.new_context(viewport={"width": w, "height": h}, device_scale_factor=1,
                                     reduced_motion="no-preference")
                ctx.add_init_script("try{localStorage.setItem('ncf_lang','en')}catch(e){}")
                # pin the theme: the site turns After Hours on by itself 21:00-07:00 local
                theme = "dark" if "--dark" in sys.argv else "light"
                ctx.add_init_script("try{localStorage.setItem('ncf_theme','%s')}catch(e){}" % theme)
                pg = ctx.new_page()
                errs = []
                pg.on("pageerror", lambda e: errs.append(str(e)[:120]))
                for name, path in PAGES:
                    errs.clear()
                    if name.endswith("-tr"):
                        pg.add_init_script("try{localStorage.setItem('ncf_lang','tr')}catch(e){}")
                    # "load", not "networkidle": app.js keeps polling live proxies, so the
                    # page never goes idle — the build-time snapshot is what we capture
                    pg.goto(f"http://127.0.0.1:{PORT}{path}{q}", wait_until="load", timeout=30000)
                    # scroll through so IntersectionObserver reveals fire, then back to top
                    pg.evaluate("""async()=>{for(let y=0;y<document.body.scrollHeight;y+=600){scrollTo(0,y);await new Promise(r=>setTimeout(r,60))}scrollTo(0,0)}""")
                    # a fast scroll can outrun IntersectionObserver: force the settled
                    # state (Broadsheet .reveal + app.js inline opacity, Liquid .rv)
                    pg.evaluate("""()=>{document.querySelectorAll('.reveal,.rv').forEach(e=>e.classList.add('in'));
                      document.querySelectorAll('[style*="opacity: 0"]').forEach(e=>{e.style.opacity='1';e.style.transform='none'})}""")
                    pg.wait_for_timeout(1500)
                    f = out / f"{name}-{wname}.png"
                    pg.screenshot(path=str(f), full_page=True)
                    over = pg.evaluate("document.documentElement.scrollWidth-innerWidth")
                    flag = ("  OVERFLOW %dpx" % over if over > 0 else "") + ("  JS: " + " | ".join(errs) if errs else "")
                    print((f.relative_to(ROOT) if f.is_relative_to(ROOT) else f), flag)
                ctx.close()
            br.close()
    finally:
        srv.shutdown()


if __name__ == "__main__":
    main()
