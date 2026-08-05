"""ETAPE 1 — construction du personnage USTUDIO_CHAR dans la copie de travail.

- Mannequin blanc mat ~0,35 m, sans visage, parties arrondies parentees aux os.
- Rig FK minimal : root / hips / spine / chest / neck / head, bras et jambes FK.
- Collection dediee USTUDIO_CHARACTER. Armature parentee a USTUDIO_BOX_FLOAT_ROOT.
- Le personnage fait face a -Y au repos (vers l'avant de la boite).

Sauvegarde le fichier de travail (la copie), jamais le template.
"""
import bpy
from mathutils import Vector

WORK_FILE = "${BLENDER_AGENT_STUDIO_ROOT}/projects/fl-studio-box-character-animation/FL_Studio_Box_Character_Anim.blend"
assert bpy.data.filepath == WORK_FILE, f"Mauvais fichier ouvert : {bpy.data.filepath}"

CHAR_COLLECTION = "USTUDIO_CHARACTER"
RIG_NAME = "USTUDIO_CHAR_RIG"
MAT_NAME = "M_CHAR_WHITE"

# ---------------------------------------------------------------- collection
if CHAR_COLLECTION in bpy.data.collections:
    raise SystemExit(f"{CHAR_COLLECTION} existe deja — abandon pour ne pas dupliquer.")
coll = bpy.data.collections.new(CHAR_COLLECTION)
bpy.context.scene.collection.children.link(coll)

def link_to_char_coll(obj):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)

# ---------------------------------------------------------------- materiau
mat = bpy.data.materials.new(MAT_NAME)
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.92, 0.92, 0.94, 1.0)
bsdf.inputs["Roughness"].default_value = 0.55
bsdf.inputs["Metallic"].default_value = 0.0
bsdf.inputs["IOR"].default_value = 1.45

# ---------------------------------------------------------------- armature
arm_data = bpy.data.armatures.new(RIG_NAME + "_DATA")
arm = bpy.data.objects.new(RIG_NAME, arm_data)
coll.objects.link(arm)

# parente au float root, transform monde conserve
float_root = bpy.data.objects["USTUDIO_BOX_FLOAT_ROOT"]
arm.parent = float_root
arm.matrix_parent_inverse = float_root.matrix_world.inverted()

bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")

# (name, head, tail, parent, connected) — coords armature, perso face a -Y
BONES = [
    ("root",        (0, 0, 0.0),     (0, 0, 0.06),     None,    False),
    ("hips",        (0, 0, 0.185),   (0, 0, 0.220),    "root",  False),
    ("spine",       (0, 0, 0.220),   (0, 0, 0.250),    "hips",  True),
    ("chest",       (0, 0, 0.250),   (0, 0, 0.285),    "spine", True),
    ("neck",        (0, 0, 0.285),   (0, 0, 0.300),    "chest", True),
    ("head",        (0, 0, 0.300),   (0, 0, 0.345),    "neck",  True),
    ("upper_arm.L", (-0.058, 0, 0.268), (-0.062, 0, 0.208), "chest", False),
    ("forearm.L",   (-0.062, 0, 0.208), (-0.064, 0, 0.152), "upper_arm.L", True),
    ("hand.L",      (-0.064, 0, 0.152), (-0.064, 0, 0.128), "forearm.L", True),
    ("upper_arm.R", (0.058, 0, 0.268),  (0.062, 0, 0.208),  "chest", False),
    ("forearm.R",   (0.062, 0, 0.208),  (0.064, 0, 0.152),  "upper_arm.R", True),
    ("hand.R",      (0.064, 0, 0.152),  (0.064, 0, 0.128),  "forearm.R", True),
    ("thigh.L",     (-0.026, 0, 0.185), (-0.028, 0, 0.100), "hips", False),
    ("shin.L",      (-0.028, 0, 0.100), (-0.028, 0, 0.022), "thigh.L", True),
    ("foot.L",      (-0.028, 0, 0.022), (-0.028, -0.045, 0.006), "shin.L", True),
    ("thigh.R",     (0.026, 0, 0.185),  (0.028, 0, 0.100),  "hips", False),
    ("shin.R",      (0.028, 0, 0.100),  (0.028, 0, 0.022),  "thigh.R", True),
    ("foot.R",      (0.028, 0, 0.022),  (0.028, -0.045, 0.006), "shin.R", True),
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
def make_part(name, bone, loc, scale, segments=24, rings=16):
    """Sphere UV etiree, parentee a un os (position monde imposee)."""
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments, ring_count=rings, radius=1.0, location=loc)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ob.data.materials.append(mat)
    link_to_char_coll(ob)
    ob.parent = arm
    ob.parent_type = "BONE"
    ob.parent_bone = bone
    m = ob.matrix_world.copy()  # conserve la pose monde voulue
    ob.matrix_world = m
    ob.select_set(False)
    return ob

PARTS = [
    # nom, os, centre, echelle (rayons)
    ("USTUDIO_CHAR_PELVIS",    "hips",  (0, 0, 0.200),      (0.045, 0.030, 0.036)),
    ("USTUDIO_CHAR_TORSO",     "chest", (0, 0, 0.252),      (0.041, 0.028, 0.052)),
    ("USTUDIO_CHAR_HEAD",      "head",  (0, -0.002, 0.321), (0.030, 0.030, 0.034)),
    ("USTUDIO_CHAR_SHOULDER_L","chest", (-0.058, 0, 0.268), (0.015, 0.015, 0.015)),
    ("USTUDIO_CHAR_SHOULDER_R","chest", (0.058, 0, 0.268),  (0.015, 0.015, 0.015)),
    ("USTUDIO_CHAR_UPPERARM_L","upper_arm.L", (-0.060, 0, 0.238), (0.011, 0.011, 0.036)),
    ("USTUDIO_CHAR_UPPERARM_R","upper_arm.R", (0.060, 0, 0.238),  (0.011, 0.011, 0.036)),
    ("USTUDIO_CHAR_ELBOW_L",   "forearm.L", (-0.062, 0, 0.208),   (0.010, 0.010, 0.010)),
    ("USTUDIO_CHAR_ELBOW_R",   "forearm.R", (0.062, 0, 0.208),    (0.010, 0.010, 0.010)),
    ("USTUDIO_CHAR_FOREARM_L", "forearm.L", (-0.063, 0, 0.180),   (0.0095, 0.0095, 0.032)),
    ("USTUDIO_CHAR_FOREARM_R", "forearm.R", (0.063, 0, 0.180),    (0.0095, 0.0095, 0.032)),
    ("USTUDIO_CHAR_HAND_L",    "hand.L",  (-0.064, 0, 0.140), (0.0125, 0.0125, 0.014)),
    ("USTUDIO_CHAR_HAND_R",    "hand.R",  (0.064, 0, 0.140),  (0.0125, 0.0125, 0.014)),
    ("USTUDIO_CHAR_THIGH_L",   "thigh.L", (-0.027, 0, 0.143), (0.0145, 0.0145, 0.048)),
    ("USTUDIO_CHAR_THIGH_R",   "thigh.R", (0.027, 0, 0.143),  (0.0145, 0.0145, 0.048)),
    ("USTUDIO_CHAR_KNEE_L",    "shin.L",  (-0.028, 0, 0.100), (0.0125, 0.0125, 0.0125)),
    ("USTUDIO_CHAR_KNEE_R",    "shin.R",  (0.028, 0, 0.100),  (0.0125, 0.0125, 0.0125)),
    ("USTUDIO_CHAR_SHIN_L",    "shin.L",  (-0.028, 0, 0.061), (0.011, 0.011, 0.044)),
    ("USTUDIO_CHAR_SHIN_R",    "shin.R",  (0.028, 0, 0.061),  (0.011, 0.011, 0.044)),
    ("USTUDIO_CHAR_FOOT_L",    "foot.L",  (-0.028, -0.014, 0.008), (0.013, 0.030, 0.010)),
    ("USTUDIO_CHAR_FOOT_R",    "foot.R",  (0.028, -0.014, 0.008),  (0.013, 0.030, 0.010)),
]
for name, bone, loc, scale in PARTS:
    make_part(name, bone, loc, scale)

bpy.ops.object.shade_smooth_by_angle() if False else None
# shade smooth sur toutes les parties
for ob in coll.objects:
    if ob.type == "MESH":
        for poly in ob.data.polygons:
            poly.use_smooth = True

bpy.ops.wm.save_mainfile()
print("CHARACTER_BUILT", len(coll.objects), "objets dans", CHAR_COLLECTION)
