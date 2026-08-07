#!/usr/bin/env python3
"""
Snapshot the public GitHub repos shown in the Finance Engineering Open Source
section, into data/repos.json.

Run at build time, not in the browser: the GitHub API rate-limits unauthenticated
requests to 60/hour per IP, which a client-side fetch would burn through and
which would also make the section's contents depend on the visitor's network.

A repo that is private, renamed or deleted resolves to status "pending" and its
card renders hidden — nothing is invented and no card ever links somewhere that
404s.

    python3 scripts/fetch_repos.py
"""
import json
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("requests is required: pip install requests")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OWNER = "orknn"
TIMEOUT = 15
UA = {"User-Agent": "Mozilla/5.0 (NoCashFlow repo fetcher)",
      "Accept": "application/vnd.github+json"}

# name -> the stack badges to show. The blurb is authored, not scraped: GitHub
# descriptions are terse and change without review.
REPOS = {
    "nocashflow.net": ["Python", "GitHub Actions", "Cloudflare"],
    "Crypto_Macro_Newsletter": ["Python", "Anthropic API", "GitHub Actions"],
    "Job-Hunter": ["Python", "GitHub Actions"],
    "stock-analyzer": ["Python", "Anthropic API"],
}


def fetch(name):
    url = f"https://api.github.com/repos/{OWNER}/{name}"
    try:
        r = requests.get(url, headers=UA, timeout=TIMEOUT)
    except Exception as e:
        print(f"  ! {name}: {e}")
        return None
    if r.status_code == 404:
        print(f"  – {name}: not public")
        return None
    if r.status_code == 403:
        print(f"  ! {name}: rate-limited — leaving the previous snapshot alone")
        return "ratelimited"
    if not r.ok:
        print(f"  ! {name}: HTTP {r.status_code}")
        return None
    d = r.json()
    if d.get("private"):
        return None
    print(f"  ✓ {name}: {d['stargazers_count']}★  pushed {d['pushed_at'][:10]}")
    return {
        "name": d["name"],
        "full_name": d["full_name"],
        "url": d["html_url"],
        "description": d.get("description") or "",
        "stars": d.get("stargazers_count", 0),
        "language": d.get("language") or "",
        "pushed_at": d.get("pushed_at", "")[:10],
        "status": "live",
    }


def main():
    prev = {}
    p = DATA / "repos.json"
    if p.exists():
        try:
            prev = {r["key"]: r for r in json.loads(p.read_text(encoding="utf-8")).get("repos", [])}
        except Exception:
            pass

    print("Fetching repo metadata…")
    out = []
    for name, stack in REPOS.items():
        d = fetch(name)
        if d == "ratelimited":
            if name in prev:
                out.append(prev[name])
            continue
        if d is None:
            out.append({"key": name, "name": name, "status": "pending", "stack": stack})
            continue
        d["key"] = name
        d["stack"] = stack
        out.append(d)

    DATA.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"repos": out}, ensure_ascii=False, indent=2) + "\n",
                 encoding="utf-8")
    live = sum(1 for r in out if r.get("status") == "live")
    print(f"\n✓ data/repos.json — {live} live, {len(out) - live} pending")


if __name__ == "__main__":
    main()
