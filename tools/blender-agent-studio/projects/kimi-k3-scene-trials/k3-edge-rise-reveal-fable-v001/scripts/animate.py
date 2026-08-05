"""Animate the arc: seated → sit-to-stand → walk up the ramp → stop and look up.

Coordinates: everything is computed in METERS in the local frame of
USTUDIO_BOX_FLOAT_ROOT, then divided by SCALE to land in armature space
(the armature object carries only the uniform scale).

The ground is the real geometry: the flat rim top at z=0.76 in front of
y=-0.42, then the measured Piano Roll ramp (46.34°) behind it. The 0.12 m
lip between them is a real step-up, not a ramp.

mode=test renders isolated key poses; mode=full keyframes 360 frames.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix, Vector

P = globals().get("UNRECORDED_PARAMS", {})
TRIAL = Path(P.get("trial_dir", ".")).resolve()
MODE = P.get("mode", "full")
SCALE = 0.424

# ----------------------------------------------------------------- ground
RIM_Z = 0.76
RAMP_EDGE_Y = -0.42
RAMP_ORIGIN = Vector((0.0, 0.415, 1.755))
RAMP_SLOPE = math.tan(math.radians(46.34))          # dz/dy = 1.0479
RAMP_N = Vector((0.0, -0.723449, 0.690377))
FLAT_N = Vector((0.0, 0.0, 1.0))

def ground_z(y):
    if y < RAMP_EDGE_Y:
        return RIM_Z
    return RAMP_ORIGIN.z + (y - RAMP_ORIGIN.y) * RAMP_SLOPE

def ground_n(y):
    return FLAT_N if y < RAMP_EDGE_Y else RAMP_N

# ----------------------------------------------------------------- timing
FPS, FRAME_END = 30, 360
BEAT = 12.1
def beat(k):
    return 9.0 + k * BEAT

F_RISE = beat(4)          # 57.4  downbeat: push starts
F_STAND = beat(8)         # 105.8 downbeat: upright on the rim
F_WALK = beat(10)         # 130.0 first step (still on the rim)
STEP_BEATS = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]   # 10 contacts
F_GATHER = beat(20)       # 251.0 trailing foot joins
F_LOOKUP = beat(24)       # 299.4 downbeat: the head starts to rise
F_CONTEMPLATE = 340.0
TAP_BEATS = [0, 1, 2, 3]  # 9, 21.1, 33.2, 45.3

# ----------------------------------------------------------------- geometry
X0 = -0.72
FEET_Y_START = -0.56
SEAT_Y = -0.72
SEAT_PELVIS_Z = RIM_Z + 0.075
STEP_LEN = 0.16
# two preparatory contacts: one still on the flat rim, then the step-up that
# clears the 0.131 m lip onto the ramp. A single 0.20 m step-up is not
# reachable with 0.217 m legs, and faking it would mean sliding feet.
RIM_CONTACT_Y = -0.46
LIP_CONTACT_Y = -0.41
# each foot alternates every 2 beats; the swing is ~40% of that cycle so at
# least one foot is always planted (a shorter plant made him levitate)
SWING_FRAMES = 9.5
FOOT_LAT = 0.0729                      # half the hip width, in meters
# standing at rest the legs are already 99% extended, so the film stands him
# slightly softer than rest: the knees stay readable and never lock.
PELVIS_H_STAND = 0.283
# as high as 0.217 m legs allow at this stride on a ~35° grade; the crouch
# solver trims it further only on the frames that need it
PELVIS_H_WALK = 0.228
LEG_MAX = (0.2760 + 0.2600) * SCALE * 0.955    # 0.2171 m usable, never straight

# path over the ground: quadratic bezier in (x, y), z follows the surface
PATH_P0 = Vector((X0, FEET_Y_START))
PATH_P1 = Vector((0.0, 0.10))     # control point on the axis: he arrives facing the back wall
PATH_P2 = Vector((0.0, 0.30))

def path_xy(t):
    u = 1.0 - t
    return PATH_P0 * (u * u) + PATH_P1 * (2 * u * t) + PATH_P2 * (t * t)

def path_tangent(t):
    d = (PATH_P1 - PATH_P0) * (2 * (1 - t)) + (PATH_P2 - PATH_P1) * (2 * t)
    return d.normalized()

# arc-length table in 3D (the step-up lip contributes its real 0.12 m)
_SAMPLES = 900
_TABLE = []
_acc = 0.0
_prev = None
for i in range(_SAMPLES + 1):
    t = i / _SAMPLES
    xy = path_xy(t)
    p = Vector((xy.x, xy.y, ground_z(xy.y)))
    if _prev is not None:
        _acc += (p - _prev).length
    _TABLE.append((_acc, t, p))
    _prev = p
PATH_LEN = _TABLE[-1][0]

def path_at_s(s):
    s = max(0.0, min(PATH_LEN, s))
    lo, hi = 0, len(_TABLE) - 1
    while lo < hi - 1:
        mid = (lo + hi) // 2
        if _TABLE[mid][0] < s:
            lo = mid
        else:
            hi = mid
    s0, t0, p0 = _TABLE[lo]
    s1, t1, p1 = _TABLE[hi]
    f = 0.0 if s1 - s0 < 1e-9 else (s - s0) / (s1 - s0)
    return p0.lerp(p1, f), t0 + (t1 - t0) * f

def s_of_y(y_target):
    for s, t, p in _TABLE:
        if p.y >= y_target:
            return s
    return PATH_LEN

S_RIM = s_of_y(RIM_CONTACT_Y)
S_LIP = s_of_y(LIP_CONTACT_Y)
# spread the remaining strides so the last contact lands near the end of the
# path instead of overshooting it; keep the stride inside a walkable range
_n_ramp = len(STEP_BEATS) - 2
STEP_LEN = min(0.175, max(0.125, (PATH_LEN * 0.985 - S_LIP) / _n_ramp))
CONTACT_S = [S_RIM, S_LIP] + [S_LIP + i * STEP_LEN for i in range(1, _n_ramp + 1)]

def offset_lateral(t, side_sign):
    # the stance width follows the BODY's lateral axis (cap = atan2(tx, -ty)),
    # which is (-ty, tx). Using the opposite normal would cross the legs.
    tangent = path_tangent(t)
    lat = Vector((-tangent.y, tangent.x))
    return lat * (FOOT_LAT * side_sign)

def contact_point(index, side_sign):
    p, t = path_at_s(CONTACT_S[index])
    off = offset_lateral(t, side_sign)
    xy = Vector((p.x + off.x, p.y + off.y))
    return Vector((xy.x, xy.y, ground_z(xy.y)))

def start_foot(side_sign):
    # before the walk the body faces +Y, so the stance width follows the body's
    # lateral axis, not the path normal (that would cross the legs)
    return Vector((X0 - FOOT_LAT * side_sign, FEET_Y_START, RIM_Z))

# which foot takes which contact: the right foot taps the tempo and leads
LEAD, TRAIL = "R", "L"
SIGN = {"L": 1.0, "R": -1.0}
CONTACTS = {"L": [], "R": []}
for i, _ in enumerate(STEP_BEATS):
    side = LEAD if i % 2 == 0 else TRAIL
    CONTACTS[side].append(i)

def smoothstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)

def ease(f, a, b):
    return smoothstep((f - a) / (b - a)) if b > a else 0.0

# ----------------------------------------------------------------- foot state
def foot_events(side):
    """Every place this foot is set down, in order, starting from the stance."""
    sign = SIGN[side]
    events = [(1.0, start_foot(sign))]
    events += [(beat(STEP_BEATS[i]), contact_point(i, sign)) for i in CONTACTS[side]]
    # the last stride belongs to TRAIL (odd indices), so LEAD is the foot that
    # steps up to join it, squared with the final body yaw (facing +Y)
    if side == LEAD:
        p_last, _ = path_at_s(CONTACT_S[-1])
        gather = Vector((p_last.x - FOOT_LAT * sign, p_last.y, 0.0))
        gather.z = ground_z(gather.y)
        events.append((F_GATHER, gather))
    return events

EVENTS = {side: foot_events(side) for side in ("L", "R")}

def foot_state(side, f):
    """Return (position, planted). A planted foot never moves: it holds the
    contact it was set down on until it lifts for the next one."""
    events = EVENTS[side]
    landed = [(t, p) for t, p in events if t <= f]
    _, cur = landed[-1]
    later = [(t, p) for t, p in events if t > f]

    tap = 0.0
    if side == LEAD and f < F_RISE:
        for k in TAP_BEATS:
            t0 = beat(k) - 3.2
            if t0 <= f <= t0 + 7.0:
                q = (f - t0) / 7.0
                tap = 0.017 * math.sin(math.pi * q) ** 1.4

    if not later:
        return cur + Vector((0, 0, tap)), tap < 0.0015
    nxt_t, nxt_p = later[0]
    lift = nxt_t - SWING_FRAMES
    if f < lift:
        return cur + Vector((0, 0, tap)), tap < 0.0015
    q = (f - lift) / (nxt_t - lift)
    pos = cur.lerp(nxt_p, smoothstep(q))
    n = ground_n(pos.y)
    # A step-up already forces deep knee flexion; lifting the foot high on top
    # of that pushes the knee through the ramp, so this swing stays low.
    stepping_up = cur.y < RAMP_EDGE_Y <= nxt_p.y
    arc = (0.022 if stepping_up else 0.055) * math.sin(math.pi * q) ** 0.75
    lip = 0.010 * math.sin(math.pi * q) if stepping_up else 0.0
    return pos + n * arc + Vector((0, 0, lip)), False

# ----------------------------------------------------------------- body state
def pelvis_s(f):
    """Arc-length position of the pelvis along the path."""
    if f <= F_WALK:
        return 0.0
    marks = [(F_WALK - 6.0, 0.0)]
    for i, b in enumerate(STEP_BEATS):
        marks.append((beat(b) + 2.0, max(0.0, CONTACT_S[i] - 0.055)))
    marks.append((F_GATHER + 4.0, CONTACT_S[-1] - 0.015))
    marks.append((1e9, CONTACT_S[-1] - 0.015))
    for (t0, s0), (t1, s1) in zip(marks, marks[1:]):
        if t0 <= f <= t1:
            return s0 + (s1 - s0) * smoothstep((f - t0) / max(t1 - t0, 1e-6))
    return marks[-1][1]

def torso_lean(f):
    """Degrees forward from world vertical. Positive = leaning toward the walk."""
    if f <= F_RISE:
        base = 12.0 + 1.6 * math.sin(2 * math.pi * f / 74.0)
    elif f <= F_RISE + 16:
        base = 12.0 + 26.0 * ease(f, F_RISE, F_RISE + 16)      # dive forward
    elif f <= F_RISE + 34:
        base = 38.0 - 20.0 * ease(f, F_RISE + 16, F_RISE + 34)  # seat-off
    elif f <= F_STAND:
        base = 18.0 - 12.0 * ease(f, F_RISE + 34, F_STAND)
    elif f <= F_WALK:
        base = 6.0 + 6.0 * ease(f, F_STAND, F_WALK)
    elif f <= F_GATHER:
        base = 12.0 + 5.0 * ease(f, F_WALK, F_WALK + 20)
    elif f <= F_LOOKUP:
        base = 17.0 - 12.0 * ease(f, F_GATHER, F_GATHER + 26)
    else:
        base = 5.0 - 7.0 * ease(f, F_LOOKUP, F_LOOKUP + 34)     # opens up, chest out
    if F_WALK < f < F_GATHER:
        base += 1.2 * math.sin(2 * math.pi * (f - F_WALK) / BEAT)
    base += 0.7 * math.sin(2 * math.pi * f / 96.0)              # breathing
    return base

def head_pitch(f):
    """Degrees relative to the torso. Positive = looking up."""
    if f <= F_RISE:
        p = 6.0 + 3.0 * math.sin(2 * math.pi * (f - 20) / 120.0)
    elif f <= F_STAND:
        p = 6.0 - 10.0 * ease(f, F_RISE, F_RISE + 20) + 12.0 * ease(f, F_RISE + 24, F_STAND)
    elif f <= F_WALK:
        p = 8.0
    elif f <= F_GATHER:
        # scanning the walls while walking: slow sweep, then settles
        p = 8.0 + 5.0 * math.sin(2 * math.pi * (f - F_WALK) / 150.0)
    elif f <= F_LOOKUP:
        p = 10.0
    else:
        p = 10.0 + 42.0 * ease(f, F_LOOKUP, F_CONTEMPLATE)
    return p

def head_yaw(f):
    """Degrees, head turning to scan the walls (relative to the body)."""
    if f <= F_STAND:
        return 4.0 * math.sin(2 * math.pi * (f - 10) / 150.0)
    if f <= F_GATHER:
        return 16.0 * math.sin(2 * math.pi * (f - F_STAND) / 118.0)
    if f <= F_LOOKUP:
        return 6.0 * math.sin(2 * math.pi * (f - F_GATHER) / 90.0)
    return 6.0 * (1.0 - ease(f, F_LOOKUP, F_LOOKUP + 30))

def path_cap(s):
    _, t = path_at_s(max(s, 0.02))
    tangent = path_tangent(t)
    return math.atan2(tangent.x, -tangent.y)

def body_cap(f):
    """Yaw of the body: 180° faces +Y (into the box)."""
    facing_in = math.radians(180.0)
    if f <= F_STAND:
        return facing_in
    if f <= F_WALK:
        # he turns toward his destination before setting off
        return facing_in + (path_cap(0.0) - facing_in) * ease(f, F_STAND, F_WALK)
    c = path_cap(pelvis_s(f))
    if f > F_GATHER:
        c = c + (facing_in - c) * ease(f, F_GATHER, F_GATHER + 30)
    return c

def pelvis_pos(f, feet):
    """Vertical-gravity governed pelvis: height above the ground under it."""
    if f <= F_RISE:
        return Vector((X0, SEAT_Y, SEAT_PELVIS_Z))
    if f <= F_STAND:
        q = ease(f, F_RISE + 10, F_STAND - 4)
        seat = Vector((X0, SEAT_Y, SEAT_PELVIS_Z))
        stand = Vector((X0, FEET_Y_START, RIM_Z + PELVIS_H_STAND))
        pos = seat.lerp(stand, q)
        pos.z -= 0.028 * math.sin(math.pi * q) ** 0.7   # the body dips before rising
        return pos
    if f <= F_WALK:
        q = ease(f, F_STAND, F_WALK)
        h = PELVIS_H_STAND + (PELVIS_H_WALK - PELVIS_H_STAND) * q
        return Vector((X0, FEET_Y_START, RIM_Z + h))
    s = pelvis_s(f)
    p, _ = path_at_s(s)
    if f <= F_GATHER:
        phase = 2 * math.pi * (f - F_WALK) / BEAT
        bob = -0.010 * math.cos(phase)
        sway = 0.010 * math.sin(phase / 2.0)
    else:
        bob = -0.004 * (1.0 - ease(f, F_GATHER, F_GATHER + 24))
        sway = 0.0
    h = PELVIS_H_WALK + bob
    if f > F_GATHER:
        h += (PELVIS_H_STAND - PELVIS_H_WALK) * ease(f, F_GATHER, F_GATHER + 30)
    tangent = path_tangent(path_at_s(s)[1])
    lat = Vector((tangent.y, -tangent.x))
    return Vector((p.x + lat.x * sway, p.y + lat.y * sway, ground_z(p.y) + h))

def arm_angles(f, side):
    """Arm pose as explicit joint angles, in degrees.

    abduction: 0 keeps the asset's V rest pose, ~95 brings the arm alongside
    the body. swing: + swings the hand forward. elbow: flexion.
    Driving the arm as rigid rotations (instead of a minimal-rotation IK aim)
    keeps the roll stable — a minimal rotation of ~120° twists this tapered
    arm mesh into a blade.
    """
    phase = 2 * math.pi * (f - F_WALK) / (2 * BEAT) + (math.pi if side == "L" else 0.0)
    # NB: the arms are 0.4165 m on a 0.88 m body and he climbs a 46° ramp, so a
    # hanging arm swung forward would go straight through the floor. The elbow
    # therefore stays folded throughout — which also reads as a climbing posture.
    # swing sign: positive rotates the hand downhill (behind him), negative
    # sends it uphill — where the ramp rises 1.05 m per metre and would swallow
    # it. The swing therefore stays biased positive for the whole climb.
    if f <= F_RISE:
        # hands planted on the rim beside the hips, elbows folded
        return 98.0, 20.0, 88.0
    if f <= F_RISE + 26:
        # the push: elbows extend while the hands stay on the rim
        q = ease(f, F_RISE, F_RISE + 26)
        return 98.0, 20.0 + 12.0 * q, 88.0 - 36.0 * q
    if f <= F_RISE + 44:
        q = ease(f, F_RISE + 26, F_RISE + 44)
        return 98.0 - 8.0 * q, 32.0 - 22.0 * q, 52.0 + 8.0 * q
    if f <= F_WALK:
        q = ease(f, F_RISE + 44, F_WALK)
        return 90.0, 10.0 + 8.0 * q + 4.0 * math.sin(2 * math.pi * f / 90.0), 60.0
    if f <= F_GATHER:
        settle = ease(f, F_WALK, F_WALK + 18)
        return 92.0, 20.0 + 16.0 * math.sin(phase) * settle, 60.0 + 8.0 * math.sin(phase * 2)
    q = ease(f, F_GATHER, F_GATHER + 34)
    swing = 20.0 + 16.0 * math.sin(phase) * (1.0 - q)
    breathe = 2.0 * math.sin(2 * math.pi * f / 96.0)
    return 92.0 - 2.0 * q, swing - 16.0 * q + breathe * q, 60.0 - 6.0 * q

# ----------------------------------------------------------------- rig posing
scene = bpy.context.scene
scene.frame_start, scene.frame_end = 1, FRAME_END
scene.render.fps = FPS
arm = bpy.data.objects["K3_FABLE_MASCOT"]
arm_data = arm.data
REST = {b.name: b.matrix_local.copy() for b in arm_data.bones}
PARENT = {b.name: (b.parent.name if b.parent else None) for b in arm_data.bones}
DES = {}
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"

HIP_OFF = Vector((0.172, 0.0, -0.060))       # asset units, relative to pelvis
SH_OFF = Vector((0.170, 0.0, 0.033))         # relative to chest head
L_THIGH, L_SHIN = 0.2760, 0.2600
L_UPARM, L_FOREARM = 0.5465, 0.4357
SPINE_LEN, CHEST_LEN, NECK_LEN = 0.280, 0.275, 0.285
ANKLE_LIFT = 0.094                            # asset units, contact → ankle

def to_arm(p):
    return Vector(p) / SCALE

def set_pose(name, desired, key_frame=None, key_location=False):
    pb = arm.pose.bones[name]
    parent = PARENT[name]
    if parent:
        basis = REST[name].inverted() @ REST[parent] @ DES[parent].inverted() @ desired
    else:
        basis = REST[name].inverted() @ desired
    DES[name] = desired.copy()
    pb.matrix_basis = basis
    if key_frame is not None:
        pb.keyframe_insert("rotation_quaternion", frame=key_frame)
        # every bone gets a location key: unconnected bones (thighs, clavicles)
        # carry a translation in their basis, and without a key they would all
        # inherit whichever frame was computed last.
        pb.keyframe_insert("location", frame=key_frame)

def desired_matrix(name, head_pos, direction, cap):
    """Rest orientation yawed by cap, then minimally rotated onto `direction`."""
    base = Matrix.Rotation(cap, 3, "Z") @ REST[name].to_3x3()
    y_ref = (base @ Vector((0, 1, 0))).normalized()
    q = y_ref.rotation_difference(Vector(direction).normalized())
    return Matrix.Translation(head_pos) @ (q.to_matrix() @ base).to_4x4()

def solve_ik(root_p, end_p, pole_dir, l1, l2):
    e = end_p - root_p
    d = max(min(e.length, l1 + l2 - 0.006), abs(l1 - l2) + 0.006)
    ehat = e.normalized() if e.length > 1e-8 else Vector((0, 0, -1))
    a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    r = math.sqrt(max(l1 * l1 - a * a, 1e-9))
    fperp = pole_dir - ehat * ehat.dot(pole_dir)
    if fperp.length < 1e-6:
        fperp = Vector((0, 0, 1)) - ehat * ehat.z
    fperp.normalize()
    return root_p + ehat * a + fperp * r

metrics = {"max_leg_reach": 0.0, "min_pelvis_h": 9.9, "pelvis_lowered_frames": 0,
           "max_hand_reach": 0.0, "min_hand_clearance": 9.9, "contacts": {"L": [], "R": []}}
DEBUG_FRAMES = {int(x) for x in P.get("debug_frames", "").split(",") if x.strip()}
DEBUG_LOG = []
NO_ARMS = P.get("no_arms", "0") == "1"

def build_frame(f, key=True):
    feet = {s: foot_state(s, f) for s in ("L", "R")}
    cap = body_cap(f)
    lean = math.radians(torso_lean(f))
    pelvis = pelvis_pos(f, feet)

    # gravity-governed: crouch until both legs stay bent. Lowering only helps
    # when the offending foot is below the hip, so the loop is signed and capped.
    lat = Vector((math.cos(cap), math.sin(cap), 0.0))
    lowered = 0.0
    worst = 0.0
    for _ in range(24):
        worst, worst_gap = 0.0, 0.0
        for side in ("L", "R"):
            hip = pelvis + lat * (HIP_OFF.x * SIGN[side] * SCALE) + Vector((0, 0, HIP_OFF.z * SCALE))
            ankle = feet[side][0] + ground_n(feet[side][0].y) * (ANKLE_LIFT * SCALE)
            d = (ankle - hip).length
            if d > worst:
                worst, worst_gap = d, hip.z - ankle.z
        if worst <= LEG_MAX:
            break
        if worst_gap < 0.01 or lowered >= 0.09:
            metrics.setdefault("infeasible_frames", []).append([f, round(worst, 4)])
            break
        step = min((worst - LEG_MAX) * 1.05 + 0.0003, 0.008)
        pelvis.z -= step
        lowered += step
        metrics["pelvis_lowered_frames"] += 1
    metrics["max_leg_reach"] = max(metrics["max_leg_reach"], worst)
    metrics["min_pelvis_h"] = min(metrics["min_pelvis_h"], pelvis.z - ground_z(pelvis.y))

    fwd = Vector((math.sin(cap), -math.cos(cap), 0.0))
    trunk = (Vector((0, 0, 1)) * math.cos(lean) + fwd * math.sin(lean)).normalized()
    pelvis_a = to_arm(pelvis)

    kf = f if key else None
    set_pose("ROOT", desired_matrix("ROOT", pelvis_a, trunk, cap), kf, key_location=True)
    spine_head = pelvis_a + trunk * SPINE_LEN
    trunk_mid = (Vector((0, 0, 1)) * math.cos(lean * 0.86) + fwd * math.sin(lean * 0.86)).normalized()
    set_pose("SPINE", desired_matrix("SPINE", spine_head, trunk_mid, cap), kf)
    chest_head = spine_head + trunk_mid * CHEST_LEN
    trunk_up = (Vector((0, 0, 1)) * math.cos(lean * 0.62) + fwd * math.sin(lean * 0.62)).normalized()
    set_pose("CHEST", desired_matrix("CHEST", chest_head, trunk_up, cap), kf)

    neck_head = chest_head + trunk_up * NECK_LEN
    pitch = math.radians(head_pitch(f))
    yaw = math.radians(head_yaw(f))
    lat_axis = lat
    head_dir = Matrix.Rotation(-pitch, 3, lat_axis) @ trunk_up
    head_dir = Matrix.Rotation(yaw, 3, Vector((0, 0, 1))) @ head_dir
    set_pose("HEAD", desired_matrix("HEAD", neck_head, head_dir, cap), kf)

    for side in ("L", "R"):
        sgn = SIGN[side]
        # arms: rigid rotations about explicit anatomical axes
        clav_head = chest_head + Vector((0, 0, 0.02))
        if NO_ARMS:
            continue
        set_pose(f"CLAV.{side}", desired_matrix(f"CLAV.{side}", clav_head, lat * sgn, cap), kf)
        shoulder = chest_head + lat * (SH_OFF.x * sgn) + trunk_up * SH_OFF.z
        abduct, swing, flex = arm_angles(f, side)
        cap_rot = Matrix.Rotation(cap, 3, "Z")
        r_arm = (Matrix.Rotation(math.radians(swing), 3, lat)
                 @ Matrix.Rotation(math.radians(abduct), 3, -fwd * sgn))
        m_up = r_arm @ (cap_rot @ REST[f"UPPERARM.{side}"].to_3x3())
        set_pose(f"UPPERARM.{side}", Matrix.Translation(shoulder) @ m_up.to_4x4(), kf)
        dir_up = (m_up @ Vector((0, 1, 0))).normalized()
        elbow = shoulder + dir_up * L_UPARM
        r_fore = Matrix.Rotation(math.radians(flex), 3, lat) @ r_arm
        m_fore = r_fore @ (cap_rot @ REST[f"FOREARM.{side}"].to_3x3())
        set_pose(f"FOREARM.{side}", Matrix.Translation(elbow) @ m_fore.to_4x4(), kf)
        hand = elbow + (m_fore @ Vector((0, 1, 0))).normalized() * L_FOREARM
        metrics["min_hand_clearance"] = min(
            metrics["min_hand_clearance"], hand.z * SCALE - ground_z(hand.y * SCALE))
        # legs
        hip = pelvis_a + (lat * (HIP_OFF.x * sgn) + Vector((0, 0, HIP_OFF.z)))
        contact, planted = feet[side]
        n = ground_n(contact.y)
        ankle = to_arm(contact + n * (ANKLE_LIFT * SCALE))
        # The knee is poled along the GROUND NORMAL, not world up. On a 46°
        # ramp a knee thrown "forward" is thrown into the slope; perpendicular
        # to the surface it is always above it. The tangential term keeps the
        # solve away from the degenerate case where leg and pole align.
        tangent = fwd - n * fwd.dot(n)
        tangent = tangent.normalized() if tangent.length > 1e-6 else fwd
        knee_pole = (n * 0.85 + tangent * 0.45 + lat * (0.25 * sgn)).normalized()
        knee = solve_ik(hip, ankle, knee_pole, L_THIGH, L_SHIN)
        set_pose(f"THIGH.{side}", desired_matrix(f"THIGH.{side}", hip, knee - hip, cap), kf)
        set_pose(f"SHIN.{side}", desired_matrix(f"SHIN.{side}", knee, ankle - knee, cap), kf)
        # The sole is flat in the rest pose, so aligning world-up onto the
        # ground normal lays it parallel to the ramp. Keeping it horizontal
        # instead drove the toe 0.1 m into a 46° slope.
        up = Vector((0, 0, 1))
        q_align = up.rotation_difference(n)
        if not planted:
            q_align = up.rotation_difference(up).slerp(q_align, 0.75)
        m_foot = q_align.to_matrix() @ (Matrix.Rotation(cap, 3, "Z") @ REST[f"FOOT.{side}"].to_3x3())
        set_pose(f"FOOT.{side}", Matrix.Translation(ankle) @ m_foot.to_4x4(), kf)
    return feet, pelvis, cap

if MODE == "full":
    for f in range(1, FRAME_END + 1):
        feet, pelvis, cap = build_frame(f, key=True)
        for side in ("L", "R"):
            metrics["contacts"][side].append([f, round(feet[side][0].x, 5), round(feet[side][0].y, 5),
                                              round(feet[side][0].z, 5), bool(feet[side][1])])
    plan = {
        "fps": FPS, "frames": FRAME_END, "beat_frames": BEAT,
        "timing": {"rise": F_RISE, "stand": F_STAND, "walk": F_WALK,
                    "gather": F_GATHER, "lookup": F_LOOKUP, "contemplate": F_CONTEMPLATE},
        "contact_frames": [beat(b) for b in STEP_BEATS],
        "contact_arclength": CONTACT_S,
        "path_length_m": round(PATH_LEN, 4),
        "step_len_m": STEP_LEN,
        "leg_max_m": round(LEG_MAX, 4),
        "metrics": {k: v for k, v in metrics.items() if k != "contacts"},
        "contacts": metrics["contacts"],
    }
    (TRIAL / "diagnostics" / "motion-plan.json").write_text(
        json.dumps(plan, ensure_ascii=False) + "\n", encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(TRIAL / "scene" / "trial.blend"))
    print("UNRECORDED_RESULT=" + json.dumps({
        "path_length_m": round(PATH_LEN, 4), "rim_contact_s": round(S_RIM, 4),
        "lip_contact_s": round(S_LIP, 4), "step_len_m": round(STEP_LEN, 4),
        "last_contact_s": round(CONTACT_S[-1], 4),
        "max_leg_reach": round(metrics["max_leg_reach"], 5), "leg_max": round(LEG_MAX, 5),
        "min_pelvis_h": round(metrics["min_pelvis_h"], 4),
        "pelvis_lowered_frames": metrics["pelvis_lowered_frames"],
        "max_hand_reach_m": round(metrics["max_hand_reach"], 4),
        "saved": True}, ensure_ascii=False))
else:
    OUT = TRIAL / P.get("out", "iterations/it02-anim-test")
    OUT.mkdir(parents=True, exist_ok=True)
    keep = {"K3_MECHA_BODY", "K3_MECHA_HEAD", "K3_FABLE_MASCOT"}
    for obj in scene.objects:
        if obj.name not in keep:
            obj.hide_render = True
    world = scene.world
    if world and world.use_nodes:
        for node in world.node_tree.nodes:
            if node.type == "BACKGROUND":
                node.inputs[0].default_value = (0.05, 0.06, 0.08, 1.0)
                node.inputs[1].default_value = 1.0
    key_light = bpy.data.lights.new("TEST_KEY", "AREA")
    key_light.energy, key_light.size = 200, 3.0
    key_obj = bpy.data.objects.new("TEST_KEY", key_light)
    scene.collection.objects.link(key_obj)
    key_obj.location = (-2.0, -2.6, 2.6)
    key_obj.rotation_euler = Vector((1.4, 2.0, -1.4)).to_track_quat("-Z", "Y").to_euler()
    cam_data = bpy.data.cameras.new("TEST_CAM_DATA")
    cam_data.lens = 35
    cam = bpy.data.objects.new("TEST_CAM", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = 512, 512
    scene.render.image_settings.file_format = "PNG"
    test_frames = [int(x) for x in P.get("frames", "1,45,70,90,106,140,175,210,240,300,340,360").split(",")]
    written = []
    for f in test_frames:
        scene.frame_set(f)
        feet, pelvis, cap = build_frame(f, key=False)
        scene.view_layers[0].update()
        # positions are local to the floating box root; the camera lives in world space
        root_mw = bpy.data.objects["USTUDIO_BOX_FLOAT_ROOT"].matrix_world
        target = root_mw @ (pelvis + Vector((0, 0, 0.14)))
        view = P.get("view", "threequarter")
        offset = Vector((-2.2, 0.0, 0.10)) if view == "profile" else Vector((-1.75, -1.35, 0.22))
        cam.location = target + root_mw.to_3x3() @ offset
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        path = OUT / f"f{f:03d}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        written.append(path.name)
    if DEBUG_FRAMES:
        f = sorted(DEBUG_FRAMES)[0]
        scene.frame_set(f)
        build_frame(f, key=False)
        scene.view_layers[0].update()
        for name in ("ROOT", "SPINE", "CHEST", "HEAD", "THIGH.L", "UPPERARM.L"):
            got = arm.pose.bones[name].matrix
            want = DES[name]
            DEBUG_LOG.append({
                "bone": name,
                "want_head": [round(c, 4) for c in want.translation],
                "got_head": [round(c, 4) for c in got.translation],
                "want_y_axis": [round(c, 4) for c in (want.to_3x3() @ Vector((0, 1, 0)))],
                "got_y_axis": [round(c, 4) for c in (got.to_3x3() @ Vector((0, 1, 0)))],
            })
    if DEBUG_LOG:
        (TRIAL / "diagnostics" / "pose-debug.json").write_text(
            json.dumps(DEBUG_LOG, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("UNRECORDED_RESULT=" + json.dumps({"rendered": written,
        "max_leg_reach": round(metrics["max_leg_reach"], 5), "leg_max": round(LEG_MAX, 5),
        "infeasible": metrics.get("infeasible_frames", [])[:12],
        "contact_s": [round(s, 3) for s in CONTACT_S], "path_len": round(PATH_LEN, 3)},
        ensure_ascii=False))
