#!/usr/bin/env python3
"""
Validate every JSON-LD block the build emits.

Parses each <script type="application/ld+json"> in the generated pages and
checks three things:

  1. it is valid JSON and carries @context / @type
  2. the required fields for its type are present and non-empty
  3. every internal @id reference resolves to a node declared on the same page

(3) is the one that matters most here. Articles reference the author and the
publisher by @id instead of restating them; if a reference ever points at an
@id no page declares, search engines silently read the author as unknown and
nothing in the build would have complained.

    python3 scripts/check_jsonld.py          # check, print a summary
    python3 scripts/check_jsonld.py -v       # list every page checked

Exit code is non-zero when anything fails, so CI can gate on it.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT_RE = re.compile(
    r'<script type="application/ld\+json">(.*?)</script>', re.S)

# type -> fields that must be present and non-empty
REQUIRED = {
    "WebSite": ["name", "url"],
    "Organization": ["name", "url"],
    "Person": ["name", "url", "jobTitle"],
    "NewsArticle": ["headline", "datePublished", "author", "publisher",
                    "inLanguage"],
    "TechArticle": ["headline", "datePublished", "author", "publisher",
                    "inLanguage"],
}

SKIP_DIRS = {"bulletins", "assets", "brand_logo", "Logo", "node_modules",
             "docs", "scripts", "content", "workers", "share", ".git"}


def pages():
    for p in sorted(ROOT.rglob("*.html")):
        rel = p.relative_to(ROOT)
        if rel.parts[0] in SKIP_DIRS or rel.parts[0].startswith("_"):
            continue
        yield p


def nodes_of(doc):
    """Flatten a JSON-LD document into its list of nodes."""
    if isinstance(doc, list):
        return [n for d in doc for n in nodes_of(d)]
    if not isinstance(doc, dict):
        return []
    if "@graph" in doc:
        return [n for n in doc["@graph"] if isinstance(n, dict)]
    return [doc]


def collect_refs(obj, out):
    """Every {"@id": ...} reference that is not itself a node declaration."""
    if isinstance(obj, dict):
        keys = set(obj) - {"@id"}
        if "@id" in obj and not keys:
            out.add(obj["@id"])
        for v in obj.values():
            collect_refs(v, out)
    elif isinstance(obj, list):
        for v in obj:
            collect_refs(v, out)


def check_page(path):
    """-> (blocks_checked, [problem, ...])"""
    html = path.read_text(encoding="utf-8")
    blocks = SCRIPT_RE.findall(html)
    problems, declared, refs = [], set(), set()
    for i, raw in enumerate(blocks):
        # the build escapes < and > inside the payload to keep it script-safe
        text = raw.replace("\\u003c", "<").replace("\\u003e", ">")
        try:
            doc = json.loads(text)
        except json.JSONDecodeError as e:
            problems.append(f"block {i}: invalid JSON — {e}")
            continue
        if "@context" not in doc:
            problems.append(f"block {i}: missing @context")
        for node in nodes_of(doc):
            t = node.get("@type")
            if not t:
                problems.append(f"block {i}: node without @type")
                continue
            if node.get("@id"):
                declared.add(node["@id"])
            for field in REQUIRED.get(t, []):
                v = node.get(field)
                if v in (None, "", [], {}):
                    problems.append(f"block {i}: {t} missing {field}")
        collect_refs(doc, refs)

    for ref in sorted(refs - declared):
        if ref.startswith("http") and "#" not in ref:
            continue  # a plain URL reference, not an internal node id
        problems.append(f"unresolved @id reference: {ref}")
    return len(blocks), problems


def main():
    verbose = "-v" in sys.argv
    total_pages = total_blocks = 0
    failures = []
    for p in pages():
        n, problems = check_page(p)
        if n == 0:
            continue
        total_pages += 1
        total_blocks += n
        rel = p.relative_to(ROOT)
        if problems:
            failures.append((rel, problems))
        elif verbose:
            print(f"  ok  {rel}  ({n} block{'s' if n > 1 else ''})")

    print(f"\nChecked {total_blocks} JSON-LD block(s) across {total_pages} page(s).")
    if failures:
        print(f"\n{len(failures)} page(s) with problems:\n")
        for rel, problems in failures:
            print(f"  {rel}")
            for problem in problems:
                print(f"      - {problem}")
        return 1
    print("No problems found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
