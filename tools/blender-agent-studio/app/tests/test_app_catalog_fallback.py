import importlib.util
import os
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(importlib.util.find_spec("fastapi"), "app dependencies not installed")
class AppCatalogFallbackTest(unittest.TestCase):
    def test_catalog_is_visible_without_binary_assets(self):
        os.environ["BLENDER_ROOT"] = str(ROOT)
        os.environ["BLENDER_ROOT_HOST"] = str(ROOT)
        from app.backend import main

        main._cache.clear()
        projects = main.scan_projects()
        assets = main.scan_assets()
        libraries = main.scan_blender_assets()
        self.assertEqual(sum(not item["available"] for item in projects), 77)
        self.assertGreater(len(assets), 12_000)
        self.assertTrue(all(item.get("url") is None for item in assets if not item["available"]))
        self.assertEqual(sum(not item["available"] for item in libraries), 5)


if __name__ == "__main__":
    unittest.main()
