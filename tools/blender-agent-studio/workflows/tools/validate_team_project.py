#!/usr/bin/env python3
"""Validate team project contracts, gates, local delivery hashes and target-import evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PROJECTS = ROOT / "projects" / "team"
PROFILE_DIR = ROOT / "standards" / "profiles"
ALLOWED_TYPES = {"asset", "game-asset", "rig", "animation", "environment", "cinematic", "still", "procedural"}
PROFILE_DOMAINS = {
    "asset": {"asset"},
    "game-asset": {"game-asset"},
    "rig": {"animation"},
    "animation": {"animation"},
    "environment": {"environment"},
    "procedural": {"environment"},
    "cinematic": {"cinematic"},
    "still": {"cinematic"},
}
REQUIRED_ROLES = {
    "asset": {"master_blend", "preview", "export", "reimport_evidence"},
    "game-asset": {"master_blend", "export", "target_engine_import"},
    "rig": {"master_blend", "rig_audit", "deformation_preview"},
    "animation": {"master_blend", "playblast", "clip_manifest", "reimport_evidence"},
    "environment": {"master_blend", "performance_report", "target_engine_import"},
    "cinematic": {"master_blend", "preview", "media_probe"},
    "still": {"master_blend", "final_render", "render_settings"},
    "procedural": {"master_blend", "procedural_manifest", "performance_report"},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.is_file():
        errors.append(f"missing:{path.name}")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"invalid_json:{path.name}:{exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"not_object:{path.name}")
        return {}
    return value


def unresolved(value: Any) -> bool:
    if isinstance(value, dict):
        return any(unresolved(child) for child in value.values())
    if isinstance(value, list):
        return any(unresolved(child) for child in value)
    return isinstance(value, str) and ("UNRESOLVED" in value or "À compléter" in value or "TO_" in value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--stage", choices=("scaffold", "final"), default="scaffold")
    args = parser.parse_args()
    project_dir = args.project_dir.expanduser().resolve()
    try:
        project_dir.relative_to(PROJECTS)
    except ValueError:
        parser.error("project_dir doit rester dans projects/team/")

    errors: list[str] = []
    warnings: list[str] = []
    project = load(project_dir / "project.json", errors)
    brief = load(project_dir / "brief.json", errors)
    technical = load(project_dir / "technical-contract.json", errors)
    quality = load(project_dir / "quality-plan.json", errors)
    delivery = load(project_dir / "delivery-manifest.json", errors)
    project_id = project.get("project_id")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*-v\d{3}", str(project_id or "")):
        errors.append("project_id_invalid")
    if project_dir.name != project_id:
        errors.append("project_directory_mismatch")
    for document in (brief, technical, quality, delivery):
        if document.get("project_id") != project_id:
            errors.append("cross_file_project_id_mismatch")
    project_type = project.get("project_type")
    if project_type not in ALLOWED_TYPES:
        errors.append("project_type_invalid")
    profile_id = project.get("technical_profile")
    profile_path = PROFILE_DIR / f"{profile_id}.json"
    profile = load(profile_path, errors)
    if profile and profile.get("domain") not in PROFILE_DOMAINS.get(project_type, set()):
        errors.append("profile_domain_incompatible")
    expected_gates = set(profile.get("required_gates", []))
    actual_gates = set(quality.get("gates", {}))
    if expected_gates != actual_gates:
        errors.append("quality_gates_do_not_match_profile")
    if project.get("source_overwrite_allowed") is not False or project.get("binary_files_allowed_in_git") is not False:
        errors.append("source_or_distribution_safety_invalid")
    catalog_ids = {item["asset_id"] for item in json.loads((ROOT / "catalog" / "assets.json").read_text(encoding="utf-8"))["assets"]}
    for asset_id in project.get("catalog_asset_references", []):
        if asset_id not in catalog_ids:
            errors.append(f"catalog_reference_missing:{asset_id}")

    has_unresolved = unresolved({"brief": brief, "technical": technical})
    if has_unresolved:
        (errors if args.stage == "final" else warnings).append("contracts_contain_unresolved_values")
    if quality.get("iteration_policy") != {"one_category_at_a_time": True, "max_attempts_per_category": 3}:
        errors.append("iteration_policy_invalid")

    verified_files = 0
    if args.stage == "final":
        if project.get("status") not in {"reviewed", "released"}:
            errors.append("project_status_must_be_reviewed_or_released")
        review = project_dir / "FINAL_REVIEW.md"
        if not review.is_file() or len(review.read_text(encoding="utf-8", errors="replace")) < 500 or "UNRESOLVED" in review.read_text(encoding="utf-8", errors="replace"):
            errors.append("final_review_incomplete")
        gates = quality.get("gates", {})
        for gate, state in gates.items():
            if not isinstance(state, dict) or state.get("status") != "passed":
                errors.append(f"gate_not_passed:{gate}")
            evidence = state.get("evidence") if isinstance(state, dict) else None
            if not isinstance(evidence, list) or not evidence:
                errors.append(f"gate_evidence_missing:{gate}")
            else:
                for raw in evidence:
                    path = (ROOT / raw).resolve() if isinstance(raw, str) else None
                    if not path or ROOT not in path.parents or not path.is_file():
                        errors.append(f"gate_evidence_file_missing:{gate}:{raw}")
        critical = quality.get("critical_failures")
        if not isinstance(critical, list):
            errors.append("critical_failures_not_list")
        elif critical:
            errors.append("critical_failures_present")
        roles = set()
        for index, item in enumerate(delivery.get("files", [])):
            if not isinstance(item, dict):
                errors.append(f"delivery_file_invalid:{index}")
                continue
            roles.add(item.get("role"))
            raw = item.get("path")
            path = (ROOT / raw).resolve() if isinstance(raw, str) else None
            if not path or ROOT not in path.parents or not path.is_file():
                errors.append(f"delivery_file_missing:{raw}")
                continue
            if item.get("bytes") != path.stat().st_size:
                errors.append(f"delivery_size_mismatch:{raw}")
            elif item.get("sha256") != sha256(path):
                errors.append(f"delivery_hash_mismatch:{raw}")
            elif item.get("status") != "validated":
                errors.append(f"delivery_file_not_validated:{raw}")
            else:
                verified_files += 1
        missing_roles = REQUIRED_ROLES.get(project_type, set()) - roles
        if missing_roles:
            errors.append("delivery_roles_missing:" + ",".join(sorted(missing_roles)))
        target = delivery.get("target_validation", {})
        if target.get("status") != "passed" or not target.get("evidence"):
            errors.append("target_validation_not_passed")
        elif target.get("target") != project.get("target"):
            errors.append("target_validation_target_mismatch")
        else:
            for raw in target.get("evidence", []):
                path = (ROOT / raw).resolve() if isinstance(raw, str) else None
                if not path or ROOT not in path.parents or not path.is_file():
                    errors.append(f"target_validation_evidence_missing:{raw}")
        rights = delivery.get("rights_review", {})
        if rights.get("status") != "passed" or not str(rights.get("notes", "")).strip():
            errors.append("rights_review_not_passed")

    report = {
        "schema_version": 1,
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "project_id": project_id,
        "project_type": project_type,
        "stage": args.stage,
        "package_valid": not errors,
        "verified_delivery_files": verified_files,
        "errors": errors,
        "warnings": warnings,
    }
    if project_dir.is_dir():
        (project_dir / "validation-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
