#!/usr/bin/env python3
"""Replace known personal path prefixes in historical text metadata with provenance tokens."""
from __future__ import annotations

import argparse
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUFFIXES = {
    ".json", ".md", ".txt", ".toml", ".yml", ".yaml", ".srt", ".vtt",
    ".py", ".sh", ".js", ".swift", ".html", ".css", ".plist", ".csv",
}
SKIP_DIRS = {".git", "third_party", "vendor", "__pycache__"}
SKIP_FILES = {Path(".studio.local.json"), Path("app/.env")}
_LEGACY_HOME = "/".join(("", "Users", "unrecorded"))
REPLACEMENTS = (
    (_LEGACY_HOME + "/unrecorded/code/_Visual_AI_Hub", "${LEGACY_VISUAL_AI_HUB_ROOT}"),
    (_LEGACY_HOME + "/unrecorded/Blender", "${BLENDER_AGENT_STUDIO_ROOT}"),
    (_LEGACY_HOME + "/.unrecorded", "${LEGACY_MEDIA_GEN_ROOT}"),
    (_LEGACY_HOME + "/unrecorded/help", "${LEGACY_HELP_ROOT}"),
    (_LEGACY_HOME + "/unrecorded", "${LEGACY_WORKSPACE_ROOT}"),
    (_LEGACY_HOME + "/Downloads", "${ORIGINAL_DOWNLOADS}"),
    (_LEGACY_HOME + "/Movies", "${ORIGINAL_MOVIES}"),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Appliquer les remplacements ; sinon dry-run")
    args = parser.parse_args()
    changed = []
    occurrences = 0
    for current, dirs, names in os.walk(ROOT):
        relative_dir = Path(current).relative_to(ROOT)
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS and not (relative_dir == Path("prompts") and name == "legacy")]
        for name in names:
            path = Path(current) / name
            if path.relative_to(ROOT) in SKIP_FILES:
                continue
            if path.suffix.lower() not in SUFFIXES or path.is_symlink():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            updated = text
            count = 0
            for source, token in REPLACEMENTS:
                found = updated.count(source)
                if found:
                    updated = updated.replace(source, token)
                    count += found
            if count:
                changed.append(str(path.relative_to(ROOT)))
                occurrences += count
                if args.write:
                    path.write_text(updated, encoding="utf-8")
    print(f"mode={'write' if args.write else 'dry-run'} files={len(changed)} occurrences={occurrences}")
    for path in changed:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
