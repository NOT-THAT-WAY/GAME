#!/usr/bin/env python3
"""Build content-addressed JSON catalogs for assets kept outside the compact repository."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
KINDS = {
    "geometry": {".blend", ".blend1", ".fbx", ".glb", ".gltf", ".obj", ".stl", ".usd", ".usda", ".usdc", ".usdz", ".abc", ".ply"},
    "image": {".png", ".jpg", ".jpeg", ".webp", ".gif", ".exr", ".hdr", ".tif", ".tiff", ".tga", ".bmp", ".psd"},
    "video": {".mp4", ".mov", ".m4v", ".webm", ".mkv"},
    "audio": {".wav", ".mp3", ".aif", ".aiff", ".flac", ".ogg", ".m4a", ".aac"},
    "simulation": {".vdb", ".npy", ".sbsar"},
    "archive": {".zip", ".7z"},
}
EXTENSION_KIND = {suffix: kind for kind, suffixes in KINDS.items() for suffix in suffixes}
SKIP_TOP_LEVEL = {".git", "third_party", "vendor"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_metadata(path: Path) -> dict[str, Any]:
    try:
        from PIL import Image

        with Image.open(path) as image:
            return {"width": image.width, "height": image.height, "mode": image.mode, "format": image.format}
    except Exception as exc:
        return {"probe_error": str(exc)}


def media_metadata(path: Path) -> dict[str, Any]:
    try:
        process = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries",
                "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels",
                "-of", "json", str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        payload = json.loads(process.stdout)
    except Exception as exc:
        return {"probe_error": str(exc)}
    result: dict[str, Any] = {}
    duration = payload.get("format", {}).get("duration")
    if duration is not None:
        try:
            result["duration_seconds"] = round(float(duration), 6)
        except (TypeError, ValueError):
            pass
    streams = []
    for stream in payload.get("streams", []):
        item = {key: stream[key] for key in ("codec_type", "codec_name", "width", "height", "sample_rate", "channels") if key in stream}
        rate = stream.get("r_frame_rate")
        if rate and rate != "0/0":
            try:
                item["fps"] = round(float(Fraction(rate)), 6)
            except (ValueError, ZeroDivisionError):
                item["fps_raw"] = rate
        streams.append(item)
    result["streams"] = streams
    return result


def role_for(path: str, kind: str) -> str:
    if path.startswith("asset_library/"):
        return "released_library_asset"
    if path.startswith("asset_sources/"):
        return "source_asset_or_reference"
    if path.startswith("assets_blender/") or path.startswith("_ALL-IMAGES"):
        return "visual_reference_or_generation"
    if path.startswith("knowledge/tutorials/"):
        return "tutorial_evidence"
    if path.startswith("renders/"):
        return "render_output_or_gate"
    if path.startswith("projects/"):
        return "project_source_or_evidence"
    if kind == "geometry":
        return "blender_source_or_interchange"
    return "uncategorized_asset"


def redistribution_for(path: str) -> str:
    if path.startswith("knowledge/tutorials/"):
        return "unknown_verify_before_publication"
    if path.startswith("asset_sources/"):
        return "owner_review"
    if path.startswith("assets_blender/") or path.startswith("projects/") or path.startswith("renders/"):
        return "owner_review"
    return "owner_review"


def family_root(path: str) -> str:
    parts = Path(path).parts
    if not parts:
        return "."
    if parts[0] in {"projects", "renders"} and len(parts) >= 2:
        return "/".join(parts[:2])
    if parts[0] == "knowledge" and len(parts) >= 3 and parts[1] == "tutorials":
        return "/".join(parts[:3])
    if parts[0] in {"asset_library", "asset_sources"} and len(parts) >= 2:
        return "/".join(parts[:2])
    if parts[0] == "assets_blender" and len(parts) >= 3 and parts[1] == "_gen-runs":
        return "/".join(parts[:3])
    return parts[0]


def inspect_regular(item: tuple[Path, str, str]) -> dict[str, Any]:
    path, relative, kind = item
    size = path.stat().st_size
    digest = sha256(path)
    metadata: dict[str, Any] = {}
    if kind == "image":
        metadata = image_metadata(path)
    elif kind in {"video", "audio"}:
        metadata = media_metadata(path)
    return {
        "path": relative,
        "kind": kind,
        "extension": path.suffix.lower(),
        "bytes": size,
        "sha256": digest,
        "metadata": metadata,
    }


def load_blend_report(path: Path | None) -> dict[str, dict[str, Any]]:
    if not path or not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {item["path"]: item for item in payload.get("files", []) if isinstance(item, dict) and item.get("path")}


def write_json(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return sha256(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-vault", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "catalog")
    parser.add_argument("--blend-report", type=Path)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 4))
    args = parser.parse_args()

    source = args.source_vault.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not source.is_dir():
        parser.error("--source-vault doit être un dossier existant")
    if output == source or source in output.parents:
        parser.error("le catalogue ne doit pas être écrit dans le coffre source")

    regular: list[tuple[Path, str, str]] = []
    aliases: list[dict[str, str]] = []
    broken_aliases: list[dict[str, str]] = []
    for current, dirs, names in os.walk(source, followlinks=False):
        current_path = Path(current)
        relative_dir = current_path.relative_to(source)
        if relative_dir == Path("."):
            dirs[:] = [name for name in dirs if name not in SKIP_TOP_LEVEL]
        else:
            dirs[:] = [name for name in dirs if name not in {".git", "__pycache__"}]
        for name in names:
            path = current_path / name
            kind = EXTENSION_KIND.get(path.suffix.lower())
            if not kind:
                continue
            relative = path.relative_to(source).as_posix()
            if path.is_symlink():
                target = os.readlink(path)
                resolved = path.resolve(strict=False)
                item = {"path": relative, "target": target}
                if not resolved.is_file() or source not in resolved.parents:
                    broken_aliases.append(item)
                else:
                    aliases.append(item)
                continue
            if path.is_file():
                regular.append((path, relative, kind))

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        inspected = list(pool.map(inspect_regular, regular))

    groups: dict[str, dict[str, Any]] = {}
    path_to_digest: dict[str, str] = {}
    for item in inspected:
        digest = item.pop("sha256")
        relative = item.pop("path")
        path_to_digest[relative] = digest
        entry = groups.setdefault(
            digest,
            {
                "asset_id": "sha256:" + digest,
                "sha256": digest,
                "bytes": item["bytes"],
                "kind": item["kind"],
                "extensions": set(),
                "paths": [],
                "aliases": [],
                "roles": set(),
                "redistribution_statuses": set(),
                "metadata": item["metadata"],
                "bundled": False,
            },
        )
        entry["extensions"].add(item["extension"])
        entry["paths"].append(relative)
        entry["roles"].add(role_for(relative, item["kind"]))
        entry["redistribution_statuses"].add(redistribution_for(relative))

    for alias in aliases:
        resolved_relative = (source / alias["path"]).resolve().relative_to(source).as_posix()
        digest = path_to_digest.get(resolved_relative)
        if digest and digest in groups:
            groups[digest]["aliases"].append(alias)
        else:
            broken_aliases.append(alias | {"reason": "target_not_cataloged"})

    assets = []
    for entry in groups.values():
        entry["extensions"] = sorted(entry["extensions"])
        entry["paths"] = sorted(entry["paths"])
        entry["aliases"] = sorted(entry["aliases"], key=lambda item: item["path"])
        entry["roles"] = sorted(entry["roles"])
        entry["redistribution_statuses"] = sorted(entry["redistribution_statuses"])
        entry["path_count"] = len(entry["paths"])
        assets.append(entry)
    assets.sort(key=lambda item: (item["kind"], item["paths"][0]))

    family_entries: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"paths": 0, "logical_bytes": 0, "asset_ids": set(), "kinds": Counter(), "extensions": Counter()}
    )
    for asset in assets:
        for relative in asset["paths"]:
            family = family_entries[family_root(relative)]
            family["paths"] += 1
            family["logical_bytes"] += asset["bytes"]
            family["asset_ids"].add(asset["asset_id"])
            family["kinds"][asset["kind"]] += 1
            family["extensions"][Path(relative).suffix.lower()] += 1
    families = []
    for root, item in sorted(family_entries.items()):
        unique_bytes = sum(groups[asset_id.split(":", 1)[1]]["bytes"] for asset_id in item["asset_ids"])
        families.append(
            {
                "family_id": root.replace("/", ":"),
                "source_prefix": root,
                "path_count": item["paths"],
                "unique_asset_count": len(item["asset_ids"]),
                "logical_bytes": item["logical_bytes"],
                "unique_bytes": unique_bytes,
                "kinds": dict(sorted(item["kinds"].items())),
                "extensions": dict(sorted(item["extensions"].items())),
                "bundled": False,
            }
        )

    blend_report = load_blend_report(args.blend_report)
    blender_scenes = []
    for asset in assets:
        blend_paths = [path for path in asset["paths"] if Path(path).suffix.lower() in {".blend", ".blend1"}]
        for relative in blend_paths:
            report = dict(blend_report.get(relative, {}))
            report.pop("path", None)
            report.pop("size", None)
            blender_scenes.append(
                {
                    "path": relative,
                    "asset_id": asset["asset_id"],
                    "bytes": asset["bytes"],
                    "bundled": False,
                    "audit": report or {"status": "not_audited"},
                }
            )
    blender_scenes.sort(key=lambda item: item["path"])

    counts = Counter(item["kind"] for item in inspected)
    logical_bytes = sum(item["bytes"] for item in inspected)
    unique_bytes = sum(item["bytes"] for item in assets)
    assets_payload = {"schema_version": 1, "source_label": "BLENDER_ASSET_VAULT", "assets": assets}
    families_payload = {"schema_version": 1, "families": families}
    scenes_payload = {"schema_version": 1, "blender_scenes": blender_scenes}
    file_hashes = {
        "assets.json": write_json(output / "assets.json", assets_payload),
        "asset-families.json": write_json(output / "asset-families.json", families_payload),
        "blender-scenes.json": write_json(output / "blender-scenes.json", scenes_payload),
    }
    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_label": "BLENDER_ASSET_VAULT",
        "source_path_embedded": False,
        "distribution_mode": "catalog_only_no_binary_assets",
        "regular_asset_paths": len(inspected),
        "symlink_aliases": len(aliases),
        "broken_aliases": broken_aliases,
        "unique_content_assets": len(assets),
        "logical_bytes_omitted": logical_bytes,
        "unique_bytes_omitted": unique_bytes,
        "duplicate_bytes_not_repeated": logical_bytes - unique_bytes,
        "kinds": dict(sorted(counts.items())),
        "blender_scenes": len(blender_scenes),
        "catalog_file_sha256": file_hashes,
        "verification": {
            "content_sha256": True,
            "image_metadata": True,
            "ffprobe_media_metadata": True,
            "blend_audit_imported": bool(blend_report),
            "assets_bundled": False,
        },
    }
    write_json(output / "catalog-manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if not broken_aliases else 2


if __name__ == "__main__":
    raise SystemExit(main())
