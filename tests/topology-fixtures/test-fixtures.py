#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "Assets" / "_Project" / "Tests" / "Fixtures" / "Topology"


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
                "canonical-bytes-and-checksum",
                "tick-and-physics",
                "player-canonical-shape",
                "energy-and-contestation",
                "round-rule",
            }.issubset(deferred)
        )


if __name__ == "__main__":
    unittest.main()
