"""Declared key poses for the 7 clips of the force / combat / life-state pole.

Same frame of reference as the rig audit, restated because every sign depends on
it: the character faces -Y, +Z is up, +X is its LEFT. On the body +rx leans
FORWARD; on an arm the same +rx swings BACKWARD, because an arm bone points down
from its head. +rz yaws the face toward -X (the character's right).

All arm angles come from `solve_pose.py` running against the evaluated fist
meshes with a body-collision penalty, so a pose that reaches its target by
routing the forearm through the belly is rejected during the solve rather than
discovered later by the gates. Every pose is verified at FULL vertex resolution, not on the stride-8
subsample the coarse search uses: the first guard and push solves came back
clean and then collided by 8 to 22 mm once every vertex was checked.
Residuals and collision depths are recorded in `evidence/solved-poses.json`.

Measured anatomical limit worth stating once: the shoulders sit at x = +/-0.52
with a 0.70 m arm, so a fist CANNOT cross the centre line. A cross-body punch is
impossible on this rig without passing through the body; the punch therefore
extends on its own side. Residual to a centre-line target: 0.257 m.
"""
import math

from pose_kernel import BODY, FOOT_L, FOOT_R, ARM_L, ARM_R


def deg(*values):
    return tuple(math.radians(v) for v in values)


def pose(dx=0.0, dy=0.0, dz=0.0, rx=0.0, ry=0.0, rz=0.0):
    """Metres for offsets, DEGREES for rotations, converted to kernel radians."""
    return (dx, dy, dz) + deg(rx, ry, rz)


def mirror(p):
    return (-p[0], p[1], p[2], p[3], -p[4], -p[5])


SOLVED = {
    "guard": dict(body_rx=13.70, upper=(-72.50, 8.15, -34.01), fore=(-14.59, 10.11, 18.84)),
    "punch": dict(body_rx=22.92, upper=(-88.81, 16.45, -36.91), fore=(-2.33, 14.68, -14.32)),
    "push":  dict(body_rx=26.43, upper=(-91.67, 18.33, -35.31), fore=(-17.96, 27.43, 10.35)),
    "splay": dict(body_rx=0.00, upper=(-11.46, -3.22, -14.50), fore=(1.88, -18.26, -1.88)),
}

# Ceiling on any downward body motion, measured on this character: the underside
# of the body sphere and the domes of the feet leave 0.0534 m at their tightest
# slice. Anything past it buries the feet in the belly.
BODY_DIP_MAX = 0.0534


def arm(key, blend=1.0, extra_upper=(0.0, 0.0, 0.0), extra_fore=(0.0, 0.0, 0.0)):
    """One LEFT arm chain from a solved pose, optionally eased toward rest."""
    s = SOLVED[key]
    upper = pose(rx=s["upper"][0] * blend + extra_upper[0],
                 ry=s["upper"][1] * blend + extra_upper[1],
                 rz=s["upper"][2] * blend + extra_upper[2])
    fore = pose(rx=s["fore"][0] * blend + extra_fore[0],
                ry=s["fore"][1] * blend + extra_fore[1],
                rz=s["fore"][2] * blend + extra_fore[2])
    return upper, fore


def arms(left_key, right_key=None, left_blend=1.0, right_blend=None,
         left_extra=(0.0, 0.0, 0.0), right_extra=(0.0, 0.0, 0.0),
         left_extra_fore=(0.0, 0.0, 0.0), right_extra_fore=(0.0, 0.0, 0.0)):
    """Both chains, each independently keyed.

    The two arms are addressed separately rather than mirrored as a pair because
    this pole is full of asymmetric actions: one fist punches while the other
    guards, one shoulder leads a knockout.
    """
    right_key = right_key if right_key is not None else left_key
    right_blend = right_blend if right_blend is not None else left_blend
    lu, lf = arm(left_key, left_blend, left_extra, left_extra_fore)
    ru, rf = arm(right_key, right_blend, right_extra, right_extra_fore)
    return {
        ARM_L[0]: lu, ARM_L[1]: lf, ARM_L[2]: pose(),
        ARM_R[0]: mirror(ru), ARM_R[1]: mirror(rf), ARM_R[2]: pose(),
    }


def feet(dx=0.0, dy=0.0, dz=0.0, rx=0.0, dx_l=None, dx_r=None,
         dy_l=None, dy_r=None, dz_l=None, dz_r=None, rx_l=None, rx_r=None):
    """Both feet, symmetric by default, per-side when a step needs it.

    A constant lateral offset is a WIDE STANCE, not drift: the drift gate
    measures how much a planted foot moves across its window, and a foot that
    simply stands somewhere other than its rest position never moves at all.
    """
    return {
        FOOT_L: pose(dx=(dx_l if dx_l is not None else dx),
                     dy=(dy_l if dy_l is not None else dy),
                     dz=(dz_l if dz_l is not None else dz),
                     rx=(rx_l if rx_l is not None else rx)),
        FOOT_R: pose(dx=-(dx_r if dx_r is not None else dx),
                     dy=(dy_r if dy_r is not None else dy),
                     dz=(dz_r if dz_r is not None else dz),
                     rx=(rx_r if rx_r is not None else rx)),
    }


def merge(*dicts):
    out = {}
    for d in dicts:
        out.update(d)
    return out


# ---------------------------------------------------------------- KO anchor
# Defined once and reused verbatim by three clips: SB_KnockedOutLoop frame 1,
# SB_Knockout frame 30 and SB_Recover frame 1 must be the SAME pose bone for
# bone, otherwise the engine pops when a knockout hands over to its loop or the
# loop hands over to a recovery.
#
# The character is a sphere: "on the ground" means rolled back onto its lower
# back with the feet in the air, not a humanoid lying prone. Rotating the body
# -50 deg about its own head puts the sphere centre at y = +0.368, z = 0.609, so
# its underside lands at z = 0.049 and a drop seats it on the floor.
# The first value tried, -0.045, left the body 0.0269 m ABOVE the ground: no
# penetration, but a KO character floating three centimetres over the floor.
# Absence of penetration is not proof of contact, so the drop is set from the
# measured gap instead of from the analytic estimate.
# The feet then have to clear forward and upward or they end up inside the belly.
# Seated from the measurement, in two steps: -0.045 left it floating
# 0.0269 m, -0.0719 drove it 0.0029 m through the floor, so the contact
# sits at -0.0685.
KO_BODY = pose(dz=-0.0685, dy=0.010, rx=-50.0)
KO_FEET = feet(dx=0.10, dy=-0.34, dz=0.19, rx=-28.0)
KO_ARMS = arms("splay", left_extra=(4.0, 0.0, 0.0), right_extra=(-2.0, 0.0, 0.0))
KO_POSE = merge({BODY: KO_BODY}, KO_FEET, KO_ARMS)


def ko_pose_breathing(phase):
    """The KO anchor with a barely visible breath. Phase 0 returns it exactly."""
    if phase == 0.0:
        return dict(KO_POSE)
    breath = math.sin(2.0 * math.pi * phase)
    # The breath can only lift, never sink: the body is already resting on the
    # floor at phase 0, so a symmetric oscillation would push it through.
    body = pose(dz=-0.0685 + 0.0035 * (breath + 1.0) * 0.5, dy=0.010,
                rx=-50.0 + 0.55 * breath)
    return merge({BODY: body}, KO_FEET,
                 arms("splay",
                      left_extra=(4.0 + 0.5 * breath, 0.0, 0.0),
                      right_extra=(-2.0 - 0.5 * breath, 0.0, 0.0)))
