#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "Assets" / "_Project" / "Tests" / "Fixtures" / "Topology"
LEGACY_TOPOLOGY = REPO_ROOT / "Assets" / "_Project" / "Maze" / "MazeGrid16x16.json"
MIGRATED_TOPOLOGY = REPO_ROOT / "Assets" / "_Project" / "Maze" / "MazeTopology16x16.v1.json"
GRAYBOX_TOPOLOGY = REPO_ROOT / "Assets" / "_Project" / "Maze" / "GrayboxTopology2x2.v1.json"


def load_migration_module():
    script = REPO_ROOT / "scripts" / "migrate-maze-topology-v1.py"
    spec = importlib.util.spec_from_file_location("migrate_maze_topology_v1", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reject_duplicate_members(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON property: {key}")
        result[key] = value
    return result


def strict_load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_members)


class TopologyFixtureContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = strict_load(FIXTURES / "manifest.json")

    def test_manifest_covers_each_payload_once(self) -> None:
        declared = [case["file"] for case in self.manifest["cases"]]
        actual = sorted(path.name for path in FIXTURES.glob("*.json") if path.name != "manifest.json")
        self.assertEqual(sorted(declared), actual)
        self.assertEqual(len(declared), len(set(declared)))
        ids = [case["id"] for case in self.manifest["cases"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_each_case_has_an_explicit_expected_verdict(self) -> None:
        for case in self.manifest["cases"]:
            with self.subTest(case=case["id"]):
                expected = case.get("expectedIssueCodes")
                self.assertIsInstance(expected, list)
                if case["id"] == "valid-minimal":
                    self.assertEqual([], expected)
                else:
                    self.assertTrue(expected)

    def test_duplicate_property_fixture_is_rejected_by_strict_json(self) -> None:
        duplicate = FIXTURES / "invalid-duplicate-json-property.json"
        with self.assertRaisesRegex(ValueError, "duplicate JSON property: widthCells"):
            strict_load(duplicate)

    def test_other_payloads_are_valid_json_documents(self) -> None:
        for case in self.manifest["cases"]:
            if case["id"] == "duplicate-json-property":
                continue
            with self.subTest(case=case["id"]):
                self.assertIsInstance(strict_load(FIXTURES / case["file"]), dict)

    def test_valid_fixture_contains_only_decided_structural_contract(self) -> None:
        fixture = strict_load(FIXTURES / "valid-minimal.json")
        self.assertEqual(1, fixture["schemaVersion"])
        self.assertEqual(2, fixture["dimensions"]["widthCells"])
        self.assertEqual(1, fixture["dimensions"]["heightCells"])
        self.assertEqual({10}, {wall["wallId"] for wall in fixture["walls"]})
        self.assertEqual({100}, {pivot["pivotId"] for pivot in fixture["pivots"]})
        self.assertEqual({200, 201}, {spawn["spawnId"] for spawn in fixture["spawns"]})
        for forbidden in ("connectivityPolicy", "checksum", "tickRate", "playerHeightMm", "roundRule"):
            self.assertNotIn(forbidden, fixture)

    def test_deferred_design_axes_remain_named(self) -> None:
        deferred = set(self.manifest["deferred"])
        self.assertTrue(
            {
                "connectivity-policy",
                "tick-and-physics",
                "player-canonical-shape",
                "energy-and-contestation",
                "round-rule",
            }.issubset(deferred)
        )
        self.assertIn("canonical-bytes-and-checksum", self.manifest["contractScope"])


class TopologyMigrationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.migration = load_migration_module()
        cls.legacy = strict_load(LEGACY_TOPOLOGY)

    def test_migration_matches_the_tracked_runtime_document(self) -> None:
        self.assertEqual(strict_load(MIGRATED_TOPOLOGY), self.migration.migrate(copy.deepcopy(self.legacy)))

    def test_graybox_checksum_and_cardinality_are_stable(self) -> None:
        graybox = strict_load(GRAYBOX_TOPOLOGY)
        self.assertEqual("2f5f3b1148408d643cad9793fb59d511948bc4f1e252898cf375affd98c13365", graybox["checksum"])
        self.assertEqual(graybox["checksum"], self.migration.checksum(graybox))
        self.assertEqual((2, 2), (graybox["dimensions"]["widthCells"], graybox["dimensions"]["heightCells"]))
        self.assertEqual(9, len(graybox["walls"]))
        self.assertEqual(1, len(graybox["pivots"]))
        self.assertEqual(2, len(graybox["spawns"]))
        self.assertEqual(0, len(graybox["openings"]))

    def test_migration_rejects_bool_and_fractional_grid_values(self) -> None:
        boolean_width = copy.deepcopy(self.legacy)
        boolean_width["meta"]["width"] = True
        with self.assertRaisesRegex(ValueError, "meta.width"):
            self.migration.migrate(boolean_width)

        fractional_wall = copy.deepcopy(self.legacy)
        fractional_wall["vwalls"][0][0] = 1.5
        with self.assertRaisesRegex(ValueError, "vwalls"):
            self.migration.migrate(fractional_wall)

    def test_migration_rejects_negative_coordinates_and_duplicate_directions(self) -> None:
        negative_node = copy.deepcopy(self.legacy)
        negative_node["pivots"][0]["node"][0] = -1
        with self.assertRaisesRegex(ValueError, "node"):
            self.migration.migrate(negative_node)

        duplicate_arm = copy.deepcopy(self.legacy)
        duplicate_arm["pivots"][0]["arms"][1] = duplicate_arm["pivots"][0]["arms"][0]
        with self.assertRaisesRegex(ValueError, "unique"):
            self.migration.migrate(duplicate_arm)

    def test_migration_rejects_a_rotated_pivot_pose_outside_the_grid(self) -> None:
        border_pivot = {
            "meta": {"width": 1, "height": 1},
            "vwalls": [[2], [1]],
            "hwalls": [[1, 1]],
            "pivots": [{"node": [0, 0], "orientation": 0, "arms": ["N"]}],
            "entrances": [],
        }

        with self.assertRaisesRegex(ValueError, "rotated pivot state leaves the grid"):
            self.migration.migrate(border_pivot)


if __name__ == "__main__":
    unittest.main()
