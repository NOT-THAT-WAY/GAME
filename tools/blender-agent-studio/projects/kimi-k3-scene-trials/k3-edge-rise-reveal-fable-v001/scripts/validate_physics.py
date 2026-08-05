"""Frame-by-frame physical validation against the real geometry.

Measures, in the local frame of USTUDIO_BOX_FLOAT_ROOT and from the EVALUATED
mesh (not the plan): foot contact height vs the actual ground under it,
penetration, planted-foot drift, and body height. Writes
diagnostics/physical-validation.json.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector

P = globals().get("UNRECORDED_PARAMS", {})
TRIAL = Path(P.get("trial_dir", ".")).resolve()
FRAME_END = 360

RIM_Z = 0.76
RAMP_EDGE_Y = -0.42
RAMP_ORIGIN = Vector((0.0, 0.415, 1.755))
RAMP_SLOPE = math.tan(math.radians(46.34))

RIM_BACK_Y = -0.36     # the rim shelf continues under the ramp lip to here

def ramp_z(y):
    return RAMP_ORIGIN.z + (y - RAMP_ORIGIN.y) * RAMP_SLOPE

def ground_z(y, z=None):
    """Height of the real support under a point.

    The rim shelf (z=0.76) and the ramp lip overlap between y=-0.42 and
    y=-0.36, so a point in that band that sits below the lip is still standing
    over the rim, not inside the ramp.
    """
    if y < RAMP_EDGE_Y:
        return RIM_Z
    r = ramp_z(y)
    if z is not None and y <= RIM_BACK_Y and z < r - 0.02:
        return RIM_Z
    return r

scene = bpy.context.scene
root = bpy.data.objects["USTUDIO_BOX_FLOAT_ROOT"]
arm = bpy.data.objects["K3_FABLE_MASCOT"]
body = bpy.data.objects["K3_MECHA_BODY"]
head = bpy.data.objects["K3_MECHA_HEAD"]

# vertices belonging to each foot, taken from the skin weights
gi = {g.index: g.name for g in body.vertex_groups}
foot_verts = {"L": [], "R": []}
for v in body.data.vertices:
    if not v.groups:
        continue
    best = max(v.groups, key=lambda g: g.weight)
    name = gi.get(best.group, "")
    if name.startswith("FOOT."):
        foot_verts[name[-1]].append(v.index)

plan = json.loads((TRIAL / "diagnostics" / "motion-plan.json").read_text(encoding="utf-8"))
planted = {}
for side in ("L", "R"):
    planted[side] = {row[0]: row[4] for row in plan["contacts"][side]}

per_frame = []
runs = {"L": [], "R": []}
current = {"L": None, "R": None}
metrics = {"max_penetration": 0.0, "min_clearance_planted": 9.9, "max_planted_drift": {"L": 0.0, "R": 0.0},
           "min_swing_clearance": 9.9, "body_lowest": 9.9, "max_body_height": 0.0,
           "frames_feet_off_ground": []}

for f in range(1, FRAME_END + 1):
    scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    body_e = body.evaluated_get(dg)
    mesh = body_e.to_mesh()
    to_local = root.matrix_world.inverted() @ body_e.matrix_world
    coords = [to_local @ mesh.vertices[i].co for i in range(len(mesh.vertices))]

    row = {"frame": f, "feet": {}}
    for side in ("L", "R"):
        pts = [coords[i] for i in foot_verts[side]]
        lowest = min(pts, key=lambda p: p.z - ground_z(p.y, p.z))
        gap = lowest.z - ground_z(lowest.y, lowest.z)
        # drift is measured on the actual bearing patch (the vertices touching
        # the ground), not the whole foot: rotating a rounded sole around a
        # fixed contact moves its centroid without any sliding
        patch = [p for p in pts if p.z - ground_z(p.y, p.z) < gap + 0.004]
        centroid = sum(patch, Vector()) / len(patch)
        is_planted = bool(planted[side].get(f, False))
        row["feet"][side] = {"gap": round(gap, 5), "planted": is_planted,
                             "cx": round(centroid.x, 5), "cy": round(centroid.y, 5)}
        if gap < 0:
            metrics["max_penetration"] = max(metrics["max_penetration"], -gap)
        if is_planted:
            metrics["min_clearance_planted"] = min(metrics["min_clearance_planted"], gap)
            run = current[side]
            if run is None:
                current[side] = run = {"start": f, "origin": (centroid.x, centroid.y), "drift": 0.0}
            drift = math.hypot(centroid.x - run["origin"][0], centroid.y - run["origin"][1])
            run["drift"] = max(run["drift"], drift)
            run["end"] = f
            metrics["max_planted_drift"][side] = max(metrics["max_planted_drift"][side], drift)
        else:
            if current[side] is not None:
                runs[side].append(current[side])
                current[side] = None
            metrics["min_swing_clearance"] = min(metrics["min_swing_clearance"], gap)

    if not (row["feet"]["L"]["planted"] or row["feet"]["R"]["planted"]):
        metrics["frames_feet_off_ground"].append(f)

    head_e = head.evaluated_get(dg)
    hmesh = head_e.to_mesh()
    to_local_h = root.matrix_world.inverted() @ head_e.matrix_world
    top = max((to_local_h @ v.co).z for v in hmesh.vertices)
    head_e.to_mesh_clear()
    idx_low = min(range(len(coords)), key=lambda i: coords[i].z - ground_z(coords[i].y, coords[i].z))
    lowest_body = coords[idx_low].z - ground_z(coords[idx_low].y, coords[idx_low].z)
    if lowest_body < metrics["body_lowest"]:
        metrics["body_lowest"] = lowest_body
        # the evaluated mesh may not share indices with the base mesh, so the
        # position is what identifies the offender
        arm_e = arm.evaluated_get(dg)
        to_l = root.matrix_world.inverted() @ arm_e.matrix_world
        metrics["body_lowest_detail"] = {
            "frame": f, "pos": [round(c, 4) for c in coords[idx_low]],
            "ground_here": round(ground_z(coords[idx_low].y, coords[idx_low].z), 4),
            "bones": {b.name: [round(c, 4) for c in (to_l @ b.matrix.translation)]
                      for b in arm_e.pose.bones}}
    stand_h = top - ground_z(min(row["feet"]["L"]["cy"], row["feet"]["R"]["cy"]))
    metrics["max_body_height"] = max(metrics["max_body_height"], stand_h)
    row["head_top_z"] = round(top, 4)
    row["standing_height"] = round(stand_h, 4)
    body_e.to_mesh_clear()
    per_frame.append(row)

for side in ("L", "R"):
    if current[side] is not None:
        runs[side].append(current[side])

shot = json.loads((TRIAL / "shot-manifest.json").read_text(encoding="utf-8"))
framing = shot["framing_check"]

checks = {
    "no_penetration": metrics["max_penetration"] <= 0.004,
    "planted_drift_ok": max(metrics["max_planted_drift"].values()) <= 0.005,
    "always_supported": len(metrics["frames_feet_off_ground"]) == 0,
    "no_body_through_floor": metrics["body_lowest"] >= -0.004,
    "camera_clearance_ok": framing["min_clearance"] >= 0.08,
    "subject_always_in_frame": len(framing["subject_out_of_frame"]) == 0,
    "subject_readable_at_end": framing["min_subject_height_fraction"] >= 0.12,
}
payload = {
    "schema_version": 1,
    "trial_id": "k3-edge-rise-reveal-fable-v001",
    "frames": FRAME_END,
    "ground_model": {"rim_z": RIM_Z, "ramp_edge_y": RAMP_EDGE_Y,
                     "ramp_slope_deg": 46.34, "lip_height_m": round(ground_z(-0.41) - RIM_Z, 4)},
    "results": {
        "max_penetration_m": round(metrics["max_penetration"], 5),
        "min_planted_gap_m": round(metrics["min_clearance_planted"], 5),
        "max_planted_drift_m": {k: round(v, 5) for k, v in metrics["max_planted_drift"].items()},
        "min_swing_gap_m": round(metrics["min_swing_clearance"], 5),
        "lowest_body_point_vs_ground_m": round(metrics["body_lowest"], 5),
        "lowest_body_point_detail": metrics.get("body_lowest_detail"),
        "max_standing_height_m": round(metrics["max_body_height"], 4),
        "frames_with_no_foot_planted": metrics["frames_feet_off_ground"][:20],
        "camera_min_clearance_m": framing["min_clearance"],
        "subject_height_fraction_min": framing["min_subject_height_fraction"],
    },
    "contact_runs": {s: [{"start": r["start"], "end": r.get("end"), "drift_m": round(r["drift"], 5)}
                          for r in runs[s]] for s in ("L", "R")},
    "checks": checks,
    "passed": all(checks.values()),
    "per_frame": per_frame,
}
(TRIAL / "diagnostics" / "physical-validation.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps({**payload["results"], "checks": checks,
                                          "passed": payload["passed"]}, ensure_ascii=False))
