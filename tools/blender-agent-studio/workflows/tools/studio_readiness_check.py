#!/usr/bin/env python3
"""Read-only capability readiness report for the compact Blender Team Studio."""
from __future__ import annotations

import ast
import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REQUIRED_DOCS = [
    "AGENTS.md",
    "AGENT_HANDBOOK.md",
    "standards/CORE_PRODUCTION_STANDARD.md",
    "standards/GAME_ASSET_STANDARD.md",
    "standards/RIG_ANIMATION_STANDARD.md",
    "standards/DELIVERY_STANDARD.md",
    "knowledge/BLENDER_RULES_PRIORITY.md",
    "knowledge/PHYSICAL_WORLD_OBJECT_RULES.md",
    "knowledge/SCENE_TRIAL_EVALUATION_RULES.md",
    "knowledge/style-profiles/neutral-production.md",
]


def discover_blender() -> Path | None:
    candidates = [
        Path(os.environ["BLENDER_BIN"]) if os.environ.get("BLENDER_BIN") else None,
        Path(shutil.which("blender")) if shutil.which("blender") else None,
        Path("/Applications/Blender.app/Contents/MacOS/Blender"),
    ]
    return next((path.resolve() for path in candidates if path and path.is_file()), None)


def script_check(relative: str) -> tuple[bool, dict | str]:
    result = subprocess.run(
        [sys.executable, str(ROOT / relative)], capture_output=True, text=True, check=False, timeout=180
    )
    try:
        detail: dict | str = json.loads(result.stdout)
    except Exception:
        detail = (result.stdout + result.stderr).strip()[-2000:]
    return result.returncode == 0, detail


def main() -> int:
    checks: dict[str, bool] = {}
    details: dict[str, object] = {}
    checks["required_docs"] = all((ROOT / name).is_file() for name in REQUIRED_DOCS)
    checks["no_submodules"] = not (ROOT / ".gitmodules").exists()
    checks["no_lfs_rules"] = "filter=lfs" not in (ROOT / ".gitattributes").read_text(encoding="utf-8")

    checks["asset_catalog"], details["asset_catalog"] = script_check("tools/verify_asset_catalog.py")
    checks["distribution_budget"], details["distribution_budget"] = script_check("tools/check_distribution_budget.py")

    json_errors: list[str] = []
    for base in (ROOT / "catalog", ROOT / "standards" / "profiles", ROOT / "workflows" / "catalog"):
        for path in sorted(base.glob("*.json")):
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                json_errors.append(f"{path.relative_to(ROOT)}:{exc}")
    checks["json_documents"] = not json_errors
    details["json_errors"] = json_errors

    workflow_errors: list[str] = []
    ids: list[str] = []
    for path in sorted((ROOT / "workflows" / "catalog").glob("*.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        ids.append(item.get("id", ""))
        if item.get("execution") not in {"mcp", "batch"}:
            workflow_errors.append(f"{path.name}:execution")
        if not isinstance(item.get("requires_confirmation"), bool):
            workflow_errors.append(f"{path.name}:requires_confirmation")
        if not isinstance(item.get("mutates_scene"), bool):
            workflow_errors.append(f"{path.name}:mutates_scene")
        if not isinstance(item.get("domains"), list) or not item.get("domains"):
            workflow_errors.append(f"{path.name}:domains")
        if not isinstance(item.get("maturity"), str) or not item.get("maturity"):
            workflow_errors.append(f"{path.name}:maturity")
        if item.get("scope") not in {"generic-or-adaptable", "historical-project-specific"}:
            workflow_errors.append(f"{path.name}:scope")
        if not (ROOT / item.get("script", "")).is_file():
            workflow_errors.append(f"{path.name}:missing_script")
        if item.get("execution") == "batch" and item.get("enabled_in_app") is not False:
            workflow_errors.append(f"{path.name}:batch_enabled_in_app")
        if item.get("scope") == "historical-project-specific" and item.get("enabled_in_app") is not False:
            workflow_errors.append(f"{path.name}:historical_enabled_in_app")
    if len(ids) != len(set(ids)) or not all(ids):
        workflow_errors.append("workflow_ids_missing_or_duplicate")
    checks["workflow_catalog"] = not workflow_errors
    details["workflow_errors"] = workflow_errors

    syntax_errors: list[str] = []
    for base in (ROOT / "workflows", ROOT / "app" / "backend", ROOT / "tools", ROOT / ".agents" / "skills"):
        for path in sorted(base.rglob("*.py")):
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except Exception as exc:
                syntax_errors.append(f"{path.relative_to(ROOT)}:{exc}")
    checks["python_syntax"] = not syntax_errors
    details["syntax_errors"] = syntax_errors

    blender = discover_blender()
    version = None
    if blender:
        result = subprocess.run([str(blender), "--version"], capture_output=True, text=True, check=False, timeout=30)
        version = (result.stdout or result.stderr).splitlines()[0] if result.returncode == 0 else None
    ffmpeg = bool(shutil.which("ffmpeg"))
    ffprobe = bool(shutil.which("ffprobe"))
    vault_raw = os.environ.get("BLENDER_ASSET_VAULT", "")
    vault_ready = bool(vault_raw and Path(vault_raw).expanduser().is_dir())

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        mcp_open = sock.connect_ex(("127.0.0.1", 9876)) == 0

    core_keys = ["required_docs", "no_submodules", "no_lfs_rules", "asset_catalog", "distribution_budget", "json_documents", "workflow_catalog", "python_syntax"]
    core_ready = all(checks[key] for key in core_keys)
    report = {
        "schema_version": 3,
        "root": str(ROOT),
        "ready_core": core_ready,
        "ready_for_blender_batch": core_ready and bool(version),
        "ready_for_animation_media": core_ready and bool(version) and ffmpeg and ffprobe,
        "ready_for_interactive_mcp": core_ready and bool(version) and mcp_open,
        "asset_vault_available": vault_ready,
        "checks": {**checks, "blender_binary": bool(version), "ffmpeg": ffmpeg, "ffprobe": ffprobe, "mcp_port_open": mcp_open},
        "details": details,
        "blender_version": version,
        "workflow_count": len(ids),
        "notes": {
            "asset_vault": "optional; required only to reuse catalogued legacy assets",
            "mcp": "optional; start BlenderMCP for interactive workflows",
            "media": "FFmpeg/ffprobe are required for animation, tutorial and video evidence",
        },
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if core_ready and bool(version) else 1


if __name__ == "__main__":
    raise SystemExit(main())
