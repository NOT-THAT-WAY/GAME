# Build the SB_Idle master .blend from the immutable source FBX.
#
# Why ad hoc bpy: no versioned workflow in workflows/catalog/ authors a character
# idle cycle. hover-loop.json is a prop-hover recipe, not a skinned-rig clip.
#
# The source FBX is opened read-only and never written. The only file written is
# the declared master .blend passed as argv[1].
#
# Loop policy: every channel is a sum of harmonics of period 60 frames, evaluated
# at theta = 2*pi*(f-1)/60. Therefore pose(f+60) == pose(f) exactly, frame 60 is
# NOT a copy of frame 1, and the 60->1 wrap is an ordinary 1/30 s step that is
# continuous in position AND velocity (C-infinity), not a patched seam.
#
# Usage:
#   blender -b --factory-startup --python build_sb_idle.py -- <src.fbx> <out.blend>

import bpy, sys, math
from mathutils import Vector, Matrix, Quaternion

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT_BLEND = argv[0], argv[1]

FPS = 30
F_START, F_END = 1, 60
PERIOD = 60.0  # frames; pose(f + PERIOD) == pose(f)

BODY = "BAS_PUNCH_body"
ROOT = "BAS_PUNCH_root"
FEET = ["BAS_PUNCH_foot.L", "BAS_PUNCH_foot.R"]
ARMS = [("BAS_PUNCH_upperarm.L", "BAS_PUNCH_forearm.L", "BAS_PUNCH_hand.L"),
        ("BAS_PUNCH_upperarm.R", "BAS_PUNCH_forearm.R", "BAS_PUNCH_hand.R")]

# ---- motion amplitudes (metres / degrees), tuned against the measured
# ---- 0.071 m body-to-foot vertical clearance of the rest pose ----
A_BREATH_1 = 0.010     # m, world Z, fundamental
A_BREATH_2 = 0.0028    # m, world Z, 2nd harmonic -> asymmetric inhale/exhale
PH_BREATH_2 = 0.9      # rad
A_SWAY_X = 0.008       # m, world X, weight transfer
A_FWD_Y = 0.0035       # m, world Y, 2nd harmonic
D_ROLL = 1.5           # deg about world Y, lean toward the loaded foot
D_PITCH = 0.7          # deg about world X
D_YAW = 0.9            # deg about world Z
PH_YAW = math.pi / 3.0

A_ARM_SWING = 2.5      # deg about world X, independent arm life
ARM_LAG = [5.0, 8.0, 10.0]    # frames of drag: upperarm, forearm, hand
ARM_DRAG_K = [0.6, 0.5, 0.4]  # how much of the body's lagged rotation each level takes

# ---------------------------------------------------------------- scene setup
bpy.ops.wm.read_factory_settings(use_empty=True)
for coll in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights,
             bpy.data.materials, bpy.data.armatures, bpy.data.actions):
    for db in list(coll):
        coll.remove(db)

bpy.ops.import_scene.fbx(filepath=SRC)

sc = bpy.context.scene
sc.render.fps = FPS
sc.render.fps_base = 1.0
sc.frame_start = F_START
sc.frame_end = F_END
sc.unit_settings.system = "METRIC"
sc.unit_settings.scale_length = 1.0
# The FBX take name is derived from the scene name when a single action is
# exported; naming the scene SB_Idle makes Unity see the clip as SB_Idle.
sc.name = "SB_Idle"

arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")

# Preserve, without modifying, the existing Punch placeholder action.
punch = None
for a in bpy.data.actions:
    if "punch" in a.name.lower():
        punch = a
        a.use_fake_user = True  # keep it in the .blend; contents untouched

# Detach it so SB_Idle is authored from the true bind pose.
if arm.animation_data:
    arm.animation_data.action = None
arm.location = (0, 0, 0)
arm.rotation_euler = (0, 0, 0)
arm.scale = (1, 1, 1)
arm.animation_data_clear()

for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
    pb.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()

# Rest (bind) armature-space matrices, captured before any posing.
REST = {b.name: b.matrix_local.copy() for b in arm.data.bones}


# ---------------------------------------------------------------- motion model
def theta(f, lag_frames=0.0):
    return 2.0 * math.pi * ((f - 1) - lag_frames) / PERIOD


def body_world_rotation(th):
    """Body orientation as a world-space quaternion. Periodic in th."""
    qx = Quaternion(Vector((1, 0, 0)), math.radians(-D_PITCH) * math.sin(th))
    qy = Quaternion(Vector((0, 1, 0)), math.radians(D_ROLL) * math.cos(th))
    qz = Quaternion(Vector((0, 0, 1)), math.radians(D_YAW) * math.sin(th + PH_YAW))
    return qz @ qy @ qx


def body_world_offset(th):
    return Vector((
        A_SWAY_X * math.cos(th),
        A_FWD_Y * math.sin(2.0 * th),
        A_BREATH_1 * math.sin(th) + A_BREATH_2 * math.sin(2.0 * th + PH_BREATH_2),
    ))


def rotate_about_head(mat, quat):
    """Apply world-space rotation `quat` about the bone head held in `mat`."""
    head = mat.translation.copy()
    return (Matrix.Translation(head) @ quat.to_matrix().to_4x4()
            @ Matrix.Translation(-head) @ mat)


# ---------------------------------------------------------------- pose + key
def pose_frame(f):
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()

    th = theta(f)

    # body: world offset + world rotation about its own head
    pb_body = arm.pose.bones[BODY]
    m = rotate_about_head(REST[BODY], body_world_rotation(th))
    m = Matrix.Translation(body_world_offset(th)) @ m
    pb_body.matrix = m
    bpy.context.view_layer.update()

    # arms: progressive drag. Each level takes a fraction of the body rotation
    # it would have had ARM_LAG[i] frames ago, relative to the level above it.
    for chain in ARMS:
        prev_lag = 0.0
        for i, bone_name in enumerate(chain):
            lag = ARM_LAG[i]
            k = ARM_DRAG_K[i]
            # rotation the body had at `lag` vs at `prev_lag`
            q_target = body_world_rotation(theta(f, lag))
            q_from = body_world_rotation(theta(f, prev_lag))
            q_drag = q_target @ q_from.inverted()
            q_drag = Quaternion().slerp(q_drag, k)

            if i == 0:  # independent swing lives on the upper arm only
                q_swing = Quaternion(Vector((1, 0, 0)),
                                     math.radians(A_ARM_SWING) * math.sin(theta(f, lag)))
                q_drag = q_drag @ q_swing

            pb = arm.pose.bones[bone_name]
            pb.matrix = rotate_about_head(pb.matrix.copy(), q_drag)
            bpy.context.view_layer.update()
            prev_lag = lag

    # root and feet stay exactly at rest -> zero root motion, planted feet.
    for name in [ROOT] + FEET:
        arm.pose.bones[name].matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()

    # Key every bone so the clip fully overrides any previous pose in Unity.
    for pb in arm.pose.bones:
        pb.keyframe_insert("location", frame=f)
        pb.keyframe_insert("rotation_quaternion", frame=f)
        pb.keyframe_insert("scale", frame=f)


for f in range(F_START, F_END + 1):
    sc.frame_set(f)
    pose_frame(f)

act = arm.animation_data.action
act.name = "SB_Idle"
act.use_fake_user = True
for s in getattr(act, "slots", []):
    s.name_display = "SB_Idle"

# Linear-ish interpolation is irrelevant here: every frame is keyed, so the
# baked samples ARE the motion. Force BEZIER->LINEAR to avoid overshoot between
# identical samples changing the exported bake.
def all_fcurves(a):
    if hasattr(a, "fcurves"):
        return list(a.fcurves)
    out = []
    for layer in a.layers:
        for strip in layer.strips:
            for cb in getattr(strip, "channelbags", []):
                out.extend(cb.fcurves)
    return out


for fc in all_fcurves(act):
    for kp in fc.keyframe_points:
        kp.interpolation = "LINEAR"

sc.frame_set(F_START)
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print("MASTER_BLEND_SAVED " + OUT_BLEND)
print("ACTION " + act.name + " frames " + str(act.frame_range[:]) +
      " fcurves " + str(len(all_fcurves(act))))
print("PUNCH_PRESERVED " + (punch.name if punch else "NONE"))
