"""ETAPES D+E+G+H (structure) — essai k3-pianoroll-slope-run-kimi-v001.

Construit dans scene/trial.blend :
- collection K3_PIANOROLL_SLOPE_RUN_KIMI_V001_WORK
- K3_RUNNER_RIG : armature FK orientee dans le repere de surface mesure
  (Z local -> SURFACE_NORMAL, -Y local -> UPHILL_TANGENT) :
  en espace armature, le Piano Roll est le plan z=0 et la montee = -Y.
- mannequin pearl 0,33 m + semelles grip lime emissives (pulse au contact)
- contrat d'adherence ustudio_grip_surface = 1.25 (plancher + rig)
- cameras : K3_CAM_MAIN (+TARGET/FOCUS), 3 cameras diagnostiques
- lumieres Drumboiii : Sun oblique, backlight dominant, glimmers lime/magenta,
  retour torse
Sauvegarde scene/trial.blend.
"""
import bpy
import json
from mathutils import Vector, Matrix

TRIAL = "${BLENDER_AGENT_STUDIO_ROOT}/projects/kimi-k3-scene-trials/k3-pianoroll-slope-run-kimi-v001"
assert bpy.data.filepath == TRIAL + "/scene/trial.blend", bpy.data.filepath

sc = bpy.context.scene
root = bpy.data.objects["USTUDIO_BOX_FLOAT_ROOT"]
floor = bpy.data.objects["USTUDIO_PIANO_ROLL_FLOOR"]

surf = json.load(open(TRIAL + "/diagnostics/surface-analysis.json"))
N = Vector(surf["SURFACE_NORMAL"])
U = Vector(surf["UPHILL_TANGENT"])
C = Vector(surf["CROSS_SLOPE_TANGENT"])
LOW = Vector(surf["low_edge_local"])
assert abs(N.z - 0.6904) < 0.01 and U.z > 0.7

COLL_NAME = "K3_PIANOROLL_SLOPE_RUN_KIMI_V001_WORK"
if COLL_NAME in bpy.data.collections:
    raise SystemExit("collection deja presente — abandon")
coll = bpy.data.collections.new(COLL_NAME)
sc.collection.children.link(coll)

def link(obj):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)

# ---------------------------------------------------------------- contrat grip
floor["ustudio_grip_surface"] = 1.25
floor["ustudio_grip_min_required"] = 1.05

# ---------------------------------------------------------------- materiaux
def mat_pearl():
    m = bpy.data.materials.new("M_K3_RUNNER_PEARL")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.93, 0.93, 0.95, 1)
    b.inputs["Roughness"].default_value = 0.4
    b.inputs["Metallic"].default_value = 0.0
    b.inputs["Coat Weight"].default_value = 0.25
    return m

def mat_grip(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.05, 0.08, 0.04, 1)
    b.inputs["Roughness"].default_value = 0.6
    b.inputs["Emission Color"].default_value = (0.42, 1.0, 0.16, 1)
    b.inputs["Emission Strength"].default_value = 0.15
    return m

PEARL = mat_pearl()
GRIP_L = mat_grip("M_K3_GRIP_L")
GRIP_R = mat_grip("M_K3_GRIP_R")

# ---------------------------------------------------------------- armature
ARM_NAME = "K3_RUNNER_RIG"
arm_data = bpy.data.armatures.new(ARM_NAME + "_DATA")
arm = bpy.data.objects.new(ARM_NAME, arm_data)
coll.objects.link(arm)
arm["ustudio_grip_surface"] = 1.25
arm.parent = root

S0 = 0.2  # marge basse depuis low_edge le long de U
P0 = LOW + U * S0
# repere : Z local -> N, -Y local -> U (avant = montee), X local -> -C
X_img = -C
Y_img = -U
Z_img = N
R = Matrix(((X_img.x, Y_img.x, Z_img.x, 0.0),
            (X_img.y, Y_img.y, Z_img.y, 0.0),
            (X_img.z, Y_img.z, Z_img.z, 0.0),
            (0.0, 0.0, 0.0, 1.0)))
M = Matrix.Translation(P0) @ R
arm.matrix_basis = M
bpy.context.view_layer.update()  # impose matrix_world avant de lier les parties

bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
BONES = [
    ("root",        (0, 0, 0.0),     (0, 0, 0.06),     None,    False),
    ("hips",        (0, 0, 0.195),   (0, 0, 0.225),    "root",  False),
    ("spine",       (0, 0, 0.225),   (0, 0, 0.255),    "hips",  True),
    ("chest",       (0, 0, 0.255),   (0, 0, 0.285),    "spine", True),
    ("neck",        (0, 0, 0.285),   (0, 0, 0.300),    "chest", True),
    ("head",        (0, 0, 0.300),   (0, 0, 0.335),    "neck",  True),
    ("upper_arm.L", (-0.058, 0, 0.262), (-0.062, 0, 0.205), "chest", False),
    ("forearm.L",   (-0.062, 0, 0.205), (-0.064, 0, 0.152), "upper_arm.L", True),
    ("hand.L",      (-0.064, 0, 0.152), (-0.064, 0, 0.130), "forearm.L", True),
    ("upper_arm.R", (0.058, 0, 0.262),  (0.062, 0, 0.205),  "chest", False),
    ("forearm.R",   (0.062, 0, 0.205),  (0.064, 0, 0.152),  "upper_arm.R", True),
    ("hand.R",      (0.064, 0, 0.152),  (0.064, 0, 0.130),  "forearm.R", True),
    ("thigh.L",     (-0.027, 0, 0.195), (-0.029, 0, 0.105), "hips", False),
    ("shin.L",      (-0.029, 0, 0.105), (-0.029, 0, 0.022), "thigh.L", True),
    ("foot.L",      (-0.029, 0, 0.022), (-0.029, -0.045, 0.006), "shin.L", True),
    ("thigh.R",     (0.027, 0, 0.195),  (0.029, 0, 0.105),  "hips", False),
    ("shin.R",      (0.029, 0, 0.105),  (0.029, 0, 0.022),  "thigh.R", True),
    ("foot.R",      (0.029, 0, 0.022),  (0.029, -0.045, 0.006), "shin.R", True),
]
for name, head, tail, parent, connected in BONES:
    b = arm_data.edit_bones.new(name)
    b.head = head
    b.tail = tail
    if parent:
        b.parent = arm_data.edit_bones[parent]
        b.use_connect = connected
bpy.ops.object.mode_set(mode="POSE")
for pb in arm.pose.bones:
    pb.rotation_mode = "XYZ"
bpy.ops.object.mode_set(mode="OBJECT")
arm.select_set(False)

# ---------------------------------------------------------------- meshes
AW = arm.matrix_world.copy()

def make_part(name, bone, loc, scale, material):
    wloc = AW @ Vector(loc)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=1.0, location=wloc)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ob.data.materials.append(material)
    link(ob)
    ob.parent = arm
    ob.parent_type = "BONE"
    ob.parent_bone = bone
    m = ob.matrix_world.copy()
    ob.matrix_world = m
    for p in ob.data.polygons:
        p.use_smooth = True
    ob.select_set(False)
    return ob

PARTS = [
    ("K3_RUNNER_PELVIS",     "hips",  (0, 0, 0.208),      (0.046, 0.030, 0.036), PEARL),
    ("K3_RUNNER_TORSO",      "chest", (0, 0, 0.253),      (0.042, 0.028, 0.050), PEARL),
    ("K3_RUNNER_HEAD",       "head",  (0, -0.002, 0.313), (0.028, 0.028, 0.032), PEARL),
    ("K3_RUNNER_SHOULDER_L", "chest", (-0.058, 0, 0.262), (0.015, 0.015, 0.015), PEARL),
    ("K3_RUNNER_SHOULDER_R", "chest", (0.058, 0, 0.262),  (0.015, 0.015, 0.015), PEARL),
    ("K3_RUNNER_UPPERARM_L", "upper_arm.L", (-0.060, 0, 0.233), (0.011, 0.011, 0.035), PEARL),
    ("K3_RUNNER_UPPERARM_R", "upper_arm.R", (0.060, 0, 0.233),  (0.011, 0.011, 0.035), PEARL),
    ("K3_RUNNER_ELBOW_L",    "forearm.L", (-0.062, 0, 0.205),   (0.010, 0.010, 0.010), PEARL),
    ("K3_RUNNER_ELBOW_R",    "forearm.R", (0.062, 0, 0.205),    (0.010, 0.010, 0.010), PEARL),
    ("K3_RUNNER_FOREARM_L",  "forearm.L", (-0.063, 0, 0.178),   (0.0095, 0.0095, 0.032), PEARL),
    ("K3_RUNNER_FOREARM_R",  "forearm.R", (0.063, 0, 0.178),    (0.0095, 0.0095, 0.032), PEARL),
    ("K3_RUNNER_HAND_L",     "hand.L",  (-0.064, 0, 0.141), (0.0125, 0.0125, 0.014), PEARL),
    ("K3_RUNNER_HAND_R",     "hand.R",  (0.064, 0, 0.141),  (0.0125, 0.0125, 0.014), PEARL),
    ("K3_RUNNER_THIGH_L",    "thigh.L", (-0.028, 0, 0.150), (0.015, 0.015, 0.048), PEARL),
    ("K3_RUNNER_THIGH_R",    "thigh.R", (0.028, 0, 0.150),  (0.015, 0.015, 0.048), PEARL),
    ("K3_RUNNER_KNEE_L",     "shin.L",  (-0.029, 0, 0.105), (0.0125, 0.0125, 0.0125), PEARL),
    ("K3_RUNNER_KNEE_R",     "shin.R",  (0.029, 0, 0.105),  (0.0125, 0.0125, 0.0125), PEARL),
    ("K3_RUNNER_SHIN_L",     "shin.L",  (-0.029, 0, 0.063), (0.011, 0.011, 0.045), PEARL),
    ("K3_RUNNER_SHIN_R",     "shin.R",  (0.029, 0, 0.063),  (0.011, 0.011, 0.045), PEARL),
    ("K3_RUNNER_FOOT_L",     "foot.L",  (-0.029, -0.014, 0.008), (0.013, 0.030, 0.010), PEARL),
    ("K3_RUNNER_FOOT_R",     "foot.R",  (0.029, -0.014, 0.008),  (0.013, 0.030, 0.010), PEARL),
    ("K3_RUNNER_SOLE_L",     "foot.L",  (-0.029, -0.014, 0.002), (0.016, 0.034, 0.005), GRIP_L),
    ("K3_RUNNER_SOLE_R",     "foot.R",  (0.029, -0.014, 0.002),  (0.016, 0.034, 0.005), GRIP_R),
]
for name, bone, loc, scale, material in PARTS:
    make_part(name, bone, loc, scale, material)

# ---------------------------------------------------------------- cameras
def new_empty(name):
    ob = bpy.data.objects.new(name, None)
    coll.objects.link(ob)
    ob.empty_display_size = 0.04
    ob.parent = root
    return ob

cam_target = new_empty("K3_CAM_MAIN_TARGET")
cam_focus = new_empty("K3_CAM_MAIN_FOCUS")

def new_cam(name, lens, target, fstop=None):
    data = bpy.data.cameras.new(name + "_DATA")
    data.lens = lens
    data.clip_start = 0.01
    cam = bpy.data.objects.new(name, data)
    coll.objects.link(cam)
    cam.parent = root
    con = cam.constraints.new("TRACK_TO")
    con.name = "Track To"
    con.target = target
    if fstop:
        data.dof.use_dof = True
        data.dof.focus_object = cam_focus
        data.dof.aperture_fstop = fstop
    return cam

cam_main = new_cam("K3_CAM_MAIN", 58.0, cam_target, fstop=4.0)
cam_profile = new_cam("K3_CAM_DIAG_PROFILE", 50.0, cam_target)
cam_top = new_cam("K3_CAM_DIAG_TOP", 35.0, cam_target)
cam_normal = new_cam("K3_CAM_DIAG_NORMAL", 35.0, cam_target)
sc.camera = cam_main

# ---------------------------------------------------------------- lumieres
def new_light(name, ltype, energy, color, track=None, **kw):
    data = bpy.data.lights.new(name + "_DATA", ltype)
    data.energy = energy
    data.color = color
    for k, v in kw.items():
        setattr(data, k, v)
    ob = bpy.data.objects.new(name, data)
    coll.objects.link(ob)
    ob.parent = root
    if track:
        con = ob.constraints.new("TRACK_TO")
        con.name = "Track To"
        con.target = track
        con.track_axis = "TRACK_NEGATIVE_Z"
        con.up_axis = "UP_Y"
    return ob

MID = LOW + U * 1.1  # milieu de la zone de course
back = new_light("K3_LIGHT_BACKLIGHT", "AREA", 300.0, (0.9, 0.95, 1.0),
                 track=cam_target, shape="DISK", size=1.5)
back.location = MID + U * 0.9 + N * 1.0
sun = new_light("K3_LIGHT_SUN", "SUN", 2.5, (1.0, 0.95, 0.88))
sun.rotation_euler = (0.9, 0.15, -0.6)
glim_lime = new_light("K3_LIGHT_GLIMMER_LIME", "POINT", 40.0, (0.42, 1.0, 0.16),
                      shadow_soft_size=0.08)
glim_lime.location = MID - C * 0.30 + N * 0.06
glim_mag = new_light("K3_LIGHT_GLIMMER_MAGENTA", "POINT", 30.0, (1.0, 0.2, 0.58),
                     shadow_soft_size=0.08)
glim_mag.location = MID + C * 0.35 + N * 0.18
torso = new_light("K3_LIGHT_TORSO_RETURN", "POINT", 25.0, (1.0, 0.98, 0.95),
                  shadow_soft_size=0.12)
torso.location = MID + C * 0.45 - U * 0.30 + N * 0.35

# ---------------------------------------------------------------- timeline + audio
sc.frame_start = 1
sc.frame_end = 240
sc.render.resolution_x = 640
sc.render.resolution_y = 360

MASTER = "${BLENDER_AGENT_STUDIO_ROOT}/projects/fl-studio-box-semantic-template/media/current/master.mp4"
if not sc.sequence_editor:
    sc.sequence_editor_create()
try:
    sc.sequence_editor.sequences.new_sound(
        name="K3_MASTER_AUDIO", filepath=MASTER, channel=1, frame_start=1)
    print("AUDIO_MOUNTED")
except Exception as e:
    print("AUDIO_MOUNT_FAILED", repr(e))

sc.frame_set(1)
bpy.ops.wm.save_mainfile()
print("RUNNER_BUILT parts=", len(PARTS), "cams=4 lights=5")
