"""Stage the ingested DRUMBOII GAMEBOII in a reusable Y2K arcade environment."""
import bpy
import json
import math
import time
from datetime import datetime
from pathlib import Path
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
ASSET_LIBRARY = ROOT / "asset_library" / "imported" / "drumboii-y2k-assets.blend"
ASSET_NAME = "DRUMBOII_GAMEBOII"
PROJECT_DIR = ROOT / "projects" / "drumboii-gameboii-arcade-scene"
PROJECT_FILE = PROJECT_DIR / "Drumboii_Gameboii_Arcade_Scene.blend"
GATE_DIR = PROJECT_DIR / "gate"
MANIFEST_FILE = PROJECT_DIR / "environment-manifest.json"


def make_material(name, color, metallic=0.0, roughness=0.35, emission=None, strength=0.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission:
        color_input = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        strength_input = bsdf.inputs.get("Emission Strength")
        if color_input:
            color_input.default_value = emission
        if strength_input:
            strength_input.default_value = strength
    return material


def move_to_collection(obj, collection):
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    collection.objects.link(obj)


def empty(collection, name, location, display="PLAIN_AXES", size=0.14):
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    obj.empty_display_type = display
    obj.empty_display_size = size
    collection.objects.link(obj)
    return obj


def bounds(objects):
    points = [obj.matrix_world @ Vector(corner) for obj in objects if obj.type == "MESH" for corner in obj.bound_box]
    minimum = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    maximum = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return minimum, maximum


def tracked_area(collection, name, location, energy, size, color, target):
    data = bpy.data.lights.new(name + "_DATA", "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    collection.objects.link(obj)
    constraint = obj.constraints.new("TRACK_TO")
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


def cube(collection, name, location, scale, material, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(obj, collection)
    obj.data.materials.append(material)
    if bevel:
        modifier = obj.modifiers.new("USTUDIO_BEVEL", "BEVEL")
        modifier.width = bevel
        modifier.segments = 4
    return obj


PROJECT_DIR.mkdir(parents=True, exist_ok=True)
GATE_DIR.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)

scene = bpy.context.scene
scene.name = "GAMEBOII_ARCADE_HERO"
scene.frame_start = 1
scene.frame_end = 120
scene.render.fps = 24
scene.render.resolution_x = 720
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.render.film_transparent = False
scene.view_settings.look = "AgX - Medium High Contrast"

world = bpy.data.worlds.new("USTUDIO_ARCADE_WORLD")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.002, 0.003, 0.012, 1.0)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.08
scene.world = world

product_controls = bpy.data.collections.new("PRODUCT_CONTROLS")
environment = bpy.data.collections.new("ENVIRONMENT_ARCADE")
lighting = bpy.data.collections.new("LIGHTING_ROLES")
camera_rig = bpy.data.collections.new("CAMERA_RIG")
for collection in (product_controls, environment, lighting, camera_rig):
    scene.collection.children.link(collection)

with bpy.data.libraries.load(str(ASSET_LIBRARY), link=False) as (data_from, data_to):
    if ASSET_NAME not in data_from.collections:
        raise RuntimeError(f"Asset collection missing: {ASSET_NAME}")
    data_to.collections = [ASSET_NAME]

product_collection = bpy.data.collections.get(ASSET_NAME)
product_collection.name = "PRODUCT_GAMEBOII"
product_collection["ustudio_source_library"] = str(ASSET_LIBRARY.relative_to(ROOT))
product_collection["ustudio_source_asset"] = ASSET_NAME
scene.collection.children.link(product_collection)

product_objects = list(product_collection.all_objects)
mesh_objects = [obj for obj in product_objects if obj.type == "MESH"]
bpy.context.view_layer.update()
minimum, maximum = bounds(mesh_objects)
product_root = empty(product_controls, "USTUDIO_PRODUCT_ROOT", (0, 0, 0), "CIRCLE", 0.25)
for obj in [item for item in product_objects if item.parent not in product_objects]:
    matrix = obj.matrix_world.copy()
    obj.parent = product_root
    obj.matrix_world = matrix
product_root.rotation_euler.z = math.radians(-7.0)
product_root.location = (0.0, 0.0, 0.30 - minimum.z)
bpy.context.view_layer.update()
minimum, maximum = bounds(mesh_objects)
center = (minimum + maximum) / 2
radius = (maximum - minimum).length / 2

mat_floor = make_material("M_ARCADE_FLOOR", (0.004, 0.008, 0.026, 1), metallic=0.55, roughness=0.2)
mat_wall = make_material("M_ARCADE_WALL", (0.008, 0.006, 0.035, 1), metallic=0.2, roughness=0.34)
mat_plinth = make_material("M_ARCADE_PLINTH", (0.035, 0.018, 0.16, 1), metallic=0.65, roughness=0.16)
mat_cyan = make_material("M_NEON_CYAN", (0.0, 0.25, 0.45, 1), roughness=0.18, emission=(0.0, 0.75, 1.0, 1), strength=8.0)
mat_magenta = make_material("M_NEON_MAGENTA", (0.45, 0.0, 0.18, 1), roughness=0.18, emission=(1.0, 0.01, 0.35, 1), strength=8.0)

profile = [(-4.5, 0.0), (1.7, 0.0), (2.15, 0.08), (2.55, 0.38), (2.82, 0.85), (2.9, 1.35), (2.9, 5.5)]
vertices = []
for x in (-5.0, 5.0):
    vertices.extend((x, y, z) for y, z in profile)
n = len(profile)
faces = [(i, i + 1, n + i + 1, n + i) for i in range(n - 1)]
mesh = bpy.data.meshes.new("USTUDIO_ARCADE_CYC_MESH")
mesh.from_pydata(vertices, [], faces)
mesh.update()
cyclorama = bpy.data.objects.new("USTUDIO_ARCADE_CYCLORAMA", mesh)
environment.objects.link(cyclorama)
cyclorama.data.materials.append(mat_wall)
for polygon in mesh.polygons:
    polygon.use_smooth = True

for index, x in enumerate(range(-4, 5)):
    cube(environment, f"USTUDIO_GRID_X_{index:02d}", (x * 0.5, -0.8, 0.012), (0.008, 3.2, 0.008), mat_cyan)
for index, y in enumerate(range(-7, 5)):
    cube(environment, f"USTUDIO_GRID_Y_{index:02d}", (0, y * 0.42, 0.014), (2.4, 0.008, 0.008), mat_magenta)

bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=1.18, depth=0.28, location=(0, center.y, 0.14))
plinth = bpy.context.object
plinth.name = "USTUDIO_GAMEBOII_PLINTH"
move_to_collection(plinth, environment)
plinth.data.materials.append(mat_plinth)
bevel = plinth.modifiers.new("USTUDIO_SOFT_EDGE", "BEVEL")
bevel.width = 0.055
bevel.segments = 5

bpy.ops.mesh.primitive_torus_add(major_radius=1.2, minor_radius=0.018, major_segments=128, minor_segments=12, location=(0, center.y, 0.285))
plinth_ring = bpy.context.object
plinth_ring.name = "USTUDIO_PLINTH_NEON"
move_to_collection(plinth_ring, environment)
plinth_ring.data.materials.append(mat_cyan)

for name, major, minor, material, z in (
    ("PORTAL_MAGENTA", 1.65, 0.035, mat_magenta, 1.35),
    ("PORTAL_CYAN", 2.25, 0.025, mat_cyan, 1.35),
):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=144, minor_segments=12, location=(0, 2.68, z), rotation=(math.radians(90), 0, 0))
    portal = bpy.context.object
    portal.name = "USTUDIO_" + name
    move_to_collection(portal, environment)
    portal.data.materials.append(material)

left_pillar = cube(environment, "USTUDIO_PILLAR_LEFT", (-2.65, 1.95, 1.35), (0.26, 0.34, 1.35), mat_floor, 0.12)
right_pillar = cube(environment, "USTUDIO_PILLAR_RIGHT", (2.65, 1.95, 1.35), (0.26, 0.34, 1.35), mat_floor, 0.12)
cube(environment, "USTUDIO_PILLAR_LEFT_STRIP", (-2.65, 1.59, 1.35), (0.035, 0.015, 0.85), mat_magenta, 0.025)
cube(environment, "USTUDIO_PILLAR_RIGHT_STRIP", (2.65, 1.59, 1.35), (0.035, 0.015, 0.85), mat_cyan, 0.025)

light_target = empty(lighting, "USTUDIO_LIGHT_TARGET", center, "SPHERE", 0.1)
sun_data = bpy.data.lights.new("USTUDIO_SUN_KEY_DATA", "SUN")
sun_data.energy = 1.8
sun_data.angle = math.radians(8.0)
sun_data.color = (1.0, 0.48, 0.3)
sun = bpy.data.objects.new("USTUDIO_SUN_KEY", sun_data)
sun.rotation_euler = (math.radians(42), math.radians(-18), math.radians(-38))
lighting.objects.link(sun)
point_light(lighting, "USTUDIO_SKY_FILL", (-2.5, -1.2, 3.7), 520, 2.2, (0.18, 0.48, 1.0))
point_light(lighting, "USTUDIO_INDOOR_BOUNCE", (2.2, -1.8, 1.2), 360, 1.4, (1.0, 0.08, 0.36))
tracked_area(lighting, "USTUDIO_PORTAL_RIM", (0.2, 2.25, 3.0), 850, 2.5, (0.2, 0.75, 1.0), light_target)

screen = bpy.data.objects.get("Screen")
screen_material = bpy.data.materials.get("DRUMBOII_GAMEBOII_Screen")
if screen_material and screen_material.node_tree:
    screen_bsdf = screen_material.node_tree.nodes.get("Principled BSDF")
    if screen_bsdf:
        screen_bsdf.inputs["Base Color"].default_value = (0.002, 0.012, 0.055, 1.0)
        screen_bsdf.inputs["Roughness"].default_value = 0.14
        emission_input = screen_bsdf.inputs.get("Emission Color") or screen_bsdf.inputs.get("Emission")
        emission_strength = screen_bsdf.inputs.get("Emission Strength")
        if emission_input:
            emission_input.default_value = (0.01, 0.12, 0.8, 1.0)
        if emission_strength:
            emission_strength.default_value = 0.8
bpy.context.view_layer.update()
if screen:
    screen_min, screen_max = bounds([screen])
    focus_location = (screen_min + screen_max) / 2
else:
    focus_location = center + Vector((0, -0.1, 0.35))
focus = empty(camera_rig, "USTUDIO_FOCUS_SCREEN", focus_location, "CUBE", 0.08)
target = empty(camera_rig, "USTUDIO_CAMERA_TARGET", center + Vector((0, 0, 0.12)), "SPHERE", 0.1)

camera_data = bpy.data.cameras.new("USTUDIO_ARCADE_CAMERA_DATA")
camera_data.lens = 62
camera_data.sensor_width = 36
camera_data.clip_start = 0.02
camera_data.clip_end = 100
camera_data.dof.use_dof = True
camera_data.dof.focus_object = focus
camera_data.dof.aperture_fstop = 3.2
camera = bpy.data.objects.new("USTUDIO_ARCADE_CAMERA", camera_data)
camera.location = center + Vector((2.65, -4.75, 1.85))
camera_rig.objects.link(camera)
track = camera.constraints.new("TRACK_TO")
track.name = "USTUDIO_TRACK_PRODUCT"
track.target = target
track.track_axis = "TRACK_NEGATIVE_Z"
track.up_axis = "UP_Y"
scene.camera = camera

scene.use_nodes = True
tree = bpy.data.node_groups.new("USTUDIO_ARCADE_COMPOSITOR", "CompositorNodeTree")
tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
scene.compositing_node_group = tree
render_layers = tree.nodes.new("CompositorNodeRLayers")
glare = tree.nodes.new("CompositorNodeGlare")
glare.inputs["Type"].default_value = "Fog Glow"
glare.inputs["Quality"].default_value = "High"
glare.inputs["Threshold"].default_value = 0.8
glare.inputs["Size"].default_value = 0.65
composite = tree.nodes.new("NodeGroupOutput")
tree.links.new(render_layers.outputs["Image"], glare.inputs["Image"])
tree.links.new(glare.outputs["Image"], composite.inputs["Image"])

scene["ustudio_schema"] = 1
scene["ustudio_asset"] = ASSET_NAME
scene["ustudio_knowledge"] = "knowledge/tutorials/beginner-blender-tutorial-2026/analysis.json"
scene["ustudio_lighting_recipe"] = "sun key + sky fill + indoor bounce + portal rim"
scene["ustudio_focus_object"] = focus.name
scene.timeline_markers.new("USTUDIO_HERO_GATE", frame=1)
scene.frame_set(1)

def render_gate(engine, filename, samples=None):
    scene.render.engine = engine
    if engine == "CYCLES":
        scene.cycles.samples = samples or 32
        scene.cycles.use_denoising = True
        scene.cycles.use_adaptive_sampling = True
        try:
            preferences = bpy.context.preferences.addons["cycles"].preferences
            preferences.compute_device_type = "METAL"
            preferences.get_devices()
            for device in preferences.devices:
                device.use = True
            scene.cycles.device = "GPU"
        except Exception as error:
            print("CYCLES_GPU_FALLBACK=" + str(error))
    scene.render.filepath = str(GATE_DIR / filename)
    started = time.perf_counter()
    bpy.ops.render.render(write_still=True)
    return round(time.perf_counter() - started, 3)


try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
bpy.ops.wm.save_as_mainfile(filepath=str(PROJECT_FILE), compress=True, relative_remap=True)

eevee_engine = scene.render.engine
eevee_seconds = render_gate(eevee_engine, "hero-eevee.png")
cycles_seconds = render_gate("CYCLES", "hero-cycles.png", samples=32)

scene.render.engine = eevee_engine
scene.render.filepath = str(GATE_DIR / "hero-eevee.png")
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(PROJECT_FILE), compress=True, relative_remap=True)

manifest = {
    "schema_version": 1,
    "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    "project": str(PROJECT_FILE.relative_to(ROOT)),
    "asset": {
        "name": ASSET_NAME,
        "library": str(ASSET_LIBRARY.relative_to(ROOT)),
        "collection": product_collection.name,
        "polygons_from_audit": 79727,
        "source_materials": len({slot.material.name for obj in mesh_objects for slot in obj.material_slots if slot.material}),
    },
    "knowledge_sources": [
        "knowledge/tutorials/beginner-blender-tutorial-2026/analysis.json",
        "knowledge/tutorials/beginner-blender-tutorial-2026/WORKFLOW_RECIPES.md",
        "knowledge/tutorials/drumboii-camera-tutorial-2026-07-18/analysis.json"
    ],
    "scene": {
        "name": scene.name,
        "camera": camera.name,
        "focus_object": focus.name,
        "frame_range": [scene.frame_start, scene.frame_end],
        "fps": scene.render.fps,
        "product_bounds": {"min": list(minimum), "max": list(maximum), "center": list(center), "radius": radius}
    },
    "environment": {
        "style": "Y2K arcade portal",
        "lighting_roles": ["USTUDIO_SUN_KEY", "USTUDIO_SKY_FILL", "USTUDIO_INDOOR_BOUNCE", "USTUDIO_PORTAL_RIM"],
        "collections": [product_collection.name, product_controls.name, environment.name, lighting.name, camera_rig.name]
    },
    "gates": {
        "eevee": {"file": str((GATE_DIR / "hero-eevee.png").relative_to(ROOT)), "seconds": eevee_seconds, "engine": eevee_engine},
        "cycles": {"file": str((GATE_DIR / "hero-cycles.png").relative_to(ROOT)), "seconds": cycles_seconds, "samples": 32, "denoise": True}
    }
}
MANIFEST_FILE.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print("UNRECORDED_GAMEBOII_SCENE=" + json.dumps(manifest, ensure_ascii=False))
