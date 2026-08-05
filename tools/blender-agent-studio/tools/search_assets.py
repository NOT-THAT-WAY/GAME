#!/usr/bin/env python3
"""Search the compact asset catalogue without materializing binary content."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", default="", help="termes recherchés dans chemins, rôles et métadonnées")
    parser.add_argument("--kind", choices=("image", "video", "audio", "geometry"))
    parser.add_argument("--role")
    parser.add_argument("--extension")
    parser.add_argument("--path-prefix")
    parser.add_argument("--redistribution-status")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--json", action="store_true", help="émettre un objet JSON complet")
    args = parser.parse_args()
    if args.limit < 1 or args.limit > 1000:
        parser.error("--limit doit être compris entre 1 et 1000")

    assets = json.loads((ROOT / "catalog" / "assets.json").read_text(encoding="utf-8"))["assets"]
    terms = [term.casefold() for term in args.query.split() if term]
    extension = args.extension.lower().lstrip(".") if args.extension else None
    matches = []
    for asset in assets:
        paths = asset.get("paths", [])
        searchable = json.dumps(
            {"paths": paths, "roles": asset.get("roles", []), "metadata": asset.get("metadata", {})},
            ensure_ascii=False,
            sort_keys=True,
        ).casefold()
        if terms and not all(term in searchable for term in terms):
            continue
        if args.kind and asset.get("kind") != args.kind:
            continue
        if args.role and args.role not in asset.get("roles", []):
            continue
        if extension and f".{extension}" not in asset.get("extensions", []):
            continue
        if args.path_prefix and not any(path.startswith(args.path_prefix) for path in paths):
            continue
        if args.redistribution_status and args.redistribution_status not in asset.get("redistribution_statuses", []):
            continue
        matches.append(asset)

    matches.sort(key=lambda item: (item.get("kind", ""), item.get("paths", [""])[0].casefold()))
    selected = matches[: args.limit]
    payload = {
        "schema_version": 1,
        "query": args.query,
        "total_matches": len(matches),
        "returned": len(selected),
        "assets": selected,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"matches={len(matches)} returned={len(selected)}")
        for asset in selected:
            print(
                f"{asset['asset_id']}  {asset['kind']}  {asset['bytes']} bytes  "
                f"{asset['paths'][0]}  roles={','.join(asset.get('roles', []))}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
