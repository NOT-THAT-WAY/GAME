# Read-only audit, pass 2: rest pose vs imported pose, punch action motion,
# orphan datablocks (Camera/Light/parasite meshes), and Unity-frame orientation.
#
# Usage: blender -b --factory-startup --python audit_source_fbx_part2.py -- <fbx> <out.json>

import bpy, sys, json, math
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = argv[0], argv[1]

# A truly empty scene. --factory-startup still loads the default Cube/Camera/Light,
# and merely deleting the objects leaves orphan mesh/camera/light datablocks that
# would be misread as parasites coming from the FBX.
bpy.ops.wm.read_factory_settings(use_empty=True)
for coll in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights,
             bpy.data.materials, bpy.data.armatures, bpy.data.actions):
    for db in list(coll):
        coll.remove(db)

bpy.ops.import_scene.fbx(filepath=SRC)
sc = bpy.context.scene
rep = {"source": SRC,
       "scene_state": "read_factory_settings(use_empty=True) + orphan datablock purge"}

# ---- orphan / parasite datablock census (not just objects) ----
rep["datablocks"] = {
    "objects": [o.name for o in bpy.data.objects],
    "object_types": sorted({o.type for o in bpy.data.objects}),
    "cameras": [c.name for c in bpy.data.cameras],
    "lights": [l.name for l in bpy.data.lights],
    "meshes": [m.name for m in bpy.data.meshes],
    "armatures": [a.name for a in bpy.data.armatures],
    "actions": [a.name for a in bpy.data.actions],
    "collections": [c.name for c in bpy.data.collections],
    "images": [i.name for i in bpy.data.images],
    "materials": [m.name for m in bpy.data.materials],
    "empties": [o.name for o in bpy.data.objects if o.type == "EMPTY"],
}
rep["parasites_found"] = [o.name for o in bpy.data.objects
                          if o.type in {"CAMERA", "LIGHT", "EMPTY"}
                          or (o.type == "MESH" and not any(m.type == "ARMATURE" for m in o.modifiers))]

arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")


def action_fcurves(act):
    if hasattr(act, "fcurves"):
        return list(act.fcurves)
    out = []
    for layer in act.layers:
        for strip in layer.strips:
            for cb in getattr(strip, "channelbags", []):
                out.extend(cb.fcurves)
    return out


# ---- what is animated by the existing punch action, per channel ----
act = bpy.data.actions[0] if bpy.data.actions else None
if act:
    chans = {}
    for fc in action_fcurves(act):
        key = f"{fc.data_path}[{fc.array_index}]"
        vals = [round(kp.co[1], 6) for kp in fc.keyframe_points]
        chans[key] = {"keys": len(vals), "min": min(vals), "max": max(vals),
                      "delta": round(max(vals) - min(vals), 6)}
    rep["punch_action"] = {
        "name": act.name,
        "object_level_channels": {k: v for k, v in chans.items() if not k.startswith("pose.bones")},
        "moving_channels": {k: v for k, v in chans.items() if v["delta"] > 1e-6},
        "channel_count": len(chans),
    }

# ---- imported pose at frame 1 vs true rest pose ----
def pose_deviation():
    worst, worst_bone = 0.0, None
    per = {}
    for pb in arm.pose.bones:
        d = pb.matrix_basis - Matrix.Identity(4)
        m = max(abs(v) for row in d for v in row)
        per[pb.name] = {
            "max_basis_dev": round(m, 6),
            "loc": [round(v, 6) for v in pb.location],
            "quat": [round(v, 6) for v in pb.rotation_quaternion],
            "rot_mode": pb.rotation_mode,
            "scale": [round(v, 6) for v in pb.scale],
        }
        if m > worst:
            worst, worst_bone = m, pb.name
    return worst, worst_bone, per


sc.frame_set(1)
w1, b1, per1 = pose_deviation()
rep["imported_pose_frame1"] = {"max_deviation": round(w1, 6), "worst_bone": b1, "per_bone": per1}

# ---- evaluated bounds helper (Blender world frame, Z-up, metres) ----
def bounds(skinned_only=True):
    dg = bpy.context.evaluated_depsgraph_get()
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        if skinned_only and not any(m.type == "ARMATURE" for m in o.modifiers):
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        for v in me.vertices:
            wv = ev.matrix_world @ v.co
            for i in range(3):
                lo[i] = min(lo[i], wv[i]); hi[i] = max(hi[i], wv[i])
        ev.to_mesh_clear()
    return lo, hi


lo, hi = bounds()
rep["bounds_at_frame1"] = {"min": [round(v, 6) for v in lo], "max": [round(v, 6) for v in hi],
                           "size": [round(hi[i] - lo[i], 6) for i in range(3)]}

# ---- true rest pose: unassign action, clear transforms ----
if arm.animation_data:
    arm.animation_data.action = None
for pb in arm.pose.bones:
    pb.matrix_basis = Matrix.Identity(4)
arm.location = (0, 0, 0)
arm.rotation_euler = (0, 0, 0)
arm.scale = (1, 1, 1)
bpy.context.view_layer.update()

w0, b0, per0 = pose_deviation()
rep["rest_pose"] = {"max_deviation": round(w0, 6), "worst_bone": b0}

lo, hi = bounds()
rep["bounds_at_rest"] = {"min": [round(v, 6) for v in lo], "max": [round(v, 6) for v in hi],
                         "size": [round(hi[i] - lo[i], 6) for i in range(3)],
                         "height_z_m": round(hi[2] - lo[2], 6),
                         "lowest_z_m": round(lo[2], 6)}

# ---- per-mesh rest bounds, for contact / foot-sole reference ----
dg = bpy.context.evaluated_depsgraph_get()
per_mesh = {}
for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    mlo = Vector((1e9,) * 3); mhi = Vector((-1e9,) * 3)
    for v in me.vertices:
        wv = ev.matrix_world @ v.co
        for i in range(3):
            mlo[i] = min(mlo[i], wv[i]); mhi[i] = max(mhi[i], wv[i])
    ev.to_mesh_clear()
    per_mesh[o.name] = {"min": [round(v, 6) for v in mlo], "max": [round(v, 6) for v in mhi],
                        "size": [round(mhi[i] - mlo[i], 6) for i in range(3)]}
rep["rest_bounds_per_mesh"] = per_mesh

# ---- orientation reading: which axis is "forward" (character faces -Y in Blender = +Z Unity) ----
rep["orientation_note"] = {
    "blender_up": "+Z", "blender_char_height_axis": "Z",
    "feet_head_local_y": [round(arm.data.bones["BAS_PUNCH_foot.L"].head_local[1], 6),
                          round(arm.data.bones["BAS_PUNCH_foot.R"].head_local[1], 6)],
    "hands_tail_local_y": round(arm.data.bones["BAS_PUNCH_hand.L"].tail_local[1], 6),
}

with open(OUT, "w") as f:
    json.dump(rep, f, indent=2)
print("AUDIT2_WRITTEN " + OUT)
