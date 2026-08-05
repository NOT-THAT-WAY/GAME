"""Create a standalone DRUMBOII Blob Speaker shot from the ingested asset library."""
import bpy
import json
import math
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
ASSET_LIBRARY = ROOT / "asset_library" / "imported" / "drumboii-y2k-assets.blend"
ASSET_NAME = "BLOB_SPEAKER"
PROJECT_DIR = ROOT / "projects" / "drumboii-blob-speaker-camera-study"
PROJECT_FILE = PROJECT_DIR / "Drumboii_Blob_Speaker_Camera_Study.blend"
GATE_DIR = PROJECT_DIR / "gate"
PREVIEW_FILE = PROJECT_DIR / "camera-study-preview.mp4"
PREVIEW_FRAMES = PROJECT_DIR / "_preview_frames"
MANIFEST_FILE = PROJECT_DIR / "shot-manifest.json"

FPS = 24
FRAME_START = 1
FRAME_END = 144
CAMERA_KEYS = {
    1: "K1_POSE",
    24: "K2_ANTICIPATION",
    96: "K3_MAIN_MOVE",
    132: "K4_SETTLE",
    144: "REST",
}
TARGET_LAG = 4


def material(name, color, metallic=0.0, roughness=0.35, emission=None, emission_strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission:
        emission_input = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        strength_input = bsdf.inputs.get("Emission Strength")
        if emission_input:
            emission_input.default_value = emission
        if strength_input:
            strength_input.default_value = emission_strength
    return mat


def create_empty(collection, name, location, display="PLAIN_AXES", size=0.12):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = display
    obj.empty_display_size = size
    obj.location = location
    collection.objects.link(obj)
    return obj


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def create_area_light(collection, name, location, energy, size, color, target):
    data = bpy.data.lights.new(name + "_DATA", "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    obj.location = location
    constraint = obj.constraints.new("TRACK_TO")
    constraint.name = "USTUDIO_POINT_AT_PRODUCT"
    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"
    return obj


def world_bounds(objects):
    points = [obj.matrix_world @ Vector(corner) for obj in objects if obj.type == "MESH" for corner in obj.bound_box]
    minimum = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    maximum = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return minimum, maximum


def set_key(obj, data_path, value, frame, group="DRUMBOII_CAMERA_STUDY"):
    setattr(obj, data_path, value)
    obj.keyframe_insert(data_path=data_path, frame=frame, group=group)


def iter_curves(owner):
    animation = getattr(owner, "animation_data", None)
    action = getattr(animation, "action", None) if animation else None
    if not action:
        return []
    if hasattr(action, "fcurves"):
        return list(action.fcurves)
    curves = []
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in strip.channelbags:
                curves.extend(channelbag.fcurves)
    return curves


def smooth(owner):
    for curve in iter_curves(owner):
        curve.auto_smoothing = "CONT_ACCEL"
        for point in curve.keyframe_points:
            point.interpolation = "BEZIER"
            point.handle_left_type = "AUTO_CLAMPED"
            point.handle_right_type = "AUTO_CLAMPED"


PROJECT_DIR.mkdir(parents=True, exist_ok=True)
GATE_DIR.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)

scene = bpy.context.scene
scene.name = "BLOB_SPEAKER_HERO"
scene.frame_start = FRAME_START
scene.frame_end = FRAME_END
scene.render.fps = FPS
scene.render.fps_base = 1.0
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_percentage = 100
scene.render.film_transparent = False
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.render.image_settings.color_depth = "8"
scene.render.use_file_extension = True

scene.view_settings.look = "AgX - Medium High Contrast"
world = bpy.data.worlds.new("USTUDIO_WORLD")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.006, 0.004, 0.018, 1.0)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.18
scene.world = world

product_controls = bpy.data.collections.new("PRODUCT_CONTROLS")
camera_rig = bpy.data.collections.new("CAMERA_RIG_TUTORIAL_K1_K4")
lighting = bpy.data.collections.new("LIGHTING_STUDIO")
environment = bpy.data.collections.new("ENVIRONMENT")
for collection in (product_controls, camera_rig, lighting, environment):
    scene.collection.children.link(collection)

with bpy.data.libraries.load(str(ASSET_LIBRARY), link=False) as (data_from, data_to):
    if ASSET_NAME not in data_from.collections:
        raise RuntimeError(f"Collection {ASSET_NAME} absente de {ASSET_LIBRARY}")
    data_to.collections = [ASSET_NAME]

product_collection = bpy.data.collections.get(ASSET_NAME)
product_collection.name = "PRODUCT_BLOB_SPEAKER"
scene.collection.children.link(product_collection)
product_collection["ustudio_source_library"] = str(ASSET_LIBRARY.relative_to(ROOT))
product_collection["ustudio_source_asset"] = ASSET_NAME

product_objects = list(product_collection.all_objects)
mesh_objects = [obj for obj in product_objects if obj.type == "MESH"]
bpy.context.view_layer.update()
minimum, maximum = world_bounds(mesh_objects)
product_root = create_empty(product_controls, "USTUDIO_PRODUCT_ROOT", (0, 0, 0), "CIRCLE", 0.18)
for obj in [item for item in product_objects if item.parent not in product_objects]:
    matrix = obj.matrix_world.copy()
    obj.parent = product_root
    obj.matrix_world = matrix
product_root.rotation_euler.z = math.radians(-8.0)
product_root.location.z = 0.14 - minimum.z
bpy.context.view_layer.update()
minimum, maximum = world_bounds(mesh_objects)
center = (minimum + maximum) / 2
radius = (maximum - minimum).length / 2

backdrop_mat = material("M_BACKDROP_INK", (0.018, 0.012, 0.055, 1), roughness=0.3)
pedestal_mat = material("M_PEDESTAL_BLUE", (0.025, 0.08, 0.22, 1), metallic=0.55, roughness=0.2)
ring_mat = material(
    "M_RING_MAGENTA",
    (0.4, 0.015, 0.16, 1),
    metallic=0.05,
    roughness=0.2,
    emission=(1.0, 0.015, 0.28, 1),
    emission_strength=5.0,
)

profile = [(-4.0, 0.0), (1.45, 0.0), (1.9, 0.08), (2.35, 0.38), (2.7, 0.88), (2.85, 1.45), (2.85, 5.5)]
vertices = []
for x in (-5.0, 5.0):
    vertices.extend((x, y, z) for y, z in profile)
count = len(profile)
faces = [(i, i + 1, count + i + 1, count + i) for i in range(count - 1)]
mesh = bpy.data.meshes.new("USTUDIO_CYC_MESH")
mesh.from_pydata(vertices, [], faces)
mesh.update()
cyclorama = bpy.data.objects.new("USTUDIO_CYCLORAMA", mesh)
environment.objects.link(cyclorama)
cyclorama.data.materials.append(backdrop_mat)
for polygon in mesh.polygons:
    polygon.use_smooth = True

bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=0.72, depth=0.14, location=(0, center.y, 0.07))
pedestal = bpy.context.object
pedestal.name = "USTUDIO_PEDESTAL"
for owner in list(pedestal.users_collection):
    owner.objects.unlink(pedestal)
environment.objects.link(pedestal)
pedestal.data.materials.append(pedestal_mat)
bevel = pedestal.modifiers.new("USTUDIO_SOFT_EDGE", "BEVEL")
bevel.width = 0.035
bevel.segments = 4

bpy.ops.mesh.primitive_torus_add(major_radius=0.735, minor_radius=0.012, major_segments=96, minor_segments=12, location=(0, center.y, 0.145))
ring = bpy.context.object
ring.name = "USTUDIO_ACCENT_RING"
for owner in list(ring.users_collection):
    owner.objects.unlink(ring)
environment.objects.link(ring)
ring.data.materials.append(ring_mat)

light_target = create_empty(lighting, "USTUDIO_LIGHT_TARGET", center, "SPHERE", 0.08)
create_area_light(lighting, "USTUDIO_KEY", (2.8, -2.7, 3.4), 850, 2.5, (1.0, 0.78, 0.66), light_target)
create_area_light(lighting, "USTUDIO_FILL", (-2.6, -1.5, 1.9), 520, 3.2, (0.34, 0.66, 1.0), light_target)
create_area_light(lighting, "USTUDIO_RIM", (1.8, 1.8, 2.8), 1100, 2.0, (1.0, 0.12, 0.48), light_target)
create_area_light(lighting, "USTUDIO_TOP", (-0.3, 0.4, 4.0), 480, 2.2, (0.62, 0.75, 1.0), light_target)

target = create_empty(camera_rig, "USTUDIO_CAMERA_TARGET", center, "SPHERE", 0.1)
focus = create_empty(camera_rig, "USTUDIO_FOCUS_TARGET", center, "CUBE", 0.07)
camera_data = bpy.data.cameras.new("USTUDIO_HERO_CAMERA_DATA")
camera_data.lens = 58
camera_data.sensor_width = 36
camera_data.clip_start = 0.01
camera_data.clip_end = 100
camera_data.show_passepartout = True
camera_data.passepartout_alpha = 0.9
camera_data.dof.use_dof = True
camera_data.dof.focus_object = focus
camera_data.dof.aperture_fstop = 2.8
camera = bpy.data.objects.new("USTUDIO_HERO_CAMERA", camera_data)
camera_rig.objects.link(camera)
track = camera.constraints.new("TRACK_TO")
track.name = "USTUDIO_TRACK_TO_DELAYED_TARGET"
track.target = target
track.track_axis = "TRACK_NEGATIVE_Z"
track.up_axis = "UP_Y"
scene.camera = camera

camera_poses = {
    1: (center + Vector((1.14, -1.52, 0.88)), 58.0, 3.2),
    24: (center + Vector((1.26, -1.66, 0.80)), 56.0, 3.0),
    96: (center + Vector((0.48, -1.38, 0.34)), 62.0, 2.2),
    132: (center + Vector((0.62, -1.49, 0.43)), 60.0, 2.8),
    144: (center + Vector((0.62, -1.49, 0.43)), 60.0, 2.8),
}
target_poses = {
    1: center + Vector((0.0, -0.01, 0.02)),
    28: center + Vector((-0.025, -0.01, 0.08)),
    100: center + Vector((0.035, -0.02, 0.16)),
    136: center + Vector((0.0, -0.01, 0.07)),
    144: center + Vector((0.0, -0.01, 0.07)),
}

for frame, (location, lens, fstop) in camera_poses.items():
    camera.location = location
    camera.keyframe_insert(data_path="location", frame=frame, group="DRUMBOII_CAMERA_K1_K4")
    camera_data.lens = lens
    camera_data.keyframe_insert(data_path="lens", frame=frame, group="DRUMBOII_CAMERA_K1_K4")
    camera_data.dof.aperture_fstop = fstop
    camera_data.dof.keyframe_insert(data_path="aperture_fstop", frame=frame, group="DRUMBOII_FOCUS")
    focus.location = target_poses.get(frame, target_poses[min(target_poses, key=lambda f: abs(f - frame))])
    focus.keyframe_insert(data_path="location", frame=frame, group="DRUMBOII_FOCUS")

for frame, location in target_poses.items():
    target.location = location
    target.keyframe_insert(data_path="location", frame=frame, group="DRUMBOII_TARGET_LAG")

for owner in (camera, camera_data, camera_data.dof, target, focus):
    smooth(owner)

for frame, label in CAMERA_KEYS.items():
    scene.timeline_markers.new("USTUDIO_" + label, frame=frame)

scene["ustudio_schema"] = 1
scene["ustudio_recipe"] = "DRUMBOII four-key hero camera"
scene["ustudio_tutorial"] = "knowledge/tutorials/drumboii-camera-tutorial-2026-07-18/analysis.json"
scene["ustudio_asset"] = ASSET_NAME
scene["ustudio_target_lag_frames"] = TARGET_LAG
scene.frame_set(FRAME_START)

manifest = {
    "schema_version": 1,
    "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    "project": str(PROJECT_FILE.relative_to(ROOT)),
    "asset": {
        "name": ASSET_NAME,
        "library": str(ASSET_LIBRARY.relative_to(ROOT)),
        "collection": product_collection.name,
        "objects": [obj.name for obj in mesh_objects],
    },
    "tutorial_source": "knowledge/tutorials/drumboii-camera-tutorial-2026-07-18/analysis.json",
    "technique": {
        "name": "Four-key momentum motif",
        "camera_keys": [{"frame": frame, "label": label} for frame, label in CAMERA_KEYS.items()],
        "target_lag_frames": TARGET_LAG,
        "track_to": track.name,
        "focus_object": focus.name,
        "focus_strategy": "focus object plus keyed f-stop at every camera pose",
    },
    "scene": {
        "name": scene.name,
        "fps": FPS,
        "frame_range": [FRAME_START, FRAME_END],
        "duration_seconds": FRAME_END / FPS,
        "engine": scene.render.engine,
        "camera": camera.name,
        "bounds": {"min": list(minimum), "max": list(maximum), "center": list(center), "radius": radius},
    },
    "outputs": {
        "gate": str(GATE_DIR.relative_to(ROOT)),
        "preview": str(PREVIEW_FILE.relative_to(ROOT)),
    },
    "saved": True,
}
MANIFEST_FILE.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

bpy.ops.wm.save_as_mainfile(filepath=str(PROJECT_FILE), compress=True, relative_remap=True)

scene.render.resolution_x = 720
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
for frame, label in CAMERA_KEYS.items():
    scene.frame_set(frame)
    scene.render.filepath = str(GATE_DIR / f"frame_{frame:04d}_{label.lower()}.png")
    bpy.ops.render.render(write_still=True)

if PREVIEW_FRAMES.exists():
    shutil.rmtree(PREVIEW_FRAMES)
PREVIEW_FRAMES.mkdir(parents=True)
scene.render.resolution_x = 480
scene.render.resolution_y = 480
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(PREVIEW_FRAMES / "frame_")
bpy.ops.render.render(animation=True)

ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
subprocess.run([
    ffmpeg,
    "-hide_banner",
    "-loglevel", "error",
    "-y",
    "-framerate", str(FPS),
    "-i", str(PREVIEW_FRAMES / "frame_%04d.png"),
    "-c:v", "libx264",
    "-preset", "medium",
    "-crf", "20",
    "-pix_fmt", "yuv420p",
    str(PREVIEW_FILE),
], check=True)
shutil.rmtree(PREVIEW_FRAMES)

scene.render.image_settings.file_format = "PNG"
scene.render.resolution_x = 720
scene.render.resolution_y = 720
scene.frame_set(FRAME_START)
bpy.ops.wm.save_as_mainfile(filepath=str(PROJECT_FILE), compress=True, relative_remap=True)
print("UNRECORDED_CAMERA_STUDY=" + json.dumps(manifest, ensure_ascii=False))
