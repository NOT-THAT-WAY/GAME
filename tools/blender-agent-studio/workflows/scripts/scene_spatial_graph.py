"""Build a read-only structural and spatial graph for agent grounding."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

P = globals().get("STUDIO_PARAMS", globals().get("UNRECORDED_PARAMS", {}))
scene = bpy.context.scene
collection_name = str(P.get("collection", "")).strip()
max_objects = int(P.get("max_objects", 80))
if collection_name:
    collection = bpy.data.collections.get(collection_name)
    if not collection:
        raise RuntimeError("Collection introuvable: " + collection_name)
    candidates = [obj for obj in collection.all_objects if obj in scene.objects[:]]
else:
    candidates = list(scene.objects)
candidates = [obj for obj in candidates if obj.type in {"MESH", "EMPTY", "CAMERA", "LIGHT"}][:max_objects]

def role(obj):
    name = obj.name.lower()
    if obj.type in {"CAMERA", "LIGHT"} or any(token in name for token in ("control", "target", "pivot", "root", "rig")):
        return "control"
    if any(token in name for token in ("ref_", "reference", "calage")):
        return "reference"
    if obj.type == "MESH" and (obj.parent is None or any(token in name for token in ("body", "shell", "device"))):
        return "core"
    return "accessory"

def bounds(obj):
    if obj.type == "MESH":
        points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    else:
        points = [obj.matrix_world.translation]
    low = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    high = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return low, high

records = []
boxes = {}
for obj in candidates:
    low, high = bounds(obj)
    boxes[obj.name] = (low, high)
    records.append({
        "name": obj.name,
        "type": obj.type,
        "role": role(obj),
        "parent": obj.parent.name if obj.parent else None,
        "collections": [collection.name for collection in obj.users_collection],
        "bounds_min": [round(v, 6) for v in low],
        "bounds_max": [round(v, 6) for v in high],
        "center": [round(v, 6) for v in ((low + high) / 2)],
        "dimensions": [round(v, 6) for v in (high - low)],
        "hidden_render": bool(obj.hide_render),
    })

relations = []
for index, left in enumerate(candidates):
    for right in candidates[index + 1:]:
        a0, a1 = boxes[left.name]
        b0, b1 = boxes[right.name]
        gaps = Vector((max(0.0, a0.x - b1.x, b0.x - a1.x), max(0.0, a0.y - b1.y, b0.y - a1.y), max(0.0, a0.z - b1.z, b0.z - a1.z)))
        distance = gaps.length
        if distance <= float(P.get("relation_distance", 0.25)):
            relations.append({
                "from": left.name,
                "to": right.name,
                "aabb_distance": round(distance, 6),
                "relation": "overlap_or_contact" if distance == 0 else "near",
                "parented": left.parent == right or right.parent == left,
            })

payload = {
    "schema_version": 1,
    "source": bpy.data.filepath,
    "scene": scene.name,
    "collection": collection_name or None,
    "truncated": len(candidates) >= max_objects,
    "objects": records,
    "relations": relations,
    "summary": {"objects": len(records), "relations": len(relations), "roles": {name: sum(1 for item in records if item["role"] == name) for name in ("core", "accessory", "control", "reference")}},
}
output = Path(P["output_dir"])
output.mkdir(parents=True, exist_ok=True)
path = output / "scene-spatial-graph.json"
path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps({"graph": str(path), "summary": payload["summary"], "saved": False}, ensure_ascii=False))
