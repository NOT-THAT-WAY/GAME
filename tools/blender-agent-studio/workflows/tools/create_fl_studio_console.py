"""Build a reusable 3D FL Studio console from the supplied visual reference."""

import bpy
import json
import math
from datetime import datetime
from pathlib import Path
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
PROJECT_DIR = ROOT / "projects" / "fl-studio-console-2026-07-19"
SOURCE_DIR = PROJECT_DIR / "source-panels"
SOURCE_REFERENCE_DIR = PROJECT_DIR / "source-reference"
GATE_DIR = PROJECT_DIR / "gate"
PROJECT_FILE = PROJECT_DIR / "FL_Studio_Console_Study.blend"
MANIFEST_FILE = PROJECT_DIR / "scene-manifest.json"


def move_to_collection(obj, collection):
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    collection.objects.link(obj)


def material(name, color, metallic=0.0, roughness=0.4, emission=None, strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission is not None:
        emission_input = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        strength_input = bsdf.inputs.get("Emission Strength")
        if emission_input:
            emission_input.default_value = emission
        if strength_input:
            strength_input.default_value = strength
    return mat


def image_material(name, path):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    image = nodes.new("ShaderNodeTexImage")
    image.name = "USTUDIO_SOURCE_IMAGE"
    image.image = bpy.data.images.load(str(path), check_existing=True)
    image.interpolation = "Linear"
    links.new(image.outputs["Color"], bsdf.inputs["Base Color"])
    emission_input = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
    if emission_input:
        links.new(image.outputs["Color"], emission_input)
    strength_input = bsdf.inputs.get("Emission Strength")
    if strength_input:
        strength_input.default_value = 0.32
    bsdf.inputs["Roughness"].default_value = 0.24
    return mat


def cube(collection, name, location, scale, mat, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(obj, collection)
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new("USTUDIO_BEVEL", "BEVEL")
        mod.width = bevel
        mod.segments = 5
    return obj


def screen(collection, name, path, location, width, height, casing, bevel=0.12):
    back = cube(
        collection,
        name + "_CASING",
        (location[0], location[1] + 0.14, location[2]),
        (width / 2 + 0.10, 0.085, height / 2 + 0.10),
        casing,
        bevel,
    )
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=location, rotation=(math.radians(90), 0, 0))
    panel = bpy.context.object
    panel.name = name
    panel.scale = (width / 2, height / 2, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(panel, collection)
    panel.data.materials.append(image_material("M_" + name, path))
    return back, panel


def empty(collection, name, location, display="PLAIN_AXES", size=0.2):
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    obj.empty_display_type = display
    obj.empty_display_size = size
    collection.objects.link(obj)
    return obj


def track(obj, target):
    con = obj.constraints.new("TRACK_TO")
    con.target = target
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"


def point_light(collection, name, location, energy, radius, color):
    data = bpy.data.lights.new(name + "_DATA", "POINT")
    data.energy = energy
    data.shadow_soft_size = radius
    data.color = color
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    collection.objects.link(obj)
    return obj


PROJECT_DIR.mkdir(parents=True, exist_ok=True)
GATE_DIR.mkdir(parents=True, exist_ok=True)
required = [SOURCE_DIR / name for name in ("browser.png", "playlist.png", "piano-roll.png", "mixer.png", "controller.png")]
missing = [str(path) for path in required if not path.exists()]
if missing:
    raise RuntimeError("Missing source panels: " + ", ".join(missing))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.name = "FL_STUDIO_CONSOLE"
scene.frame_start = 1
scene.frame_end = 240
scene.render.fps = 24
scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.view_settings.look = "AgX - Medium High Contrast"
scene.render.engine = "BLENDER_EEVEE"

world = bpy.data.worlds.new("USTUDIO_FL_WORLD")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.002, 0.004, 0.009, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.055
scene.world = world

structure = bpy.data.collections.new("STRUCTURE_MODULAR")
interface = bpy.data.collections.new("INTERFACE_PANELS")
motion = bpy.data.collections.new("MOTION_CONTROLS")
lighting = bpy.data.collections.new("LIGHTING_ROLES")
camera_rig = bpy.data.collections.new("CAMERA_RIG")
for collection in (structure, interface, motion, lighting, camera_rig):
    scene.collection.children.link(collection)

mat_shell = material("M_SHELL_WARM_GREY", (0.095, 0.085, 0.105, 1), metallic=0.55, roughness=0.28)
mat_inner = material("M_INNER_GRAPHITE", (0.008, 0.012, 0.019, 1), metallic=0.18, roughness=0.36)
mat_glass = material("M_SCREEN_CASING", (0.012, 0.018, 0.025, 1), metallic=0.25, roughness=0.20)
mat_green = material("M_NEON_LIME", (0.10, 0.55, 0.03, 1), roughness=0.16, emission=(0.25, 1.0, 0.08, 1), strength=10.0)
mat_purple = material("M_NEON_PURPLE", (0.34, 0.04, 0.54, 1), roughness=0.16, emission=(0.68, 0.12, 1.0, 1), strength=10.0)
mat_floor = material("M_FLOOR", (0.004, 0.007, 0.012, 1), metallic=0.35, roughness=0.24)

# A real modular enclosure: the source image is never used as the shell.
cube(structure, "USTUDIO_BACK_CAVITY", (0, 0.62, 3.15), (5.28, 0.56, 3.05), mat_inner, 0.42)
cube(structure, "USTUDIO_FRAME_TOP", (0, -0.04, 6.15), (4.72, 0.42, 0.34), mat_shell, 0.28)
cube(structure, "USTUDIO_FRAME_BOTTOM", (0, -0.10, 0.17), (4.72, 0.42, 0.34), mat_shell, 0.28)
cube(structure, "USTUDIO_FRAME_LEFT", (-5.02, -0.02, 3.16), (0.37, 0.46, 2.72), mat_shell, 0.30)
cube(structure, "USTUDIO_FRAME_RIGHT", (5.02, -0.02, 3.16), (0.37, 0.46, 2.72), mat_shell, 0.30)

# Corner caps give the silhouette the soft Y2K luggage/console language of the reference.
for name, x, z in (
    ("TL", -4.68, 5.89), ("TR", 4.68, 5.89), ("BL", -4.68, 0.45), ("BR", 4.68, 0.45)
):
    cube(structure, "USTUDIO_CORNER_" + name, (x, -0.35, z), (0.58, 0.54, 0.58), mat_shell, 0.30)

screen(interface, "USTUDIO_BROWSER", SOURCE_DIR / "browser.png", (-4.02, -0.57, 3.20), 1.28, 4.62, mat_glass, 0.10)
screen(interface, "USTUDIO_PLAYLIST", SOURCE_DIR / "playlist.png", (-0.18, -0.61, 4.88), 5.98, 1.82, mat_glass, 0.12)
screen(interface, "USTUDIO_PIANO_ROLL", SOURCE_DIR / "piano-roll.png", (-0.55, -0.72, 2.31), 6.32, 3.06, mat_glass, 0.14)
screen(interface, "USTUDIO_MIXER", SOURCE_DIR / "mixer.png", (3.83, -0.65, 3.55), 1.76, 3.06, mat_glass, 0.11)

# Floating controller module.
controller_root = empty(motion, "USTUDIO_CONTROLLER_ROOT", (2.22, -1.02, 1.16), "CUBE", 0.3)
controller_back, controller_panel = screen(
    interface, "USTUDIO_CONTROLLER", SOURCE_DIR / "controller.png", (2.22, -1.14, 1.16), 3.48, 0.97, mat_glass, 0.18
)
for obj in (controller_back, controller_panel):
    matrix = obj.matrix_world.copy()
    obj.parent = controller_root
    obj.matrix_world = matrix
for frame, z, angle in ((1, 1.16, -2.0), (60, 1.25, 1.2), (120, 1.18, -0.8), (180, 1.25, 1.0), (240, 1.16, -2.0)):
    controller_root.location.z = z
    controller_root.rotation_euler.y = math.radians(angle)
    controller_root.keyframe_insert("location", frame=frame)
    controller_root.keyframe_insert("rotation_euler", frame=frame)

# Animated UI depth cues: playheads and meters are actual geometry, not baked pixels.
playhead = cube(motion, "USTUDIO_PLAYHEAD_PIANO", (-3.45, -0.84, 2.30), (0.025, 0.025, 1.46), mat_green, 0.018)
playhead.location.x = -3.45
playhead.keyframe_insert("location", frame=1)
playhead.location.x = 2.34
playhead.keyframe_insert("location", frame=240)

playlist_head = cube(motion, "USTUDIO_PLAYHEAD_PLAYLIST", (-3.00, -0.73, 4.88), (0.022, 0.024, 0.80), mat_green, 0.016)
playlist_head.location.x = -3.00
playlist_head.keyframe_insert("location", frame=1)
playlist_head.location.x = 2.60
playlist_head.keyframe_insert("location", frame=240)

for index, x in enumerate((3.36, 3.62, 3.88, 4.14, 4.40)):
    meter = cube(motion, f"USTUDIO_METER_{index+1:02d}", (x, -0.82, 3.12), (0.055, 0.025, 0.24), mat_green, 0.02)
    for frame in (1, 31, 61, 91, 121, 151, 181, 211, 240):
        value = 0.35 + 0.65 * abs(math.sin((frame + index * 17) * 0.071))
        meter.scale.z = value
        meter.keyframe_insert("scale", frame=frame)

cube(structure, "USTUDIO_NEON_LEFT", (-4.63, -0.62, 3.15), (0.055, 0.055, 0.82), mat_purple, 0.045)
cube(structure, "USTUDIO_NEON_RIGHT", (4.63, -0.62, 3.15), (0.055, 0.055, 0.82), mat_purple, 0.045)
cube(structure, "USTUDIO_NEON_STATUS", (0, -0.61, 0.50), (0.72, 0.055, 0.055), mat_green, 0.045)
cube(structure, "USTUDIO_FLOOR", (0, 2.6, -0.24), (8.2, 7.0, 0.18), mat_floor, 0.10)

target = empty(camera_rig, "USTUDIO_CAMERA_TARGET", (0, 0, 3.20), "SPHERE", 0.18)
camera_data = bpy.data.cameras.new("USTUDIO_HERO_CAMERA_DATA")
camera_data.lens = 44
camera_data.sensor_width = 36
camera = bpy.data.objects.new("USTUDIO_HERO_CAMERA", camera_data)
camera_rig.objects.link(camera)
track(camera, target)
scene.camera = camera

# Still -> one continuous push-in -> still.
for frame, location, lens in (
    (1, (0.45, -16.4, 3.78), 47),
    (36, (0.28, -15.8, 3.62), 46),
    (96, (0.08, -15.0, 3.42), 44),
    (168, (-0.08, -14.6, 3.32), 44),
    (240, (0.0, -14.6, 3.32), 44),
):
    camera.location = location
    camera.data.lens = lens
    camera.keyframe_insert("location", frame=frame)
    camera.data.keyframe_insert("lens", frame=frame)

point_light(lighting, "USTUDIO_KEY_SOFTBOX", (-3.8, -5.0, 7.4), 1200, 3.0, (0.60, 0.72, 1.0))
point_light(lighting, "USTUDIO_FILL_SOFTBOX", (4.4, -4.0, 4.8), 800, 2.5, (1.0, 0.38, 0.55))
point_light(lighting, "USTUDIO_NEON_BOUNCE", (0, -2.0, 0.6), 520, 1.8, (0.38, 1.0, 0.12))

scene["ustudio_project"] = "fl-studio-console-2026-07-19"
scene["ustudio_reference_video"] = str(SOURCE_REFERENCE_DIR / "output.mp4")
scene["ustudio_motion_reference"] = str(SOURCE_REFERENCE_DIR / "output-2.mp4")
scene["ustudio_design_rule"] = "separate real geometry from independently replaceable interface panels"
scene.frame_set(120)
bpy.ops.wm.save_as_mainfile(filepath=str(PROJECT_FILE))

for frame in (1, 60, 120, 180, 240):
    scene.frame_set(frame)
    scene.render.filepath = str(GATE_DIR / f"frame_{frame:04d}.png")
    bpy.ops.render.render(write_still=True)

manifest = {
    "project": "FL Studio Console Study",
    "created_at": datetime.now().astimezone().isoformat(),
    "blend": str(PROJECT_FILE.relative_to(ROOT)),
    "references": [str(path.relative_to(ROOT)) for path in sorted(SOURCE_REFERENCE_DIR.iterdir())],
    "editable_modules": ["shell", "browser", "playlist", "piano_roll", "mixer", "controller", "playheads", "meters", "lighting", "camera"],
    "animation": {"frames": [1, 240], "fps": 24, "duration_seconds": 10},
    "gate_frames": [1, 60, 120, 180, 240],
    "source_strategy": "cropped FL Studio reference panels on real modular geometry; no recursive projection of the final render",
}
MANIFEST_FILE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps(manifest))
