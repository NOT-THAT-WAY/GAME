import ast
import json
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class DistributionContractsTest(unittest.TestCase):
    def test_all_templates_are_valid_json(self):
        for path in sorted((ROOT / "workflows" / "templates").rglob("*.json")):
            with self.subTest(path=path.relative_to(ROOT)):
                json.loads(path.read_text(encoding="utf-8"))

    def test_catalog_declares_execution_and_safety(self):
        ids = []
        for path in sorted((ROOT / "workflows" / "catalog").glob("*.json")):
            item = json.loads(path.read_text(encoding="utf-8"))
            ids.append(item["id"])
            self.assertIn(item.get("execution"), {"mcp", "batch"}, path.name)
            self.assertIsInstance(item.get("mutates_scene"), bool, path.name)
            self.assertIsInstance(item.get("requires_confirmation"), bool, path.name)
            self.assertIsInstance(item.get("enabled_in_app"), bool, path.name)
            self.assertIsInstance(item.get("domains"), list, path.name)
            self.assertTrue(item["domains"], path.name)
            self.assertIsInstance(item.get("maturity"), str, path.name)
            self.assertIn(item.get("scope"), {"generic-or-adaptable", "historical-project-specific"}, path.name)
            self.assertTrue((ROOT / item["script"]).is_file(), path.name)
            if item["execution"] == "batch":
                self.assertFalse(item["enabled_in_app"], path.name)
            if item["scope"] == "historical-project-specific":
                self.assertFalse(item["enabled_in_app"], path.name)
        self.assertEqual(len(ids), len(set(ids)))

    def test_known_unsafe_workflows_are_bounded(self):
        hover = json.loads((ROOT / "workflows" / "catalog" / "hover-loop.json").read_text())
        articulation = json.loads((ROOT / "workflows" / "catalog" / "validate-articulated-object.json").read_text())
        self.assertFalse(hover["enabled_in_app"])
        self.assertEqual(articulation["evidence_level"], "preliminary")
        historical = json.loads((ROOT / "workflows" / "catalog" / "relink-fl-studio-box-media.json").read_text())
        self.assertFalse(historical["enabled_in_app"])
        self.assertEqual(historical["scope"], "historical-project-specific")

    def test_compact_distribution_has_no_lfs_submodules_binary_or_symlink(self):
        self.assertFalse((ROOT / ".gitmodules").exists())
        self.assertNotIn("filter=lfs", (ROOT / ".gitattributes").read_text(encoding="utf-8"))
        result = subprocess.run(
            ["python3", str(ROOT / "tools" / "check_distribution_budget.py")],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_asset_catalog_is_content_addressed_and_unbundled(self):
        catalog = json.loads((ROOT / "catalog" / "assets.json").read_text(encoding="utf-8"))
        ids = set()
        paths = set()
        for item in catalog["assets"]:
            self.assertEqual(item["asset_id"], "sha256:" + item["sha256"])
            self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")
            self.assertFalse(item["bundled"])
            self.assertNotIn(item["asset_id"], ids)
            ids.add(item["asset_id"])
            for path in item["paths"]:
                self.assertFalse(Path(path).is_absolute())
                self.assertNotIn(path, paths)
                paths.add(path)
        manifest = json.loads((ROOT / "catalog" / "catalog-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["unique_content_assets"], len(ids))
        self.assertEqual(manifest["regular_asset_paths"], len(paths))

    def test_profiles_and_capabilities_are_machine_readable(self):
        profile_ids = set()
        for path in sorted((ROOT / "standards" / "profiles").glob("*.json")):
            item = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(item["id"], path.stem)
            self.assertTrue(item["required_gates"])
            self.assertEqual(item["final_validator"], "workflows/tools/validate_team_project.py")
            profile_ids.add(item["id"])
        capabilities = json.loads((ROOT / "catalog" / "capabilities.json").read_text(encoding="utf-8"))
        domain_ids = [item["id"] for item in capabilities["domains"]]
        self.assertEqual(len(domain_ids), len(set(domain_ids)))
        self.assertTrue({"game-ready-assets", "animation-clips", "environments-and-procedural"}.issubset(domain_ids))
        declared_profiles = {profile for item in capabilities["domains"] for profile in item.get("profiles", [])}
        declared_profiles.update(item["profile"] for item in capabilities["domains"] if item.get("profile"))
        self.assertTrue(declared_profiles.issubset(profile_ids))

    def test_active_entrypoints_have_no_personal_home_path(self):
        roots = [
            ROOT / "README.md", ROOT / "AGENTS.md", ROOT / "AGENT_HANDBOOK.md",
            ROOT / "GETTING_STARTED.md", ROOT / "app" / "backend", ROOT / "app" / "static",
            ROOT / "app" / "macos", ROOT / "app" / "compose.yml", ROOT / "tools",
            ROOT / ".agents" / "skills", ROOT / "workflows" / "catalog", ROOT / "workflows" / "templates" / "scene-trial",
            ROOT / "workflows" / "templates" / "asset-build", ROOT / "workflows" / "tools" / "create_scene_trial.py",
            ROOT / "workflows" / "tools" / "validate_scene_trial.py", ROOT / "workflows" / "tools" / "create_asset_build.py",
            ROOT / "workflows" / "tools" / "validate_asset_build.py", ROOT / "workflows" / "tools" / "studio_readiness_check.py",
        ]
        pattern = re.compile(r"/(?:Users|home)/unrecorded(?:/|$)")
        offenders = []
        for base in roots:
            paths = [base] if base.is_file() else list(base.rglob("*"))
            for path in paths:
                if path.is_file() and path.suffix.lower() in {".md", ".py", ".json", ".js", ".swift", ".yml", ".yaml", ".toml"}:
                    if pattern.search(path.read_text(encoding="utf-8", errors="replace")):
                        offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])

    def test_active_python_parses(self):
        for base in (ROOT / "tools", ROOT / "workflows" / "tools", ROOT / "app" / "backend", ROOT / ".agents" / "skills"):
            for path in base.rglob("*.py"):
                with self.subTest(path=path.relative_to(ROOT)):
                    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


if __name__ == "__main__":
    unittest.main()
