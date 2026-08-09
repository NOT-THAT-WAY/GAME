#!/usr/bin/env python3
"""Validate DVC restore and Blender-to-Unity evidence reports without external dependencies."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
UNITY_VERSION_FILE = REPO_ROOT / "config" / "toolchain.env"
UNITY_PROFILE_FILE = (
    REPO_ROOT
    / "tools"
    / "blender-agent-studio"
    / "standards"
    / "profiles"
    / "game-unity.json"
)
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
GIT_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
PROJECT_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*-v\d{3}$")
RESULTS = {"PASS", "FAIL", "BLOCKED"}


def expected_unity_version() -> str:
    for line in UNITY_VERSION_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("UNITY_VERSION="):
            return line.split("=", 1)[1]
    raise RuntimeError("UNITY_VERSION missing from config/toolchain.env")


def required_unity_gates() -> set[str]:
    profile = json.loads(UNITY_PROFILE_FILE.read_text(encoding="utf-8"))
    return set(profile["required_gates"])


def unresolved(value: Any) -> bool:
    return not isinstance(value, str) or not value.strip() or "UNRESOLVED" in value


def evidence_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(not unresolved(item) for item in value)


def valid_utc(value: Any) -> bool:
    if unresolved(value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def validate_common(report: dict[str, Any], errors: list[str]) -> None:
    if report.get("schemaVersion") != 1:
        errors.append("schemaVersion_must_be_1")
    if not valid_utc(report.get("startedAtUtc")):
        errors.append("startedAtUtc_invalid")
    if not valid_utc(report.get("finishedAtUtc")):
        errors.append("finishedAtUtc_invalid")
    if valid_utc(report.get("startedAtUtc")) and valid_utc(report.get("finishedAtUtc")):
        started = datetime.fromisoformat(report["startedAtUtc"].replace("Z", "+00:00"))
        finished = datetime.fromisoformat(report["finishedAtUtc"].replace("Z", "+00:00"))
        if finished < started:
            errors.append("finishedAtUtc_precedes_startedAtUtc")
    if not GIT_COMMIT_PATTERN.fullmatch(str(report.get("sourceGitCommit", ""))):
        errors.append("sourceGitCommit_invalid")
    if not isinstance(report.get("sourceDirtyWorktree"), bool):
        errors.append("sourceDirtyWorktree_must_be_boolean")
    for field in ("sessionId", "machineAlias"):
        if unresolved(report.get(field)):
            errors.append(f"{field}_missing")


def validate_dvc(report: dict[str, Any], errors: list[str]) -> None:
    result = report.get("result")
    if result not in RESULTS:
        errors.append("result_invalid")
        return
    if report.get("testId") not in {"DVC-02", "DVC-03"}:
        errors.append("testId_invalid")
    if report.get("platform") not in {"macos", "windows"}:
        errors.append("platform_invalid")
    if report.get("remoteAlias") != "assets":
        errors.append("remoteAlias_must_be_assets")
    if result == "BLOCKED" and not evidence_list(report.get("blockers")):
        errors.append("blocked_result_requires_blockers")
    if result == "FAIL" and not evidence_list(report.get("failures")):
        errors.append("failed_result_requires_failures")
    if result != "PASS":
        return

    if report.get("sourceDirtyWorktree") is not False:
        errors.append("pass_requires_clean_worktree")
    if report.get("blockers") or report.get("failures"):
        errors.append("pass_cannot_have_blockers_or_failures")
    if unresolved(report.get("dvcVersion")):
        errors.append("dvcVersion_missing")

    cache = report.get("cachePreparation")
    if not isinstance(cache, dict) or cache.get("mode") != "empty-cache":
        errors.append("pass_requires_empty_cache")
    elif unresolved(cache.get("proof")):
        errors.append("empty_cache_proof_missing")

    pull = report.get("pull")
    if not isinstance(pull, dict) or pull.get("exitCode") != 0:
        errors.append("dvc_pull_did_not_succeed")
    elif unresolved(pull.get("target")) or unresolved(pull.get("log")):
        errors.append("dvc_pull_evidence_incomplete")

    artifacts = report.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("restored_artifacts_missing")
    else:
        for index, artifact in enumerate(artifacts):
            if not isinstance(artifact, dict):
                errors.append(f"artifact_{index}_invalid")
                continue
            expected = artifact.get("expectedSha256")
            actual = artifact.get("actualSha256")
            if unresolved(artifact.get("path")):
                errors.append(f"artifact_{index}_path_missing")
            if not SHA256_PATTERN.fullmatch(str(expected or "")):
                errors.append(f"artifact_{index}_expected_hash_invalid")
            if not SHA256_PATTERN.fullmatch(str(actual or "")):
                errors.append(f"artifact_{index}_actual_hash_invalid")
            if expected != actual:
                errors.append(f"artifact_{index}_hash_mismatch")
            if not isinstance(artifact.get("bytes"), int) or artifact["bytes"] <= 0:
                errors.append(f"artifact_{index}_size_invalid")

    if report.get("testId") == "DVC-03":
        storage = report.get("storageControls")
        if not isinstance(storage, dict):
            errors.append("storage_controls_missing")
        else:
            if storage.get("objectVersioning") != "confirmed":
                errors.append("dvc03_requires_object_versioning_confirmation")
            if storage.get("secondCopy") != "confirmed":
                errors.append("dvc03_requires_second_copy_confirmation")
            if not evidence_list(storage.get("evidence")):
                errors.append("storage_control_evidence_missing")


def validate_gate(name: str, gate: Any, errors: list[str]) -> None:
    if not isinstance(gate, dict):
        errors.append(f"gate_{name}_invalid")
        return
    status = gate.get("status")
    if status not in {"PASS", "FAIL", "BLOCKED", "NOT_APPLICABLE"}:
        errors.append(f"gate_{name}_status_invalid")
    elif status == "PASS" and not evidence_list(gate.get("evidence")):
        errors.append(f"gate_{name}_pass_requires_evidence")
    elif status == "NOT_APPLICABLE" and unresolved(gate.get("notes")):
        errors.append(f"gate_{name}_not_applicable_requires_notes")


def validate_blender_unity(report: dict[str, Any], errors: list[str]) -> None:
    technical_result = report.get("technicalResult")
    if technical_result not in RESULTS:
        errors.append("technicalResult_invalid")
        return
    if not PROJECT_ID_PATTERN.fullmatch(str(report.get("projectId", ""))):
        errors.append("projectId_invalid")
    if unresolved(report.get("assetId")):
        errors.append("assetId_missing")
    if technical_result == "BLOCKED" and not evidence_list(report.get("blockers")):
        errors.append("blocked_result_requires_blockers")
    if technical_result == "FAIL" and not evidence_list(report.get("failures")):
        errors.append("failed_result_requires_failures")

    gates = report.get("gates")
    if not isinstance(gates, dict):
        errors.append("gates_missing")
        gates = {}
    required_gates = required_unity_gates()
    missing_gates = required_gates - set(gates)
    extra_gates = set(gates) - required_gates
    if missing_gates:
        errors.append("required_gates_missing:" + ",".join(sorted(missing_gates)))
    if extra_gates:
        errors.append("unknown_gates:" + ",".join(sorted(extra_gates)))
    for name, gate in gates.items():
        validate_gate(name, gate, errors)

    delivery = report.get("deliveryDisposition")
    if delivery not in {"SHIP", "PROTOTYPE_ONLY", "REJECT", "BLOCKED"}:
        errors.append("deliveryDisposition_invalid")

    if technical_result != "PASS":
        if delivery in {"SHIP", "PROTOTYPE_ONLY"}:
            errors.append("delivery_cannot_pass_when_technical_result_is_not_pass")
        return

    if report.get("sourceDirtyWorktree") is not False:
        errors.append("pass_requires_clean_worktree")
    if report.get("blockers") or report.get("failures"):
        errors.append("pass_cannot_have_blockers_or_failures")
    if report.get("criticalFailures"):
        errors.append("pass_cannot_have_critical_failures")

    source = report.get("source")
    if not isinstance(source, dict):
        errors.append("source_missing")
        source = {}
    if source.get("masterStatus") != "available":
        errors.append("pass_requires_available_master")
    if not SHA256_PATTERN.fullmatch(str(source.get("masterSha256", ""))):
        errors.append("master_hash_invalid")
    if unresolved(source.get("blenderVersion")):
        errors.append("blender_version_missing")

    exported = report.get("export")
    if not isinstance(exported, dict):
        errors.append("export_missing")
        exported = {}
    if not SHA256_PATTERN.fullmatch(str(exported.get("sha256", ""))):
        errors.append("export_hash_invalid")
    if not isinstance(exported.get("bytes"), int) or exported.get("bytes", 0) <= 0:
        errors.append("export_size_invalid")
    if unresolved(exported.get("path")) or unresolved(exported.get("settingsEvidence")):
        errors.append("export_evidence_incomplete")
    reimport = exported.get("independentReimport")
    if not isinstance(reimport, dict) or reimport.get("status") != "PASS" or not evidence_list(reimport.get("evidence")):
        errors.append("independent_reimport_not_proven")

    unity = report.get("unityImport")
    if not isinstance(unity, dict):
        errors.append("unity_import_missing")
        unity = {}
    if unity.get("performed") is not True:
        errors.append("unity_target_import_not_performed")
    if unity.get("unityVersion") != expected_unity_version():
        errors.append("unity_version_mismatch")
    if unity.get("platform") not in {"macos", "windows"}:
        errors.append("unity_platform_invalid")
    if not SHA256_PATTERN.fullmatch(str(unity.get("assetSha256", ""))):
        errors.append("unity_asset_hash_invalid")
    if unresolved(unity.get("assetPath")) or unresolved(unity.get("importerLog")):
        errors.append("unity_import_evidence_incomplete")
    if not evidence_list(unity.get("targetImportEvidence")):
        errors.append("unity_target_import_evidence_missing")
    if not isinstance(unity.get("measurements"), dict) or not unity["measurements"]:
        errors.append("unity_measurements_missing")

    comparison = report.get("artifactComparison")
    if not isinstance(comparison, dict):
        errors.append("artifact_comparison_missing")
    else:
        mode = comparison.get("mode")
        if mode == "byte-identical":
            if exported.get("sha256") != unity.get("assetSha256"):
                errors.append("export_and_unity_asset_hash_mismatch")
        elif mode == "derived":
            if not evidence_list(comparison.get("derivationEvidence")):
                errors.append("derived_artifact_requires_evidence")
        else:
            errors.append("artifact_comparison_mode_invalid")

    for name in required_gates:
        status = gates.get(name, {}).get("status") if isinstance(gates.get(name), dict) else None
        if status not in {"PASS", "NOT_APPLICABLE"}:
            errors.append(f"technical_pass_requires_closed_gate:{name}")

    rights_status = source.get("rightsStatus")
    review_status = report.get("humanReview", {}).get("status") if isinstance(report.get("humanReview"), dict) else None
    if delivery == "SHIP" and (rights_status != "passed" or review_status != "approved"):
        errors.append("ship_requires_rights_and_human_approval")
    if delivery == "PROTOTYPE_ONLY" and (rights_status != "prototype-only" or review_status != "approved"):
        errors.append("prototype_only_requires_declared_rights_and_human_approval")


def validate_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["report_must_be_json_object"]
    errors: list[str] = []
    validate_common(report, errors)
    kind = report.get("kind")
    if kind == "dvc-restore-report":
        validate_dvc(report, errors)
    elif kind == "blender-unity-import-report":
        validate_blender_unity(report, errors)
    else:
        errors.append("kind_invalid")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "errors": [f"report_unreadable:{exc}"]}, ensure_ascii=False, indent=2))
        return 1
    errors = validate_report(report)
    print(json.dumps({"valid": not errors, "kind": report.get("kind"), "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
