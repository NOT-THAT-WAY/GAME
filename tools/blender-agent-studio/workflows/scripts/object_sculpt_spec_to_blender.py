"""Build an isolated Blender asset trial from an ObjectSculptSpec extension.

Run with Blender, never with the Studio MCP:

    blender --background --factory-startup \
      --python workflows/scripts/object_sculpt_spec_to_blender.py -- \
      --spec projects/.../object-sculpt-spec.json \
      --trial-root projects/... \
      --render-gates

The upstream img2threejs schema remains authoritative for intake, feature inventory,
quality gates, and semantic component hierarchy.  The optional ``blenderRecipe``
extension is intentionally small: it maps named primitives and repetitions to bpy,
while preserving pivots, sockets, colliders, material intent, and custom properties.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import bpy
from mathutils import Euler, Quaternion, Vector


PREFIX = "K3_TAD_"
ASSET_COLLECTION = PREFIX + "ASSET"
TECH_COLLECTION = PREFIX + "TECH"
SHOT_COLLECTION = PREFIX + "SHOT"
LIGHT_COLLECTION = PREFIX + "LIGHTS"
ROOT_NAME = PREFIX + "ROOT"
CAMERA_NAME = PREFIX + "CAMERA"
CAMERA_TARGET_NAME = PREFIX + "CAMERA_TARGET"
LIGHT_ROLES = (
    "SUN_REFLECTION",
    "BACK_SHAPE",
    "SIDE_GLIMMER_A",
    "SIDE_GLIMMER_B",
    "DETAIL_RETURN",
)


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--trial-root", required=True, type=Path)
    parser.add_argument("--render-gates", action="store_true")
    parser.add_argument("--render-preview", action="store_true")
    parser.add_argument("--resolution", type=int, default=640)
    return parser.parse_args(argv)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prefixed(value: str) -> str:
    return value if value.startswith("K3_") else PREFIX + value.upper().replace("-", "_")


def ensure_collection(name: str, parent: bpy.types.Collection | None = None) -> bpy.types.Collection:
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(collection)
    return collection


def move_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    for owner in tuple(obj.users_collection):
        owner.objects.unlink(obj)
    collection.objects.link(obj)


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for item in tuple(block):
            if item.users == 0:
                block.remove(item)
    for collection in tuple(bpy.data.collections):
        bpy.data.collections.remove(collection)


def rgba(value: str, alpha: float | None = None) -> tuple[float, float, float, float]:
    raw = value.lstrip("#")
    if len(raw) == 3:
        raw = "".join(char * 2 for char in raw)
    if len(raw) != 6:
        raise ValueError(f"Invalid hex colour: {value}")
    red, green, blue = (int(raw[index : index + 2], 16) / 255.0 for index in (0, 2, 4))
    return (red, green, blue, 1.0 if alpha is None else alpha)


def node_input(node: bpy.types.Node, *names: str) -> bpy.types.NodeSocket | None:
    for name in names:
        if name in node.inputs:
            return node.inputs[name]
    return None


def set_input(node: bpy.types.Node, names: Iterable[str], value: Any) -> None:
    socket = node_input(node, *names)
    if socket is not None:
        socket.default_value = value


def build_materials(spec: dict[str, Any]) -> dict[str, bpy.types.Material]:
    definitions = spec.get("blenderRecipe", {}).get("materials")
    if not isinstance(definitions, list) or not definitions:
        definitions = spec.get("materials", [])
    materials: dict[str, bpy.types.Material] = {}
    for definition in definitions:
        if not isinstance(definition, dict) or not definition.get("id"):
            continue
        material_id = str(definition["id"])
        material = bpy.data.materials.new(prefixed("MAT_" + material_id))
        material.use_nodes = True
        nodes = material.node_tree.nodes
        bsdf = nodes.get("Principled BSDF")
        if bsdf is None:
            bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        alpha = float(definition.get("alpha", 1.0))
        color = rgba(str(definition.get("baseColor", definition.get("color", "#808080"))), alpha)
        set_input(bsdf, ("Base Color",), color)
        set_input(bsdf, ("Metallic",), float(definition.get("metallic", definition.get("metalness", 0.0))))
        roughness = definition.get("roughness", 0.5)
        if isinstance(roughness, dict):
            roughness = roughness.get("base", 0.5)
        set_input(bsdf, ("Roughness",), float(roughness))
        set_input(bsdf, ("IOR",), float(definition.get("ior", 1.45)))
        set_input(
            bsdf,
            ("Transmission Weight", "Transmission"),
            float(definition.get("transmission", 0.0)),
        )
        set_input(bsdf, ("Alpha",), alpha)
        set_input(
            bsdf,
            ("Coat Weight", "Clearcoat"),
            float(definition.get("clearcoat", definition.get("coat", 0.0))),
        )
        set_input(
            bsdf,
            ("Coat Roughness", "Clearcoat Roughness"),
            float(definition.get("coatRoughness", 0.08)),
        )
        emission = definition.get("emission")
        if emission:
            set_input(bsdf, ("Emission Color", "Emission"), rgba(str(emission)))
            set_input(bsdf, ("Emission Strength",), float(definition.get("emissionStrength", 1.0)))
        if alpha < 0.999:
            try:
                material.surface_render_method = "BLENDED"
            except (AttributeError, TypeError):
                pass
            material.diffuse_color = color
            material.use_transparency_overlap = False
        material["k3_material_id"] = material_id
        material["k3_source"] = "ObjectSculptSpec.blenderRecipe.materials"
        materials[material_id] = material
    return materials


def add_bevel(obj: bpy.types.Object, width: float, segments: int = 3) -> None:
    if width <= 0 or obj.type != "MESH":
        return
    modifier = obj.modifiers.new(name=PREFIX + "BEVEL", type="BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"


def apply_transform(obj: bpy.types.Object) -> None:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.select_set(False)


def build_box(item: dict[str, Any]) -> bpy.types.Object:
    size = item.get("size", [1.0, 1.0, 1.0])
    bpy.ops.mesh.primitive_cube_add(location=item.get("location", [0, 0, 0]))
    obj = bpy.context.object
    obj.scale = Vector(size) * 0.5
    obj.rotation_euler = Euler(tuple(math.radians(v) for v in item.get("rotation", [0, 0, 0])), "XYZ")
    apply_transform(obj)
    add_bevel(obj, float(item.get("bevel", 0.0)), int(item.get("bevelSegments", 4)))
    return obj


def build_cylinder(item: dict[str, Any]) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=int(item.get("vertices", 64)),
        radius=float(item.get("radius", 0.5)),
        depth=float(item.get("depth", 1.0)),
        location=item.get("location", [0, 0, 0]),
        rotation=tuple(math.radians(v) for v in item.get("rotation", [0, 0, 0])),
    )
    obj = bpy.context.object
    add_bevel(obj, float(item.get("bevel", 0.0)), int(item.get("bevelSegments", 3)))
    return obj


def build_torus(item: dict[str, Any]) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(
        major_radius=float(item.get("majorRadius", 0.5)),
        minor_radius=float(item.get("minorRadius", 0.1)),
        major_segments=int(item.get("majorSegments", 72)),
        minor_segments=int(item.get("minorSegments", 16)),
        location=item.get("location", [0, 0, 0]),
        rotation=tuple(math.radians(v) for v in item.get("rotation", [0, 0, 0])),
    )
    return bpy.context.object


def build_sphere(item: dict[str, Any]) -> bpy.types.Object:
    scale = item.get("scale", [1, 1, 1])
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=int(item.get("segments", 48)),
        ring_count=int(item.get("rings", 24)),
        radius=float(item.get("radius", 0.5)),
        location=item.get("location", [0, 0, 0]),
        rotation=tuple(math.radians(v) for v in item.get("rotation", [0, 0, 0])),
    )
    obj = bpy.context.object
    obj.scale = Vector(scale)
    apply_transform(obj)
    return obj


def build_curve(item: dict[str, Any]) -> bpy.types.Object:
    curve_data = bpy.data.curves.new(prefixed(item["id"] + "_CURVE"), type="CURVE")
    curve_data.dimensions = "3D"
    curve_data.resolution_u = int(item.get("resolution", 12))
    curve_data.bevel_depth = float(item.get("bevelDepth", 0.001))
    curve_data.bevel_resolution = int(item.get("bevelResolution", 4))
    spline = curve_data.splines.new("BEZIER" if item.get("smooth", True) else "POLY")
    points = item.get("points", [])
    if spline.type == "BEZIER":
        spline.bezier_points.add(max(0, len(points) - 1))
        for point, coords in zip(spline.bezier_points, points):
            point.co = coords
            point.handle_left_type = "AUTO"
            point.handle_right_type = "AUTO"
    else:
        spline.points.add(max(0, len(points) - 1))
        for point, coords in zip(spline.points, points):
            point.co = (*coords, 1.0)
    obj = bpy.data.objects.new(prefixed(item["id"]), curve_data)
    obj.location = item.get("location", [0, 0, 0])
    obj.rotation_euler = Euler(tuple(math.radians(v) for v in item.get("rotation", [0, 0, 0])), "XYZ")
    bpy.context.scene.collection.objects.link(obj)
    return obj


def build_text(item: dict[str, Any]) -> bpy.types.Object:
    curve = bpy.data.curves.new(prefixed(item["id"] + "_FONT"), type="FONT")
    curve.body = str(item.get("text", ""))
    curve.align_x = str(item.get("alignX", "LEFT"))
    curve.align_y = str(item.get("alignY", "CENTER"))
    curve.size = float(item.get("size", 0.01))
    curve.extrude = float(item.get("extrude", 0.0002))
    curve.bevel_depth = float(item.get("bevelDepth", 0.00005))
    obj = bpy.data.objects.new(prefixed(item["id"]), curve)
    obj.location = item.get("location", [0, 0, 0])
    obj.rotation_euler = Euler(tuple(math.radians(v) for v in item.get("rotation", [90, 0, 0])), "XYZ")
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.object
    obj.select_set(False)
    return obj


def build_empty(item: dict[str, Any]) -> bpy.types.Object:
    obj = bpy.data.objects.new(prefixed(item["id"]), None)
    obj.empty_display_type = str(item.get("displayType", "PLAIN_AXES"))
    obj.empty_display_size = float(item.get("displaySize", 0.02))
    obj.location = item.get("location", [0, 0, 0])
    obj.rotation_euler = Euler(tuple(math.radians(v) for v in item.get("rotation", [0, 0, 0])), "XYZ")
    bpy.context.scene.collection.objects.link(obj)
    return obj


BUILDERS = {
    "box": build_box,
    "cylinder": build_cylinder,
    "torus": build_torus,
    "sphere": build_sphere,
    "curve": build_curve,
    "text": build_text,
    "empty": build_empty,
}


def expanded_recipe(recipe: dict[str, Any]) -> list[dict[str, Any]]:
    objects = [dict(item) for item in recipe.get("objects", []) if isinstance(item, dict)]
    for repetition in recipe.get("repetitions", []):
        if not isinstance(repetition, dict):
            continue
        template = repetition.get("template")
        if not isinstance(template, dict):
            continue
        repetition_id = str(repetition.get("id", template.get("id", "repeat")))
        mode = repetition.get("mode", "points")
        if mode == "points":
            for index, point in enumerate(repetition.get("points", [])):
                item = dict(template)
                item["id"] = f"{repetition_id}_{index + 1:02d}"
                if isinstance(point, dict):
                    item.update(point)
                else:
                    item["location"] = point
                objects.append(item)
        elif mode == "linear":
            count = int(repetition.get("count", 0))
            start = Vector(repetition.get("start", [0, 0, 0]))
            step = Vector(repetition.get("step", [0, 0, 0]))
            for index in range(count):
                item = dict(template)
                item["id"] = f"{repetition_id}_{index + 1:02d}"
                item["location"] = list(start + step * index)
                objects.append(item)
        elif mode == "radial-x":
            count = int(repetition.get("count", 0))
            center = Vector(repetition.get("center", [0, 0, 0]))
            radius = float(repetition.get("radius", 0.01))
            phase = math.radians(float(repetition.get("phaseDegrees", 0)))
            for index in range(count):
                angle = phase + (2 * math.pi * index / count)
                item = dict(template)
                item["id"] = f"{repetition_id}_{index + 1:02d}"
                item["location"] = [
                    center.x,
                    center.y + math.cos(angle) * radius,
                    center.z + math.sin(angle) * radius,
                ]
                base_rotation = item.get("rotation", [0, 0, 0])
                item["rotation"] = [base_rotation[0] + math.degrees(angle), base_rotation[1], base_rotation[2]]
                objects.append(item)
    return objects


def assign_material(obj: bpy.types.Object, material: bpy.types.Material | None) -> None:
    if material is None or not hasattr(obj.data, "materials"):
        return
    obj.data.materials.append(material)


def build_recipe(
    spec: dict[str, Any],
    materials: dict[str, bpy.types.Material],
    asset_collection: bpy.types.Collection,
    tech_collection: bpy.types.Collection,
) -> dict[str, bpy.types.Object]:
    recipe = spec.get("blenderRecipe")
    if not isinstance(recipe, dict):
        raise RuntimeError("ObjectSculptSpec.blenderRecipe is required")
    objects: dict[str, bpy.types.Object] = {}
    root = bpy.data.objects.new(ROOT_NAME, None)
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = 0.03
    root["k3_component_id"] = "root"
    root["k3_source_spec"] = str(spec.get("targetName", "unknown"))
    asset_collection.objects.link(root)
    objects["root"] = root
    for item in expanded_recipe(recipe):
        item_id = str(item.get("id", "")).strip()
        kind = str(item.get("type", "")).strip()
        if not item_id or kind not in BUILDERS:
            raise RuntimeError(f"Invalid blenderRecipe object: id={item_id!r}, type={kind!r}")
        obj = BUILDERS[kind](item)
        obj.name = prefixed(item_id)
        is_technical = bool(item.get("technical", False))
        move_to_collection(obj, tech_collection if is_technical else asset_collection)
        assign_material(obj, materials.get(str(item.get("material", ""))))
        obj["k3_recipe_id"] = item_id
        obj["k3_component_id"] = str(item.get("component", item_id))
        obj["k3_semantic_role"] = str(item.get("role", "visual-part"))
        obj["k3_source_confidence"] = float(item.get("confidence", 0.7))
        obj["k3_hidden_side_inferred"] = bool(item.get("inferred", False))
        obj["k3_runtime_properties"] = json.dumps(item.get("runtimeProperties", {}), sort_keys=True)
        if is_technical:
            obj.hide_render = True
            obj.display_type = "WIRE"
        objects[item_id] = obj
    for item in expanded_recipe(recipe):
        item_id = str(item.get("id", "")).strip()
        parent_id = str(item.get("parent", "root"))
        if parent_id and parent_id in objects:
            objects[item_id].parent = objects[parent_id]
    root["k3_dimensions_m"] = json.dumps(recipe.get("dimensionsMeters", {}), sort_keys=True)
    root["k3_coordinate_frame"] = json.dumps(spec.get("coordinateFrame", {}), sort_keys=True)
    root["k3_source_limitations"] = json.dumps(spec.get("sourceLimitations", []), ensure_ascii=False)
    return objects


def create_light(
    role: str,
    light_type: str,
    location: tuple[float, float, float],
    energy: float,
    color: tuple[float, float, float],
    collection: bpy.types.Collection,
    size: float = 1.0,
) -> bpy.types.Object:
    data = bpy.data.lights.new(PREFIX + "LIGHT_DATA_" + role, type=light_type)
    data.energy = energy
    data.color = color
    if hasattr(data, "shape"):
        data.shape = "DISK"
    if hasattr(data, "size"):
        data.size = size
    obj = bpy.data.objects.new(PREFIX + "LIGHT_" + role, data)
    collection.objects.link(obj)
    obj.location = location
    obj["k3_light_role"] = role
    return obj


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def setup_shot(
    trial_root: Path,
    resolution: int,
    shot_collection: bpy.types.Collection,
    light_collection: bpy.types.Collection,
) -> tuple[bpy.types.Object, bpy.types.Object, dict[str, bpy.types.Object]]:
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    if hasattr(scene, "eevee"):
        scene.eevee.taa_render_samples = 128
        scene.eevee.use_taa_reprojection = True
    scene.render.resolution_x = resolution
    scene.render.resolution_y = round(resolution * 1.25)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.use_file_extension = True
    scene.render.fps = 24
    scene.frame_start = 1
    scene.frame_end = 192
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    scene.view_settings.exposure = -0.30
    scene.render.image_settings.color_mode = "RGBA"

    world = bpy.data.worlds.new(PREFIX + "WORLD")
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.12, 0.17, 0.21, 1.0)
    background.inputs["Strength"].default_value = 0.32
    scene.world = world

    ground = build_box(
        {
            "id": "GROUND",
            "size": [1.4, 1.4, 0.01],
            "location": [0, 0, -0.005],
            "bevel": 0.002,
        }
    )
    ground.name = PREFIX + "GROUND"
    move_to_collection(ground, shot_collection)
    ground["k3_semantic_role"] = "support-surface"

    ground_material = bpy.data.materials.new(PREFIX + "MAT_GROUND")
    ground_material.use_nodes = True
    ground_bsdf = ground_material.node_tree.nodes.get("Principled BSDF")
    set_input(ground_bsdf, ("Base Color",), (0.055, 0.075, 0.09, 1.0))
    set_input(ground_bsdf, ("Roughness",), 0.28)
    ground.data.materials.append(ground_material)

    target = bpy.data.objects.new(CAMERA_TARGET_NAME, None)
    target.empty_display_type = "SPHERE"
    target.empty_display_size = 0.012
    target.location = (0, 0, 0.122)
    shot_collection.objects.link(target)

    camera_data = bpy.data.cameras.new(PREFIX + "CAMERA_DATA")
    camera = bpy.data.objects.new(CAMERA_NAME, camera_data)
    shot_collection.objects.link(camera)
    camera.data.lens = 62
    camera.data.sensor_width = 36
    camera.data.dof.use_dof = True
    camera.data.dof.focus_object = target
    camera.data.dof.aperture_fstop = 7.1
    camera.location = (0.285, -0.49, 0.285)
    look_at(camera, target.location)
    scene.camera = camera

    lights: dict[str, bpy.types.Object] = {}
    lights["SUN_REFLECTION"] = create_light(
        "SUN_REFLECTION", "SUN", (-0.6, -0.7, 0.8), 1.15, (0.72, 0.86, 1.0), light_collection
    )
    lights["SUN_REFLECTION"].rotation_euler = Euler((math.radians(28), math.radians(-18), math.radians(-30)), "XYZ")
    lights["BACK_SHAPE"] = create_light(
        "BACK_SHAPE", "AREA", (-0.30, 0.26, 0.34), 420, (0.42, 0.68, 1.0), light_collection, 0.36
    )
    lights["SIDE_GLIMMER_A"] = create_light(
        "SIDE_GLIMMER_A", "AREA", (0.34, -0.15, 0.23), 3.0, (1.0, 0.24, 0.32), light_collection, 0.11
    )
    lights["SIDE_GLIMMER_B"] = create_light(
        "SIDE_GLIMMER_B", "AREA", (-0.30, -0.11, 0.16), 0.8, (0.30, 0.76, 1.0), light_collection, 0.13
    )
    lights["DETAIL_RETURN"] = create_light(
        "DETAIL_RETURN", "AREA", (0.02, -0.32, 0.34), 1.5, (0.80, 0.92, 1.0), light_collection, 0.30
    )
    for role, light in lights.items():
        if light.data.type != "SUN":
            look_at(light, target.location)

    scene["k3_trial_root"] = str(trial_root)
    scene["k3_lighting_style"] = "Drumboiii layered, recalibrated for 0.235 m transparent prop"
    return camera, target, lights


def set_camera_pose(camera: bpy.types.Object, target: bpy.types.Object, position: Iterable[float], lens: float) -> None:
    camera.location = position
    camera.data.lens = lens
    look_at(camera, target.location)


def render_still(scene: bpy.types.Scene, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def render_views(
    trial_root: Path,
    camera: bpy.types.Object,
    target: bpy.types.Object,
    resolution: int,
) -> list[dict[str, Any]]:
    scene = bpy.context.scene
    views = [
        ("hero", (0.285, -0.49, 0.285), 62),
        ("front", (0.0, -0.57, 0.145), 68),
        ("right", (0.46, -0.025, 0.165), 66),
        ("rear_three_quarter", (0.29, 0.47, 0.25), 64),
    ]
    output = []
    for view_id, position, lens in views:
        set_camera_pose(camera, target, position, lens)
        path = trial_root / "gates" / "views" / f"{view_id}.png"
        render_still(scene, path)
        output.append(
            {
                "id": view_id,
                "path": str(path.relative_to(trial_root)),
                "cameraPosition": list(position),
                "lensMm": lens,
                "resolution": [resolution, round(resolution * 1.25)],
            }
        )
    set_camera_pose(camera, target, views[0][1], views[0][2])
    return output


def render_clay_blockout(
    trial_root: Path,
    camera: bpy.types.Object,
    target: bpy.types.Object,
    asset_collection: bpy.types.Collection,
) -> Path:
    scene = bpy.context.scene
    material = bpy.data.materials.new(PREFIX + "MAT_BLOCKOUT_CLAY")
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    set_input(bsdf, ("Base Color",), (0.24, 0.34, 0.39, 1.0))
    set_input(bsdf, ("Roughness",), 0.62)
    originals: dict[str, list[bpy.types.Material]] = {}
    try:
        for obj in asset_collection.all_objects:
            if obj.type != "MESH":
                continue
            originals[obj.name] = list(obj.data.materials)
            obj.data.materials.clear()
            obj.data.materials.append(material)
        set_camera_pose(camera, target, (0.285, -0.49, 0.285), 62)
        path = trial_root / "gates" / "views" / "blockout-clay.png"
        render_still(scene, path)
        return path
    finally:
        for object_name, slots in originals.items():
            obj = bpy.data.objects.get(object_name)
            if obj is None or obj.type != "MESH":
                continue
            obj.data.materials.clear()
            for slot in slots:
                obj.data.materials.append(slot)


def render_reference_alignment(
    trial_root: Path,
    camera: bpy.types.Object,
    target: bpy.types.Object,
) -> Path:
    """Render a silhouette-comparison view without using it as physical proof."""
    scene = bpy.context.scene
    ground = bpy.data.objects.get(PREFIX + "GROUND")
    ground_hidden = ground.hide_render if ground else False
    background = scene.world.node_tree.nodes.get("Background")
    original_colour = tuple(background.inputs["Color"].default_value)
    original_strength = float(background.inputs["Strength"].default_value)
    try:
        if ground:
            ground.hide_render = True
        background.inputs["Color"].default_value = (0.22, 0.30, 0.34, 1.0)
        background.inputs["Strength"].default_value = 0.72
        camera.location = (0.356, -0.613, 0.326)
        base = (target.location - camera.location).to_track_quat("-Z", "Y")
        camera.rotation_euler = (base @ Quaternion((0.0, 0.0, 1.0), math.radians(26.0))).to_euler()
        camera.data.lens = 62
        path = trial_root / "gates" / "views" / "reference-aligned.png"
        render_still(scene, path)
        return path
    finally:
        if ground:
            ground.hide_render = ground_hidden
        background.inputs["Color"].default_value = original_colour
        background.inputs["Strength"].default_value = original_strength


def render_lighting_gate(
    trial_root: Path,
    camera: bpy.types.Object,
    target: bpy.types.Object,
    lights: dict[str, bpy.types.Object],
) -> dict[str, Any]:
    scene = bpy.context.scene
    set_camera_pose(camera, target, (0.285, -0.49, 0.285), 62)
    original_percentage = scene.render.resolution_percentage
    scene.render.resolution_percentage = 55
    stages: list[tuple[str, list[str]]] = [("00_BASE_WORLD", [])]
    enabled: list[str] = []
    for role in LIGHT_ROLES:
        enabled = [*enabled, role]
        stages.append((f"{len(enabled):02d}_{role}", list(enabled)))
    renders = []
    for label, active_roles in stages:
        for role, light in lights.items():
            light.hide_render = role not in active_roles
        path = trial_root / "gates" / "lighting" / f"{label}.png"
        render_still(scene, path)
        renders.append(
            {
                "stage": label,
                "enabled": active_roles,
                "path": str(path.relative_to(trial_root)),
            }
        )
    for light in lights.values():
        light.hide_render = False
    scene.render.resolution_percentage = original_percentage
    manifest = {
        "schema_version": 1,
        "workflow": "object-sculpt-spec-to-blender/drumboiii-lighting-gate",
        "created_at": utc_now(),
        "frame": 1,
        "engine": scene.render.engine,
        "order": list(LIGHT_ROLES),
        "principle": "world, reflection sun, shape backlight, two local glimmers, detail return",
        "renders": renders,
        "saved": True,
    }
    write_json(trial_root / "gates" / "lighting-gate-manifest.json", manifest)
    return manifest


def keyframe_camera_orbit(camera: bpy.types.Object, target: bpy.types.Object) -> list[dict[str, Any]]:
    keyframes = [
        (1, -30.0, 0.54, 0.285, "establish"),
        (25, -34.0, 0.54, 0.278, "anticipation"),
        (120, 30.0, 0.52, 0.245, "travel"),
        (165, 49.0, 0.54, 0.270, "overshoot"),
        (192, 43.0, 0.54, 0.260, "recovery"),
    ]
    manifest = []
    for frame, angle_degrees, distance, height, beat in keyframes:
        angle = math.radians(angle_degrees)
        camera.location = (
            math.sin(angle) * distance,
            -math.cos(angle) * distance,
            height,
        )
        look_at(camera, target.location)
        camera.keyframe_insert(data_path="location", frame=frame)
        camera.keyframe_insert(data_path="rotation_euler", frame=frame)
        manifest.append(
            {
                "frame": frame,
                "time_seconds": round((frame - 1) / 24, 3),
                "beat": beat,
                "angle_degrees": angle_degrees,
            }
        )
    # Blender 5.1 actions use layered channel bags; inserted keyframes already use
    # Bezier interpolation by default, so no legacy Action.fcurves mutation is needed.
    return manifest


def render_preview(trial_root: Path, resolution: int) -> None:
    scene = bpy.context.scene
    if hasattr(scene, "eevee"):
        scene.eevee.taa_render_samples = 32
    scene.render.resolution_x = min(resolution, 576)
    scene.render.resolution_y = round(scene.render.resolution_x * 1.25)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    frames_dir = trial_root / "renders" / ".preview-frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    source_frames = list(range(1, 193, 4))
    for index, source_frame in enumerate(source_frames, start=1):
        scene.frame_set(source_frame)
        scene.render.filepath = str(frames_dir / f"frame_{index:04d}.png")
        bpy.ops.render.render(write_still=True)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to encode renders/preview.mp4")
    output = trial_root / "renders" / "preview.mp4"
    command = [
        ffmpeg,
        "-y",
        "-loglevel",
        "error",
        "-framerate",
        "6",
        "-i",
        str(frames_dir / "frame_%04d.png"),
        "-r",
        "24",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-t",
        "8",
        str(output),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError("ffmpeg preview encode failed: " + result.stderr.strip())
    for frame in frames_dir.glob("frame_*.png"):
        frame.unlink()
    frames_dir.rmdir()
    scene.frame_set(1)


def evaluated_bounds(objects: Iterable[bpy.types.Object]) -> tuple[Vector, Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    minimum = Vector((math.inf, math.inf, math.inf))
    maximum = Vector((-math.inf, -math.inf, -math.inf))
    found = False
    for obj in objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            for vertex in mesh.vertices:
                world = evaluated.matrix_world @ vertex.co
                minimum.x = min(minimum.x, world.x)
                minimum.y = min(minimum.y, world.y)
                minimum.z = min(minimum.z, world.z)
                maximum.x = max(maximum.x, world.x)
                maximum.y = max(maximum.y, world.y)
                maximum.z = max(maximum.z, world.z)
                found = True
        finally:
            evaluated.to_mesh_clear()
    if not found:
        raise RuntimeError("No evaluated asset meshes found")
    return minimum, maximum


def export_glb(trial_root: Path, asset_collection: bpy.types.Collection) -> dict[str, Any]:
    output = trial_root / "scene" / "asset.glb"
    bpy.ops.object.select_all(action="DESELECT")
    selected = []
    for obj in asset_collection.all_objects:
        obj.select_set(True)
        selected.append(obj.name)
    kwargs = {
        "filepath": str(output),
        "export_format": "GLB",
        "use_selection": True,
        "export_apply": True,
        "export_cameras": False,
        "export_lights": False,
    }
    bpy.ops.export_scene.gltf(**kwargs)
    manifest = {
        "schema_version": 1,
        "workflow": "object-sculpt-spec-to-blender",
        "file": str(output.relative_to(trial_root)),
        "bytes": output.stat().st_size,
        "sha256": sha256(output),
        "collection": asset_collection.name,
        "objects": selected,
        "source": "scene/trial.blend",
    }
    write_json(trial_root / "scene" / "asset-manifest.json", manifest)
    return manifest


def write_diagnostics(
    trial_root: Path,
    spec: dict[str, Any],
    asset_collection: bpy.types.Collection,
    camera: bpy.types.Object,
    views: list[dict[str, Any]],
    export_manifest: dict[str, Any],
) -> None:
    asset_objects = list(asset_collection.all_objects)
    minimum, maximum = evaluated_bounds(asset_objects)
    mesh_objects = [obj for obj in asset_objects if obj.type == "MESH"]
    vertices = sum(len(obj.data.vertices) for obj in mesh_objects)
    polygons = sum(len(obj.data.polygons) for obj in mesh_objects)
    prefix_violations = [obj.name for obj in bpy.data.objects if not obj.name.startswith("K3_")]
    audit = {
        "schema_version": 1,
        "trial_id": trial_root.name,
        "status": "completed",
        "audited_at": utc_now(),
        "blender_version": bpy.app.version_string,
        "source_spec": "object-sculpt-spec.json",
        "source_target": spec.get("targetName"),
        "collections": [collection.name for collection in bpy.data.collections],
        "object_count": len(bpy.data.objects),
        "asset_object_count": len(asset_objects),
        "mesh_count": len(mesh_objects),
        "material_count": len(bpy.data.materials),
        "vertex_count": vertices,
        "polygon_count": polygons,
        "bounds_m": {
            "min": [round(value, 6) for value in minimum],
            "max": [round(value, 6) for value in maximum],
            "size": [round(value, 6) for value in (maximum - minimum)],
        },
        "prefix_violations": prefix_violations,
        "hidden_side_policy": "conservative inferred continuation; exact rear layout not claimed",
        "glb": export_manifest,
        "passed": not prefix_violations and len(mesh_objects) >= 20,
    }
    write_json(trial_root / "diagnostics" / "scene-audit.json", audit)

    ground_top = 0.0
    penetration = max(0.0, ground_top - minimum.z)
    support_gap = max(0.0, minimum.z - ground_top)
    camera_samples = []
    for frame in range(1, 193):
        bpy.context.scene.frame_set(frame)
        position = camera.matrix_world.translation
        closest = Vector(
            (
                min(max(position.x, minimum.x), maximum.x),
                min(max(position.y, minimum.y), maximum.y),
                min(max(position.z, minimum.z), maximum.z),
            )
        )
        camera_samples.append((frame, (position - closest).length))
    bpy.context.scene.frame_set(1)
    camera_worst_frame, camera_distance = min(camera_samples, key=lambda item: item[1])
    camera_outside = sum(1 for _, value in camera_samples if value < 0.08)
    support_evidence = ["gates/views/front.png", "diagnostics/scene-audit.json"]
    camera_evidence = ["gates/preview-keyframes.jpg", "shot-manifest.json"]
    physical = {
        "schema_version": 2,
        "trial_id": trial_root.name,
        "status": "completed",
        "passed": penetration <= 0.002 and support_gap <= 0.005 and camera_distance >= 0.08,
        "method": {
            "evaluated_geometry": True,
            "modifiers_and_armature_applied_in_evaluation": True,
            "coordinate_space": "Blender world, meters, +Z up, front -Y, right +X",
            "coordinate_space_source": "scene-contract.json and ObjectSculptSpec.coordinateFrame",
            "moving_parent_evaluated_each_frame": "not_applicable",
            "distance_method": "evaluated world-space asset AABB against z=0 support; camera point-to-AABB clearance sampled every frame",
            "overlap_method": "evaluated mesh vertices against support half-space; no other collision pairs",
            "frame_start": 1,
            "frame_end": 192,
            "sample_frame_step": 1,
        },
        "semantic_pairs": [
            {
                "subject": ROOT_NAME,
                "environment": PREFIX + "GROUND",
                "relationship": "required support contact without penetration",
            }
        ],
        "checks": {
            "environment_penetration": {
                "applicable": True,
                "passed": penetration <= 0.002,
                "value_m": round(penetration, 6),
                "operator": "<=",
                "threshold_m": 0.002,
                "worst_frame": 1,
                "frames_outside_threshold": 0,
                "evidence": support_evidence,
            },
            "support_gap": {
                "applicable": True,
                "passed": support_gap <= 0.005,
                "value_m": round(support_gap, 6),
                "operator": "<=",
                "threshold_m": 0.005,
                "worst_frame": 1,
                "frames_outside_threshold": 0,
                "evidence": support_evidence,
            },
            "planted_contact_drift": {
                "applicable": False,
                "not_applicable_reason": "The asset stays static; only the camera moves.",
            },
            "swing_clearance": {
                "applicable": False,
                "not_applicable_reason": "No articulated or swinging part is animated in this reconstruction trial.",
            },
            "camera_clearance": {
                "applicable": True,
                "passed": camera_distance >= 0.08,
                "value_m": round(camera_distance, 6),
                "operator": ">=",
                "threshold_m": 0.08,
                "worst_frame": camera_worst_frame,
                "frames_outside_threshold": camera_outside,
                "evidence": camera_evidence,
            },
        },
        "proof_views": [item["path"] for item in views],
        "critical_failures": [],
        "limitations": [
            "Support and penetration use evaluated bounds for this static prop; the check is not a triangle-pair collision solver.",
            "The rear and internal mechanical connectivity remain inferred from one reference view.",
        ],
    }
    write_json(trial_root / "diagnostics" / "physical-validation.json", physical)


def main() -> int:
    args = parse_args()
    spec_path = args.spec.expanduser().resolve()
    trial_root = args.trial_root.expanduser().resolve()
    if not spec_path.is_file():
        raise FileNotFoundError(spec_path)
    if spec_path.parent != trial_root:
        raise RuntimeError("The spec must live at the root of its isolated trial")
    if trial_root.parent.name != "kimi-k3-scene-trials":
        raise RuntimeError("trial-root must live directly under projects/kimi-k3-scene-trials")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    bpy.context.preferences.filepaths.save_version = 0

    for relative in ("scene", "diagnostics", "gates/views", "gates/lighting", "renders", "iterations"):
        (trial_root / relative).mkdir(parents=True, exist_ok=True)

    clear_scene()
    asset_collection = ensure_collection(ASSET_COLLECTION)
    tech_collection = ensure_collection(TECH_COLLECTION)
    shot_collection = ensure_collection(SHOT_COLLECTION)
    light_collection = ensure_collection(LIGHT_COLLECTION)
    materials = build_materials(spec)
    objects = build_recipe(spec, materials, asset_collection, tech_collection)
    camera, target, lights = setup_shot(trial_root, args.resolution, shot_collection, light_collection)
    views: list[dict[str, Any]] = []
    if args.render_gates:
        render_clay_blockout(trial_root, camera, target, asset_collection)
        views = render_views(trial_root, camera, target, args.resolution)
        render_reference_alignment(trial_root, camera, target)
        render_lighting_gate(trial_root, camera, target, lights)

    scene = bpy.context.scene
    scene.frame_set(1)
    set_camera_pose(camera, target, (0.285, -0.49, 0.285), 62)
    beats = keyframe_camera_orbit(camera, target)
    scene.frame_set(1)
    blend_path = trial_root / "scene" / "trial.blend"
    scene.render.filepath = str(trial_root / "renders" / "preview.mp4")
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
    export_manifest = export_glb(trial_root, asset_collection)

    if not views:
        views = [
            {
                "id": "pending",
                "path": "gates/views/hero.png",
                "cameraPosition": list(camera.location),
                "lensMm": camera.data.lens,
            }
        ]
    write_diagnostics(trial_root, spec, asset_collection, camera, views, export_manifest)
    write_json(
        trial_root / "shot-manifest.json",
        {
            "schema_version": 1,
            "trial_id": trial_root.name,
            "camera": CAMERA_NAME,
            "camera_target": CAMERA_TARGET_NAME,
            "fps": 24,
            "frame_start": 1,
            "frame_end": 192,
            "duration_seconds": 8,
            "move": "Drumboiii anticipation → arc travel → overshoot → recovery",
            "hero_views": views,
            "beats": beats,
            "object_motion": "static and supported; camera-only move",
        },
    )
    write_json(
        trial_root / "diagnostics" / "bridge-run.json",
        {
            "schema_version": 1,
            "status": "completed",
            "created_at": utc_now(),
            "workflow": "object-sculpt-spec-to-blender",
            "source_spec": str(spec_path),
            "blender_version": bpy.app.version_string,
            "objects_built": len(objects),
            "materials_built": len(materials),
            "blend": str(blend_path),
            "glb": export_manifest,
            "rendered_gates": args.render_gates,
            "rendered_preview": args.render_preview,
        },
    )
    if args.render_preview:
        render_preview(trial_root, args.resolution)
        scene.render.image_settings.file_format = "PNG"
        scene.render.resolution_x = args.resolution
        scene.render.resolution_y = round(args.resolution * 1.25)
        scene.frame_set(1)
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)

    print(
        "K3_RESULT="
        + json.dumps(
            {
                "trial": str(trial_root),
                "blend": str(blend_path),
                "glb": str(trial_root / "scene" / "asset.glb"),
                "objects": len(objects),
                "views": len(views),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
