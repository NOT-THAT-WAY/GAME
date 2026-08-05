"""Validate a Blender Agent Studio asset-build package and its export evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BUILDS = ROOT / "projects" / "asset-builds"


def load(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.is_file():
        errors.append(f"missing:{path.name}")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"invalid_json:{path.name}:{exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"json_not_object:{path.name}")
        return {}
    return value


def unresolved(value: Any) -> bool:
    if isinstance(value, dict):
        return any(unresolved(child) for child in value.values())
    if isinstance(value, list):
        return any(unresolved(child) for child in value)
    return isinstance(value, str) and ("TO_" in value or "À compléter" in value or "__" in value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asset_dir", type=Path)
    parser.add_argument("--stage", choices=("scaffold", "final"), default="scaffold")
    args = parser.parse_args()
    asset = args.asset_dir.expanduser().resolve()
    try:
        asset.relative_to(BUILDS)
    except ValueError:
        parser.error("asset_dir doit rester dans projects/asset-builds/")

    errors: list[str] = []
    warnings: list[str] = []
    for folder in ("source", "references", "diagnostics", "gates", "exports"):
        if not (asset / folder).is_dir():
            errors.append(f"missing_directory:{folder}")
    brief = load(asset / "brief.json", errors)
    contract = load(asset / "asset-contract.json", errors)
    manifest = load(asset / "asset-manifest.json", errors)
    asset_id = manifest.get("asset_id") or brief.get("asset_id")
    if asset.name != asset_id or contract.get("asset_id") != asset_id or brief.get("asset_id") != asset_id:
        errors.append("asset_id_mismatch")
    if unresolved({"brief": brief, "contract": contract}):
        (warnings if args.stage == "scaffold" else errors).append("unresolved_contract_fields")

    if args.stage == "final":
        blend = asset / "source" / "asset.blend"
        if not blend.is_file() or blend.stat().st_size < 100_000:
            errors.append("asset_blend_missing_or_small")
        for relative, minimum in (("diagnostics/asset-audit.json", 10), ("gates/contact-sheet.jpg", 10_000), ("FINAL_REVIEW.md", 500)):
            path = asset / relative
            if not path.is_file() or path.stat().st_size < minimum:
                errors.append(f"final_artifact_missing_or_small:{relative}")
        load(asset / "diagnostics" / "asset-audit.json", errors)
        formats = brief.get("delivery", {}).get("formats", [])
        export_validation = {}
        if any(fmt != "blend" for fmt in formats):
            export_validation = load(asset / "diagnostics" / "export-validation.json", errors)
        checks = export_validation.get("exports", []) if export_validation else []
        for fmt in formats:
            if fmt == "blend":
                continue
            expected = asset / "exports" / f"{asset_id}.{fmt.lower()}"
            if not expected.is_file():
                errors.append(f"export_missing:{fmt}")
            evidence = next((item for item in checks if item.get("format", "").lower() == fmt.lower()), None)
            if not evidence or evidence.get("reimported") is not True or evidence.get("passed") is not True:
                errors.append(f"export_reimport_not_proven:{fmt}")
        if contract.get("mechanics", {}).get("articulated") is True:
            if not (asset / "diagnostics" / "physical-validation.json").is_file():
                errors.append("articulated_asset_physical_validation_missing")

    report = {
        "schema_version": 1,
        "asset_id": asset_id,
        "stage": args.stage,
        "package_valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "note": "package_valid proves package completeness, not artistic or physical quality",
    }
    (asset / "validation-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
