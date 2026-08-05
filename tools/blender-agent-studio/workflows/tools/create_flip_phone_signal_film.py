"""Build the original 30-second LAST SIGNAL product film from the unused Flip Phone asset."""
import bpy
import math
import json
import sys
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "projects" / "flip-phone-signal-film"
LIBRARY = ROOT / "asset_library" / "imported" / "drumboii-y2k-assets.blend"
BLEND = PROJECT / "Flip_Phone_Last_Signal.blend"
PROJECT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.name = "LAST_SIGNAL_MASTER"
scene.frame_start = 1
scene.frame_end = 720
scene.render.fps = 24
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 960
scene.render.resolution_y = 540
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = 0.35
scene.world = bpy.data.worlds.new("LAST_SIGNAL_WORLD")
scene.world.use_nodes = True
world_bg = scene.world.node_tree.nodes.get("Background")
world_bg.inputs["Color"].default_value = (0.0015, 0.003, 0.012, 1)
world_bg.inputs["Strength"].default_value = 0.12


def collection(name, parent=None):
    item = bpy.data.collections.new(name)
    (parent or scene.collection).children.link(item)
    return item


source_col = collection("SOURCE_ASSET_FLIP_PHONE")
work_col = collection("WORK_ASSET_FLIP_PHONE")
env_col = collection("ENVIRONMENT_LAST_SIGNAL")
lights_col = collection("LIGHTS_LAST_SIGNAL")
rig_col = collection("RIG_LAST_SIGNAL")
fx_col = collection("FX_LAST_SIGNAL")

with bpy.data.libraries.load(str(LIBRARY), link=False) as (data_from, data_to):
    if "DRUMBOII_FLIP_PHONE" not in data_from.collections:
        raise RuntimeError("DRUMBOII_FLIP_PHONE absent de la bibliothèque")
    data_to.collections = ["DRUMBOII_FLIP_PHONE"]
imported = bpy.data.collections["DRUMBOII_FLIP_PHONE"]
for obj in list(imported.objects):
    imported.objects.unlink(obj)
    source_col.objects.link(obj)
source_col.hide_render = True
source_col.hide_viewport = True
bpy.data.collections.remove(imported)

mapping = {}
for original in source_col.all_objects:
    duplicate = original.copy()
    if original.data:
        duplicate.data = original.data.copy()
    duplicate.animation_data_clear()
    duplicate.name = "LS_" + original.name
    work_col.objects.link(duplicate)
    mapping[original] = duplicate
for original, duplicate in mapping.items():
    duplicate.parent = mapping.get(original.parent)
    duplicate.matrix_parent_inverse = original.matrix_parent_inverse.copy()


def principled_material(name, color, metallic=0.0, roughness=0.35, emission=None, emission_strength=0.0, noise=False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 0.28
        bsdf.inputs["Coat Roughness"].default_value = 0.16
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    if noise:
        tex = nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = 34
        tex.inputs["Detail"].default_value = 5
        tex.inputs["Roughness"].default_value = 0.62
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.09
        bump.inputs["Distance"].default_value = 0.035
        links.new(tex.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def action_fcurves(action):
    curves = list(getattr(action, "fcurves", []))
    if curves:
        return curves
    for layer in getattr(action, "layers", []):
        for strip in getattr(layer, "strips", []):
            for channelbag in getattr(strip, "channelbags", []):
                curves.extend(channelbag.fcurves)
    return curves


shell_mat = principled_material("LS_MAT_PHONE_COBALT", (0.018, 0.055, 0.19), metallic=0.62, roughness=0.16, noise=True)
button_mat = principled_material("LS_MAT_BUTTON_PEARL", (0.68, 0.14, 0.42), metallic=0.25, roughness=0.22)
text_mat = principled_material("LS_MAT_TEXT_CYAN", (0.12, 0.8, 1.0), metallic=0.1, roughness=0.25, emission=(0.02, 0.55, 1.0), emission_strength=1.8)
metal_mat = principled_material("LS_MAT_HINGE_METAL", (0.16, 0.2, 0.28), metallic=0.92, roughness=0.11)
screen_mat = principled_material("LS_MAT_SCREEN_SIGNAL", (0.001, 0.004, 0.012), metallic=0.05, roughness=0.1, emission=(0.03, 0.75, 1.0), emission_strength=0.0)
floor_mat = principled_material("LS_MAT_FLOOR", (0.004, 0.006, 0.012), metallic=0.7, roughness=0.18, noise=True)
dark_mat = principled_material("LS_MAT_STRUCTURE", (0.012, 0.018, 0.04), metallic=0.5, roughness=0.28)
cyan_mat = principled_material("LS_MAT_CYAN_EMISSION", (0.01, 0.2, 0.32), roughness=0.22, emission=(0.0, 0.75, 1.0), emission_strength=7.0)
pink_mat = principled_material("LS_MAT_PINK_EMISSION", (0.32, 0.015, 0.16), roughness=0.22, emission=(1.0, 0.02, 0.35), emission_strength=7.0)
white_mat = principled_material("LS_MAT_WHITE_EMISSION", (0.25, 0.3, 0.38), roughness=0.2, emission=(0.7, 0.9, 1.0), emission_strength=5.0)

for obj in mapping.values():
    if obj.type != "MESH":
        continue
    lower = obj.name.lower()
    obj.data.materials.clear()
    if "screen2" in lower:
        obj.data.materials.append(screen_mat)
    elif any(token in lower for token in ("123", "456", "789", "abc", "def", "ghi", "jkl", "mno", "pqr", "stu", "vw", "xyz", "!!", "??", "%%")):
        obj.data.materials.append(text_mat)
    elif any(token in lower for token in ("button", "circle")):
        obj.data.materials.append(button_mat)
    elif any(token in lower for token in ("hinge", "screw")):
        obj.data.materials.append(metal_mat)
    else:
        obj.data.materials.append(shell_mat)


def empty(name, location=(0, 0, 0), parent=None):
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = 0.45
    rig_col.objects.link(obj)
    obj.parent = parent
    return obj


root_ctrl = empty("LS_PRODUCT_ROOT", (-8, 0, 2.0))
root_ctrl.scale = (2.25, 2.25, 2.25)
phone = mapping[next(obj for obj in source_col.all_objects if obj.name == "Phone")]
phone.parent = root_ctrl
phone.matrix_parent_inverse.identity()
target = empty("LS_CAMERA_TARGET", (0, -0.05, -0.12), root_ctrl)
focus = empty("LS_CAMERA_FOCUS", (0, -0.2, -0.12), root_ctrl)


def cube(name, location, scale, mat, col=env_col, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    col.objects.link(obj)
    obj.data.materials.append(mat)
    if bevel:
        modifier = obj.modifiers.new("LS_BEVEL", "BEVEL")
        modifier.width = bevel
        modifier.segments = 3
    return obj


def cylinder(name, location, radius, depth, mat, vertices=48, rotation=(0, 0, 0), col=env_col):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    col.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def torus(name, location, major, minor, mat, rotation=(math.pi / 2, 0, 0), col=fx_col):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=64, minor_segments=10, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    col.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


# Continuous world: assembly bay -> conveyor -> activation dais -> signal city.
cube("LS_GROUND", (1, 0, -0.35), (18, 9, 0.35), floor_mat, bevel=0.15)
cube("LS_CONVEYOR", (-3.2, 0, 0.15), (7.2, 1.65, 0.18), dark_mat, bevel=0.16)
for index in range(30):
    x = -10.0 + index * 0.47
    slat = cube(f"LS_BELT_SLAT_{index:02d}", (x, 0, 0.38), (0.19, 1.52, 0.055), dark_mat, bevel=0.025)
    strip = cube(f"LS_BELT_LIGHT_{index:02d}", (x, -1.48, 0.46), (0.13, 0.025, 0.018), cyan_mat if index % 2 == 0 else pink_mat, bevel=0.01)

# Assembly portal.
for x in (-9.5, -6.5):
    cube(f"LS_ASSEMBLY_PILLAR_L_{x}", (x, -2.5, 2.8), (0.16, 0.2, 3.15), cyan_mat, bevel=0.08)
    cube(f"LS_ASSEMBLY_PILLAR_R_{x}", (x, 2.5, 2.8), (0.16, 0.2, 3.15), pink_mat, bevel=0.08)
    cube(f"LS_ASSEMBLY_TOP_{x}", (x, 0, 5.85), (0.16, 2.7, 0.16), white_mat, bevel=0.08)

# Activation dais and concentric hardware.
cylinder("LS_DAIS_BASE", (4.2, 0, 0.28), 2.55, 0.55, dark_mat, vertices=96)
cylinder("LS_DAIS_RING", (4.2, 0, 0.59), 2.1, 0.08, cyan_mat, vertices=96)
cylinder("LS_DAIS_CORE", (4.2, 0, 0.7), 1.45, 0.18, dark_mat, vertices=96)

# Signal city: restrained masses around a negative corridor.
city_blocks = [
    (1.0, 4.8, 2.0, 1.0), (3.0, 5.4, 3.5, 0.8), (6.0, 5.0, 4.7, 0.9), (8.5, 4.5, 3.0, 1.0),
    (1.5, -8.2, 3.3, 0.9), (4.8, -8.5, 4.2, 1.0), (7.7, -8.2, 2.5, 0.8), (10.0, -7.8, 5.0, 1.0),
]
for index, (x, y, height, width) in enumerate(city_blocks):
    cube(f"LS_CITY_BLOCK_{index:02d}", (x, y, height / 2 - 0.1), (width, 0.8, height / 2), dark_mat, bevel=0.12)
    accent = cyan_mat if index % 2 == 0 else pink_mat
    cube(f"LS_CITY_STRIP_{index:02d}", (x, y - math.copysign(0.82, y), height * 0.65), (width * 0.72, 0.025, 0.045), accent, bevel=0.015)

for index, radius in enumerate((2.9, 4.2, 5.6)):
    ring = torus(f"LS_SIGNAL_RING_{index}", (4.2, 0.25, 2.9), radius, 0.035, cyan_mat if index % 2 == 0 else pink_mat)
    ring.scale = (0.01, 0.01, 0.01)
    ring.keyframe_insert("scale", frame=390 + index * 18)
    ring.scale = (1, 1, 1)
    ring.keyframe_insert("scale", frame=470 + index * 22)

for index in range(26):
    angle = 2 * math.pi * index / 26
    radius = 3.4 + (index % 4) * 0.55
    orb = cylinder(f"LS_SIGNAL_ORB_{index:02d}", (4.2 + math.cos(angle) * radius, math.sin(angle) * radius, 1.2 + (index % 5) * 0.45), 0.055, 0.1, cyan_mat if index % 2 == 0 else pink_mat, vertices=16, rotation=(math.pi / 2, 0, 0), col=fx_col)
    orb.scale = (0.01, 0.01, 0.01)
    orb.keyframe_insert("scale", frame=410 + index * 3)
    orb.scale = (1, 1, 1)
    orb.keyframe_insert("scale", frame=460 + index * 3)


def area_light(name, location, energy, size, color, target_obj=target):
    data = bpy.data.lights.new(name + "_DATA", "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    lights_col.objects.link(obj)
    track = obj.constraints.new("TRACK_TO")
    track.target = target_obj
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"
    return obj


area_light("LS_KEY", (-3, -8, 8), 1150, 5.0, (0.65, 0.82, 1.0))
area_light("LS_FILL", (3, 6, 5), 700, 4.5, (1.0, 0.2, 0.48))
area_light("LS_TOP", (2, 0, 10), 950, 3.5, (0.55, 0.72, 1.0))
area_light("LS_CITY_RIM", (10, -3, 7), 1300, 4.0, (0.1, 0.85, 1.0))


def key_value(owner, path, frame, value, index=None, interpolation="BEZIER"):
    if index is None:
        setattr(owner, path, value)
    else:
        getattr(owner, path)[index] = value
    owner.keyframe_insert(path, frame=frame, index=index if index is not None else -1)
    action = owner.animation_data.action if owner.animation_data else None
    if action:
        for curve in getattr(action, "fcurves", []):
            for point in curve.keyframe_points:
                point.interpolation = interpolation
                if interpolation == "BEZIER":
                    point.handle_left_type = "AUTO_CLAMPED"
                    point.handle_right_type = "AUTO_CLAMPED"


# Assembly reveal: final transforms are the source of truth; pieces converge in staggered groups.
reveal_names = ["Buttons", "Hinge", "Screen.001", "Screws2", "Screws3"]
offsets = [(-2.4, -0.8, 0.2), (2.1, 0.5, 1.4), (0.4, 1.5, 2.3), (-1.6, 0.2, -1.4), (1.6, 0.2, -1.4)]
for index, (name, offset) in enumerate(zip(reveal_names, offsets)):
    obj = mapping[next(original for original in source_col.all_objects if original.name == name)]
    final = obj.location.copy()
    start = final + Vector(offset)
    obj.location = start
    obj.scale = (0.4, 0.4, 0.4)
    obj.keyframe_insert("location", frame=1 + index * 5)
    obj.keyframe_insert("scale", frame=1 + index * 5)
    obj.location = final
    obj.scale = (1, 1, 1)
    obj.keyframe_insert("location", frame=104 + index * 7)
    obj.keyframe_insert("scale", frame=104 + index * 7)

# Product motion: still -> linear conveyor -> eased activation -> levitating hero.
root_ctrl.location = (-8, 0, 2.0)
root_ctrl.keyframe_insert("location", frame=1)
root_ctrl.keyframe_insert("location", frame=132)
root_ctrl.location = (0.2, 0, 2.0)
root_ctrl.keyframe_insert("location", frame=286)
root_ctrl.location = (4.2, 0, 2.15)
root_ctrl.keyframe_insert("location", frame=342)
root_ctrl.keyframe_insert("location", frame=432)
root_ctrl.location = (4.2, 0, 2.8)
root_ctrl.rotation_euler = (math.radians(-3), math.radians(2), math.radians(-10))
root_ctrl.keyframe_insert("location", frame=540)
root_ctrl.keyframe_insert("rotation_euler", frame=540)
root_ctrl.location = (4.2, 0, 3.05)
root_ctrl.rotation_euler = (math.radians(2), math.radians(-2), math.radians(8))
root_ctrl.keyframe_insert("location", frame=650)
root_ctrl.keyframe_insert("rotation_euler", frame=650)
root_ctrl.location = (4.2, 0, 2.95)
root_ctrl.rotation_euler = (0, 0, 0)
root_ctrl.keyframe_insert("location", frame=700)
root_ctrl.keyframe_insert("rotation_euler", frame=700)
root_ctrl.keyframe_insert("location", frame=720)
root_ctrl.keyframe_insert("rotation_euler", frame=720)
if root_ctrl.animation_data and root_ctrl.animation_data.action:
    for curve in action_fcurves(root_ctrl.animation_data.action):
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR" if 132 <= point.co.x <= 286 else "BEZIER"
            if point.interpolation == "BEZIER":
                point.handle_left_type = "AUTO_CLAMPED"
                point.handle_right_type = "AUTO_CLAMPED"

# The attention target reacts after arrival: keypad -> hinge/screen -> whole product.
target.location = (0, -0.05, -0.12)
target.keyframe_insert("location", frame=288)
target.location = (0, -0.05, 0.48)
target.keyframe_insert("location", frame=374)
target.location = (0, -0.05, 0.24)
target.keyframe_insert("location", frame=432)
target.location = (0, -0.05, -0.12)
target.keyframe_insert("location", frame=540)
focus.location = (0, -0.2, -0.12)
focus.keyframe_insert("location", frame=288)
focus.location = (0, -0.2, 0.42)
focus.keyframe_insert("location", frame=386)
focus.location = (0, -0.2, -0.12)
focus.keyframe_insert("location", frame=540)

# Mechanical hinge choreography and screen ignition.
hinge = mapping[next(obj for obj in source_col.all_objects if obj.name == "Hinge")]
hinge_base = hinge.rotation_euler.copy()
hinge.rotation_euler.x = hinge_base.x - math.radians(92)
hinge.keyframe_insert("rotation_euler", frame=1)
hinge.keyframe_insert("rotation_euler", frame=286)
hinge.rotation_euler.x = hinge_base.x - math.radians(102)
hinge.keyframe_insert("rotation_euler", frame=318)
hinge.rotation_euler.x = hinge_base.x
hinge.keyframe_insert("rotation_euler", frame=388)
hinge.rotation_euler.x = hinge_base.x - math.radians(4)
hinge.keyframe_insert("rotation_euler", frame=420)
for curve in action_fcurves(hinge.animation_data.action):
    for point in curve.keyframe_points:
        point.interpolation = "BEZIER"
        point.handle_left_type = "AUTO_CLAMPED"
        point.handle_right_type = "AUTO_CLAMPED"

screen_bsdf = screen_mat.node_tree.nodes.get("Principled BSDF")
screen_bsdf.inputs["Emission Strength"].default_value = 0.0
screen_bsdf.inputs["Emission Strength"].keyframe_insert("default_value", frame=1)
screen_bsdf.inputs["Emission Strength"].keyframe_insert("default_value", frame=350)
screen_bsdf.inputs["Emission Strength"].default_value = 8.0
screen_bsdf.inputs["Emission Strength"].keyframe_insert("default_value", frame=398)
screen_bsdf.inputs["Emission Strength"].default_value = 3.5
screen_bsdf.inputs["Emission Strength"].keyframe_insert("default_value", frame=720)


def camera(name, location, lens, start, end, positions):
    data = bpy.data.cameras.new(name + "_DATA")
    data.lens = lens
    data.dof.use_dof = True
    data.dof.focus_object = focus
    data.dof.aperture_fstop = 3.2
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    rig_col.objects.link(obj)
    track = obj.constraints.new("TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"
    for frame, position, focal in positions:
        obj.location = position
        data.lens = focal
        obj.keyframe_insert("location", frame=frame)
        data.keyframe_insert("lens", frame=frame)
    for owner in (obj, data):
        action = owner.animation_data.action if owner.animation_data else None
        if action:
            for curve in action_fcurves(action):
                for point in curve.keyframe_points:
                    point.interpolation = "BEZIER"
                    point.handle_left_type = "AUTO_CLAMPED"
                    point.handle_right_type = "AUTO_CLAMPED"
    marker = scene.timeline_markers.new("LS_CAM_" + name, frame=start)
    marker.camera = obj
    return obj


cam_a = camera("LS_CAM_ASSEMBLY", (-8, -11, 4.2), 58, 1, 144, [
    (1, (-8.8, -12.5, 4.0), 62), (24, (-9.1, -12.8, 4.1), 64),
    (106, (-7.4, -10.1, 3.5), 56), (144, (-7.8, -10.8, 3.7), 60),
])
cam_b = camera("LS_CAM_CONVEYOR", (-6, -9, 3.2), 48, 145, 288, [
    (145, (-7.5, -9.5, 3.0), 50), (176, (-7.8, -9.8, 3.0), 52),
    (250, (-0.8, -8.2, 2.8), 58), (288, (0.2, -8.8, 3.0), 62),
])
cam_c = camera("LS_CAM_ACTIVATION", (4.2, -8.4, 3.2), 66, 289, 432, [
    (289, (2.0, -9.2, 3.2), 58), (318, (2.3, -9.4, 3.3), 60),
    (388, (4.2, -6.6, 3.2), 72), (432, (4.5, -7.1, 3.6), 68),
])
cam_d = camera("LS_CAM_SIGNAL_CITY", (0, -12, 6), 52, 433, 600, [
    (433, (1.0, -11.8, 5.0), 52), (470, (0.4, -12.2, 5.4), 54),
    (552, (9.6, -9.6, 7.0), 66), (600, (7.5, -10.4, 6.2), 62),
])
cam_e = camera("LS_CAM_HERO", (-2.0, -8.0, 4.6), 60, 601, 720, [
    (601, (0.0, -9.0, 5.3), 58), (626, (-0.4, -9.3, 5.4), 60),
    (682, (-1.8, -8.0, 4.5), 62), (704, (-1.2, -8.6, 4.3), 60), (720, (-1.2, -8.6, 4.3), 60),
])
scene.camera = cam_a

for frame, name in [(1, "S0_DORMANT"), (24, "S1_ANTICIPATION"), (120, "S2_ASSEMBLED"), (145, "S3_TRANSPORT"), (288, "S4_ARRIVAL"), (388, "S5_OPEN"), (432, "S6_SIGNAL"), (600, "S7_WORLD_ON"), (704, "S8_HERO_REST"), (720, "S9_STILL")]:
    scene.timeline_markers.new("LS_" + name, frame=frame)

manifest = {
    "schema_version": 1,
    "title": "LAST SIGNAL",
    "source_asset": "DRUMBOII_FLIP_PHONE",
    "source_library": str(LIBRARY.relative_to(ROOT)),
    "duration_seconds": 30,
    "fps": 24,
    "frame_range": [1, 720],
    "acts": [
        {"frames": [1, 144], "name": "assembly", "concepts": ["reverse assembly reveal", "stagger", "camera anticipation"]},
        {"frames": [145, 288], "name": "transport", "concepts": ["linear conveyor", "tracking camera", "negative corridor"]},
        {"frames": [289, 432], "name": "activation", "concepts": ["hinge axis", "causal choreography", "focus pull", "screen emission"]},
        {"frames": [433, 600], "name": "signal city", "concepts": ["environment reveal", "camera arc/crane", "procedural FX"]},
        {"frames": [601, 720], "name": "hero", "concepts": ["floating hold", "settle", "final still"]},
    ],
    "collections": [source_col.name, work_col.name, env_col.name, lights_col.name, rig_col.name, fx_col.name],
    "materials": [shell_mat.name, button_mat.name, text_mat.name, metal_mat.name, screen_mat.name, floor_mat.name],
    "cameras": [cam_a.name, cam_b.name, cam_c.name, cam_d.name, cam_e.name],
    "saved_source_modified": False,
}
(PROJECT / "film-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
print("LAST_SIGNAL_RESULT=" + json.dumps({"blend": str(BLEND), "manifest": str(PROJECT / 'film-manifest.json')}))
