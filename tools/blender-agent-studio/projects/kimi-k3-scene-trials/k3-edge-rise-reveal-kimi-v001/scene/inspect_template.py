"""Inspection en lecture seule du template FL Studio Box.
Mesure : boîte, bord inférieur, sol, playhead, markers, audio, caméras existantes.
"""
import bpy, json, math
from mathutils import Vector

out = {"objects": {}, "markers": [], "frame_range": None, "fps": None, "audio": [], "cameras": []}
sc = bpy.context.scene
out["frame_range"] = [sc.frame_start, sc.frame_end]
out["fps"] = sc.render.fps

def world_bbox(obj):
    if obj.type != 'MESH':
        return None
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return {"min": list(mn), "max": list(mx), "size": list(mx - mn)}

for obj in sc.objects:
    info = {
        "type": obj.type,
        "parent": obj.parent.name if obj.parent else None,
        "loc": list(obj.location),
        "scale": list(obj.scale),
        "hide_render": obj.hide_render,
    }
    bb = world_bbox(obj)
    if bb:
        info["world_bbox"] = bb
    # animation summary
    ad = obj.animation_data
    if ad and ad.action:
        frange = [1e9, -1e9]
        for layer in ad.action.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    for fc in cb.fcurves:
                        frange[0] = min(frange[0], fc.keyframe_points[0].co.x if fc.keyframe_points else 0)
                        frange[1] = max(frange[1], fc.keyframe_points[-1].co.x if fc.keyframe_points else 0)
        if frange[0] < frange[1]:
            info["action_range"] = frange
    out["objects"][obj.name] = info

for m in sc.timeline_markers:
    out["markers"].append({"name": m.name, "frame": m.frame})

if sc.sequence_editor:
    for s in sc.sequence_editor.strips_all:
        if s.type == 'SOUND':
            out["audio"].append({"name": s.name, "file": s.sound.filepath if s.sound else None,
                                 "frame_start": s.frame_start, "duration": s.frame_final_duration})

for obj in sc.objects:
    if obj.type == 'CAMERA':
        out["cameras"].append({"name": obj.name, "lens": obj.data.lens,
                               "loc": list(obj.matrix_world.translation)})

print("INSPECT_JSON=" + json.dumps(out, indent=1))
