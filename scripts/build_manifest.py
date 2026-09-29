#!/usr/bin/env python3
"""Write manifest.json: the file list with sha256, entry counts and versions.

    python build_manifest.py [--check]

The easy-to-read skill downloads this small file first and fetches a dictionary only
when its hash changed. `--check` exits 1 when the committed manifest is stale (used in
CI on pull requests; the workflow on main rewrites it).
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "manifest.json"


def build() -> dict:
    files = {}
    versions = []
    for p in sorted((ROOT / "slovniky").glob("*.json")):
        raw = p.read_bytes()
        data = json.loads(raw.decode("utf-8"))
        files[f"slovniky/{p.name}"] = {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "entries": len(data.get("entries", [])),
            "version": data.get("version"),
            "tier": data.get("tier"),
            "lang": data.get("lang"),
            "licence": data.get("licence", {}).get("name"),
        }
        versions.append(data.get("version") or "")
    return {
        "name": "etr-slovnik",
        "version": max(versions) if versions else "",
        "schema": "schema/slovnik.schema.json",
        "files": files,
    }


def main() -> int:
    manifest = build()
    if "--check" in sys.argv:
        if not OUT.exists():
            print("manifest.json missing; run scripts/build_manifest.py")
            return 1
        old = json.loads(OUT.read_text("utf-8"))
        old.pop("updated", None)
        if old != manifest:
            print("manifest.json is stale; run scripts/build_manifest.py and commit it")
            return 1
        print("manifest.json is current")
        return 0
    # Keep the old timestamp when nothing else changed, so CI does not commit on every push.
    if OUT.exists():
        old = json.loads(OUT.read_text("utf-8"))
        stamp = old.pop("updated", None)
        if old == manifest and stamp:
            print(f"manifest.json unchanged (version {manifest['version']})")
            return 0
    manifest["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"manifest.json: version {manifest['version']}, {len(manifest['files'])} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
