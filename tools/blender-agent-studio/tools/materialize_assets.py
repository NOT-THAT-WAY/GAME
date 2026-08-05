#!/usr/bin/env python3
"""Copy explicitly selected catalog assets from a private vault and verify their hashes."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-vault", type=Path, required=True)
    parser.add_argument("--asset-id", action="append", default=[], help="sha256 complet ou préfixe unique")
    parser.add_argument("--path", action="append", default=[], help="chemin source exact du catalogue")
    parser.add_argument("--destination", type=Path, default=ROOT / "local_assets")
    parser.add_argument("--confirm-rights", action="store_true", help="confirmer que la copie locale est autorisée")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    if not args.confirm_rights:
        parser.error("--confirm-rights est requis avant de matérialiser un asset")
    if not args.asset_id and not args.path:
        parser.error("fournir au moins un --asset-id ou --path")

    source = args.source_vault.expanduser().resolve()
    destination = args.destination.expanduser().resolve()
    try:
        destination.relative_to(ROOT)
    except ValueError as exc:
        parser.error("--destination doit rester dans le clone compact")
    if not source.is_dir():
        parser.error("--source-vault doit être un dossier existant")

    document = json.loads((ROOT / "catalog" / "assets.json").read_text(encoding="utf-8"))
    assets = document["assets"]
    by_path = {path: asset for asset in assets for path in asset["paths"]}
    selected: list[tuple[dict, str]] = []
    for raw in args.path:
        asset = by_path.get(raw)
        if not asset:
            parser.error(f"chemin absent du catalogue: {raw}")
        selected.append((asset, raw))
    for prefix in args.asset_id:
        normalized = prefix.removeprefix("sha256:").lower()
        matches = [asset for asset in assets if asset["sha256"].startswith(normalized)]
        if len(matches) != 1:
            parser.error(f"asset-id doit correspondre à un asset unique: {prefix} ({len(matches)} résultats)")
        selected.append((matches[0], matches[0]["paths"][0]))

    unique: dict[str, tuple[dict, str]] = {}
    for asset, raw in selected:
        unique[asset["asset_id"]] = (asset, raw)
    records = []
    for asset, raw in unique.values():
        src = (source / raw).resolve()
        try:
            src.relative_to(source)
        except ValueError as exc:
            raise SystemExit(f"source hors coffre: {raw}") from exc
        if not src.is_file():
            raise SystemExit(f"source introuvable: {raw}")
        if src.stat().st_size != asset["bytes"] or sha256(src) != asset["sha256"]:
            raise SystemExit(f"échec d’intégrité source: {raw}")
        target = destination / raw
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not args.replace:
            if target.stat().st_size == asset["bytes"] and sha256(target) == asset["sha256"]:
                status = "already_present_verified"
            else:
                raise SystemExit(f"destination existante différente (utiliser --replace): {target}")
        else:
            shutil.copy2(src, target)
            if target.stat().st_size != asset["bytes"] or sha256(target) != asset["sha256"]:
                target.unlink(missing_ok=True)
                raise SystemExit(f"échec d’intégrité après copie: {raw}")
            status = "copied_verified"
        records.append({"asset_id": asset["asset_id"], "source_path": raw, "local_path": target.relative_to(ROOT).as_posix(), "status": status})

    manifest = {
        "schema_version": 1,
        "materialized_at": datetime.now(timezone.utc).isoformat(),
        "rights_confirmed_by_operator": True,
        "assets": records,
    }
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "materialization-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
