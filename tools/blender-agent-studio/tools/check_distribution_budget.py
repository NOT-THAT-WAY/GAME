#!/usr/bin/env python3
"""Fail when the compact repository starts embedding binary assets or exceeds its size budget."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "standards" / "distribution-budget.json"


def tracked_or_present() -> list[Path]:
    if (ROOT / ".git").exists():
        output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
        return [ROOT / raw.decode() for raw in output.split(b"\0") if raw]
    ignored_roots = {".git", "local_assets", "local_work", "projects/work", "renders/local"}
    ignored_files = {".studio.local.json", "app/.env"}
    result = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT).as_posix()
        if any(relative == root or relative.startswith(root + "/") for root in ignored_roots):
            continue
        if relative in ignored_files:
            continue
        if any(part in {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".venv", "venv"} for part in path.relative_to(ROOT).parts):
            continue
        if path.is_file() or path.is_symlink():
            result.append(path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    args = parser.parse_args()
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    forbidden = set(policy["forbidden_binary_extensions"])
    errors: list[str] = []
    files = tracked_or_present()
    total = 0
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        if path.is_symlink():
            errors.append(f"symlink_forbidden:{relative}")
            continue
        if not path.is_file():
            errors.append(f"tracked_path_missing:{relative}")
            continue
        size = path.stat().st_size
        total += size
        if path.suffix.lower() in forbidden:
            errors.append(f"binary_forbidden:{relative}")
        limit = policy.get("catalog_max_file_bytes") if relative.startswith("catalog/") else policy["max_file_bytes"]
        if size > limit:
            errors.append(f"file_over_budget:{relative}:{size}>{limit}")
        if size <= 2_000_000 and path.suffix.lower() in policy["text_extensions"]:
            text = path.read_text(encoding="utf-8", errors="replace")
            for username in policy.get("forbidden_path_usernames", []):
                patterns = (
                    rf"/(?:Users|home)/{re.escape(username)}(?:/|$)",
                    rf"(?i:[a-z]:[\\/]Users[\\/]{re.escape(username)}(?:[\\/]|$))",
                )
                if any(re.search(pattern, text) for pattern in patterns):
                    errors.append(f"personal_path:{relative}:{username}")
    if total > policy["max_repository_bytes"]:
        errors.append(f"repository_over_budget:{total}>{policy['max_repository_bytes']}")
    for required in policy["required_files"]:
        if not (ROOT / required).is_file():
            errors.append(f"required_file_missing:{required}")
    if (ROOT / ".gitmodules").exists():
        errors.append("submodules_forbidden_in_compact_distribution")

    report = {
        "schema_version": 1,
        "compact_distribution_valid": not errors,
        "tracked_or_present_files": len(files),
        "repository_bytes": total,
        "max_repository_bytes": policy["max_repository_bytes"],
        "binary_assets_bundled": sum(error.startswith("binary_forbidden:") for error in errors),
        "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
