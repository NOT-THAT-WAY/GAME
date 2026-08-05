"""Inspection en lecture seule de l'asset mecha-mascot-v002."""
import bpy, json
from mathutils import Vector

out = {"objects": {}, "collections": [c.name for c in bpy.data.collections]}
for obj in bpy.data.objects:
    info = {"type": obj.type, "parent": obj.parent.name if obj.parent else None,
            "loc": list(obj.location), "scale": list(obj.scale),
            "dim": list(obj.dimensions),
            "materials": [m.name if m else None for m in obj.data.materials] if hasattr(obj.data, "materials") else []}
    if obj.type == 'MESH':
        pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        info["world_bbox"] = {"min": list(mn), "max": list(mx), "size": list(mx - mn)}
        info["verts"] = len(obj.data.vertices)
        info["vgroups"] = [g.name for g in obj.vertex_groups]
        info["modifiers"] = [m.type for m in obj.modifiers]
    if obj.type == 'ARMATURE':
        info["bones"] = [{"name": b.name, "head": list(b.head_local), "tail": list(b.tail_local),
                          "parent": b.parent.name if b.parent else None} for b in obj.data.bones]
    out["objects"][obj.name] = info
print("ASSET_JSON=" + json.dumps(out, indent=1))
