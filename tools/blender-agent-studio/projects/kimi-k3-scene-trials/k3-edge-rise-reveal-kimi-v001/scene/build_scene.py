"""BUILD — k3-edge-rise-reveal-kimi-v001
- Append asset mecha-mascot-v002 (mesh intact)
- Crée le rig K3_EDGE_RIG (ajout documenté, aucun remodelage)
- Skinning auto-weights, scale 1/5 hauteur intérieure, parent float root
- Caméra plan continu + target + lumières + ramp émission + audio VSE
L'animation est bakée séparément (bake_anim.py).
"""
import bpy, math, os
from mathutils import Vector, Matrix

ROOT_DIR = "${BLENDER_AGENT_STUDIO_ROOT}"
ASSET = os.path.join(ROOT_DIR, "asset_library/characters/mecha-mascot-v002.blend")
MASTER_AUDIO = os.path.join(ROOT_DIR, "projects/fl-studio-box-semantic-template/media/current/master.mp4")
SCALE = 0.413            # hauteur 2.073 m -> 0.856 m  ≈ 1/5 hauteur intérieure (4.28 m)
GRIP = 1.25

sc = bpy.context.scene

# ---------------------------------------------------------------- asset
with bpy.data.libraries.load(ASSET, link=False) as (src, dst):
    dst.collections = ["K3_MECHA_MASCOT_ASSET"]
asset_col = dst.collections[0]
sc.collection.children.link(asset_col)
root = bpy.data.objects["K3_MECHA_MASCOT_ROOT"]
body = bpy.data.objects["K3_MECHA_BODY"]
head = bpy.data.objects["K3_MECHA_HEAD"]

# ---------------------------------------------------------------- rig (AJOUT)
BONES = {  # head, tail, parent  (espace armature = espace asset, mètres)
    "Pelvis":    ((0, 0, 0.80),   (0, 0, 0.99),   None),
    "Spine":     ((0, 0, 0.99),   (0, 0, 1.22),   "Pelvis"),
    "Chest":     ((0, 0, 1.22),   (0, 0, 1.39),   "Spine"),
    "Neck":      ((0, 0, 1.39),   (0, 0, 1.545),  "Chest"),
    "Head":      ((0, 0, 1.545),  (0, 0, 1.95),   "Neck"),
    "UpperArm.L":((-0.449, 0, 1.410), (-0.75, 0, 1.506), "Chest"),
    "Forearm.L": ((-0.75, 0, 1.506),  (-1.055, 0, 1.635), "UpperArm.L"),
    "UpperArm.R":((0.449, 0, 1.410),  (0.75, 0, 1.506),  "Chest"),
    "Forearm.R": ((0.75, 0, 1.506),   (1.055, 0, 1.635), "UpperArm.R"),
    "Thigh.L":   ((-0.19, 0, 0.66),  (-0.221, 0, 0.454), "Pelvis"),
    "Shin.L":    ((-0.221, 0, 0.454), (-0.24, 0, 0.05),  "Thigh.L"),
    "Thigh.R":   ((0.19, 0, 0.66),   (0.221, 0, 0.454),  "Pelvis"),
    "Shin.R":    ((0.221, 0, 0.454),  (0.24, 0, 0.05),   "Thigh.R"),
}
arm_data = bpy.data.armatures.new("K3_EDGE_RIG")
rig = bpy.data.objects.new("K3_EDGE_RIG", arm_data)
sc.collection.objects.link(rig)
rig.parent = root
rig.matrix_parent_inverse = Matrix.Identity(4)
rig.matrix_basis = Matrix.Identity(4)

bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
ebs = {}
for name, (h, t, parent) in BONES.items():
    eb = arm_data.edit_bones.new(name)
    eb.head, eb.tail = Vector(h), Vector(t)
    ebs[name] = eb
for name, (h, t, parent) in BONES.items():
    if parent:
        ebs[name].parent = ebs[parent]
bpy.ops.object.mode_set(mode='OBJECT')

# ---------------------------------------------------------------- skinning
# parent_set AUTO crée les vertex groups + modifier (mesh non remodelé)
bpy.ops.object.select_all(action='DESELECT')
body.select_set(True); head.select_set(True); rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.parent_set(type='ARMATURE_AUTO')

# reparente les meshes sous le ROOT (échelle commune), garde le modifier armature
for m in (body, head):
    mw = m.matrix_world.copy()
    m.parent = root
    m.matrix_parent_inverse = Matrix.Identity(4)
    m.matrix_world = mw

# armature modifier avant subsurf sur le body
bpy.context.view_layer.objects.active = body
for _ in range(len(body.modifiers)):
    if body.modifiers[0].type == 'ARMATURE':
        break
    bpy.ops.object.modifier_move_up(modifier=body.modifiers[-1].name)

covered = sum(1 for v in body.data.vertices if v.groups)
print(f"SKIN body verts weighted: {covered}/{len(body.data.vertices)}")
covered_h = sum(1 for v in head.data.vertices if v.groups)
print(f"SKIN head verts weighted: {covered_h}/{len(head.data.vertices)}")

# ------------------------------------------------- scale + ancrage float root
root.scale = (SCALE, SCALE, SCALE)
root.parent = bpy.data.objects["USTUDIO_BOX_FLOAT_ROOT"]
root.matrix_parent_inverse = Matrix.Identity(4)
root.location = (0, 0, 0)
root["ustudio_grip_surface"] = GRIP
rig["ustudio_grip_surface"] = GRIP
bpy.data.objects["USTUDIO_PIANO_ROLL_FLOOR"]["ustudio_grip_surface"] = GRIP

# ---------------------------------------------------------------- caméra
cam_data = bpy.data.cameras.new("K3_EDGE_CAM")
cam = bpy.data.objects.new("K3_EDGE_CAM", cam_data)
sc.collection.objects.link(cam)
cam_data.lens = 50
cam_data.sensor_width = 36
cam_data.dof.use_dof = True
cam_data.dof.aperture_fstop = 2.8

target = bpy.data.objects.new("K3_EDGE_TARGET", None)
sc.collection.objects.link(target)
target.parent = bpy.data.objects["USTUDIO_BOX_FLOAT_ROOT"]
target.matrix_parent_inverse = Matrix.Identity(4)
target.empty_display_size = 0.1

con = cam.constraints.new('TRACK_TO')
con.name = "K3_EDGE_TRACK"
con.target = target
con.track_axis = 'TRACK_NEGATIVE_Z'
con.up_axis = 'UP_Y'
cam_data.dof.focus_object = target
sc.camera = cam

CAM_KEYS = [  # frame, position monde, focale
    (1,   (-1.55, -3.60, 1.30), 50),
    (40,  (-1.45, -3.45, 1.38), 50),
    (57,  (-1.30, -3.30, 1.50), 48),
    (106, (-0.70, -3.20, 2.20), 46),
    (154, (-0.20, -4.00, 2.90), 42),
    (203, ( 0.00, -5.20, 3.50), 38),
    (251, ( 0.00, -6.80, 4.10), 35),
    (299, ( 0.00, -8.30, 4.50), 33),
    (348, ( 0.00, -9.00, 4.60), 35),
    (360, ( 0.00, -9.10, 4.62), 35),
]
TGT_KEYS = [  # frame, position locale (repère float root)
    (1,   (0, -0.60, 1.05)),
    (57,  (0, -0.58, 1.15)),
    (106, (0, -0.45, 1.55)),
    (154, (0, -0.10, 1.90)),
    (203, (0,  0.15, 2.30)),
    (251, (0,  0.35, 2.65)),
    (299, (0,  0.42, 2.95)),
    (348, (0,  0.35, 3.35)),
    (360, (0,  0.35, 3.37)),
]
FSTOPS = [(1, 2.8), (203, 4.0), (348, 5.6)]

def key_path(obj, keys, attr):
    for f, pos, *rest in keys:
        setattr(obj, attr, pos)
        obj.keyframe_insert(attr, frame=f)

for f, pos, lens in CAM_KEYS:
    cam.location = pos
    cam.keyframe_insert("location", frame=f)
    cam_data.lens = lens
    cam_data.keyframe_insert("lens", frame=f)
for f, pos in TGT_KEYS:
    target.location = pos
    target.keyframe_insert("location", frame=f)
for f, fs in FSTOPS:
    cam_data.dof.aperture_fstop = fs
    cam_data.dof.keyframe_insert("aperture_fstop", frame=f)

# ---------------------------------------------------------------- lumières
float_root = bpy.data.objects["USTUDIO_BOX_FLOAT_ROOT"]

def add_light(name, ltype, color, energy, loc, aim=None, size=1.0):
    ld = bpy.data.lights.new(name, ltype)
    ld.color = color
    ld.energy = energy
    if ltype == 'AREA':
        ld.shape = 'DISK'; ld.size = size
    ob = bpy.data.objects.new(name, ld)
    sc.collection.objects.link(ob)
    ob.parent = float_root
    ob.matrix_parent_inverse = Matrix.Identity(4)
    ob.location = loc
    if aim is not None:
        d = (Vector(aim) - Vector(loc)).normalized()
        ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return ob

# rebond lime du piano roll (faux bounce, les écrans sont la source)
add_light("K3_EDGE_BOUNCE", 'AREA', (0.35, 1.0, 0.18), 45,
          (0, 0.15, 1.9), aim=(0, 0.3, 1.0), size=2.2)
# rim magenta depuis les écrans du fond
add_light("K3_EDGE_BACKRIM", 'AREA', (1.0, 0.16, 0.5), 70,
          (0, 1.55, 4.6), aim=(0, 0.2, 1.6), size=2.5)
# balayage lime synchronisé sur la playhead (idée personnelle : traversée à la mesure 203)
sweep = add_light("K3_EDGE_PLAYHEAD_SWEEP", 'POINT', (0.2, 1.0, 0.06), 0.0, (0, 0.55, 2.6))
for f in range(185, 230):
    x = -3.45 + (f - 1) * 6.47 / 396.0
    sweep.location.x = x
    sweep.keyframe_insert("location", frame=f)
    if f < 200:
        e = 35.0 * (f - 185) / 15.0
    elif f <= 214:
        e = 35.0
    else:
        e = 35.0 * (228 - f) / 14.0
    sweep.data.energy = e
    sweep.data.keyframe_insert("energy", frame=f)

# assagit les fills génériques du template pour laisser les écrans dominer
for n in ("USTUDIO_SOFT_KEY", "USTUDIO_SOFT_FILL"):
    if n in bpy.data.objects:
        bpy.data.objects[n].data.energy *= 0.4

# hero light : la silhouette devient le point le plus lumineux sur le climax
hero = add_light("K3_EDGE_HERO", 'AREA', (1.0, 0.98, 0.9), 0.0,
                 (-1.2, -2.0, 4.2), aim=(0, 0.35, 1.9), size=1.2)
for f, e in ((289, 0.0), (320, 35.0), (348, 60.0), (360, 60.0)):
    hero.data.energy = e
    hero.data.keyframe_insert("energy", frame=f)

# ramp d'intensité des écrans : les murs-écrans montent vers le climax
for mat_name in ("M_MOVIE_PLAYLIST", "M_MOVIE_PIANO_ROLL", "M_MOVIE_MIXER", "M_MOVIE_BROWSER"):
    m = bpy.data.materials.get(mat_name)
    if not m or not m.use_nodes:
        continue
    for node in m.node_tree.nodes:
        if node.type == 'BSDF_PRINCIPLED':
            es = node.inputs.get("Emission Strength")
            if es is None:
                continue
            for f, v in ((1, 0.35), (203, 0.5), (299, 0.65), (348, 1.05), (360, 1.05)):
                es.default_value = v
                es.keyframe_insert("default_value", frame=f)

# ---------------------------------------------------------------- markers + audio + rendu
for name, f in (("K3_EDGE_SIT", 1), ("K3_EDGE_STAND", 57), ("K3_EDGE_WALK", 106),
                ("K3_EDGE_PLAYHEAD", 203), ("K3_EDGE_STOP", 299), ("K3_EDGE_LOOK", 320),
                ("K3_EDGE_HOLD", 348)):
    sc.timeline_markers.new(name, frame=f)

sc.frame_start = 1
sc.frame_end = 360
sc.render.fps = 30
sc.render.resolution_x = 640
sc.render.resolution_y = 360
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'
sc.render.filepath = os.path.join(os.path.dirname(bpy.data.filepath), "..", "renders", "frames", "f_")
try:
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
except Exception:
    sc.render.engine = 'BLENDER_EEVEE'

if sc.sequence_editor is None:
    sc.sequence_editor_create()
se = sc.sequence_editor
if not any(s.type == 'SOUND' for s in se.strips_all):
    se.strips.new_sound("K3_EDGE_AUDIO", filepath=MASTER_AUDIO, channel=1, frame_start=1)

bpy.ops.wm.save_mainfile()
print("BUILD_OK")
