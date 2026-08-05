"""Final physical and continuity audit for the USTUDIO character film."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy


TRIAL = Path(__file__).resolve().parent
OUTPUT = TRIAL / "diagnostics" / "physical-validation.json"
SOURCE = TRIAL.parents[1] / "fl-studio-box-semantic-template" / "FL_Studio_Box_Semantic_Template.blend"
scene = bpy.context.scene
root = bpy.data.objects["USTUDIO_BOX_FLOAT_ROOT"]
character = bpy.data.objects["USTUDIO_CHARACTER_ROOT"]
hips = bpy.data.objects["USTUDIO_CHAR_RIG_HIPS"]


def local_position(obj):
    return root.matrix_world.inverted_safe() @ obj.matrix_world.translation


support_errors = []
camera_errors = []
drift_errors = []
samples = []
max_run_camera_error = 0.0
orbit_bounds = {"x": [1e9, -1e9], "y": [1e9, -1e9], "z": [1e9, -1e9]}

for frame in range(scene.frame_start, scene.frame_end + 1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    char = local_position(character)
    pelvis = local_position(hips)

    if frame <= 105 or 203 <= frame <= 406:
        if abs(char.z - 1.945) > 0.002:
            support_errors.append({"frame": frame, "rule": "bridge_root_z", "actual": char.z})
        if not (-3.25 <= char.x <= 3.25 and -0.35 <= char.y <= 0.60):
            support_errors.append({"frame": frame, "rule": "bridge_plan_bounds", "actual": list(char)})
    elif 106 <= frame <= 202:
        if abs(pelvis.z - 0.760) > 0.004:
            support_errors.append({"frame": frame, "rule": "seat_pelvis_contact", "actual": pelvis.z})
        if char.y > -0.95:
            support_errors.append({"frame": frame, "rule": "seat_front_side", "actual": char.y})

    if 203 <= frame <= 298:
        camera = bpy.data.objects["USTUDIO_CAM_SCENE3_RUN"]
        camera_local = local_position(camera)
        error = abs((camera_local.x - char.x) - 1.25)
        max_run_camera_error = max(max_run_camera_error, error)
        if error > 0.003:
            drift_errors.append({"frame": frame, "camera_character_offset_error_m": error})

    if 299 <= frame <= 406:
        camera = bpy.data.objects["USTUDIO_CAM_SCENE4_COMMUNION"]
        position = local_position(camera)
        for axis, value in zip(("x", "y", "z"), position):
            orbit_bounds[axis][0] = min(orbit_bounds[axis][0], float(value))
            orbit_bounds[axis][1] = max(orbit_bounds[axis][1], float(value))
        # Rear wall is at local y=1.36; y<=1.28 preserves the contracted 8 cm margin.
        if not (-1.35 <= position.y <= 1.28 and -1.35 <= position.x <= 1.35 and 1.95 <= position.z <= 4.75):
            camera_errors.append({"frame": frame, "rule": "orbit_corridor", "actual": list(position)})

    if frame in {1, 9, 57, 105, 106, 154, 202, 203, 251, 298, 299, 348, 396, 406}:
        samples.append({
            "frame": frame,
            "character_local": [round(float(v), 6) for v in char],
            "pelvis_local": [round(float(v), 6) for v in pelvis],
            "active_camera": scene.camera.name if scene.camera else None,
        })

frames_dir = TRIAL / "renders" / "frames"
render_files = sorted(frames_dir.glob("frame_*.png"))
bad_png = []
for path in render_files:
    data = path.read_bytes()
    if len(data) < 10_000 or not data.startswith(b"\x89PNG\r\n\x1a\n") or not data.endswith(b"IEND\xaeB`\x82"):
        bad_png.append(path.name)

playhead_back = bpy.data.objects.get("USTUDIO_PLAYHEAD_BACK")
playhead_floor = bpy.data.objects.get("USTUDIO_PLAYHEAD_FLOOR")
checks = {
    "source_exists": SOURCE.is_file(),
    "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest() if SOURCE.is_file() else None,
    "trial_is_not_source": Path(bpy.data.filepath).resolve() != SOURCE.resolve(),
    "visible_horizontal_support": bpy.data.objects.get("USTUDIO_INTERFACE_BRIDGE") is not None,
    "support_errors": len(support_errors),
    "seat_contact_errors": len([item for item in support_errors if item["rule"].startswith("seat")]),
    "camera_corridor_errors": len(camera_errors),
    "run_drift_errors": len(drift_errors),
    "max_run_camera_offset_error_m": round(max_run_camera_error, 8),
    "render_frame_count": len(render_files),
    "bad_png_count": len(bad_png),
    "playhead_back_reused": bool(playhead_back and playhead_back.parent == root),
    "floor_playhead_still_disabled": bool(playhead_floor and playhead_floor.hide_render and playhead_floor.hide_viewport),
    "camera_count_new": len([obj for obj in bpy.data.objects if obj.type == "CAMERA" and obj.name.startswith("USTUDIO_CAM_SCENE")]),
}

critical_failures = []
if support_errors:
    critical_failures.append("collision_or_environment_traversal")
if camera_errors:
    critical_failures.append("camera_or_geometry_clipping")
if drift_errors:
    critical_failures.append("unmotivated_drift_or_contact_slip")
if len(render_files) != 406 or bad_png:
    critical_failures.append("corrupt_missing_or_glitched_frames")
if not checks["playhead_back_reused"] or not checks["floor_playhead_still_disabled"]:
    critical_failures.append("canonical_identity_broken")

report = {
    "schema_version": 1,
    "passed": not critical_failures,
    "critical_failures": critical_failures,
    "method": "sample all 406 frames in evaluated Blender scene plus PNG signature/size checks",
    "checks": checks,
    "orbit_camera_local_bounds_m": {axis: [round(v, 6) for v in values] for axis, values in orbit_bounds.items()},
    "sampled_states": samples,
    "errors": {
        "support": support_errors[:20],
        "camera_corridor": camera_errors[:20],
        "run_drift": drift_errors[:20],
        "bad_png": bad_png[:20],
    },
    "physical_rule": "character is supported by the visible horizontal bridge or the real lower rim; no invisible floor",
}
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("USTUDIO_PHYSICAL_VALIDATION=" + json.dumps({"passed": report["passed"], "checks": checks, "critical_failures": critical_failures}))
