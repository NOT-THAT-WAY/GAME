# Read-only audit of the immutable source FBX.
#
# Why ad hoc bpy: no versioned workflow in workflows/catalog/ audits an FBX
# skeleton, bind pose, skin weights and Actions. inspect-scene / deep-audit-scene
# are execution=mcp and audit an already-open scene, not an FBX import.
#
# This script NEVER writes to the source. It imports into a factory-startup
# session and dumps JSON to stdout. No .blend is saved.
#
# Usage:
#   blender --background --factory-startup --python audit_source_fbx.py -- <fbx> <out.json>

import bpy, sys, json, math
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = argv[0], argv[1]

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

bpy.ops.import_scene.fbx(filepath=SRC)

report = {"source": SRC, "blender": bpy.app.version_string}
sc = bpy.context.scene
report["scene"] = {
    "fps": sc.render.fps,
    "fps_base": sc.render.fps_base,
    "effective_fps": sc.render.fps / sc.render.fps_base,
    "frame_start": sc.frame_start,
    "frame_end": sc.frame_end,
    "unit_system": sc.unit_settings.system,
    "scale_length": sc.unit_settings.scale_length,
}

# ---------- objects ----------
objs = []
for o in bpy.data.objects:
    e = {
        "name": o.name,
        "type": o.type,
        "parent": o.parent.name if o.parent else None,
        "parent_type": o.parent_type if o.parent else None,
        "location": [round(v, 6) for v in o.location],
        "rotation_euler_deg": [round(math.degrees(v), 4) for v in o.rotation_euler],
        "scale": [round(v, 6) for v in o.scale],
        "matrix_world": [[round(v, 6) for v in row] for row in o.matrix_world],
        "modifiers": [{"name": m.name, "type": m.type,
                       "object": getattr(getattr(m, "object", None), "name", None)}
                      for m in o.modifiers],
    }
    if o.type == "MESH":
        me = o.data
        e["vertices"] = len(me.vertices)
        e["polygons"] = len(me.polygons)
        e["tris"] = sum(len(p.vertices) - 2 for p in me.polygons)
        e["vertex_groups"] = [g.name for g in o.vertex_groups]
        e["materials"] = [m.name if m else None for m in me.materials]
        e["shape_keys"] = (len(me.shape_keys.key_blocks) if me.shape_keys else 0)
    objs.append(e)
report["objects"] = objs

# ---------- armature ----------
arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
report["armature_count"] = len(arms)
armatures = []
for a in arms:
    ad = {
        "object": a.name,
        "data": a.data.name,
        "object_scale": [round(v, 6) for v in a.scale],
        "object_location": [round(v, 6) for v in a.location],
        "object_rotation_deg": [round(math.degrees(v), 4) for v in a.rotation_euler],
        "matrix_world": [[round(v, 6) for v in row] for row in a.matrix_world],
        "bone_count": len(a.data.bones),
    }
    bones = []
    for b in a.data.bones:
        # rest-space (armature local) data
        bones.append({
            "name": b.name,
            "parent": b.parent.name if b.parent else None,
            "children": [c.name for c in b.children],
            "head_local": [round(v, 6) for v in b.head_local],
            "tail_local": [round(v, 6) for v in b.tail_local],
            "length": round(b.length, 6),
            "use_deform": b.use_deform,
            "use_connect": b.use_connect,
            "roll_matrix_3x3": [[round(v, 6) for v in row] for row in b.matrix_local.to_3x3()],
            "y_axis_world_dir": [round(v, 6) for v in (a.matrix_world.to_3x3() @ (b.tail_local - b.head_local)).normalized()] if b.length > 1e-9 else None,
        })
    ad["bones"] = bones
    # pose (bind/current) check: is pose identity?
    worst = 0.0
    for pb in a.pose.bones:
        d = (pb.matrix_basis - Matrix.Identity(4))
        worst = max(worst, max(abs(v) for row in d for v in row))
    ad["pose_max_deviation_from_rest"] = round(worst, 8)
    ad["pose_is_rest"] = worst < 1e-6
    armatures.append(ad)
report["armatures"] = armatures

# ---------- skin weights ----------
weights = []
for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    arm_mods = [m for m in o.modifiers if m.type == "ARMATURE" and m.object]
    if not arm_mods:
        weights.append({"mesh": o.name, "skinned": False,
                        "vertices": len(o.data.vertices),
                        "tris": sum(len(p.vertices) - 2 for p in o.data.polygons)})
        continue
    deform_names = set()
    for m in arm_mods:
        deform_names |= {b.name for b in m.object.data.bones if b.use_deform}
    gi_to_name = {g.index: g.name for g in o.vertex_groups}
    deform_idx = {i for i, n in gi_to_name.items() if n in deform_names}
    max_inf = 0
    over4 = 0
    unweighted = 0
    worst_sum_err = 0.0
    bones_used = set()
    for v in o.data.vertices:
        gs = [g for g in v.groups if g.group in deform_idx and g.weight > 1e-6]
        n = len(gs)
        max_inf = max(max_inf, n)
        if n > 4:
            over4 += 1
        if n == 0:
            unweighted += 1
        else:
            s = sum(g.weight for g in gs)
            worst_sum_err = max(worst_sum_err, abs(s - 1.0))
            for g in gs:
                bones_used.add(gi_to_name[g.group])
    weights.append({
        "mesh": o.name, "skinned": True,
        "vertices": len(o.data.vertices),
        "tris": sum(len(p.vertices) - 2 for p in o.data.polygons),
        "max_influences": max_inf,
        "vertices_over_4_influences": over4,
        "unweighted_vertices": unweighted,
        "worst_weight_sum_error": round(worst_sum_err, 6),
        "bones_used": sorted(bones_used),
    })
report["weights"] = weights
report["total_vertices"] = sum(w["vertices"] for w in weights)
report["total_tris"] = sum(w["tris"] for w in weights)
report["skinned_vertices"] = sum(w["vertices"] for w in weights if w["skinned"])
report["skinned_tris"] = sum(w["tris"] for w in weights if w["skinned"])

# ---------- actions ----------
def action_fcurves(act):
    """Blender 5.x removed Action.fcurves (slotted actions). Walk layers/strips/channelbags."""
    if hasattr(act, "fcurves"):
        return list(act.fcurves)
    out = []
    for layer in act.layers:
        for strip in layer.strips:
            for cb in getattr(strip, "channelbags", []):
                out.extend(cb.fcurves)
    return out


acts = []
for act in bpy.data.actions:
    fr = act.frame_range
    ch = set()
    paths = set()
    fcs = action_fcurves(act)
    for fc in fcs:
        dp = fc.data_path
        paths.add(dp)
        if dp.startswith('pose.bones["'):
            ch.add(dp.split('"')[1])
    acts.append({
        "name": act.name,
        "frame_range": [round(fr[0], 4), round(fr[1], 4)],
        "fcurve_count": len(fcs),
        "bones_animated": sorted(ch),
        "sample_data_paths": sorted(paths)[:12],
        "slots": [s.identifier for s in getattr(act, "slots", [])],
        "users": act.users,
    })
report["actions"] = acts

# ---------- evaluated bounds (real geometry, world frame Z-up Blender) ----------
dg = bpy.context.evaluated_depsgraph_get()
lo = Vector((1e9, 1e9, 1e9)); hi = Vector((-1e9, -1e9, -1e9))
lo_s = Vector((1e9, 1e9, 1e9)); hi_s = Vector((-1e9, -1e9, -1e9))
for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    skinned = any(m.type == "ARMATURE" for m in o.modifiers)
    for v in me.vertices:
        w = ev.matrix_world @ v.co
        for i in range(3):
            lo[i] = min(lo[i], w[i]); hi[i] = max(hi[i], w[i])
            if skinned:
                lo_s[i] = min(lo_s[i], w[i]); hi_s[i] = max(hi_s[i], w[i])
    ev.to_mesh_clear()
report["evaluated_bounds_all_m"] = {
    "min": [round(v, 6) for v in lo], "max": [round(v, 6) for v in hi],
    "size": [round(hi[i] - lo[i], 6) for i in range(3)],
}
report["evaluated_bounds_skinned_m"] = {
    "min": [round(v, 6) for v in lo_s], "max": [round(v, 6) for v in hi_s],
    "size": [round(hi_s[i] - lo_s[i], 6) for i in range(3)],
    "height_z": round(hi_s[2] - lo_s[2], 6),
}

with open(OUT, "w") as f:
    json.dump(report, f, indent=2)
print("AUDIT_WRITTEN " + OUT)
