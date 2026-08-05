"""ETAPE 2 — 4 scenes : cameras, cibles, lumieres, markers, animation complete.

Grille temporelle (markers existants, 30 fps) :
  S1 EVEIL       1 -> 102   (USTUDIO_MEDIA_IN -> QUARTER)
  S2 PAUSE       102 -> 203 (QUARTER -> MIDDLE)
  S3 COURSE      203 -> 305 (MIDDLE -> THREE_QUARTERS, impact pile sur 305)
  S4 COMMUNION   305 -> 406 (THREE_QUARTERS -> OUT)

Conventions de pose (personnage face a -Y) :
  os verticaux descendants (bras/jambes) : -X = balancement avant, +X = arriere
  chaine spine ascendante : +X = penche avant, -X = arriere ; tete : -X = regarde en haut
  root : location (dx, dz, -dy), yaw = rotation_euler[1] (degres, + = vers +X)
  abduction bras : upper_arm.L +Z, upper_arm.R -Z

Sauvegarde uniquement la copie de travail.
"""
import bpy
from math import radians, sin, pi
from mathutils import Vector

WORK_FILE = "${BLENDER_AGENT_STUDIO_ROOT}/projects/fl-studio-box-character-animation/FL_Studio_Box_Character_Anim.blend"
assert bpy.data.filepath == WORK_FILE, f"Mauvais fichier ouvert : {bpy.data.filepath}"

sc = bpy.context.scene
root = bpy.data.objects["USTUDIO_BOX_FLOAT_ROOT"]
arm = bpy.data.objects["USTUDIO_CHAR_RIG"]
char_coll = bpy.data.collections["USTUDIO_CHARACTER"]
cam_coll = bpy.data.collections["CAMERA_RIG"]
light_coll = bpy.data.collections["LIGHTING"]

CAM_RIG_COLL = cam_coll

# ------------------------------------------------------------------ helpers
def update(frame):
    sc.frame_set(frame)
    bpy.context.view_layer.update()

def world_to_root_local(world, frame):
    update(frame)
    return root.matrix_world.inverted() @ Vector(world)

def world_to_arm(world, frame):
    update(frame)
    return arm.matrix_world.inverted() @ Vector(world)

def _hide_char_meshes(hide):
    for o in char_coll.objects:
        if o.type == "MESH":
            o.hide_set(hide)
    bpy.context.view_layer.update()

def floor_z(x, y, frame):
    """Z monde du sol (piano roll incline) au point (x, y), a la frame donnee.

    Le personnage est masque pendant le raycast pour ne pas s'auto-detecter.
    """
    update(frame)
    _hide_char_meshes(True)
    deps = bpy.context.evaluated_depsgraph_get()
    hit, loc, *_ = sc.ray_cast(deps, Vector((x, y, 5.0)), Vector((0, 0, -1)))
    _hide_char_meshes(False)
    if not hit:
        raise RuntimeError(f"raycast sol rate en ({x},{y}) f{frame}")
    return loc.z

def playhead_x(frame):
    """X local (espace FLOAT_ROOT) de la playhead, lineaire 1->397."""
    f = min(max(frame, 1), 397)
    return -2.78 + (f - 1) * (5.56 / 396.0)

def new_empty(name, coll):
    ob = bpy.data.objects.new(name, None)
    coll.objects.link(ob)
    ob.empty_display_size = 0.05
    return ob

def new_camera(name, lens, target, fstop=None):
    data = bpy.data.cameras.new(name + "_DATA")
    data.lens = lens
    cam = bpy.data.objects.new(name, data)
    cam_coll.objects.link(cam)
    con = cam.constraints.new("TRACK_TO")
    con.name = "Track To"
    con.target = target
    if fstop:
        data.dof.use_dof = True
        data.dof.focus_object = target
        data.dof.aperture_fstop = fstop
    return cam

def key(obj, path, frame, value):
    setattr(obj, path, value) if isinstance(path, str) else None

# ------------------------------------------------------------------ cameras + cibles
# cible S1 : tete du perso (statique locale, le perso pivote sur place)
s1_target = new_empty("USTUDIO_CAM_S1_TARGET", cam_coll)
s1_target.parent = root
s1_target.location = world_to_root_local((-1.8, 0.45, 3.30), 50)

cam_s1 = new_camera("USTUDIO_CAM_SCENE1_AWAKENING", 18.0, s1_target, fstop=2.8)
cam_s1.parent = root

# cible S2 : centre boite (monde, statique) — camera monde, plan poster symetrique
s2_target = new_empty("USTUDIO_CAM_S2_TARGET", cam_coll)
s2_target.location = (0.0, 0.3, 4.1)
cam_s2 = new_camera("USTUDIO_CAM_SCENE2_PAUSE", 55.0, s2_target, fstop=11.0)

# cible S3 : poitrine du perso en course (animee)
s3_target = new_empty("USTUDIO_CAM_S3_TARGET", cam_coll)
s3_target.parent = root
cam_s3 = new_camera("USTUDIO_CAM_SCENE3_RUN", 35.0, s3_target, fstop=4.0)
cam_s3.parent = root

# S4 : orbite (empty parente au root) + camera enfant + cible poitrine
s4_target = new_empty("USTUDIO_CAM_S4_TARGET", cam_coll)
s4_target.parent = root
s4_target.location = world_to_root_local((0.2, 0.5, 3.15), 350)

s4_orbit = new_empty("USTUDIO_CAM_S4_ORBIT", cam_coll)
s4_orbit.parent = root
s4_orbit.location = world_to_root_local((0.2, 0.5, 3.0), 350)

cam_s4 = new_camera("USTUDIO_CAM_SCENE4_COMMUNION", 32.0, s4_target, fstop=1.4)
cam_s4.parent = s4_orbit

# ------------------------------------------------------------------ lumieres de scene
# S1 : balayage rim quand la playhead passe (spot derriere le perso)
rim_data = bpy.data.lights.new("USTUDIO_S1_RIM_SWEEP_DATA", type="SPOT")
rim_data.energy = 0.0
rim_data.color = (0.75, 1.0, 0.6)
rim_data.spot_size = radians(50)
rim_data.spot_blend = 0.45
rim_data.shadow_soft_size = 0.05
rim = bpy.data.objects.new("USTUDIO_S1_RIM_SWEEP", rim_data)
light_coll.objects.link(rim)
rim.parent = root
rim.location = world_to_root_local((-1.8, 1.1, 4.6), 70)
con = rim.constraints.new("TRACK_TO")
con.name = "Track To"
con.target = s1_target
con.track_axis = "TRACK_NEGATIVE_Z"
con.up_axis = "UP_Y"

# S3 : flash d'impact
flash_data = bpy.data.lights.new("USTUDIO_S3_FLASH_DATA", type="POINT")
flash_data.energy = 0.0
flash_data.color = (0.7, 1.0, 0.55)
flash_data.shadow_soft_size = 0.3
flash = bpy.data.objects.new("USTUDIO_S3_FLASH", flash_data)
light_coll.objects.link(flash)
flash.parent = root
flash.location = world_to_root_local((1.45, 0.45, 3.6), 305)

# S4 : montee climax — le perso devient le point le plus lumineux
climax_data = bpy.data.lights.new("USTUDIO_S4_CLIMAX_DATA", type="POINT")
climax_data.energy = 0.0
climax_data.color = (1.0, 0.95, 0.85)
climax_data.shadow_soft_size = 0.25
climax = bpy.data.objects.new("USTUDIO_S4_CLIMAX", climax_data)
light_coll.objects.link(climax)
climax.parent = root
climax.location = world_to_root_local((0.2, 0.15, 3.6), 350)

# ------------------------------------------------------------------ markers cameras
for name, frame, cam in [
    ("USTUDIO_SCENE1_AWAKENING", 1, cam_s1),
    ("USTUDIO_SCENE2_PAUSE", 102, cam_s2),
    ("USTUDIO_SCENE3_RUN", 203, cam_s3),
    ("USTUDIO_SCENE4_COMMUNION", 305, cam_s4),
]:
    if name in sc.timeline_markers:
        sc.timeline_markers.remove(sc.timeline_markers[name])
    m = sc.timeline_markers.new(name, frame=frame)
    m.camera = cam
sc.camera = cam_s1

# ==================================================================
# ANIMATION PERSONNAGE
# ==================================================================
pb = {b.name: b for b in arm.pose.bones}
ALL_POSE_BONES = [n for n in pb if n != "root"]

def key_pose(frame, pose):
    """pose : {bone: (x, y, z) degres}. Les os absents sont keyes a zero."""
    for name in ALL_POSE_BONES:
        e = pose.get(name, (0.0, 0.0, 0.0))
        pb[name].rotation_euler = (radians(e[0]), radians(e[1]), radians(e[2]))
        pb[name].keyframe_insert("rotation_euler", frame=frame)

def key_root(frame, world_xy, world_z, yaw_deg):
    p_arm = world_to_arm((world_xy[0], world_xy[1], world_z), frame)
    r = pb["root"]
    r.location = (p_arm.x, p_arm.z, -p_arm.y)
    r.rotation_euler = (0.0, radians(yaw_deg), 0.0)
    r.keyframe_insert("location", frame=frame)
    r.keyframe_insert("rotation_euler", frame=frame)

def track_floor(scene_frames, x_of, y=0.45, step=8):
    """Keys root x/y/z echantillonnes pour coller au sol qui flotte."""
    for f in scene_frames:
        z = floor_z(x_of(f), y, f)
        yield f, x_of(f), z

# ---------------- S1 EVEIL (1-102) : debout, leve la tete, pivote -150°
s1_x, s1_y = -1.8, 0.45
for f in range(1, 102, 8):
    z = floor_z(s1_x, s1_y, f)
    yaw = -150.0 * (f - 1) / 101.0
    key_root(f, (s1_x, s1_y), z, yaw)
key_root(101, (s1_x, s1_y), floor_z(s1_x, s1_y, 101), -150.0)

key_pose(1,   {"head": (10, 0, 0), "chest": (4, 0, 0)})
key_pose(35,  {"head": (-30, 0, 0), "chest": (-4, 0, 0)})
key_pose(70,  {"head": (-26, 0, 0), "chest": (-6, 0, 0)})
key_pose(102, {"head": (-18, 0, 0), "chest": (-8, 0, 0),
               "upper_arm.L": (0, 0, 20), "upper_arm.R": (0, 0, -20)})

# ---------------- S2 PAUSE (102-203) : assis sur le cadre avant, pied qui bat
s2_x, s2_y = 0.0, -0.72
def rim_top(frame):
    update(frame)
    _hide_char_meshes(True)
    deps = bpy.context.evaluated_depsgraph_get()
    hit, loc, *_ = sc.ray_cast(deps, Vector((s2_x, s2_y, 4.0)), Vector((0, 0, -1)))
    _hide_char_meshes(False)
    if not hit:
        raise RuntimeError(f"raycast cadre rate f{frame}")
    return loc.z

sit_pose = {
    "thigh.L": (-78, 0, 0), "thigh.R": (-78, 0, 0),
    "shin.L": (72, 0, 0), "shin.R": (72, 0, 0),
    "foot.L": (6, 0, 0),
    "chest": (-12, 0, 0), "spine": (-6, 0, 0),
    "head": (-4, 0, 0),
    "upper_arm.L": (42, 0, 8), "upper_arm.R": (42, 0, -8),
    "forearm.L": (18, 0, 0), "forearm.R": (18, 0, 0),
}
for f in list(range(102, 204, 8)) + [203]:
    key_root(f, (s2_x, s2_y), rim_top(f) - 0.148, 0.0)
    key_pose(f, sit_pose) if f in (102, 203) else None

# pied R qui bat le tempo (~138 BPM => battement toutes les 13 frames)
f = 108.0
tap_up = True
while f < 200:
    fr = round(f)
    pose = dict(sit_pose)
    pose["foot.R"] = (28 if tap_up else -4, 0, 0)
    key_pose(fr, pose)
    tap_up = not tap_up
    f += 13.04 / 2.0

# ---------------- S3 COURSE (203-305) : fuite devant la playhead, impact a 305
s3_y = 0.45
def char_x(f):
    if f <= 203:
        return 0.35
    if f >= 305:
        return 1.45
    return 0.35 + (1.45 - 0.35) * (f - 203) / 102.0

stride = 10.0  # frames par cycle
for f in range(203, 306, 5):
    z = floor_z(char_x(f), s3_y, f)
    bob = 0.018 * sin(2 * pi * (f - 203) / stride)
    key_root(f, (char_x(f), s3_y), z + bob + 0.01, 90.0)  # yaw +90 => face a +X

lookbacks = {225: 55, 232: 0, 255: 55, 262: 0, 285: 60, 292: 0}
for f in range(203, 306, 5):
    ph = 2 * pi * (f - 203) / stride
    swing = 38 * sin(ph)
    lb = 0
    for k in sorted(lookbacks):
        if f >= k:
            lb = lookbacks[k]
    key_pose(f, {
        "thigh.L": (-swing, 0, 0), "thigh.R": (swing, 0, 0),
        "shin.L": (max(0.0, 50 * sin(ph + 1.2)), 0, 0),
        "shin.R": (max(0.0, 50 * sin(ph + pi + 1.2)), 0, 0),
        "foot.L": (-10, 0, 0), "foot.R": (-10, 0, 0),
        "upper_arm.L": (swing * 0.8, 0, 6), "upper_arm.R": (-swing * 0.8, 0, -6),
        "forearm.L": (-45, 0, 0), "forearm.R": (-45, 0, 0),
        "chest": (18, 0, 0), "spine": (8, 0, 0),
        "head": (-8, lb, 0),
    })

# impact a 305 : secousse puis affaissement (deborde sur l'ouverture de S4)
key_pose(303, {"chest": (18, 0, 0), "head": (-8, 0, 0)})
key_pose(307, {"chest": (34, 0, 0), "spine": (14, 0, 0), "head": (22, 0, 0),
               "upper_arm.L": (30, 0, 25), "upper_arm.R": (30, 0, -25),
               "thigh.L": (0, 0, 0), "thigh.R": (0, 0, 0),
               "shin.L": (0, 0, 0), "shin.R": (0, 0, 0)})
key_pose(315, {"chest": (28, 0, 0), "spine": (12, 0, 0), "head": (30, 0, 0)})

# ---------------- S4 COMMUNION (305-406) : accroupi main au sol, se redresse
s4_x, s4_y = 0.2, 0.5
crouch_drop = 0.115
crouch_pose = {
    "thigh.L": (-82, 0, 0), "thigh.R": (-82, 0, 0),
    "shin.L": (104, 0, 0), "shin.R": (104, 0, 0),
    "foot.L": (-22, 0, 0), "foot.R": (-22, 0, 0),
    "chest": (24, 0, 0), "spine": (10, 0, 0), "head": (12, 0, 0),
    "upper_arm.R": (-68, 0, -10), "forearm.R": (-24, 0, 0),
    "upper_arm.L": (14, 0, 10), "forearm.L": (8, 0, 0),
}
hero_pose = {
    "thigh.L": (0, 0, 0), "thigh.R": (0, 0, 0),
    "shin.L": (0, 0, 0), "shin.R": (0, 0, 0),
    "foot.L": (0, 0, 0), "foot.R": (0, 0, 0),
    "chest": (-8, 0, 0), "spine": (-4, 0, 0), "head": (-22, 0, 0),
    "upper_arm.L": (0, 0, 26), "upper_arm.R": (0, 0, -26),
    "forearm.L": (-10, 0, 0), "forearm.R": (-10, 0, 0),
}
slump_pose = {k: v for k, v in crouch_pose.items()}
slump_pose.update({
    "thigh.L": (-20, 0, 0), "thigh.R": (-20, 0, 0),
    "shin.L": (28, 0, 0), "shin.R": (28, 0, 0),
    "foot.L": (0, 0, 0), "foot.R": (0, 0, 0),
    "chest": (28, 0, 0), "spine": (12, 0, 0), "head": (30, 0, 0),
    "upper_arm.R": (10, 0, -6), "forearm.R": (6, 0, 0),
    "upper_arm.L": (10, 0, 6), "forearm.L": (6, 0, 0),
})

for f in list(range(305, 407, 8)) + [406]:
    z = floor_z(s4_x, s4_y, f)
    if f < 318:
        drop = 0.03        # reste debout mais affaisse juste apres l'impact
    elif f < 332:
        drop = crouch_drop # accroupi, main au sol
    elif f < 392:
        drop = crouch_drop * (392 - f) / 60.0  # remontee progressive
    else:
        drop = 0.0
    key_root(f, (s4_x, s4_y), z + drop * 0 + (0 if drop == 0 else -drop) + 0.0, 0.0)
# yaw : face avant (-Y) pendant toute la communion
key_pose(305, slump_pose)
key_pose(318, slump_pose)
key_pose(332, crouch_pose)
key_pose(360, crouch_pose)
key_pose(392, hero_pose)
key_pose(406, hero_pose)

# ==================================================================
# ANIMATION CAMERAS
# ==================================================================
def key_cam_local(cam, frame, world_pos):
    local = world_to_root_local(world_pos, frame)
    cam.location = local
    cam.keyframe_insert("location", frame=frame)

# S1 : worm's eye, push-in lent + leger rehaussement
for f, pos in [(1, (-1.80, -0.30, 3.02)), (50, (-1.79, -0.14, 3.06)),
               (102, (-1.74, 0.04, 3.12))]:
    key_cam_local(cam_s1, f, pos)
# tilt-up : la cible monte doucement
for f, zoff in [(1, -0.06), (102, 0.22)]:
    loc = world_to_root_local((-1.8, 0.45, 3.30 + zoff), f)
    s1_target.location = loc
    s1_target.keyframe_insert("location", frame=f)

# S2 : plan large frontal symetrique, push-in imperceptible (monde, non parente)
for f, pos in [(102, (0.0, -26.0, 4.45)), (203, (0.0, -24.9, 4.40))]:
    cam_s2.location = pos
    cam_s2.keyframe_insert("location", frame=f)

# S3 : tracking frontal, la camera recule devant lui, shake croissant
def jitter(f, amp):
    return amp * (sin(f * 1.7) + sin(f * 2.9 + 1.3) + sin(f * 4.3 + 2.1)) / 3.0

for f in range(203, 306, 3):
    amp = 0.004 + 0.030 * max(0.0, (f - 203) / 102.0) ** 2
    offset = 0.85
    if f >= 303:
        offset = 0.55  # speed ramp : la camera se rapproche d'un coup
    cx = char_x(f) + offset + jitter(f, amp)
    cy = 0.40 + jitter(f + 40, amp * 0.6)
    cz = floor_z(char_x(f), s3_y, f) + 0.26 + jitter(f + 80, amp * 0.5)
    key_cam_local(cam_s3, f, (cx, cy, cz))
    tloc = world_to_root_local((char_x(f), s3_y, floor_z(char_x(f), s3_y, f) + 0.22), f)
    s3_target.location = tloc
    s3_target.keyframe_insert("location", frame=f)

# S4 : orbite 360 spirale descendante-resserrante
for f, ang_deg, radius, height, lens in [
    (305, 0.0, 2.4, 1.9, 32.0),
    (356, 180.0, 1.35, 0.75, 50.0),
    (406, 360.0, 0.55, 0.05, 85.0),
]:
    s4_orbit.rotation_euler = (0.0, 0.0, radians(ang_deg))
    s4_orbit.keyframe_insert("rotation_euler", frame=f)
    cam_s4.location = (0.0, -radius, height)
    cam_s4.keyframe_insert("location", frame=f)
    cam_s4.data.lens = lens
    cam_s4.data.keyframe_insert("lens", frame=f)

# ==================================================================
# ANIMATION LUMIERES
# ==================================================================
# S1 rim sweep : suit la playhead (~f70 a x=-1.8), balaie la silhouette
for f, energy, x in [(50, 0.0, -2.15), (70, 900.0, -1.80), (88, 0.0, -1.45)]:
    rim_data.energy = energy
    rim_data.keyframe_insert("energy", frame=f)
    loc = world_to_root_local((x, 1.1, 4.6), f)
    rim.location = loc
    rim.keyframe_insert("location", frame=f)

# S3 flash : pic pile sur 305
for f, energy in [(300, 0.0), (304, 700.0), (306, 220.0), (312, 0.0)]:
    flash_data.energy = energy
    flash_data.keyframe_insert("energy", frame=f)

# S4 climax : montee 340 -> 406
for f, energy in [(330, 0.0), (360, 60.0), (385, 160.0), (406, 320.0)]:
    climax_data.energy = energy
    climax_data.keyframe_insert("energy", frame=f)

# retour frame 1 + sauvegarde
update(1)
bpy.ops.wm.save_mainfile()
print("SCENES_BUILT cameras=4 markers=4 lights=3")
