"""Build LAST SIGNAL V2: a coherent 30-second product narrative with restrained motion."""
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "projects" / "flip-phone-signal-film-v2"
LIBRARY = ROOT / "asset_library" / "imported" / "drumboii-y2k-assets.blend"
BLEND = PROJECT / "Flip_Phone_Last_Signal_V2.blend"
PROJECT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.name = "LAST_SIGNAL_V2_MASTER"
scene.frame_start, scene.frame_end = 1, 720
scene.render.fps = 24
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = 960, 540
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.render.image_settings.color_mode = "RGBA"
scene.render.fps_base = 1.0
scene.unit_settings.system = "METRIC"
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = 0.05
scene.world = bpy.data.worlds.new("LS2_WORLD")
scene.world.use_nodes = True
world = scene.world.node_tree.nodes["Background"]
world.inputs["Color"].default_value = (0.0015, 0.004, 0.009, 1)
world.inputs["Strength"].default_value = 0.08


def col(name):
    value = bpy.data.collections.new(name)
    scene.collection.children.link(value)
    return value


source_col = col("LS2_SOURCE_FLIP_PHONE")
product_col = col("LS2_PRODUCT")
set_col = col("LS2_OBSERVATORY")
light_col = col("LS2_LIGHTS")
rig_col = col("LS2_RIG")
fx_col = col("LS2_FX")

with bpy.data.libraries.load(str(LIBRARY), link=False) as (src, dst):
    dst.collections = ["DRUMBOII_FLIP_PHONE"]
incoming = bpy.data.collections["DRUMBOII_FLIP_PHONE"]
for obj in list(incoming.objects):
    incoming.objects.unlink(obj)
    source_col.objects.link(obj)
source_col.hide_render = True
source_col.hide_viewport = True
bpy.data.collections.remove(incoming)

mapping = {}
for original in source_col.all_objects:
    obj = original.copy()
    if original.data:
        obj.data = original.data.copy()
    obj.animation_data_clear()
    obj.name = "LS2_" + original.name
    product_col.objects.link(obj)
    mapping[original.name] = obj
for original in source_col.all_objects:
    obj = mapping[original.name]
    obj.parent = mapping.get(original.parent.name) if original.parent else None
    obj.matrix_parent_inverse = original.matrix_parent_inverse.copy()


def curves(owner):
    action = getattr(getattr(owner, "animation_data", None), "action", None)
    if not action:
        return []
    result = list(getattr(action, "fcurves", []))
    for layer in getattr(action, "layers", []):
        for strip in getattr(layer, "strips", []):
            for bag in getattr(strip, "channelbags", []):
                result.extend(bag.fcurves)
    return result


def set_interp(owner, mode="BEZIER"):
    for curve in curves(owner):
        for key in curve.keyframe_points:
            key.interpolation = mode
            if mode == "BEZIER":
                key.handle_left_type = "AUTO_CLAMPED"
                key.handle_right_type = "AUTO_CLAMPED"


def material(name, base, metallic=0, roughness=.4, emission=None, strength=0, noise=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*base, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = .18
        bsdf.inputs["Coat Roughness"].default_value = .22
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1)
        bsdf.inputs["Emission Strength"].default_value = strength
    if noise:
        tex = nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = noise
        tex.inputs["Detail"].default_value = 3.2
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = .055
        bump.inputs["Distance"].default_value = .018
        links.new(tex.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


graphite = material("LS2_MAT_GRAPHITE_CERAMIC", (.018, .025, .032), .55, .24, noise=42)
ivory = material("LS2_MAT_WARM_IVORY", (.62, .48, .30), .12, .3)
copper = material("LS2_MAT_OXIDIZED_COPPER", (.24, .07, .025), .82, .2, noise=28)
screen = material("LS2_MAT_SCREEN_TEAL", (.002, .012, .014), .05, .16, (0.02, .72, .62), 0)
letter = material("LS2_MAT_SCREEN_LETTER", (.05, .25, .18), .05, .3, (.45, 1.0, .68), 5)
structure = material("LS2_MAT_STRUCTURE", (.008, .014, .022), .48, .34, noise=18)
floor_mat = material("LS2_MAT_FLOOR", (.004, .008, .012), .58, .24, noise=12)
amber = material("LS2_MAT_AMBER_SIGNAL", (.25, .045, .006), .12, .24, (1.0, .17, .015), 0)
teal = material("LS2_MAT_TEAL_SIGNAL", (.006, .12, .11), .08, .24, (.01, .8, .66), 0)

for obj in mapping.values():
    if obj.type != "MESH":
        continue
    name = obj.name.lower()
    obj.data.materials.clear()
    if "screen2" in name:
        obj.data.materials.append(screen)
    elif any(x in name for x in ("123", "456", "789", "abc", "def", "ghi", "jkl", "mno", "pqr", "stu", "vw", "xyz", "!!", "??", "%%")):
        obj.data.materials.append(letter)
    elif "button" in name or "circle" in name:
        obj.data.materials.append(ivory)
    elif "hinge" in name or "screw" in name:
        obj.data.materials.append(copper)
    else:
        obj.data.materials.append(graphite)


def empty(name, location=(0, 0, 0), parent=None):
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = .35
    rig_col.objects.link(obj)
    obj.parent = parent
    return obj


root = empty("LS2_PRODUCT_ROOT", (-5.4, 0, 1.4))
root.scale = (2.2,) * 3
phone = mapping["Phone"]
phone.parent = root
phone.matrix_parent_inverse.identity()
target = empty("LS2_CAMERA_TARGET", (0, 0, .05), root)
focus = empty("LS2_CAMERA_FOCUS", (0, -.08, .05), root)


def cube(name, loc, scale, mat, bevel=.05, collection=set_col):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for c in list(obj.users_collection): c.objects.unlink(obj)
    collection.objects.link(obj)
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new("LS2_BEVEL", "BEVEL")
        mod.width, mod.segments = bevel, 3
    return obj


def cylinder(name, loc, radius, depth, mat, vertices=64, collection=set_col):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    obj = bpy.context.object
    obj.name = name
    for c in list(obj.users_collection): c.objects.unlink(obj)
    collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def torus(name, loc, major, minor, mat, rotation=(math.pi / 2, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=72,
                                    minor_segments=10, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    for c in list(obj.users_collection): c.objects.unlink(obj)
    fx_col.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


# Observatory: one central route with three readable thresholds, no foreground occluders.
cube("LS2_FLOOR", (0, 0, -.28), (13, 7, .28), floor_mat, .14)
cube("LS2_RAIL", (-1.4, 0, .16), (6.3, 1.25, .12), structure, .12)
for i in range(22):
    x = -7.4 + i * .55
    cube(f"LS2_RAIL_TIE_{i:02d}", (x, 0, .34), (.18, 1.1, .045), copper if i % 4 == 0 else structure, .018)

# Physical carrier: it shares the phone velocity during transport, then retracts below the rail.
carrier = cube("LS2_PRODUCT_CARRIER", (-5.4, 0, .55), (.72, 1.03, .11), copper, .08)
carrier_inlay = cube("LS2_PRODUCT_CARRIER_INLAY", (-5.4, -.88, .68), (.5, .035, .025), teal, .012)
carrier_inlay.parent = carrier
carrier_inlay.matrix_parent_inverse = carrier.matrix_world.inverted()
for frame in (1, 144):
    carrier.keyframe_insert("location", frame=frame)
carrier.location.x = 3.0
carrier.keyframe_insert("location", frame=236)
carrier.location.z = 1.15
carrier.keyframe_insert("location", frame=248)
carrier.location.x = 5.5
carrier.keyframe_insert("location", frame=264)
carrier.location.z = .87
carrier.keyframe_insert("location", frame=276)
carrier.keyframe_insert("location", frame=288)
carrier.keyframe_insert("location", frame=720)
for curve in curves(carrier):
    for key in curve.keyframe_points:
        key.interpolation = "LINEAR" if key.co.x <= 236 else "BEZIER"
        if key.interpolation == "BEZIER":
            key.handle_left_type = key.handle_right_type = "AUTO_CLAMPED"

# Three observatory portals provide depth and a sequential destination for the signal.
portal_mats = []
for i, x in enumerate((-5.5, .0, 5.5)):
    glow = material(f"LS2_MAT_PORTAL_{i}", (.03, .02, .012), .08, .25, (1.0, .12 + i*.07, .02), 0)
    portal_mats.append(glow)
    # All portal geometry sits behind the product corridor from the final cameras.
    for side in (-1, 1):
        cube(f"LS2_PORTAL_{i}_SIDE_{side}", (x + side * 1.35, 4.65, 2.8), (.15, .18, 2.8), glow, .08)
    cube(f"LS2_PORTAL_{i}_TOP", (x, 4.65, 5.5), (1.5, .18, .15), glow, .08)

# Arrival pedestal and restrained background masses.
cylinder("LS2_DAIS", (5.5, 0, .42), 2.05, .55, structure, 96)
cylinder("LS2_DAIS_INLAY", (5.5, 0, .72), 1.58, .07, copper, 96)
for i, (x, y, h) in enumerate(((-3.8, 5.8, 2.4), (-1.0, 6.2, 3.0), (2.0, 6.0, 3.6),
                                (4.4, 6.3, 2.8), (7.5, 5.9, 4.2), (10.0, 6.1, 2.7))):
    cube(f"LS2_ARCHIVE_{i:02d}", (x, y, h/2), (.75, .7, h/2), structure, .14)


def emission_key(mat, frame, value):
    socket = mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    socket.default_value = value
    socket.keyframe_insert("default_value", frame=frame)


for i, mat in enumerate(portal_mats):
    emission_key(mat, 1, 0)
    emission_key(mat, 420 + i * 52, 0)
    emission_key(mat, 440 + i * 52, 5.5)
    emission_key(mat, 590, 3.0)
    emission_key(mat, 720, 3.0)

# Scanner crosses the object once and visually motivates the journey.
scanner = cube("LS2_SCANNER", (-7.0, -1.18, 2.2), (.035, .04, 1.8), teal, .015, fx_col)
scanner.keyframe_insert("location", frame=100)
scanner.location.x = -3.8
scanner.keyframe_insert("location", frame=150)
scanner.scale = (0.001, .001, .001)
scanner.keyframe_insert("scale", frame=154)
set_interp(scanner, "LINEAR")

# Signal rings appear only after the screen is awake; each has a clean attack and settle.
for i, radius in enumerate((1.9, 2.75, 3.65)):
    ring = torus(f"LS2_SIGNAL_RING_{i}", (5.5, .15, 2.75), radius, .028, teal if i != 1 else amber)
    ring.scale = (.001,) * 3
    ring.keyframe_insert("scale", frame=406 + i * 22)
    ring.scale = (1.0,) * 3
    ring.keyframe_insert("scale", frame=448 + i * 26)
    ring.scale = (1.035,) * 3
    ring.keyframe_insert("scale", frame=464 + i * 26)
    ring.scale = (1.0,) * 3
    ring.keyframe_insert("scale", frame=482 + i * 26)
    set_interp(ring)


def area(name, loc, energy, size, color, target_obj=target):
    data = bpy.data.lights.new(name + "_DATA", "AREA")
    data.energy, data.shape, data.size, data.color = energy, "DISK", size, color
    obj = bpy.data.objects.new(name, data)
    obj.location = loc
    light_col.objects.link(obj)
    con = obj.constraints.new("TRACK_TO")
    con.target, con.track_axis, con.up_axis = target_obj, "TRACK_NEGATIVE_Z", "UP_Y"
    return obj


area("LS2_KEY_WARM", (-2, -7, 7), 950, 5.5, (1.0, .52, .28))
area("LS2_RIM_TEAL", (8, 3, 7), 1250, 4.0, (.12, 1.0, .82))
area("LS2_TOP_SOFT", (3, 0, 10), 700, 5.0, (.56, .68, 1.0))
area("LS2_ARCHIVE_FILL", (-8, 4, 5), 450, 5.0, (.22, .34, .62))

# Product movement: true holds, one linear transport, one restrained hero lift.
root.location = (-5.4, 0, 2.70)
for f in (1, 144): root.keyframe_insert("location", frame=f)
root.location = (3.0, 0, 2.70)
root.keyframe_insert("location", frame=236)
root.location = (3.0, 0, 3.30)
root.keyframe_insert("location", frame=248)
root.location = (5.5, 0, 3.30)
root.keyframe_insert("location", frame=264)
root.location = (5.5, 0, 3.02)
root.keyframe_insert("location", frame=276)
root.keyframe_insert("location", frame=288)
root.keyframe_insert("location", frame=432)
root.location = (5.5, 0, 3.67)
root.rotation_euler = (math.radians(-2), math.radians(1.5), math.radians(-5))
root.keyframe_insert("location", frame=590)
root.keyframe_insert("rotation_euler", frame=590)
root.location = (5.5, 0, 3.38)
root.rotation_euler = (0, 0, 0)
root.keyframe_insert("location", frame=660)
root.keyframe_insert("rotation_euler", frame=660)
for f in (696, 720):
    root.keyframe_insert("location", frame=f)
    root.keyframe_insert("rotation_euler", frame=f)
for curve in curves(root):
    for key in curve.keyframe_points:
        key.interpolation = "LINEAR" if 144 <= key.co.x <= 236 else "BEZIER"
        if key.interpolation == "BEZIER":
            key.handle_left_type = key.handle_right_type = "AUTO_CLAMPED"

# Correct mechanical event: only the hinge parent moves; screen descendants inherit once.
hinge = mapping["Hinge"]
base = hinge.rotation_euler.copy()
hinge.rotation_euler.x = base.x + math.radians(140)
for f in (1, 288): hinge.keyframe_insert("rotation_euler", frame=f)
hinge.rotation_euler.x = base.x + math.radians(140)
hinge.keyframe_insert("rotation_euler", frame=310)
hinge.rotation_euler.x = base.x
hinge.keyframe_insert("rotation_euler", frame=350)
hinge.rotation_euler.x = base.x - math.radians(3)
hinge.keyframe_insert("rotation_euler", frame=365)
hinge.rotation_euler.x = base.x
for f in (378, 720): hinge.keyframe_insert("rotation_euler", frame=f)
set_interp(hinge)

emission_key(screen, 1, 0)
emission_key(screen, 354, 0)
emission_key(screen, 370, 4.5)
emission_key(screen, 392, 2.6)
emission_key(screen, 590, 2.2)
emission_key(screen, 720, 2.2)

# A real message, attached to the moving screen rather than composited over it.
font_curve = bpy.data.curves.new("LS2_HELLO_TYPE_DATA", "FONT")
font_curve.body = "HELLO"
font_curve.align_x = "CENTER"
font_curve.align_y = "CENTER"
font_curve.size = .22
font_curve.extrude = .002
font_curve.bevel_depth = .001
hello = bpy.data.objects.new("LS2_HELLO_TYPE", font_curve)
product_col.objects.link(hello)
hello.parent = mapping["Screen.001"]
hello.location = (0, -.061, .066)
hello.rotation_euler = (math.pi / 2, 0, 0)
hello.data.materials.append(letter)
hello.scale = (.001,) * 3
hello.keyframe_insert("scale", frame=366)
hello.scale = (.28,) * 3
hello.keyframe_insert("scale", frame=378)
hello.scale = (.25,) * 3
hello.keyframe_insert("scale", frame=390)
hello.keyframe_insert("scale", frame=720)
set_interp(hello)

# Camera system: four shots, cuts only on holds; target changes are minimal and delayed.
target.location = (0, 0, -.30)
target.keyframe_insert("location", frame=1)
target.keyframe_insert("location", frame=288)
target.location = (0, 0, .38)
target.keyframe_insert("location", frame=354)
target.keyframe_insert("location", frame=408)
target.location = (0, 0, .03)
target.keyframe_insert("location", frame=470)
set_interp(target)
focus.location = (0, -.08, -.30)
focus.keyframe_insert("location", frame=1)
focus.keyframe_insert("location", frame=300)
focus.location = (0, -.08, .35)
focus.keyframe_insert("location", frame=366)
focus.keyframe_insert("location", frame=414)
focus.location = (0, -.08, .03)
focus.keyframe_insert("location", frame=482)
set_interp(focus)


def camera(name, start, positions, lens=60):
    data = bpy.data.cameras.new(name + "_DATA")
    data.lens = lens
    data.dof.use_dof = True
    data.dof.focus_object = focus
    data.dof.aperture_fstop = 4.0
    obj = bpy.data.objects.new(name, data)
    rig_col.objects.link(obj)
    con = obj.constraints.new("TRACK_TO")
    con.target, con.track_axis, con.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
    for frame, location, focal in positions:
        obj.location = location
        data.lens = focal
        obj.keyframe_insert("location", frame=frame)
        data.keyframe_insert("lens", frame=frame)
    set_interp(obj)
    set_interp(data)
    marker = scene.timeline_markers.new("LS2_CUT_" + name, frame=start)
    marker.camera = obj
    return obj


cam1 = camera("LS2_CAM_DORMANT", 1, [
    (1, (-5.8, -10.4, 3.5), 56), (24, (-5.8, -10.4, 3.5), 56),
    (120, (-5.25, -9.2, 3.25), 60), (144, (-5.25, -9.2, 3.25), 60)])
cam2 = camera("LS2_CAM_JOURNEY", 145, [
    (145, (-.4, -10.8, 3.7), 52), (264, (-.4, -10.8, 3.7), 52),
    (288, (-.4, -10.8, 3.7), 52)])
cam3 = camera("LS2_CAM_MESSAGE", 289, [
    (289, (5.5, -8.4, 3.45), 72), (312, (5.5, -8.4, 3.45), 72),
    (382, (5.25, -6.8, 3.35), 76), (408, (5.25, -6.8, 3.35), 76),
    (432, (5.0, -7.15, 3.55), 72)])
cam4 = camera("LS2_CAM_RESTORED", 433, [
    (433, (1.0, -11.6, 5.2), 58), (458, (1.0, -11.6, 5.2), 58),
    (560, (7.8, -10.2, 6.0), 66), (590, (7.4, -10.4, 5.8), 64),
    (660, (2.0, -11.5, 5.2), 62), (696, (2.0, -11.5, 5.2), 62),
    (720, (2.0, -11.5, 5.2), 62)])
scene.camera = cam1

for frame, name in ((1, "DORMANT"), (96, "SCAN"), (145, "JOURNEY"), (264, "ARRIVAL"),
                    (289, "LISTEN"), (350, "OPEN"), (370, "MESSAGE"), (433, "SIGNAL"),
                    (590, "LIFT"), (696, "FINAL_STILL"), (720, "END")):
    scene.timeline_markers.new("LS2_" + name, frame=frame)

manifest = {
    "schema_version": 2,
    "title": "LAST SIGNAL — ONE LAST MESSAGE",
    "logline": "A forgotten flip phone receives one final message and relights a silent observatory.",
    "duration_seconds": 30,
    "fps": 24,
    "frame_range": [1, 720],
    "design": {
        "object": "graphite ceramic, warm ivory keys, oxidized copper mechanics, teal display",
        "set": "communication observatory with three sequential signal portals",
        "palette": ["#071018", "#171D21", "#D89A58", "#27D7B5", "#FF542C"],
        "lighting": "warm directional key, teal rim, soft top, low ambient world",
        "typography": "minimal off-white grotesk overlays; no text over mechanical action"
    },
    "acts": [
        {"frames": [1, 144], "name": "forgotten", "function": "establish stillness and scan"},
        {"frames": [145, 288], "name": "journey", "function": "one constant-speed transfer"},
        {"frames": [289, 432], "name": "message", "function": "hold, hinge action, screen response"},
        {"frames": [433, 590], "name": "restoration", "function": "signal causes portals to light"},
        {"frames": [591, 720], "name": "proof", "function": "restrained lift and true final still"}
    ],
    "motion_rules": [
        "no parent and descendant animated for the same reveal",
        "camera remains static during linear transport",
        "cuts occur on holds",
        "only one dominant movement per beat",
        "final 24 frames are identical"
    ],
    "physical_contract": "knowledge/physics/object-contracts/drumboii-flip-phone.json",
    "physical_validation_required": True,
    "source_asset_modified": False
}
(PROJECT / "film-manifest-v2.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
print("LAST_SIGNAL_V2_RESULT=" + json.dumps({"blend": str(BLEND), "manifest": str(PROJECT / "film-manifest-v2.json")}))
