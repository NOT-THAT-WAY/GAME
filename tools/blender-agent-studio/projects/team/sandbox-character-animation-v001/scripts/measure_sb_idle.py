# Physical validation of SB_Idle on EVALUATED geometry, every frame.
#
# Measures, in the declared world frame (Blender Z-up, metres):
#   - root bone + armature object immobility (root motion)
#   - planted-foot drift and ground penetration
#   - part-vs-part penetration (BVH triangle overlap) and clearance (nearest point)
#   - loop seam treated CYCLICALLY: frame 60 -> frame 1 is an ordinary step.
#     Position, velocity and acceleration at the seam are compared against the
#     distribution over the rest of the cycle, and frame 60 is checked to be
#     distinct from frame 1 (no duplicated end pose).
#
# Usage: blender -b <master.blend> --python measure_sb_idle.py -- <out.json>

import bpy, sys, json, math
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

OUT = sys.argv[sys.argv.index("--") + 1:][0]

F_START, F_END = 1, 60
N = F_END - F_START + 1

TH = {
    "root_translation_max_m": 0.0,
    "root_rotation_max_deg": 0.0,
    "planted_foot_drift_max_m": 0.005,
    "ground_penetration_max_m": 0.002,
    "limb_body_min_clearance_m": 0.010,
    "socket_deepening_max_m": 0.001,
}

# Declared semantic pairs, applied to ALL 36 mesh pairs.
#
# The character is built from detached rigid volumes that interpenetrate at each
# joint: body/upperarm is the shoulder, upperarm/forearm the elbow, forearm/fist
# the wrist. Those intersections exist in the untouched SOURCE bind pose (e.g.
# 102 body vertices inside the upper arm at 0.1489 m) - they are the joints, not
# collisions. Proven in evidence/shoulder-socket-baseline.json.
#
# For an ADJACENT (socket) pair the test is therefore "the animation must not
# deepen the joint beyond its source rest baseline".
# For every NON-ADJACENT pair the test is real clearance: zero triangle overlap
# and a minimum separation. This is what catches a fist entering a foot or the
# body - including cases that merely LOOK like contact in a projected view.
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
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
BODY_MESH = "BAS_PUNCH_Body"
FOOT_MESHES = ["BAS_PUNCH_Foot_L", "BAS_PUNCH_Foot_R"]
ROOT_BONE = "BAS_PUNCH_root"

rep = {
    "blender": bpy.app.version_string,
    "master_blend": bpy.data.filepath,
    "frame_range": [F_START, F_END],
    "fps": sc.render.fps / sc.render.fps_base,
    "action": arm.animation_data.action.name if arm.animation_data and arm.animation_data.action else None,
    "coordinate_frame": "Blender world, Z-up, metres; armature object at identity",
    "method": "evaluated meshes via depsgraph (armature + modifiers applied), sample_frame_step = 1, cyclic seam analysis",
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


# ------------------------------------------------- rest baseline for sockets
# Detach the action so the true bind pose is measured, then restore it.
_ad = arm.animation_data
_saved_action = _ad.action if _ad else None
_saved_slot = getattr(_ad, "action_slot", None) if _ad else None
if _ad:
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


def pair_metrics(geo, a, b):
    """Symmetric depth/clearance between two evaluated meshes."""
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

rest_socket = {}
for a, b in ALL_PAIRS:
    rest_socket[frozenset((a, b))] = pair_metrics(_rest_geo, a, b)
del _rest_geo

if _ad:
    _ad.action = _saved_action
    if _saved_slot is not None:
        try:
            _ad.action_slot = _saved_slot
        except Exception:
            pass
rep["rest_baseline_pairs"] = {
    " | ".join(sorted(k)): {kk: round(vv, 6) if isinstance(vv, float) else vv
                            for kk, vv in v.items()}
    for k, v in rest_socket.items()}

# ---------------------------------------------------------- per-frame sampling
frames = []
vert_track = {o.name: [] for o in meshes}   # per mesh: list over frames of list of Vector
root_dev = []
obj_dev = []

for f in range(F_START, F_END + 1):
    sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()

    # --- root immobility (bone + object) ---
    pbr = arm.pose.bones[ROOT_BONE]
    rest = arm.data.bones[ROOT_BONE].matrix_local
    world_root = arm.matrix_world @ pbr.matrix
    world_rest = arm.matrix_world @ rest
    dt = (world_root.translation - world_rest.translation).length
    dq = world_root.to_quaternion().rotation_difference(world_rest.to_quaternion())
    droll = math.degrees(dq.angle)
    root_dev.append({"frame": f, "translation_m": dt, "rotation_deg": droll})
    od = (arm.matrix_world - Matrix.Identity(4))
    obj_dev.append({"frame": f, "max_abs": max(abs(v) for row in od for v in row)})

    # --- evaluated geometry ---
    per_mesh = {}
    bvhs = {}
    for o in meshes:
        vs, tris = eval_world_verts(dg, o)
        vert_track[o.name].append(vs)
        per_mesh[o.name] = vs
        bvhs[o.name] = BVHTree.FromPolygons([tuple(v) for v in vs], tris, all_triangles=True)

    # --- ground contact / penetration ---
    lowest_all = min(v.z for vs in per_mesh.values() for v in vs)
    foot_info = {}
    for fm in FOOT_MESHES:
        vs = per_mesh[fm]
        c = sum(vs, Vector((0, 0, 0))) / len(vs)
        foot_info[fm] = {
            "min_z": min(v.z for v in vs),
            "centroid": [c.x, c.y, c.z],
        }

    # --- ALL mesh pairs: overlap (penetration) and nearest distance (clearance) ---
    geo = {nm: (per_mesh[nm], bvhs[nm]) for nm in per_mesh}
    pairs = []
    for a, b in ALL_PAIRS:
        m = pair_metrics(geo, a, b)
        m["pair"] = [a, b]
        pairs.append(m)

    frames.append({"frame": f, "lowest_z": lowest_all, "feet": foot_info, "pairs": pairs})

# ---------------------------------------------------------- root motion verdict
rep["root_motion"] = {
    "bone": ROOT_BONE,
    "max_translation_m": max(r["translation_m"] for r in root_dev),
    "max_rotation_deg": max(r["rotation_deg"] for r in root_dev),
    "worst_frame_translation": max(root_dev, key=lambda r: r["translation_m"])["frame"],
    "armature_object_max_abs_deviation_from_identity": max(o["max_abs"] for o in obj_dev),
    "passed": (max(r["translation_m"] for r in root_dev) <= 1e-9
               and max(r["rotation_deg"] for r in root_dev) <= 1e-7
               and max(o["max_abs"] for o in obj_dev) <= 1e-9),
}

# ---------------------------------------------------------- foot drift verdict
foot_report = {}
for fm in FOOT_MESHES:
    cents = [Vector(fr["feet"][fm]["centroid"]) for fr in frames]
    c0 = cents[0]
    drift_xy = max((Vector((c.x - c0.x, c.y - c0.y, 0.0))).length for c in cents)
    drift_3d = max((c - c0).length for c in cents)
    minz = min(fr["feet"][fm]["min_z"] for fr in frames)
    maxz = max(fr["feet"][fm]["min_z"] for fr in frames)
    # per-frame sole movement (worst single-vertex travel across the whole cycle)
    vtracks = vert_track[fm]
    nv = len(vtracks[0])
    worst_vert = 0.0
    for i in range(nv):
        p0 = vtracks[0][i]
        for t in range(1, N):
            d = (vtracks[t][i] - p0).length
            if d > worst_vert:
                worst_vert = d
    foot_report[fm] = {
        "centroid_drift_xy_m": drift_xy,
        "centroid_drift_3d_m": drift_3d,
        "worst_single_vertex_travel_m": worst_vert,
        "sole_min_z_m": minz,
        "sole_min_z_max_over_cycle_m": maxz,
        "ground_penetration_m": max(0.0, -minz),
        "passed": (drift_xy <= TH["planted_foot_drift_max_m"]
                   and worst_vert <= TH["planted_foot_drift_max_m"]
                   and max(0.0, -minz) <= TH["ground_penetration_max_m"]),
    }
rep["planted_feet"] = foot_report
rep["ground"] = {
    "lowest_z_over_cycle_m": min(fr["lowest_z"] for fr in frames),
    "penetration_m": max(0.0, -min(fr["lowest_z"] for fr in frames)),
    "passed": max(0.0, -min(fr["lowest_z"] for fr in frames)) <= TH["ground_penetration_max_m"],
}

# ---------------------------------------------------------- clearance verdict
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
    entry = {
        "pair": [a, b],
        "kind": "socket" if is_socket else "clearance",
        "min_distance_m": worst,
        "worst_frame": wf,
        "max_overlap_triangle_pairs_per_frame": max(ov_per_frame),
        "deepest_penetration_m": deepest,
        "deepest_frame": df,
        "rest_baseline_depth_m": round(base, 6),
        "rest_baseline_overlap_tris": rest_socket[key]["overlap_tris"],
        "deepening_vs_rest_m": round(deepest - base, 6),
    }
    if is_socket:
        entry["criterion"] = ("declared joint socket (adjacent chain segments): the "
                              "animation must not deepen it by more than %.3f m vs the "
                              "source bind pose" % TH["socket_deepening_max_m"])
        entry["passed"] = (deepest - base) <= TH["socket_deepening_max_m"]
    else:
        entry["criterion"] = ("declared clearance pair (non-adjacent): zero triangle "
                              "overlap and at least %.3f m of separation"
                              % TH["limb_body_min_clearance_m"])
        entry["passed"] = (max(ov_per_frame) == 0
                           and worst >= TH["limb_body_min_clearance_m"])
    clear.append(entry)
rep["pair_count"] = len(clear)
rep["clearances"] = clear
rep["clearances_passed"] = all(c["passed"] for c in clear)
rep["clearance_failures"] = [c["pair"] for c in clear if not c["passed"]]

# ---------------------------------------------------------- cyclic seam analysis
# Treat the cycle as [1..60] -> 1. Step s(t) = P(t+1) - P(t), with s(N-1) the wrap.
all_names = [o.name for o in meshes]


def frame_points(t):
    return [v for nm in all_names for v in vert_track[nm][t]]


P = [frame_points(t) for t in range(N)]
nv = len(P[0])

steps = []      # steps[t] = max per-vertex displacement from t to t+1 (cyclic)
for t in range(N):
    t2 = (t + 1) % N
    steps.append(max((P[t2][i] - P[t][i]).length for i in range(nv)))

accels = []     # accels[t] = max per-vertex |P(t+1) - 2P(t) + P(t-1)| (cyclic)
for t in range(N):
    tp, tn = (t - 1) % N, (t + 1) % N
    accels.append(max((P[tn][i] - 2 * P[t][i] + P[tp][i]).length for i in range(nv)))

seam_step = steps[N - 1]            # frame 60 -> frame 1
seam_accel_at_60 = accels[N - 1]
seam_accel_at_1 = accels[0]
interior_steps = steps[:N - 1]
interior_accels = [accels[t] for t in range(1, N - 1)]

dup = max((P[N - 1][i] - P[0][i]).length for i in range(nv))  # frame60 vs frame1

rep["loop_seam"] = {
    "policy": "cyclic: the 60->1 wrap is an ordinary 1/30 s step, not a patched join",
    "max_vertex_step_at_seam_m": seam_step,
    "interior_step_mean_m": sum(interior_steps) / len(interior_steps),
    "interior_step_max_m": max(interior_steps),
    "interior_step_min_m": min(interior_steps),
    "seam_step_within_interior_range": min(interior_steps) <= seam_step <= max(interior_steps),
    "seam_step_ratio_to_mean": seam_step / (sum(interior_steps) / len(interior_steps)),
    "max_vertex_accel_at_seam_m": max(seam_accel_at_60, seam_accel_at_1),
    "interior_accel_max_m": max(interior_accels),
    "interior_accel_mean_m": sum(interior_accels) / len(interior_accels),
    "seam_accel_within_interior_range": max(seam_accel_at_60, seam_accel_at_1) <= max(interior_accels) * 1.05,
    "frame60_vs_frame1_max_vertex_distance_m": dup,
    "frame60_is_not_duplicate_of_frame1": dup > 1e-4,
    "passed": (min(interior_steps) <= seam_step <= max(interior_steps)
               and max(seam_accel_at_60, seam_accel_at_1) <= max(interior_accels) * 1.05
               and dup > 1e-4),
}

# ---------------------------------------------------------- motion amplitude
body_track = vert_track[BODY_MESH]
cents = []
for t in range(N):
    vs = body_track[t]
    cents.append(sum(vs, Vector((0, 0, 0))) / len(vs))
rep["body_motion"] = {
    "centroid_travel_x_m": max(c.x for c in cents) - min(c.x for c in cents),
    "centroid_travel_y_m": max(c.y for c in cents) - min(c.y for c in cents),
    "centroid_travel_z_m": max(c.z for c in cents) - min(c.z for c in cents),
}
lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
for t in range(N):
    for nm in all_names:
        for v in vert_track[nm][t]:
            for i in range(3):
                lo[i] = min(lo[i], v[i]); hi[i] = max(hi[i], v[i])
rep["bounds_over_cycle_m"] = {"min": list(lo), "max": list(hi),
                              "size": [hi[i] - lo[i] for i in range(3)]}

rep["passed"] = (rep["root_motion"]["passed"]
                 and all(v["passed"] for v in foot_report.values())
                 and rep["ground"]["passed"]
                 and rep["clearances_passed"]
                 and rep["loop_seam"]["passed"])


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
