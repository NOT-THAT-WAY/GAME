"""Complement d'audit : valeurs de keyframes et bounding boxes monde.

Lecture seule, aucune modification ni sauvegarde.
"""
import bpy
import json

sc = bpy.context.scene
deps = bpy.context.evaluated_depsgraph_get()

out = {"fps": sc.render.fps, "keyframes": {}, "world_bounds_frame1": {},
       "world_bounds_mid": {}, "panel_world": {}}

def iter_fcurves(action):
    for layer in action.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                yield cb.slot.identifier if cb.slot else None, cb.fcurves

for name in ["USTUDIO_PLAYHEAD_BACK", "USTUDIO_PLAYHEAD_FLOOR",
             "USTUDIO_BOX_FLOAT_ROOT", "USTUDIO_BOX_TARGET", "USTUDIO_BOX_CAMERA"]:
    ob = bpy.data.objects.get(name)
    if not ob or not ob.animation_data or not ob.animation_data.action:
        continue
    act = ob.animation_data.action
    curves = {}
    for slot, fcs in iter_fcurves(act):
        for fc in fcs:
            key = f"{fc.data_path}[{fc.array_index}]"
            curves[key] = [
                {"f": round(k.co.x, 2), "v": round(k.co.y, 4),
                 "interp": k.interpolation}
                for k in fc.keyframe_points
            ]
    out["keyframes"][name] = curves

# camera data action (lens)
cam = bpy.data.objects["USTUDIO_BOX_CAMERA"]
if cam.data.animation_data and cam.data.animation_data.action:
    curves = {}
    for slot, fcs in iter_fcurves(cam.data.animation_data.action):
        for fc in fcs:
            curves[f"{fc.data_path}[{fc.array_index}]"] = [
                {"f": round(k.co.x, 2), "v": round(k.co.y, 4)}
                for k in fc.keyframe_points
            ]
    out["keyframes"]["USTUDIO_BOX_CAMERA.lens"] = curves

def world_bounds(frame):
    sc.frame_set(frame)
    res = {}
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        pts = [o.matrix_world @ v.co for v in o.bound_box_owner.data.vertices] \
            if False else None
        from mathutils import Vector
        corners = [o.matrix_world @ Vector(c) for c in o.bound_box]
        xs = [c.x for c in corners]; ys = [c.y for c in corners]; zs = [c.z for c in corners]
        res[o.name] = {
            "x": [round(min(xs), 3), round(max(xs), 3)],
            "y": [round(min(ys), 3), round(max(ys), 3)],
            "z": [round(min(zs), 3), round(max(zs), 3)],
        }
    return res

out["world_bounds_frame1"] = world_bounds(1)
out["world_bounds_mid"] = world_bounds(203)
sc.frame_set(1)

import os
dest = "${BLENDER_AGENT_STUDIO_ROOT}/projects/fl-studio-box-character-animation/analysis/template-keyframes-bounds.json"
with open(dest, "w") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print("WROTE", dest)
