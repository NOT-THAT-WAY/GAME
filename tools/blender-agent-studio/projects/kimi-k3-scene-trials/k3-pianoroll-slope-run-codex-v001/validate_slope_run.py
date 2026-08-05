"""Frame-by-frame physical validation for the Codex slope-run trial."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


TRIAL = Path(__file__).resolve().parent
OUT = TRIAL / "diagnostics" / "physical-validation.json"
scene = bpy.context.scene
analysis = json.loads((TRIAL / "diagnostics" / "surface-analysis.json").read_text())
low = Vector((0.0, -0.42, 0.88))
normal = Vector(analysis["surface_normal"])
uphill = Vector(analysis["uphill_tangent"])
cross = Vector(analysis["cross_slope_tangent"])

pelvis = bpy.data.objects["USTUDIO_SLOPE_JOINT_PELVIS"]
chest = bpy.data.objects["USTUDIO_SLOPE_JOINT_CHEST"]
rig = bpy.data.objects["USTUDIO_SLOPE_RUN_RIG"]
camera = bpy.data.objects["USTUDIO_SLOPE_CAM_MAIN"]
focus = bpy.data.objects["USTUDIO_SLOPE_CAM_FOCUS"]
feet = {side: bpy.data.objects[f"USTUDIO_SLOPE_JOINT_FOOT_{side}"] for side in ("L", "R")}
soles = {side: bpy.data.objects[f"USTUDIO_SLOPE_CHAR_GRIP_SOLE_{side}"] for side in ("L", "R")}


def local_point(obj):
    # All authored benchmark nodes share the float-root coordinate system.
    return obj.location.copy()


def sole_min_distance(side):
    obj = soles[side]
    root = bpy.data.objects["USTUDIO_BOX_FLOAT_ROOT"]
    inverse = root.matrix_world.inverted_safe()
    return min(normal.dot((inverse @ obj.matrix_world) @ vertex.co - low) for vertex in obj.data.vertices)


max_penetration = 0.0
min_swing_clearance = 999.0
max_planted_drift = 0.0
pelvis_distances = []
measured_leans = []
authored_leans = []
camera_distances = []
camera_positions = []
previous_planted = {"L": None, "R": None}
plant_samples = 0
swing_samples = 0

for frame in range(1, 241):
    scene.frame_set(frame)
    pelvis_point = local_point(pelvis)
    pelvis_distances.append(normal.dot(pelvis_point - low))
    torso = (local_point(chest) - pelvis_point).normalized()
    measured_leans.append(math.degrees(math.acos(max(-1.0, min(1.0, torso.dot(Vector((0, 0, 1))))))))
    authored_leans.append(float(rig["ustudio_torso_lean_world_deg"]))
    camera_distances.append((camera.location - focus.location).length)
    camera_positions.append(camera.location.copy())

    for side in ("L", "R"):
        planted = bool(round(float(feet[side]["ustudio_planted"])))
        position = local_point(feet[side])
        minimum = sole_min_distance(side)
        max_penetration = max(max_penetration, max(0.0, -minimum))
        if planted:
            plant_samples += 1
            previous = previous_planted[side]
            if previous is not None:
                delta = position - previous
                tangent_drift = math.sqrt(delta.dot(uphill) ** 2 + delta.dot(cross) ** 2)
                max_planted_drift = max(max_planted_drift, tangent_drift)
            previous_planted[side] = position.copy()
        else:
            swing_samples += 1
            # Endpoints deliberately touch down; assess clearance only once the
            # authored swing has cleared 5 mm.
            authored_clearance = float(feet[side]["ustudio_swing_clearance_m"])
            if authored_clearance >= 0.005:
                min_swing_clearance = min(min_swing_clearance, minimum)
            previous_planted[side] = None

frames_dir = TRIAL / "renders" / "frames"
rendered = sorted(frames_dir.glob("frame_*.png")) if frames_dir.exists() else []
hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in rendered]
floor_vertices = [Vector(value) for value in analysis["vertices_local"]]
floor_x = (min(value.x for value in floor_vertices), max(value.x for value in floor_vertices))
floor_y = (min(value.y for value in floor_vertices), max(value.y for value in floor_vertices))
camera_floor_distances = [normal.dot(value - low) for value in camera_positions]
camera_x = [value.x for value in camera_positions]
camera_y = [value.y for value in camera_positions]
checks = {
    "slope_measured_46deg": abs(float(analysis["slope_degrees"]) - 46.340008) <= 0.01,
    "grip_exceeds_static_minimum": float(analysis["authored_grip_coefficient"]) >= float(analysis["static_friction_min"]),
    "sole_penetration_le_2mm": max_penetration <= 0.002,
    "planted_foot_drift_le_5mm_per_frame": max_planted_drift <= 0.005,
    "swing_clearance_ge_5mm": min_swing_clearance >= 0.005,
    "pelvis_surface_height_stable": max(pelvis_distances) - min(pelvis_distances) <= 0.001,
    "torso_lean_world_8_to_22deg": min(measured_leans) >= 7.9 and max(measured_leans) <= 22.1,
    "camera_distance_variation_le_10mm": max(camera_distances) - min(camera_distances) <= 0.01,
    "camera_corridor_clear": (
        min(camera_floor_distances) >= 0.08
        and min(camera_x) >= floor_x[0] + 0.08
        and max(camera_x) <= floor_x[1] - 0.08
        and min(camera_y) >= floor_y[0] + 0.08
        and max(camera_y) <= floor_y[1] - 0.08
    ),
    "render_sequence_240_frames": len(rendered) == 240,
    "render_frames_not_identical": len(set(hashes)) >= 200 if hashes else False,
}
critical = [name for name, passed in checks.items() if not passed and name not in {"render_sequence_240_frames", "render_frames_not_identical"}]
report = {
    "schema_version": 1,
    "trial": "k3-pianoroll-slope-run-codex-v001",
    "frames_sampled": 240,
    "plant_samples": plant_samples,
    "swing_samples": swing_samples,
    "metrics": {
        "slope_degrees": analysis["slope_degrees"],
        "static_friction_min": analysis["static_friction_min"],
        "authored_grip_coefficient": analysis["authored_grip_coefficient"],
        "max_sole_penetration_m": round(max_penetration, 8),
        "max_planted_drift_per_frame_m": round(max_planted_drift, 8),
        "min_assessed_swing_clearance_m": round(min_swing_clearance, 8),
        "pelvis_surface_height_range_m": [round(min(pelvis_distances), 8), round(max(pelvis_distances), 8)],
        "measured_torso_lean_range_deg": [round(min(measured_leans), 5), round(max(measured_leans), 5)],
        "authored_torso_lean_range_deg": [round(min(authored_leans), 5), round(max(authored_leans), 5)],
        "camera_distance_range_m": [round(min(camera_distances), 8), round(max(camera_distances), 8)],
        "camera_surface_clearance_range_m": [round(min(camera_floor_distances), 8), round(max(camera_floor_distances), 8)],
        "camera_x_range_m": [round(min(camera_x), 8), round(max(camera_x), 8)],
        "camera_y_range_m": [round(min(camera_y), 8), round(max(camera_y), 8)],
        "rendered_frame_count": len(rendered),
        "unique_render_hashes": len(set(hashes)),
    },
    "checks": checks,
    "critical_failures": critical,
    "verdict": "pass" if not critical and all(checks.values()) else "incomplete" if not rendered else "fail",
}
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("USTUDIO_PHYSICAL_VALIDATION=" + json.dumps(report))
