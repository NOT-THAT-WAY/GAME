"""Production-oriented, read-only audit of the active Blender file."""
import bpy
import bmesh
import json
import os
from pathlib import Path

P = globals().get("STUDIO_PARAMS", globals().get("UNRECORDED_PARAMS", {}))
output_dir = Path(P["output_dir"])
output_dir.mkdir(parents=True, exist_ok=True)
include_nodes = bool(P.get("include_nodes", True))
include_geometry_checks = bool(P.get("include_geometry_checks", True))


def rounded(values):
    return [round(float(value), 5) for value in values]


def animation_summary(owner):
    data = getattr(owner, "animation_data", None)
    action = getattr(data, "action", None) if data else None
    if not action:
        return None
    layers = getattr(action, "layers", [])
    slots = getattr(action, "slots", [])
    fcurves = list(getattr(action, "fcurves", []))
    if not fcurves:
        for layer in getattr(action, "layers", []):
            for strip in layer.strips:
                for channelbag in strip.channelbags:
                    fcurves.extend(channelbag.fcurves)
    return {
        "action": action.name,
        "frame_range": rounded(action.frame_range),
        "fcurves": len(fcurves),
        "layers": len(layers),
        "slots": len(slots),
    }


objects = []
geometry_issues = {}
for obj in bpy.data.objects:
    entry = {
        "name": obj.name,
        "type": obj.type,
        "collections": [collection.name for collection in obj.users_collection],
        "location": rounded(obj.location),
        "rotation_euler": rounded(obj.rotation_euler),
        "scale": rounded(obj.scale),
        "dimensions": rounded(obj.dimensions),
        "parent": obj.parent.name if obj.parent else None,
        "hidden_viewport": bool(obj.hide_viewport),
        "hidden_render": bool(obj.hide_render),
        "modifiers": [{"name": mod.name, "type": mod.type} for mod in obj.modifiers],
        "constraints": [{"name": con.name, "type": con.type, "target": getattr(getattr(con, "target", None), "name", None)} for con in obj.constraints],
        "materials": [slot.material.name if slot.material else None for slot in obj.material_slots],
        "animation": animation_summary(obj),
        "custom_properties": sorted(key for key in obj.keys() if key != "_RNA_UI"),
    }
    if obj.type == "MESH":
        mesh = obj.data
        entry["geometry"] = {
            "mesh": mesh.name,
            "vertices": len(mesh.vertices),
            "edges": len(mesh.edges),
            "polygons": len(mesh.polygons),
            "uv_layers": [layer.name for layer in mesh.uv_layers],
            "shape_keys": list(mesh.shape_keys.key_blocks.keys()) if mesh.shape_keys else [],
        }
        if include_geometry_checks:
            bm = bmesh.new()
            try:
                bm.from_mesh(mesh)
                bm.normal_update()
                loose_vertices = sum(1 for vertex in bm.verts if not vertex.link_edges)
                loose_edges = sum(1 for edge in bm.edges if not edge.link_faces)
                non_manifold_edges = sum(1 for edge in bm.edges if not edge.is_manifold)
                degenerate_faces = sum(1 for face in bm.faces if face.calc_area() <= 1e-12)
                diagnostics = {
                    "loose_vertices": loose_vertices,
                    "loose_edges": loose_edges,
                    "boundary_edges": sum(1 for edge in bm.edges if edge.is_boundary),
                    "non_manifold_edges": non_manifold_edges,
                    "degenerate_faces": degenerate_faces,
                    "ngons": sum(1 for face in bm.faces if len(face.verts) > 4),
                    "triangles": sum(1 for face in bm.faces if len(face.verts) == 3),
                    "negative_determinant": obj.matrix_world.to_3x3().determinant() < 0,
                    "unapplied_scale": any(abs(value - 1.0) > 1e-5 for value in obj.scale),
                    "missing_uv": len(mesh.uv_layers) == 0,
                    "missing_material": len(obj.material_slots) == 0,
                }
                entry["geometry_diagnostics"] = diagnostics
                if any((loose_vertices, loose_edges, non_manifold_edges, degenerate_faces)) or diagnostics["negative_determinant"]:
                    geometry_issues[obj.name] = diagnostics
            finally:
                bm.free()
    elif obj.type == "CAMERA":
        camera = obj.data
        entry["camera"] = {
            "type": camera.type,
            "lens": camera.lens,
            "sensor_width": camera.sensor_width,
            "clip": [camera.clip_start, camera.clip_end],
            "dof": bool(camera.dof.use_dof),
            "focus_object": camera.dof.focus_object.name if camera.dof.focus_object else None,
        }
    elif obj.type == "LIGHT":
        light = obj.data
        entry["light"] = {"type": light.type, "energy": light.energy, "color": rounded(light.color)}
    objects.append(entry)

materials = []
for material in bpy.data.materials:
    nodes = []
    if include_nodes and material.use_nodes and material.node_tree:
        for node in material.node_tree.nodes:
            nodes.append({"name": node.name, "type": node.bl_idname, "label": node.label})
    materials.append({
        "name": material.name,
        "users": material.users,
        "asset": bool(material.asset_data),
        "blend_method": getattr(material.surface_render_method, "name", str(material.surface_render_method)) if hasattr(material, "surface_render_method") else None,
        "nodes": nodes,
    })

images = []
missing_images = []
for image in bpy.data.images:
    absolute = bpy.path.abspath(image.filepath) if image.filepath else ""
    exists = bool(absolute and os.path.exists(absolute))
    entry = {
        "name": image.name,
        "source": image.source,
        "filepath": image.filepath,
        "absolute_path": absolute,
        "packed": bool(image.packed_file),
        "exists": exists or bool(image.packed_file) or image.source == "GENERATED",
        "size": list(image.size),
        "colorspace": image.colorspace_settings.name,
    }
    images.append(entry)
    if not entry["exists"]:
        missing_images.append(image.name)

asset_blocks = []
for group_name in ("collections", "objects", "materials", "worlds", "node_groups", "actions"):
    for datablock in getattr(bpy.data, group_name):
        if getattr(datablock, "asset_data", None):
            asset_blocks.append({
                "type": group_name,
                "name": datablock.name,
                "description": datablock.asset_data.description,
                "author": datablock.asset_data.author,
                "catalog_id": str(datablock.asset_data.catalog_id),
                "tags": [tag.name for tag in datablock.asset_data.tags],
            })

scenes = []
for scene in bpy.data.scenes:
    scenes.append({
        "name": scene.name,
        "active": scene == bpy.context.scene,
        "objects": len(scene.objects),
        "camera": scene.camera.name if scene.camera else None,
        "frame_range": [scene.frame_start, scene.frame_end],
        "fps": scene.render.fps / scene.render.fps_base,
        "engine": scene.render.engine,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage],
        "pixel_aspect": [scene.render.pixel_aspect_x, scene.render.pixel_aspect_y],
        "film_transparent": scene.render.film_transparent,
        "filepath": scene.render.filepath,
        "file_format": scene.render.image_settings.file_format,
        "view_transform": scene.view_settings.view_transform,
        "look": scene.view_settings.look,
        "exposure": scene.view_settings.exposure,
        "gamma": scene.view_settings.gamma,
        "units": {
            "system": scene.unit_settings.system,
            "scale_length": scene.unit_settings.scale_length,
            "length_unit": scene.unit_settings.length_unit,
        },
        "markers": [{"name": marker.name, "frame": marker.frame} for marker in scene.timeline_markers],
    })

payload = {
    "schema_version": 2,
    "file": bpy.data.filepath,
    "blender_version": bpy.app.version_string,
    "saved": not bpy.data.is_dirty,
    "active_scene": bpy.context.scene.name,
    "summary": {
        "scenes": len(bpy.data.scenes),
        "objects": len(objects),
        "meshes": len(bpy.data.meshes),
        "materials": len(materials),
        "images": len(images),
        "missing_images": len(missing_images),
        "asset_blocks": len(asset_blocks),
        "external_libraries": len(bpy.data.libraries),
        "geometry_issue_objects": len(geometry_issues),
    },
    "scenes": scenes,
    "collections": [{"name": collection.name, "objects": len(collection.objects), "children": [child.name for child in collection.children], "asset": bool(collection.asset_data)} for collection in bpy.data.collections],
    "objects": objects,
    "materials": materials,
    "images": images,
    "assets": asset_blocks,
    "external_libraries": [{"name": library.name, "filepath": library.filepath} for library in bpy.data.libraries],
    "issues": {
        "missing_images": missing_images,
        "objects_with_unapplied_scale": [obj.name for obj in bpy.data.objects if obj.type == "MESH" and any(abs(value - 1.0) > 1e-5 for value in obj.scale)],
        "unnamed_objects": [obj.name for obj in bpy.data.objects if obj.name.startswith(("Cube", "Camera", "Light"))],
        "geometry": geometry_issues,
        "scenes_without_camera": [scene.name for scene in bpy.data.scenes if not scene.camera],
        "scenes_without_units": [scene.name for scene in bpy.data.scenes if scene.unit_settings.system == "NONE"],
    },
}

json_path = output_dir / "scene-audit.json"
json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
summary = payload["summary"]
md = f"""# Audit de production Blender

- Fichier: `{payload['file']}`
- Blender: {payload['blender_version']}
- Scène active: `{payload['active_scene']}`
- Objets: {summary['objects']}
- Meshes: {summary['meshes']}
- Matériaux: {summary['materials']}
- Images manquantes: {summary['missing_images']}
- Objets avec alertes géométriques: {summary['geometry_issue_objects']}
- Assets marqués: {summary['asset_blocks']}
- Bibliothèques externes: {summary['external_libraries']}

Le détail exploitable par un agent se trouve dans `scene-audit.json`.
"""
(output_dir / "README.md").write_text(md, encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps({"audit": str(json_path), "summary": summary, "saved": False}, ensure_ascii=False))
