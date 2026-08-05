"""Build the FL Studio reference as a deep open box whose interior is the DAW."""

import bpy
import json
import math
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROJECT_DIR = ROOT / "projects" / "fl-studio-console-2026-07-19"
CLIP_DIR = PROJECT_DIR / "source-panel-clips"
GATE_DIR = PROJECT_DIR / "gate-v2-box"
PROJECT_FILE = PROJECT_DIR / "FL_Studio_Box_V2.blend"
MANIFEST_FILE = PROJECT_DIR / "box-v2-manifest.json"


def move_to_collection(obj, collection):
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    collection.objects.link(obj)


def mat(name, color, metallic=0.0, roughness=0.4, emission=None, strength=0.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission is not None:
        emission_input = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        if emission_input:
            emission_input.default_value = emission
        if bsdf.inputs.get("Emission Strength"):
            bsdf.inputs["Emission Strength"].default_value = strength
    return material


def movie_mat(name, path):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    texture = nodes.new("ShaderNodeTexImage")
    texture.name = "USTUDIO_FL_STUDIO_MOVIE"
    texture.image = bpy.data.images.load(str(path), check_existing=True)
    texture.image.source = "MOVIE"
    texture.image_user.frame_duration = 36
    texture.image_user.frame_start = 1
    texture.image_user.use_cyclic = True
    texture.image_user.use_auto_refresh = True
    links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
    emission_input = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
    if emission_input:
        links.new(texture.outputs["Color"], emission_input)
    if bsdf.inputs.get("Emission Strength"):
        bsdf.inputs["Emission Strength"].default_value = 0.22
    bsdf.inputs["Roughness"].default_value = 0.32
    return material


def cube(collection, name, location, scale, material, bevel=0.0, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(obj, collection)
    obj.data.materials.append(material)
    if bevel:
        modifier = obj.modifiers.new("USTUDIO_BEVEL", "BEVEL")
        modifier.width = bevel
        modifier.segments = 6
    return obj


def quad(collection, name, vertices, material):
    mesh = bpy.data.meshes.new(name + "_MESH")
    mesh.from_pydata(vertices, [], [(0, 1, 2, 3)])
    mesh.update()
    uv_layer = mesh.uv_layers.new(name="UVMap")
    uvs = ((0, 0), (1, 0), (1, 1), (0, 1))
    for loop, uv in zip(mesh.polygons[0].loop_indices, uvs):
        uv_layer.data[loop].uv = uv
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def empty(collection, name, location, display="PLAIN_AXES", size=0.2):
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    obj.empty_display_type = display
    obj.empty_display_size = size
    collection.objects.link(obj)
    return obj


def point_light(collection, name, location, energy, radius, color):
    data = bpy.data.lights.new(name + "_DATA", "POINT")
    data.energy = energy
    data.shadow_soft_size = radius
    data.color = color
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    collection.objects.link(obj)
    return obj


def track(obj, target):
    constraint = obj.constraints.new("TRACK_TO")
    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"


PROJECT_DIR.mkdir(parents=True, exist_ok=True)
GATE_DIR.mkdir(parents=True, exist_ok=True)
clip_names = ("browser.mp4", "playlist.mp4", "piano-roll.mp4", "mixer.mp4", "controller.mp4")
for clip_name in clip_names:
    if not (CLIP_DIR / clip_name).exists():
        raise RuntimeError(f"Missing panel clip: {clip_name}")

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.name = "FL_STUDIO_INSIDE_THE_BOX"
scene.frame_start = 1
scene.frame_end = 240
scene.render.fps = 24
scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.engine = "BLENDER_EEVEE"
scene.view_settings.look = "AgX - Medium High Contrast"

world = bpy.data.worlds.new("USTUDIO_BOX_WORLD")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.0015, 0.0025, 0.005, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.035
scene.world = world

shell = bpy.data.collections.new("BOX_SHELL")
interior = bpy.data.collections.new("FL_STUDIO_INTERIOR")
motion = bpy.data.collections.new("PLAYBACK_MOTION")
lights = bpy.data.collections.new("LIGHTING")
camera_rig = bpy.data.collections.new("CAMERA_RIG")
for collection in (shell, interior, motion, lights, camera_rig):
    scene.collection.children.link(collection)

shell_mat = mat("M_BOX_WARM_GREY", (0.10, 0.085, 0.105, 1), metallic=0.42, roughness=0.33)
liner_mat = mat("M_BOX_DARK_LINER", (0.006, 0.008, 0.012, 1), metallic=0.08, roughness=0.48)
screen_frame_mat = mat("M_SCREEN_FRAME", (0.012, 0.016, 0.021, 1), metallic=0.20, roughness=0.28)
floor_mat = mat("M_STAGE_FLOOR", (0.003, 0.005, 0.008, 1), metallic=0.26, roughness=0.30)
green = mat("M_PLAYBACK_GREEN", (0.12, 0.55, 0.02, 1), roughness=0.12, emission=(0.28, 1.0, 0.07, 1), strength=12)
purple = mat("M_SIDE_PURPLE", (0.36, 0.03, 0.58, 1), roughness=0.15, emission=(0.72, 0.10, 1.0, 1), strength=10)

# The shell is a deep open container. The front rim and depth rails are deliberately separate.
cube(shell, "USTUDIO_FRONT_TOP_RIM", (0, -0.72, 5.72), (4.55, 0.36, 0.34), shell_mat, 0.28)
cube(shell, "USTUDIO_FRONT_BOTTOM_RIM", (0, -0.72, 0.42), (4.55, 0.36, 0.34), shell_mat, 0.28)
cube(shell, "USTUDIO_FRONT_LEFT_RIM", (-4.50, -0.72, 3.07), (0.36, 0.36, 2.36), shell_mat, 0.28)
cube(shell, "USTUDIO_FRONT_RIGHT_RIM", (4.50, -0.72, 3.07), (0.36, 0.36, 2.36), shell_mat, 0.28)

for name, x, z in (("TL", -4.30, 5.52), ("TR", 4.30, 5.52), ("BL", -4.30, 0.62), ("BR", 4.30, 0.62)):
    cube(shell, "USTUDIO_FRONT_CORNER_" + name, (x, -0.78, z), (0.55, 0.47, 0.55), shell_mat, 0.30)

# Rails and dark ceiling make the depth visible even without the interface texture.
cube(shell, "USTUDIO_LEFT_DEPTH_TOP", (-4.34, 0.38, 5.43), (0.30, 1.15, 0.28), shell_mat, 0.22)
cube(shell, "USTUDIO_RIGHT_DEPTH_TOP", (4.34, 0.38, 5.43), (0.30, 1.15, 0.28), shell_mat, 0.22)
cube(shell, "USTUDIO_LEFT_DEPTH_BOTTOM", (-4.34, 0.32, 0.72), (0.30, 1.10, 0.28), shell_mat, 0.22)
cube(shell, "USTUDIO_RIGHT_DEPTH_BOTTOM", (4.34, 0.32, 0.72), (0.30, 1.10, 0.28), shell_mat, 0.22)
cube(shell, "USTUDIO_CEILING", (0, 0.42, 5.30), (4.05, 1.15, 0.18), liner_mat, 0.18)
cube(shell, "USTUDIO_BACK_WALL", (0, 1.58, 3.15), (3.50, 0.18, 2.20), liner_mat, 0.22)

# FL Studio is the room: back wall, side walls and sloped floor/pupitre.
playlist = quad(
    interior,
    "USTUDIO_PLAYLIST_BACK_WALL",
    [(-3.02, 1.36, 2.96), (3.02, 1.36, 2.96), (3.02, 1.36, 4.86), (-3.02, 1.36, 4.86)],
    movie_mat("M_MOVIE_PLAYLIST", CLIP_DIR / "playlist.mp4"),
)
browser = quad(
    interior,
    "USTUDIO_BROWSER_LEFT_WALL",
    [(-4.08, -0.36, 1.05), (-3.16, 1.28, 2.55), (-3.16, 1.28, 5.02), (-4.08, -0.36, 5.05)],
    movie_mat("M_MOVIE_BROWSER", CLIP_DIR / "browser.mp4"),
)
mixer = quad(
    interior,
    "USTUDIO_MIXER_RIGHT_WALL",
    [(3.16, 1.28, 2.55), (4.08, -0.36, 1.05), (4.08, -0.36, 5.05), (3.16, 1.28, 5.02)],
    movie_mat("M_MOVIE_MIXER", CLIP_DIR / "mixer.mp4"),
)
piano = quad(
    interior,
    "USTUDIO_PIANO_ROLL_FLOOR",
    [(-3.78, -0.42, 0.88), (3.78, -0.42, 0.88), (3.05, 1.25, 2.63), (-3.05, 1.25, 2.63)],
    movie_mat("M_MOVIE_PIANO_ROLL", CLIP_DIR / "piano-roll.mp4"),
)

# Thin dark boundaries make each plane feel integrated into the same cavity.
cube(shell, "USTUDIO_BACK_SCREEN_TOP", (0, 1.30, 5.02), (3.25, 0.08, 0.10), screen_frame_mat, 0.06)
cube(shell, "USTUDIO_BACK_SCREEN_BOTTOM", (0, 1.30, 2.83), (3.25, 0.08, 0.10), screen_frame_mat, 0.06)

# Front floating channel rack, a physical control deck inside the box.
controller_root = empty(motion, "USTUDIO_CHANNEL_RACK_ROOT", (2.05, -0.94, 1.25), "CUBE", 0.24)
controller_case = cube(interior, "USTUDIO_CHANNEL_RACK_CASE", (2.05, -0.82, 1.25), (1.78, 0.12, 0.52), screen_frame_mat, 0.18, (0, 0, math.radians(-2)))
controller = quad(
    interior,
    "USTUDIO_CHANNEL_RACK_SURFACE",
    [(0.38, -1.08, 0.83), (3.72, -1.08, 0.83), (3.72, -1.08, 1.67), (0.38, -1.08, 1.67)],
    movie_mat("M_MOVIE_CHANNEL_RACK", CLIP_DIR / "controller.mp4"),
)
for obj in (controller_case, controller):
    matrix = obj.matrix_world.copy()
    obj.parent = controller_root
    obj.matrix_world = matrix

# Real playback indicators bridge the rear wall and the sloped floor.
back_playhead = cube(motion, "USTUDIO_PLAYHEAD_BACK", (-2.78, 1.24, 3.91), (0.026, 0.028, 0.88), green, 0.018)
floor_playhead = cube(motion, "USTUDIO_PLAYHEAD_FLOOR", (-3.45, 0.34, 1.68), (0.026, 1.22, 0.022), green, 0.018, (math.radians(46.4), 0, 0))
for obj, start_x, end_x in ((back_playhead, -2.78, 2.78), (floor_playhead, -3.45, 3.02)):
    obj.location.x = start_x
    obj.keyframe_insert("location", frame=1)
    obj.location.x = end_x
    obj.keyframe_insert("location", frame=240)

# Minimal front lighting signatures from the reference.
cube(shell, "USTUDIO_LEFT_PURPLE_LED", (-4.52, -1.10, 2.90), (0.045, 0.055, 0.72), purple, 0.04)
cube(shell, "USTUDIO_RIGHT_PURPLE_LED", (4.52, -1.10, 2.90), (0.045, 0.055, 0.72), purple, 0.04)
cube(shell, "USTUDIO_BOTTOM_GREEN_LED", (0, -1.10, 0.40), (0.72, 0.055, 0.055), green, 0.04)
cube(shell, "USTUDIO_GROUND", (0, 3.0, -0.16), (8, 7, 0.16), floor_mat, 0.10)

target = empty(camera_rig, "USTUDIO_BOX_TARGET", (0, 0.25, 3.02), "SPHERE", 0.16)
camera_data = bpy.data.cameras.new("USTUDIO_BOX_CAMERA_DATA")
camera_data.lens = 53
camera_data.sensor_width = 36
camera = bpy.data.objects.new("USTUDIO_BOX_CAMERA", camera_data)
camera.location = (0, -15.8, 3.92)
camera_rig.objects.link(camera)
track(camera, target)
scene.camera = camera

# The box is the background, so the camera remains essentially locked.
for frame, x, z in ((1, 0.0, 3.92), (120, -0.04, 3.90), (240, 0.0, 3.92)):
    camera.location.x = x
    camera.location.z = z
    camera.keyframe_insert("location", frame=frame)

point_light(lights, "USTUDIO_FRONT_KEY", (-3.8, -5.0, 7.0), 980, 3.0, (0.55, 0.68, 1.0))
point_light(lights, "USTUDIO_FRONT_FILL", (4.0, -4.2, 4.7), 650, 2.6, (1.0, 0.30, 0.48))
point_light(lights, "USTUDIO_GREEN_BOUNCE", (0, -1.8, 0.55), 410, 1.6, (0.25, 1.0, 0.08))
point_light(lights, "USTUDIO_INTERIOR_FILL", (0, 0.55, 4.9), 240, 1.8, (0.26, 0.38, 0.55))

scene["ustudio_project"] = "fl-studio-box-v2"
scene["ustudio_concept"] = "one deep box whose inner walls are FL Studio"
scene["ustudio_reference_analysis"] = "reference-analysis/output-1/contact-4fps.jpg"
scene["ustudio_v1_status"] = "rejected: front collage without room depth"
scene.frame_set(120)
bpy.ops.wm.save_as_mainfile(filepath=str(PROJECT_FILE))

for frame in (1, 60, 120, 180, 240):
    scene.frame_set(frame)
    scene.render.filepath = str(GATE_DIR / f"frame_{frame:04d}.png")
    bpy.ops.render.render(write_still=True)

manifest = {
    "project": "FL Studio Inside The Box V2",
    "created_at": datetime.now().astimezone().isoformat(),
    "blend": str(PROJECT_FILE.relative_to(ROOT)),
    "concept": "single deep open box containing FL Studio across its interior architecture",
    "surface_mapping": {
        "back_wall": "playlist",
        "left_wall": "browser",
        "right_wall": "mixer",
        "sloped_floor": "piano_roll",
        "floating_front_module": "channel_rack",
    },
    "motion": ["looped source panel clips", "back playhead", "floor playhead", "subtle locked-camera drift"],
    "animation": {"frames": [1, 240], "fps": 24, "duration_seconds": 10},
    "gate_frames": [1, 60, 120, 180, 240],
}
MANIFEST_FILE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps(manifest))
