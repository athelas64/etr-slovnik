#!/usr/bin/env python3
"""Harvest the standard / easy-to-read text pairs from komisar.sk.

    python harvest_komisar.py [--out ../zdroje/komisar-pary.json] [--base https://www.komisar.sk]

The site of the Komisár pre osoby so zdravotným postihnutím carries, on some pages, the
standard text and its easy-to-read version side by side: elements with `data-standard`
and elements with `data-etr` (a `div.etr-text` or a heading). This script reads the
sitemap, fetches every internal page, and writes the pairs in document order, grouped
under the standard heading they follow. The pairs are the raw material from which the
public-sector dictionary entries are drafted and reviewed by a person; the script
itself invents nothing.

Needs beautifulsoup4 and lxml.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) etr-slovnik-harvest/0.1 (+https://github.com/athelas64/etr-slovnik)"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "sk"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def text_of(el) -> str:
    """Plain text with one sentence per line where the source had block elements."""
    parts = []
    for child in el.descendants:
        if isinstance(child, str):
            parts.append(child)
        elif child.name in ("p", "li", "br", "h1", "h2", "h3", "h4", "div"):
            parts.append("\n")
    txt = "".join(parts)
    lines = [re.sub(r"[ \t ]+", " ", ln).strip() for ln in txt.split("\n")]
    return "\n".join(ln for ln in lines if ln)


def internal_links(html: str, base: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    host = urlparse(base).netloc
    urls = set()
    for a in soup.select("a[href]"):
        u = urljoin(base, a["href"].split("#")[0])
        p = urlparse(u)
        if p.netloc == host and not re.search(r"\.(xml|pdf|jpg|png|webp|svg|mp3|zip|docx?)$", p.path, re.I):
            urls.add(u.rstrip("/") or base)
    return sorted(urls)


def harvest_page(url: str, html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "noscript", "svg"]):
        t.decompose()
    title = soup.title.get_text(strip=True) if soup.title else url
    pairs: list[dict] = []
    current: dict | None = None
    for el in soup.find_all(lambda tag: tag.has_attr("data-standard") or tag.has_attr("data-etr")):
        is_std = el.has_attr("data-standard")
        is_head = el.name in ("h1", "h2", "h3", "h4")
        if is_std and is_head:
            current = {"page": url, "page_title": title, "heading_standard": text_of(el),
                       "heading_etr": "", "standard": [], "etr": []}
            pairs.append(current)
            continue
        if current is None:
            current = {"page": url, "page_title": title, "heading_standard": "", "heading_etr": "",
                       "standard": [], "etr": []}
            pairs.append(current)
        if is_std:
            current["standard"].append(text_of(el))
        elif is_head:
            current["heading_etr"] = text_of(el)
        else:
            current["etr"].append(text_of(el))
    out = []
    for p in pairs:
        if not p["etr"] and not p["heading_etr"]:
            continue
        p["standard"] = "\n\n".join(x for x in p["standard"] if x)
        p["etr"] = "\n\n".join(x for x in p["etr"] if x)
        out.append(p)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="https://www.komisar.sk")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "zdroje" / "komisar-pary.json"))
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    a = ap.parse_args()

    sitemap = fetch(a.base + "/mapa-stranok")
    urls = internal_links(sitemap, a.base)
    if a.base.rstrip("/") not in urls:
        urls.insert(0, a.base.rstrip("/"))
    print(f"{len(urls)} pages in the sitemap", file=sys.stderr)
    all_pairs, pages_with_etr = [], []
    for i, u in enumerate(urls, 1):
        try:
            html = fetch(u)
        except Exception as e:  # noqa: BLE001
            print(f"  skip {u}: {e}", file=sys.stderr)
            continue
        pairs = harvest_page(u, html)
        if pairs:
            pages_with_etr.append(u)
            all_pairs.extend(pairs)
        print(f"  [{i}/{len(urls)}] {u} -> {len(pairs)} pairs", file=sys.stderr)
        time.sleep(a.delay)
    result = {
        "source": {"name": "Úrad komisára pre osoby so zdravotným postihnutím", "base": a.base,
                   "fetched": date.today().isoformat(), "pages_with_etr": pages_with_etr,
                   "note": "Standard and easy-to-read texts as published on the site (data-standard / data-etr). "
                           "Raw material for dictionary entries; every entry is drafted and reviewed by a person."},
        "pairs": all_pairs,
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(all_pairs)} pairs from {len(pages_with_etr)} pages -> {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
