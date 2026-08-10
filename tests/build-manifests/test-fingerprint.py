#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build-bundle-fingerprint.py"
SPEC = importlib.util.spec_from_file_location("build_bundle_fingerprint", SCRIPT_PATH)
FINGERPRINT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = FINGERPRINT
SPEC.loader.exec_module(FINGERPRINT)


class BundleFingerprintTests(unittest.TestCase):
    def test_fingerprint_is_stable_and_never_contains_the_absolute_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Data").mkdir()
            (root / "GAME.exe").write_bytes(b"launcher")
            (root / "Data" / "sharedassets0.assets").write_bytes(b"assets")

            first = FINGERPRINT.fingerprint(root)
            second = FINGERPRINT.fingerprint(root)

            self.assertEqual(first, second)
            self.assertEqual(2, first["fileCount"])
            self.assertEqual(14, first["totalBytes"])
            self.assertEqual(
                ["Data/sharedassets0.assets", "GAME.exe"],
                [entry["relativePath"] for entry in first["files"]],
            )
            self.assertNotIn(str(root), str(first))

    def test_any_content_change_changes_the_bundle_manifest_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "GAME"
            artifact.write_bytes(b"before")
            before = FINGERPRINT.fingerprint(root)["bundleManifestSha256"]
            artifact.write_bytes(b"after")
            after = FINGERPRINT.fingerprint(root)["bundleManifestSha256"]
            self.assertNotEqual(before, after)

    def test_explicit_exclusion_breaks_manifest_self_reference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "GAME.exe").write_bytes(b"launcher")
            manifest = root / "build-bundle-fingerprint.json"
            manifest.write_text("changes every time", encoding="utf-8")

            result = FINGERPRINT.fingerprint(root, [manifest.name])
            self.assertEqual(["GAME.exe"], [entry["relativePath"] for entry in result["files"]])


if __name__ == "__main__":
    unittest.main()
