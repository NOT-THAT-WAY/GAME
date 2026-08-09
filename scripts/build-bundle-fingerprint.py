#!/usr/bin/env python3
"""Fingerprint every regular file in a Unity player bundle with relative paths only."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class FileEntry:
    relativePath: str
    sizeBytes: int
    sha256: str


def hash_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def fingerprint(root: Path, excluded_relative_paths: Iterable[str] = ()) -> dict[str, object]:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"bundle root is not a directory: {root}")

    excluded = {Path(item).as_posix().lstrip("./") for item in excluded_relative_paths}
    entries: list[FileEntry] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative_path = path.relative_to(root).as_posix()
        if relative_path in excluded:
            continue
        digest, size = hash_file(path)
        entries.append(FileEntry(relative_path, size, digest))

    entries.sort(key=lambda item: item.relativePath)
    canonical = "".join(
        f"{entry.relativePath}\t{entry.sizeBytes}\t{entry.sha256}\n" for entry in entries
    ).encode("utf-8")

    return {
        "schemaVersion": 1,
        "kind": "unity-build-bundle-fingerprint",
        "algorithm": "sha256-relative-path-size-content-v1",
        "fileCount": len(entries),
        "totalBytes": sum(entry.sizeBytes for entry in entries),
        "bundleManifestSha256": hashlib.sha256(canonical).hexdigest(),
        "files": [asdict(entry) for entry in entries],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--exclude", action="append", default=[], help="relative path omitted from the hash")
    parser.add_argument("--output", type=Path, help="optional JSON destination; stdout otherwise")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = fingerprint(args.root, args.exclude)
        serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.expanduser().parent.mkdir(parents=True, exist_ok=True)
            args.output.expanduser().write_text(serialized, encoding="utf-8")
        else:
            sys.stdout.write(serialized)
    except (OSError, ValueError) as error:
        print(f"BUNDLE FINGERPRINT ERROR: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
