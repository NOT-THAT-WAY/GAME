"""Build a namespaced, copyable camera rig and a reproducible shot manifest."""
import bpy
import json
import math
import re
from pathlib import Path
from mathutils import Vector


P = globals().get("STUDIO_PARAMS", globals().get("UNRECORDED_PARAMS", {}))
template = P.get("template", "studio-orbit")
duration = float(P.get("duration", 6.0))
lens = float(P.get("lens", 70.0))
distance_multiplier = float(P.get("distance_multiplier", 4.0))
direction = -1 if P.get("direction", "gauche") == "gauche" else 1
collection_name = str(P.get("target_collection", "")).strip()
job_id = re.sub(r"[^A-Za-z0-9]", "", str(P.get("job_id", "manual")))[:8] or "MANUAL"
output_dir = Path(P["output_dir"])
output_dir.mkdir(parents=True, exist_ok=True)

scene = bpy.context.scene
previous = {
    "camera": scene.camera.name if scene.camera else None,
    "frame_start": scene.frame_start,
    "frame_end": scene.frame_end,
    "frame_current": scene.frame_current,
    "fps": scene.render.fps,
    "fps_base": scene.render.fps_base,
}
if "fps" in P:
    fps = int(P["fps"])
    scene.render.fps = fps
    scene.render.fps_base = 1.0
else:
    fps = scene.render.fps / scene.render.fps_base if scene.render.fps_base else float(scene.render.fps)
end = max(2, round(duration * fps))
scene.frame_start, scene.frame_end = 1, end

if collection_name:
    source_collection = bpy.data.collections.get(collection_name)
    if not source_collection:
        raise RuntimeError("Collection cible introuvable: " + collection_name)
    candidates = [obj for obj in source_collection.all_objects if obj.type == "MESH" and not obj.hide_render]
else:
    source_collection = None
    candidates = [obj for obj in bpy.context.selected_objects if obj.type == "MESH" and not obj.hide_render]
    if not candidates and bpy.context.view_layer.objects.active:
        active = bpy.context.view_layer.objects.active
        active_collections = [collection for collection in active.users_collection if collection.name != scene.collection.name]
        if active_collections:
            source_collection = active_collections[0]
            candidates = [obj for obj in source_collection.all_objects if obj.type == "MESH" and not obj.hide_render]
    if not candidates:
        candidates = [
            obj for obj in scene.objects
            if obj.type == "MESH" and not obj.hide_render
            and not obj.name.lower().startswith(("ref_", "void_", "bas_", "ustudio_"))
        ]
if not candidates:
    raise RuntimeError("Aucun mesh visible ou sélectionné pour construire le rig caméra")

depsgraph = bpy.context.evaluated_depsgraph_get()
points = []
for obj in candidates:
    evaluated = obj.evaluated_get(depsgraph)
    points.extend(evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box)
minimum = Vector((min(point.x for point in points), min(point.y for point in points), min(point.z for point in points)))
maximum = Vector((max(point.x for point in points), max(point.y for point in points), max(point.z for point in points)))
center = (minimum + maximum) / 2
radius = max((maximum - minimum).length / 2, 0.1)
distance = max(radius * distance_multiplier, radius + 0.1)

prefix = "BAS_SHOT_" + job_id.upper()
rig_collection = bpy.data.collections.new(prefix)
scene.collection.children.link(rig_collection)
rig_collection["bas_schema"] = 2
rig_collection["bas_template"] = template
rig_collection["bas_job_id"] = job_id
rig_collection["bas_previous_scene_state"] = json.dumps(previous)


def empty(name, location):
    obj = bpy.data.objects.new(prefix + "_" + name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.location = location
    rig_collection.objects.link(obj)
    return obj


root = empty("ROOT", center)
pivot = empty("PIVOT", center)
target = empty("TARGET", center)
focus = empty("FOCUS", center)
pivot.parent = root
target.parent = root
focus.parent = root
camera_data = bpy.data.cameras.new(prefix + "_CAMERA_DATA")
camera_data.lens = lens
camera_data.show_passepartout = True
camera_data.passepartout_alpha = 0.85
camera_data.dof.use_dof = bool(P.get("use_dof", True))
camera_data.dof.focus_object = focus
camera = bpy.data.objects.new(prefix + "_CAMERA", camera_data)
rig_collection.objects.link(camera)
camera.parent = pivot
track = camera.constraints.new("TRACK_TO")
track.name = prefix + "_TRACK"
track.target = target
track.track_axis = "TRACK_NEGATIVE_Z"
track.up_axis = "UP_Y"
scene.camera = camera

markers = []


def marker(name, frame):
    full_name = prefix + "_" + name
    scene.timeline_markers.new(full_name, frame=frame)
    markers.append({"name": full_name, "frame": frame})


def key(frame, angle, local_y, local_z, focal, name):
    scene.frame_set(frame)
    pivot.rotation_euler = (0, 0, math.radians(angle))
    pivot.keyframe_insert("rotation_euler", frame=frame, group=prefix)
    camera.location = (0, local_y, local_z)
    camera.keyframe_insert("location", frame=frame, group=prefix)
    camera.data.lens = focal
    camera.data.keyframe_insert("lens", frame=frame, group=prefix)
    marker(name, frame)


hold = max(2, round(end * 0.1))
if template == "studio-orbit":
    key(1, 0, -distance, 0, lens, "HOLD_IN")
    key(hold, 0, -distance, 0, lens, "MOVE")
    key(end - hold, direction * 360, -distance, 0, lens, "HOLD_OUT")
    key(end, direction * 360, -distance, 0, lens, "REST")
elif template == "dolly-reveal":
    key(1, 0, -distance * 0.38, -radius * 0.18, max(24, lens * 0.55), "DETAIL")
    key(hold, 0, -distance * 0.38, -radius * 0.18, max(24, lens * 0.55), "MOVE")
    key(end - hold, 0, -distance * 1.18, 0, lens, "REVEAL")
    key(end, 0, -distance * 1.18, 0, lens, "REST")
elif template == "crane-hero":
    key(1, direction * 18, -distance * 0.55, -radius * 0.55, max(28, lens * 0.7), "LOW")
    key(hold, direction * 18, -distance * 0.55, -radius * 0.55, max(28, lens * 0.7), "CRANE")
    key(end - hold, direction * 48, -distance, radius * 0.65, lens, "HERO")
    key(end, direction * 48, -distance, radius * 0.65, lens, "REST")
elif template == "three-quarter-rest":
    key(1, direction * 42, -distance, radius * 0.08, lens, "HOLD_IN")
    key(hold, direction * 42, -distance, radius * 0.08, lens, "DRIFT")
    key(end - hold, direction * 28, -distance * 1.06, 0, lens * 1.05, "SETTLE")
    key(end, direction * 28, -distance * 1.06, 0, lens * 1.05, "REST")
else:
    raise RuntimeError("Template caméra inconnu: " + template)

for owner in (pivot, camera, camera.data):
    animation = getattr(owner, "animation_data", None)
    action = getattr(animation, "action", None) if animation else None
    if action:
        curves = []
        if hasattr(action, "fcurves"):
            curves.extend(action.fcurves)
        else:
            for layer in action.layers:
                for strip in layer.strips:
                    for channelbag in strip.channelbags:
                        curves.extend(channelbag.fcurves)
        for curve in curves:
            curve.auto_smoothing = "CONT_ACCEL"
            for point in curve.keyframe_points:
                point.interpolation = "BEZIER"
                point.handle_left_type = "AUTO_CLAMPED"
                point.handle_right_type = "AUTO_CLAMPED"

scene.frame_set(1)
manifest = {
    "schema_version": 2,
    "job_id": job_id,
    "template": template,
    "scene": scene.name,
    "target_collection": source_collection.name if source_collection else None,
    "target_objects": [obj.name for obj in candidates],
    "bounds": {"min": list(minimum), "max": list(maximum), "center": list(center), "radius": radius, "evaluated_geometry": True},
    "settings": {"duration": duration, "fps": fps, "lens": lens, "distance_multiplier": distance_multiplier, "direction": P.get("direction", "gauche")},
    "rig": {"collection": rig_collection.name, "root": root.name, "pivot": pivot.name, "target": target.name, "focus": focus.name, "camera": camera.name},
    "previous_scene_state": previous,
    "markers": markers,
    "saved": False,
}
manifest_path = output_dir / "shot-manifest.json"
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps({"manifest": str(manifest_path), "rig": manifest["rig"], "markers": markers, "saved": False}, ensure_ascii=False))
