"""Build the K3 Fable runner: rigged pearl humanoid climbing the Piano Roll ramp.

Everything happens in the "slope frame": armature local space whose origin is the
plane origin of USTUDIO_PIANO_ROLL_FLOOR, X = UPHILL_TANGENT, Y = CROSS_SLOPE_TANGENT,
Z = SURFACE_NORMAL. The plane Z=0 IS the ramp surface, so sole coplanarity and
clearances are exact by construction. World gravity expressed in this frame is
(-0.723449, 0, -0.690377) — posture is governed by that vector, not by +Z.

Saves scene/trial.blend and writes diagnostics/motion-plan.json.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix, Vector

P = globals().get("UNRECORDED_PARAMS", {})
TRIAL = Path(P.get("trial_dir", ".")).resolve()

# ---------------------------------------------------------------- constants
U = Vector((0.0, 0.690377, 0.723449))    # uphill tangent (root frame)
C = Vector((-1.0, 0.0, 0.0))             # cross slope tangent
N = Vector((0.0, -0.723449, 0.690377))   # surface normal
O = Vector((0.0, 0.415, 1.755))          # plane origin (root frame)
V_A = Vector((0.723449, 0.0, 0.690377))  # world up in slope frame
G_A = -V_A                               # world gravity direction in slope frame
SLOPE_DEG = 46.34

FPS = 30
FRAME_END = 240
T_STEP = 12.1          # frames per footfall (148.7 bpm downbeat grid)
FIRST_LAND = 57.0      # first strong footfall (audio downbeat)
N_RUN_STEPS = 12       # landings on the beat: frames 57 .. 190.1
STEP_LEN = 0.13
V_RUN = STEP_LEN / T_STEP          # slope-distance per frame
CONTACT_FRAMES = 8.0
SWING_FRAMES = 2 * T_STEP - CONTACT_FRAMES  # 16.2

# character dimensions (meters)
ANKLE_H = 0.016
SHIN_L = 0.066
THIGH_L = 0.073
HIP_LAT = 0.024
PELVIS_Z = 0.165       # rest pelvis root height
SPINE1_TOP = 0.205
CHEST_TOP = 0.253
HEAD_TOP = 0.323
SHOULDER_LAT = 0.042
SHOULDER_Z = 0.245
UPARM_L = 0.052
FOREARM_L = 0.048
FOOT_FWD = 0.034       # ankle -> toe forward
FOOT_BACK = 0.014      # ankle -> heel
SOLE_TOP = 0.0025      # sole slab top (rest sole bottom at z=0.0005)
LEG_MAX = THIGH_L + SHIN_L - 0.004  # keep the knee bent, no hyperextension

# gait plan (slope coordinates)
S_START = -0.85        # pelvis s during opening still
FOOT_L_START = -0.88   # front foot (under the body)
FOOT_R_START = -0.92   # rear foot, braced downhill
H_STAND = 0.120
H_CROUCH = 0.106
H_RUN = 0.112
BOB_AMP = 0.008
SWAY_AMP = 0.006
LAND_OFFSET = 0.005    # foot lands slightly uphill of pelvis s

# ------------------------------------------------------------- easing utils
def clamp(x, a, b):
    return max(a, min(b, x))

def smoothstep(x):
    x = clamp(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)

def hermite(t, p0, p1, v0, v1, dur):
    """Cubic hermite on [0,1] with endpoint velocities given per-frame."""
    t = clamp(t, 0.0, 1.0)
    m0, m1 = v0 * dur, v1 * dur
    t2, t3 = t * t, t * t * t
    return ((2 * t3 - 3 * t2 + 1) * p0 + (t3 - 2 * t2 + t) * m0
            + (-2 * t3 + 3 * t2) * p1 + (t3 - t2) * m1)

# ------------------------------------------------------------- pelvis path s(f)
S_AT_57 = -0.774
S_AT_190 = S_AT_57 + V_RUN * (FIRST_LAND + (N_RUN_STEPS - 1) * T_STEP - FIRST_LAND)  # at f190.1

def pelvis_s(f):
    if f <= 16:
        return S_START
    if f <= 32:
        return hermite((f - 16) / 16.0, S_START, -0.840, 0.0, 0.0, 16.0)
    if f <= 44:
        return hermite((f - 32) / 12.0, -0.840, -0.844, 0.0, 0.0, 12.0)
    if f <= FIRST_LAND:
        return hermite((f - 44) / (FIRST_LAND - 44), -0.844, S_AT_57, 0.0, V_RUN, FIRST_LAND - 44)
    t_last = FIRST_LAND + (N_RUN_STEPS - 1) * T_STEP  # 190.1
    if f <= t_last:
        return S_AT_57 + V_RUN * (f - FIRST_LAND)
    if f <= 206:
        return hermite((f - t_last) / (206 - t_last), S_AT_190, 0.741, V_RUN, 0.0, 206 - t_last)
    if f <= 215:
        return hermite((f - 206) / 9.0, 0.741, 0.744, 0.0, 0.0, 9.0)
    return 0.744

def speed_factor(f):
    return clamp(abs(pelvis_s(f + 0.5) - pelvis_s(f - 0.5)) / V_RUN, 0.0, 1.2)

def pelvis_h(f):
    if f <= 16:
        base = H_STAND + 0.0015 * math.sin(2 * math.pi * (f - 1) / 52.0)
    elif f <= 32:
        base = hermite((f - 16) / 16.0, H_STAND, 0.117, 0.0, 0.0, 16.0)
    elif f <= 48:
        base = hermite((f - 32) / 16.0, 0.117, H_CROUCH, 0.0, 0.0, 16.0)
    elif f <= FIRST_LAND:
        base = hermite((f - 48) / 9.0, H_CROUCH, H_RUN, 0.0, 0.0, 9.0)
    elif f <= 190:
        base = H_RUN
    elif f <= 206:
        base = hermite((f - 190) / 16.0, H_RUN, H_STAND, 0.0, 0.0, 16.0)
    else:
        base = H_STAND + 0.0015 * math.sin(2 * math.pi * (f - 206) / 60.0)
    bob = -BOB_AMP * speed_factor(f) * math.cos(2 * math.pi * (f - 61.0) / T_STEP)
    return base + bob

def pelvis_y(f):
    return -SWAY_AMP * speed_factor(f) * math.cos(2 * math.pi * (f - 61.0) / (2 * T_STEP))

def torso_lean_deg(f):
    if f <= 16:
        lean = 10.0
    elif f <= 32:
        lean = hermite((f - 16) / 16.0, 10.0, 14.0, 0, 0, 16.0)
    elif f <= 48:
        lean = hermite((f - 32) / 16.0, 14.0, 16.5, 0, 0, 16.0)
    elif f <= FIRST_LAND:
        lean = hermite((f - 48) / 9.0, 16.5, 21.0, 0, 0, 9.0)
    elif f <= 190:
        lean = 21.0
    elif f <= 208:
        lean = hermite((f - 190) / 18.0, 21.0, 11.0, 0, 0, 18.0)
    elif f <= 224:
        lean = hermite((f - 208) / 16.0, 11.0, 9.0, 0, 0, 16.0)
    else:
        lean = 9.0
    lean += 1.5 * speed_factor(f) * math.sin(2 * math.pi * (f - 57.0) / T_STEP)
    lean += 0.8 * math.sin(2 * math.pi * f / 55.0) * (1.0 - speed_factor(f))  # breathing
    return lean

# ------------------------------------------------------------- foot schedules
# Contact list per foot: (land_frame, lift_frame, s_position). lift == None -> planted to end.
def build_contacts():
    lands_R, lands_L = [], []
    for n in range(N_RUN_STEPS):
        t_n = FIRST_LAND + n * T_STEP
        s_n = (S_AT_57 + V_RUN * (t_n - FIRST_LAND)) + LAND_OFFSET
        (lands_R if n % 2 == 0 else lands_L).append((t_n, s_n))
    contacts = {"L": [], "R": []}
    # L: planted from the start until its first swing (drive push-off).
    first_L_land = FIRST_LAND + 1 * T_STEP            # 69.1
    contacts["L"].append({"land": 1.0, "lift": first_L_land - SWING_FRAMES, "s": FOOT_L_START})
    # R: planted from start, lifts into the anticipation knee raise, lands on beat 57.
    contacts["R"].append({"land": 1.0, "lift": FIRST_LAND - SWING_FRAMES, "s": FOOT_R_START})
    for t_n, s_n in lands_L:
        contacts["L"].append({"land": t_n, "lift": t_n + CONTACT_FRAMES, "s": s_n})
    for t_n, s_n in lands_R:
        contacts["R"].append({"land": t_n, "lift": t_n + CONTACT_FRAMES, "s": s_n})
    # Deceleration: last L landing (f190.1) stays planted to the end.
    contacts["L"][-1]["lift"] = None
    # R settle step: lifts normally after its last beat landing (f178.1+8), lands uphill brace.
    contacts["R"].append({"land": 197.0, "lift": None, "s": 0.700})
    return contacts

CONTACTS = build_contacts()
FOOT_LAT = {"L": HIP_LAT, "R": -HIP_LAT}

def foot_state(foot, f):
    """Return (phase, s, h, toe_up_deg). phase: planted / swing / transition."""
    cs = CONTACTS[foot]
    for i, c in enumerate(cs):
        lift = c["lift"] if c["lift"] is not None else 1e9
        if c["land"] <= f < lift:
            phase = "planted"
            # one transition frame right at each boundary
            if f - c["land"] < 1.0 or lift - f < 1.0:
                phase = "transition"
            return phase, c["s"], 0.0, 0.0
        if i + 1 < len(cs) and lift <= f < cs[i + 1]["land"]:
            nxt = cs[i + 1]
            q = (f - lift) / (nxt["land"] - lift)
            s = c["s"] + (nxt["s"] - c["s"]) * smoothstep(q)
            h = 0.042 * (math.sin(math.pi * q) ** 0.8)
            toe_up = 12.0 * math.sin(math.pi * q)
            phase = "swing"
            if q < 0.06 or q > 0.94:
                phase = "transition"
            return phase, s, h, toe_up
    # before first / after last contact handled above; fallback: planted at last s
    return "planted", cs[-1]["s"], 0.0, 0.0

# ------------------------------------------------------------- scene setup
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = FRAME_END
scene.render.resolution_x = 640
scene.render.resolution_y = 360

root = bpy.data.objects["USTUDIO_BOX_FLOAT_ROOT"]
floor = bpy.data.objects["USTUDIO_PIANO_ROLL_FLOOR"]
floor["ustudio_grip_surface"] = 1.25
floor["ustudio_grip_note"] = "contrat d'adherence avec les semelles lime du coureur ; minimum requis tan(46.34deg)=1.048"

work_col = bpy.data.collections.new("K3_PIANOROLL_SLOPE_RUN_FABLE_V001_WORK")
scene.collection.children.link(work_col)

# audio in the VSE
if not scene.sequence_editor:
    scene.sequence_editor_create()
master = str((TRIAL / "../../fl-studio-box-semantic-template/media/current/master.mp4").resolve())
snd = scene.sequence_editor.strips.new_sound("K3_FABLE_AUDIO", master, 1, 1)
snd.frame_final_end = FRAME_END + 1
scene.sync_mode = "AUDIO_SYNC"

# ------------------------------------------------------------- armature
arm_data = bpy.data.armatures.new("K3_FABLE_RUNNER_RIG")
arm_obj = bpy.data.objects.new("K3_FABLE_RUNNER", arm_data)
work_col.objects.link(arm_obj)
arm_obj.parent = root
slope_mat = Matrix((
    (U.x, C.x, N.x, O.x),
    (U.y, C.y, N.y, O.y),
    (U.z, C.z, N.z, O.z),
    (0.0, 0.0, 0.0, 1.0),
))
arm_obj.matrix_basis = slope_mat
arm_obj["ustudio_grip_surface"] = 1.25
arm_obj["ustudio_grip_cause"] = "semelles grip lime, pulse d'emission uniquement au contact"

bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode="EDIT")

def add_bone(name, head, tail, parent=None, roll_hint=Vector((1, 0, 0))):
    b = arm_data.edit_bones.new(name)
    b.head, b.tail = Vector(head), Vector(tail)
    if parent:
        b.parent = arm_data.edit_bones[parent]
    b.align_roll(Vector(roll_hint))
    return b

Z_HINT = Vector((0, 0, 1))
X_HINT = Vector((1, 0, 0))
add_bone("ROOT", (0, 0, PELVIS_Z), (0, 0, SPINE1_TOP), None, X_HINT)
add_bone("SPINE1", (0, 0, SPINE1_TOP), (0, 0, CHEST_TOP - 0.018), "ROOT", X_HINT)
add_bone("CHEST", (0, 0, CHEST_TOP - 0.018), (0, 0, CHEST_TOP), "SPINE1", X_HINT)
add_bone("NECK_HEAD", (0, 0, CHEST_TOP), (0, 0, HEAD_TOP), "CHEST", X_HINT)
for side, sgn in (("L", 1), ("R", -1)):
    y_sh = sgn * SHOULDER_LAT
    add_bone(f"CLAV.{side}", (0, sgn * 0.012, SHOULDER_Z), (0, y_sh, SHOULDER_Z), "CHEST", Z_HINT)
    add_bone(f"UPPERARM.{side}", (0, y_sh, SHOULDER_Z), (0, y_sh, SHOULDER_Z - UPARM_L), f"CLAV.{side}", X_HINT)
    add_bone(f"FOREARM.{side}", (0, y_sh, SHOULDER_Z - UPARM_L), (0, y_sh, SHOULDER_Z - UPARM_L - FOREARM_L), f"UPPERARM.{side}", X_HINT)
    y_hip = sgn * HIP_LAT
    hip_z = PELVIS_Z - 0.010
    add_bone(f"THIGH.{side}", (0, y_hip, hip_z), (0, y_hip, hip_z - THIGH_L), "ROOT", X_HINT)
    add_bone(f"SHIN.{side}", (0, y_hip, hip_z - THIGH_L), (0, y_hip, ANKLE_H), f"THIGH.{side}", X_HINT)
    add_bone(f"FOOT.{side}", (0, y_hip, ANKLE_H), (FOOT_FWD, y_hip, 0.004), f"SHIN.{side}", Z_HINT)
bpy.ops.object.mode_set(mode="OBJECT")

REST = {b.name: b.matrix_local.copy() for b in arm_data.bones}
HIP_Z = PELVIS_Z - 0.010

# ------------------------------------------------------------- materials
def make_material(name, color, rough, emission=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 0.0
    return mat

pearl = make_material("M_K3_PEARL", (0.90, 0.90, 0.93), 0.42)
pearl.node_tree.nodes["Principled BSDF"].inputs["Coat Weight"].default_value = 0.35
LIME = (0.45, 1.0, 0.08)
sole_mats = {s: make_material(f"M_K3_SOLE_{s}", (0.30, 0.62, 0.06), 0.55, emission=LIME) for s in ("L", "R")}
for s, m in sole_mats.items():
    m["ustudio_grip_surface"] = 1.25

# ------------------------------------------------------------- mesh parts
parts = []

def add_box(name, group, center, size, material):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(material)
    vg = obj.vertex_groups.new(name=group)
    vg.add(range(len(obj.data.vertices)), 1.0, "REPLACE")
    parts.append(obj)
    return obj

def add_sphere(name, group, center, radius, material):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=center, segments=20, ring_count=12)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(material)
    vg = obj.vertex_groups.new(name=group)
    vg.add(range(len(obj.data.vertices)), 1.0, "REPLACE")
    parts.append(obj)
    return obj

add_box("part_pelvis", "ROOT", (0, 0, 0.176), (0.040, 0.066, 0.040), pearl)
add_box("part_belly", "SPINE1", (0.002, 0, 0.212), (0.038, 0.058, 0.034), pearl)
add_box("part_chest", "CHEST", (0.004, 0, 0.243), (0.044, 0.076, 0.036), pearl)
add_sphere("part_head", "NECK_HEAD", (0.004, 0, 0.294), 0.028, pearl)
add_sphere("part_waist", "SPINE1", (0.001, 0, SPINE1_TOP), 0.017, pearl)
add_sphere("part_neck", "NECK_HEAD", (0.004, 0, CHEST_TOP + 0.002), 0.013, pearl)
for side, sgn in (("L", 1), ("R", -1)):
    y_sh = sgn * SHOULDER_LAT
    y_hip = sgn * HIP_LAT
    add_sphere(f"part_shoulder_{side}", f"UPPERARM.{side}", (0, y_sh, SHOULDER_Z), 0.013, pearl)
    add_box(f"part_uparm_{side}", f"UPPERARM.{side}", (0, y_sh, SHOULDER_Z - UPARM_L / 2), (0.019, 0.019, UPARM_L), pearl)
    add_sphere(f"part_elbow_{side}", f"FOREARM.{side}", (0, y_sh, SHOULDER_Z - UPARM_L), 0.0115, pearl)
    add_box(f"part_forearm_{side}", f"FOREARM.{side}", (0, y_sh, SHOULDER_Z - UPARM_L - FOREARM_L / 2 - 0.004), (0.018, 0.018, FOREARM_L + 0.008), pearl)
    add_sphere(f"part_hip_{side}", f"THIGH.{side}", (0, y_hip, HIP_Z), 0.016, pearl)
    add_box(f"part_thigh_{side}", f"THIGH.{side}", (0, y_hip, HIP_Z - THIGH_L / 2), (0.027, 0.025, THIGH_L + 0.006), pearl)
    add_sphere(f"part_knee_{side}", f"SHIN.{side}", (0, y_hip, HIP_Z - THIGH_L), 0.0145, pearl)
    add_box(f"part_shin_{side}", f"SHIN.{side}", (0, y_hip, ANKLE_H + SHIN_L / 2), (0.022, 0.021, SHIN_L + 0.004), pearl)
    add_sphere(f"part_ankle_{side}", f"FOOT.{side}", (0, y_hip, ANKLE_H + 0.002), 0.011, pearl)
    add_box(f"part_foot_{side}", f"FOOT.{side}",
            ((FOOT_FWD - FOOT_BACK) / 2, y_hip, SOLE_TOP + (0.022 - SOLE_TOP) / 2),
            (FOOT_FWD + FOOT_BACK, 0.023, 0.022 - SOLE_TOP), pearl)
    add_box(f"part_sole_{side}", f"FOOT.{side}",
            ((FOOT_FWD - FOOT_BACK) / 2, y_hip, (SOLE_TOP + 0.0005) / 2),
            (FOOT_FWD + FOOT_BACK + 0.004, 0.026, SOLE_TOP - 0.0005), sole_mats[side])

for obj in parts:
    obj.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
body = bpy.context.active_object
body.name = "K3_FABLE_RUNNER_MESH"
for col in list(body.users_collection):
    col.objects.unlink(body)
work_col.objects.link(body)
bevel = body.modifiers.new("K3_BEVEL", "BEVEL")
bevel.width = 0.0022
bevel.segments = 2
bevel.limit_method = "ANGLE"
arm_mod = body.modifiers.new("K3_ARMATURE", "ARMATURE")
arm_mod.object = arm_obj
body.parent = arm_obj
body.matrix_basis = Matrix.Identity(4)
bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))

# ------------------------------------------------------------- pose helpers
def mat_from_y_z(head, y_dir, z_hint):
    y = y_dir.normalized()
    z = (z_hint - y * y.dot(z_hint))
    if z.length < 1e-6:
        z = Vector((0, 0, 1)) - y * y.z
    z.normalize()
    x = y.cross(z)
    m = Matrix((
        (x.x, y.x, z.x, head.x),
        (x.y, y.y, z.y, head.y),
        (x.z, y.z, z.z, head.z),
        (0, 0, 0, 1),
    ))
    return m

def solve_ik(hip, ankle, pole, l1, l2):
    e = ankle - hip
    d = e.length
    d = clamp(d, abs(l1 - l2) + 0.002, l1 + l2 - 0.0015)
    ehat = e.normalized()
    a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    r2 = max(l1 * l1 - a * a, 1e-8)
    r = math.sqrt(r2)
    f_perp = (pole - ehat * ehat.dot(pole))
    if f_perp.length < 1e-6:
        f_perp = Vector((1, 0, 0)) - ehat * ehat.x
    f_perp.normalize()
    knee = hip + ehat * a + f_perp * r
    return knee, d

def trunk_dir(lean_deg):
    """World-vertical tilted uphill by lean_deg, expressed in slope frame."""
    lam = math.radians(lean_deg)
    root_vec = Vector((0.0, math.sin(lam), math.cos(lam)))  # root frame, tilt toward +Y
    return Vector((root_vec.dot(U), root_vec.dot(C), root_vec.dot(N))).normalized()

pose = arm_obj.pose.bones
armature_bones = arm_data.bones
PARENT = {b.name: b.parent.name if b.parent else None for b in arm_data.bones}
DES = {}

def set_pose(name, desired, frame, key_location=False):
    """Basis from the parent's DESIRED matrix (never the stale evaluated pose)."""
    pb = pose[name]
    rest = REST[name]
    parent = PARENT[name]
    if parent:
        basis = rest.inverted() @ REST[parent] @ DES[parent].inverted() @ desired
    else:
        basis = rest.inverted() @ desired
    DES[name] = desired.copy()
    pb.matrix_basis = basis
    pb.keyframe_insert("rotation_quaternion", frame=frame)
    if key_location:
        pb.keyframe_insert("location", frame=frame)

for pb in pose:
    pb.rotation_mode = "QUATERNION"

# ------------------------------------------------------------- frame loop
plan = {"frames": [], "contacts": CONTACTS, "constants": {
    "T_STEP": T_STEP, "FIRST_LAND": FIRST_LAND, "STEP_LEN": STEP_LEN,
    "CONTACT_FRAMES": CONTACT_FRAMES, "H_RUN": H_RUN, "SOLE_REST_BOTTOM": 0.0005,
    "slope_deg": SLOPE_DEG}}
max_leg_stretch = 0.0
min_planned_toe_clearance = 1e9

for f in range(1, FRAME_END + 1):
    sf = speed_factor(f)
    s_p, h_p, y_p = pelvis_s(f), pelvis_h(f), pelvis_y(f)
    lean_chest = torso_lean_deg(f)
    lean_pelvis = 0.55 * lean_chest
    yaw = math.radians(6.5 * sf * math.sin(2 * math.pi * (f - 61.0) / (2 * T_STEP)))
    roll = math.radians(4.0 * sf * math.cos(2 * math.pi * (f - 61.0) / (2 * T_STEP)))

    # pelvis
    up_p = trunk_dir(lean_pelvis)
    fwd_hint = Vector((1, 0, 0))
    pelvis_head = Vector((s_p, y_p, h_p))
    m_pelvis = mat_from_y_z(pelvis_head, up_p, fwd_hint)
    m_pelvis = m_pelvis @ Matrix.Rotation(yaw, 4, "Y") @ Matrix.Rotation(roll, 4, "X")
    # NOTE bone Y = up axis, bone Z = forward hint, bone X = lateral
    set_pose("ROOT", m_pelvis, f, key_location=True)

    # spine chain: head of SPINE1 = pelvis pose applied to rest offset
    lean_mid = lean_pelvis + (lean_chest - lean_pelvis) * 0.55
    spine1_head = (m_pelvis @ REST["ROOT"].inverted()) @ REST["SPINE1"].translation
    m_spine1 = mat_from_y_z(spine1_head, trunk_dir(lean_mid), fwd_hint)
    m_spine1 = m_spine1 @ Matrix.Rotation(-yaw * 0.6, 4, "Y")
    set_pose("SPINE1", m_spine1, f)

    chest_head = (m_spine1 @ REST["SPINE1"].inverted()) @ REST["CHEST"].translation
    m_chest = mat_from_y_z(chest_head, trunk_dir(lean_chest), fwd_hint)
    m_chest = m_chest @ Matrix.Rotation(-yaw * 0.9, 4, "Y")
    set_pose("CHEST", m_chest, f)

    neck_head = (m_chest @ REST["CHEST"].inverted()) @ REST["NECK_HEAD"].translation
    m_neck = mat_from_y_z(neck_head, trunk_dir(max(lean_chest - 15.0, 4.0)), fwd_hint)
    set_pose("NECK_HEAD", m_neck, f)

    chest_delta = m_chest @ REST["CHEST"].inverted()

    # arms: swing opposite same-side leg (R leg lands at 57 -> R arm back at 57)
    for side, sgn in (("L", 1), ("R", -1)):
        clav_head = chest_delta @ REST[f"CLAV.{side}"].translation
        clav_tail_rest = Vector((0, sgn * SHOULDER_LAT, SHOULDER_Z))
        m_clav = mat_from_y_z(clav_head, (chest_delta.to_3x3() @ Vector((0, sgn, 0))), Z_HINT)
        set_pose(f"CLAV.{side}", m_clav, f)
        shoulder = chest_delta @ clav_tail_rest
        phase = 2 * math.pi * (f - FIRST_LAND) / (2 * T_STEP)
        swing = math.radians(10.0 + (38.0 * sf) * math.sin(phase + (math.pi if side == "R" else 0.0)))
        elbow_flex = math.radians(30.0 + 55.0 * sf + 10.0 * sf * math.sin(phase + (math.pi if side == "R" else 0.0) + 0.6))
        chest3 = m_chest.to_3x3()
        arm_down = (chest3 @ Vector((0, -1, 0))).normalized()      # bone frame: -Y is down along chest
        arm_fwd = (chest3 @ Vector((0, 0, 1))).normalized()        # chest z-hint = forward
        lat_axis = (chest3 @ Vector((1, 0, 0))).normalized()
        rot_sw = Matrix.Rotation(swing, 3, lat_axis)
        up_dir = rot_sw @ arm_down
        m_uparm = mat_from_y_z(shoulder, up_dir, arm_fwd)
        set_pose(f"UPPERARM.{side}", m_uparm, f)
        elbow = shoulder + up_dir * UPARM_L
        fore_dir = Matrix.Rotation(elbow_flex, 3, lat_axis) @ up_dir
        m_fore = mat_from_y_z(elbow, fore_dir, arm_fwd)
        set_pose(f"FOREARM.{side}", m_fore, f)

    # legs
    pelvis_delta = m_pelvis @ REST["ROOT"].inverted()
    frame_feet = {}
    for side, sgn in (("L", 1), ("R", -1)):
        phase_name, s_f, h_f, toe_up = foot_state(side, f)
        y_f = FOOT_LAT[side]
        ankle = Vector((s_f, y_f, ANKLE_H + h_f + 0.0005))
        hip = pelvis_delta @ Vector((0, sgn * HIP_LAT, HIP_Z))
        pole = (Vector((math.cos(yaw), math.sin(yaw), 0)) * 0.9 + Vector((0, 0, 0.45))).normalized()
        knee, d_used = solve_ik(hip, ankle, pole, THIGH_L, SHIN_L)
        max_leg_stretch = max(max_leg_stretch, (ankle - hip).length)
        m_thigh = mat_from_y_z(hip, (knee - hip), pole)
        set_pose(f"THIGH.{side}", m_thigh, f)
        m_shin = mat_from_y_z(knee, (ankle - knee), pole)
        set_pose(f"SHIN.{side}", m_shin, f)
        # foot: flat on plane during contact (delta identity = coplanar), toe-up in swing
        foot_dir_rest = (REST[f"FOOT.{side}"].to_3x3() @ Vector((0, 1, 0))).normalized()
        pitch = Matrix.Rotation(math.radians(toe_up), 3, Vector((0, -1, 0)))  # about -Y: toe up
        foot_dir = pitch @ foot_dir_rest
        foot_z = pitch @ Vector((0, 0, 1))
        m_foot = mat_from_y_z(ankle, foot_dir, foot_z)
        set_pose(f"FOOT.{side}", m_foot, f)
        toe = ankle + foot_dir * ((FOOT_FWD ** 2 + (ANKLE_H - 0.004) ** 2) ** 0.5)
        toe_clear = toe.z - 0.0005
        if phase_name == "swing":
            min_planned_toe_clearance = min(min_planned_toe_clearance, toe_clear)
        frame_feet[side] = {
            "phase": phase_name,
            "s": round(s_f, 6), "y": round(y_f, 6), "h": round(h_f, 6),
            "toe_up_deg": round(toe_up, 3),
        }

    plan["frames"].append({
        "frame": f,
        "pelvis": {"s": round(s_p, 6), "y": round(y_p, 6), "h": round(h_p, 6)},
        "lean_chest_deg": round(lean_chest, 3),
        "speed_factor": round(sf, 4),
        "feet": frame_feet,
    })

# ------------------------------------------------------------- sole pulses
for side in ("L", "R"):
    mat = sole_mats[side]
    strength = mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    def key(v, fr):
        strength.default_value = v
        strength.keyframe_insert("default_value", frame=fr)
    for c in CONTACTS[side]:
        land = c["land"]
        lift = c["lift"] if c["lift"] is not None else FRAME_END + 6
        if land <= 1.0:
            key(1.0, 1)
        else:
            key(0.0, land - 1.5)
            key(5.0, land + 0.2)
        key(1.0, min(land + 4.0, lift - 0.5))
        if lift < FRAME_END:
            key(0.6, lift - 0.5)
            key(0.0, lift + 1.0)
        else:
            key(0.9, FRAME_END)

# ------------------------------------------------------------- save + plan
out = TRIAL / "diagnostics" / "motion-plan.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(plan, ensure_ascii=False) + "\n", encoding="utf-8")

bpy.ops.wm.save_as_mainfile(filepath=str(TRIAL / "scene" / "trial.blend"))
print("UNRECORDED_RESULT=" + json.dumps({
    "bones": len(arm_data.bones),
    "mesh_objects": body.name,
    "max_leg_stretch": round(max_leg_stretch, 5),
    "leg_max_allowed": LEG_MAX,
    "min_planned_toe_clearance": round(min_planned_toe_clearance, 5),
    "frames_keyed": FRAME_END,
    "audio_strip": snd.name,
    "saved": True,
}, ensure_ascii=False))
