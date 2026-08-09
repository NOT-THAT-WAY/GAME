#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "human-test-report.py"
SPEC = importlib.util.spec_from_file_location("human_test_report", SCRIPT_PATH)
REPORT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(REPORT)


class HumanTestReportTests(unittest.TestCase):
    def analyse(self, contents: str) -> dict:
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "host.log"
            log_path.write_text(contents, encoding="utf-8")
            return REPORT.analyse_log(log_path)

    def test_complete_pivot_path_passes(self) -> None:
        markers = "\n".join(
            f"[GAME-SMOKE] {event}"
            for event in ("ready", "look", "movement", "jump", "punch", "bot_hit", "pivot_turned")
        )
        result = self.analyse(markers)
        self.assertEqual("PASS", result["verdict"])
        self.assertEqual([], result["missing"])

    def test_wall_turn_satisfies_the_maze_action(self) -> None:
        markers = "\n".join(
            f"[GAME-SMOKE] {event}"
            for event in ("ready", "look", "movement", "jump", "punch", "bot_hit", "wall_turned")
        )
        self.assertEqual("PASS", self.analyse(markers)["verdict"])

    def test_missing_actions_are_incomplete(self) -> None:
        result = self.analyse(
            "[GAME-SMOKE] ready\n[GAME-SMOKE] movement\n[GAME-SMOKE] pivot_input\n"
        )
        self.assertEqual("INCOMPLETE", result["verdict"])
        self.assertIn("bot_hit", result["missing"])
        self.assertIn("pivot_turned|wall_turned", result["missing"])
        self.assertEqual(["pivot_input"], result["mazeDiagnostics"])

    def test_exception_is_a_failure(self) -> None:
        result = self.analyse("NullReferenceException: broken\n")
        self.assertEqual("FAIL", result["verdict"])
        self.assertEqual(1, len(result["fatalErrors"]))

    def test_normal_unity_stack_line_is_not_a_failure(self) -> None:
        result = self.analyse("Some.Namespace.ExceptionUtility:Log () (at Assets/Test.cs:10)\n")
        self.assertEqual("INCOMPLETE", result["verdict"])
        self.assertEqual([], result["fatalErrors"])


if __name__ == "__main__":
    unittest.main()
