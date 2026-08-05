#!/usr/bin/env python3
"""Create a lightweight team project contract plus an ignored local binary workspace."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PROJECTS = ROOT / "projects" / "team"
LOCAL_WORK = ROOT / "local_work"
PROFILE_DIR = ROOT / "standards" / "profiles"
STYLE_DIR = ROOT / "knowledge" / "style-profiles"
TYPE_DEFAULTS = {
    "asset": "asset-general",
    "game-asset": "game-gltf",
    "rig": "rig-animation",
    "animation": "rig-animation",
    "environment": "environment",
    "cinematic": "cinematic",
    "still": "cinematic",
    "procedural": "environment",
}
TYPE_REQUIREMENTS = {
    "asset": ["dimensions", "identity", "topology", "uv", "materials", "pivot", "exports"],
    "game-asset": ["engine_version", "platform", "triangles_per_lod", "collision", "uv", "textures", "pivot", "exports"],
    "rig": ["skeleton", "bone_axes", "joint_limits", "weight_limits", "export_skeleton"],
    "animation": ["fps", "clips", "contacts", "root_motion", "loop_policy", "export_sampling"],
    "environment": ["metric_grid", "navigation", "modular_rules", "collision", "performance_budgets", "engine_import"],
    "cinematic": ["fps", "duration", "shots", "camera", "color_management", "render_target", "codec"],
    "still": ["camera", "resolution", "color_management", "render_engine", "samples", "delivery_format"],
    "procedural": ["seed", "node_groups", "inputs", "instance_budget", "realization_policy", "bake_plan"],
}


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def catalog_ids() -> list[str]:
    path = ROOT / "catalog" / "assets.json"
    if not path.is_file():
        return []
    return [item["asset_id"] for item in json.loads(path.read_text(encoding="utf-8"))["assets"]]


def resolve_asset_id(raw: str, ids: list[str]) -> str:
    prefix = raw.removeprefix("sha256:").lower()
    matches = [asset_id for asset_id in ids if asset_id.split(":", 1)[1].startswith(prefix)]
    if len(matches) != 1:
        raise argparse.ArgumentTypeError(f"référence asset ambiguë ou absente: {raw} ({len(matches)} résultats)")
    return matches[0]


def main() -> int:
    profiles = {path.stem: json.loads(path.read_text(encoding="utf-8")) for path in PROFILE_DIR.glob("*.json")}
    styles = sorted(path.stem for path in STYLE_DIR.glob("*.md"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="slug terminé par -vNNN")
    parser.add_argument("--type", required=True, choices=sorted(TYPE_DEFAULTS))
    parser.add_argument("--objective", required=True)
    parser.add_argument("--target", required=True, help="usage, moteur, plateforme ou média cible")
    parser.add_argument("--profile", choices=sorted(profiles))
    parser.add_argument("--style-profile", choices=styles, default="neutral-production")
    parser.add_argument("--owner", default="unassigned")
    parser.add_argument("--reference-asset-id", action="append", default=[])
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*-v\d{3}", args.id):
        parser.error("--id doit être un slug terminé par -vNNN")
    profile_id = args.profile or TYPE_DEFAULTS[args.type]
    profile = profiles[profile_id]
    ids = catalog_ids()
    try:
        references = [resolve_asset_id(raw, ids) for raw in args.reference_asset_id]
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    project = PROJECTS / args.id
    local = LOCAL_WORK / args.id
    if project.exists() or local.exists():
        parser.error("le projet ou son workspace local existe déjà")
    project.mkdir(parents=True)
    (project / "evidence").mkdir()
    for name in ("source", "references", "work", "diagnostics", "gates", "exports", "renders"):
        (local / name).mkdir(parents=True)

    created = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    prefix = "BAS_" + re.sub(r"[^A-Z0-9]+", "_", args.id.upper()).strip("_") + "_"
    project_doc = {
        "schema_version": 1,
        "project_id": args.id,
        "project_type": args.type,
        "status": "scaffolded",
        "owner": args.owner,
        "objective": args.objective,
        "target": args.target,
        "technical_profile": profile_id,
        "style_profile": args.style_profile,
        "created_at": created,
        "object_prefix": prefix,
        "catalog_asset_references": references,
        "local_work_root": f"local_work/{args.id}",
        "source_overwrite_allowed": False,
        "binary_files_allowed_in_git": False,
    }
    brief = {
        "schema_version": 1,
        "project_id": args.id,
        "objective": args.objective,
        "target": args.target,
        "audience_or_player": "UNRESOLVED",
        "usage_and_viewing_distance": "UNRESOLVED",
        "deliverables": [],
        "identity_invariants": [],
        "physical_invariants": [],
        "explicit_non_goals": [],
        "acceptance_criteria": [],
    }
    technical = {
        "schema_version": 1,
        "project_id": args.id,
        "project_type": args.type,
        "profile": profile_id,
        "common": {
            "blender_units": "meters",
            "coordinate_frame": "UNRESOLVED",
            "dimensions_m": "UNRESOLVED",
            "origin_and_pivot": "UNRESOLVED",
            "supports_contacts_and_colliders": "UNRESOLVED",
            "source_provenance": references,
        },
        "domain": {field: "UNRESOLVED" for field in TYPE_REQUIREMENTS[args.type]},
        "budgets": {field: "UNRESOLVED" for field in profile.get("budgets_must_be_declared", [])},
        "delivery": {"formats": [], "target_importer": "UNRESOLVED", "version": "UNRESOLVED"},
    }
    gates = profile.get("required_gates", [])
    quality = {
        "schema_version": 1,
        "project_id": args.id,
        "iteration_policy": {"one_category_at_a_time": True, "max_attempts_per_category": 3},
        "gates": {gate: {"status": "pending", "evidence": [], "notes": ""} for gate in gates},
        "critical_failures": [],
        "human_review_required": True,
    }
    delivery = {
        "schema_version": 1,
        "project_id": args.id,
        "files": [],
        "target_validation": {"status": "pending", "target": args.target, "evidence": []},
        "rights_review": {"status": "pending", "notes": ""},
    }
    for name, payload in (
        ("project.json", project_doc),
        ("brief.json", brief),
        ("technical-contract.json", technical),
        ("quality-plan.json", quality),
        ("delivery-manifest.json", delivery),
    ):
        write_json(project / name, payload)
    (project / "evidence" / "README.md").write_text(
        "# Preuves textuelles\n\nPlacer ici les audits et rapports JSON/Markdown. Les images, vidéos et fichiers 3D restent dans `local_work/` et sont référencés par hash.\n",
        encoding="utf-8",
    )
    (project / "FINAL_REVIEW.md").write_text(
        f"# Revue finale — {args.id}\n\n## Verdict\n\nUNRESOLVED\n\n## Résultat par rapport au brief\n\nUNRESOLVED\n\n## Preuves techniques, physiques et visuelles\n\nUNRESOLVED\n\n## Limites et décision humaine\n\nUNRESOLVED\n",
        encoding="utf-8",
    )
    print(json.dumps({"created": display_path(project), "local_work": display_path(local), "profile": profile_id, "next": "complete contracts then validate --stage scaffold"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
