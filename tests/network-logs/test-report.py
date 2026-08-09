#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import hashlib
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
    def make_source(
        self,
        root: Path,
        name: str,
        role: str,
        platform: str,
        contents: str,
        *,
        identity: bool = True,
        commit: str = "a" * 40,
        dirty: bool = False,
        build_set_id: str = "b" * 64,
    ):
        path = root / name
        if identity:
            build_id = ("c" if platform == "macos" else "d") * 64
            marker = (
                "[GAME-BUILD] schema=1 "
                f"buildId={build_id} buildSetId={build_set_id} commit={commit} "
                f"dirty={str(dirty).lower()} profile=connection platform={platform} "
                "unity=6000.3.20f1 startedAt=2026-08-09T10:00:00Z"
            )
            contents = f"{marker}\n{contents}"
        path.write_text(contents, encoding="utf-8")
        return REPORT.Source(role=role, platform=platform, path=path)

    def make_manifests(self, sources):
        manifests = []
        seen_platforms = set()
        for source in sources:
            if source.platform in seen_platforms:
                continue
            _, _, _, identities, marker_count = REPORT.extract_events(source.path)
            if marker_count != 1 or len(identities) != 1:
                continue
            identity = identities[0]
            file_digest = "0" * 64
            canonical = f"GAME\t1\t{file_digest}\n"
            fingerprint = {
                "schemaVersion": 1,
                "kind": "unity-build-bundle-fingerprint",
                "algorithm": "sha256-relative-path-size-content-v1",
                "fileCount": 1,
                "totalBytes": 1,
                "bundleManifestSha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
                "files": [{"relativePath": "GAME", "sizeBytes": 1, "sha256": file_digest}],
            }
            document = {
                "schemaVersion": 2,
                "kind": "unity-player-build",
                "buildId": identity["buildId"],
                "buildSetId": identity["buildSetId"],
                "profile": identity["profile"],
                "platform": identity["platform"],
                "sourceGitCommit": identity["sourceGitCommit"],
                "sourceDirtyWorktree": identity["sourceDirtyWorktree"],
                "unityVersion": identity["unityVersion"],
                "startedAtUtc": identity["startedAtUtc"],
                "binarySha256": "1" * 64,
                "binarySizeBytes": 1,
                "bundleFingerprint": fingerprint,
                "provenance": "current-run",
                "result": "passed",
                "exitCode": 0,
            }
            path = source.path.parent / f"build-manifest-{source.platform}.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            manifests.append(REPORT.BuildManifestSource(platform=source.platform, path=path))
            seen_platforms.add(source.platform)
        return manifests

    def analyse(self, sources, *, expected=3, reconnect=False, manifests=None):
        return REPORT.analyse_sources(
            sources,
            manifests=self.make_manifests(sources) if manifests is None else manifests,
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
            self.assertEqual("a" * 40, result["sourceGitCommit"])
            self.assertEqual("b" * 64, result["buildSetId"])
            self.assertEqual(2, result["manifestCount"])
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

    def test_manual_commit_cannot_relabel_a_legacy_log(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self.make_source(
                Path(directory),
                "legacy.log",
                "host",
                "macos",
                "Local server is started for Tugboat.\n"
                "Local client is started for Tugboat.\n"
                "[GAME-CONNECTION] Authenticated as Player on OSXPlayer.\n"
                "[GAME-CONNECTION] Roster updated (1 participant(s)).\n",
                identity=False,
            )
            result = self.analyse([source], expected=1)
            self.assertEqual("INCOMPLETE", result["summary"]["verdict"])
            self.assertIn("build_identity_once_per_log", result["summary"]["missing"])
            self.assertIn("one_build_manifest_per_platform", result["summary"]["missing"])
            self.assertIsNone(result["sourceGitCommit"])

    def test_mismatched_embedded_commit_is_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self.make_source(
                Path(directory),
                "wrong-commit.log",
                "host",
                "macos",
                "Local server is started for Tugboat.\n"
                "Local client is started for Tugboat.\n"
                "[GAME-CONNECTION] Authenticated as Player on OSXPlayer.\n"
                "[GAME-CONNECTION] Roster updated (1 participant(s)).\n",
                commit="e" * 40,
            )
            result = self.analyse([source], expected=1)
            self.assertEqual("INCOMPLETE", result["summary"]["verdict"])
            self.assertIn("source_commit_match", result["summary"]["missing"])
            self.assertEqual("e" * 40, result["sourceGitCommit"])

    def test_dirty_build_is_never_final_network_proof(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self.make_source(
                Path(directory),
                "dirty.log",
                "host",
                "macos",
                "Local server is started for Tugboat.\n"
                "Local client is started for Tugboat.\n"
                "[GAME-CONNECTION] Authenticated as Player on OSXPlayer.\n"
                "[GAME-CONNECTION] Roster updated (1 participant(s)).\n",
                dirty=True,
            )
            result = self.analyse([source], expected=1)
            self.assertEqual("INCOMPLETE", result["summary"]["verdict"])
            self.assertIn("clean_build_per_log", result["summary"]["missing"])

    def test_platform_builds_must_share_one_build_set(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host = self.make_source(
                root,
                "host.log",
                "host",
                "macos",
                "Local server is started for Tugboat.\n"
                "Local client is started for Tugboat.\n"
                "[GAME-CONNECTION] Authenticated as Host on OSXPlayer.\n"
                "[GAME-CONNECTION] Roster updated (2 participant(s)).\n",
            )
            client = self.make_source(
                root,
                "client.log",
                "client",
                "windows",
                "Local client is started for Tugboat.\n"
                "[GAME-CONNECTION] Authenticated as Client on WindowsPlayer.\n",
                build_set_id="f" * 64,
            )
            result = self.analyse([host, client], expected=2)
            self.assertEqual("INCOMPLETE", result["summary"]["verdict"])
            self.assertIn("shared_build_set", result["summary"]["missing"])
            self.assertIsNone(result["buildSetId"])

    def test_tampered_bundle_manifest_is_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self.make_source(
                Path(directory),
                "host.log",
                "host",
                "macos",
                "Local server is started for Tugboat.\n"
                "Local client is started for Tugboat.\n"
                "[GAME-CONNECTION] Authenticated as Player on OSXPlayer.\n"
                "[GAME-CONNECTION] Roster updated (1 participant(s)).\n",
            )
            manifests = self.make_manifests([source])
            document = json.loads(manifests[0].path.read_text(encoding="utf-8"))
            document["bundleFingerprint"]["bundleManifestSha256"] = "9" * 64
            manifests[0].path.write_text(json.dumps(document), encoding="utf-8")

            result = self.analyse([source], expected=1, manifests=manifests)
            self.assertEqual("INCOMPLETE", result["summary"]["verdict"])
            self.assertIn("valid_build_manifest_per_platform", result["summary"]["missing"])
            self.assertIn(
                "bundle_manifest_hash_mismatch",
                result["manifests"][0]["validationErrors"],
            )

    def test_log_and_manifest_build_ids_must_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self.make_source(
                Path(directory),
                "host.log",
                "host",
                "macos",
                "Local server is started for Tugboat.\n"
                "Local client is started for Tugboat.\n"
                "[GAME-CONNECTION] Authenticated as Player on OSXPlayer.\n"
                "[GAME-CONNECTION] Roster updated (1 participant(s)).\n",
            )
            manifests = self.make_manifests([source])
            document = json.loads(manifests[0].path.read_text(encoding="utf-8"))
            document["buildId"] = "9" * 64
            manifests[0].path.write_text(json.dumps(document), encoding="utf-8")

            result = self.analyse([source], expected=1, manifests=manifests)
            self.assertEqual("INCOMPLETE", result["summary"]["verdict"])
            self.assertIn("log_manifest_identity_match", result["summary"]["missing"])


if __name__ == "__main__":
    unittest.main()
