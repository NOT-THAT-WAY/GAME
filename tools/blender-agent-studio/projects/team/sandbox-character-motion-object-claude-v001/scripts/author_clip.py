"""Author one clip inside the live BlenderMCP session, then checkpoint it.

Usage:
    python3 author_clip.py <CLIP_NAME>

The scene is mutated interactively over the MCP socket; nothing here runs
`--background`. The session's open file is asserted before every mutation and
again before every save, so a session that had drifted onto Kimi's master, the
SB_Idle master or the runtime FBX aborts instead of being written.
"""
from __future__ import annotations

import json
import pathlib
import sys

import mcp_client as mcp

SCRIPTS = pathlib.Path(__file__).resolve().parent
PROJECT = SCRIPTS.parent
STUDIO = PROJECT.parent.parent.parent
LOCAL = STUDIO / "local_work" / "sandbox-character-motion-object-claude-v001"
CHECKPOINTS = LOCAL / "checkpoints"

BOOTSTRAP = f"""
import sys, importlib
if {str(SCRIPTS)!r} not in sys.path:
    sys.path.insert(0, {str(SCRIPTS)!r})
import pose_kernel, clips, clip_specs
importlib.reload(pose_kernel)
importlib.reload(clips)
importlib.reload(clip_specs)
"""


def author(clip_name: str) -> dict:
    mcp.assert_owned_session()
    code = BOOTSTRAP + f"""
import json
spec = clip_specs.build({clip_name!r})
report = pose_kernel.author(
    spec["name"], spec["f_start"], spec["f_end"],
    spec["keyposes"], spec["periodic"],
)
report["declared"] = spec.get("declared", {{}})
print('<<<JSON' + json.dumps(report) + 'JSON>>>')
"""
    return mcp.run_json(code)


def checkpoint(clip_name: str) -> dict:
    """Save a versioned checkpoint. Never overwrites an earlier one."""
    mcp.assert_owned_session()
    CHECKPOINTS.mkdir(parents=True, exist_ok=True)
    existing = sorted(CHECKPOINTS.glob(f"{clip_name}_v*.blend"))
    version = len(existing) + 1
    target = CHECKPOINTS / f"{clip_name}_v{version:03d}.blend"
    if target.exists():
        raise SystemExit(f"REFUS: le checkpoint {target} existe deja")

    code = f"""
import bpy, json
# Copy save: the session keeps pointing at the master, so the ownership guard
# stays meaningful for the next clip instead of following the checkpoint.
bpy.ops.wm.save_as_mainfile(filepath={str(target)!r}, copy=True)
bpy.ops.wm.save_mainfile()
print('<<<JSON' + json.dumps({{"checkpoint": {str(target)!r},
                              "master": bpy.data.filepath}}) + 'JSON>>>')
"""
    return mcp.run_json(code)


if __name__ == "__main__":
    name = sys.argv[1]
    print(json.dumps(author(name), indent=2))
    print(json.dumps(checkpoint(name), indent=2))
