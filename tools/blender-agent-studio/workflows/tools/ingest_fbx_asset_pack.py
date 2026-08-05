"""Import an FBX folder as curated Blender collection assets and emit a deep audit."""
import bpy
import json
import math
import os
import sys
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "asset_sources" / "drumboii-y2k" / "fbx"
PREVIEWS = ROOT / "asset_sources" / "drumboii-y2k" / "previews"
OUTPUT = ROOT / "asset_library" / "imported" / "drumboii-y2k-assets.blend"
MANIFEST = OUTPUT.with_suffix(".manifest.json")
AUDIT = ROOT / "asset_sources" / "drumboii-y2k" / "audit.json"
CATALOG_ID = "fb2a13fe-2b45-4d99-9cdc-e0cd819f72df"

PREVIEWS.mkdir(parents=True, exist_ok=True)
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for collection in list(bpy.data.collections):
    bpy.data.collections.remove(collection)

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 640
scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = True
scene.display.shading.light = "STUDIO"
scene.display.shading.studio_light = "paint.sl"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = "BOTH"

camera_data = bpy.data.cameras.new("USTUDIO_AUDIT_CAMERA_DATA")
camera = bpy.data.objects.new("USTUDIO_AUDIT_CAMERA", camera_data)
scene.collection.objects.link(camera)
camera_data.lens = 58
scene.camera = camera


def safe_name(path):
    return path.stem.upper().replace(" ", "_").replace("-", "_")


def bounds(objects):
    points = [obj.matrix_world @ Vector(corner) for obj in objects if obj.type == "MESH" for corner in obj.bound_box]
    if not points:
        return Vector((-1, -1, -1)), Vector((1, 1, 1))
    minimum = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    maximum = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return minimum, maximum


def camera_to(minimum, maximum):
    center = (minimum + maximum) / 2
    size = maximum - minimum
    radius = max(size.length / 2, 0.1)
    camera.location = center + Vector((1.35, -1.8, 1.05)).normalized() * radius * 3.1
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.clip_start = max(radius / 1000, 0.001)
    camera.data.clip_end = max(radius * 20, 1000)
    return center, radius


assets = []
all_asset_objects = []
for fbx in sorted(SOURCE.glob("*.fbx")):
    prefix = safe_name(fbx)
    before_objects = set(bpy.data.objects)
    before_materials = set(bpy.data.materials)
    before_meshes = set(bpy.data.meshes)
    before_images = set(bpy.data.images)
    bpy.ops.wm.fbx_import(filepath=str(fbx))
    imported = [obj for obj in bpy.data.objects if obj not in before_objects]
    new_materials = [item for item in bpy.data.materials if item not in before_materials]
    new_meshes = [item for item in bpy.data.meshes if item not in before_meshes]
    new_images = [item for item in bpy.data.images if item not in before_images]
    if not imported:
        raise RuntimeError("FBX vide ou non importé: " + fbx.name)

    collection = bpy.data.collections.new(prefix)
    scene.collection.children.link(collection)
    for obj in imported:
        for owner in list(obj.users_collection):
            owner.objects.unlink(obj)
        collection.objects.link(obj)
        obj["ustudio_source_fbx"] = fbx.name
    for mesh in new_meshes:
        if not mesh.name.startswith(prefix + "_"):
            mesh.name = prefix + "_" + mesh.name
    for material in new_materials:
        if not material.name.startswith(prefix + "_"):
            material.name = prefix + "_" + material.name
    for image in new_images:
        if not image.name.startswith(prefix + "_"):
            image.name = prefix + "_" + image.name

    mesh_objects = [obj for obj in imported if obj.type == "MESH"]
    minimum, maximum = bounds(mesh_objects)
    center, radius = camera_to(minimum, maximum)
    collection["ustudio_schema"] = 1
    collection["ustudio_source"] = fbx.name
    collection["ustudio_radius"] = radius
    collection.asset_mark()
    collection.asset_data.author = "DRUMBOII / ingested by Unrecorded"
    collection.asset_data.description = f"{fbx.stem} — FBX source preserved; collection import audited in Blender 5.1"
    collection.asset_data.catalog_id = CATALOG_ID
    for tag in ("drumboii", "y2k", "fbx", "prop"):
        collection.asset_data.tags.new(tag)

    for obj in all_asset_objects:
        obj.hide_render = True
    for obj in imported:
        obj.hide_render = False
    preview = PREVIEWS / (prefix.lower() + ".png")
    scene.render.filepath = str(preview)
    bpy.ops.render.render(write_still=True)

    images = []
    for image in new_images:
        absolute = bpy.path.abspath(image.filepath) if image.filepath else ""
        images.append({
            "name": image.name,
            "filepath": image.filepath,
            "absolute_path": absolute,
            "exists": bool(absolute and os.path.exists(absolute)),
            "packed": bool(image.packed_file),
            "size": list(image.size),
        })
    material_details = []
    for material in new_materials:
        has_nodes = material.node_tree is not None
        material_details.append({
            "name": material.name,
            "diffuse_color": list(material.diffuse_color),
            "metallic": float(material.metallic),
            "roughness": float(material.roughness),
            "use_nodes": has_nodes,
            "node_types": sorted({node.bl_idname for node in material.node_tree.nodes}) if has_nodes else [],
        })
    non_unit_scale = [obj.name for obj in imported if any(abs(float(value) - 1.0) > 1e-5 for value in obj.scale)]
    entry = {
        "name": collection.name,
        "type": "collection",
        "catalog": "Props/DRUMBOII Y2K",
        "source": str(fbx.relative_to(ROOT)),
        "preview": str(preview.relative_to(ROOT)),
        "object_count": len(imported),
        "mesh_count": len(mesh_objects),
        "vertices": sum(len(obj.data.vertices) for obj in mesh_objects),
        "polygons": sum(len(obj.data.polygons) for obj in mesh_objects),
        "materials": [material.name for material in new_materials],
        "material_details": material_details,
        "images": images,
        "bounds": {"min": list(minimum), "max": list(maximum), "center": list(center), "radius": radius},
        "objects": [{
            "name": obj.name,
            "type": obj.type,
            "parent": obj.parent.name if obj.parent else None,
            "scale": list(obj.scale),
            "rotation": list(obj.rotation_euler),
            "modifiers": [mod.type for mod in obj.modifiers],
        } for obj in imported],
        "root_objects": [obj.name for obj in imported if obj.parent is None],
        "warnings": {
            "non_unit_scale": non_unit_scale,
            "high_poly": sum(len(obj.data.polygons) for obj in mesh_objects) > 50000,
            "image_textures_absent": len(new_images) == 0,
        },
        "usage": "Append (Reuse Data) for local shots; Link for a centrally updated library",
    }
    assets.append(entry)
    all_asset_objects.extend(imported)

for obj in all_asset_objects:
    obj.hide_render = False
camera.hide_render = True

payload = {
    "schema_version": 1,
    "version": "1.0.0",
    "blender_version": bpy.app.version_string,
    "source_directory": str(SOURCE.relative_to(ROOT)),
    "asset_count": len(assets),
    "total_vertices": sum(asset["vertices"] for asset in assets),
    "total_polygons": sum(asset["polygons"] for asset in assets),
    "assets": assets,
}
AUDIT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT), compress=True, relative_remap=True)
print("UNRECORDED_FBX_PACK=" + json.dumps({"file": str(OUTPUT), "audit": str(AUDIT), "assets": len(assets)}, ensure_ascii=False))
