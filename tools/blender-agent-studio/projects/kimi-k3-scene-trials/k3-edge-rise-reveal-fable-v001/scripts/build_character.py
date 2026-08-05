"""Append the imposed mecha mascot asset, scale it, and complete its rig.

The mesh is never edited: only vertex groups (skinning data) are added, the head
is parented to a bone, and the armature object carries the scale/placement.

Armature local space == float-root local space / SCALE, so world positions are
converted with a single division.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix, Vector

P = globals().get("UNRECORDED_PARAMS", {})
TRIAL = Path(P.get("trial_dir", ".")).resolve()
ASSET = Path(P["asset"]).resolve()
SCALE = float(P.get("scale", 0.424))

scene = bpy.context.scene
root = bpy.data.objects["USTUDIO_BOX_FLOAT_ROOT"]

work = bpy.data.collections.new("K3_EDGE_RISE_REVEAL_FABLE_V001_WORK")
scene.collection.children.link(work)

# ---------------------------------------------------------------- append asset
before = set(bpy.data.objects)
bpy.ops.wm.append(
    directory=str(ASSET) + "/Collection/",
    filename="K3_MECHA_MASCOT_ASSET",
    link=False,
)
new_objects = [o for o in bpy.data.objects if o not in before]
body = bpy.data.objects["K3_MECHA_BODY"]
head = bpy.data.objects["K3_MECHA_HEAD"]
asset_root = bpy.data.objects.get("K3_MECHA_MASCOT_ROOT")

# move the appended objects into the work collection, drop the appended collection
for obj in new_objects:
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    work.objects.link(obj)
for col in list(bpy.data.collections):
    if col.name.startswith("K3_MECHA_MASCOT_ASSET") and not col.objects and not col.children:
        bpy.data.collections.remove(col)

# ---------------------------------------------------------------- measure arms
verts = [body.matrix_world @ v.co for v in body.data.vertices]
arm_line = {}
for side, sgn in (("L", 1), ("R", -1)):
    band_all = [v for v in verts if sgn * v.x > 0.22 and v.z > 1.15]
    x_lo, x_hi = min(sgn * v.x for v in band_all), max(sgn * v.x for v in band_all)
    line = []
    for i in range(18):
        a = x_lo + (x_hi - x_lo) * i / 18.0
        b = x_lo + (x_hi - x_lo) * (i + 1) / 18.0
        band = [v for v in band_all if a <= sgn * v.x < b]
        if len(band) < 4:
            continue
        c = sum(band, Vector()) / len(band)
        line.append(c)
    arm_line[side] = line

def arc_point(line, fraction):
    lengths = [0.0]
    for a, b in zip(line, line[1:]):
        lengths.append(lengths[-1] + (b - a).length)
    target = lengths[-1] * fraction
    for i, (a, b) in enumerate(zip(line, line[1:])):
        if lengths[i] <= target <= lengths[i + 1]:
            seg = lengths[i + 1] - lengths[i]
            t = 0.0 if seg < 1e-9 else (target - lengths[i]) / seg
            return a.lerp(b, t)
    return line[-1]

# ---------------------------------------------------------------- armature
arm_data = bpy.data.armatures.new("K3_FABLE_MASCOT_RIG")
arm_obj = bpy.data.objects.new("K3_FABLE_MASCOT", arm_data)
work.objects.link(arm_obj)
arm_obj.parent = root
# bind at asset scale so the heat weighting sees mesh and bones in the same
# space; the film scale is applied after the bind
arm_obj.matrix_basis = Matrix.Identity(4)

bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode="EDIT")
eb = arm_data.edit_bones

# measured landmarks (asset units, +Z up, -Y front)
PELVIS_Z = 0.680
SPINE_Z = 0.960
CHEST_Z = 1.235
NECK_Z = 1.520
HEAD_TOP = 2.075
HIP_X, HIP_Z = 0.172, 0.620
KNEE_X, KNEE_Z = 0.238, 0.352
ANKLE_X, ANKLE_Z = 0.241, 0.092
TOE_Y, TOE_Z = -0.046, 0.016
SH_X, SH_Z = 0.170, 1.268

def bone(name, head_co, tail_co, parent=None, roll_axis=Vector((1, 0, 0)), connect=False):
    b = eb.new(name)
    b.head, b.tail = Vector(head_co), Vector(tail_co)
    if parent:
        b.parent = eb[parent]
        b.use_connect = connect
    b.align_roll(Vector(roll_axis))
    return b

X_HINT, Z_HINT = Vector((1, 0, 0)), Vector((0, 0, 1))
bone("ROOT", (0, 0, PELVIS_Z), (0, 0, SPINE_Z), None, X_HINT)
bone("SPINE", (0, 0, SPINE_Z), (0, 0, CHEST_Z), "ROOT", X_HINT, True)
bone("CHEST", (0, 0, CHEST_Z), (0, 0, NECK_Z), "SPINE", X_HINT, True)
bone("HEAD", (0, 0, NECK_Z), (0, 0, HEAD_TOP), "CHEST", X_HINT, True)
for side, sgn in (("L", 1), ("R", -1)):
    shoulder = Vector((sgn * SH_X, 0.0, SH_Z))
    elbow = arc_point(arm_line[side], 0.5)
    hand = arm_line[side][-1]
    bone(f"CLAV.{side}", (0, 0, SH_Z - 0.02), shoulder, "CHEST", Z_HINT)
    bone(f"UPPERARM.{side}", shoulder, elbow, f"CLAV.{side}", Z_HINT, True)
    bone(f"FOREARM.{side}", elbow, hand, f"UPPERARM.{side}", Z_HINT, True)
    bone(f"THIGH.{side}", (sgn * HIP_X, 0, HIP_Z), (sgn * KNEE_X, 0, KNEE_Z), "ROOT", X_HINT)
    bone(f"SHIN.{side}", (sgn * KNEE_X, 0, KNEE_Z), (sgn * ANKLE_X, 0, ANKLE_Z), f"THIGH.{side}", X_HINT, True)
    bone(f"FOOT.{side}", (sgn * ANKLE_X, 0, ANKLE_Z), (sgn * ANKLE_X, TOE_Y, TOE_Z), f"SHIN.{side}", Z_HINT, True)

bpy.ops.object.mode_set(mode="OBJECT")

# ---------------------------------------------------------------- skinning
# Blender's heat weighting collapses on this mesh (it handed almost every
# vertex to FOOT.R), so the weights are computed explicitly: inverse-distance
# to each bone segment, restricted to the vertex's own side for paired bones.
skin_method = "DETERMINISTIC_SEGMENT_DISTANCE"
body.parent = arm_obj
body.matrix_parent_inverse = Matrix.Identity(4)
body.matrix_basis = Matrix.Identity(4)
for group in list(body.vertex_groups):
    body.vertex_groups.remove(group)
mod = body.modifiers.new("K3_ARMATURE", "ARMATURE")
mod.object = arm_obj

SEGMENTS = [(b.name, b.head_local.copy(), b.tail_local.copy()) for b in arm_data.bones]
POWER, K_BONES, EPS = 3.6, 3, 0.008
SIDE_PENALTY = 4.0

def segment_distance(p, a, b):
    ab = b - a
    denom = ab.length_squared
    t = 0.0 if denom < 1e-12 else max(0.0, min(1.0, (p - a).dot(ab) / denom))
    return (p - (a + ab * t)).length

groups = {name: body.vertex_groups.new(name=name) for name, _, _ in SEGMENTS}
for vert in body.data.vertices:
    p = vert.co
    scored = []
    for name, a, b in SEGMENTS:
        d = segment_distance(p, a, b)
        if name.endswith(".L") and p.x < -0.02:
            d *= SIDE_PENALTY
        elif name.endswith(".R") and p.x > 0.02:
            d *= SIDE_PENALTY
        scored.append((d, name))
    scored.sort()
    chosen = scored[:K_BONES]
    weights = [(1.0 / (d + EPS) ** POWER, name) for d, name in chosen]
    total = sum(w for w, _ in weights)
    for w, name in weights:
        groups[name].add([vert.index], w / total, "REPLACE")

# head: rigid, parented to the HEAD bone (no mesh change at all).
# Blender anchors bone-parented children at the bone TAIL, so the parent
# inverse must undo the rest tail transform for the head to bind in place.
head.parent = arm_obj
head.parent_type = "BONE"
head.parent_bone = "HEAD"
head_bone = arm_data.bones["HEAD"]
rest_tail = head_bone.matrix_local @ Matrix.Translation(Vector((0.0, head_bone.length, 0.0)))
head.matrix_parent_inverse = rest_tail.inverted()
head.matrix_basis = Matrix.Translation(Vector((0.0, 0.0, 1.798)))  # rest place, armature units

# parent_set() bakes a parent inverse that cancels the armature transform;
# clear it so the body inherits the film scale exactly like the head does
body.matrix_parent_inverse = Matrix.Identity(4)
body.matrix_basis = Matrix.Identity(4)
arm_obj.matrix_basis = Matrix.Diagonal((SCALE, SCALE, SCALE, 1.0))

if asset_root:
    bpy.data.objects.remove(asset_root, do_unlink=True)

groups = sorted(g.name for g in body.vertex_groups)
weighted = sum(1 for v in body.data.vertices if v.groups)

report = {
    "asset": str(ASSET),
    "scale": SCALE,
    "character_height_m": round(HEAD_TOP * SCALE, 4),
    "bones": [b.name for b in arm_data.bones],
    "skin_method": skin_method,
    "vertex_groups": groups,
    "weighted_vertices": weighted,
    "total_vertices": len(body.data.vertices),
    "mesh_untouched": {
        "body_vertices": len(body.data.vertices),
        "body_polygons": len(body.data.polygons),
        "head_vertices": len(head.data.vertices),
        "note": "seuls des vertex groups ont ete ajoutes ; aucune coordonnee de vertex modifiee",
    },
    "landmarks_asset_units": {
        "pelvis_z": PELVIS_Z, "hip": [HIP_X, HIP_Z], "knee": [KNEE_X, KNEE_Z],
        "ankle": [ANKLE_X, ANKLE_Z], "shoulder": [SH_X, SH_Z],
        "elbow_L": [round(c, 4) for c in arc_point(arm_line["L"], 0.5)],
        "hand_L": [round(c, 4) for c in arm_line["L"][-1]],
    },
}
(TRIAL / "diagnostics" / "rig-report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

bpy.ops.wm.save_as_mainfile(filepath=str(TRIAL / "scene" / "trial.blend"))
print("UNRECORDED_RESULT=" + json.dumps({
    "skin_method": skin_method, "bones": len(arm_data.bones),
    "weighted_vertices": weighted, "total_vertices": len(body.data.vertices),
    "height_m": report["character_height_m"],
    "elbow_L": report["landmarks_asset_units"]["elbow_L"],
    "hand_L": report["landmarks_asset_units"]["hand_L"],
}, ensure_ascii=False))
