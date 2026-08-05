#!/usr/bin/env python3
"""Produce a reproducible, read-only inventory of a compact Blender Team Studio clone."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".venv",
    "venv", "node_modules", "dist", "local_assets", "local_work",
}
TEXT_SUFFIXES = {".md", ".py", ".json", ".js", ".swift", ".toml", ".yml", ".yaml", ".sh", ".txt"}
ACTIVE_ROOTS = ("README.md", "AGENTS.md", "AGENT_HANDBOOK.md", "GETTING_STARTED.md", ".agents", "app", "tools", "workflows")


def files() -> list[Path]:
    if (ROOT / ".git").is_dir():
        output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
        return [ROOT / raw.decode() for raw in output.split(b"\0") if raw and (ROOT / raw.decode()).is_file()]
    result: list[Path] = []
    for current, dirs, names in os.walk(ROOT):
        dirs[:] = sorted(name for name in dirs if name not in SKIP_DIRS)
        for name in sorted(names):
            path = Path(current) / name
            if path.is_file() and not path.is_symlink():
                result.append(path)
    return result


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--hash-duplicates", action="store_true")
    args = parser.parse_args()
    all_files = files()
    sizes = {path: path.stat().st_size for path in all_files}
    extensions = Counter((path.suffix.lower() or "[none]") for path in all_files)
    links = []
    for path in ROOT.rglob("*"):
        if path.is_symlink():
            links.append({"path": str(path.relative_to(ROOT)), "target": os.readlink(path), "broken": not path.exists()})

    json_errors = []
    python_errors = []
    for path in all_files:
        relative = str(path.relative_to(ROOT))
        if path.suffix.lower() == ".json":
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                json_errors.append({"path": relative, "error": str(exc)})
        if path.suffix.lower() == ".py" and not relative.startswith(("third_party/", "vendor/")):
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=relative)
            except Exception as exc:
                python_errors.append({"path": relative, "error": str(exc)})

    personal = re.compile(r"/(?:Users|home)/unrecorded(?:/|$)")
    absolute_paths = []
    for entry in ACTIVE_ROOTS:
        base = ROOT / entry
        candidates = [base] if base.is_file() else list(base.rglob("*")) if base.exists() else []
        for path in candidates:
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            matches = sorted(set(personal.findall(path.read_text(encoding="utf-8", errors="replace"))))
            if matches:
                absolute_paths.append({"path": str(path.relative_to(ROOT)), "matches": matches})

    catalog = []
    for path in sorted((ROOT / "workflows" / "catalog").glob("*.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        catalog.append({
            "id": item.get("id"),
            "execution": item.get("execution"),
            "mutates_scene": item.get("mutates_scene"),
            "requires_confirmation": item.get("requires_confirmation"),
            "enabled_in_app": item.get("enabled_in_app"),
            "evidence_level": item.get("evidence_level"),
            "domains": item.get("domains"),
            "maturity": item.get("maturity"),
            "scope": item.get("scope"),
            "script_exists": (ROOT / item.get("script", "")).is_file(),
        })

    duplicates = []
    duplicate_savings = 0
    if args.hash_duplicates:
        by_size: dict[int, list[Path]] = defaultdict(list)
        for path, size in sizes.items():
            if size:
                by_size[size].append(path)
        for size, group in by_size.items():
            if len(group) < 2:
                continue
            by_hash: dict[str, list[Path]] = defaultdict(list)
            for path in group:
                by_hash[hash_file(path)].append(path)
            for digest, matches in by_hash.items():
                if len(matches) > 1:
                    duplicate_savings += size * (len(matches) - 1)
                    duplicates.append({"sha256": digest, "size": size, "paths": [str(p.relative_to(ROOT)) for p in matches]})

    nested_git = sorted(str(path.parent.relative_to(ROOT)) for path in ROOT.rglob(".git") if path.parent != ROOT)
    report = {
        "schema_version": 1,
        "root": ".",
        "totals": {"files": len(all_files), "bytes": sum(sizes.values()), "symlinks": len(links)},
        "extensions": dict(extensions.most_common()),
        "largest_files": [
            {"path": str(path.relative_to(ROOT)), "bytes": sizes[path]}
            for path in sorted(all_files, key=lambda item: sizes[item], reverse=True)[:100]
        ],
        "symlinks": links,
        "broken_symlinks": sum(item["broken"] for item in links),
        "json_errors": json_errors,
        "python_errors": python_errors,
        "active_personal_absolute_paths": absolute_paths,
        "catalog": catalog,
        "nested_git_directories": nested_git,
        "duplicate_groups": duplicates,
        "duplicate_potential_savings_bytes": duplicate_savings,
    }
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = args.output if args.output.is_absolute() else ROOT / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")
        print(output)
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
