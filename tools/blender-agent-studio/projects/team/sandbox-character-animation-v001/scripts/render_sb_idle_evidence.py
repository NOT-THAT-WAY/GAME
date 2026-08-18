# Visual evidence for SB_Idle: orthographic contact sheet frames + perspective
# playblast frames, from face / profile / three-quarter.
#
# Profile neutral-production: readable camera without competing movement,
# subject separated from background by value and hue, light built by function
# (exposure, form, separation). A ground plane at Z=0 is added SO THE FOOT
# CONTACT IS VISIBLE - it is render-only scaffolding, prefixed with the project
# prefix, and this script never saves the .blend.
#
# The character faces -Y (measured from the eye material patch), so the face
# camera sits on -Y.
#
# Usage: blender -b <master.blend> --python render_sb_idle_evidence.py -- <outdir>

import bpy, sys, os, math
from mathutils import Vector

OUTDIR = sys.argv[sys.argv.index("--") + 1:][0]
os.makedirs(OUTDIR, exist_ok=True)

PREFIX = "BAS_SANDBOX_CHARACTER_ANIMATION_V001_"
sc = bpy.context.scene
AIM = Vector((0.0, 0.0, 0.70))
CONTACT_FRAMES = [1, 11, 21, 31, 41, 51]

VIEWS = [
    ("face",    Vector((0.0, -1.0, 0.0))),
    ("profile", Vector((1.0,  0.0, 0.0))),
    ("threequarter", Vector((math.sin(math.radians(45)), -math.cos(math.radians(45)), 0.0))),
]

# ---------------------------------------------------------------- engine
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
    try:
        sc.render.engine = eng
        break
    except TypeError:
        continue
print("ENGINE " + sc.render.engine)

sc.render.image_settings.file_format = "PNG"
sc.render.film_transparent = False
sc.view_settings.view_transform = "AgX" if "AgX" in [
    t.name for t in bpy.data.scenes[0].view_settings.bl_rna.properties["view_transform"].enum_items
] else "Standard"

# ---------------------------------------------------------------- world
world = bpy.data.worlds.new(PREFIX + "World")
sc.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.055, 0.065, 0.085, 1.0)  # cool desaturated, separates the terracotta
bg.inputs[1].default_value = 1.0

# ---------------------------------------------------------------- ground
mesh = bpy.data.meshes.new(PREFIX + "GroundMesh")
ground = bpy.data.objects.new(PREFIX + "Ground", mesh)
sc.collection.objects.link(ground)
verts = [(-6, -6, 0), (6, -6, 0), (6, 6, 0), (-6, 6, 0)]
mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
mesh.update()
gm = bpy.data.materials.new(PREFIX + "GroundMat")
gm.use_nodes = True
gp = gm.node_tree.nodes["Principled BSDF"]
gp.inputs["Base Color"].default_value = (0.16, 0.17, 0.19, 1.0)
gp.inputs["Roughness"].default_value = 0.85
ground.data.materials.append(gm)

# ---------------------------------------------------------------- light
def add_light(name, kind, energy, loc, rot, size=3.0):
    ld = bpy.data.lights.new(PREFIX + name, type=kind)
    ld.energy = energy
    if kind == "AREA":
        ld.size = size
    ob = bpy.data.objects.new(PREFIX + name, ld)
    ob.location = loc
    ob.rotation_euler = rot
    sc.collection.objects.link(ob)
    return ob


# key: exposure + form
add_light("Key", "AREA", 900.0, (-2.6, -3.4, 3.6),
          (math.radians(50), 0.0, math.radians(-38)), size=4.0)
# fill: keeps the shadow side readable, lower value
add_light("Fill", "AREA", 220.0, (3.4, -2.6, 1.7),
          (math.radians(72), 0.0, math.radians(52)), size=5.0)
# rim: separation from the background
add_light("Rim", "AREA", 700.0, (1.2, 3.8, 2.9),
          (math.radians(118), 0.0, math.radians(160)), size=3.0)


def make_camera(name, direction, ortho, distance, ortho_scale=2.05, lens=48.0):
    cd = bpy.data.cameras.new(PREFIX + name)
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho_scale
    else:
        cd.type = "PERSP"
        cd.lens = lens
    ob = bpy.data.objects.new(PREFIX + name, cd)
    sc.collection.objects.link(ob)
    d = direction.normalized()
    # lift the camera slightly so the ground reads as a floor, not a horizon line
    pos = AIM + d * distance + Vector((0.0, 0.0, 0.34))
    ob.location = pos
    fwd = (AIM - pos).normalized()
    ob.rotation_euler = fwd.to_track_quat("-Z", "Y").to_euler()
    return ob


def render_to(path):
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------- contact sheet
sc.render.resolution_x = 620
sc.render.resolution_y = 620
sc.render.resolution_percentage = 100
sc.render.use_stamp = True
sc.render.use_stamp_note = True
sc.render.use_stamp_frame = True
sc.render.use_stamp_date = False
sc.render.use_stamp_time = False
sc.render.use_stamp_render_time = False
sc.render.use_stamp_scene = False
sc.render.use_stamp_camera = False
sc.render.use_stamp_filename = False
sc.render.stamp_font_size = 22

tile_dir = os.path.join(OUTDIR, "contact_tiles")
os.makedirs(tile_dir, exist_ok=True)

idx = 1
for vname, vdir in VIEWS:
    cam = make_camera("Cam_ortho_" + vname, vdir, ortho=True, distance=6.0)
    sc.camera = cam
    for f in CONTACT_FRAMES:
        sc.frame_set(f)
        sc.render.stamp_note_text = "SB_Idle  %s" % vname
        render_to(os.path.join(tile_dir, "tile_%03d" % idx))
        idx += 1

# ---------------------------------------------------------------- playblast
sc.render.resolution_x = 540
sc.render.resolution_y = 540
sc.render.use_stamp_note = True

for vname, vdir in VIEWS:
    cam = make_camera("Cam_persp_" + vname, vdir, ortho=False, distance=4.15)
    sc.camera = cam
    vdirp = os.path.join(OUTDIR, "playblast_" + vname)
    os.makedirs(vdirp, exist_ok=True)
    sc.render.stamp_note_text = "SB_Idle  %s  30fps  loop 1-60" % vname
    for f in range(sc.frame_start, sc.frame_end + 1):
        sc.frame_set(f)
        render_to(os.path.join(vdirp, "f_%03d" % f))

print("EVIDENCE_RENDERED " + OUTDIR)
