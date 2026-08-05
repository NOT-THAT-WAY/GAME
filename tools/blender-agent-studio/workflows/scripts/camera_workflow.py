"""Create or update a scale-aware BAS camera rig without saving the blend file."""
import bpy
import json
import math
from mathutils import Vector


P = globals().get("STUDIO_PARAMS", globals().get("UNRECORDED_PARAMS", {}))
pattern = P.get("pattern", "orbit-360")
duration = float(P.get("duration", 6))
intensity = float(P.get("intensity", 1))
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

collection_name = str(P.get("target_collection", "")).strip()
source_collection = None
if collection_name:
    source_collection = bpy.data.collections.get(collection_name)
    if not source_collection:
        raise RuntimeError("Collection cible introuvable: " + collection_name)
    visible_meshes = [obj for obj in source_collection.all_objects if obj.type == "MESH" and not obj.hide_render]
else:
    visible_meshes = [obj for obj in bpy.context.selected_objects if obj.type == "MESH" and not obj.hide_render]
    if not visible_meshes:
        visible_meshes = [
            obj for obj in scene.objects
            if obj.type == "MESH" and not obj.hide_render
            and not obj.name.lower().startswith(("ref_", "void_", "bas_", "ustudio_"))
        ]
if not visible_meshes:
    raise RuntimeError("Aucun mesh visible ou sélectionné pour calculer la cible caméra")

depsgraph = bpy.context.evaluated_depsgraph_get()
points = []
for obj in visible_meshes:
    evaluated = obj.evaluated_get(depsgraph)
    points.extend(evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box)
low = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
high = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
center = (low + high) / 2
radius = max((high - low).length / 2, 0.1)


def ensure_empty(name, location):
    obj = bpy.data.objects.get(name)
    if not obj:
        obj = bpy.data.objects.new(name, None)
        scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (0, 0, 0)
    obj.animation_data_clear()
    return obj


preferences = bpy.context.preferences.edit
old_interpolation = preferences.keyframe_new_interpolation_type
preferences.keyframe_new_interpolation_type = "BEZIER"
try:
    target = ensure_empty("BAS_CAMERA_TARGET", center)
    focus = ensure_empty("BAS_CAMERA_FOCUS", center)
    pivot = ensure_empty("BAS_CAMERA_PIVOT", center)
    pivot["bas_previous_scene_state"] = json.dumps(previous)
    cam = bpy.data.objects.get("BAS_CAMERA")
    if not cam:
        data = bpy.data.cameras.new("BAS_CAMERA_DATA")
        cam = bpy.data.objects.new("BAS_CAMERA", data)
        scene.collection.objects.link(cam)
    cam.animation_data_clear()
    cam.data.animation_data_clear()
    cam.parent = pivot
    cam.matrix_parent_inverse.identity()
    for constraint in list(cam.constraints):
        cam.constraints.remove(constraint)
    track = cam.constraints.new("TRACK_TO")
    track.target, track.track_axis, track.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
    cam.data.dof.use_dof = bool(P.get("use_dof", True))
    cam.data.dof.focus_object = focus
    scene.camera = cam

    for marker in list(scene.timeline_markers):
        if marker.name.startswith("BAS_"):
            scene.timeline_markers.remove(marker)

    def key(frame, azimuth, distance, z, focal, marker_name):
        scene.frame_set(frame)
        pivot.rotation_euler = (0, 0, math.radians(azimuth))
        pivot.keyframe_insert("rotation_euler", frame=frame)
        cam.location = (0, -distance, z)
        cam.keyframe_insert("location", frame=frame)
        cam.data.lens = focal
        cam.data.keyframe_insert("lens", frame=frame)
        if marker_name:
            scene.timeline_markers.new("BAS_" + marker_name, frame=frame)

    def frame_at(ratio):
        return max(1, round(1 + ratio * (end - 1)))

    if pattern == "orbit-360":
        if "distance_multiplier" in P:
            distance = radius * float(P["distance_multiplier"])
        else:
            distance = float(P.get("distance", radius * 4.0))
        distance = max(distance, radius * 1.2)
        focal = float(P.get("lens", 70))
        direction = -1 if P.get("direction", "gauche") == "gauche" else 1
        hold = max(2, round(end * 0.1))
        key(1, 0, distance, 0, focal, "HOLD_IN")
        key(hold, 0, distance, 0, focal, "MOVE")
        key(end - hold, direction * 360, distance, 0, focal, "HOLD_OUT")
        key(end, direction * 360, distance, 0, focal, "REST")
    elif pattern == "lowrise-orbit":
        near = radius * 1.35
        mid = radius * (1.35 + 1.9 * intensity)
        far = radius * (3.25 + 2.4 * intensity)
        key(1, 0, near, -radius * 0.48 * intensity, 28, "LOW")
        key(frame_at(0.14), 0, near, -radius * 0.48 * intensity, 28, "TURN")
        key(frame_at(0.44), -45 * intensity, mid, -radius * 0.10 * intensity, 70, "RISE")
        key(frame_at(0.83), 0, far * 0.88, 0, 70, "RETURN")
        key(end, 0, far, 0, 70, "REST")
    elif pattern == "arc-crane-vertigo":
        near = radius * 1.55
        mid = radius * (1.55 + 1.45 * intensity)
        far = radius * (3.0 + 2.5 * intensity)
        key(1, -15 * intensity, near, -radius * 0.35 * intensity, 35, "HOLD")
        key(frame_at(0.11), -15 * intensity, near, -radius * 0.35 * intensity, 35, "ARC_CRANE")
        key(frame_at(0.53), -65 * intensity, mid, radius * 0.60 * intensity, 70, "SWINGBACK")
        key(frame_at(0.88), 0, far * 0.90, 0, 52, "VERTIGO")
        key(frame_at(0.97), 0, far, 0, 57, "REST")
        key(end, 0, far, 0, 57, None)
    else:
        raise RuntimeError("Pattern inconnu: " + pattern)

    scene.frame_set(1)
finally:
    preferences.keyframe_new_interpolation_type = old_interpolation

print("UNRECORDED_RESULT=" + json.dumps({
    "pattern": pattern,
    "frames": [1, end],
    "fps": fps,
    "camera": cam.name,
    "target": list(center),
    "focus": focus.name,
    "radius": radius,
    "evaluated_geometry": True,
    "target_collection": source_collection.name if source_collection else None,
    "saved": False,
}))
