#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "validate-evidence-report.py"
SPEC = importlib.util.spec_from_file_location("validate_evidence_report", SCRIPT_PATH)
REPORT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(REPORT)


def common(kind: str) -> dict:
    return {
        "schemaVersion": 1,
        "kind": kind,
        "sessionId": "proof-20260809T180000Z",
        "startedAtUtc": "2026-08-09T18:00:00Z",
        "finishedAtUtc": "2026-08-09T18:05:00Z",
        "sourceGitCommit": "a" * 40,
        "sourceDirtyWorktree": False,
        "machineAlias": "QA-MAC-01",
    }


def passing_dvc() -> dict:
    report = common("dvc-restore-report")
    report.update(
        {
            "testId": "DVC-03",
            "platform": "macos",
            "dvcVersion": "3.67.1",
            "remoteAlias": "assets",
            "cachePreparation": {"mode": "empty-cache", "proof": "Logs/AssetRestore/cache-before.txt"},
            "pull": {
                "target": "ExternalAssets/Art/ART-PERSO-PUNCH-001.dvc",
                "exitCode": 0,
                "log": "Logs/AssetRestore/dvc-pull.log",
            },
            "artifacts": [
                {
                    "path": "ExternalAssets/Art/ART-PERSO-PUNCH-001/master/player.blend",
                    "expectedSha256": "b" * 64,
                    "actualSha256": "b" * 64,
                    "bytes": 173302,
                }
            ],
            "storageControls": {
                "objectVersioning": "confirmed",
                "secondCopy": "confirmed",
                "evidence": ["private-proof:R2-versioning", "private-proof:second-copy"],
            },
            "result": "PASS",
            "blockers": [],
            "failures": [],
            "limits": [],
        }
    )
    return report


def passing_blender_unity() -> dict:
    report = common("blender-unity-import-report")
    gates = {
        name: {"status": "PASS", "evidence": [f"evidence/{name}.json"], "notes": ""}
        for name in REPORT.required_unity_gates()
    }
    for optional in ("lod_group", "avatar_or_skeleton_if_present", "animation_clips_if_present"):
        gates[optional] = {
            "status": "NOT_APPLICABLE",
            "evidence": [],
            "notes": "Le contrat de cet asset statique ne demande pas ce système.",
        }
    report.update(
        {
            "projectId": "stone-pivot-v001",
            "assetId": "ART-PIVOT-001",
            "source": {
                "masterStatus": "available",
                "masterSha256": "c" * 64,
                "blenderVersion": "Blender 5.1.1",
                "rightsStatus": "prototype-only",
            },
            "export": {
                "path": "local_work/stone-pivot-v001/exports/pivot.fbx",
                "format": "fbx",
                "sha256": "d" * 64,
                "bytes": 4242,
                "settingsEvidence": "projects/team/stone-pivot-v001/evidence/export-settings.json",
                "independentReimport": {
                    "status": "PASS",
                    "evidence": ["projects/team/stone-pivot-v001/evidence/reimport.json"],
                },
            },
            "unityImport": {
                "performed": True,
                "unityVersion": REPORT.expected_unity_version(),
                "platform": "macos",
                "assetPath": "Assets/_Project/Pivot/Pivot.fbx",
                "assetSha256": "d" * 64,
                "importerLog": "Logs/AssetImport/pivot.log",
                "importerWarnings": [],
                "targetImportEvidence": ["projects/team/stone-pivot-v001/evidence/unity-import.json"],
                "measurements": {"heightM": 2.4, "triangles": 2200},
            },
            "artifactComparison": {"mode": "byte-identical", "derivationEvidence": []},
            "gates": gates,
            "criticalFailures": [],
            "technicalResult": "PASS",
            "deliveryDisposition": "PROTOTYPE_ONLY",
            "humanReview": {"status": "approved", "reviewerAlias": "ART-REVIEW-01"},
            "blockers": [],
            "failures": [],
            "limits": ["Validation Windows encore à exécuter."],
        }
    )
    return report


class EvidenceReportTests(unittest.TestCase):
    def test_dvc_empty_cache_restore_passes(self) -> None:
        self.assertEqual([], REPORT.validate_report(passing_dvc()))

    def test_dvc_hash_mismatch_cannot_pass(self) -> None:
        report = passing_dvc()
        report["artifacts"][0]["actualSha256"] = "e" * 64
        self.assertIn("artifact_0_hash_mismatch", REPORT.validate_report(report))

    def test_dvc03_requires_storage_controls(self) -> None:
        report = passing_dvc()
        report["storageControls"]["secondCopy"] = "not-tested"
        self.assertIn("dvc03_requires_second_copy_confirmation", REPORT.validate_report(report))

    def test_blender_to_unity_target_import_passes(self) -> None:
        self.assertEqual([], REPORT.validate_report(passing_blender_unity()))

    def test_blender_reimport_alone_cannot_pass(self) -> None:
        report = passing_blender_unity()
        report["unityImport"]["performed"] = False
        self.assertIn("unity_target_import_not_performed", REPORT.validate_report(report))

    def test_optional_gate_needs_a_reason(self) -> None:
        report = passing_blender_unity()
        report["gates"]["lod_group"]["notes"] = ""
        self.assertIn("gate_lod_group_not_applicable_requires_notes", REPORT.validate_report(report))

    def test_templates_are_json_but_not_finished_proofs(self) -> None:
        for name in (
            "dvc-restore-report.template.json",
            "blender-unity-import-report.template.json",
        ):
            template = json.loads((REPO_ROOT / "docs" / "templates" / name).read_text(encoding="utf-8"))
            self.assertTrue(REPORT.validate_report(template), name)


if __name__ == "__main__":
    unittest.main()
