"""Render a short Blender Studio capabilities reel without saving the source blend."""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector

output = Path(globals()["VIDEO_OUTPUT"])
output.mkdir(parents=True, exist_ok=False)
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = 144
scene.render.fps = 24
scene.render.resolution_x = 640
scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
frames_dir = output / "frames"
frames_dir.mkdir(parents=True, exist_ok=False)
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(frames_dir / "frame_")
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except Exception:
    pass
try:
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
except TypeError:
    pass

prefix = "USTUDIO_DEMO_VIDEO"
old = bpy.data.collections.get(prefix)
if old:
    for obj in list(old.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(old)
rig = bpy.data.collections.new(prefix)
scene.collection.children.link(rig)

target = bpy.data.objects.new(prefix + "_TARGET", None)
target.location = (0.1, -10.8, 11.2)
rig.objects.link(target)
source_camera = bpy.data.objects.get("flroom_cam_front") or scene.camera
camera = source_camera.copy()
camera.data = source_camera.data.copy()
camera.name = prefix + "_CAMERA"
camera.data.name = prefix + "_CAMERA_DATA"
rig.objects.link(camera)
for constraint in list(camera.constraints):
    camera.constraints.remove(constraint)
track = camera.constraints.new("TRACK_TO")
track.target = target
track.track_axis = "TRACK_NEGATIVE_Z"
track.up_axis = "UP_Y"
scene.camera = camera

poses = [
    (1, (0, -140, 11), 50),
    (32, (0, -105, 15), 58),
    (68, (-64, -96, 37), 65),
    (104, (-34, -64, 25), 60),
    (132, (0, -52, 16), 72),
    (144, (0, -52, 16), 72),
]
for frame, location, lens in poses:
    camera.location = location
    camera.data.lens = lens
    camera.keyframe_insert("location", frame=frame, group=prefix)
    camera.data.keyframe_insert("lens", frame=frame, group=prefix)

for owner in (camera, camera.data):
    action = owner.animation_data.action if owner.animation_data else None
    if action:
        for curve in getattr(action, "fcurves", []):
            for point in curve.keyframe_points:
                point.interpolation = "BEZIER"
                point.handle_left_type = "AUTO_CLAMPED"
                point.handle_right_type = "AUTO_CLAMPED"

device = bpy.data.objects.get("flroom_device_pivot")
if device:
    device.animation_data_clear()
    base_location = device.location.copy()
    base_rotation = device.rotation_euler.copy()
    for frame in range(1, 145, 12):
        phase = 2 * math.pi * (frame - 1) / 143
        device.location = base_location + Vector((0.12 * math.sin(phase), 0.0, 0.35 * math.sin(2 * phase)))
        device.rotation_euler = (
            base_rotation.x + math.radians(1.2) * math.sin(2 * phase),
            base_rotation.y + math.radians(1.0) * math.cos(phase),
            base_rotation.z + math.radians(2.0) * math.sin(phase),
        )
        device.keyframe_insert("location", frame=frame, group=prefix)
        device.keyframe_insert("rotation_euler", frame=frame, group=prefix)
    device.location = base_location
    device.rotation_euler = base_rotation
    device.keyframe_insert("location", frame=144, group=prefix)
    device.keyframe_insert("rotation_euler", frame=144, group=prefix)

def area(name, location, energy, color, size):
    data = bpy.data.lights.new(prefix + "_" + name + "_DATA", "AREA")
    data.energy = energy
    data.color = color
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(prefix + "_" + name, data)
    obj.location = location
    rig.objects.link(obj)
    constraint = obj.constraints.new("TRACK_TO")
    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"
    return obj

rim_left = area("RIM_LEFT", (-28, -24, 24), 0, (0.08, 0.75, 1.0), 10)
rim_right = area("RIM_RIGHT", (28, -24, 22), 0, (1.0, 0.12, 0.05), 10)
for light in (rim_left, rim_right):
    light.data.energy = 0
    light.data.keyframe_insert("energy", frame=1)
    light.data.keyframe_insert("energy", frame=54)
    light.data.energy = 1800
    light.data.keyframe_insert("energy", frame=76)
    light.data.keyframe_insert("energy", frame=144)

markers = [(1, "BUILD"), (36, "CAMERA"), (72, "LIGHT"), (108, "REFINE"), (132, "FINAL")]
for frame, name in markers:
    scene.timeline_markers.new(prefix + "_" + name, frame=frame)

bpy.ops.render.render(animation=True)
manifest = {
    "schema_version": 1,
    "source": bpy.data.filepath,
    "scene": scene.name,
    "camera": camera.name,
    "frames": [1, 144],
    "fps": 24,
    "resolution": [640, 640],
    "frames_directory": str(frames_dir),
    "features": ["camera path", "focal animation", "product hover", "animated rim lighting", "agent phase markers"],
    "saved": False,
}
(output / "video-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print("UNRECORDED_VIDEO=" + json.dumps(manifest, ensure_ascii=False))
