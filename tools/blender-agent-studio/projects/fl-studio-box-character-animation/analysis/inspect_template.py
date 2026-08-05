"""Audit lecture seule du template FL Studio Box Semantic.

Dump JSON de la structure complete : collections, objets, parents, dimensions,
actions/keyframes, markers, cameras, lumieres, materiaux, world, rendu.
Aucune modification, aucune sauvegarde.
"""
import bpy
import json

out = {}

sc = bpy.context.scene
out["scene"] = {
    "name": sc.name,
    "fps": sc.render.fps,
    "fps_base": sc.render.fps_base,
    "frame_start": sc.frame_start,
    "frame_end": sc.frame_end,
    "frame_current": sc.frame_current,
    "resolution": [sc.render.resolution_x, sc.render.resolution_y],
    "engine": sc.render.engine,
    "camera": sc.camera.name if sc.camera else None,
    "world": sc.world.name if sc.world else None,
    "unit_scale": sc.unit_settings.scale_length,
    "view_transform": sc.view_settings.view_transform,
    "look": sc.view_settings.look,
    "exposure": sc.view_settings.exposure,
}

out["markers"] = [
    {"name": m.name, "frame": m.frame, "camera": m.camera.name if m.camera else None}
    for m in sorted(sc.timeline_markers, key=lambda m: m.frame)
]


def coll_tree(c):
    return {
        "name": c.name,
        "objects": sorted(o.name for o in c.objects),
        "children": [coll_tree(ch) for ch in c.children],
    }


out["collections"] = coll_tree(bpy.context.scene.collection)

objs = []
for o in bpy.data.objects:
    entry = {
        "name": o.name,
        "type": o.type,
        "parent": o.parent.name if o.parent else None,
        "parent_type": o.parent_type if o.parent else None,
        "location": [round(v, 4) for v in o.location],
        "rotation_euler": [round(v, 4) for v in o.rotation_euler],
        "scale": [round(v, 4) for v in o.scale],
        "dimensions": [round(v, 4) for v in o.dimensions],
        "collections": [c.name for c in o.users_collection],
        "hide_render": o.hide_render,
        "animated": bool(o.animation_data and o.animation_data.action),
    }
    if o.type == "CAMERA":
        entry["lens"] = o.data.lens
        entry["sensor_width"] = o.data.sensor_width
        entry["dof_use"] = o.data.dof.use_dof
        entry["dof_focus_object"] = (
            o.data.dof.focus_object.name if o.data.dof.focus_object else None
        )
        entry["constraint_targets"] = [
            {"constraint": c.name, "type": c.type,
             "target": c.target.name if getattr(c, "target", None) else None}
            for c in o.constraints
        ]
    if o.type == "LIGHT":
        entry["light_type"] = o.data.type
        entry["energy"] = o.data.energy
        entry["color"] = [round(v, 4) for v in o.data.color]
        if o.data.type == "AREA":
            entry["shape"] = o.data.shape
            entry["size"] = o.data.size
    if o.constraints:
        entry["constraints"] = [
            {"name": c.name, "type": c.type,
             "target": getattr(c, "target", None).name if getattr(c, "target", None) else None}
            for c in o.constraints
        ]
    if o.type == "MESH":
        entry["materials"] = [m.name if m else None for m in o.data.materials]
        entry["vertices"] = len(o.data.vertices)
    objs.append(entry)
out["objects"] = sorted(objs, key=lambda e: e["name"])

actions = []
for a in bpy.data.actions:
    fcurves = []
    for layer in a.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                for fc in cb.fcurves:
                    fcurves.append({
                        "slot": cb.slot.identifier if cb.slot else None,
                        "data_path": fc.data_path,
                        "array_index": fc.array_index,
                        "keys": len(fc.keyframe_points),
                        "range": [round(fc.keyframe_points[0].co.x, 2),
                                  round(fc.keyframe_points[-1].co.x, 2)] if fc.keyframe_points else None,
                    })
    actions.append({"name": a.name, "users": a.users, "fcurves": fcurves})
out["actions"] = sorted(actions, key=lambda e: e["name"])

out["materials"] = sorted(m.name for m in bpy.data.materials)
out["images"] = [
    {"name": im.name, "source": im.source, "filepath": im.filepath,
     "size": list(im.size) if im.has_data is False else list(im.size)}
    for im in bpy.data.images
]
out["worlds"] = []
for w in bpy.data.worlds:
    wentry = {"name": w.name, "use_nodes": w.use_nodes}
    if w.use_nodes:
        wentry["nodes"] = [
            {"type": n.type, "name": n.name,
             **({"image": n.image.name if n.image else None} if n.type == "TEX_ENVIRONMENT" else {})}
            for n in w.node_tree.nodes
        ]
    out["worlds"].append(wentry)

out["workspaces"] = [w.name for w in bpy.data.workspaces]

import os
dest = os.path.join(os.path.dirname(bpy.data.filepath), "analysis", "template-structure.json")
os.makedirs(os.path.dirname(dest), exist_ok=True)
with open(dest, "w") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print("WROTE", dest)
print("OBJECTS", len(out["objects"]), "ACTIONS", len(out["actions"]),
      "MARKERS", len(out["markers"]), "MATS", len(out["materials"]))
