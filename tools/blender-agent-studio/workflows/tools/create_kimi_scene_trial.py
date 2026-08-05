"""Create a deterministic, non-destructive Kimi K3 scene-trial workspace."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "workflows" / "templates" / "kimi-scene-trial"
TRIALS = ROOT / "projects" / "kimi-k3-scene-trials"


def replace_tokens(text: str, values: dict[str, object]) -> str:
    for key, value in values.items():
        token = f"__{key}__"
        text = text.replace(f'"{token}"', json.dumps(value, ensure_ascii=False))
        text = text.replace(token, str(value))
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="Identifiant slug, ex. k3-phone-desk-v001")
    parser.add_argument("--objective", required=True)
    parser.add_argument("--source-blend", default="Pulsed_3D_model.blend")
    parser.add_argument("--duration", type=float, default=8.0)
    parser.add_argument("--fps", type=int, default=24)
    args = parser.parse_args()

    if not re.fullmatch(r"k3-[a-z0-9]+(?:-[a-z0-9]+)*-v\d{3}", args.id):
        parser.error("--id doit suivre k3-objet-intention-v001")
    if not 4.0 <= args.duration <= 30.0:
        parser.error("--duration doit être entre 4 et 30 secondes")
    if args.fps not in {24, 25, 30, 50, 60}:
        parser.error("--fps doit être 24, 25, 30, 50 ou 60")
    source = (ROOT / args.source_blend).resolve()
    if not source.is_file() or source.suffix.lower() != ".blend":
        parser.error("--source-blend doit pointer vers un .blend existant dans le workspace")
    try:
        source.relative_to(ROOT)
    except ValueError:
        parser.error("--source-blend doit rester dans le workspace")

    destination = TRIALS / args.id
    if destination.exists():
        parser.error(f"le dossier existe déjà: {destination}")
    for folder in (destination, destination / "scene", destination / "diagnostics", destination / "gates", destination / "renders", destination / "iterations"):
        folder.mkdir(parents=True, exist_ok=False)

    values = {
        "TRIAL_ID": args.id,
        "OBJECTIVE": args.objective,
        "SOURCE_BLEND": str(source.relative_to(ROOT)),
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
        content = replace_tokens((TEMPLATES / source_name).read_text(encoding="utf-8"), values)
        (destination / target_name).write_text(content, encoding="utf-8")

    manifest = {
        "schema_version": 1,
        "trial_id": args.id,
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "status": "scaffolded",
        "source_blend": str(source.relative_to(ROOT)),
        "source_blend_bytes": source.stat().st_size,
        "output_root": str(destination.relative_to(ROOT)),
        "source_overwrite_allowed": False,
        "trial_blend": "scene/trial.blend",
        "preview": "renders/preview.mp4",
        "validation": "validation-report.json",
    }
    (destination / "trial-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"created": str(destination), "trial_id": args.id, "next": "complete brief.json and scene-contract.json, then validate --stage scaffold"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
