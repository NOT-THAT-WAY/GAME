"""Create a namespaced, replaceable product-lighting rig without saving the blend file."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

P = globals().get("STUDIO_PARAMS", globals().get("UNRECORDED_PARAMS", {}))
scene = bpy.context.scene
# Validate external input before mutating the scene.
hdri_value = str(P.get("hdri_path", "")).strip()
resolved_hdri = None
if hdri_value:
    resolved_hdri = Path(bpy.path.abspath(hdri_value)).expanduser().resolve()
    if not resolved_hdri.is_file():
        raise RuntimeError("HDRI introuvable: " + str(resolved_hdri))

# Restore lights muted by a previous pass before rebuilding the rig.
for existing_light in [obj for obj in bpy.data.objects if obj.type == "LIGHT"]:
    for property_name in ("bas_previous_hide_render", "ustudio_previous_hide_render"):
        if property_name in existing_light:
            existing_light.hide_render = bool(existing_light[property_name])
            del existing_light[property_name]
collection_name = str(P.get("target_collection", "")).strip()
if collection_name:
    source = bpy.data.collections.get(collection_name)
    if not source:
        raise RuntimeError("Collection cible introuvable: " + collection_name)
    meshes = [obj for obj in source.all_objects if obj.type == "MESH" and not obj.hide_render]
else:
    meshes = [obj for obj in bpy.context.selected_objects if obj.type == "MESH" and not obj.hide_render]
    if not meshes:
        meshes = [obj for obj in scene.objects if obj.type == "MESH" and not obj.hide_render and not obj.name.lower().startswith(("ref_", "void_", "bas_", "ustudio_"))]
if not meshes:
    raise RuntimeError("Aucun mesh visible pour placer le rig lumière")

depsgraph = bpy.context.evaluated_depsgraph_get()
points = []
for obj in meshes:
    evaluated = obj.evaluated_get(depsgraph)
    points.extend(evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box)
low = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
high = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
center = (low + high) / 2
radius = max((high - low).length / 2, 0.5)
prefix = "BAS_LIGHTING"
old = bpy.data.collections.get(prefix)
if old:
    previous_world_name = old.get("bas_previous_world", "")
    generated_world_name = old.get("bas_generated_world", "")
    if previous_world_name and generated_world_name and scene.world and scene.world.name == generated_world_name:
        scene.world = bpy.data.worlds.get(previous_world_name)
    generated_world = bpy.data.worlds.get(generated_world_name) if generated_world_name else None
    for obj in list(old.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(old)
    if generated_world and generated_world.users == 0:
        bpy.data.worlds.remove(generated_world)
rig = bpy.data.collections.new(prefix)
scene.collection.children.link(rig)
target = bpy.data.objects.new(prefix + "_TARGET", None)
target.location = center
rig.objects.link(target)

intensity = float(P.get("intensity", 1.0))
preset = P.get("preset", "softbox-product")
distance_energy_scale = max(1.0, (radius / 4.0) ** 2)

def area(name, offset, energy, size, color, shape="DISK"):
    data = bpy.data.lights.new(prefix + "_" + name + "_DATA", "AREA")
    data.energy = energy * intensity * distance_energy_scale
    data.shape = shape
    data.size = size
    data.color = color
    if hasattr(data, "normalize"):
        data.normalize = True
    obj = bpy.data.objects.new(prefix + "_" + name, data)
    obj.location = center + Vector(offset) * radius
    rig.objects.link(obj)
    track = obj.constraints.new("TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"
    return obj

def sun(name, offset, energy, angle, color):
    data = bpy.data.lights.new(prefix + "_" + name + "_DATA", "SUN")
    data.energy = energy * intensity
    data.angle = angle
    data.color = color
    obj = bpy.data.objects.new(prefix + "_" + name, data)
    obj.location = center + Vector(offset) * radius
    rig.objects.link(obj)
    track = obj.constraints.new("TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"
    return obj

def configure_drumboiii_world():
    """Create a dedicated world; never clear the user's existing world node tree."""
    previous_world = scene.world
    world = bpy.data.worlds.new(prefix + "_DRUMBOIII_WORLD")
    try:
        scene.world = world
        world.use_nodes = True
        nodes = world.node_tree.nodes
        links = world.node_tree.links
        nodes.clear()

        output = nodes.new("ShaderNodeOutputWorld")
        output.name = prefix + "_WORLD_OUTPUT"
        mix = nodes.new("ShaderNodeMixShader")
        mix.name = prefix + "_CAMERA_RAY_MIX"
        light_path = nodes.new("ShaderNodeLightPath")
        light_path.name = prefix + "_LIGHT_PATH"

        lighting = nodes.new("ShaderNodeBackground")
        lighting.name = prefix + "_ENVIRONMENT_LIGHTING"
        lighting.inputs["Strength"].default_value = float(P.get("world_strength", 0.7))
        lighting.inputs["Color"].default_value = (0.055, 0.07, 0.10, 1.0)
        hdri_loaded = False
        if resolved_hdri:
            environment = nodes.new("ShaderNodeTexEnvironment")
            environment.name = prefix + "_HDRI"
            environment.image = bpy.data.images.load(str(resolved_hdri), check_existing=True)
            links.new(environment.outputs["Color"], lighting.inputs["Color"])
            hdri_loaded = True

        visible = nodes.new("ShaderNodeBackground")
        visible.name = prefix + "_VISIBLE_SKY"
        visible.inputs["Strength"].default_value = float(P.get("visible_world_strength", 0.35))
        sky = nodes.new("ShaderNodeTexSky")
        sky.name = prefix + "_VISIBLE_NISHITA_FALLBACK"
        sky_types = {item.identifier for item in sky.bl_rna.properties["sky_type"].enum_items}
        sky.sky_type = "NISHITA" if "NISHITA" in sky_types else "MULTIPLE_SCATTERING"
        for attribute, value in {
            "sun_elevation": 0.42,
            "sun_rotation": 2.2,
            "altitude": 0.1,
            "air_density": 1.15,
            "dust_density": 2.0,
        }.items():
            if hasattr(sky, attribute):
                setattr(sky, attribute, value)
        links.new(sky.outputs["Color"], visible.inputs["Color"])

        # Is Camera Ray = 0 uses environment lighting; camera rays use the visible sky.
        links.new(light_path.outputs["Is Camera Ray"], mix.inputs[0])
        links.new(lighting.outputs["Background"], mix.inputs[1])
        links.new(visible.outputs["Background"], mix.inputs[2])
        links.new(mix.outputs[0], output.inputs["Surface"])
        rig["bas_previous_world"] = previous_world.name if previous_world else ""
        rig["bas_generated_world"] = world.name
        return {
            "configured": True,
            "hdri_loaded": hdri_loaded,
            "strength": lighting.inputs["Strength"].default_value,
            "previous_world": previous_world.name if previous_world else None,
            "generated_world": world.name,
            "original_world_preserved": True,
        }
    except Exception:
        scene.world = previous_world
        bpy.data.worlds.remove(world)
        raise

world_result = {"configured": False, "hdri_loaded": False}

if preset == "three-point":
    area("KEY", (2.8, -3.2, 3.0), 900, radius * 2.0, (1.0, 0.93, 0.84))
    area("FILL", (-2.5, -1.5, 1.2), 350, radius * 2.5, (0.78, 0.88, 1.0))
    area("RIM", (0.5, 2.8, 3.2), 700, radius * 1.5, (0.75, 0.9, 1.0))
elif preset == "dark-rim":
    area("KEY", (3.0, -3.5, 2.0), 650, radius * 1.8, (0.88, 0.94, 1.0))
    area("RIM_L", (-2.8, 1.5, 2.2), 800, radius * 1.0, (0.25, 0.8, 1.0))
    area("RIM_R", (2.8, 1.5, 2.2), 800, radius * 1.0, (1.0, 0.28, 0.16))
elif preset == "drumboiii-layered":
    # Tutorial values were 1400/440/170/220 W on 1 m square emitters. Preserve
    # those ratios, scale for the subject, and place the rig camera-relatively.
    up = Vector((0.0, 0.0, 1.0))
    camera = scene.camera
    if camera:
        to_camera = camera.matrix_world.translation - center
        to_camera.z = 0.0
        if to_camera.length < 1e-5:
            to_camera = Vector((0.0, -1.0, 0.0))
        else:
            to_camera.normalize()
    else:
        to_camera = Vector((0.0, -1.0, 0.0))
    screen_right = to_camera.cross(up).normalized()
    neutral = (1.0, 1.0, 1.0)
    sun("SUN_REFLECTION", screen_right * 3.0 - to_camera * 1.5 + up * 1.2, 1.0, 0.035, neutral)
    area("BACK_SHAPE", -to_camera * 2.8 + up * 2.0, 1400, max(1.0, radius * 0.8), neutral, "SQUARE")
    area("SIDE_GLIMMER_A", screen_right * 2.6 - to_camera * 0.6 + up * 1.1, 440, max(1.0, radius * 0.8), neutral, "SQUARE")
    area("SIDE_GLIMMER_B", -screen_right * 2.4 - to_camera * 0.2 + up * 1.0, 170, max(1.0, radius * 0.8), neutral, "SQUARE")
    area("DETAIL_RETURN", screen_right * 1.0 + to_camera * 2.3 + up * 0.7, 220, max(1.0, radius * 0.8), neutral, "SQUARE")
    if bool(P.get("configure_world", True)):
        world_result = configure_drumboiii_world()
else:
    area("KEY", (3.2, -3.5, 3.5), 1000, radius * 3.0, (1.0, 0.95, 0.9))
    area("FILL", (-3.0, -1.5, 1.5), 450, radius * 3.5, (0.82, 0.9, 1.0))
    area("TOP", (0.0, 0.5, 4.0), 550, radius * 2.5, (1.0, 1.0, 1.0))

if bool(P.get("mute_existing_lights", True)):
    rig_lights = {obj.name for obj in rig.objects if obj.type == "LIGHT"}
    for existing_light in [obj for obj in scene.objects if obj.type == "LIGHT" and obj.name not in rig_lights]:
        existing_light["bas_previous_hide_render"] = bool(existing_light.hide_render)
        existing_light.hide_render = True

view = P.get("view_transform", "AgX")
try:
    scene.view_settings.view_transform = view
except Exception:
    pass
engine = str(P.get("render_engine", "KEEP"))
if engine != "KEEP":
    try:
        scene.render.engine = engine
    except Exception:
        pass
rig["bas_schema"] = 2
rig["bas_preset"] = preset
rig["bas_intensity"] = intensity
rig["bas_source_tutorial"] = "drumboii-lighting-tutorial-2026-07-20" if preset == "drumboiii-layered" else ""
print("UNRECORDED_RESULT=" + json.dumps({"workflow": "studio-lighting", "collection": rig.name, "preset": preset, "lights": [obj.name for obj in rig.objects if obj.type == "LIGHT"], "muted_existing_lights": bool(P.get("mute_existing_lights", True)), "target": list(center), "radius": radius, "evaluated_geometry": True, "energy_scale": distance_energy_scale, "world": world_result, "render_engine": scene.render.engine, "saved": False}))
