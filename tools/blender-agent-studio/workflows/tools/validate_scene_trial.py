"""Validate the structure, evidence and scoring of a Blender Agent Studio scene trial."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_CATEGORIES = {
    "physics_affordance": 20,
    "causality_continuity": 15,
    "composition_camera": 15,
    "motion_rhythm": 15,
    "lighting": 15,
    "materials_color_typography": 10,
    "technical_integrity": 10,
}

PHYSICAL_V2_CHECKS = {
    "environment_penetration": ("<=", 0.002),
    "support_gap": ("<=", 0.005),
    "planted_contact_drift": ("<=", 0.005),
    "swing_clearance": (">=", 0.010),
    "camera_clearance": (">=", 0.080),
}


def load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.is_file():
        errors.append(f"missing:{path.name}")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"invalid_json:{path.name}:{exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"json_not_object:{path.name}")
        return {}
    return value


def unresolved(value: Any, location: str = "") -> list[str]:
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            found.extend(unresolved(child, f"{location}.{key}" if location else key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(unresolved(child, f"{location}[{index}]"))
    elif isinstance(value, str) and ("TO_" in value or "À compléter" in value or "__" in value):
        found.append(location)
    return found


def probe_video(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size < 50_000:
        errors.append("preview_missing_or_small")
        return {}
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        errors.append("ffprobe_missing")
        return {}
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration:stream=codec_name,width,height,avg_frame_rate,nb_frames", "-of", "json", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        errors.append("preview_ffprobe_failed")
        return {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        errors.append("preview_probe_invalid_json")
        return {}


def validate_physical_v2(
    physical: dict[str, Any], trial: Path, errors: list[str], warnings: list[str]
) -> None:
    """Validate evidence structure and internal consistency, not physical success itself."""
    if physical.get("schema_version") != 2:
        errors.append("physical_evidence_schema_v2_required")
        return
    if physical.get("status") != "completed":
        errors.append("physical_evidence_not_completed")

    method = physical.get("method")
    if not isinstance(method, dict):
        errors.append("physical_method_missing")
        return
    if unresolved(method):
        errors.append("physical_method_unresolved")
    if method.get("evaluated_geometry") is not True:
        errors.append("physical_must_measure_evaluated_geometry")
    if method.get("modifiers_and_armature_applied_in_evaluation") is not True:
        errors.append("physical_must_include_deformation_stack")
    if not isinstance(method.get("coordinate_space"), str) or not method.get("coordinate_space"):
        errors.append("physical_coordinate_space_missing")
    if not isinstance(method.get("coordinate_space_source"), str) or not method.get("coordinate_space_source"):
        errors.append("physical_coordinate_space_source_missing")
    parent_mode = method.get("moving_parent_evaluated_each_frame")
    if parent_mode is not True and parent_mode != "not_applicable":
        errors.append("physical_moving_parent_evaluation_invalid")
    if method.get("sample_frame_step") != 1:
        errors.append("physical_must_sample_every_frame")
    frame_start = method.get("frame_start")
    frame_end = method.get("frame_end")
    if not isinstance(frame_start, int) or not isinstance(frame_end, int) or frame_end < frame_start:
        errors.append("physical_frame_range_invalid")
    for key in ("distance_method", "overlap_method"):
        value = method.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"physical_{key}_missing")

    semantic_pairs = physical.get("semantic_pairs")
    if not isinstance(semantic_pairs, list) or not semantic_pairs:
        errors.append("physical_semantic_pairs_missing")
    elif unresolved(semantic_pairs):
        errors.append("physical_semantic_pairs_unresolved")

    checks = physical.get("checks")
    if not isinstance(checks, dict):
        errors.append("physical_checks_invalid")
        return
    missing_checks = set(PHYSICAL_V2_CHECKS) - set(checks)
    if missing_checks:
        errors.append("physical_checks_missing:" + ",".join(sorted(missing_checks)))

    all_applicable_pass = True
    applicable_count = 0
    for name, (required_operator, default_threshold) in PHYSICAL_V2_CHECKS.items():
        check = checks.get(name)
        if not isinstance(check, dict):
            continue
        applicable = check.get("applicable")
        if not isinstance(applicable, bool):
            errors.append(f"physical_check_applicability_invalid:{name}")
            continue
        if not applicable:
            reason = check.get("not_applicable_reason")
            if not isinstance(reason, str) or not reason.strip():
                errors.append(f"physical_check_not_applicable_reason_missing:{name}")
            continue
        applicable_count += 1
        operator = check.get("operator")
        value = check.get("value_m")
        threshold = check.get("threshold_m")
        if operator != required_operator:
            errors.append(f"physical_check_operator_invalid:{name}")
        if not isinstance(value, (int, float)) or value < 0:
            errors.append(f"physical_check_value_invalid:{name}")
            all_applicable_pass = False
            continue
        if not isinstance(threshold, (int, float)) or threshold < 0:
            errors.append(f"physical_check_threshold_invalid:{name}")
            all_applicable_pass = False
            continue
        if required_operator == "<=" and threshold > default_threshold + 1e-9:
            errors.append(f"physical_threshold_weaker_than_default:{name}")
        if required_operator == ">=" and threshold < default_threshold - 1e-9:
            errors.append(f"physical_threshold_weaker_than_default:{name}")
        numeric_pass = value <= threshold if required_operator == "<=" else value >= threshold
        if check.get("passed") is not numeric_pass:
            errors.append(f"physical_check_result_contradiction:{name}")
        if not numeric_pass:
            all_applicable_pass = False
        worst_frame = check.get("worst_frame")
        outside = check.get("frames_outside_threshold")
        if not isinstance(worst_frame, int):
            errors.append(f"physical_check_worst_frame_missing:{name}")
        if not isinstance(outside, int) or outside < 0:
            errors.append(f"physical_check_outside_count_invalid:{name}")
        elif numeric_pass and outside != 0:
            errors.append(f"physical_check_outside_count_contradiction:{name}")
        elif not numeric_pass and outside == 0:
            errors.append(f"physical_check_outside_count_contradiction:{name}")
        evidence = check.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"physical_check_evidence_missing:{name}")
        elif not any(isinstance(item, str) and (trial / item).exists() for item in evidence):
            errors.append(f"physical_check_evidence_path_missing:{name}")

    if applicable_count == 0:
        errors.append("physical_no_applicable_checks")
    if physical.get("passed") is not all_applicable_pass:
        errors.append("physical_overall_result_contradiction")
    critical = physical.get("critical_failures")
    if not isinstance(critical, list):
        errors.append("physical_critical_failures_not_list")
    elif all_applicable_pass and critical:
        errors.append("physical_passed_with_critical_failures")
    elif not all_applicable_pass and not critical:
        errors.append("physical_failed_without_critical_failure")

    proof_views = physical.get("proof_views")
    if not isinstance(proof_views, list) or not proof_views:
        errors.append("physical_proof_views_missing")
    elif not any(isinstance(item, str) and (trial / item).exists() for item in proof_views):
        errors.append("physical_proof_view_path_missing")

    if not isinstance(physical.get("limitations"), list):
        warnings.append("physical_limitations_should_be_list")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trial_dir", type=Path)
    parser.add_argument("--stage", choices=("scaffold", "final"), default="scaffold")
    args = parser.parse_args()

    trial = args.trial_dir.expanduser().resolve()
    try:
        trial.relative_to(ROOT / "projects" / "scene-trials")
    except ValueError:
        parser.error("trial_dir doit rester dans projects/scene-trials/")

    errors: list[str] = []
    warnings: list[str] = []
    for folder in ("scene", "diagnostics", "gates", "renders", "iterations"):
        if not (trial / folder).is_dir():
            errors.append(f"missing_directory:{folder}")

    brief = load_json(trial / "brief.json", errors)
    contract = load_json(trial / "scene-contract.json", errors)
    score = load_json(trial / "score.json", errors)
    manifest = load_json(trial / "trial-manifest.json", errors)
    trial_id = manifest.get("trial_id") or brief.get("trial_id")
    if not trial_id or trial.name != trial_id:
        errors.append("trial_id_mismatch")
    if brief.get("trial_id") != trial_id or contract.get("trial_id") != trial_id or score.get("trial_id") != trial_id:
        errors.append("cross_file_trial_id_mismatch")

    duration = brief.get("duration_seconds")
    fps = brief.get("fps")
    if not isinstance(duration, (int, float)) or not 4 <= duration <= 30:
        errors.append("brief_duration_out_of_range")
    if fps not in {24, 25, 30, 50, 60}:
        errors.append("brief_fps_invalid")
    categories = score.get("categories", {})
    if set(categories) != set(EXPECTED_CATEGORIES):
        errors.append("score_categories_invalid")
    weights = {name: value.get("weight") for name, value in categories.items() if isinstance(value, dict)}
    if weights != EXPECTED_CATEGORIES:
        errors.append("score_weights_invalid")
    if sum(value for value in weights.values() if isinstance(value, (int, float))) != 100:
        errors.append("score_weights_not_100")

    unresolved_fields = unresolved({"brief": brief, "contract": contract})
    if unresolved_fields:
        message = "unresolved_fields:" + ",".join(unresolved_fields[:20])
        (warnings if args.stage == "scaffold" else errors).append(message)

    video_probe = {}
    calculated_score = None
    expected_verdict = None
    if args.stage == "final":
        required = [
            trial / "scene" / "trial.blend",
            trial / "diagnostics" / "scene-audit.json",
            trial / "diagnostics" / "physical-validation.json",
            trial / "gates" / "contact-sheet.jpg",
            trial / "gates" / "lighting-gate-manifest.json",
            trial / "shot-manifest.json",
            trial / "renders" / "preview.mp4",
            trial / "FINAL_REVIEW.md",
        ]
        for path in required:
            if not path.is_file():
                errors.append(f"final_artifact_missing:{path.relative_to(trial)}")
        blend = trial / "scene" / "trial.blend"
        if blend.is_file() and blend.stat().st_size < 100_000:
            errors.append("trial_blend_too_small")
        load_json(trial / "diagnostics" / "scene-audit.json", errors)
        physical = load_json(trial / "diagnostics" / "physical-validation.json", errors)
        evidence_version = contract.get("validation", {}).get("physical_evidence_schema_version")
        if evidence_version == 2:
            validate_physical_v2(physical, trial, errors, warnings)
        else:
            warnings.append("legacy_physical_evidence_schema_not_v2")
        lighting_gate = load_json(trial / "gates" / "lighting-gate-manifest.json", errors)
        if lighting_gate and len(lighting_gate.get("renders", [])) != 6:
            errors.append("lighting_gate_must_have_6_renders")
        if lighting_gate:
            missing_light_renders = []
            for item in lighting_gate.get("renders", []):
                raw = item.get("path") if isinstance(item, dict) else None
                if not raw:
                    missing_light_renders.append("missing_path")
                    continue
                path = Path(raw)
                if not path.is_absolute():
                    path = trial / path
                if not path.is_file():
                    missing_light_renders.append(str(raw))
            if missing_light_renders:
                errors.append("lighting_gate_render_missing:" + ",".join(missing_light_renders[:6]))
        shot = load_json(trial / "shot-manifest.json", errors)
        if shot and not (shot.get("camera") or shot.get("camera_name")):
            errors.append("shot_manifest_camera_missing")
        contact_sheet = trial / "gates" / "contact-sheet.jpg"
        if contact_sheet.is_file() and contact_sheet.stat().st_size < 10_000:
            errors.append("contact_sheet_too_small")
        review = trial / "FINAL_REVIEW.md"
        if review.is_file():
            text = review.read_text(encoding="utf-8", errors="replace")
            if len(text) < 500 or "unscored" in text or "À compléter" in text:
                errors.append("final_review_incomplete")

        video_probe = probe_video(trial / "renders" / "preview.mp4", errors)
        if video_probe and isinstance(duration, (int, float)):
            actual = float(video_probe.get("format", {}).get("duration", 0) or 0)
            if abs(actual - float(duration)) > max(0.5, 1 / max(int(fps or 1), 1)):
                errors.append(f"preview_duration_mismatch:{actual:.3f}!={duration}")

        if score.get("status") != "completed":
            errors.append("score_not_completed")
        weighted = 0.0
        for name, weight in EXPECTED_CATEGORIES.items():
            value = categories.get(name, {}).get("score")
            evidence = categories.get(name, {}).get("evidence")
            if not isinstance(value, (int, float)) or not 0 <= value <= 100:
                errors.append(f"category_score_invalid:{name}")
                continue
            if not isinstance(evidence, list) or not evidence:
                errors.append(f"category_evidence_missing:{name}")
            elif not any(isinstance(item, str) and (trial / item).exists() for item in evidence):
                errors.append(f"category_evidence_path_missing:{name}")
            weighted += float(value) * weight / 100.0
        critical = score.get("critical_failures", [])
        if not isinstance(critical, list):
            errors.append("critical_failures_not_list")
            critical = ["invalid"]
        physical_critical = {
            "collision_or_environment_traversal",
            "levitation_or_missing_required_support",
            "impossible_articulation_or_wrong_affordance",
            "unmotivated_drift_or_contact_slip",
        }
        if physical and physical.get("passed") is False and not physical_critical.intersection(critical):
            errors.append("failed_physical_validation_missing_critical_failure")
        if evidence_version == 2:
            physical_failures = physical.get("critical_failures", [])
            if isinstance(physical_failures, list) and set(physical_failures) != physical_critical.intersection(critical):
                errors.append("physical_and_score_critical_failures_mismatch")
        calculated_score = round(min(weighted, 49.0) if critical else weighted, 2)
        declared = score.get("overall_score")
        if not isinstance(declared, (int, float)) or abs(float(declared) - calculated_score) > 0.11:
            errors.append(f"overall_score_mismatch:{declared}!={calculated_score}")
        expected_verdict = "ship" if not critical and calculated_score >= 85 else "revise" if not critical and calculated_score >= 70 else "reject"
        if score.get("verdict") != expected_verdict:
            errors.append(f"verdict_mismatch:{score.get('verdict')}!={expected_verdict}")

    report = {
        "schema_version": 1,
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "trial_id": trial_id,
        "stage": args.stage,
        "package_valid": not errors,
        "artistic_verdict": score.get("verdict"),
        "calculated_score": calculated_score,
        "expected_verdict": expected_verdict,
        "errors": errors,
        "warnings": warnings,
        "video_probe": video_probe,
    }
    if trial.is_dir():
        (trial / "validation-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
