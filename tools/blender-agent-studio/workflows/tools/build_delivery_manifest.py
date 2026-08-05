#!/usr/bin/env python3
"""Hash selected local project outputs into the tracked delivery manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROJECTS = ROOT / "projects" / "team"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_file(raw: str) -> tuple[str, Path]:
    if "=" not in raw:
        raise argparse.ArgumentTypeError("--file attend role=chemin")
    role, value = raw.split("=", 1)
    if not role.strip() or not value.strip():
        raise argparse.ArgumentTypeError("role et chemin sont requis")
    return role.strip(), Path(value.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--file", action="append", type=parse_file, required=True)
    parser.add_argument("--replace-role", action="store_true")
    parser.add_argument("--validated", action="store_true", help="marquer les fichiers comme validés après contrôle métier")
    args = parser.parse_args()
    project = args.project_dir.expanduser().resolve()
    try:
        project.relative_to(PROJECTS)
    except ValueError:
        parser.error("project_dir doit rester dans projects/team/")
    manifest_path = project / "delivery-manifest.json"
    if not manifest_path.is_file():
        parser.error("delivery-manifest.json introuvable")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    existing = manifest.get("files", [])
    roles = {role for role, _ in args.file}
    if args.replace_role:
        existing = [item for item in existing if item.get("role") not in roles]
    elif roles.intersection(item.get("role") for item in existing):
        parser.error("un rôle existe déjà ; utiliser --replace-role pour le remplacer")

    records = []
    for role, raw in args.file:
        path = raw.expanduser()
        if not path.is_absolute():
            path = ROOT / path
        path = path.resolve()
        try:
            relative = path.relative_to(ROOT)
        except ValueError:
            parser.error(f"fichier hors workspace: {raw}")
        if not path.is_file():
            parser.error(f"fichier introuvable: {raw}")
        records.append(
            {
                "role": role,
                "path": relative.as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "extension": path.suffix.lower(),
                "status": "validated" if args.validated else "hashed_not_yet_validated",
            }
        )
    manifest["files"] = existing + records
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": manifest_path.relative_to(ROOT).as_posix(), "added": records}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
