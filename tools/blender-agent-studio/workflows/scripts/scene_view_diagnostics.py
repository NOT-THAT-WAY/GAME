"""Project scene objects into a camera frame and report deterministic visibility metrics."""
import bpy
import json
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

P = globals().get("STUDIO_PARAMS", globals().get("UNRECORDED_PARAMS", {}))
scene = bpy.context.scene
frame = int(P.get("frame", scene.frame_current))
scene.frame_set(frame)
camera_name = str(P.get("camera", "")).strip()
camera = bpy.data.objects.get(camera_name) if camera_name else scene.camera
if not camera or camera.type != "CAMERA":
    raise RuntimeError("Caméra active ou demandée introuvable")

collection_name = str(P.get("collection", "")).strip()
if collection_name:
    collection = bpy.data.collections.get(collection_name)
    if not collection:
        raise RuntimeError("Collection introuvable: " + collection_name)
    targets = [obj for obj in collection.all_objects if obj.type == "MESH" and not obj.hide_render]
else:
    targets = [obj for obj in scene.objects if obj.type == "MESH" and not obj.hide_render]

depsgraph = bpy.context.evaluated_depsgraph_get()
origin = camera.matrix_world.translation
results = []
for obj in targets:
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    projected = [world_to_camera_view(scene, camera, corner) for corner in corners]
    xs, ys, zs = [p.x for p in projected], [p.y for p in projected], [p.z for p in projected]
    raw = [min(xs), min(ys), max(xs), max(ys)]
    clipped = [max(0.0, raw[0]), max(0.0, raw[1]), min(1.0, raw[2]), min(1.0, raw[3])]
    width = max(0.0, clipped[2] - clipped[0])
    height = max(0.0, clipped[3] - clipped[1])
    coverage = width * height
    behind = max(zs) <= 0
    outside = raw[2] <= 0 or raw[0] >= 1 or raw[3] <= 0 or raw[1] >= 1
    partial = raw[0] < 0 or raw[1] < 0 or raw[2] > 1 or raw[3] > 1
    center = sum(corners, Vector()) / len(corners)
    direction = center - origin
    distance = direction.length
    occluded_by = None
    if distance > 1e-6:
        hit, _, _, _, hit_obj, _ = scene.ray_cast(depsgraph, origin, direction.normalized(), distance=max(0.0, distance - 1e-5))
        if hit and hit_obj and hit_obj != obj:
            occluded_by = hit_obj.original.name if getattr(hit_obj, "original", None) else hit_obj.name
    clip_near = min(zs) < camera.data.clip_start
    clip_far = max(zs) > camera.data.clip_end
    if behind or outside or coverage == 0:
        verdict = "off-frame"
    elif occluded_by:
        verdict = "occluded"
    elif partial or clip_near or clip_far:
        verdict = "partial"
    else:
        verdict = "visible"
    results.append({
        "object": obj.name,
        "verdict": verdict,
        "occluded_by": occluded_by,
        "frame_bounds": [round(value, 6) for value in raw],
        "clipped_bounds": [round(value, 6) for value in clipped],
        "coverage": round(coverage, 6),
        "center_offset": [round((raw[0] + raw[2]) / 2 - 0.5, 6), round((raw[1] + raw[3]) / 2 - 0.5, 6)],
        "depth_range": [round(min(zs), 6), round(max(zs), 6)],
        "clip_near": clip_near,
        "clip_far": clip_far,
    })

payload = {
    "schema_version": 1,
    "source": bpy.data.filepath,
    "scene": scene.name,
    "frame": frame,
    "camera": camera.name,
    "lens": camera.data.lens,
    "clip": [camera.data.clip_start, camera.data.clip_end],
    "resolution": [scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage],
    "collection": collection_name or None,
    "summary": {name: sum(1 for item in results if item["verdict"] == name) for name in ("visible", "partial", "occluded", "off-frame")},
    "objects": results,
}
output = Path(P["output_dir"])
output.mkdir(parents=True, exist_ok=True)
path = output / "scene-view-diagnostics.json"
path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps({"diagnostics": str(path), "summary": payload["summary"], "saved": False}, ensure_ascii=False))
