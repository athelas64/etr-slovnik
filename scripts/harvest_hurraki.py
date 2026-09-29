#!/usr/bin/env python3
"""Harvest Hurraki, the Leichte-Sprache / plain-language wiki, through its MediaWiki API.

    python harvest_hurraki.py --edition de --out hurraki-de.jsonl [--since 2026-01-01]
    python harvest_hurraki.py --edition en --out hurraki-en.jsonl

Writes one JSON object per article (JSON Lines): title, page id, revision id, timestamp,
categories, the parsed parts of the article (lead, same_words, explanation) and the raw
wikitext. With --since only pages changed after that date are fetched, so a later run
updates an existing file (pass the same --out; entries are merged by page id).

Licence of the harvested text: Creative Commons BY-SA 3.0 (German edition: BY-SA 3.0 DE).
Any dictionary built from it must carry the attribution and stay under the same licence.
Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

EDITIONS = {
    "de": {"api": "https://hurraki.de/w/api.php", "site": "https://hurraki.de/wiki/",
           "licence": "CC BY-SA 3.0 DE", "licence_url": "https://creativecommons.org/licenses/by-sa/3.0/de/",
           "same": ("Gleiche Wörter", "Gleiche Woerter", "Synonyme"), "long": ("Genaue Erklärung", "Genaue Erklaerung"),
           "cat": "Kategorie", "file": ("Datei", "File", "Bild")},
    "en": {"api": "https://hurraki.org/english/w/api.php", "site": "https://hurraki.org/english/wiki/",
           "licence": "CC BY-SA 3.0", "licence_url": "https://creativecommons.org/licenses/by-sa/3.0/",
           "same": ("Same words", "Synonyms", "Other words"), "long": ("Detailed explanation", "Exact explanation", "More information"),
           "cat": "Category", "file": ("File", "Image")},
}
UA = "etr-slovnik-harvest/0.1 (+https://github.com/athelas64/etr-slovnik; easy-to-read dictionary, non-commercial)"


def api(url: str, params: dict) -> dict:
    params = {**params, "format": "json", "formatversion": "2"}
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            if attempt == 3:
                raise
            print(f"  retry after error: {e}", file=sys.stderr)
            time.sleep(5 * (attempt + 1))
    return {}


# ------------------------------------------------------------------ wikitext -> parts
def clean(text: str, ed: dict) -> str:
    t = text
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = re.sub(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>", "", t, flags=re.S)
    t = re.sub(r"\{\{(?:[^{}]|\{\{[^{}]*\}\})*\}\}", "", t, flags=re.S)  # templates, one level nested
    t = re.sub(r"\[\[(?:%s):[^\]]*\]\]" % "|".join(ed["file"]), "", t)  # images
    t = re.sub(r"\[\[(?:%s):[^\]]*\]\]" % ed["cat"], "", t)
    t = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", t)  # [[target|shown]]
    t = re.sub(r"\[\[([^\]]*)\]\]", r"\1", t)  # [[shown]]
    t = re.sub(r"\[https?://\S+\s+([^\]]*)\]", r"\1", t)  # [url text]
    t = re.sub(r"\[https?://\S+\]", "", t)
    t = re.sub(r"'{2,}", "", t)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    t = t.replace("&nbsp;", " ")
    t = re.sub(r"__\w+__", "", t)
    # Mediopunkt and its look-alikes inside compound words: Internet·seite -> Internetseite
    t = re.sub(r"(?<=\w)[·˙•‧・](?=\w)", "", t)
    t = re.sub(r"(?<=\w)-(?=[a-zäöüß])", "", t) if ed is EDITIONS["de"] else t  # Internet-seite (lower-case tail)
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in t.split("\n")]
    out, blank = [], False
    for ln in lines:
        if ln.startswith("*") or ln.startswith("#"):
            ln = "- " + ln.lstrip("*# ").strip()
        if not ln:
            if not blank and out:
                out.append("")
            blank = True
            continue
        blank = False
        out.append(ln)
    return "\n".join(out).strip()


def split_sections(wikitext: str) -> list[tuple[str, str]]:
    """[(heading or '', body)] in order; '' is the lead."""
    parts = re.split(r"^==+\s*(.*?)\s*==+\s*$", wikitext, flags=re.M)
    sections = [("", parts[0])]
    for i in range(1, len(parts), 2):
        sections.append((parts[i].strip(), parts[i + 1] if i + 1 < len(parts) else ""))
    return sections


def parse_article(wikitext: str, ed: dict) -> dict:
    cats = re.findall(r"\[\[%s:([^\]|]+)" % ed["cat"], wikitext)
    lead, same, long, other = "", [], "", {}
    for head, body in split_sections(wikitext):
        h = head.lower()
        if head == "":
            lead = clean(body, ed)
        elif any(h == s.lower() for s in ed["same"]):
            same = [ln.lstrip("- ").strip() for ln in clean(body, ed).split("\n") if ln.strip()]
        elif any(h == s.lower() for s in ed["long"]):
            long = clean(body, ed)
        else:
            c = clean(body, ed)
            if c:
                other[head] = c
    return {"lead": lead, "same_words": same, "explanation": long, "other_sections": other, "categories": cats}


# ------------------------------------------------------------------ harvest
def iter_pages(ed: dict, since: str | None):
    """Yield (title, pageid, revid, timestamp, wikitext) for all articles, or the changed ones."""
    if since:
        params = {"action": "query", "generator": "recentchanges", "grcnamespace": "0", "grcend": since + "T00:00:00Z",
                  "grclimit": "50", "grctoponly": "1", "grctype": "edit|new",
                  "prop": "revisions", "rvprop": "ids|timestamp|content", "rvslots": "main"}
    else:
        params = {"action": "query", "generator": "allpages", "gapnamespace": "0", "gapfilterredir": "nonredirects",
                  "gaplimit": "50", "prop": "revisions", "rvprop": "ids|timestamp|content", "rvslots": "main"}
    cont: dict = {}
    while True:
        data = api(ed["api"], {**params, **cont})
        for p in data.get("query", {}).get("pages", []):
            revs = p.get("revisions") or []
            if not revs:
                continue
            r = revs[0]
            content = r.get("slots", {}).get("main", {}).get("content", "")
            if content.lstrip().lower().startswith("#redirect") or content.lstrip().lower().startswith("#weiterleitung"):
                continue
            yield p["title"], p["pageid"], r["revid"], r["timestamp"], content
        if "continue" not in data:
            break
        cont = data["continue"]
        time.sleep(0.5)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--edition", choices=EDITIONS, default="de")
    ap.add_argument("--out", required=True, help="JSON Lines file (merged by page id if it exists)")
    ap.add_argument("--since", help="only pages changed since this date (YYYY-MM-DD)")
    a = ap.parse_args()
    ed = EDITIONS[a.edition]
    out = Path(a.out)
    existing: dict[int, dict] = {}
    if out.exists():
        for ln in out.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                rec = json.loads(ln)
                existing[rec["pageid"]] = rec
        print(f"{len(existing)} articles already in {out}", file=sys.stderr)
    n = 0
    for title, pageid, revid, ts, wikitext in iter_pages(ed, a.since):
        rec = {"title": title, "pageid": pageid, "revid": revid, "timestamp": ts,
               "url": ed["site"] + urllib.parse.quote(title.replace(" ", "_")),
               "edition": a.edition, "licence": ed["licence"], "licence_url": ed["licence_url"],
               **parse_article(wikitext, ed), "wikitext": wikitext}
        existing[pageid] = rec
        n += 1
        if n % 250 == 0:
            print(f"  {n} articles ...", file=sys.stderr)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        for rec in sorted(existing.values(), key=lambda r: r["title"].lower()):
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"{n} articles fetched, {len(existing)} in {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
