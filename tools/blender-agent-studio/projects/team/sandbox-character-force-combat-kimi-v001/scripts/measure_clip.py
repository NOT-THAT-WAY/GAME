# Generic physical validation for one Kimi pole clip, on EVALUATED geometry.
#
# Measures in the declared world frame (Blender Z-up, metres), every frame
# (sample_frame_step = 1):
#   - root bone + armature object immobility
#   - planted-foot drift / ground penetration (feet declared planted over the
#     whole clip or per-frame windows)
#   - ground contact for meshes declared as intended contacts (KO/Recover)
#   - all 36 mesh pairs: socket non-aggravation vs rest baseline, clearance
#     for non-adjacent pairs
#   - loop seam (cyclic) when the clip loops
#   - interface poses: per-bone numeric comparison (e.g. f30 of SB_Knockout
#     vs f1 of SB_KnockedOutLoop, f36 of SB_Recover vs f1 of SB_Idle)
#
# Usage:
#   blender -b <checkpoint.blend> --python measure_clip.py -- <config.json> <out.json>
#
# config.json:
#   action, frame_start, frame_end, loop (bool),
#   planted_feet: "all" | "none" | {"BAS_PUNCH_Foot_L": [[a,b],...], ...}
#   ground_contacts: {mesh_name: {"frames": [a,b], "mode": "touch"}}
#   interface_checks: [{"frame": 20, "other_action": "SB_Idle", "other_frame": 1,
#                       "max_translation_m": 0.0001, "max_rotation_deg": 0.05,
#                       "label": "..."}]

import bpy, sys, json, math
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:]
CFG_PATH, OUT = argv[0], argv[1]
CFG = json.load(open(CFG_PATH))

F_START, F_END = CFG["frame_start"], CFG["frame_end"]
N = F_END - F_START + 1
LOOP = bool(CFG.get("loop", False))

TH = {
    "root_translation_max_m": 0.0,
    "root_rotation_max_deg": 0.0,
    "planted_foot_drift_max_m": 0.005,
    "planted_support_gap_max_m": 0.005,
    "ground_penetration_max_m": 0.002,
    "limb_body_min_clearance_m": 0.010,
    "socket_deepening_max_m": 0.001,
}

SOCKET_PAIRS = {
    frozenset(("BAS_PUNCH_Body", "BAS_PUNCH_UpperArm_L")),
    frozenset(("BAS_PUNCH_Body", "BAS_PUNCH_UpperArm_R")),
    frozenset(("BAS_PUNCH_UpperArm_L", "BAS_PUNCH_Forearm_L")),
    frozenset(("BAS_PUNCH_UpperArm_R", "BAS_PUNCH_Forearm_R")),
    frozenset(("BAS_PUNCH_Forearm_L", "BAS_PUNCH_Fist_L")),
    frozenset(("BAS_PUNCH_Forearm_R", "BAS_PUNCH_Fist_R")),
}

sc = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
meshes = [o for o in bpy.data.objects if o.type == "MESH"
          and not o.name.startswith("BAS_KIMI_")]
ROOT_BONE = "BAS_PUNCH_root"
FOOT_MESHES = ["BAS_PUNCH_Foot_L", "BAS_PUNCH_Foot_R"]

act = bpy.data.actions[CFG["action"]]
if arm.animation_data is None:
    arm.animation_data_create()
arm.animation_data.action = act
try:
    arm.animation_data.action_slot = act.slots[0]
except Exception:
    pass

rep = {
    "blender": bpy.app.version_string,
    "master_blend": bpy.data.filepath,
    "config": CFG,
    "frame_range": [F_START, F_END],
    "fps": sc.render.fps / sc.render.fps_base,
    "action": CFG["action"],
    "coordinate_frame": "Blender world, Z-up, metres; armature object at identity",
    "method": "evaluated meshes via depsgraph (armature applied), sample_frame_step = 1"
              + (", cyclic seam analysis" if LOOP else ""),
    "thresholds": TH,
}


def eval_world_verts(dg, obj):
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    mw = ev.matrix_world
    vs = [mw @ v.co for v in me.vertices]
    tris = []
    me.calc_loop_triangles()
    for lt in me.loop_triangles:
        tris.append(tuple(lt.vertices))
    ev.to_mesh_clear()
    return vs, tris


def pair_metrics(geo, a, b):
    (va, ba), (vb, bb) = geo[a], geo[b]
    depth, inside, d_min = 0.0, 0, 1e9
    for src, tgt_bvh in ((va, bb), (vb, ba)):
        for v in src:
            loc, nor, idx, dist = tgt_bvh.find_nearest(v)
            if loc is None:
                continue
            if dist is not None and dist < d_min:
                d_min = dist
            signed = (v - loc).dot(nor)
            if signed < 0:
                inside += 1
                depth = max(depth, -signed)
    return {"overlap_tris": len(ba.overlap(bb)), "min_distance_m": d_min,
            "penetration_depth_m": depth, "vertices_inside": inside}


ALL_PAIRS = []
_names = sorted(o.name for o in meshes)
for _i in range(len(_names)):
    for _j in range(_i + 1, len(_names)):
        ALL_PAIRS.append((_names[_i], _names[_j]))

# ---- rest baseline (action detached) ----
_ad = arm.animation_data
_saved = _ad.action
_ad.action = None
for pb in arm.pose.bones:
    pb.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
_dg = bpy.context.evaluated_depsgraph_get()
_rest_geo = {}
for o in meshes:
    vs, tris = eval_world_verts(_dg, o)
    _rest_geo[o.name] = (vs, BVHTree.FromPolygons([tuple(v) for v in vs], tris,
                                                  all_triangles=True))
rest_socket = {}
for a, b in ALL_PAIRS:
    rest_socket[frozenset((a, b))] = pair_metrics(_rest_geo, a, b)
del _rest_geo
_ad.action = _saved

# ---- per-frame sampling ----
frames = []
vert_track = {o.name: [] for o in meshes}
root_dev, obj_dev = [], []

for f in range(F_START, F_END + 1):
    sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    pbr = arm.pose.bones[ROOT_BONE]
    rest = arm.data.bones[ROOT_BONE].matrix_local
    world_root = arm.matrix_world @ pbr.matrix
    world_rest = arm.matrix_world @ rest
    root_dev.append({"frame": f,
                     "translation_m": (world_root.translation - world_rest.translation).length,
                     "rotation_deg": math.degrees(world_root.to_quaternion().rotation_difference(
                         world_rest.to_quaternion()).angle)})
    od = arm.matrix_world - Matrix.Identity(4)
    obj_dev.append(max(abs(v) for row in od for v in row))

    per_mesh, bvhs = {}, {}
    for o in meshes:
        vs, tris = eval_world_verts(dg, o)
        vert_track[o.name].append(vs)
        per_mesh[o.name] = vs
        bvhs[o.name] = BVHTree.FromPolygons([tuple(v) for v in vs], tris, all_triangles=True)

    lowest_all = min(v.z for vs in per_mesh.values() for v in vs)
    foot_info = {}
    for fm in FOOT_MESHES:
        vs = per_mesh[fm]
        c = sum(vs, Vector((0, 0, 0))) / len(vs)
        foot_info[fm] = {"min_z": min(v.z for v in vs), "centroid": [c.x, c.y, c.z]}
    mesh_minz = {nm: min(v.z for v in vs) for nm, vs in per_mesh.items()}

    geo = {nm: (per_mesh[nm], bvhs[nm]) for nm in per_mesh}
    pairs = []
    for a, b in ALL_PAIRS:
        m = pair_metrics(geo, a, b)
        m["pair"] = [a, b]
        pairs.append(m)
    frames.append({"frame": f, "lowest_z": lowest_all, "feet": foot_info,
                   "mesh_min_z": mesh_minz, "pairs": pairs})

# ---- root verdict ----
rep["root_motion"] = {
    "bone": ROOT_BONE,
    "max_translation_m": max(r["translation_m"] for r in root_dev),
    "max_rotation_deg": max(r["rotation_deg"] for r in root_dev),
    "worst_frame_translation": max(root_dev, key=lambda r: r["translation_m"])["frame"],
    "armature_object_max_abs_deviation_from_identity": max(obj_dev),
    "passed": (max(r["translation_m"] for r in root_dev) <= 1e-9
               and max(r["rotation_deg"] for r in root_dev) <= 1e-7
               and max(obj_dev) <= 1e-9),
}

# ---- planted feet ----
pf_cfg = CFG.get("planted_feet", "all")
foot_report = {}
for fm in FOOT_MESHES:
    cents = [Vector(fr["feet"][fm]["centroid"]) for fr in frames]
    if pf_cfg == "all":
        windows = [(F_START, F_END)]
    elif pf_cfg == "none":
        windows = []
    else:
        windows = [tuple(w) for w in pf_cfg.get(fm, [])]
    worst_drift_xy = 0.0
    worst_vert = 0.0
    worst_pen = 0.0
    worst_gap = 0.0
    for (a, b) in windows:
        idx0 = a - F_START
        c0 = cents[idx0]
        for t in range(a - F_START, b - F_START + 1):
            d = Vector((cents[t].x - c0.x, cents[t].y - c0.y, 0.0)).length
            worst_drift_xy = max(worst_drift_xy, d)
            worst_pen = max(worst_pen, max(0.0, -frames[t]["feet"][fm]["min_z"]))
            worst_gap = max(worst_gap, frames[t]["feet"][fm]["min_z"])
        nv = len(vert_track[fm][0])
        for i in range(nv):
            p0 = vert_track[fm][idx0][i]
            for t in range(a - F_START + 1, b - F_START + 1):
                worst_vert = max(worst_vert, (vert_track[fm][t][i] - p0).length)
    entry = {
        "planted_windows": windows,
        "centroid_drift_xy_m": worst_drift_xy,
        "worst_single_vertex_travel_m": worst_vert,
        "ground_penetration_m": worst_pen,
        "max_sole_gap_m": worst_gap,
    }
    entry["passed"] = all([
        worst_drift_xy <= TH["planted_foot_drift_max_m"],
        worst_vert <= TH["planted_foot_drift_max_m"],
        worst_pen <= TH["ground_penetration_max_m"],
        worst_gap <= TH["planted_support_gap_max_m"],
    ]) if windows else None
    foot_report[fm] = entry
rep["planted_feet"] = foot_report

# ---- ground ----
lowest = min(fr["lowest_z"] for fr in frames)
rep["ground"] = {
    "lowest_z_over_clip_m": lowest,
    "penetration_m": max(0.0, -lowest),
    "worst_frame": min(frames, key=lambda fr: fr["lowest_z"])["frame"],
    "passed": max(0.0, -lowest) <= TH["ground_penetration_max_m"],
}

# ---- intended ground contacts (KO / Recover) ----
gc = {}
for nm, spec in CFG.get("ground_contacts", {}).items():
    a, b = spec["frames"]
    vals = [frames[t - F_START]["mesh_min_z"][nm] for t in range(a, b + 1)]
    pen = max(0.0, -min(vals))
    gap = max(vals)
    gc[nm] = {"frames": [a, b], "min_z_min_m": min(vals), "min_z_max_m": max(vals),
              "penetration_m": pen, "max_gap_m": gap,
              "passed": pen <= TH["ground_penetration_max_m"]
              and gap <= TH["planted_support_gap_max_m"]}
rep["intended_ground_contacts"] = gc

# ---- hands on proxy plane (SB_Push): vertical plane y = const derived from
# evaluated geometry; the fist front surface must touch it (gap <= 0.005)
# and never cross it (y < plane_y - 0.002 => penetration).
plane_rep = {}
for nm, spec in CFG.get("plane_contacts", {}).items():
    py = spec["plane_y"]
    a, b = spec["frames"]
    front_min, front_max, pen = 1e9, -1e9, 0.0
    worst_f = a
    for t in range(a, b + 1):
        vs = vert_track[nm][t - F_START]
        fy = min(v.y for v in vs)
        if fy < front_min:
            front_min, worst_f = fy, t
        front_max = max(front_max, fy)
        pen = max(pen, py - fy)
    plane_rep[nm] = {"plane_y_m": py, "frames": [a, b],
                     "front_y_min_m": front_min, "front_y_max_m": front_max,
                     "worst_frame": worst_f,
                     "penetration_m": pen,
                     "gap_m": front_max - py,
                     "passed": (pen <= TH["ground_penetration_max_m"]
                                and (front_max - py) <= TH["planted_support_gap_max_m"])}
rep["plane_contacts"] = plane_rep

# ---- clearances / sockets ----
clear = []
for a, b in ALL_PAIRS:
    key = frozenset((a, b))
    vals, ov_per_frame, depths = [], [], []
    for fr in frames:
        for p in fr["pairs"]:
            if frozenset(p["pair"]) == key:
                vals.append((p["min_distance_m"], fr["frame"]))
                ov_per_frame.append(p["overlap_tris"])
                depths.append((p["penetration_depth_m"], fr["frame"]))
    worst, wf = min(vals)
    deepest, df = max(depths)
    is_socket = key in SOCKET_PAIRS
    base = rest_socket[key]["penetration_depth_m"]
    entry = {"pair": [a, b], "kind": "socket" if is_socket else "clearance",
             "min_distance_m": worst, "worst_frame": wf,
             "max_overlap_triangle_pairs_per_frame": max(ov_per_frame),
             "deepest_penetration_m": deepest, "deepest_frame": df,
             "rest_baseline_depth_m": round(base, 6),
             "deepening_vs_rest_m": round(deepest - base, 6)}
    if is_socket:
        entry["passed"] = (deepest - base) <= TH["socket_deepening_max_m"]
    else:
        entry["passed"] = (max(ov_per_frame) == 0
                           and worst >= TH["limb_body_min_clearance_m"])
    clear.append(entry)
rep["pair_count"] = len(clear)
rep["clearances"] = clear
rep["clearances_passed"] = all(c["passed"] for c in clear)
rep["clearance_failures"] = [c["pair"] for c in clear if not c["passed"]]

# ---- loop seam ----
if LOOP:
    all_names = [o.name for o in meshes]

    def frame_points(t):
        return [v for nm in all_names for v in vert_track[nm][t]]

    P = [frame_points(t) for t in range(N)]
    nv = len(P[0])
    steps = [max((P[(t + 1) % N][i] - P[t][i]).length for i in range(nv))
             for t in range(N)]
    accels = [max((P[(t + 1) % N][i] - 2 * P[t][i] + P[(t - 1) % N][i]).length
                  for i in range(nv)) for t in range(N)]
    seam_step = steps[N - 1]
    interior_steps = steps[:N - 1]
    interior_accels = [accels[t] for t in range(1, N - 1)]
    dup = max((P[N - 1][i] - P[0][i]).length for i in range(nv))
    rep["loop_seam"] = {
        "policy": "cyclic: wrap is an ordinary 1/30 s step, not a patched join",
        "max_vertex_step_at_seam_m": seam_step,
        "interior_step_mean_m": sum(interior_steps) / len(interior_steps),
        "interior_step_max_m": max(interior_steps),
        "interior_step_min_m": min(interior_steps),
        "seam_step_within_interior_range": min(interior_steps) <= seam_step <= max(interior_steps),
        "max_vertex_accel_at_seam_m": max(accels[N - 1], accels[0]),
        "interior_accel_max_m": max(interior_accels),
        "seam_accel_within_interior_range": max(accels[N - 1], accels[0]) <= max(interior_accels) * 1.05,
        "last_vs_first_frame_max_vertex_distance_m": dup,
        "last_frame_is_not_duplicate_of_first": dup > 1e-4,
        "passed": (min(interior_steps) <= seam_step <= max(interior_steps)
                   and max(accels[N - 1], accels[0]) <= max(interior_accels) * 1.05
                   and dup > 1e-4),
    }

# ---- interface pose checks (per-bone numeric) ----
def pose_at(action_name, frame):
    ad = arm.animation_data
    saved = ad.action
    a = bpy.data.actions[action_name]
    ad.action = a
    try:
        ad.action_slot = a.slots[0]
    except Exception:
        pass
    sc.frame_set(frame)
    bpy.context.view_layer.update()
    pose = {pb.name: pb.matrix.copy() for pb in arm.pose.bones}
    ad.action = saved
    sc.frame_set(F_START)
    return pose


iface = []
for chk in CFG.get("interface_checks", []):
    pa = pose_at(CFG["action"], chk["frame"])
    pb2 = pose_at(chk["other_action"], chk["other_frame"])
    dt = dr = 0.0
    worst = None
    for n in pa:
        d = (pa[n].translation - pb2[n].translation).length
        r = math.degrees(pa[n].to_quaternion().rotation_difference(
            pb2[n].to_quaternion()).angle)
        if d > dt:
            dt, worst = d, n
        dr = max(dr, r)
    iface.append({"label": chk["label"], "frame": chk["frame"],
                  "other": "%s f%d" % (chk["other_action"], chk["other_frame"]),
                  "max_translation_delta_m": dt, "worst_bone": worst,
                  "max_rotation_delta_deg": dr,
                  "limit_translation_m": chk["max_translation_m"],
                  "limit_rotation_deg": chk["max_rotation_deg"],
                  "passed": dt <= chk["max_translation_m"] and dr <= chk["max_rotation_deg"]})
rep["interface_checks"] = iface

# ---- amplitude / bounds ----
lo = Vector((1e9,) * 3)
hi = Vector((-1e9,) * 3)
for t in range(N):
    for nm in vert_track:
        for v in vert_track[nm][t]:
            for i in range(3):
                lo[i] = min(lo[i], v[i])
                hi[i] = max(hi[i], v[i])
rep["bounds_over_clip_m"] = {"min": list(lo), "max": list(hi),
                             "size": [hi[i] - lo[i] for i in range(3)]}

feet_ok = all((v["passed"] in (True, None)) for v in foot_report.values())
plane_ok = all(v["passed"] for v in plane_rep.values())
gc_ok = all(v["passed"] for v in gc.values())
iface_ok = all(v["passed"] for v in iface)
rep["passed"] = (rep["root_motion"]["passed"] and feet_ok and plane_ok
                 and rep["ground"]["passed"] and gc_ok
                 and rep["clearances_passed"] and iface_ok
                 and (rep["loop_seam"]["passed"] if LOOP else True))


def rnd(o, n=6):
    if isinstance(o, float):
        return round(o, n)
    if isinstance(o, dict):
        return {k: rnd(v, n) for k, v in o.items()}
    if isinstance(o, list):
        return [rnd(v, n) for v in o]
    return o


with open(OUT, "w") as fh:
    json.dump(rnd(rep), fh, indent=2)
print("MEASURE_WRITTEN " + OUT + " passed=" + str(rep["passed"]))
