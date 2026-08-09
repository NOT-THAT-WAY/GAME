#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "network-log-report.py"
SPEC = importlib.util.spec_from_file_location("network_log_report", SCRIPT_PATH)
REPORT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = REPORT
SPEC.loader.exec_module(REPORT)


class NetworkLogReportTests(unittest.TestCase):
    def make_source(self, root: Path, name: str, role: str, platform: str, contents: str):
        path = root / name
        path.write_text(contents, encoding="utf-8")
        return REPORT.Source(role=role, platform=platform, path=path)

    def analyse(self, sources, *, expected=3, reconnect=False):
        return REPORT.analyse_sources(
            sources,
            commit="a" * 40,
            session_id="net-proof-01",
            expected_participants=expected,
            transport="tugboat-tailscale",
            require_reconnection=reconnect,
        )

    def test_allowlisted_three_player_proof_passes_without_identifiers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host = self.make_source(
                root,
                "host-Nils-100.64.0.1.log",
                "host",
                "macos",
                "\n".join(
                    (
                        'Player connection * "[IP] 100.64.0.1 [Guid] 123 [Id] OSXPlayer(machine.local)"',
                        "/Users/nils/GAME secret@example.com",
                        "Local server is started for Tugboat.",
                        "Remote connection started for Id 0.",
                        "Local client is started for Tugboat.",
                        "[GAME-CONNECTION] Authenticated as Nils on OSXPlayer.",
                        "[GAME-CONNECTION] Roster updated (3 participant(s)).",
                        "Remote connection stopped for Id 2.",
                        "Remote connection started for Id 3.",
                    )
                ),
            )
            client_a = self.make_source(
                root,
                "client-a.log",
                "client",
                "windows",
                "Local client is started for Tugboat.\n[GAME-CONNECTION] Authenticated as Sean on WindowsPlayer.\n",
            )
            client_b = self.make_source(
                root,
                "client-b.log",
                "client",
                "macos",
                "Local client is started for Tugboat.\n[GAME-CONNECTION] Authenticated as Zak on OSXPlayer.\n",
            )
            result = self.analyse([host, client_a, client_b], reconnect=True)
            self.assertEqual("PASS", result["summary"]["verdict"])
            self.assertTrue(result["summary"]["reconnectionObserved"])
            serialized = json.dumps(result, ensure_ascii=False)
            for secret in ("Nils", "Sean", "Zak", "100.64.0.1", "machine.local", "/Users/nils", "secret@example.com"):
                self.assertNotIn(secret, serialized)
            REPORT.assert_redacted(result)

    def test_missing_roster_is_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self.make_source(
                Path(directory),
                "host.log",
                "host",
                "macos",
                "Local server is started for Tugboat.\n"
                "Local client is started for Tugboat.\n"
                "[GAME-CONNECTION] Authenticated as Player on OSXPlayer.\n",
            )
            result = self.analyse([source])
            self.assertEqual("INCOMPLETE", result["summary"]["verdict"])
            self.assertIn("log_count_3", result["summary"]["missing"])
            self.assertIn("roster_3", result["summary"]["missing"])

    def test_same_log_cannot_stand_in_for_three_machines(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self.make_source(
                Path(directory),
                "host.log",
                "host",
                "macos",
                "Local server is started for Tugboat.\n"
                "Local client is started for Tugboat.\n"
                "[GAME-CONNECTION] Authenticated as Player on OSXPlayer.\n"
                "[GAME-CONNECTION] Roster updated (3 participant(s)).\n",
            )
            result = self.analyse([source, source, source])
            self.assertEqual("INCOMPLETE", result["summary"]["verdict"])
            self.assertIn("distinct_log_sources", result["summary"]["missing"])
            self.assertIn("distinct_log_content", result["summary"]["missing"])

    def test_exception_fails_without_copying_message(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self.make_source(
                Path(directory),
                "host.log",
                "host",
                "macos",
                "NullReferenceException: token secret at /Users/person/GAME\n",
            )
            result = self.analyse([source], expected=1)
            self.assertEqual("FAIL", result["summary"]["verdict"])
            serialized = json.dumps(result)
            self.assertIn("NullReferenceException", serialized)
            self.assertNotIn("token secret", serialized)
            self.assertNotIn("/Users/person", serialized)

    def test_written_report_never_embeds_raw_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(
                root,
                "private-name.log",
                "host",
                "macos",
                "Local server is started for Tugboat.\n"
                "Local client is started for Tugboat.\n"
                "[GAME-CONNECTION] Authenticated as Private Name on OSXPlayer.\n"
                "[GAME-CONNECTION] Roster updated (1 participant(s)).\n",
            )
            result = self.analyse([source], expected=1)
            output = root / "public"
            REPORT.write_reports(output, result)
            contents = (output / "network-report.json").read_text(encoding="utf-8")
            self.assertNotIn(str(source.path), contents)
            self.assertNotIn("Private Name", contents)


if __name__ == "__main__":
    unittest.main()
