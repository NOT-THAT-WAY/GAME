"""Build the isolated neutral composition handoff scene from the validated SB_Idle master.

No catalog workflow can be used directly here: the camera and lighting authoring workflows are
MCP-only, while studio_readiness_check reports the MCP port closed. This project-local batch script
therefore applies the same separation contract in a factory-startup Blender process. It opens the
declared source read-only and saves only the explicit output path passed after ``--``.

Usage:
  blender --background --factory-startup --python build_composition_scene.py -- \
    <source.blend> <output.blend> <scene-manifest.json>
"""

from __future__ import annotations

import bpy
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

from mathutils import Vector


PREFIX = "BAS_SANDBOX_CHARACTER_COMPOSITION_V001_"
STUDIO_ROOT = Path(__file__).resolve().parents[4]
EXPECTED_SOURCE_SHA256 = "864807e970705bf44a1c3dcbcfaac85102458917a5c8ccec90f5f36728590464"
EXPECTED_CHARACTER_OBJECTS = {
    "BAS_PUNCH_Body",
    "BAS_PUNCH_Fist_L",
    "BAS_PUNCH_Fist_R",
    "BAS_PUNCH_Foot_L",
    "BAS_PUNCH_Foot_R",
    "BAS_PUNCH_Forearm_L",
    "BAS_PUNCH_Forearm_R",
    "BAS_PUNCH_Rig",
    "BAS_PUNCH_UpperArm_L",
    "BAS_PUNCH_UpperArm_R",
}
EXPECTED_ACTIONS = {"SB_Idle", "BAS_PUNCH_Rig|BAS_PUNCH_Rig|BAS_PUNCH_punch"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def workspace_path(path: Path) -> str:
    return path.resolve().relative_to(STUDIO_ROOT).as_posix()


def all_fcurves(action):
    if hasattr(action, "fcurves"):
        return list(action.fcurves)
    curves = []
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in getattr(strip, "channelbags", []):
                curves.extend(channelbag.fcurves)
    return curves


def fingerprint_character() -> dict:
    objects = {}
    for name in sorted(EXPECTED_CHARACTER_OBJECTS):
        obj = bpy.data.objects[name]
        record = {
            "type": obj.type,
            "parent": obj.parent.name if obj.parent else None,
            "matrix_world": [round(value, 9) for row in obj.matrix_world for value in row],
            "modifiers": [[modifier.name, modifier.type] for modifier in obj.modifiers],
        }
        if obj.type == "MESH":
            record.update(
                vertices=len(obj.data.vertices),
                polygons=len(obj.data.polygons),
                materials=[slot.material.name if slot.material else None for slot in obj.material_slots],
            )
        elif obj.type == "ARMATURE":
            record.update(bones=[bone.name for bone in obj.data.bones])
        objects[name] = record
    actions = {}
    for name in sorted(EXPECTED_ACTIONS):
        action = bpy.data.actions[name]
        curves = all_fcurves(action)
        actions[name] = {
            "frame_range": [round(value, 6) for value in action.frame_range],
            "fcurves": len(curves),
            "keyframes": sum(len(curve.keyframe_points) for curve in curves),
        }
    return {"objects": objects, "actions": actions}


def new_collection(scene, suffix: str):
    collection = bpy.data.collections.new(PREFIX + suffix)
    scene.collection.children.link(collection)
    collection["bas_project_id"] = "sandbox-character-composition-v001"
    collection["runtime_export"] = False
    return collection


def link_exclusively(obj, collection, scene):
    if collection.objects.get(obj.name) is None:
        collection.objects.link(obj)
    for owner in list(obj.users_collection):
        if owner != collection:
            owner.objects.unlink(obj)
    if scene.collection.objects.get(obj.name) is not None:
        scene.collection.objects.unlink(obj)


def look_at(obj, point: Vector):
    direction = point - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_empty(collection, suffix: str, location, display_type="SPHERE", size=0.08):
    obj = bpy.data.objects.new(PREFIX + suffix, None)
    obj.location = location
    obj.empty_display_type = display_type
    obj.empty_display_size = size
    obj.hide_render = True
    obj["runtime_export"] = False
    collection.objects.link(obj)
    return obj


def add_camera(collection, suffix: str, location, target: Vector, lens=None, ortho_scale=None):
    data = bpy.data.cameras.new(PREFIX + suffix + "_DATA")
    data.sensor_width = 36.0
    data.clip_start = 0.1
    data.clip_end = 100.0
    if ortho_scale is not None:
        data.type = "ORTHO"
        data.ortho_scale = ortho_scale
    else:
        data.type = "PERSP"
        data.lens = float(lens)
    obj = bpy.data.objects.new(PREFIX + suffix, data)
    obj.location = location
    look_at(obj, target)
    obj["runtime_export"] = False
    collection.objects.link(obj)
    return obj


def add_area_light(collection, suffix: str, location, target: Vector, energy: float, size: float, color):
    data = bpy.data.lights.new(PREFIX + suffix + "_DATA", type="AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(PREFIX + suffix, data)
    obj.location = location
    look_at(obj, target)
    obj["lighting_role"] = suffix.lower()
    obj["runtime_export"] = False
    collection.objects.link(obj)
    return obj


def make_material(name: str, base_color, roughness: float, metallic: float = 0.0):
    material = bpy.data.materials.new(PREFIX + name)
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (*base_color, 1.0)
    principled.inputs["Roughness"].default_value = roughness
    principled.inputs["Metallic"].default_value = metallic
    return material


def build_cyclorama(collection):
    width = 6.0
    cross_section = [(-6.0, 0.0), (1.8, 0.0)]
    center_y, center_z, radius = 1.8, 1.0, 1.0
    for step in range(1, 13):
        theta = math.radians(-90.0 + 90.0 * step / 12.0)
        cross_section.append((center_y + radius * math.cos(theta), center_z + radius * math.sin(theta)))
    cross_section.append((2.8, 4.0))

    vertices = []
    for y, z in cross_section:
        vertices.extend([(-width, y, z), (width, y, z)])
    faces = []
    for index in range(len(cross_section) - 1):
        left = index * 2
        faces.append((left, left + 1, left + 3, left + 2))

    mesh = bpy.data.meshes.new(PREFIX + "STAGE_CYCLORAMA_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    obj = bpy.data.objects.new(PREFIX + "STAGE_CYCLORAMA", mesh)
    obj["support_plane_z"] = 0.0
    obj["runtime_export"] = False
    collection.objects.link(obj)
    obj.data.materials.append(make_material("MAT_STAGE", (0.075, 0.095, 0.135), 0.82))
    return obj


def configure_world_and_render(scene):
    world = bpy.data.worlds.new(PREFIX + "WORLD_NEUTRAL")
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.012, 0.020, 0.040, 1.0)
    background.inputs["Strength"].default_value = 0.22
    scene.world = world

    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 64
    scene.eevee.taa_samples = 32
    scene.eevee.use_shadows = True
    scene.eevee.use_fast_gi = True
    scene.eevee.gi_diffuse_bounces = 2
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 15
    scene.render.film_transparent = False
    scene.render.use_stamp = False
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) != 3:
        raise SystemExit("expected: <source.blend> <output.blend> <scene-manifest.json>")
    source, output, manifest_path = map(lambda value: Path(value).expanduser().resolve(), argv)
    if source == output:
        raise RuntimeError("output must not overwrite source")
    if sha256(source) != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("source hash mismatch")
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    scene = bpy.context.scene
    if scene.name != "SB_Idle" or scene.frame_start != 1 or scene.frame_end != 60 or scene.render.fps != 30:
        raise RuntimeError("unexpected source scene contract")
    if set(bpy.data.objects.keys()) != EXPECTED_CHARACTER_OBJECTS:
        raise RuntimeError("unexpected source object set")
    if not EXPECTED_ACTIONS.issubset(set(bpy.data.actions.keys())):
        raise RuntimeError("expected actions missing")
    source_fingerprint = fingerprint_character()

    scene.name = "BAS_SANDBOX_CHARACTER_COMPOSITION_V001_REVIEW"
    scene["bas_project_id"] = "sandbox-character-composition-v001"
    scene["bas_source_sha256"] = EXPECTED_SOURCE_SHA256
    scene["bas_status"] = "technical composition ready; creative art direction pending"
    scene["runtime_export"] = False

    character_collection = new_collection(scene, "CHARACTER_LOCKED")
    character_collection["edit_policy"] = "P0-P2 locked: do not alter mesh, rig, materials or actions"
    if hasattr(character_collection, "hide_select"):
        character_collection.hide_select = True
    for name in sorted(EXPECTED_CHARACTER_OBJECTS):
        link_exclusively(bpy.data.objects[name], character_collection, scene)

    stage_collection = new_collection(scene, "STAGE_EDITABLE")
    lighting_collection = new_collection(scene, "LIGHTING_EDITABLE")
    camera_collection = new_collection(scene, "CAMERAS_EDITABLE")
    guides_collection = new_collection(scene, "GUIDES")
    guides_collection.hide_render = True

    stage = build_cyclorama(stage_collection)
    target = add_empty(guides_collection, "TARGET_CHARACTER", (0.0, 0.0, 0.67), "SPHERE", 0.08)
    focus = add_empty(guides_collection, "FOCUS_FACE", (0.0, -0.44, 1.08), "CIRCLE", 0.08)

    hero = add_camera(
        camera_collection,
        "CAM_HERO_3Q",
        (2.55, -5.0, 1.78),
        target.location,
        lens=64.0,
    )
    hero.data.dof.use_dof = False
    hero.data.dof.focus_object = focus
    hero.data.dof.aperture_fstop = 5.6
    hero["composition_role"] = "neutral hero three-quarter; Claude may redesign after P0-P2 review"

    front = add_camera(
        camera_collection,
        "CAM_FRONT_ORTHO",
        (0.0, -6.0, 0.78),
        target.location,
        ortho_scale=1.72,
    )
    front["composition_role"] = "identity and silhouette control; keep available"
    profile = add_camera(
        camera_collection,
        "CAM_PROFILE_ORTHO",
        (6.0, 0.0, 0.78),
        target.location,
        ortho_scale=1.72,
    )
    profile["composition_role"] = "profile and contact control; keep available"

    light_target = Vector((0.0, -0.08, 0.92))
    add_area_light(
        lighting_collection,
        "LIGHT_KEY",
        (-1.8, -3.8, 4.0),
        light_target,
        480.0,
        4.2,
        (1.0, 0.94, 0.88),
    )
    add_area_light(
        lighting_collection,
        "LIGHT_FILL",
        (3.8, -2.4, 2.5),
        light_target,
        180.0,
        5.0,
        (0.76, 0.86, 1.0),
    )
    add_area_light(
        lighting_collection,
        "LIGHT_RIM",
        (1.6, 3.7, 3.4),
        light_target,
        320.0,
        3.2,
        (0.86, 0.93, 1.0),
    )

    configure_world_and_render(scene)
    scene.camera = hero
    scene.frame_set(1)

    handoff = bpy.data.texts.new(PREFIX + "CLAUDE_HANDOFF")
    handoff.write(
        "Creative handoff: CHARACTER_LOCKED and both Actions are P0-P2 invariants.\n"
        "Edit only STAGE_EDITABLE, LIGHTING_EDITABLE and CAMERAS_EDITABLE first.\n"
        "Keep CAM_FRONT_ORTHO and CAM_PROFILE_ORTHO as identity/contact controls.\n"
        "Do not enable DOF, bloom, grain or motion blur until composition and contact gates pass.\n"
        "See projects/team/sandbox-character-composition-v001/CLAUDE_CREATIVE_HANDOFF.md.\n"
    )

    if fingerprint_character() != source_fingerprint:
        raise RuntimeError("character fingerprint changed during composition build")

    bpy.ops.wm.save_as_mainfile(filepath=str(output), check_existing=False)
    output_hash = sha256(output)
    manifest = {
        "schema_version": 1,
        "project_id": "sandbox-character-composition-v001",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "execution_mode": "isolated batch",
        "source": {"path": workspace_path(source), "sha256": EXPECTED_SOURCE_SHA256, "overwritten": False},
        "output": {"path": workspace_path(output), "sha256": output_hash, "saved": True},
        "source_fingerprint_preserved": True,
        "scene": scene.name,
        "frame_range": [scene.frame_start, scene.frame_end],
        "fps": scene.render.fps / scene.render.fps_base,
        "collections": [collection.name for collection in scene.collection.children],
        "active_camera": {
            "name": hero.name,
            "type": hero.data.type,
            "lens_mm": hero.data.lens,
            "location_m": [round(value, 6) for value in hero.location],
            "target_m": [round(value, 6) for value in target.location],
            "dof_enabled": hero.data.dof.use_dof,
            "focus_object": focus.name,
        },
        "utility_cameras": [front.name, profile.name],
        "stage": {"name": stage.name, "support_plane_z": 0.0},
        "lights": [obj.name for obj in lighting_collection.objects if obj.type == "LIGHT"],
        "render": {
            "engine": scene.render.engine,
            "resolution": [scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage],
            "samples": scene.eevee.taa_render_samples,
            "view_transform": scene.view_settings.view_transform,
            "look": scene.view_settings.look,
            "file_format": scene.render.image_settings.file_format,
        },
        "runtime_export": False,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("COMPOSITION_SCENE_SAVED " + str(output))
    print("OUTPUT_SHA256 " + output_hash)


if __name__ == "__main__":
    main()
