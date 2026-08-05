"""Read-only inspection of the imposed mecha mascot asset."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

P = globals().get("UNRECORDED_PARAMS", {})
out_path = Path(P.get("output", "diagnostics/asset-analysis.json"))

scene = bpy.context.scene
payload = {
    "file": bpy.data.filepath,
    "objects": [],
    "collections": [c.name for c in bpy.data.collections],
    "armatures": [a.name for a in bpy.data.armatures],
    "materials": [m.name for m in bpy.data.materials],
    "actions": [a.name for a in bpy.data.actions],
}

for obj in bpy.data.objects:
    entry = {
        "name": obj.name,
        "type": obj.type,
        "parent": obj.parent.name if obj.parent else None,
        "location": [round(v, 5) for v in obj.location],
        "scale": [round(v, 5) for v in obj.scale],
        "rotation_euler": [round(v, 5) for v in obj.rotation_euler],
        "modifiers": [(m.name, m.type) for m in obj.modifiers],
        "vertex_groups": [g.name for g in obj.vertex_groups],
    }
    if obj.type == "MESH":
        pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        entry["world_bbox_min"] = [round(min(p[i] for p in pts), 5) for i in range(3)]
        entry["world_bbox_max"] = [round(max(p[i] for p in pts), 5) for i in range(3)]
        entry["dimensions"] = [round(v, 5) for v in obj.dimensions]
        entry["vertices"] = len(obj.data.vertices)
        entry["polygons"] = len(obj.data.polygons)
        entry["materials"] = [m.name if m else None for m in obj.data.materials]
        # vertical slices: how wide is the mesh at each height (reveals legs/torso/arms)
        zs = [(obj.matrix_world @ v.co).z for v in obj.data.vertices]
        z0, z1 = min(zs), max(zs)
        slices = []
        n = 16
        for i in range(n):
            a = z0 + (z1 - z0) * i / n
            b = z0 + (z1 - z0) * (i + 1) / n
            band = [obj.matrix_world @ v.co for v in obj.data.vertices if a <= (obj.matrix_world @ v.co).z <= b]
            if band:
                slices.append({
                    "z": [round(a, 4), round(b, 4)],
                    "x": [round(min(p.x for p in band), 4), round(max(p.x for p in band), 4)],
                    "y": [round(min(p.y for p in band), 4), round(max(p.y for p in band), 4)],
                    "count": len(band),
                })
        entry["z_slices"] = slices
        # separate left/right lowest points (feet)
        left = [obj.matrix_world @ v.co for v in obj.data.vertices if (obj.matrix_world @ v.co).x > 0.01]
        right = [obj.matrix_world @ v.co for v in obj.data.vertices if (obj.matrix_world @ v.co).x < -0.01]
        if left:
            lo = min(left, key=lambda p: p.z)
            entry["lowest_positive_x"] = [round(lo.x, 4), round(lo.y, 4), round(lo.z, 4)]
        if right:
            lo = min(right, key=lambda p: p.z)
            entry["lowest_negative_x"] = [round(lo.x, 4), round(lo.y, 4), round(lo.z, 4)]
    payload["objects"].append(entry)

out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps({
    "objects": [(o["name"], o["type"], o.get("dimensions")) for o in payload["objects"]],
    "armatures": payload["armatures"],
    "materials": payload["materials"],
}, ensure_ascii=False))
