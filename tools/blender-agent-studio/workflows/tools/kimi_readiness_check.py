"""Read-only environment and repository readiness check for Kimi K3."""
from __future__ import annotations

import json
import shutil
import socket
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BLENDER = Path("/Applications/Blender.app/Contents/MacOS/Blender")
REQUIRED_DOCS = [
    "AGENTS.md",
    "KIMI_K3_HANDOFF.md",
    "knowledge/PHYSICAL_WORLD_OBJECT_RULES.md",
    "knowledge/SCENE_TRIAL_EVALUATION_RULES.md",
    "knowledge/tutorials/DRUMBOIII_DIRECTION.md",
    "knowledge/BLENDER_AGENT_LOOP.md",
]
REQUIRED_WORKFLOWS = {
    "inspect-scene",
    "deep-audit-scene",
    "scene-spatial-graph",
    "scene-view-diagnostics",
    "build-camera-shot",
    "studio-lighting",
    "drumboiii-lighting-gate",
    "render-keyframes",
    "validate-articulated-object",
    "iteration-manifest",
}


def main() -> int:
    checks = {}
    checks["workspace"] = ROOT.is_dir()
    checks["source_blend"] = (ROOT / "Pulsed_3D_model.blend").is_file()
    checks["required_docs"] = all((ROOT / name).is_file() for name in REQUIRED_DOCS)
    checks["ffmpeg"] = bool(shutil.which("ffmpeg"))
    checks["ffprobe"] = bool(shutil.which("ffprobe"))
    checks["blender_binary"] = BLENDER.is_file()

    version = None
    if checks["blender_binary"]:
        result = subprocess.run([str(BLENDER), "--version"], capture_output=True, text=True, check=False, timeout=30)
        version = (result.stdout or result.stderr).splitlines()[0] if result.returncode == 0 else None
    checks["blender_version_readable"] = bool(version)

    catalog_errors = []
    workflow_ids = []
    for path in sorted((ROOT / "workflows" / "catalog").glob("*.json")):
        try:
            workflow_ids.append(json.loads(path.read_text(encoding="utf-8"))["id"])
        except Exception as exc:
            catalog_errors.append(f"{path.name}:{exc}")
    checks["catalog_json_valid"] = not catalog_errors
    checks["workflow_ids_unique"] = len(workflow_ids) == len(set(workflow_ids))
    checks["required_workflows"] = REQUIRED_WORKFLOWS.issubset(workflow_ids)

    script_errors = []
    for path in sorted((ROOT / "workflows" / "scripts").glob("*.py")):
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except Exception as exc:
            script_errors.append(f"{path.name}:{exc}")
    checks["workflow_scripts_compile"] = not script_errors

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        mcp_open = sock.connect_ex(("127.0.0.1", 9876)) == 0

    batch_requirements = [key for key in checks if key != "mcp_port_open"]
    report = {
        "schema_version": 1,
        "root": str(ROOT),
        "ready_for_batch": all(checks[key] for key in batch_requirements),
        "ready_for_interactive_mcp": all(checks[key] for key in batch_requirements) and mcp_open,
        "checks": {**checks, "mcp_port_open": mcp_open},
        "blender_version": version,
        "workflow_count": len(workflow_ids),
        "required_workflows": sorted(REQUIRED_WORKFLOWS),
        "catalog_errors": catalog_errors,
        "script_errors": script_errors,
        "mcp_note": "Port 9876 fermé: ouvrir Blender et démarrer BlenderMCP si un essai interactif est souhaité." if not mcp_open else "BlenderMCP écoute sur 127.0.0.1:9876.",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready_for_batch"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
