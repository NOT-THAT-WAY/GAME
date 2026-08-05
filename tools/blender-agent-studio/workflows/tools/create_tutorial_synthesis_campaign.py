"""Build one reproducible stage of the tutorial-synthesis production campaign.

Run with Blender, for example:
  Blender --background --python workflows/tools/create_tutorial_synthesis_campaign.py -- --stage 1

Every stage is rebuilt from the immutable DRUMBOII asset library and written to its
own directory.  The script never opens or overwrites the Pulsed production file.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
ASSET_LIBRARY = ROOT / "asset_library" / "imported" / "drumboii-y2k-assets.blend"
CAMPAIGN_DIR = ROOT / "projects" / "tutorial-synthesis-lab-2026-07-19"
FPS = 24
STAGE_NAMES = {
    1: "01-clay-object-motion",
    2: "02-camera-language",
    3: "03-procedural-lookdev",
    4: "04-mechanical-choreography",
    5: "05-environment-shot",
    6: "06-final-multishot",
}
STAGE_GATES = {
    1: [1, 12, 24, 54, 72],
    2: [1, 12, 24, 54, 72],
    3: [1, 12, 24, 54, 72],
    4: [73, 84, 108, 128, 144],
    5: [145, 156, 192, 228, 240],
    6: [1, 24, 54, 72, 73, 108, 144, 145, 192, 228, 240],
}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=int, choices=range(1, 7), required=True)
    parser.add_argument("--skip-renders", action="store_true")
    return parser.parse_args(argv)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def move_to_collection(obj, collection):
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    collection.objects.link(obj)


def material(name, color, metallic=0.0, roughness=0.35, emission=None, strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission is not None:
        emission_socket = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        strength_socket = bsdf.inputs.get("Emission Strength")
        if emission_socket:
            emission_socket.default_value = emission
        if strength_socket:
            strength_socket.default_value = strength
    return mat


def procedural_material(name, color_a, color_b, metallic=0.15, roughness=0.24, scale=4.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    texcoord = nodes.new("ShaderNodeTexCoord")
    texcoord.name = "USTUDIO_GENERATED_COORDS"
    noise = nodes.new("ShaderNodeTexNoise")
    noise.name = "USTUDIO_MICRO_TEXTURE"
    noise.noise_dimensions = "3D"
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 5.0
    noise.inputs["Roughness"].default_value = 0.62
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.name = "USTUDIO_COLOR_SYSTEM"
    ramp.color_ramp.elements[0].color = color_a
    ramp.color_ramp.elements[1].color = color_b
    ramp.color_ramp.elements[0].position = 0.28
    ramp.color_ramp.elements[1].position = 0.74
    bump = nodes.new("ShaderNodeBump")
    bump.name = "USTUDIO_MICRO_BUMP"
    bump.inputs["Strength"].default_value = 0.12
    bump.inputs["Distance"].default_value = 0.035
    links.new(texcoord.outputs["Generated"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def empty(collection, name, location=(0, 0, 0), display="PLAIN_AXES", size=0.2):
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    obj.empty_display_type = display
    obj.empty_display_size = size
    collection.objects.link(obj)
    return obj


def cube(collection, name, location, scale, mat, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(obj, collection)
    if mat:
        obj.data.materials.append(mat)
    if bevel:
        modifier = obj.modifiers.new("USTUDIO_BEVEL", "BEVEL")
        modifier.width = bevel
        modifier.segments = 3
    return obj


def cylinder(collection, name, location, radius, depth, mat, rotation=(0, 0, 0), vertices=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    move_to_collection(obj, collection)
    if mat:
        obj.data.materials.append(mat)
    return obj


def area_light(collection, name, location, energy, size, color, target):
    data = bpy.data.lights.new(name + "_DATA", "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    collection.objects.link(obj)
    constraint = obj.constraints.new("TRACK_TO")
    constraint.name = "USTUDIO_LIGHT_TARGET"
    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"
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


def world_bounds(objects):
    points = [obj.matrix_world @ Vector(corner) for obj in objects if obj.type == "MESH" for corner in obj.bound_box]
    if not points:
        return Vector((0, 0, 0)), Vector((0, 0, 0))
    return (
        Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points))),
        Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points))),
    )


def append_asset(asset_name, collection_name, controls, position=(0, 0, 0), scale=1.0):
    with bpy.data.libraries.load(str(ASSET_LIBRARY), link=False) as (data_from, data_to):
        if asset_name not in data_from.collections:
            raise RuntimeError(f"Asset {asset_name} absent de {ASSET_LIBRARY}")
        data_to.collections = [asset_name]
    source_collection = data_to.collections[0]
    source_collection.name = collection_name
    bpy.context.scene.collection.children.link(source_collection)
    source_collection["ustudio_source_library"] = str(ASSET_LIBRARY.relative_to(ROOT))
    source_collection["ustudio_source_asset"] = asset_name
    objects = list(source_collection.all_objects)
    roots = [obj for obj in objects if obj.parent not in objects]
    bpy.context.view_layer.update()
    minimum, maximum = world_bounds(objects)
    center = (minimum + maximum) / 2
    root = empty(controls, f"USTUDIO_{asset_name}_ROOT", display="CIRCLE", size=0.35)
    for obj in roots:
        matrix = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = matrix
    root.scale = (scale, scale, scale)
    root.location = Vector(position) - Vector((center.x * scale, center.y * scale, minimum.z * scale))
    root["ustudio_asset_source"] = asset_name
    root["ustudio_work_copy"] = True
    bpy.context.view_layer.update()
    return {"collection": source_collection, "root": root, "objects": objects, "source_bounds": [list(minimum), list(maximum)]}


def key(obj, data_path, value, frame, index=None, group="USTUDIO_TUTORIAL_SYNTHESIS"):
    if index is None:
        setattr(obj, data_path, value)
        obj.keyframe_insert(data_path=data_path, frame=frame, group=group)
    else:
        values = list(getattr(obj, data_path))
        values[index] = value
        setattr(obj, data_path, values)
        obj.keyframe_insert(data_path=data_path, index=index, frame=frame, group=group)


def curves(owner):
    animation = getattr(owner, "animation_data", None)
    action = getattr(animation, "action", None) if animation else None
    if not action:
        return []
    if hasattr(action, "fcurves"):
        return list(action.fcurves)
    result = []
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                result.extend(bag.fcurves)
    return result


def smooth(owner, linear_paths=()):
    for curve in curves(owner):
        is_linear = curve.data_path in linear_paths
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR" if is_linear else "BEZIER"
            if not is_linear:
                point.handle_left_type = "AUTO_CLAMPED"
                point.handle_right_type = "AUTO_CLAMPED"


def animate_render_visibility(objects, visible_start, visible_end):
    """Use constant visibility keys so shot-specific assets never contaminate another shot."""
    for obj in objects:
        if visible_start > 1:
            obj.hide_render = True
            obj.keyframe_insert(data_path="hide_render", frame=1)
            obj.keyframe_insert(data_path="hide_render", frame=visible_start - 1)
        obj.hide_render = False
        obj.keyframe_insert(data_path="hide_render", frame=visible_start)
        obj.keyframe_insert(data_path="hide_render", frame=visible_end)
        obj.hide_render = True
        obj.keyframe_insert(data_path="hide_render", frame=visible_end + 1)
        for curve in curves(obj):
            if curve.data_path == "hide_render":
                for point in curve.keyframe_points:
                    point.interpolation = "CONSTANT"


def camera(collection, name, target, focus, lens=58):
    data = bpy.data.cameras.new(name + "_DATA")
    data.lens = lens
    data.sensor_width = 36
    data.clip_start = 0.03
    data.clip_end = 250
    data.dof.use_dof = True
    data.dof.focus_object = focus
    data.dof.aperture_fstop = 3.8
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    constraint = obj.constraints.new("TRACK_TO")
    constraint.name = "USTUDIO_TRACK_TO"
    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"
    return obj


def animate_speaker(root, base):
    x, y, z = base
    poses = {
        1: ((x - 0.75, y, z + 0.02), (0, 0, math.radians(-18))),
        12: ((x - 0.75, y, z + 0.02), (0, 0, math.radians(-18))),
        24: ((x - 0.95, y, z + 0.11), (math.radians(-5), 0, math.radians(-28))),
        54: ((x, y, z + 0.46), (math.radians(4), math.radians(-8), math.radians(342))),
        66: ((x + 0.08, y, z + 0.16), (0, math.radians(2), math.radians(366))),
        72: ((x, y, z + 0.12), (0, 0, math.radians(360))),
    }
    for frame, (location, rotation) in poses.items():
        key(root, "location", location, frame)
        key(root, "rotation_euler", rotation, frame)
    smooth(root)
    root["ustudio_motion_recipe"] = "still-anticipation-main-settle-still"


def animate_gameboii(root, base):
    x, y, z = base
    poses = {
        73: ((x - 3.2, y, z), (0, 0, math.radians(-5))),
        84: ((x - 3.2, y, z), (0, 0, math.radians(-5))),
        108: ((x - 0.6, y, z + 1.15), (math.radians(-22), math.radians(8), math.radians(5))),
        128: ((x + 1.0, y, z + 0.05), (0, 0, math.radians(3))),
        144: ((x + 3.0, y, z), (0, 0, math.radians(3))),
    }
    for frame, (location, rotation) in poses.items():
        key(root, "location", location, frame)
        key(root, "rotation_euler", rotation, frame)
    smooth(root)
    for curve in curves(root):
        if curve.data_path == "location" and curve.array_index == 0:
            for point in curve.keyframe_points:
                point.interpolation = "LINEAR"
    root["ustudio_motion_recipe"] = "linear-transport-bezier-pop-impact"
    root["ustudio_loop_pitch"] = 0.32


def animate_bike(root, base):
    x, y, z = base
    poses = {
        145: ((x - 5.2, y, z), (0, 0, math.radians(-2))),
        156: ((x - 5.2, y, z), (0, 0, math.radians(-2))),
        192: ((x, y, z + 0.05), (0, math.radians(-2), math.radians(1))),
        228: ((x + 5.2, y, z), (0, 0, math.radians(2))),
        240: ((x + 5.2, y, z), (0, 0, math.radians(2))),
    }
    for frame, (location, rotation) in poses.items():
        key(root, "location", location, frame)
        key(root, "rotation_euler", rotation, frame)
    smooth(root)
    for curve in curves(root):
        if curve.data_path == "location" and curve.array_index == 0:
            for point in curve.keyframe_points:
                point.interpolation = "LINEAR"
    root["ustudio_motion_recipe"] = "environment-travel-hold-move-hold"


def create_floor(environment, mats):
    floor = cube(environment, "USTUDIO_FLOOR", (0, 0, -0.13), (9.5, 7.0, 0.12), mats["floor"], bevel=0.08)
    floor["ustudio_role"] = "environment_blockout"
    return floor


def create_pedestal(environment, location, mats):
    pedestal = cylinder(environment, "USTUDIO_HERO_PEDESTAL", location, 0.88, 0.24, mats["pedestal"], vertices=72)
    bevel = pedestal.modifiers.new("USTUDIO_PEDESTAL_BEVEL", "BEVEL")
    bevel.width = 0.045
    bevel.segments = 3
    ring = cylinder(environment, "USTUDIO_PEDESTAL_RING", (location[0], location[1], location[2] + 0.135), 0.91, 0.025, mats["magenta"], vertices=72)
    return pedestal, ring


def create_cyclorama(environment, mats):
    back = cube(environment, "USTUDIO_CYC_BACK", (0, 4.8, 3.0), (9.5, 0.12, 3.2), mats["backdrop"], bevel=0.12)
    left = cube(environment, "USTUDIO_CYC_LEFT", (-9.35, 0.7, 2.0), (0.12, 4.0, 2.1), mats["backdrop"], bevel=0.1)
    right = cube(environment, "USTUDIO_CYC_RIGHT", (9.35, 0.7, 2.0), (0.12, 4.0, 2.1), mats["backdrop"], bevel=0.1)
    return [back, left, right]


def create_conveyor(environment, mats):
    base = cube(environment, "USTUDIO_CONVEYOR_BASE", (0.25, 0.55, 0.22), (4.4, 0.86, 0.2), mats["machine"], bevel=0.12)
    base["ustudio_recipe"] = "factory-array-curve-loop"
    for i in range(28):
        x = -4.05 + i * 0.30
        link = cube(environment, f"USTUDIO_BELT_LINK_{i:02d}", (x, 0.55, 0.47), (0.135, 0.76, 0.055), mats["belt"], bevel=0.025)
        link["ustudio_loop_index"] = i
    for x in (-4.0, 4.5):
        cylinder(environment, f"USTUDIO_ROLLER_{x:+.1f}", (x, 0.55, 0.24), 0.27, 1.5, mats["cyan"], rotation=(math.pi / 2, 0, 0), vertices=48)
    for x in (-3.5, -1.75, 0, 1.75, 3.5):
        cube(environment, f"USTUDIO_CONVEYOR_LEG_{x:+.2f}", (x, 0.55, -0.15), (0.10, 0.62, 0.32), mats["machine"], bevel=0.035)
    return base


def create_environment(environment, mats):
    road = cube(environment, "USTUDIO_ROAD", (0, -3.15, 0.015), (8.2, 1.35, 0.035), mats["road"], bevel=0.05)
    road["ustudio_negative_corridor"] = True
    for x in range(-7, 8, 2):
        cube(environment, f"USTUDIO_ROAD_DASH_{x:+03d}", (x, -3.15, 0.06), (0.52, 0.035, 0.012), mats["cyan"], bevel=0.01)
    for idx, x in enumerate((-6.6, -3.3, 0.0, 3.3, 6.6)):
        cube(environment, f"USTUDIO_ARCH_L_{idx}", (x, -4.48, 1.55), (0.09, 0.09, 1.5), mats["magenta"], bevel=0.025)
        cube(environment, f"USTUDIO_ARCH_R_{idx}", (x, -1.82, 1.55), (0.09, 0.09, 1.5), mats["cyan"], bevel=0.025)
        cube(environment, f"USTUDIO_ARCH_TOP_{idx}", (x, -3.15, 3.02), (0.09, 1.42, 0.09), mats["violet"], bevel=0.025)
    random.seed(1987)
    for idx in range(18):
        x = random.uniform(-8.0, 8.0)
        # Keep all large masses behind the road.  The camera travels on the near
        # side, so scattering there would violate the negative camera corridor.
        y = -3.15 + random.uniform(2.3, 3.8)
        height = random.uniform(0.6, 2.8)
        width = random.uniform(0.25, 0.8)
        mat = mats["city_a"] if idx % 3 else mats["city_b"]
        block = cube(environment, f"USTUDIO_CITY_MASS_{idx:02d}", (x, y, height / 2), (width, width, height / 2), mat, bevel=0.05)
        block["ustudio_scatter_seed"] = 1987
    return road


def copy_procedural_to_asset(asset, prefix, mat):
    count = 0
    for obj in asset["objects"]:
        if obj.type != "MESH":
            continue
        if len(obj.data.materials) == 0:
            obj.data.materials.append(mat)
        else:
            for index in range(len(obj.data.materials)):
                original = obj.data.materials[index]
                clone = mat.copy()
                clone.name = f"{prefix}_{original.name if original else index}"
                obj.data.materials[index] = clone
        count += 1
    return count


def create_mats():
    return {
        "clay": material("M_TEST_CLAY", (0.34, 0.37, 0.44, 1), metallic=0.0, roughness=0.6),
        "floor": material("M_FLOOR_INK", (0.012, 0.017, 0.035, 1), metallic=0.2, roughness=0.28),
        "backdrop": material("M_BACKDROP_NAVY", (0.006, 0.009, 0.03, 1), roughness=0.38),
        "pedestal": material("M_PEDESTAL_BLUE", (0.025, 0.085, 0.24, 1), metallic=0.65, roughness=0.19),
        "machine": material("M_MACHINE", (0.025, 0.034, 0.065, 1), metallic=0.75, roughness=0.22),
        "belt": material("M_BELT", (0.035, 0.045, 0.065, 1), metallic=0.45, roughness=0.3),
        "road": material("M_ROAD", (0.018, 0.022, 0.035, 1), metallic=0.05, roughness=0.52),
        "city_a": material("M_CITY_A", (0.025, 0.035, 0.08, 1), metallic=0.15, roughness=0.42),
        "city_b": material("M_CITY_B", (0.08, 0.018, 0.075, 1), metallic=0.12, roughness=0.4),
        "magenta": material("M_NEON_MAGENTA", (0.3, 0.005, 0.12, 1), roughness=0.2, emission=(1, 0.01, 0.25, 1), strength=8),
        "cyan": material("M_NEON_CYAN", (0.005, 0.20, 0.32, 1), roughness=0.18, emission=(0.01, 0.8, 1, 1), strength=7),
        "violet": material("M_NEON_VIOLET", (0.12, 0.015, 0.38, 1), roughness=0.2, emission=(0.4, 0.03, 1, 1), strength=6),
    }


def create_speaker_camera(cameras, target_pos, animated=True):
    target = empty(cameras, "USTUDIO_SPEAKER_TARGET", target_pos, "SPHERE", 0.12)
    focus = empty(cameras, "USTUDIO_SPEAKER_FOCUS", target_pos, "CUBE", 0.09)
    cam = camera(cameras, "USTUDIO_CAM_SPEAKER", target, focus, 62)
    if not animated:
        cam.location = Vector(target_pos) + Vector((2.7, -5.2, 1.65))
    else:
        positions = {
            1: Vector(target_pos) + Vector((3.1, -5.8, 2.0)),
            12: Vector(target_pos) + Vector((3.1, -5.8, 2.0)),
            24: Vector(target_pos) + Vector((3.45, -6.0, 1.72)),
            54: Vector(target_pos) + Vector((2.65, -4.85, 1.58)),
            66: Vector(target_pos) + Vector((2.0, -3.8, 1.38)),
            72: Vector(target_pos) + Vector((2.0, -3.8, 1.38)),
        }
        for frame, location in positions.items():
            key(cam, "location", location, frame)
        target_locations = {
            1: Vector(target_pos) + Vector((-0.16, 0, -0.05)),
            16: Vector(target_pos) + Vector((-0.16, 0, -0.05)),
            28: Vector(target_pos) + Vector((-0.30, 0, 0.06)),
            58: Vector(target_pos) + Vector((0.04, 0, 0.20)),
            70: Vector(target_pos) + Vector((0.02, 0, 0.02)),
            72: Vector(target_pos) + Vector((0.02, 0, 0.02)),
        }
        for frame, location in target_locations.items():
            key(target, "location", location, frame)
        smooth(cam)
        smooth(target)
    cam["ustudio_camera_recipe"] = "K1-pose-K2-anticipation-K3-main-K4-settle"
    cam["ustudio_target_lag_frames"] = 4
    return cam


def create_game_camera(cameras, target_pos):
    target = empty(cameras, "USTUDIO_GAME_TARGET", target_pos, "SPHERE", 0.15)
    focus = empty(cameras, "USTUDIO_GAME_FOCUS", target_pos, "CUBE", 0.1)
    cam = camera(cameras, "USTUDIO_CAM_GAMEBOII", target, focus, 70)
    positions = {
        73: Vector(target_pos) + Vector((4.8, -6.2, 2.8)),
        84: Vector(target_pos) + Vector((4.8, -6.2, 2.8)),
        108: Vector(target_pos) + Vector((2.7, -4.3, 2.15)),
        128: Vector(target_pos) + Vector((3.7, -5.1, 2.45)),
        144: Vector(target_pos) + Vector((3.7, -5.1, 2.45)),
    }
    for frame, location in positions.items():
        key(cam, "location", location, frame)
    for frame, offset in ((73, (-1.8, 0, 0)), (84, (-1.8, 0, 0)), (108, (-0.35, 0, 0.8)), (128, (1.0, 0, 0.05)), (144, (2.0, 0, 0))):
        key(target, "location", Vector(target_pos) + Vector(offset), frame)
    smooth(cam)
    smooth(target)
    cam["ustudio_camera_recipe"] = "restrained-product-camera-during-complex-action"
    return cam


def create_bike_camera(cameras, target_pos):
    target = empty(cameras, "USTUDIO_BIKE_TARGET", target_pos, "SPHERE", 0.2)
    focus = empty(cameras, "USTUDIO_BIKE_FOCUS", target_pos, "CUBE", 0.12)
    cam = camera(cameras, "USTUDIO_CAM_BIKE", target, focus, 46)
    xs = {145: -5.2, 156: -5.2, 192: 0.0, 228: 5.2, 240: 5.2}
    for frame, x in xs.items():
        key(cam, "location", Vector((x - 4.6, target_pos[1] - 4.6, 2.6)), frame)
        key(target, "location", Vector((x, target_pos[1], target_pos[2])), frame)
    smooth(cam, linear_paths=("location",))
    smooth(target, linear_paths=("location",))
    cam["ustudio_camera_recipe"] = "environment-follow-with-negative-corridor"
    return cam


def setup_lighting(lighting, target, stage):
    area_light(lighting, "USTUDIO_KEY", (2.6, -3.8, 6.2), 1050, 4.0, (0.58, 0.72, 1.0), target)
    area_light(lighting, "USTUDIO_FILL", (-4.2, -0.7, 3.3), 720, 3.2, (0.35, 0.15, 1.0), target)
    area_light(lighting, "USTUDIO_RIM", (3.4, 3.2, 4.0), 1300, 2.2, (1.0, 0.04, 0.32), target)
    if stage >= 4:
        point_light(lighting, "USTUDIO_CONVEYOR_GLOW", (0, 0.4, 2.7), 480, 1.0, (0.1, 0.55, 1.0))
    if stage >= 5:
        for index, x in enumerate((-5.0, 0.0, 5.0)):
            point_light(lighting, f"USTUDIO_ROAD_LIGHT_{index}", (x, -3.2, 2.6), 720, 1.2, (1.0, 0.04, 0.25) if index % 2 == 0 else (0.02, 0.65, 1.0))


def add_markers(scene, stage):
    labels = {
        1: "USTUDIO_S0_STILL",
        24: "USTUDIO_S1_ANTICIPATION",
        54: "USTUDIO_S2_ACTION",
        72: "USTUDIO_SPEAKER_REST",
        73: "USTUDIO_CONVEYOR_START",
        108: "USTUDIO_GAME_PEAK",
        128: "USTUDIO_GAME_IMPACT",
        144: "USTUDIO_GAME_REST",
        145: "USTUDIO_ENV_START",
        192: "USTUDIO_ENV_TRAVEL",
        228: "USTUDIO_ENV_ARRIVAL",
        240: "USTUDIO_FINAL_STILL",
    }
    limit = 72 if stage <= 3 else 144 if stage == 4 else 240
    for frame, name in labels.items():
        if frame <= limit:
            scene.timeline_markers.new(name, frame=frame)


def configure_compositor(scene):
    # Blender 5.1 stores the compositor in Scene.compositing_node_group.  The
    # older Scene.node_tree API was removed.
    tree = bpy.data.node_groups.new("USTUDIO_FINAL_COMPOSITOR", "CompositorNodeTree")
    tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    output = tree.nodes.new("NodeGroupOutput")
    output.name = "USTUDIO_COMPOSITE_OUTPUT"
    render_layers = tree.nodes.new("CompositorNodeRLayers")
    glare = tree.nodes.new("CompositorNodeGlare")
    glare.inputs["Type"].default_value = "Fog Glow"
    glare.inputs["Quality"].default_value = "High"
    glare.inputs["Threshold"].default_value = 1.0
    glare.inputs["Size"].default_value = 0.55
    tree.links.new(render_layers.outputs["Image"], glare.inputs["Image"])
    tree.links.new(glare.outputs["Image"], output.inputs["Image"])
    scene.compositing_node_group = tree


def render_gates(scene, stage_dir, frames):
    gate_dir = stage_dir / "snapshots"
    gate_dir.mkdir(parents=True, exist_ok=True)
    rendered = []
    for frame in frames:
        scene.frame_set(frame)
        path = gate_dir / f"frame_{frame:04d}.png"
        scene.render.filepath = str(path)
        started = time.monotonic()
        bpy.ops.render.render(write_still=True)
        rendered.append({"frame": frame, "path": str(path.relative_to(ROOT)), "seconds": round(time.monotonic() - started, 3)})
    return rendered


def validate_scene(scene, stage, assets, cameras, rendered):
    errors = []
    if scene.camera is None:
        errors.append("camera_missing")
    if not cameras:
        errors.append("camera_list_empty")
    if not assets:
        errors.append("asset_list_empty")
    for item in rendered:
        path = ROOT / item["path"]
        if not path.exists() or path.stat().st_size < 1024:
            errors.append(f"render_missing_or_small:{path.name}")
    animated_roots = [asset["root"].name for asset in assets if asset["root"].animation_data]
    if not animated_roots:
        errors.append("no_animated_asset_root")
    return {
        "passed": not errors,
        "errors": errors,
        "scene": scene.name,
        "stage": stage,
        "objects": len(scene.objects),
        "materials": len(bpy.data.materials),
        "cameras": [item.name for item in cameras],
        "animated_roots": animated_roots,
        "timeline_markers": [{"name": marker.name, "frame": marker.frame} for marker in scene.timeline_markers],
    }


def main():
    args = parse_args()
    stage = args.stage
    stage_name = STAGE_NAMES[stage]
    stage_dir = CAMPAIGN_DIR / "stages" / stage_name
    stage_dir.mkdir(parents=True, exist_ok=True)
    (stage_dir / "snapshots").mkdir(exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = f"TUTORIAL_SYNTHESIS_STAGE_{stage:02d}"
    scene.frame_start = 1
    scene.frame_end = 72 if stage <= 3 else 144 if stage == 4 else 240
    scene.render.fps = FPS
    scene.render.fps_base = 1.0
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.render.use_file_extension = True
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene["ustudio_campaign"] = "tutorial-synthesis-lab-2026-07-19"
    scene["ustudio_stage"] = stage
    scene["ustudio_no_silent_source_save"] = True
    scene["ustudio_knowledge_sources"] = json.dumps([
        "knowledge/tutorials/drumboii-camera-tutorial-2026-07-18/analysis.json",
        "knowledge/tutorials/beginner-blender-tutorial-2026/analysis.json",
        "knowledge/tutorials/ray-ban-product-animation/analysis.json",
        "knowledge/tutorials/factory-animation-polygon-runway/analysis.json",
        "knowledge/tutorials/quick-animation-blender-4/analysis.json",
        "knowledge/tutorials/wireless-pods-animation-polygon-runway/analysis.json",
    ])

    world = bpy.data.worlds.new("USTUDIO_SYNTHESIS_WORLD")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.0025, 0.004, 0.015, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.11 if stage >= 2 else 0.22
    scene.world = world

    controls = bpy.data.collections.new("WORK_ASSET_CONTROLS")
    environment = bpy.data.collections.new("ENVIRONMENT")
    lighting = bpy.data.collections.new("LIGHTS")
    cameras_collection = bpy.data.collections.new("CAMERA_RIGS")
    fx = bpy.data.collections.new("FX")
    for collection in (controls, environment, lighting, cameras_collection, fx):
        scene.collection.children.link(collection)

    mats = create_mats()
    create_floor(environment, mats)
    if stage >= 2:
        create_cyclorama(environment, mats)

    speaker_base = (-6.2, 3.6, 0.25) if stage >= 4 else (0.0, 0.0, 0.25)
    speaker = append_asset("BLOB_SPEAKER", "WORK_ASSET_BLOB_SPEAKER", controls, speaker_base, 1.0)
    animate_speaker(speaker["root"], speaker_base)
    speaker_pedestal = create_pedestal(environment, (speaker_base[0], speaker_base[1], 0.12), mats)

    if stage == 1:
        scene.view_layers[0].material_override = mats["clay"]
    elif stage >= 3:
        speaker_surface = procedural_material(
            "M_TEST_SPEAKER_PROCEDURAL",
            (0.015, 0.02, 0.06, 1),
            (0.18, 0.015, 0.42, 1),
            metallic=0.48,
            roughness=0.2,
            scale=5.5,
        )
        copy_procedural_to_asset(speaker, "M_WORK_SPEAKER", speaker_surface)

    assets = [speaker]
    cameras = []
    speaker_target = Vector((speaker_base[0], speaker_base[1], 0.72))
    speaker_cam = create_speaker_camera(cameras_collection, speaker_target, animated=stage >= 2)
    cameras.append(speaker_cam)
    scene.camera = speaker_cam

    global_target = empty(lighting, "USTUDIO_GLOBAL_LIGHT_TARGET", (0, 0, 0.8), "SPHERE", 0.12)
    setup_lighting(lighting, global_target, stage)

    lookdev_objects = []
    if stage >= 3:
        for x in (-1.25, 1.25):
            lookdev_objects.append(cube(environment, f"USTUDIO_LOOKDEV_BAR_{x:+.2f}", (speaker_base[0] + x, speaker_base[1] + 1.0, 1.1), (0.035, 0.035, 1.1), mats["magenta"] if x < 0 else mats["cyan"], bevel=0.015))

    gameboii = None
    game_cam = None
    conveyor_objects = []
    if stage >= 4:
        animate_render_visibility([*speaker["objects"], *speaker_pedestal, *lookdev_objects], 1, 72)
        objects_before = set(environment.objects)
        create_conveyor(environment, mats)
        conveyor_objects = [obj for obj in environment.objects if obj not in objects_before]
        if stage >= 5:
            animate_render_visibility(conveyor_objects, 73, 144)
        game_base = (0.25, 0.55, 0.50)
        gameboii = append_asset("DRUMBOII_GAMEBOII", "WORK_ASSET_GAMEBOII", controls, game_base, 0.72)
        animate_gameboii(gameboii["root"], game_base)
        game_surface = procedural_material(
            "M_TEST_GAMEBOII_PROCEDURAL",
            (0.015, 0.16, 0.24, 1),
            (0.55, 0.015, 0.30, 1),
            metallic=0.22,
            roughness=0.26,
            scale=8.0,
        )
        copy_procedural_to_asset(gameboii, "M_WORK_GAMEBOII", game_surface)
        if stage >= 5:
            animate_render_visibility(gameboii["objects"], 73, 144)
        assets.append(gameboii)
        game_cam = create_game_camera(cameras_collection, (0.25, 0.55, 1.15))
        cameras.append(game_cam)
        scene.camera = game_cam

    bike = None
    bike_cam = None
    if stage >= 5:
        objects_before = set(environment.objects)
        create_environment(environment, mats)
        road_environment_objects = [obj for obj in environment.objects if obj not in objects_before]
        if stage >= 6:
            animate_render_visibility(road_environment_objects, 145, 240)
        bike_base = (0.0, -3.15, 0.10)
        bike = append_asset("DRUMBOII_BLOB_BIKE", "WORK_ASSET_BLOB_BIKE", controls, bike_base, 0.72)
        animate_bike(bike["root"], bike_base)
        animate_render_visibility(bike["objects"], 145, 240)
        assets.append(bike)
        traffic = append_asset("DRUMBOII_TRAFFIC_LIGHT", "SET_DRESSING_TRAFFIC_LIGHT", controls, (6.8, -0.5, 0.0), 0.62)
        traffic["root"]["ustudio_role"] = "set_dressing"
        animate_render_visibility(traffic["objects"], 145, 240)
        assets.append(traffic)
        bike_cam = create_bike_camera(cameras_collection, (0.0, -3.15, 1.0))
        cameras.append(bike_cam)
        scene.camera = bike_cam

    if stage >= 6:
        configure_compositor(scene)
        scene.camera = speaker_cam
        for frame, cam, name in (
            (1, speaker_cam, "USTUDIO_SHOT_A_SPEAKER"),
            (73, game_cam, "USTUDIO_SHOT_B_GAMEBOII"),
            (145, bike_cam, "USTUDIO_SHOT_C_BIKE"),
        ):
            marker = scene.timeline_markers.get(name) or scene.timeline_markers.new(name, frame=frame)
            marker.camera = cam
        if hasattr(scene.render, "use_motion_blur"):
            scene.render.use_motion_blur = True

    add_markers(scene, stage)
    scene.frame_set(STAGE_GATES[stage][0])

    blend_file = stage_dir / f"{stage_name}.blend"
    scene.render.filepath = str(stage_dir / "snapshots" / "frame_####.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_file), compress=True, relative_remap=True)

    rendered = [] if args.skip_renders else render_gates(scene, stage_dir, STAGE_GATES[stage])
    validation = validate_scene(scene, stage, assets, cameras, rendered)
    manifest = {
        "schema_version": 1,
        "campaign": "tutorial-synthesis-lab-2026-07-19",
        "stage": stage,
        "stage_name": stage_name,
        "created_at": utc_now(),
        "blend_file": str(blend_file.relative_to(ROOT)),
        "source_library": str(ASSET_LIBRARY.relative_to(ROOT)),
        "source_assets": [asset["root"].get("ustudio_asset_source", "unknown") for asset in assets],
        "frame_range": [scene.frame_start, scene.frame_end],
        "fps": FPS,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "active_camera": scene.camera.name,
        "cameras": [cam.name for cam in cameras],
        "snapshots": rendered,
        "validation": validation,
        "knowledge_sources": json.loads(scene["ustudio_knowledge_sources"]),
        "principles_tested": {
            1: ["immutable source asset", "work root", "still-action-settle", "clay silhouette"],
            2: ["four-pose camera", "anticipation", "delayed target", "independent focus"],
            3: ["procedural texture", "roughness hierarchy", "neon rim", "AgX lookdev"],
            4: ["linear transport", "bezier event", "causal choreography", "conveyor pitch"],
            5: ["camera-first environment", "negative corridor", "controlled scatter", "follow camera"],
            6: ["multi-shot edit", "camera markers", "combined tutorial knowledge", "professional gates"],
        }[stage],
    }
    (stage_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    if not validation["passed"]:
        raise RuntimeError(f"Stage validation failed: {validation['errors']}")
    print("UNRECORDED_RESULT=" + json.dumps({"stage": stage, "blend": str(blend_file), "validation": validation}))


if __name__ == "__main__":
    main()
