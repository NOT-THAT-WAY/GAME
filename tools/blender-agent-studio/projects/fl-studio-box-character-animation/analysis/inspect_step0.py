"""Read-only structural inspection for the FL Studio Box character-animation source."""
import bpy
import hashlib
import json
import math
import os
from pathlib import Path
from mathutils import Vector


output = Path(os.environ["USTUDIO_ANALYSIS_OUTPUT"]).expanduser().resolve()
source = Path(bpy.data.filepath).resolve()
scene = bpy.context.scene
depsgraph = bpy.context.evaluated_depsgraph_get()


def rounded(values, digits=6):
    return [round(float(value), digits) for value in values]


def custom_properties(block):
    result = {}
    for key in block.keys():
        if key == "_RNA_UI":
            continue
        value = block[key]
        if isinstance(value, (str, int, float, bool)) or value is None:
            result[key] = value
        else:
            try:
                result[key] = list(value)
            except Exception:
                result[key] = str(value)
    return result


def fcurves_for(action, slot=None):
    curves = []
    try:
        curves.extend(list(action.fcurves))
    except Exception:
        pass
    if curves:
        return curves
    for layer in getattr(action, "layers", []):
        for strip in getattr(layer, "strips", []):
            bags = list(getattr(strip, "channelbags", []))
            if slot is not None:
                bags = [bag for bag in bags if getattr(bag, "slot", None) == slot] or bags
            for bag in bags:
                curves.extend(list(getattr(bag, "fcurves", [])))
    unique = []
    seen = set()
    for curve in curves:
        pointer = curve.as_pointer()
        if pointer not in seen:
            seen.add(pointer)
            unique.append(curve)
    return unique


def animation_report(block):
    animation = getattr(block, "animation_data", None)
    action = animation.action if animation else None
    slot = getattr(animation, "action_slot", None) if animation else None
    if not action:
        return None
    channels = []
    for curve in fcurves_for(action, slot):
        channels.append({
            "data_path": curve.data_path,
            "array_index": curve.array_index,
            "keyframes": [
                {
                    "frame": round(float(point.co.x), 6),
                    "value": round(float(point.co.y), 6),
                    "interpolation": point.interpolation,
                }
                for point in curve.keyframe_points
            ],
        })
    return {
        "action": action.name,
        "slot": getattr(slot, "identifier", None),
        "frame_range": rounded(action.frame_range),
        "channels": channels,
    }


def object_report(obj):
    data = {
        "name": obj.name,
        "type": obj.type,
        "collections": sorted(collection.name for collection in obj.users_collection),
        "parent": obj.parent.name if obj.parent else None,
        "location": rounded(obj.location),
        "rotation_euler_deg": rounded(math.degrees(value) for value in obj.rotation_euler),
        "scale": rounded(obj.scale),
        "matrix_world_translation": rounded(obj.matrix_world.translation),
        "dimensions_world": rounded(obj.dimensions),
        "hide_viewport": obj.hide_viewport,
        "hide_render": obj.hide_render,
        "constraints": [
            {
                "name": constraint.name,
                "type": constraint.type,
                "target": getattr(getattr(constraint, "target", None), "name", None),
            }
            for constraint in obj.constraints
        ],
        "custom_properties": custom_properties(obj),
        "animation": animation_report(obj),
    }
    if obj.type == "CAMERA":
        data["camera"] = {
            "lens_mm": obj.data.lens,
            "sensor_width_mm": obj.data.sensor_width,
            "clip_start": obj.data.clip_start,
            "clip_end": obj.data.clip_end,
            "dof_enabled": obj.data.dof.use_dof,
            "focus_object": obj.data.dof.focus_object.name if obj.data.dof.focus_object else None,
            "fstop": obj.data.dof.aperture_fstop,
            "animation": animation_report(obj.data),
        }
    if obj.type == "LIGHT":
        data["light"] = {
            "light_type": obj.data.type,
            "energy": obj.data.energy,
            "color": rounded(obj.data.color),
            "size": getattr(obj.data, "size", None),
            "shadow_soft_size": getattr(obj.data, "shadow_soft_size", None),
        }
    if obj.type == "MESH":
        data["materials"] = [material.name if material else None for material in obj.data.materials]
        data["mesh"] = {
            "vertices": len(obj.data.vertices),
            "edges": len(obj.data.edges),
            "polygons": len(obj.data.polygons),
            "uv_layers": [layer.name for layer in obj.data.uv_layers],
        }
    return data


def local_bounds(objects, reference):
    inverse = reference.matrix_world.inverted_safe()
    points = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(depsgraph)
        matrix = inverse @ evaluated.matrix_world
        points.extend(matrix @ Vector(corner) for corner in evaluated.bound_box)
    if not points:
        return None
    low = Vector((min(point.x for point in points), min(point.y for point in points), min(point.z for point in points)))
    high = Vector((max(point.x for point in points), max(point.y for point in points), max(point.z for point in points)))
    return {"min": rounded(low), "max": rounded(high), "dimensions": rounded(high - low), "center": rounded((low + high) / 2)}


def mesh_vertices_in_reference(obj, reference):
    inverse = reference.matrix_world.inverted_safe()
    matrix = inverse @ obj.matrix_world
    return [matrix @ vertex.co for vertex in obj.data.vertices]


def sampled_state(frame):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    names = [
        "USTUDIO_BOX_FLOAT_ROOT",
        "USTUDIO_BOX_CAMERA",
        "USTUDIO_BOX_TARGET",
        "USTUDIO_PLAYHEAD_BACK",
        "USTUDIO_PLAYHEAD_FLOOR",
    ]
    state = {}
    for name in names:
        obj = bpy.data.objects.get(name)
        if not obj:
            continue
        item = {
            "location_local": rounded(obj.location),
            "rotation_local_deg": rounded(math.degrees(value) for value in obj.rotation_euler),
            "location_world": rounded(obj.matrix_world.translation),
        }
        if obj.type == "CAMERA":
            item["lens_mm"] = round(float(obj.data.lens), 6)
            item["fstop"] = round(float(obj.data.dof.aperture_fstop), 6)
        state[name] = item
    return state


root = bpy.data.objects.get("USTUDIO_BOX_FLOAT_ROOT")
if not root:
    raise RuntimeError("USTUDIO_BOX_FLOAT_ROOT missing")

collections = {}
for collection in bpy.data.collections:
    collections[collection.name] = {
        "objects_direct": sorted(obj.name for obj in collection.objects),
        "children": sorted(child.name for child in collection.children),
        "hide_viewport": collection.hide_viewport,
        "hide_render": collection.hide_render,
    }

markers = [{"name": marker.name, "frame": marker.frame, "seconds": round((marker.frame - scene.frame_start) / scene.render.fps, 6)} for marker in scene.timeline_markers]
marker_frames = sorted({marker["frame"] for marker in markers})
sampled = {str(frame): sampled_state(frame) for frame in marker_frames}

# Return to middle marker for stable geometric inspection.
middle = next((marker.frame for marker in scene.timeline_markers if marker.name == "USTUDIO_MEDIA_MIDDLE"), scene.frame_start)
scene.frame_set(middle)
bpy.context.view_layer.update()

shell_collection = bpy.data.collections.get("BOX_SHELL")
interior_collection = bpy.data.collections.get("FL_STUDIO_INTERIOR")
motion_collection = bpy.data.collections.get("PLAYBACK_MOTION")
shell_objects = list(shell_collection.all_objects) if shell_collection else []
interior_objects = list(interior_collection.all_objects) if interior_collection else []
motion_objects = list(motion_collection.all_objects) if motion_collection else []
shell_without_ground = [obj for obj in shell_objects if obj.name != "USTUDIO_GROUND"]

floor = bpy.data.objects.get("USTUDIO_PIANO_ROLL_FLOOR")
ceiling = bpy.data.objects.get("USTUDIO_CEILING")
geometry = {
    "shell_local_to_float_root": local_bounds(shell_without_ground, root),
    "interior_panels_local_to_float_root": local_bounds(interior_objects, root),
    "playback_local_to_float_root": local_bounds(motion_objects, root),
}
if floor and floor.type == "MESH":
    vertices = mesh_vertices_in_reference(floor, root)
    if len(vertices) >= 3:
        normal = (vertices[1] - vertices[0]).cross(vertices[-1] - vertices[0]).normalized()
        if normal.z < 0:
            normal.negate()
        slope = math.degrees(math.acos(max(-1.0, min(1.0, normal.dot(Vector((0, 0, 1)))))))
        geometry["piano_roll_floor"] = {
            "vertices_local": [rounded(vertex) for vertex in vertices],
            "normal_local": rounded(normal),
            "slope_from_horizontal_deg": round(slope, 6),
            "friction_coefficient_min_static": round(math.tan(math.radians(slope)), 6),
            "center_local": rounded(sum(vertices, Vector()) / len(vertices)),
        }
if ceiling and floor and geometry.get("piano_roll_floor"):
    ceiling_bounds = local_bounds([ceiling], root)
    floor_center_z = geometry["piano_roll_floor"]["center_local"][2]
    usable_center_height = ceiling_bounds["min"][2] - floor_center_z
    geometry["usable_center_height_m"] = round(usable_center_height, 6)
    geometry["requested_character_height_range_m"] = [round(usable_center_height / 15, 6), round(usable_center_height / 10, 6)]

images = []
for image in bpy.data.images:
    images.append({
        "name": image.name,
        "source": image.source,
        "filepath": image.filepath,
        "absolute_path": bpy.path.abspath(image.filepath),
        "exists": Path(bpy.path.abspath(image.filepath)).exists() if image.filepath else None,
        "size": list(image.size),
    })

materials = []
for material in bpy.data.materials:
    movie_nodes = []
    if material.node_tree:
        for node in material.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image:
                movie_nodes.append({
                    "node": node.name,
                    "image": node.image.name,
                    "frame_start": node.image_user.frame_start,
                    "frame_duration": node.image_user.frame_duration,
                    "cyclic": node.image_user.use_cyclic,
                    "auto_refresh": node.image_user.use_auto_refresh,
                })
    materials.append({
        "name": material.name,
        "movie_nodes": movie_nodes,
        "node_tree_animation": animation_report(material.node_tree) if material.node_tree else None,
    })

report = {
    "schema_version": 1,
    "source": str(source),
    "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "read_only": True,
    "blender_version": bpy.app.version_string,
    "scene": {
        "name": scene.name,
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end,
        "fps": scene.render.fps / scene.render.fps_base,
        "duration_seconds": (scene.frame_end - scene.frame_start + 1) / (scene.render.fps / scene.render.fps_base),
        "resolution": [scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage],
        "engine": scene.render.engine,
        "active_camera": scene.camera.name if scene.camera else None,
        "units": {"system": scene.unit_settings.system, "scale_length": scene.unit_settings.scale_length, "length_unit": scene.unit_settings.length_unit},
        "view": {"transform": scene.view_settings.view_transform, "look": scene.view_settings.look, "exposure": scene.view_settings.exposure},
        "custom_properties": custom_properties(scene),
    },
    "markers": markers,
    "collections": collections,
    "objects": [object_report(obj) for obj in sorted(scene.objects, key=lambda item: item.name)],
    "geometry": geometry,
    "sampled_marker_states": sampled,
    "images": images,
    "materials": materials,
    "actions": [
        {
            "name": action.name,
            "frame_range": rounded(action.frame_range),
            "slots": [slot.identifier for slot in getattr(action, "slots", [])],
            "users": action.users,
        }
        for action in bpy.data.actions
    ],
}
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("USTUDIO_STEP0=" + json.dumps({
    "output": str(output),
    "objects": len(report["objects"]),
    "collections": len(report["collections"]),
    "markers": len(markers),
    "actions": len(report["actions"]),
    "read_only": True,
}))
