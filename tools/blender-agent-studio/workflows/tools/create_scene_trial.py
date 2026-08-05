"""Create a deterministic, non-destructive Blender Agent Studio scene trial."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "workflows" / "templates" / "scene-trial"
TRIALS = ROOT / "projects" / "scene-trials"
STYLE_PROFILES = ROOT / "knowledge" / "style-profiles"


def render_template(text: str, values: dict[str, Any]) -> str:
    """Replace quoted JSON tokens safely, while still supporting Markdown tokens."""
    for key, value in values.items():
        token = f"__{key}__"
        text = text.replace(f'"{token}"', json.dumps(value, ensure_ascii=False))
        text = text.replace(token, str(value))
    return text


def contained_file(raw: str, suffix: str) -> Path:
    source = (ROOT / raw).resolve()
    try:
        source.relative_to(ROOT)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("le fichier doit rester dans le workspace") from exc
    if not source.is_file() or source.suffix.lower() != suffix:
        raise argparse.ArgumentTypeError(f"fichier {suffix} introuvable dans le workspace: {raw}")
    return source


def main() -> int:
    profiles = sorted(path.stem for path in STYLE_PROFILES.glob("*.md"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="Slug terminé par -vNNN, ex. studio-phone-reveal-v001")
    parser.add_argument("--objective", required=True)
    parser.add_argument("--source-blend", required=True, help="Chemin relatif d’un .blend existant")
    parser.add_argument("--style-profile", choices=profiles, default="neutral-production")
    parser.add_argument("--duration", type=float, default=8.0)
    parser.add_argument("--fps", type=int, default=24)
    args = parser.parse_args()

    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*-v\d{3}", args.id):
        parser.error("--id doit être un slug terminé par -vNNN")
    if not 4.0 <= args.duration <= 30.0:
        parser.error("--duration doit être entre 4 et 30 secondes")
    if args.fps not in {24, 25, 30, 50, 60}:
        parser.error("--fps doit être 24, 25, 30, 50 ou 60")
    try:
        source = contained_file(args.source_blend, ".blend")
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    destination = TRIALS / args.id
    if destination.exists():
        parser.error(f"le dossier existe déjà: {destination}")
    for folder in (destination, destination / "scene", destination / "diagnostics", destination / "gates", destination / "renders", destination / "iterations"):
        folder.mkdir(parents=True, exist_ok=False)

    values: dict[str, Any] = {
        "TRIAL_ID": args.id,
        "OBJECTIVE": args.objective,
        "SOURCE_BLEND": str(source.relative_to(ROOT)),
        "STYLE_PROFILE": args.style_profile,
        "DURATION": args.duration,
        "FPS": args.fps,
    }
    mapping = {
        "brief.template.json": "brief.json",
        "scene-contract.template.json": "scene-contract.json",
        "score.template.json": "score.json",
        "physical-validation.template.json": "diagnostics/physical-validation.json",
        "FINAL_REVIEW.template.md": "FINAL_REVIEW.md",
        "README.template.md": "README.md",
    }
    for source_name, target_name in mapping.items():
        content = render_template((TEMPLATES / source_name).read_text(encoding="utf-8"), values)
        if target_name.endswith(".json"):
            json.loads(content)
        target = destination / target_name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    manifest = {
        "schema_version": 2,
        "trial_id": args.id,
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "status": "scaffolded",
        "source_blend": str(source.relative_to(ROOT)),
        "source_blend_bytes": source.stat().st_size,
        "style_profile": args.style_profile,
        "output_root": str(destination.relative_to(ROOT)),
        "object_prefix": "BAS_" + re.sub(r"[^A-Z0-9]+", "_", args.id.upper()).strip("_") + "_",
        "source_overwrite_allowed": False,
        "source_copied": False,
        "trial_blend": "scene/trial.blend",
        "preview": "renders/preview.mp4",
        "validation": "validation-report.json",
    }
    (destination / "trial-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "created": str(destination),
        "trial_id": args.id,
        "style_profile": args.style_profile,
        "next": "inspect the source, explicitly copy it to scene/trial.blend, then validate --stage scaffold",
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
