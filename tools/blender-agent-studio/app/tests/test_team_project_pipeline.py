import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from workflows.tools import build_delivery_manifest, create_team_project, validate_team_project


class TeamProjectPipelineTest(unittest.TestCase):
    def test_every_project_type_scaffolds_and_validates(self):
        project_types = (
            "asset", "game-asset", "rig", "animation", "environment", "cinematic", "still", "procedural"
        )
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            projects = base / "projects"
            local_work = base / "local_work"
            with mock.patch.object(create_team_project, "PROJECTS", projects), mock.patch.object(
                create_team_project, "LOCAL_WORK", local_work
            ), mock.patch.object(validate_team_project, "PROJECTS", projects):
                for project_type in project_types:
                    project_id = f"smoke-{project_type}-v001"
                    argv = [
                        "create_team_project.py", "--id", project_id, "--type", project_type,
                        "--objective", f"Smoke {project_type}", "--target", "Declared target 1.0",
                    ]
                    with self.subTest(project_type=project_type), mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(create_team_project.main(), 0)
                        project = projects / project_id
                        self.assertTrue((project / "project.json").is_file())
                        self.assertTrue((local_work / project_id / "work").is_dir())
                        technical = json.loads((project / "technical-contract.json").read_text(encoding="utf-8"))
                        self.assertIn("budgets", technical)
                        validate_argv = ["validate_team_project.py", str(project), "--stage", "scaffold"]
                        with mock.patch.object(sys, "argv", validate_argv), contextlib.redirect_stdout(io.StringIO()):
                            self.assertEqual(validate_team_project.main(), 0)
                        report = json.loads((project / "validation-report.json").read_text(encoding="utf-8"))
                        self.assertTrue(report["package_valid"])
                        self.assertIn("contracts_contain_unresolved_values", report["warnings"])

    def test_final_delivery_hashes_gates_target_and_rights(self):
        local_root = create_team_project.ROOT / "local_work"
        local_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=local_root) as temporary:
            base = Path(temporary).resolve()
            projects = base / "projects"
            deliveries = base / "deliveries"
            with mock.patch.object(create_team_project, "PROJECTS", projects), mock.patch.object(
                create_team_project, "LOCAL_WORK", deliveries
            ), mock.patch.object(validate_team_project, "PROJECTS", projects), mock.patch.object(
                build_delivery_manifest, "PROJECTS", projects
            ):
                project_id = "final-still-smoke-v001"
                argv = [
                    "create_team_project.py", "--id", project_id, "--type", "still",
                    "--objective", "Validate a still delivery", "--target", "PNG review target 1.0",
                ]
                with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(create_team_project.main(), 0)
                project = projects / project_id

                def resolve_values(value):
                    if isinstance(value, dict):
                        return {key: resolve_values(child) for key, child in value.items()}
                    if isinstance(value, list):
                        return [resolve_values(child) for child in value]
                    return "declared" if isinstance(value, str) and "UNRESOLVED" in value else value

                for name in ("brief.json", "technical-contract.json"):
                    path = project / name
                    path.write_text(json.dumps(resolve_values(json.loads(path.read_text())), indent=2) + "\n")
                project_doc = json.loads((project / "project.json").read_text())
                project_doc["status"] = "reviewed"
                (project / "project.json").write_text(json.dumps(project_doc, indent=2) + "\n")

                evidence = project / "evidence" / "review.txt"
                evidence.write_text("Measured and reviewed evidence.\n")
                evidence_rel = evidence.relative_to(create_team_project.ROOT).as_posix()
                quality_path = project / "quality-plan.json"
                quality = json.loads(quality_path.read_text())
                for state in quality["gates"].values():
                    state.update({"status": "passed", "evidence": [evidence_rel], "notes": "reviewed"})
                quality_path.write_text(json.dumps(quality, indent=2) + "\n")

                output_dir = deliveries / project_id / "exports"
                output_dir.mkdir(parents=True, exist_ok=True)
                role_files = {}
                for role in ("master_blend", "final_render", "render_settings"):
                    path = output_dir / f"{role}.txt"
                    path.write_text(f"validated {role}\n")
                    role_files[role] = path.relative_to(create_team_project.ROOT).as_posix()
                manifest_argv = ["build_delivery_manifest.py", str(project), "--validated"]
                for role, path in role_files.items():
                    manifest_argv.extend(["--file", f"{role}={path}"])
                with mock.patch.object(sys, "argv", manifest_argv), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(build_delivery_manifest.main(), 0)

                delivery_path = project / "delivery-manifest.json"
                delivery = json.loads(delivery_path.read_text())
                delivery["target_validation"] = {
                    "status": "passed", "target": project_doc["target"], "evidence": [evidence_rel]
                }
                delivery["rights_review"] = {"status": "passed", "notes": "Synthetic test data only."}
                delivery_path.write_text(json.dumps(delivery, indent=2) + "\n")
                (project / "FINAL_REVIEW.md").write_text(
                    "# Final review\n\nVerdict: accepted.\n\n" + "Evidence and limitations were reviewed. " * 20
                )

                validate_argv = ["validate_team_project.py", str(project), "--stage", "final"]
                with mock.patch.object(sys, "argv", validate_argv), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(validate_team_project.main(), 0)
                report = json.loads((project / "validation-report.json").read_text())
                self.assertTrue(report["package_valid"])
                self.assertEqual(report["verified_delivery_files"], 3)


if __name__ == "__main__":
    unittest.main()
