"""Frame-by-frame physical validation of the slope run (evaluated scene, 240 frames).

All slope-frame quantities come from the ARMATURE space of K3_FABLE_RUNNER,
whose local frame is exactly the measured surface frame (Z=0 is the ramp plane).
Writes diagnostics/physical-validation.json.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector

P = globals().get("UNRECORDED_PARAMS", {})
TRIAL = Path(P.get("trial_dir", ".")).resolve()

U = Vector((0.0, 0.690377, 0.723449))
C = Vector((-1.0, 0.0, 0.0))
N = Vector((0.0, -0.723449, 0.690377))
O = Vector((0.0, 0.415, 1.755))
S_MIN, S_MAX = -1.209484, 1.209484
T_MIN, T_MAX = -3.78, 3.78
FRAME_END = 240
RUN_START, RUN_END = 57, 203

THRESH = {
    "planted_drift_max": 0.005,
    "penetration_max": 0.002,
    "swing_toe_clearance_min": 0.01,
    "root_height_error_max": 0.003,
    "camera_distance_variation_max": 0.01,
    "camera_clearance_min": 0.08,
    "surface_margin_min": 0.15,
    "feet_visible_fraction_min": 0.80,
}

GATE_FRAMES = [1, 17, 33, 49, 57, 81, 106, 130, 154, 178, 192, 203, 224, 240]

scene = bpy.context.scene
arm = bpy.data.objects["K3_FABLE_RUNNER"]
cam = bpy.data.objects["K3_FABLE_CAM_MAIN"]
root = bpy.data.objects["USTUDIO_BOX_FLOAT_ROOT"]

plan = json.loads((TRIAL / "diagnostics" / "motion-plan.json").read_text(encoding="utf-8"))
frames_plan = {fr["frame"]: fr for fr in plan["frames"]}
surface = json.loads((TRIAL / "diagnostics" / "surface-analysis.json").read_text(encoding="utf-8"))
context_bounds = surface["context_bounds_local_root"]

REST_FOOT = {s: arm.data.bones[f"FOOT.{s}"].matrix_local.copy() for s in ("L", "R")}
FOOT_LAT = {"L": 0.024, "R": -0.024}

def sole_points_rest(side):
    lat = FOOT_LAT[side]
    pts = []
    for x in (-0.016, 0.036):
        for dy in (-0.013, 0.013):
            pts.append(Vector((x, lat + dy, 0.0005)))
    return pts  # index 2,3 are the toe-side corners (x=0.036)

SOLE_REST = {s: [REST_FOOT[s].inverted() @ p for p in sole_points_rest(s)] for s in ("L", "R")}

from bpy_extras.object_utils import world_to_camera_view

def point_aabb_distance(p, bmin, bmax):
    dx = max(bmin[0] - p.x, 0.0, p.x - bmax[0])
    dy = max(bmin[1] - p.y, 0.0, p.y - bmax[1])
    dz = max(bmin[2] - p.z, 0.0, p.z - bmax[2])
    return math.sqrt(dx * dx + dy * dy + dz * dz)

def to_root_vec(v_arm):
    return U * v_arm.x + C * v_arm.y + N * v_arm.z

per_frame = []
contact_runs = {"L": [], "R": []}
current_run = {"L": None, "R": None}
metrics = {
    "max_planted_drift": {"L": 0.0, "R": 0.0},
    "max_penetration": 0.0,
    "min_swing_toe_clearance": 1e9,
    "max_root_height_error": 0.0,
    "max_planted_corner_spread": 0.0,
    "knee_inversions": 0,
    "min_surface_margin_s": 1e9,
    "min_surface_margin_t": 1e9,
    "cam_dist_min": 1e9,
    "cam_dist_max": 0.0,
    "cam_clearance_min": 1e9,
    "lean_run_min": 1e9,
    "lean_run_max": -1e9,
    "feet_in_frame": 0,
    "feet_checked": 0,
    "black_frames": [],
}
support_by_frame = {}

for f in range(1, FRAME_END + 1):
    scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    arm_e = arm.evaluated_get(dg)
    pb = arm_e.pose.bones
    plan_fr = frames_plan[f]

    pelvis = pb["ROOT"].matrix.translation.copy()
    root_err = abs(pelvis.z - plan_fr["pelvis"]["h"])
    metrics["max_root_height_error"] = max(metrics["max_root_height_error"], root_err)

    chest_y = (pb["CHEST"].matrix.col[1]).to_3d().normalized()
    chest_root_v = to_root_vec(chest_y)
    lean = math.degrees(chest_root_v.angle(Vector((0, 0, 1))))
    if RUN_START <= f <= 190:
        metrics["lean_run_min"] = min(metrics["lean_run_min"], lean)
        metrics["lean_run_max"] = max(metrics["lean_run_max"], lean)

    fwd = (pb["ROOT"].matrix.col[2]).to_3d().normalized()  # bone Z = forward hint
    frame_data = {"frame": f, "pelvis_h": round(pelvis.z, 5), "pelvis_s": round(pelvis.x, 5),
                  "root_height_error": round(root_err, 5), "lean_deg": round(lean, 2), "feet": {}}

    supports = []
    for side in ("L", "R"):
        phase = plan_fr["feet"][side]["phase"]
        m_foot = pb[f"FOOT.{side}"].matrix
        corners = [m_foot @ q for q in SOLE_REST[side]]
        zs = [c.z for c in corners]
        z_min, z_max = min(zs), max(zs)
        center = sum(corners, Vector()) / 4.0
        toe_z = min(zs[2], zs[3])
        pen = max(0.0, -z_min)
        metrics["max_penetration"] = max(metrics["max_penetration"], pen)
        for cpt in corners:
            metrics["min_surface_margin_s"] = min(metrics["min_surface_margin_s"],
                                                  cpt.x - S_MIN, S_MAX - cpt.x)
            metrics["min_surface_margin_t"] = min(metrics["min_surface_margin_t"],
                                                  cpt.y - T_MIN, T_MAX - cpt.y)
        if phase == "planted":
            supports.append(side)
            run = current_run[side]
            if run is None:
                current_run[side] = run = {"start": f, "origin": (center.x, center.y), "max_drift": 0.0,
                                           "corner_spread": 0.0}
            drift = math.hypot(center.x - run["origin"][0], center.y - run["origin"][1])
            run["max_drift"] = max(run["max_drift"], drift)
            run["corner_spread"] = max(run["corner_spread"], z_max - z_min)
            run["end"] = f
            metrics["max_planted_drift"][side] = max(metrics["max_planted_drift"][side], drift)
            metrics["max_planted_corner_spread"] = max(metrics["max_planted_corner_spread"], z_max - z_min)
        else:
            if current_run[side] is not None:
                contact_runs[side].append(current_run[side])
                current_run[side] = None
            if phase == "swing":
                metrics["min_swing_toe_clearance"] = min(metrics["min_swing_toe_clearance"], toe_z)

        hip = pb[f"THIGH.{side}"].matrix.translation
        knee = pb[f"SHIN.{side}"].matrix.translation
        ankle = pb[f"FOOT.{side}"].matrix.translation
        knee_fwd = (knee - (hip + ankle) * 0.5).dot(fwd)
        if knee_fwd < 0.0005:
            metrics["knee_inversions"] += 1
        frame_data["feet"][side] = {"phase": phase, "z_min": round(z_min, 5), "toe_z": round(toe_z, 5),
                                    "center_s": round(center.x, 5), "knee_fwd": round(knee_fwd, 5)}

    support_by_frame[f] = supports
    frame_data["support"] = supports

    # camera metrics (world space; both rigid with the float root)
    cam_e = cam.evaluated_get(dg)
    pelvis_world = arm_e.matrix_world @ pelvis
    cam_world = cam_e.matrix_world.translation
    dist = (cam_world - pelvis_world).length
    metrics["cam_dist_min"] = min(metrics["cam_dist_min"], dist)
    metrics["cam_dist_max"] = max(metrics["cam_dist_max"], dist)
    frame_data["cam_dist"] = round(dist, 5)

    root_inv = root.evaluated_get(dg).matrix_world.inverted()
    cam_root = root_inv @ cam_world
    clear = (cam_root - O).dot(N)  # height above ramp plane
    for name, bb in context_bounds.items():
        # The inclined ramp is handled by its true plane distance above; its AABB is
        # a fat diagonal slab that would falsely contain the camera. Ground and the
        # hidden floor playhead sit outside the box below the interior.
        if name in ("USTUDIO_GROUND", "USTUDIO_PLAYHEAD_FLOOR", "USTUDIO_PIANO_ROLL_FLOOR"):
            continue
        clear = min(clear, point_aabb_distance(cam_root, bb["min"], bb["max"]))
    metrics["cam_clearance_min"] = min(metrics["cam_clearance_min"], clear)
    frame_data["cam_clearance"] = round(clear, 4)

    if RUN_START <= f <= RUN_END:
        for side in ("L", "R"):
            foot_world = arm_e.matrix_world @ pb[f"FOOT.{side}"].matrix.translation
            uv = world_to_camera_view(scene, cam_e, foot_world)
            metrics["feet_checked"] += 1
            if 0.02 <= uv.x <= 0.98 and 0.02 <= uv.y <= 0.98 and uv.z > 0:
                metrics["feet_in_frame"] += 1

    per_frame.append(frame_data)

for side in ("L", "R"):
    if current_run[side] is not None:
        contact_runs[side].append(current_run[side])

feet_fraction = metrics["feet_in_frame"] / max(metrics["feet_checked"], 1)
cam_var = metrics["cam_dist_max"] - metrics["cam_dist_min"]

checks = {
    "planted_drift_ok": max(metrics["max_planted_drift"].values()) <= THRESH["planted_drift_max"],
    "penetration_ok": metrics["max_penetration"] <= THRESH["penetration_max"],
    "swing_clearance_ok": metrics["min_swing_toe_clearance"] >= THRESH["swing_toe_clearance_min"],
    "root_height_ok": metrics["max_root_height_error"] <= THRESH["root_height_error_max"],
    "camera_distance_ok": cam_var <= THRESH["camera_distance_variation_max"],
    "camera_clearance_ok": metrics["cam_clearance_min"] >= THRESH["camera_clearance_min"],
    "surface_margin_ok": metrics["min_surface_margin_s"] >= THRESH["surface_margin_min"],
    "no_knee_inversion": metrics["knee_inversions"] == 0,
    "feet_visible_ok": feet_fraction >= THRESH["feet_visible_fraction_min"],
    "lean_in_band_15_25": 15.0 <= metrics["lean_run_min"] and metrics["lean_run_max"] <= 25.0,
    "torso_not_slope_perpendicular": abs(metrics["lean_run_max"] - 46.34) > 10.0,
}
passed = all(checks.values())

payload = {
    "schema_version": 1,
    "trial_id": "k3-pianoroll-slope-run-fable-v001",
    "surface_angle_degrees": 46.34,
    "frames_evaluated": FRAME_END,
    "thresholds": THRESH,
    "results": {
        "max_planted_drift_m": {k: round(v, 6) for k, v in metrics["max_planted_drift"].items()},
        "max_penetration_m": round(metrics["max_penetration"], 6),
        "min_swing_toe_clearance_m": round(metrics["min_swing_toe_clearance"], 6),
        "max_root_height_error_m": round(metrics["max_root_height_error"], 6),
        "max_planted_sole_corner_spread_m": round(metrics["max_planted_corner_spread"], 6),
        "camera_distance_m": {"min": round(metrics["cam_dist_min"], 5), "max": round(metrics["cam_dist_max"], 5),
                               "variation": round(cam_var, 5)},
        "camera_clearance_min_m": round(metrics["cam_clearance_min"], 4),
        "surface_margin_min_m": {"uphill_s": round(metrics["min_surface_margin_s"], 4),
                                  "cross_t": round(metrics["min_surface_margin_t"], 4)},
        "knee_inversions": metrics["knee_inversions"],
        "torso_lean_run_deg": {"min": round(metrics["lean_run_min"], 2), "max": round(metrics["lean_run_max"], 2)},
        "feet_visible_fraction_run": round(feet_fraction, 4),
    },
    "checks": checks,
    "passed": passed,
    "contact_runs": {s: [{"start": r["start"], "end": r.get("end"), "max_drift_m": round(r["max_drift"], 6),
                           "corner_spread_m": round(r["corner_spread"], 6)} for r in contact_runs[s]]
                     for s in ("L", "R")},
    "gate_frames": {str(f): {
        "pelvis_h": per_frame[f - 1]["pelvis_h"],
        "pelvis_s": per_frame[f - 1]["pelvis_s"],
        "lean_deg": per_frame[f - 1]["lean_deg"],
        "support": per_frame[f - 1]["support"],
        "cam_dist": per_frame[f - 1]["cam_dist"],
        "cam_clearance": per_frame[f - 1]["cam_clearance"],
        "feet": per_frame[f - 1]["feet"],
    } for f in GATE_FRAMES},
    "per_frame": per_frame,
}
out = TRIAL / "diagnostics" / "physical-validation.json"
out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
summary = {k: v for k, v in payload["results"].items()}
summary["passed"] = passed
summary["checks"] = checks
print("UNRECORDED_RESULT=" + json.dumps(summary, ensure_ascii=False))
