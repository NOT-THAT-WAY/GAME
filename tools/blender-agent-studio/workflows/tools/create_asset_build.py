"""Create an isolated Blender asset-build workspace without modifying source assets."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "workflows" / "templates" / "asset-build"
BUILDS = ROOT / "projects" / "asset-builds"
STYLE_PROFILES = ROOT / "knowledge" / "style-profiles"


def render(text: str, values: dict[str, Any]) -> str:
    for key, value in values.items():
        token = f"__{key}__"
        text = text.replace(f'"{token}"', json.dumps(value, ensure_ascii=False))
        text = text.replace(token, str(value))
    return text


def local_reference(raw: str) -> str:
    path = (ROOT / raw).resolve()
    try:
        relative = path.relative_to(ROOT)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("les références doivent rester dans le workspace") from exc
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"référence introuvable: {raw}")
    return str(relative)


def main() -> int:
    profiles = sorted(path.stem for path in STYLE_PROFILES.glob("*.md"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="Slug terminé par -vNNN")
    parser.add_argument("--objective", required=True)
    parser.add_argument("--style-profile", choices=profiles, default="neutral-production")
    parser.add_argument("--reference", action="append", default=[], help="Fichier de référence relatif, répétable")
    args = parser.parse_args()

    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*-v\d{3}", args.id):
        parser.error("--id doit être un slug terminé par -vNNN")
    try:
        references = [local_reference(raw) for raw in args.reference]
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
    destination = BUILDS / args.id
    if destination.exists():
        parser.error(f"le dossier existe déjà: {destination}")
    for folder in (destination, destination / "source", destination / "references", destination / "diagnostics", destination / "gates", destination / "exports"):
        folder.mkdir(parents=True, exist_ok=False)

    values = {
        "ASSET_ID": args.id,
        "OBJECTIVE": args.objective,
        "STYLE_PROFILE": args.style_profile,
        "REFERENCE_FILES": references,
    }
    mapping = {
        "brief.template.json": "brief.json",
        "asset-contract.template.json": "asset-contract.json",
        "FINAL_REVIEW.template.md": "FINAL_REVIEW.md",
        "README.template.md": "README.md",
    }
    for source_name, target_name in mapping.items():
        content = render((TEMPLATES / source_name).read_text(encoding="utf-8"), values)
        if target_name.endswith(".json"):
            json.loads(content)
        (destination / target_name).write_text(content, encoding="utf-8")

    manifest = {
        "schema_version": 1,
        "asset_id": args.id,
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "status": "scaffolded",
        "style_profile": args.style_profile,
        "references": references,
        "output_root": str(destination.relative_to(ROOT)),
        "work_blend": "source/asset.blend",
        "source_overwrite_allowed": False,
        "object_prefix": "BAS_" + re.sub(r"[^A-Z0-9]+", "_", args.id.upper()).strip("_") + "_",
    }
    (destination / "asset-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"created": str(destination), "asset_id": args.id, "next": "complete contracts, then validate --stage scaffold"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
