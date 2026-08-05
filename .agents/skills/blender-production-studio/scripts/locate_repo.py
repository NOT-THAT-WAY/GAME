#!/usr/bin/env python3
"""Locate the nearest Blender Team Studio root from the current directory."""
from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    start = Path.cwd().resolve()
    for candidate in (start, *start.parents):
        if (candidate / "AGENTS.md").is_file() and (candidate / "workflows" / "catalog").is_dir():
            print(json.dumps({"root": str(candidate), "agents": str(candidate / "AGENTS.md")}))
            return 0
    print(json.dumps({"error": "Blender Team Studio root not found", "start": str(start)}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
