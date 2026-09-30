#!/usr/bin/env python3
"""Parse the Inclusion Europe easy-to-read dictionary (English) from a saved copy of its page.

    python harvest_inclusion_europe.py [--html easy-to-read-term-en.html] [--out inclusion-europe-en.json]
    python harvest_inclusion_europe.py --fetch      # download the page first, then parse

The page https://www.inclusion-europe.eu/easy-to-read-term/ has an alphabetical index of
`<p><strong>Term</strong></p>` items (some wrapped in a link to `#Anchor`), followed by the
definitions: `<h3 id="Anchor">Term</h3>` and the `<p>` and `<ul>` blocks up to the next
`<h3>`. Some definitions have an `<h3>` without an id; they are kept, with an empty anchor
and the page URL. The page's HTML nests badly (stray `</article>` and re-opened wrappers
between definitions), so the raw text is split at every `<h3` and each piece is parsed on
its own; a DOM walk would move paragraphs to the wrong term.

Writes one JSON file: `index` (every index item, its anchor and whether a definition was
found) and `terms` (term, anchor, url, paragraphs). A paragraph keeps the source's line
breaks (`<br />`) as newlines; a list becomes one paragraph with a `- ` line per item.
Cross-links are dropped, their words kept. The script invents nothing: an index item
without a definition is reported, not filled in.

Default paths are in %LOCALAPPDATA%\\easy-to-read\\inclusion-europe (the live site blocks
some bots, so work from the saved copy; keep downloads out of the repository).
Licence of the harvested text: (c) Inclusion Europe; cite the page at every entry.
Needs beautifulsoup4 and lxml.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString

PAGE = "https://www.inclusion-europe.eu/easy-to-read-term/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) etr-slovnik-harvest/0.1 (+https://github.com/athelas64/etr-slovnik)"
BASE = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local" / "share") / "easy-to-read" / "inclusion-europe"
# the definitions end where the page's sidebar widgets begin
END_MARKERS = ('<div class="awac-wrapper"', '<div class="vc_row wpb_row', 'id="comments"')


def fetch(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    print(f"saved {len(data)} bytes to {dest}", file=sys.stderr)


def norm(s: str) -> str:
    """Key for matching an index item to a heading: case, spaces and hyphens ignored."""
    return re.sub(r"[\s\-‐‑–]+", " ", s).strip().lower()


def anchor_of(href: str) -> str:
    return urllib.parse.unquote(href.split("#", 1)[1]) if "#" in href else ""


def url_for(anchor: str) -> str:
    return PAGE + ("#" + urllib.parse.quote(anchor) if anchor else "")


def block_text(el) -> str:
    """Text of a block with <br> as newline; spaces collapsed; empty lines dropped."""
    for br in el.find_all("br"):
        br.replace_with(NavigableString("\n"))
    txt = el.get_text("")
    lines = [re.sub(r"[ \t \r]+", " ", ln).strip() for ln in txt.split("\n")]
    out = []
    for ln in lines:
        if not ln:
            continue
        if ln[0] in "•·▪◦":
            ln = "- " + ln[1:].strip()
        out.append(ln)
    return "\n".join(out)


# ------------------------------------------------------------------ index
def parse_index(html: str) -> list[dict]:
    """The alphabetical index: from the first letter heading to the first definition."""
    start = html.find('<h2 id="A"')
    end = html.find("<h3", start)
    soup = BeautifulSoup(html[start:end], "lxml")
    items = []
    for p in soup.find_all("p"):
        strong = p.find("strong")
        if not strong or not p.get_text(strip=True) or len(p.find_all("strong")) > 1:
            continue
        a = p.find("a", href=True)
        items.append({"term": re.sub(r"\s+", " ", strong.get_text()).strip(),
                      "anchor": anchor_of(a["href"]) if a else ""})
    return items


# ------------------------------------------------------------------ definitions
def parse_terms(html: str) -> list[dict]:
    first = html.find("<h3")
    stop = min((i for i in (html.find(m, first) for m in END_MARKERS) if i > 0), default=len(html))
    body = html[first:stop]
    pieces = [p for p in re.split(r"(?=<h3[\s>])", body) if p.startswith("<h3")]
    terms = []
    for piece in pieces:
        soup = BeautifulSoup(piece, "lxml")
        h3 = soup.find("h3")
        term = re.sub(r"\s+", " ", h3.get_text()).strip()
        anchor = (h3.get("id") or "").strip()
        h3.decompose()
        paragraphs = []
        for el in soup.find_all(["p", "ul", "ol"]):
            if el.find_parent(["p", "ul", "ol"]):
                continue
            if el.name == "p":
                t = block_text(el)
            else:
                t = "\n".join("- " + block_text(li).replace("\n", " ") for li in el.find_all("li", recursive=False))
            if t.strip():
                paragraphs.append(t)
        terms.append({"term": term, "anchor": anchor, "url": url_for(anchor), "paragraphs": paragraphs})
    return terms


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--html", default=str(BASE / "easy-to-read-term-en.html"), help="saved page (input)")
    ap.add_argument("--out", default=str(BASE / "inclusion-europe-en.json"), help="parsed terms (output)")
    ap.add_argument("--fetch", action="store_true", help=f"download {PAGE} to --html first")
    ap.add_argument("--fetched", help="date the page was fetched (YYYY-MM-DD), stored in the output")
    a = ap.parse_args()
    src = Path(a.html)
    if a.fetch:
        fetch(PAGE, src)
    html = src.read_text(encoding="utf-8")
    index = parse_index(html)
    terms = parse_terms(html)
    by_anchor = {t["anchor"]: t for t in terms if t["anchor"]}
    by_name = {norm(t["term"]): t for t in terms}
    for it in index:
        t = by_anchor.get(it["anchor"]) or by_name.get(norm(it["term"]))
        it["has_definition"] = bool(t and t["paragraphs"])
        it["heading"] = t["term"] if t else ""
    indexed = {norm(it["heading"]) for it in index if it["heading"]}
    out = {"source": PAGE, "fetched": a.fetched, "html": src.name,
           "index": index, "terms": terms,
           "not_in_index": [t["term"] for t in terms if norm(t["term"]) not in indexed]}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    missing = [it["term"] for it in index if not it["has_definition"]]
    print(f"{len(index)} index items, {len(terms)} definitions, "
          f"{len(missing)} index items without a definition: {', '.join(missing) or '-'}", file=sys.stderr)
    if out["not_in_index"]:
        print(f"definitions not in the index: {', '.join(out['not_in_index'])}", file=sys.stderr)
    print(f"written to {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
