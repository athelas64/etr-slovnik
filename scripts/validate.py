#!/usr/bin/env python3
"""Validate dictionary files against schema/slovnik.schema.json and the house rules.

    python validate.py slovniky/*.json

Checks: JSON Schema (needs the `jsonschema` package; without it only the house rules run),
unique ids, id derived from the term, one sentence per line in `easy` (no line over 15
words), no brackets, slashes, semicolons or paragraph signs in `easy`, and that a
machine-translated entry is not marked reviewed or reader-checked.
Exit code 1 when anything fails.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schema" / "slovnik.schema.json"
MAX_WORDS = 15
BAD_CHARS = re.compile(r"[()\[\]/;§&#]|—|–")
WORD = re.compile(r"[\wÀ-ſ]+(?:-[\wÀ-ſ]+)*")


def slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s)).strip("-")


def _words(s: str) -> list[str]:
    return [slug(w) for w in WORD.findall(s) if slug(w)]


def form_matches_term(form: str, term: str) -> bool:
    """A form must be an inflection or a fixed variant of the headword: at least one of its
    words (4+ letters) starts with the same 4 letters as a word of the term. Short
    headwords (under 4 letters, e.g. 'súd') match exactly."""
    tw = _words(term)
    for fw in _words(form):
        for t in tw:
            if len(t) < 4 or len(fw) < 4:
                if fw == t:
                    return True
            elif fw[:4] == t[:4]:
                return True
    return False


def house_rules(data: dict, name: str) -> list[str]:
    errs: list[str] = []
    ids: dict[str, str] = {}
    for e in data.get("entries", []):
        eid, term = e.get("id", "?"), e.get("term", "?")
        where = f"{name}: {eid}"
        if eid in ids:
            errs.append(f"{where}: duplicate id (also used by '{ids[eid]}')")
        ids[eid] = term
        for f in e.get("forms") or []:
            if re.fullmatch(r"[A-ZÁÄČĎÉÍĹĽŇÓÔŔŠŤÚÝŽ]{2,6}", f):
                errs.append(f"{where}: form '{f}' is an abbreviation; put it in same_words (matched exactly)")
            elif not form_matches_term(f, term):
                errs.append(f"{where}: form '{f}' is not an inflection of '{term}'; move it to same_words or drop it")
        for s in e.get("same_words") or []:
            if slug(s) == eid or s in (e.get("forms") or []):
                errs.append(f"{where}: same_words repeats the term or a form: '{s}'")
        easy = e.get("easy", "")
        for ln in easy.split("\n"):
            if not ln.strip():
                continue
            n = len(WORD.findall(ln))
            if n > MAX_WORDS:
                errs.append(f"{where}: sentence has {n} words (limit {MAX_WORDS}): {ln[:70]}")
            if re.search(r"[.!?]\s+[A-ZÁÄČĎÉÍĹĽŇÓÔŔŠŤÚÝŽ]", ln):
                errs.append(f"{where}: two sentences on one line: {ln[:70]}")
            m = BAD_CHARS.search(ln)
            if m:
                errs.append(f"{where}: character '{m.group(0)}' not allowed in easy text: {ln[:70]}")
        if e.get("origin") == "machine-translated" and e.get("status") in ("reviewed", "reader-checked"):
            errs.append(f"{where}: machine-translated entries stay 'draft' until a person reviews them")
        if data.get("domains") and e.get("domain") and e["domain"] not in data["domains"]:
            errs.append(f"{where}: domain '{e['domain']}' is not in the file's domains list")
    return errs


def main(paths: list[str]) -> int:
    schema = json.loads(SCHEMA.read_text("utf-8"))
    try:
        import jsonschema  # type: ignore
        validator = jsonschema.Draft202012Validator(schema)
    except ImportError:
        validator = None
        print("note: jsonschema not installed, schema check skipped (pip install jsonschema)", file=sys.stderr)
    failed = False
    for p in paths:
        path = Path(p)
        try:
            data = json.loads(path.read_text("utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"{path}: not valid JSON: {e}")
            failed = True
            continue
        errs = []
        if validator:
            for err in sorted(validator.iter_errors(data), key=lambda x: list(x.path)):
                loc = "/".join(str(x) for x in err.path) or "(root)"
                errs.append(f"{path.name}: schema: {loc}: {err.message}")
        errs += house_rules(data, path.name)
        if errs:
            failed = True
            print("\n".join(errs))
        else:
            print(f"{path.name}: ok ({len(data.get('entries', []))} entries, version {data.get('version')})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or [str(p) for p in (ROOT / "slovniky").glob("*.json")]))
