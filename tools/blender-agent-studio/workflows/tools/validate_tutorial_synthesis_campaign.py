"""Host-side validation for the progressive tutorial synthesis campaign."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = ROOT / "projects" / "tutorial-synthesis-lab-2026-07-19"
EXPECTED_STAGES = [
    "01-clay-object-motion",
    "02-camera-language",
    "03-procedural-lookdev",
    "04-mechanical-choreography",
    "05-environment-shot",
    "06-final-multishot",
]


def luma(image):
    return ImageStat.Stat(image.convert("L")).mean[0]


def delta(a, b):
    return ImageStat.Stat(ImageChops.difference(a, b).convert("L")).mean[0]


errors = []
warnings = []
stage_reports = []

preview = CAMPAIGN / "final-preview.mp4"
preview_frames = sorted((CAMPAIGN / "final-preview-frames").glob("frame_*.png"))
if not preview.exists() or preview.stat().st_size < 100_000:
    errors.append("final_preview_missing_or_small")
if len(preview_frames) != 240:
    errors.append(f"final_preview_frame_count:{len(preview_frames)}")

for stage_name in EXPECTED_STAGES:
    stage_dir = CAMPAIGN / "stages" / stage_name
    manifest_path = stage_dir / "manifest.json"
    if not manifest_path.exists():
        errors.append(f"manifest_missing:{stage_name}")
        continue
    manifest = json.loads(manifest_path.read_text())
    blend = ROOT / manifest["blend_file"]
    if not blend.exists() or blend.stat().st_size < 100_000:
        errors.append(f"blend_missing_or_small:{stage_name}")
    images = []
    image_reports = []
    for item in manifest["snapshots"]:
        path = ROOT / item["path"]
        if not path.exists():
            errors.append(f"snapshot_missing:{stage_name}:{path.name}")
            continue
        image = Image.open(path).convert("RGB")
        images.append((item["frame"], image))
        mean = luma(image)
        extrema = ImageStat.Stat(image.convert("L")).extrema[0]
        if image.size != tuple(manifest["resolution"]):
            errors.append(f"snapshot_resolution:{stage_name}:{path.name}:{image.size}")
        if mean < 5 or mean > 248:
            warnings.append(f"extreme_luma:{stage_name}:{path.name}:{mean:.2f}")
        image_reports.append({"frame": item["frame"], "mean_luma": round(mean, 3), "extrema": extrema})
    deltas = []
    for (frame_a, image_a), (frame_b, image_b) in zip(images, images[1:]):
        deltas.append({"from": frame_a, "to": frame_b, "mean_abs_delta": round(delta(image_a, image_b), 3)})
    if images and max((item["mean_abs_delta"] for item in deltas), default=0) < 2:
        errors.append(f"animation_not_observable:{stage_name}")
    if not manifest.get("validation", {}).get("passed"):
        errors.append(f"blender_validation_failed:{stage_name}")
    stage_reports.append({
        "stage": manifest["stage"],
        "stage_name": stage_name,
        "blend_bytes": blend.stat().st_size if blend.exists() else 0,
        "snapshot_count": len(images),
        "image_metrics": image_reports,
        "adjacent_deltas": deltas,
        "blender_validation": manifest.get("validation"),
    })

tutorial_reports = []
for manifest_path in sorted((ROOT / "knowledge" / "tutorials").glob("*/manifest.json")):
    folder = manifest_path.parent
    manifest = json.loads(manifest_path.read_text())
    required = ["analysis.json", "ANALYSIS.md", "probe.json", "audio.wav", "contact-sheet.jpg"]
    missing = [name for name in required if not (folder / name).exists()]
    source = folder / "source.mp4"
    if not source.exists():
        source = folder / "source-proxy.mp4"
    if missing or not source.exists():
        errors.append(f"tutorial_incomplete:{folder.name}:{missing}")
    if manifest.get("analysis_status") != "completed":
        errors.append(f"tutorial_analysis_incomplete:{folder.name}")
    tutorial_reports.append({
        "id": manifest.get("id"),
        "folder": folder.name,
        "analysis_status": manifest.get("analysis_status"),
        "source_bytes": source.stat().st_size if source.exists() else 0,
        "missing": missing,
    })

report = {
    "schema_version": 1,
    "validated_at": datetime.now(timezone.utc).isoformat(),
    "passed": not errors,
    "errors": errors,
    "warnings": warnings,
    "final_preview": {
        "path": str(preview.relative_to(ROOT)),
        "bytes": preview.stat().st_size if preview.exists() else 0,
        "frame_count": len(preview_frames),
    },
    "tutorials": tutorial_reports,
    "stages": stage_reports,
}
(CAMPAIGN / "validation-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({
    "passed": report["passed"],
    "errors": errors,
    "warnings": warnings,
    "tutorial_count": len(tutorial_reports),
    "stage_count": len(stage_reports),
    "snapshot_count": sum(stage["snapshot_count"] for stage in stage_reports),
}, indent=2, ensure_ascii=False))
raise SystemExit(0 if report["passed"] else 1)
