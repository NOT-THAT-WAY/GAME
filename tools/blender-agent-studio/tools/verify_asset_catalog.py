#!/usr/bin/env python3
"""Validate catalog consistency and optionally re-hash every asset in a local source vault."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(path: Path, errors: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"invalid_json:{path.name}:{exc}")
        return {}


def valid_relative(raw: str) -> bool:
    path = Path(raw)
    return bool(raw) and not path.is_absolute() and ".." not in path.parts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=ROOT / "catalog")
    parser.add_argument("--source-vault", type=Path)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--output", type=Path, help="écrire le rapport JSON sans exposer le chemin du coffre")
    args = parser.parse_args()

    catalog = args.catalog.expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []
    assets_doc = load(catalog / "assets.json", errors)
    families_doc = load(catalog / "asset-families.json", errors)
    scenes_doc = load(catalog / "blender-scenes.json", errors)
    manifest = load(catalog / "catalog-manifest.json", errors)
    assets = assets_doc.get("assets", []) if isinstance(assets_doc, dict) else []
    families = families_doc.get("families", []) if isinstance(families_doc, dict) else []
    scenes = scenes_doc.get("blender_scenes", []) if isinstance(scenes_doc, dict) else []
    if assets_doc.get("schema_version") != 1:
        errors.append("assets_schema_version")
    if families_doc.get("schema_version") != 1:
        errors.append("families_schema_version")
    if scenes_doc.get("schema_version") != 1:
        errors.append("scenes_schema_version")
    if manifest.get("schema_version") != 1:
        errors.append("manifest_schema_version")
    if manifest.get("distribution_mode") != "catalog_only_no_binary_assets":
        errors.append("distribution_mode_invalid")
    if manifest.get("broken_aliases"):
        errors.append("catalog_has_broken_aliases")

    ids: set[str] = set()
    paths: dict[str, str] = {}
    kind_counts: Counter[str] = Counter()
    logical_bytes = 0
    unique_bytes = 0
    source_jobs: list[tuple[Path, str, int, str]] = []
    source = args.source_vault.expanduser().resolve() if args.source_vault else None
    if source and not source.is_dir():
        parser.error("--source-vault doit être un dossier existant")

    for index, asset in enumerate(assets):
        prefix = f"asset[{index}]"
        if not isinstance(asset, dict):
            errors.append(prefix + ":not_object")
            continue
        digest = asset.get("sha256")
        asset_id = asset.get("asset_id")
        if not isinstance(digest, str) or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            errors.append(prefix + ":sha256_invalid")
            continue
        if asset_id != "sha256:" + digest:
            errors.append(prefix + ":asset_id_mismatch")
        if asset_id in ids:
            errors.append(prefix + ":duplicate_asset_id")
        ids.add(asset_id)
        if asset.get("bundled") is not False:
            errors.append(prefix + ":must_not_be_bundled")
        size = asset.get("bytes")
        if not isinstance(size, int) or size < 0:
            errors.append(prefix + ":bytes_invalid")
            continue
        unique_bytes += size
        regular_paths = asset.get("paths")
        if not isinstance(regular_paths, list) or not regular_paths:
            errors.append(prefix + ":paths_missing")
            continue
        if asset.get("path_count") != len(regular_paths):
            errors.append(prefix + ":path_count_mismatch")
        for raw in regular_paths:
            if not isinstance(raw, str) or not valid_relative(raw):
                errors.append(prefix + ":path_invalid")
                continue
            if raw in paths:
                errors.append(prefix + f":path_duplicate:{raw}")
            paths[raw] = asset_id
            logical_bytes += size
            if source:
                source_jobs.append((source / raw, digest, size, raw))
        for alias in asset.get("aliases", []):
            if not isinstance(alias, dict) or not valid_relative(alias.get("path", "")):
                errors.append(prefix + ":alias_invalid")
            elif alias["path"] in paths:
                errors.append(prefix + f":alias_duplicate:{alias['path']}")
            else:
                paths[alias["path"]] = asset_id
        kind = asset.get("kind")
        if not isinstance(kind, str):
            errors.append(prefix + ":kind_invalid")
        else:
            kind_counts[kind] += len(regular_paths)

    if manifest.get("regular_asset_paths") != sum(kind_counts.values()):
        errors.append("manifest_regular_path_count_mismatch")
    if manifest.get("unique_content_assets") != len(assets):
        errors.append("manifest_unique_asset_count_mismatch")
    if manifest.get("logical_bytes_omitted") != logical_bytes:
        errors.append("manifest_logical_bytes_mismatch")
    if manifest.get("unique_bytes_omitted") != unique_bytes:
        errors.append("manifest_unique_bytes_mismatch")
    if manifest.get("kinds") != dict(sorted(kind_counts.items())):
        errors.append("manifest_kind_counts_mismatch")
    if manifest.get("blender_scenes") != len(scenes):
        errors.append("manifest_blender_scene_count_mismatch")
    family_ids = [item.get("family_id") for item in families if isinstance(item, dict)]
    if len(family_ids) != len(set(family_ids)):
        errors.append("duplicate_family_id")

    for filename, expected in manifest.get("catalog_file_sha256", {}).items():
        path = catalog / filename
        if not path.is_file() or sha256(path) != expected:
            errors.append(f"catalog_checksum_mismatch:{filename}")

    verified_paths = 0
    if source:
        def verify(job: tuple[Path, str, int, str]) -> str | None:
            path, expected_hash, expected_size, raw = job
            if not path.is_file():
                return f"source_missing:{raw}"
            if path.stat().st_size != expected_size:
                return f"source_size_mismatch:{raw}"
            if sha256(path) != expected_hash:
                return f"source_hash_mismatch:{raw}"
            return None

        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            for result in pool.map(verify, source_jobs):
                if result:
                    errors.append(result)
                else:
                    verified_paths += 1
        for asset in assets:
            for alias in asset.get("aliases", []):
                alias_path = source / alias["path"]
                if not alias_path.is_symlink():
                    errors.append(f"source_alias_missing:{alias['path']}")
                elif alias_path.readlink().as_posix() != alias["target"]:
                    errors.append(f"source_alias_target_mismatch:{alias['path']}")

    report = {
        "schema_version": 1,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "source_path_embedded": False,
        "catalog_valid": not errors,
        "source_vault_verified": bool(source) and not any(error.startswith("source_") for error in errors),
        "unique_assets": len(assets),
        "regular_asset_paths": sum(kind_counts.values()),
        "aliases": sum(len(asset.get("aliases", [])) for asset in assets if isinstance(asset, dict)),
        "families": len(families),
        "blender_scenes": len(scenes),
        "verified_source_paths": verified_paths,
        "logical_bytes_omitted": logical_bytes,
        "errors": errors,
        "warnings": warnings,
    }
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = args.output if args.output.is_absolute() else ROOT / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
