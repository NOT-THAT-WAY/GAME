# Is the Body/UpperArm intersection a defect introduced by SB_Idle, or is the
# upper arm socketed into the body sphere by the source character's own design?
#
# Establishes the REST (bind) pose baseline from the immutable source FBX, then
# compares it against every animated frame of the master .blend. The animation is
# only acceptable if it does not deepen the socket beyond its rest envelope.
#
# Penetration depth = for each upper-arm vertex, the signed distance below the
# body surface (negative side of the body's nearest-surface normal).
#
# Usage:
#   blender -b --factory-startup --python measure_shoulder_socket.py -- <src.fbx> <master.blend> <out.json>

import bpy, sys, json
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:]
SRC_FBX, MASTER, OUT = argv[0], argv[1], argv[2]

BODY = "BAS_PUNCH_Body"
LIMBS = ["BAS_PUNCH_UpperArm_L", "BAS_PUNCH_UpperArm_R",
         "BAS_PUNCH_Forearm_L", "BAS_PUNCH_Forearm_R",
         "BAS_PUNCH_Fist_L", "BAS_PUNCH_Fist_R",
         "BAS_PUNCH_Foot_L", "BAS_PUNCH_Foot_R"]


def eval_obj(dg, obj):
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    mw = ev.matrix_world
    vs = [mw @ v.co for v in me.vertices]
    me.calc_loop_triangles()
    tris = [tuple(lt.vertices) for lt in me.loop_triangles]
    ev.to_mesh_clear()
    return vs, tris


def socket_metrics():
    """Depth of each limb inside the body, in the current scene state."""
    dg = bpy.context.evaluated_depsgraph_get()
    objs = {o.name: o for o in bpy.data.objects if o.type == "MESH"}
    bvs, btris = eval_obj(dg, objs[BODY])
    body_bvh = BVHTree.FromPolygons([tuple(v) for v in bvs], btris, all_triangles=True)
    out = {}
    for lm in LIMBS:
        if lm not in objs:
            continue
        vs, tris = eval_obj(dg, objs[lm])
        limb_bvh = BVHTree.FromPolygons([tuple(v) for v in vs], tris, all_triangles=True)
        deepest = 0.0
        inside = 0
        for v in vs:
            loc, nor, idx, dist = body_bvh.find_nearest(v)
            if loc is None:
                continue
            signed = (v - loc).dot(nor)   # <0 => inside the body surface
            if signed < 0:
                inside += 1
                deepest = max(deepest, -signed)
        out[lm] = {
            "vertices_inside_body": inside,
            "vertex_count": len(vs),
            "deepest_penetration_m": round(deepest, 6),
            "overlap_triangle_pairs": len(body_bvh.overlap(limb_bvh)),
        }
    return out


# ---------------------------------------------------- 1. REST baseline from FBX
bpy.ops.wm.read_factory_settings(use_empty=True)
for coll in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights,
             bpy.data.materials, bpy.data.armatures, bpy.data.actions):
    for db in list(coll):
        coll.remove(db)
bpy.ops.import_scene.fbx(filepath=SRC_FBX)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
if arm.animation_data:
    arm.animation_data.action = None
for pb in arm.pose.bones:
    pb.matrix_basis = Matrix.Identity(4)
arm.location = (0, 0, 0); arm.rotation_euler = (0, 0, 0); arm.scale = (1, 1, 1)
bpy.context.view_layer.update()

rest = socket_metrics()

# ---------------------------------------------------- 2. animated master .blend
bpy.ops.wm.open_mainfile(filepath=MASTER)
sc = bpy.context.scene
per_frame = {}
for f in range(sc.frame_start, sc.frame_end + 1):
    sc.frame_set(f)
    per_frame[f] = socket_metrics()

# ---------------------------------------------------- 3. compare
summary = {}
for lm in rest:
    r = rest[lm]
    depths = [(per_frame[f][lm]["deepest_penetration_m"], f) for f in per_frame]
    counts = [per_frame[f][lm]["vertices_inside_body"] for f in per_frame]
    worst, wf = max(depths)
    summary[lm] = {
        "rest_deepest_m": r["deepest_penetration_m"],
        "rest_vertices_inside": r["vertices_inside_body"],
        "rest_overlap_tris": r["overlap_triangle_pairs"],
        "animated_deepest_m": round(worst, 6),
        "animated_worst_frame": wf,
        "animated_max_vertices_inside": max(counts),
        "delta_vs_rest_m": round(worst - r["deepest_penetration_m"], 6),
        "socketed_at_rest": r["vertices_inside_body"] > 0,
    }

rep = {
    "question": "Is Body/UpperArm intersection a source-design socket or an SB_Idle defect?",
    "method": "signed distance of limb vertices against the body's nearest-surface normal, evaluated geometry; rest baseline taken from the untouched source FBX with the Punch action detached",
    "source_fbx": SRC_FBX,
    "master_blend": MASTER,
    "rest_baseline": rest,
    "comparison": summary,
    "verdict": {
        "socketed_by_design": [k for k, v in summary.items() if v["socketed_at_rest"]],
        "clear_by_design": [k for k, v in summary.items() if not v["socketed_at_rest"]],
        "deepened_by_animation_m": {k: v["delta_vs_rest_m"] for k, v in summary.items()},
        "max_deepening_m": max(v["delta_vs_rest_m"] for v in summary.values()),
    },
}

with open(OUT, "w") as fh:
    json.dump(rep, fh, indent=2)
print("SOCKET_WRITTEN " + OUT)
