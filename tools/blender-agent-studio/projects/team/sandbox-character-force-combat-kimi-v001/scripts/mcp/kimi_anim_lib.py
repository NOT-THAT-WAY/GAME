# BAS_KIMI_ animation authoring library — force/combat pole.
#
# Executed INSIDE the open MCP Blender session (prepended to every builder via
# exec(open(...).read())). Never run in batch. Never saves the file by itself.
#
# Model: a POSE SPEC maps bone names to world-space operations applied over the
# rest pose, parent-first:
#     spec[bone] = (axis_vector, angle_deg, world_offset_Vector)
# The bone's matrix (already composed with its animated parents) is rotated by
# `angle_deg` around `axis_vector` about the bone's own head, then translated
# by `world_offset`. root is always forced to identity: zero root motion.
#
# One-shots blend between pose specs with smoothstep easing and key EVERY frame
# (LINEAR fcurves): the baked samples ARE the motion, no tangent overshoot.
# Loops add harmonic modifiers of the exact clip period: pose(f+N)==pose(f) by
# construction (position AND velocity continuity at the seam).

import bpy
import json
import math
from mathutils import Vector, Matrix, Quaternion

EXPECTED_MASTER = "local_work/sandbox-character-force-combat-kimi-v001/work/sandbox_character_kimi_force_combat_master.blend"

ROOT = "BAS_PUNCH_root"
BODY = "BAS_PUNCH_body"
FEET = ["BAS_PUNCH_foot.L", "BAS_PUNCH_foot.R"]
CHAINS = [("BAS_PUNCH_upperarm.L", "BAS_PUNCH_forearm.L", "BAS_PUNCH_hand.L"),
          ("BAS_PUNCH_upperarm.R", "BAS_PUNCH_forearm.R", "BAS_PUNCH_hand.R")]
BONES_PARENT_FIRST = ["BAS_PUNCH_root", "BAS_PUNCH_body",
                      "BAS_PUNCH_upperarm.L", "BAS_PUNCH_forearm.L", "BAS_PUNCH_hand.L",
                      "BAS_PUNCH_upperarm.R", "BAS_PUNCH_forearm.R", "BAS_PUNCH_hand.R",
                      "BAS_PUNCH_foot.L", "BAS_PUNCH_foot.R"]

X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))


def guard():
    """P0 stop: the MCP session must be on MY working copy."""
    fp = bpy.data.filepath
    assert fp == EXPECTED_MASTER, "SESSION ISOLATION BREACH: filepath=%r" % fp
    return True


def get_arm():
    return next(o for o in bpy.data.objects if o.type == "ARMATURE")


def reset_pose(arm):
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()


def rest_mats(arm):
    return {b.name: b.matrix_local.copy() for b in arm.data.bones}


def rot_about_head(mat, quat):
    head = mat.translation.copy()
    return (Matrix.Translation(head) @ quat.to_matrix().to_4x4()
            @ Matrix.Translation(-head) @ mat)


def detach_action(arm):
    """Pose computation/keying must never be stomped by fcurve evaluation."""
    if arm.animation_data:
        arm.animation_data.action = None


def compute_pose(arm, spec):
    """spec: bone -> (rotations, offset) where rotations is a Quaternion or a
    list of (axis, angle_deg) composed in order, all world-space about the
    bone's own head; offset is a world Vector. Returns {bone: Matrix}."""
    detach_action(arm)
    reset_pose(arm)
    out = {}
    for name in BONES_PARENT_FIRST:
        pb = arm.pose.bones[name]
        if name == ROOT:
            pb.matrix_basis = Matrix.Identity(4)  # root never moves
        elif name in spec:
            rots, off = spec[name]
            q = rots if isinstance(rots, Quaternion) else None
            if q is None:
                q = Quaternion()
                for axis, ang in rots:
                    q = Quaternion(axis, math.radians(ang)) @ q
            m = pb.matrix.copy()
            if q.angle > 1e-9:
                m = rot_about_head(m, q)
            if off.length > 1e-12:
                m = Matrix.Translation(off) @ m
            pb.matrix = m
        bpy.context.view_layer.update()
        out[name] = pb.matrix.copy()
    return out


def blend_poses(pa, pb_, t):
    """t in [0,1]: per-bone lerp of translation + slerp of rotation."""
    out = {}
    for name in pa:
        ma, mb = pa[name], pb_[name]
        la, lb = ma.translation, mb.translation
        qa, qb = ma.to_quaternion(), mb.to_quaternion()
        loc = la.lerp(lb, t)
        rot = qa.slerp(qb, t)
        out[name] = Matrix.Translation(loc) @ rot.to_matrix().to_4x4()
    return out


def smoothstep(t):
    return t * t * (3.0 - 2.0 * t)


def apply_pose(arm, pose):
    for name in BONES_PARENT_FIRST:
        arm.pose.bones[name].matrix = pose[name]
        bpy.context.view_layer.update()


def key_all(arm, f):
    for pb in arm.pose.bones:
        pb.keyframe_insert("location", frame=f)
        pb.keyframe_insert("rotation_quaternion", frame=f)
        pb.keyframe_insert("scale", frame=f)


def new_action(arm, name):
    a = bpy.data.actions.get(name)
    if a is not None:
        bpy.data.actions.remove(a)
    if arm.animation_data is None:
        arm.animation_data_create()
    a = bpy.data.actions.new(name)
    a.use_fake_user = True
    arm.animation_data.action = a
    try:
        slot = a.slots[0]
        arm.animation_data.action_slot = slot
    except Exception:
        pass
    return a


def all_fcurves(a):
    if hasattr(a, "fcurves"):
        try:
            return list(a.fcurves)
        except Exception:
            pass
    out = []
    for layer in a.layers:
        for strip in layer.strips:
            for cb in getattr(strip, "channelbags", []):
                out.extend(cb.fcurves)
    return out


def force_linear(a):
    for fc in all_fcurves(a):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


def capture_pose(arm):
    bpy.context.view_layer.update()
    return {pb.name: pb.matrix.copy() for pb in arm.pose.bones}


def idle_f1_pose(arm):
    """World(=armature)-space pose matrices of SB_Idle frame 1 (reference pose).
    Leaves the armature with NO action assigned (authoring mode)."""
    ad = arm.animation_data
    idle = bpy.data.actions["SB_Idle"]
    ad.action = idle
    try:
        ad.action_slot = idle.slots[0]
    except Exception:
        pass
    bpy.context.scene.frame_set(1)
    pose = capture_pose(arm)
    ad.action = None
    reset_pose(arm)
    return pose


def pose_delta(pa, pb_):
    """Max translation (m) and rotation (deg) deltas between two pose dicts."""
    dt = dr = 0.0
    for n in pa:
        dt = max(dt, (pa[n].translation - pb_[n].translation).length)
        dr = max(dr, math.degrees(pa[n].to_quaternion()
                 .rotation_difference(pb_[n].to_quaternion()).angle))
    return dt, dr


def set_view(direction, dist=3.2, target=(0.0, 0.0, 0.7)):
    """Aim the first 3D viewport from `direction` (world Vector) at `target`."""
    d = Vector(direction).normalized()
    for area in bpy.context.screen.areas:
        if area.type != "VIEW_3D":
            continue
        r3d = area.spaces.active.region_3d
        r3d.view_perspective = "ORTHO"
        r3d.view_distance = dist
        r3d.view_location = Vector(target)
        # camera looks along -Z of view_rotation; want view direction -d,
        # i.e. local +Z maps to d
        r3d.view_rotation = d.to_track_quat("Z", "Y")
        break


def fist_positions(arm):
    bpy.context.view_layer.update()
    out = {}
    for side in ("L", "R"):
        pb = arm.pose.bones["BAS_PUNCH_hand.%s" % side]
        out[side] = [round(v, 4) for v in (arm.matrix_world @ pb.matrix).translation]
    return out
