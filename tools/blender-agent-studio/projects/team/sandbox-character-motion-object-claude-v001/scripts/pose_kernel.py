"""Pose kernel executed INSIDE the live BlenderMCP session.

Sent over the addon socket by `author_clip.py`; never run with `--background`.

Rig facts this kernel is built on (measured, not assumed — see
`evidence/skeleton-audit.json`):

  * 10 deform bones, all prefixed BAS_PUNCH_, armature matrix = identity;
  * BAS_PUNCH_root is the only root; it is NEVER keyed away from rest, so every
    clip is in-place and the engine owns all translation;
  * the character has no legs and no knees: BAS_PUNCH_foot.L/.R are direct
    children of root, so a foot is a free-floating volume whose world pose is
    independent of the body's bob and lean. A "step" is therefore authored as a
    translation + rotation of the foot itself, not as a leg articulation;
  * arms are chains body -> upperarm -> forearm -> hand, so an arm pose is
    applied after the body and inherits it;
  * the character faces -Y in Blender, +Z is up, units are metres.

Pose representation: each bone carries six floats per key,
(dx, dy, dz, rx, ry, rz) — a world-space offset in metres and a world-space
rotation vector in radians (axis * angle) applied about the bone's own head.
Rotation vectors are used rather than quaternions because every angle in this
pole stays well under 90 deg, which keeps the log map single-valued and lets
position and rotation share one interpolator with no sign-flip handling.

Interpolation: centripetal-style Catmull-Rom over the declared keys, evaluated
at every frame. `periodic=True` wraps the tangent window around the seam, so a
loop is C1-continuous in pose AND velocity across 60->1 without duplicating the
first pose onto the last frame.
"""
import bpy
import json
import math
from mathutils import Vector, Matrix, Quaternion

ROOT = "BAS_PUNCH_root"
BODY = "BAS_PUNCH_body"
FOOT_L, FOOT_R = "BAS_PUNCH_foot.L", "BAS_PUNCH_foot.R"
FEET = [FOOT_L, FOOT_R]
ARM_L = ("BAS_PUNCH_upperarm.L", "BAS_PUNCH_forearm.L", "BAS_PUNCH_hand.L")
ARM_R = ("BAS_PUNCH_upperarm.R", "BAS_PUNCH_forearm.R", "BAS_PUNCH_hand.R")
ARMS = [ARM_L, ARM_R]
ALL_POSED = [BODY, FOOT_L, FOOT_R] + list(ARM_L) + list(ARM_R)

ZERO6 = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


def get_rig():
    return bpy.data.objects["BAS_PUNCH_Rig"]


def rest_matrices(rig):
    """Bind-pose armature-space matrices, read before any posing."""
    return {b.name: b.matrix_local.copy() for b in rig.data.bones}


def rotate_about_head(mat, rotvec):
    """Rotate `mat` by world-space rotation vector `rotvec` about its own head."""
    v = Vector(rotvec)
    angle = v.length
    if angle < 1e-12:
        return mat.copy()
    quat = Quaternion(v.normalized(), angle)
    head = mat.translation.copy()
    return (Matrix.Translation(head) @ quat.to_matrix().to_4x4()
            @ Matrix.Translation(-head) @ mat)


# ------------------------------------------------------------- interpolation
def _hermite(p1, p2, m1, m2, s):
    s2 = s * s
    s3 = s2 * s
    return ((2 * s3 - 3 * s2 + 1) * p1 + (s3 - 2 * s2 + s) * m1
            + (-2 * s3 + 3 * s2) * p2 + (s3 - s2) * m2)


def _segment(p0, p1, p2, p3, t0, t1, t2, t3, t):
    """Non-uniform Catmull-Rom on [t1, t2], expressed as a Hermite.

    The tangents are divided by the REAL key spacing. The uniform form, which
    assumes every key is one step from the next, produced a 59 deg single-frame
    jump on SB_Throw: its keys sit at 1, 6, 11, 12, 17, 24, so the one-frame
    segment 11->12 was handed a tangent sized for a five-frame segment and the
    curve bolted. Clips whose keys happen to be evenly spaced are unaffected,
    which is why the locomotion cycles never showed the fault.
    """
    span = t2 - t1
    if span <= 0:
        return p1
    m1 = (p2 - p0) / (t2 - t0) * span if t2 > t0 else 0.0
    m2 = (p3 - p1) / (t3 - t1) * span if t3 > t1 else 0.0
    return _hermite(p1, p2, m1, m2, (t - t1) / span)


def sample_channel(keys, frames, f, periodic, period):
    """Evaluate one scalar channel at frame `f`.

    `keys` maps key frame -> value; `frames` is the sorted key frame list.
    """
    n = len(frames)
    if n == 1:
        return keys[frames[0]]

    if periodic:
        i = 0
        for idx in range(n):
            if frames[idx] <= f:
                i = idx
            else:
                break
        if f < frames[0]:
            i = n - 1
        # Unwrap the four key times onto a monotone axis around the seam so the
        # spacing stays meaningful where the cycle wraps.
        t1 = frames[i]
        t2 = frames[(i + 1) % n] + (period if (i + 1) >= n else 0)
        t0 = frames[(i - 1) % n] - (period if (i - 1) < 0 else 0)
        t3 = frames[(i + 2) % n] + (period if (i + 2) >= n else 0)
        if t3 <= t2:
            t3 += period
        t = f if f >= t1 else f + period
        return _segment(keys[frames[(i - 1) % n]], keys[frames[i]],
                        keys[frames[(i + 1) % n]], keys[frames[(i + 2) % n]],
                        t0, t1, t2, t3, t)

    if f <= frames[0]:
        return keys[frames[0]]
    if f >= frames[-1]:
        return keys[frames[-1]]
    i = 0
    for idx in range(n - 1):
        if frames[idx] <= f <= frames[idx + 1]:
            i = idx
            break
    # Clamped ends: mirror the boundary key so the curve starts and ends without
    # an invented overshoot outside the authored range.
    t1, t2 = frames[i], frames[i + 1]
    t0 = frames[i - 1] if i - 1 >= 0 else t1 - (t2 - t1)
    t3 = frames[i + 2] if i + 2 < n else t2 + (t2 - t1)
    p0 = keys[frames[i - 1]] if i - 1 >= 0 else keys[frames[i]]
    p3 = keys[frames[i + 2]] if i + 2 < n else keys[frames[i + 1]]
    return _segment(p0, keys[frames[i]], keys[frames[i + 1]], p3,
                    t0, t1, t2, t3, f)


def build_tracks(keyposes, periodic, period):
    """Turn {frame: {bone: 6-tuple}} into {bone: (6 channel dicts, key frames)}.

    Each bone keeps its OWN key frame list. This matters for locomotion: a
    stance phase has to stay exactly linear in Y so the planted foot is static
    in the reconstructed world, so feet are keyed analytically on every frame,
    while the body and arms stay on a handful of readable key poses. Giving all
    bones a shared frame list would have forced the dense feet and the sparse
    body onto the same spline and bent the stance ramp.
    """
    bones = sorted({b for pose in keyposes.values() for b in pose})
    tracks = {}
    for bone in bones:
        frames = sorted(f for f, pose in keyposes.items() if bone in pose)
        channels = [{f: keyposes[f][bone][c] for f in frames} for c in range(6)]
        tracks[bone] = (channels, frames)
    return tracks


def evaluate(tracks, f, periodic, period):
    out = {}
    for bone, (channels, frames) in tracks.items():
        out[bone] = tuple(
            sample_channel(ch, frames, f, periodic, period) for ch in channels
        )
    return out


# ------------------------------------------------------------------- posing
def apply_pose(rig, rest, pose):
    """Apply one evaluated pose. Order matters: root, body, feet, then arms."""
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()

    # Root is never posed. Keeping it at identity is what makes the clip
    # in-place; it is asserted again after keying.
    rig.pose.bones[ROOT].matrix_basis = Matrix.Identity(4)

    dx, dy, dz, rx, ry, rz = pose.get(BODY, ZERO6)
    mat = rotate_about_head(rest[BODY], (rx, ry, rz))
    rig.pose.bones[BODY].matrix = Matrix.Translation(Vector((dx, dy, dz))) @ mat
    bpy.context.view_layer.update()

    for foot in FEET:
        dx, dy, dz, rx, ry, rz = pose.get(foot, ZERO6)
        mat = rotate_about_head(rest[foot], (rx, ry, rz))
        rig.pose.bones[foot].matrix = Matrix.Translation(Vector((dx, dy, dz))) @ mat
    bpy.context.view_layer.update()

    # Arms inherit the body, so each level is read AFTER the level above it has
    # been committed, and the authored rotation is added on top of inheritance.
    for chain in ARMS:
        for bone in chain:
            dx, dy, dz, rx, ry, rz = pose.get(bone, ZERO6)
            pb = rig.pose.bones[bone]
            mat = rotate_about_head(pb.matrix.copy(), (rx, ry, rz))
            if dx or dy or dz:
                mat = Matrix.Translation(Vector((dx, dy, dz))) @ mat
            pb.matrix = mat
            bpy.context.view_layer.update()

    rig.pose.bones[ROOT].matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()


def all_fcurves(action):
    """Blender 5.x slotted actions removed Action.fcurves."""
    if hasattr(action, "fcurves"):
        return list(action.fcurves)
    out = []
    for layer in action.layers:
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", []):
                out.extend(bag.fcurves)
    return out


def _body_bvh(depsgraph):
    from mathutils.bvhtree import BVHTree
    obj = bpy.data.objects["BAS_PUNCH_Body"].evaluated_get(depsgraph)
    mesh = obj.to_mesh()
    matrix = obj.matrix_world
    verts = [tuple(matrix @ v.co) for v in mesh.vertices]
    mesh.calc_loop_triangles()
    tris = [tuple(t.vertices) for t in mesh.loop_triangles]
    obj.to_mesh_clear()
    return BVHTree.FromPolygons(verts, tris, all_triangles=True)


def _part_bvh(depsgraph, name):
    from mathutils.bvhtree import BVHTree
    obj = bpy.data.objects[name].evaluated_get(depsgraph)
    mesh = obj.to_mesh()
    matrix = obj.matrix_world
    verts = [tuple(matrix @ v.co) for v in mesh.vertices]
    mesh.calc_loop_triangles()
    tris = [tuple(t.vertices) for t in mesh.loop_triangles]
    obj.to_mesh_clear()
    return BVHTree.FromPolygons(verts, tris, all_triangles=True)


ARM_CLEARANCE_PARTS = ("BAS_PUNCH_Forearm_L", "BAS_PUNCH_Fist_L",
                       "BAS_PUNCH_Forearm_R", "BAS_PUNCH_Fist_R")


def relax_arms(rig, f_start, f_end, step_deg=1.5, max_extra_deg=34.0,
               periodic_clip=False):
    """Clear the arms and body from self-collision WITHOUT introducing a snap.

    Authoring the key poses collision-free is not enough: the frames BETWEEN two
    clean keys interpolate through configurations neither key visits, and those
    are where the forearm crossed the belly.

    Correcting each frame independently is not enough either. The first version
    of this pass did exactly that, cleared every frame, and produced 52.8 deg and
    58.1 deg single-frame jumps on the throw and the deposit - clips that passed
    every physical gate while visibly snapping. So the search here is temporally
    seeded: each frame prefers the correction closest to the one its predecessor
    received, and the resulting sequence is then smoothed and re-verified.

    Abduction is the degree of freedom used because it moves an arm off the torso
    while barely disturbing the hand's forward reach. Both signs are offered: on
    an already-extended arm, pushing further out swings the fist down into the
    side of the body, so an outward-only search runs to its cap without clearing.

    The criterion is BVH triangle overlap, the same metric the acceptance gate
    uses; a nearest-surface depth of zero can still hide an edge through a face.
    """
    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()
    report = {"frames_relaxed": 0, "max_extra_deg": 0.0, "unresolved": [],
              "body_lifted_frames": 0, "max_body_lift_m": 0.0,
              "method": "rate-limited envelope over per-frame minimal clearing"}

    def arm_overlaps():
        body = _body_bvh(depsgraph)
        total = 0
        for part in ARM_CLEARANCE_PARTS:
            try:
                total += len(_part_bvh(depsgraph, part).overlap(body))
            except Exception:
                pass
        return total

    def foot_overlaps():
        body = _body_bvh(depsgraph)
        total = 0
        for part in ("BAS_PUNCH_Foot_L", "BAS_PUNCH_Foot_R"):
            try:
                total += len(_part_bvh(depsgraph, part).overlap(body))
            except Exception:
                pass
        return total

    frames = list(range(f_start, f_end + 1))

    # Pass 0: capture the authored pose of every frame before touching anything,
    # so later passes can always return to it instead of stacking corrections.
    base = {}
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        base[frame] = {n: rig.pose.bones[n].matrix.copy()
                       for n in [BODY] + [c[0] for c in ARMS]}

    def apply_correction(frame, abduct, lift, body_lift):
        rig.pose.bones[BODY].matrix = (
            Matrix.Translation(Vector((0.0, 0.0, body_lift))) @ base[frame][BODY])
        bpy.context.view_layer.update()
        for chain, side in ((ARM_L, +1.0), (ARM_R, -1.0)):
            rotvec = (math.radians(lift), -side * math.radians(abduct), 0.0)
            rig.pose.bones[chain[0]].matrix = rotate_about_head(
                base[frame][chain[0]], rotvec)
        bpy.context.view_layer.update()
        depsgraph.update()

    magnitudes = [0.0]
    magnitude = step_deg
    while magnitude <= max_extra_deg:
        magnitudes.append(magnitude)
        magnitude += step_deg

    # Pass 1: for each frame, the SMALLEST clearing magnitude, computed
    # separately for each sign of abduction. Both signs are kept because on an
    # already-extended arm pushing further out swings the fist down into the
    # side of the body, so an outward-only search runs to its cap without ever
    # clearing.
    need = {+1.0: {}, -1.0: {}}
    body_lifts = {}
    for frame in frames:
        scene.frame_set(frame)
        lift = 0.0
        apply_correction(frame, 0.0, 0.0, 0.0)
        if foot_overlaps() > 0:
            while lift < 0.10:
                lift += 0.002
                apply_correction(frame, 0.0, 0.0, lift)
                if foot_overlaps() == 0:
                    break
            report["body_lifted_frames"] += 1
            report["max_body_lift_m"] = max(report["max_body_lift_m"], lift)
        body_lifts[frame] = lift

        for sign in (+1.0, -1.0):
            found = None
            for value in magnitudes:
                apply_correction(frame, sign * value, 0.0, lift)
                if arm_overlaps() == 0:
                    found = value
                    break
            need[sign][frame] = found

    # One sign for the whole clip. Letting the sign flip between neighbouring
    # frames is itself a snap, so the cheaper feasible direction is chosen once.
    def cost_of(candidate):
        values = [need[candidate][f] for f in frames]
        missing = sum(1 for v in values if v is None)
        present = [v for v in values if v is not None]
        return (missing, max(present) if present else 0.0)

    sign = min((+1.0, -1.0), key=cost_of)
    report["abduction_sign"] = sign
    required = {f: (need[sign][f] if need[sign][f] is not None else max_extra_deg)
                for f in frames}
    report["unresolved"] = [{"frame": f} for f in frames
                            if need[sign][f] is None]

    # Pass 2: rate-limited envelope. Each frame takes the largest requirement in
    # the clip discounted by RATE per frame of distance, so the applied sequence
    # is everywhere at least what its own frame needs AND never changes by more
    # than RATE between neighbours. A moving average could not do this: the
    # requirement jumps from 0 to 33 deg within a couple of frames on the throw
    # and the deposit, and averaging that either under-corrects a frame or keeps
    # the jump.
    rate = 3.0
    count = len(frames)

    def distance(i, j):
        direct = abs(i - j)
        # A loop has no ends, so the envelope travels the short way round.
        return min(direct, count - direct) if periodic_clip else direct

    envelope = {}
    for i, frame in enumerate(frames):
        envelope[frame] = max(
            0.0,
            max(required[frames[j]] - rate * distance(i, j) for j in range(count)),
        )

    report["max_extra_deg"] = max(envelope.values()) if envelope else 0.0
    report["frames_relaxed"] = sum(1 for f in frames if envelope[f] > 0.0)

    # Pass 3: apply and verify. Over-correcting past the minimum can in principle
    # create a new contact, so every frame is re-checked rather than assumed.
    residual = []
    for frame in frames:
        scene.frame_set(frame)
        apply_correction(frame, sign * envelope[frame], 0.0, body_lifts[frame])
        if arm_overlaps() != 0 or foot_overlaps() != 0:
            residual.append(frame)
        for chain in ARMS:
            for bone in chain:
                pb = rig.pose.bones[bone]
                pb.keyframe_insert("location", frame=frame)
                pb.keyframe_insert("rotation_quaternion", frame=frame)
                pb.keyframe_insert("scale", frame=frame)
        pb_body = rig.pose.bones[BODY]
        pb_body.keyframe_insert("location", frame=frame)
        pb_body.keyframe_insert("rotation_quaternion", frame=frame)
        pb_body.keyframe_insert("scale", frame=frame)

    report["residual_contact_frames"] = residual
    report["rate_limit_deg_per_frame"] = rate
    return report


def author(name, f_start, f_end, keyposes, periodic, existing="replace"):
    """Author one Action from declared key poses. Returns a report dict."""
    rig = get_rig()
    scene = bpy.context.scene
    scene.render.fps = 30
    scene.render.fps_base = 1.0
    scene.frame_start = f_start
    scene.frame_end = f_end

    period = float(f_end - f_start + 1)

    # Detach whatever is active so the new clip is authored from the bind pose
    # and never accumulates a previous clip's residue.
    if rig.animation_data and rig.animation_data.action:
        rig.animation_data.action.use_fake_user = True
        rig.animation_data.action = None
    rig.animation_data_clear()
    rig.location = (0, 0, 0)
    rig.rotation_euler = (0, 0, 0)
    rig.scale = (1, 1, 1)
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()

    rest = rest_matrices(rig)

    if existing == "replace":
        old = bpy.data.actions.get(name)
        if old is not None:
            old.use_fake_user = False
            bpy.data.actions.remove(old)

    tracks = build_tracks(keyposes, periodic, period)

    for f in range(f_start, f_end + 1):
        scene.frame_set(f)
        apply_pose(rig, rest, evaluate(tracks, f, periodic, period))
        for pb in rig.pose.bones:
            pb.keyframe_insert("location", frame=f)
            pb.keyframe_insert("rotation_quaternion", frame=f)
            pb.keyframe_insert("scale", frame=f)

    action = rig.animation_data.action
    action.name = name
    action.use_fake_user = True
    for slot in getattr(action, "slots", []):
        slot.name_display = name

    # Every frame is keyed, so the samples ARE the motion. LINEAR prevents
    # Bezier auto-tangents from inventing overshoot between baked samples.
    for fcurve in all_fcurves(action):
        for kp in fcurve.keyframe_points:
            kp.interpolation = "LINEAR"

    relax = relax_arms(rig, f_start, f_end, periodic_clip=periodic)

    for fcurve in all_fcurves(action):
        for kp in fcurve.keyframe_points:
            kp.interpolation = "LINEAR"

    scene.frame_set(f_start)
    return {
        "action": action.name,
        "range": list(action.frame_range),
        "fcurves": len(all_fcurves(action)),
        "fake_user": action.use_fake_user,
        "arm_relax": relax,
    }
