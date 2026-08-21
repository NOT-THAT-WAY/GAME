"""Declared key poses for the 11 clips of the locomotion / verticality / object pole.

Executed inside the live MCP session on top of `pose_kernel.py`.

Frame of reference, measured from the rig and restated here because every sign
below depends on it:

  * the character faces -Y, +Z is up, +X is the character's LEFT (foot.L is at
    x = +0.28);
  * body rotation +rx pitches the top toward -Y, i.e. +rx = lean FORWARD;
  * an arm bone points downward from its head, so the same +rx swings an arm
    BACKWARD. Forward arm swing is therefore -rx. This sign inversion between
    body and arms is a property of the bind pose, not a convention choice;
  * +ry rolls the body toward +X (character's left);
  * +rz yaws the face toward -X (character's right).

Nominal cycle speeds are NOT invented. Gameplay walks at 4.2 m/s and sprints at
7.0 m/s (`PredictedPlayerMotor._walkSpeed` / `._sprintSpeed`). A 1.34 m
character covering 4.2 m in one authored second would need a 2.1 m stride per
step, which reads as a leap rather than a walk. Every locomotion cycle is
therefore authored at exactly HALF the gameplay speed, giving one single, clean
playback multiplier of x2.0 for both walk and sprint. The residual decision —
accept x2.0 playback or re-time the clips — is recorded as an integration limit,
not silently resolved here.
"""
import math

FPS = 30.0

# ----------------------------------------------------------------- locomotion
WALK = dict(
    name="SB_Walk", f_start=1, f_end=30, periodic=True,
    speed=2.10,          # m/s authored; gameplay 4.2 m/s -> playback x2.0
    duty=0.60,           # stance fraction; > 0.5 so both feet overlap, no flight
    contact_l=1, contact_r=16,
    apex_l=23, apex_r=8,  # brief's "passage" frames, honoured as swing apex
    lift=0.095, out=0.22,
    body=dict(bob=0.032, sway=0.030, lean=5.0, roll=3.0, yaw=2.0, nod=1.5),
    arm=dict(upper=24.0, fore=10.0, hand=5.0, lag_fore=3.0, lag_hand=5.0,
             abduct=16.0),
)

SPRINT = dict(
    name="SB_Sprint", f_start=1, f_end=24, periodic=True,
    speed=3.50,          # m/s authored; gameplay 7.0 m/s -> playback x2.0
    duty=0.35,           # < 0.5 -> genuine flight phase, unlike the walk
    contact_l=1, contact_r=13,
    apex_l=19, apex_r=7,  # brief's "suspension" frames
    lift=0.130, out=0.24,
    body=dict(bob=0.055, sway=0.022, lean=16.0, roll=2.0, yaw=3.5, nod=2.5),
    arm=dict(upper=42.0, fore=26.0, hand=9.0, lag_fore=2.0, lag_hand=3.0,
             abduct=20.0),
)

CARRY_WALK_BASE = dict(
    name="SB_CarryWalk", f_start=1, f_end=30, periodic=True,
    speed=2.10,          # identical to SB_Walk, as mandated
    duty=0.60,
    contact_l=1, contact_r=16,
    apex_l=23, apex_r=8,
    lift=0.085, out=0.20,  # lower and wider: carrying settles the gait
    body=dict(bob=0.022, sway=0.020, lean=3.0, roll=2.0, yaw=1.0, nod=0.8),
    arm=None,            # arms are held in the carry pose, they do not swing
)


def _hermite(p0, p1, m0, m1, s):
    s2, s3 = s * s, s * s * s
    return ((2 * s3 - 3 * s2 + 1) * p0 + (s3 - 2 * s2 + s) * m0
            + (-2 * s3 + 3 * s2) * p1 + (s3 - s2) * m1)


def _warp_apex(s, s_peak):
    """Map s so that the lift apex lands on s_peak instead of 0.5."""
    if s_peak <= 0.0 or s_peak >= 1.0:
        return s
    if s < s_peak:
        return 0.5 * s / s_peak
    return 0.5 + 0.5 * (s - s_peak) / (1.0 - s_peak)


def swing_arc(f, spec, contact, apex):
    """0 while the foot is planted, sin(pi*w) over its swing. Shared shape.

    The arm abduction reads this so a fist opens the corridor at exactly the
    frames its own foot needs it, and closes again by touchdown.
    """
    n = spec["f_end"] - spec["f_start"] + 1
    stance = round(n * spec["duty"])
    swing = n - stance
    phase = (f - contact) % n
    if phase <= stance:
        return 0.0
    s = (phase - stance) / float(swing)
    s_peak = ((apex - contact) % n - stance) / float(swing)
    return math.sin(math.pi * _warp_apex(s, s_peak))


def foot_channel(f, spec, contact, apex, side):
    """Analytic foot pose for frame `f`.

    Keyed on EVERY frame so the stance ramp stays exactly linear: a planted foot
    must be static in the world reconstructed at the nominal speed, and letting a
    sparse spline approximate that ramp is what produces foot sliding.

    Stance: the character advances along -Y at `speed`, so a world-static foot
    travels +Y at `speed` in the clip's local frame.
    Swing: a cubic Hermite whose end tangents MATCH the stance velocity, so the
    foot is already travelling backward at exactly stance speed at touchdown.
    That is what makes contact drift zero by construction rather than by luck.
    """
    n = spec["f_end"] - spec["f_start"] + 1
    v = spec["speed"]
    stance = round(n * spec["duty"])
    swing = n - stance
    amp = v * stance / FPS / 2.0          # half the stance excursion, metres
    per_frame = v / FPS

    phase = (f - contact) % n
    if phase <= stance:
        y = -amp + per_frame * phase
        z = 0.0
        # The stance foot stays strictly flat. A heel-to-toe roll was authored
        # first and measured worse on both gates at once: rotating the foot about
        # its head, which sits at z = 0, drove a corner 5.3 mm through the ground
        # and slid the contact patch 56 mm along the sole. This rig has pancake
        # feet and no ankle, so there is no articulation for a roll to express.
        return (0.0, y, 0.0, 0.0, 0.0, 0.0)

    s = (phase - stance) / float(swing)
    tangent = per_frame * swing
    y = _hermite(amp, -amp, tangent, tangent, s)
    s_peak = ((apex - contact) % n - stance) / float(swing)
    w = _warp_apex(s, s_peak)
    arc = math.sin(math.pi * w)
    z = spec["lift"] * arc ** 1.5
    # The swing foot travels OUTWARD, not just upward. At rest the top of a foot
    # (z = 0.220) is exactly tangent to the bottom of the body sphere
    # (z = 0.220), so this character has no vertical clearance at all and any
    # straight lift buries the foot in the belly - measured at 98 mm deep with a
    # 0.20 m lift. The body is a sphere of radius 0.56 centred at (0, 0, 0.78),
    # so moving the foot's inner edge out to x = 0.11 + out clears it when
    # (0.11 + out)^2 >= 1.12 * lift - lift^2. The declared pair below satisfies
    # that with margin, and turns the constraint into a readable waddle.
    dx = side * spec["out"] * arc
    # Toe hangs down over the apex, levels out before touchdown.
    pitch = math.radians(8.0 - 14.0 * s) * arc ** 0.5
    return (dx, y, z, pitch, 0.0, 0.0)


def _body_pose(f, spec, contact_l):
    """Body key value at frame `f` from the declared locomotion model."""
    n = spec["f_end"] - spec["f_start"] + 1
    b = spec["body"]
    th = 2.0 * math.pi * (f - contact_l) / n      # one per cycle
    th2 = 2.0 * th                                # one per step
    return (
        b["sway"] * math.cos(th),                                  # dx
        0.0,                                                       # dy
        -b["bob"] * math.cos(th2),                                 # dz: low at contact
        math.radians(b["lean"] + b["nod"] * math.cos(th2)),        # rx forward lean
        math.radians(b["roll"]) * math.cos(th),                    # ry toward stance foot
        -math.radians(b["yaw"]) * math.cos(th),                    # rz counter-rotation
    )


def _arm_pose(f, spec, contact_l, side, arc):
    """Arm chain key values; `side` is +1 for left, -1 for right.

    `arc` is the same-side foot's swing arc. The upper arm abducts outward in
    step with it, because the measured corridor between the foot's outer edge
    (x = 0.45) and the fist's inner edge (x = 0.5738) is only 0.124 m, while
    clearing the body sphere needs about 0.23 m of outward foot travel. With the
    arms fixed those two constraints have no common solution; abducting the arm
    moves the fist out of the way and makes one exist. Outward is -ry on the
    left and +ry on the right, hence the -side factor.
    """
    n = spec["f_end"] - spec["f_start"] + 1
    a = spec["arm"]
    def swing(amp_deg, lag):
        th = 2.0 * math.pi * (f - contact_l - lag) / n
        # At contact_l the left foot is forward, so the left arm must be BACK.
        # +rx swings an arm backward, hence +cos for the left side.
        return math.radians(amp_deg) * math.cos(th) * side
    abduct = -side * math.radians(a.get("abduct", 0.0)) * arc
    return {
        "upper": (0.0, 0.0, 0.0, swing(a["upper"], 0.0), abduct, 0.0),
        "fore": (0.0, 0.0, 0.0, swing(a["fore"], a["lag_fore"]), 0.0, 0.0),
        "hand": (0.0, 0.0, 0.0, swing(a["hand"], a["lag_hand"]), 0.0, 0.0),
    }


def locomotion_keyposes(spec, carry_arms=None, body_key_step=3):
    """Build {frame: {bone: 6-tuple}} for a locomotion cycle.

    Feet are keyed on every frame (exact stance ramp). Body and arms are keyed
    on a sparse readable grid and interpolated by the periodic Catmull-Rom, so
    they stay hand-tunable key poses rather than a baked formula.
    """
    from pose_kernel import BODY, FOOT_L, FOOT_R, ARM_L, ARM_R

    f0, f1 = spec["f_start"], spec["f_end"]
    keyposes = {f: {} for f in range(f0, f1 + 1)}

    for f in range(f0, f1 + 1):
        keyposes[f][FOOT_L] = foot_channel(f, spec, spec["contact_l"], spec["apex_l"], +1.0)
        keyposes[f][FOOT_R] = foot_channel(f, spec, spec["contact_r"], spec["apex_r"], -1.0)

    body_frames = sorted(set(list(range(f0, f1 + 1, body_key_step))
                             + [spec["contact_l"], spec["contact_r"],
                                spec["apex_l"], spec["apex_r"]]))
    for f in body_frames:
        keyposes[f][BODY] = _body_pose(f, spec, spec["contact_l"])
        if spec["arm"] is not None:
            for chain, side, contact, apex in (
                    (ARM_L, +1.0, spec["contact_l"], spec["apex_l"]),
                    (ARM_R, -1.0, spec["contact_r"], spec["apex_r"])):
                arc = swing_arc(f, spec, contact, apex)
                arm = _arm_pose(f, spec, spec["contact_l"], side, arc)
                keyposes[f][chain[0]] = arm["upper"]
                keyposes[f][chain[1]] = arm["fore"]
                keyposes[f][chain[2]] = arm["hand"]
        elif carry_arms is not None:
            for chain in (ARM_L, ARM_R):
                for i, bone in enumerate(chain):
                    keyposes[f][bone] = carry_arms[bone]

    # Drop frames that ended up with no bone at all (cannot happen for feet, but
    # keeps the dict clean if a caller changes the grid).
    return {f: p for f, p in keyposes.items() if p}


# ------------------------------------------------- solved and derived poses
# Every angle below in POSES came out of `solve_carry.py` running against the
# evaluated fist meshes and the real carry zone the gameplay code uses
# (Unity-local (side, 0.86, +0.62) -> Blender (side, -0.62, 0.86)). They are
# frozen here so a clip is reproducible without re-running the solve, and the
# residuals they achieved are recorded in evidence/solved-poses.json.
#
# An earlier hand estimate concluded the hands could not reach the carry zone at
# all. That estimate was wrong: it only considered a planar arm swing, while the
# shoulder's full 3-axis rotation reaches the target to within 0.22 mm. Measuring
# beat reasoning here, which is why these numbers are solved rather than chosen.

def deg(*values):
    return tuple(math.radians(v) for v in values)


def pose(dx=0.0, dy=0.0, dz=0.0, rx=0.0, ry=0.0, rz=0.0):
    """Metres for offsets, DEGREES for rotations, converted to the kernel's radians."""
    return (dx, dy, dz) + deg(rx, ry, rz)


def mirror(p):
    """Mirror a left-side pose to the right across the X plane."""
    return (-p[0], p[1], p[2], p[3], -p[4], -p[5])


SOLVED = {
    "carry":   dict(body_rx=5.06, upper=(-69.74, 17.50, -27.71), fore=(-5.86, 6.22, -9.44)),
    "grab":    dict(body_rx=34.38, upper=(-34.74, 11.46, -35.81), fore=(-0.78, 22.92, -34.38)),
    "reach":   dict(body_rx=20.95, upper=(-91.67, 32.95, -22.92), fore=(-10.61, 6.04, 0.36)),
    "release": dict(body_rx=0.22, upper=(-44.87, 13.25, -20.19), fore=(-23.16, 8.93, 20.14)),
}


def arm_pair(key, blend=1.0, extra_upper=(0.0, 0.0, 0.0), extra_fore=(0.0, 0.0, 0.0)):
    """Both arm chains for a solved pose, optionally eased toward rest."""
    from pose_kernel import ARM_L, ARM_R
    s = SOLVED[key]
    upper = pose(rx=s["upper"][0] * blend + extra_upper[0],
                 ry=s["upper"][1] * blend + extra_upper[1],
                 rz=s["upper"][2] * blend + extra_upper[2])
    fore = pose(rx=s["fore"][0] * blend + extra_fore[0],
                ry=s["fore"][1] * blend + extra_fore[1],
                rz=s["fore"][2] * blend + extra_fore[2])
    out = {ARM_L[0]: upper, ARM_L[1]: fore, ARM_L[2]: pose(),
           ARM_R[0]: mirror(upper), ARM_R[1]: mirror(fore), ARM_R[2]: pose()}
    return out


def feet_planted(dy_l=0.0, dy_r=0.0):
    from pose_kernel import FOOT_L, FOOT_R
    return {FOOT_L: pose(dy=dy_l), FOOT_R: pose(dy=dy_r)}


def feet_tucked(out_m, lift, dy=0.0):
    """Both feet lifted and spread. `out_m` clears the body sphere; see
    foot_channel for the (0.11 + out)^2 >= 1.12*lift - lift^2 condition."""
    from pose_kernel import FOOT_L, FOOT_R
    return {FOOT_L: pose(dx=+out_m, dy=dy, dz=lift),
            FOOT_R: pose(dx=-out_m, dy=dy, dz=lift)}
