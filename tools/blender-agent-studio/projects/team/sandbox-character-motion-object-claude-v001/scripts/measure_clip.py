"""Physical validation of one clip. Batch, isolated, read-only on a checkpoint.

Everything is measured on EVALUATED geometry (post-armature, post-modifier) in
one declared frame of reference, on every frame (sample_frame_step = 1). Bone
heads and tails are never used as a contact proof.

Declared frame of reference
---------------------------
`world_blender`: the armature object's world space, which is the identity, so
armature space and world space coincide. Z is up, the character faces -Y.

Reconstructed world for locomotion
----------------------------------
An in-place clip cannot be judged in its own local frame: a planted foot is
SUPPOSED to travel backward there. The reconstruction adds the virtual travel
the engine will apply, at the clip's declared nominal speed:

    world_reconstructed(p, f) = p + (0, -1, 0) * v_nom * (f - f_start) / fps

A foot that is genuinely planted is then STATIC in that frame, and its residual
motion is the drift being thresholded.

Thresholds (locked before authoring, from SCENE_TRIAL_EVALUATION_RULES.md)
-------------------------------------------------------------------------
    ground penetration      <= 0.002 m
    planted contact gap     <= 0.005 m
    planted drift           <= 0.005 m
    swing clearance         >= 0.010 m

Self-intersection uses the rest pose as its baseline. The shoulder sockets of
this rig intersect in the BIND POSE itself (the arm roots are inside the body
sphere), so a socket pair is judged by NON-AGGRAVATION against that baseline,
never by an absolute zero it could never reach. Non-adjacent pairs are judged as
clearance and must not intersect at all.

Usage:
  blender -b --factory-startup <checkpoint.blend> --python measure_clip.py -- \
      <action> <contract.json> <out.json>
"""
import bpy
import bmesh
import json
import math
import sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:]
ACTION, CONTRACT_PATH, OUT_PATH = argv[0], argv[1], argv[2]

with open(CONTRACT_PATH) as handle:
    CONTRACT = json.load(handle)

GROUND_PENETRATION_MAX = 0.002
PLANTED_GAP_MAX = 0.005
PLANTED_DRIFT_MAX = 0.005
SWING_CLEARANCE_MIN = 0.010

FOOT_L, FOOT_R = "BAS_PUNCH_Foot_L", "BAS_PUNCH_Foot_R"
ROOT_BONE = "BAS_PUNCH_root"

# Adjacent pairs in the kinematic chain: these share a socket and already
# intersect in the BIND POSE. Everything else must stay clear.
#
# Body <-> Foot is deliberately NOT here. The feet are children of root, not of
# body, so they are not adjacent in the chain, and their measured rest overlap is
# exactly 0. Classifying them as sockets would have granted a rotating-joint
# tolerance to a pair that must simply never touch.
SOCKET_PAIRS = {
    frozenset(("BAS_PUNCH_Body", "BAS_PUNCH_UpperArm_L")),
    frozenset(("BAS_PUNCH_Body", "BAS_PUNCH_UpperArm_R")),
    frozenset(("BAS_PUNCH_UpperArm_L", "BAS_PUNCH_Forearm_L")),
    frozenset(("BAS_PUNCH_UpperArm_R", "BAS_PUNCH_Forearm_R")),
    frozenset(("BAS_PUNCH_Forearm_L", "BAS_PUNCH_Fist_L")),
    frozenset(("BAS_PUNCH_Forearm_R", "BAS_PUNCH_Fist_R")),
}

# A socket that rotates ALWAYS gains overlapping triangle pairs; the count has no
# physical unit and cannot be thresholded. SCENE_TRIAL_EVALUATION_RULES.md asks
# for nearest-surface distance AND BVH overlap, so depth below is the verdict
# metric and the triangle count is kept as diagnostic only.
#
# Tolerance declared here, before re-measuring: a socket may deepen by at most
# 20 mm beyond its bind-pose depth. The shortest segment in the chain is the
# 0.191 m forearm, so 20 mm is about a tenth of it — far short of a piece
# visibly sinking into its neighbour, and far short of one end emerging through
# the other side.
SOCKET_DEPTH_TOLERANCE = 0.020

scene = bpy.context.scene
rig = bpy.data.objects["BAS_PUNCH_Rig"]
action = bpy.data.actions[ACTION]
if rig.animation_data is None:
    rig.animation_data_create()
rig.animation_data.action = action
for slot in getattr(action, "slots", []):
    try:
        rig.animation_data.action_slot = slot
        break
    except Exception:
        pass

F_START = CONTRACT["f_start"]
F_END = CONTRACT["f_end"]
FPS = 30.0
V_NOM = CONTRACT.get("nominal_speed_mps", 0.0)
MESHES = [o.name for o in bpy.data.objects if o.type == "MESH"]

depsgraph = bpy.context.evaluated_depsgraph_get()


def evaluated_world_verts(name):
    """World-space vertices of the evaluated mesh, i.e. what is really rendered."""
    obj = bpy.data.objects[name]
    ev = obj.evaluated_get(depsgraph)
    mesh = ev.to_mesh()
    matrix = ev.matrix_world
    verts = [matrix @ v.co for v in mesh.vertices]
    tris = []
    mesh.calc_loop_triangles()
    for tri in mesh.loop_triangles:
        tris.append(tuple(tri.vertices))
    ev.to_mesh_clear()
    return verts, tris


def bvh_of(verts, tris):
    return BVHTree.FromPolygons([tuple(v) for v in verts], tris, all_triangles=True)


def overlap_count(a, b):
    try:
        return len(a.overlap(b))
    except Exception:
        return -1


def penetration_depth(verts_a, bvh_b):
    """Deepest point of A inside B, via nearest surface point and its normal.

    Returns 0.0 when no vertex of A is inside B. The sign test uses the surface
    normal at the nearest point, which is reliable for the closed convex-ish
    blobs this character is built from.
    """
    worst = 0.0
    for vert in verts_a:
        hit = bvh_b.find_nearest(vert)
        if hit[0] is None:
            continue
        location, normal, _, distance = hit
        if (vert - location).dot(normal) < 0.0:
            if distance > worst:
                worst = distance
    return worst


def pair_depth(name_a, name_b, geo, bvh):
    """Symmetric deepest interpenetration between two meshes, in metres."""
    return max(penetration_depth(geo[name_a][0], bvh[name_b]),
               penetration_depth(geo[name_b][0], bvh[name_a]))


def reconstruct(p, frame):
    """Add the virtual engine travel so a planted foot becomes world-static."""
    t = (frame - F_START) / FPS
    return Vector((p.x, p.y - V_NOM * t, p.z))


# ---------------------------------------------------------------- rest baseline
scene.frame_set(F_START)
rig_rest_action = rig.animation_data.action
rig.animation_data.action = None
for pb in rig.pose.bones:
    pb.matrix_basis.identity()
bpy.context.view_layer.update()
depsgraph.update()

rest_geo = {name: evaluated_world_verts(name) for name in MESHES}
rest_bvh = {name: bvh_of(*rest_geo[name]) for name in MESHES}
rest_overlap, rest_depth = {}, {}
for i, a in enumerate(MESHES):
    for b in MESHES[i + 1:]:
        count = overlap_count(rest_bvh[a], rest_bvh[b])
        rest_overlap[f"{a}|{b}"] = count
        rest_depth[f"{a}|{b}"] = (
            pair_depth(a, b, rest_geo, rest_bvh) if count > 0 else 0.0
        )

rest_root = rig.pose.bones[ROOT_BONE].matrix.copy()
rest_min_z = min(v.z for name in MESHES for v in rest_geo[name][0])

rig.animation_data.action = rig_rest_action
for slot in getattr(action, "slots", []):
    try:
        rig.animation_data.action_slot = slot
        break
    except Exception:
        pass

# --------------------------------------------------------------- per-frame pass
frames = []
for frame in range(F_START, F_END + 1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    depsgraph.update()

    geo = {name: evaluated_world_verts(name) for name in MESHES}
    bvh = {name: bvh_of(*geo[name]) for name in MESHES}

    min_z = {name: min(v.z for v in geo[name][0]) for name in MESHES}
    global_min_z = min(min_z.values())

    # Sole contact patch: the vertices within 1 cm of the foot's own lowest point.
    soles = {}
    for foot in (FOOT_L, FOOT_R):
        verts = geo[foot][0]
        low = min_z[foot]
        patch = [v for v in verts if v.z <= low + 0.01]
        centroid = sum(patch, Vector((0, 0, 0))) / len(patch)
        soles[foot] = {
            "min_z": low,
            "patch_size": len(patch),
            "centroid_local": [centroid.x, centroid.y, centroid.z],
            "centroid_world": list(reconstruct(centroid, frame)),
        }

    overlaps, depths = {}, {}
    for i, a in enumerate(MESHES):
        for b in MESHES[i + 1:]:
            key = f"{a}|{b}"
            count = overlap_count(bvh[a], bvh[b])
            overlaps[key] = count
            # Depth is only meaningful where the meshes actually intersect, and
            # it is the expensive half of the measurement, so it is skipped when
            # the BVH already proved there is no contact at all.
            depths[key] = pair_depth(a, b, geo, bvh) if count > 0 else 0.0

    root = rig.pose.bones[ROOT_BONE].matrix
    root_delta_t = (root.translation - rest_root.translation).length
    root_delta_r = math.degrees(
        root.to_quaternion().rotation_difference(rest_root.to_quaternion()).angle
    )

    body_centroid = sum(geo["BAS_PUNCH_Body"][0], Vector((0, 0, 0))) / len(
        geo["BAS_PUNCH_Body"][0]
    )

    frames.append({
        "frame": frame,
        "global_min_z": global_min_z,
        "penetration": max(0.0, -global_min_z),
        "min_z": min_z,
        "soles": soles,
        "overlaps": overlaps,
        "depths": depths,
        "root_delta_translation_m": root_delta_t,
        "root_delta_rotation_deg": root_delta_r,
        "body_centroid": list(body_centroid),
    })

# ------------------------------------------------------------------- reductions
report = {
    "action": ACTION,
    "frame_reference": "world_blender (armature matrix = identity)",
    "reconstruction": {
        "applied": V_NOM > 0.0,
        "formula": "p + (0,-1,0) * v_nom * (f - f_start) / 30",
        "nominal_speed_mps": V_NOM,
    },
    "sample_frame_step": 1,
    "frames_evaluated": len(frames),
    "thresholds": {
        "ground_penetration_max_m": GROUND_PENETRATION_MAX,
        "planted_gap_max_m": PLANTED_GAP_MAX,
        "planted_drift_max_m": PLANTED_DRIFT_MAX,
        "swing_clearance_min_m": SWING_CLEARANCE_MIN,
    },
    "rest_baseline": {
        "min_z": rest_min_z,
        "overlaps": rest_overlap,
        "depths_m": rest_depth,
    },
    "socket_depth_tolerance_m": SOCKET_DEPTH_TOLERANCE,
}

worst_pen = max(frames, key=lambda x: x["penetration"])
report["ground"] = {
    "worst_penetration_m": worst_pen["penetration"],
    "worst_frame": worst_pen["frame"],
    "frames_over_threshold": sum(
        1 for x in frames if x["penetration"] > GROUND_PENETRATION_MAX
    ),
    "pass": worst_pen["penetration"] <= GROUND_PENETRATION_MAX,
}

worst_root = max(frames, key=lambda x: x["root_delta_translation_m"])
worst_root_r = max(frames, key=lambda x: x["root_delta_rotation_deg"])
report["root_motion"] = {
    "worst_translation_m": worst_root["root_delta_translation_m"],
    "worst_translation_frame": worst_root["frame"],
    "worst_rotation_deg": worst_root_r["root_delta_rotation_deg"],
    "worst_rotation_frame": worst_root_r["frame"],
    "pass": (worst_root["root_delta_translation_m"] <= 1e-6
             and worst_root_r["root_delta_rotation_deg"] <= 1e-4),
}

# Contacts, driven by the declared stance windows rather than guessed from z.
contacts = {}
for foot_key, windows in CONTRACT.get("stance_windows", {}).items():
    mesh_name = FOOT_L if foot_key == "L" else FOOT_R
    entries = []
    for window in windows:
        span = [f for f in range(F_START, F_END + 1)
                if window["start"] <= f <= window["end"]]
        if not span:
            continue
        sample = [next(x for x in frames if x["frame"] == f) for f in span]
        gaps = [s["soles"][mesh_name]["min_z"] for s in sample]
        pts = [Vector(s["soles"][mesh_name]["centroid_world"]) for s in sample]
        centre = sum(pts, Vector((0, 0, 0))) / len(pts)
        drift = max((p - centre).length for p in pts)
        entries.append({
            "window": [window["start"], window["end"]],
            "frames": len(span),
            "max_abs_gap_m": max(abs(g) for g in gaps),
            "max_drift_m": drift,
            "gap_pass": max(abs(g) for g in gaps) <= PLANTED_GAP_MAX,
            "drift_pass": drift <= PLANTED_DRIFT_MAX,
        })
    contacts[foot_key] = entries
report["planted_contacts"] = contacts
report["planted_pass"] = all(
    e["gap_pass"] and e["drift_pass"]
    for entries in contacts.values() for e in entries
) if contacts else None

# Swing clearance over the declared swing windows.
swings = {}
for foot_key, windows in CONTRACT.get("swing_windows", {}).items():
    mesh_name = FOOT_L if foot_key == "L" else FOOT_R
    entries = []
    for window in windows:
        span = [f for f in range(F_START, F_END + 1)
                if window["start"] <= f <= window["end"]]
        if not span:
            continue
        sample = [next(x for x in frames if x["frame"] == f) for f in span]
        peak = max(s["soles"][mesh_name]["min_z"] for s in sample)
        entries.append({
            "window": [window["start"], window["end"]],
            "peak_clearance_m": peak,
            "pass": peak >= SWING_CLEARANCE_MIN,
        })
    swings[foot_key] = entries
report["swing_clearance"] = swings
report["swing_pass"] = all(
    e["pass"] for entries in swings.values() for e in entries
) if swings else None

# Self-intersection, split by semantics.
socket_report, clearance_report = {}, {}
for key in rest_overlap:
    a, b = key.split("|")
    worst_tri = max(frames, key=lambda x: x["overlaps"][key])
    worst_depth = max(frames, key=lambda x: x["depths"][key])
    entry = {
        "rest_triangles": rest_overlap[key],
        "worst_triangles": worst_tri["overlaps"][key],
        "worst_triangles_frame": worst_tri["frame"],
        "rest_depth_m": rest_depth[key],
        "worst_depth_m": worst_depth["depths"][key],
        "worst_depth_frame": worst_depth["frame"],
        "depth_gain_m": worst_depth["depths"][key] - rest_depth[key],
    }
    if frozenset((a, b)) in SOCKET_PAIRS:
        # A rotating socket necessarily gains triangle pairs, so the verdict is
        # on how much DEEPER it sinks than the bind pose already is.
        entry["tolerance_m"] = SOCKET_DEPTH_TOLERANCE
        entry["pass"] = entry["depth_gain_m"] <= SOCKET_DEPTH_TOLERANCE
        socket_report[key] = entry
    else:
        entry["pass"] = worst_tri["overlaps"][key] == 0
        clearance_report[key] = entry
report["socket_pairs"] = socket_report
report["clearance_pairs"] = clearance_report
report["intersection_pass"] = (
    all(e["pass"] for e in socket_report.values())
    and all(e["pass"] for e in clearance_report.values())
)

# Loop seam, treated as an ordinary step so a duplicated last pose is visible.
if CONTRACT.get("loop"):
    def body_at(frame):
        return Vector(next(x for x in frames if x["frame"] == frame)["body_centroid"])

    steps = [
        (body_at(f + 1) - body_at(f)).length
        for f in range(F_START, F_END)
    ]
    seam = (body_at(F_START) - body_at(F_END)).length
    report["loop_seam"] = {
        "seam_step_m": seam,
        "interior_step_min_m": min(steps),
        "interior_step_max_m": max(steps),
        "last_frame_is_duplicate_of_first": seam < 1e-6,
        "seam_inside_interior_range": min(steps) <= seam <= max(steps),
        "pass": seam >= 1e-6 and min(steps) * 0.5 <= seam <= max(steps) * 1.5,
    }
else:
    report["loop_seam"] = None

report["frames"] = frames

with open(OUT_PATH, "w") as handle:
    json.dump(report, handle, indent=1)

gates = [report["ground"]["pass"], report["root_motion"]["pass"],
         report["intersection_pass"]]
for optional in (report["planted_pass"], report["swing_pass"],
                 (report["loop_seam"] or {}).get("pass")):
    if optional is not None:
        gates.append(optional)
print("MEASURE_DONE " + OUT_PATH)
print("PHYSICAL_PASS " + str(all(gates)))
