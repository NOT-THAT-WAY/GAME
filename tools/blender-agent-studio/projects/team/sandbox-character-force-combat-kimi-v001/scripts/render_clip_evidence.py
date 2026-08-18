# Generic visual evidence for one Kimi pole clip: orthographic contact-sheet
# tiles (key poses x face/profile/three-quarter), perspective playblast frames
# of the WHOLE clip, and seam-strip tiles for loops.
# neutral-production: readable fixed cameras, light by function, ground plane
# added as render-only scaffolding (BAS_KIMI_ prefix, never saved, never exported).
#
# Usage:
#   blender -b <checkpoint.blend> --python render_clip_evidence.py -- \
#     <ACTION> <fstart> <fend> <loop:0|1> <outdir> <contact_frames_csv> [seam_frames_csv]

import bpy, sys, os, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
ACTION, F_START, F_END = argv[0], int(argv[1]), int(argv[2])
LOOP = argv[3] == "1"
OUTDIR = argv[4]
CONTACT_FRAMES = [int(x) for x in argv[5].split(",")]
SEAM_FRAMES = [int(x) for x in argv[6].split(",")] if LOOP and len(argv) > 6 else []
os.makedirs(OUTDIR, exist_ok=True)

PREFIX = "BAS_KIMI_"
sc = bpy.context.scene
AIM = Vector((0.0, 0.0, 0.70))

arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
act = bpy.data.actions[ACTION]
if arm.animation_data is None:
    arm.animation_data_create()
arm.animation_data.action = act
try:
    arm.animation_data.action_slot = act.slots[0]
except Exception:
    pass
sc.frame_start, sc.frame_end = F_START, F_END

for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
    try:
        sc.render.engine = eng
        break
    except TypeError:
        continue

sc.render.image_settings.file_format = "PNG"
sc.render.film_transparent = False
try:
    sc.view_settings.view_transform = "AgX"
except Exception:
    pass

world = bpy.data.worlds.new(PREFIX + "World")
sc.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.055, 0.065, 0.085, 1.0)
bg.inputs[1].default_value = 1.0

mesh = bpy.data.meshes.new(PREFIX + "GroundMesh")
ground = bpy.data.objects.new(PREFIX + "Ground", mesh)
sc.collection.objects.link(ground)
mesh.from_pydata([(-6, -6, 0), (6, -6, 0), (6, 6, 0), (-6, 6, 0)], [], [(0, 1, 2, 3)])
mesh.update()
gm = bpy.data.materials.new(PREFIX + "GroundMat")
gm.use_nodes = True
gp = gm.node_tree.nodes["Principled BSDF"]
gp.inputs["Base Color"].default_value = (0.16, 0.17, 0.19, 1.0)
gp.inputs["Roughness"].default_value = 0.85
ground.data.materials.append(gm)


def add_light(name, kind, energy, loc, rot, size=3.0):
    ld = bpy.data.lights.new(PREFIX + name, type=kind)
    ld.energy = energy
    if kind == "AREA":
        ld.size = size
    ob = bpy.data.objects.new(PREFIX + name, ld)
    ob.location = loc
    ob.rotation_euler = rot
    sc.collection.objects.link(ob)


add_light("Key", "AREA", 900.0, (-2.6, -3.4, 3.6),
          (math.radians(50), 0.0, math.radians(-38)), size=4.0)
add_light("Fill", "AREA", 220.0, (3.4, -2.6, 1.7),
          (math.radians(72), 0.0, math.radians(52)), size=5.0)
add_light("Rim", "AREA", 700.0, (1.2, 3.8, 2.9),
          (math.radians(118), 0.0, math.radians(160)), size=3.0)


def make_camera(name, direction, ortho, distance, ortho_scale=2.4, lens=48.0):
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
    pos = AIM + d * distance + Vector((0.0, 0.0, 0.34))
    ob.location = pos
    fwd = (AIM - pos).normalized()
    ob.rotation_euler = fwd.to_track_quat("-Z", "Y").to_euler()
    return ob


VIEWS = [
    ("face", Vector((0.0, -1.0, 0.0))),
    ("profile", Vector((1.0, 0.0, 0.0))),
    ("threequarter", Vector((math.sin(math.radians(45)), -math.cos(math.radians(45)), 0.0))),
]


def render_to(path):
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


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
        sc.render.stamp_note_text = "%s  %s" % (ACTION, vname)
        render_to(os.path.join(tile_dir, "tile_%03d" % idx))
        idx += 1

if SEAM_FRAMES:
    seam_dir = os.path.join(OUTDIR, "seam_tiles")
    os.makedirs(seam_dir, exist_ok=True)
    cam = make_camera("Cam_ortho_seam", VIEWS[2][1], ortho=True, distance=6.0)
    sc.camera = cam
    idx = 1
    for f in SEAM_FRAMES:
        sc.frame_set(f)
        sc.render.stamp_note_text = "%s  seam" % ACTION
        render_to(os.path.join(seam_dir, "tile_%03d" % idx))
        idx += 1

sc.render.resolution_x = 540
sc.render.resolution_y = 540
for vname, vdir in VIEWS:
    cam = make_camera("Cam_persp_" + vname, vdir, ortho=False, distance=4.3)
    sc.camera = cam
    vdirp = os.path.join(OUTDIR, "playblast_" + vname)
    os.makedirs(vdirp, exist_ok=True)
    sc.render.stamp_note_text = "%s  %s  30fps  %d-%d%s" % (
        ACTION, vname, F_START, F_END, " loop" if LOOP else "")
    for f in range(F_START, F_END + 1):
        sc.frame_set(f)
        render_to(os.path.join(vdirp, "f_%03d" % f))

print("EVIDENCE_RENDERED " + OUTDIR)
