"""Validate the saved composition on evaluated character geometry across all 60 frames.

Usage:
  blender --background --factory-startup <composition.blend> \
    --python validate_composition_scene.py -- <composition-validation.json>
"""

from __future__ import annotations

import bpy
import json
import math
import sys
from pathlib import Path

from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


PREFIX = "BAS_SANDBOX_CHARACTER_COMPOSITION_V001_"
STUDIO_ROOT = Path(__file__).resolve().parents[4]
EXPECTED_CHARACTER_OBJECTS = {
    "BAS_PUNCH_Body",
    "BAS_PUNCH_Fist_L",
    "BAS_PUNCH_Fist_R",
    "BAS_PUNCH_Foot_L",
    "BAS_PUNCH_Foot_R",
    "BAS_PUNCH_Forearm_L",
    "BAS_PUNCH_Forearm_R",
    "BAS_PUNCH_Rig",
    "BAS_PUNCH_UpperArm_L",
    "BAS_PUNCH_UpperArm_R",
}
SAFE = (0.06, 0.05, 0.94, 0.95)
HEIGHT_TARGET = (0.64, 0.82)
WIDTH_MAX = 0.70
CENTER_MAX = (0.08, 0.08)


def evaluated_world_vertices(scene, depsgraph):
    points = []
    for name in sorted(EXPECTED_CHARACTER_OBJECTS):
        original = bpy.data.objects[name]
        if original.type != "MESH":
            continue
        evaluated = original.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            points.extend(evaluated.matrix_world @ vertex.co for vertex in mesh.vertices)
        finally:
            evaluated.to_mesh_clear()
    return points


def camera_frame_metrics(scene, camera, points):
    projected = [world_to_camera_view(scene, camera, point) for point in points]
    xs = [point.x for point in projected]
    ys = [point.y for point in projected]
    zs = [point.z for point in projected]
    bounds = [min(xs), min(ys), max(xs), max(ys)]
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    center = [(bounds[0] + bounds[2]) * 0.5, (bounds[1] + bounds[3]) * 0.5]
    return {
        "bounds": [round(value, 6) for value in bounds],
        "width_coverage": round(width, 6),
        "height_coverage": round(height, 6),
        "center_offset": [round(center[0] - 0.5, 6), round(center[1] - 0.5, 6)],
        "depth_range_m": [round(min(zs), 6), round(max(zs), 6)],
        "safe_frame": bounds[0] >= SAFE[0] and bounds[1] >= SAFE[1] and bounds[2] <= SAFE[2] and bounds[3] <= SAFE[3],
        "clip_clear": min(zs) > camera.data.clip_start and max(zs) < camera.data.clip_end,
    }


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) != 1:
        raise SystemExit("expected: <composition-validation.json>")
    output = Path(argv[0]).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    scene = bpy.context.scene
    hero = bpy.data.objects.get(PREFIX + "CAM_HERO_3Q")
    stage = bpy.data.objects.get(PREFIX + "STAGE_CYCLORAMA")
    character_collection = bpy.data.collections.get(PREFIX + "CHARACTER_LOCKED")
    if not hero or hero.type != "CAMERA" or scene.camera != hero:
        raise RuntimeError("active hero camera contract missing")
    if not stage or not character_collection:
        raise RuntimeError("stage or locked character collection missing")
    if {obj.name for obj in character_collection.objects} != EXPECTED_CHARACTER_OBJECTS:
        raise RuntimeError("locked character collection changed")

    depsgraph = bpy.context.evaluated_depsgraph_get()
    frames = []
    ground_min = math.inf
    camera_clearance = math.inf
    camera_origin = hero.matrix_world.translation.copy()
    root = bpy.data.objects["BAS_PUNCH_Rig"]
    root_identity_max = 0.0

    for frame in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        points = evaluated_world_vertices(scene, depsgraph)
        metrics = camera_frame_metrics(scene, hero, points)
        metrics["frame"] = frame
        frames.append(metrics)
        ground_min = min(ground_min, min(point.z for point in points))
        camera_clearance = min(camera_clearance, min((point - camera_origin).length for point in points))
        root_identity_max = max(
            root_identity_max,
            max(abs(value - expected) for value, expected in zip(
                [value for row in root.matrix_world for value in row],
                [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0],
            )),
        )

    worst = {
        "min_left_margin": min(item["bounds"][0] for item in frames),
        "min_bottom_margin": min(item["bounds"][1] for item in frames),
        "min_right_margin": min(1.0 - item["bounds"][2] for item in frames),
        "min_top_margin": min(1.0 - item["bounds"][3] for item in frames),
        "height_coverage_range": [min(item["height_coverage"] for item in frames), max(item["height_coverage"] for item in frames)],
        "width_coverage_max": max(item["width_coverage"] for item in frames),
        "center_offset_abs_max": [
            max(abs(item["center_offset"][0]) for item in frames),
            max(abs(item["center_offset"][1]) for item in frames),
        ],
        "ground_min_z_m": ground_min,
        "camera_to_character_clearance_min_m": camera_clearance,
        "root_identity_max_abs": root_identity_max,
    }
    checks = {
        "all_frames_in_safe_frame": all(item["safe_frame"] for item in frames),
        "all_frames_clip_clear": all(item["clip_clear"] for item in frames),
        "height_coverage_in_target": worst["height_coverage_range"][0] >= HEIGHT_TARGET[0] and worst["height_coverage_range"][1] <= HEIGHT_TARGET[1],
        "width_coverage_under_max": worst["width_coverage_max"] <= WIDTH_MAX,
        "center_offset_under_max": worst["center_offset_abs_max"][0] <= CENTER_MAX[0] and worst["center_offset_abs_max"][1] <= CENTER_MAX[1],
        "ground_contact_plane_consistent": abs(ground_min) <= 0.0005 and abs(float(stage.get("support_plane_z", 999.0))) <= 1e-9,
        "camera_clearance": camera_clearance >= 0.08,
        "root_object_identity": root_identity_max <= 1e-9,
        "render_resolution": [scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage] == [1920, 1080, 100],
        "dof_disabled_for_baseline": not hero.data.dof.use_dof,
        "runtime_export_disabled": scene.get("runtime_export") is False,
    }
    payload = {
        "schema_version": 2,
        "project_id": "sandbox-character-composition-v001",
        "source": Path(bpy.data.filepath).resolve().relative_to(STUDIO_ROOT).as_posix(),
        "method": "all evaluated character mesh vertices after armature/modifiers, projected through the saved hero camera; every frame 1-60",
        "coordinate_frame": "Blender world Z-up, metres; normalized camera frame x/y in [0,1]",
        "thresholds": {
            "safe_frame": SAFE,
            "height_coverage": HEIGHT_TARGET,
            "width_coverage_max": WIDTH_MAX,
            "center_offset_abs_max": CENTER_MAX,
            "camera_clearance_min_m": 0.08,
            "support_plane_z_m": 0.0,
        },
        "sample_frame_step": 1,
        "frame_range": [scene.frame_start, scene.frame_end],
        "worst": worst,
        "checks": checks,
        "passed": all(checks.values()),
        "critical_failures": [] if all(checks.values()) else [name for name, passed in checks.items() if not passed],
        "frames": frames,
        "limitations": [
            "This validates technical composition and contact visibility, not final artistic taste.",
            "Ray-based occlusion is confirmed by the rendered hero/front/profile gates, not inferred from projection alone.",
        ],
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("COMPOSITION_VALIDATION " + ("PASS" if payload["passed"] else "FAIL"))
    print(json.dumps({"worst": worst, "failed": payload["critical_failures"]}, ensure_ascii=False))
    if not payload["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
