"""Solve the carry arm pose against the real carry zone, in the live session.

The gameplay code holds a carried object at Unity-local (side, y=0.86, z=+0.62),
which is Blender (x=side, y=-0.62, z=0.86) with side in {-0.16, 0, +0.16}. The
solver drives the EVALUATED fist meshes toward the sides of that volume and
reports the residual, because the answer to "can this rig actually hold the
object where the code puts it" has to be measured, not asserted.

Search is a bounded coordinate descent over the upper-arm and forearm rotation
vectors plus the body pitch, evaluating the true fist centroid each step. It is
slow but it is honest: no inverse-kinematics assumption, no guessed angle.

Prints the best pose found and the residual distance for both object envelopes.
"""
import bpy
import json
import math
from mathutils import Vector, Matrix, Quaternion

import pose_kernel as pk

CARRY_Y = -0.62
CARRY_Z = 0.86
SLOTS = (-0.16, 0.0, 0.16)
ROCK = (0.66, 0.55, 0.62)
TROPHY = (0.78, 1.00, 0.78)


def fist_centroid(rig, depsgraph, name):
    obj = bpy.data.objects[name].evaluated_get(depsgraph)
    mesh = obj.to_mesh()
    matrix = obj.matrix_world
    pts = [matrix @ v.co for v in mesh.vertices]
    centroid = sum(pts, Vector((0, 0, 0))) / len(pts)
    obj.to_mesh_clear()
    return centroid


def apply(rig, rest, body, upper_l, fore_l, hand_l):
    pose = {
        pk.BODY: body,
        pk.ARM_L[0]: upper_l, pk.ARM_L[1]: fore_l, pk.ARM_L[2]: hand_l,
        # Mirror across X: negate the X offset and the Y/Z rotation components.
        pk.ARM_R[0]: (-upper_l[0], upper_l[1], upper_l[2],
                      upper_l[3], -upper_l[4], -upper_l[5]),
        pk.ARM_R[1]: (-fore_l[0], fore_l[1], fore_l[2],
                      fore_l[3], -fore_l[4], -fore_l[5]),
        pk.ARM_R[2]: (-hand_l[0], hand_l[1], hand_l[2],
                      hand_l[3], -hand_l[4], -hand_l[5]),
    }
    pk.apply_pose(rig, rest, pose)


def solve(target_x=0.36, target_y=CARRY_Y, target_z=CARRY_Z,
          pitch_penalty=0.35, pitch_bounds=(-0.05, 0.45)):
    """Find arm angles putting the LEFT fist centroid on the given target.

    `pitch_penalty` prices the body lean the solver is allowed to spend to
    reach: a pose is only worth its reach if it stays readable, so leaning is
    made to cost something rather than being free.
    """
    rig = pk.get_rig()
    if rig.animation_data:
        rig.animation_data.action = None
    rig.animation_data_clear()
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    rest = pk.rest_matrices(rig)
    depsgraph = bpy.context.evaluated_depsgraph_get()

    target = Vector((target_x, target_y, target_z))

    # Parameters: body pitch, then the two arm rotation vectors (radians).
    params = [0.0,                      # body rx (forward lean)
              0.0, 0.0, 0.0,            # upperarm rx, ry, rz
              0.0, 0.0, 0.0]            # forearm rx, ry, rz
    bounds = [pitch_bounds,
              (-1.6, 0.6), (-0.9, 0.9), (-0.9, 0.9),
              (-1.6, 0.9), (-0.9, 0.9), (-0.9, 0.9)]

    # Body-collision penalty. Without it the solver happily routes the arm
    # THROUGH the belly to reach the target: the first carry solve buried the
    # forearm 0.135 m inside the body sphere, and all six object clips built on
    # it inherited the fault. Reaching a point is only a solution if the arm can
    # get there AROUND the body.
    from mathutils.bvhtree import BVHTree

    def body_bvh():
        obj = bpy.data.objects["BAS_PUNCH_Body"].evaluated_get(depsgraph)
        mesh = obj.to_mesh()
        matrix = obj.matrix_world
        verts = [tuple(matrix @ v.co) for v in mesh.vertices]
        mesh.calc_loop_triangles()
        tris = [tuple(t.vertices) for t in mesh.loop_triangles]
        obj.to_mesh_clear()
        return BVHTree.FromPolygons(verts, tris, all_triangles=True)

    def depth_into(name, bvh, stride):
        obj = bpy.data.objects[name].evaluated_get(depsgraph)
        mesh = obj.to_mesh()
        matrix = obj.matrix_world
        worst = 0.0
        for i in range(0, len(mesh.vertices), stride):
            point = matrix @ mesh.vertices[i].co
            hit = bvh.find_nearest(point)
            if hit[0] is not None:
                location, normal, _, distance = hit
                if (point - location).dot(normal) < 0.0 and distance > worst:
                    worst = distance
        obj.to_mesh_clear()
        return worst

    # Bind-pose depths first, so the shoulder socket is judged on how much
    # DEEPER it sinks, not against an absolute zero it can never reach.
    PARTS = ("BAS_PUNCH_Forearm_L", "BAS_PUNCH_Fist_L", "BAS_PUNCH_UpperArm_L")
    TOLERANCE = {"BAS_PUNCH_Forearm_L": 0.0, "BAS_PUNCH_Fist_L": 0.0,
                 "BAS_PUNCH_UpperArm_L": 0.015}
    apply(rig, rest, (0.0,) * 6, (0.0,) * 6, (0.0,) * 6, (0.0,) * 6)
    depsgraph.update()
    rest_bvh = body_bvh()
    rest_depths = {p: depth_into(p, rest_bvh, 4) for p in PARTS}

    def cost(values, stride=8):
        body = (0.0, 0.0, 0.0, values[0], 0.0, 0.0)
        upper = (0.0, 0.0, 0.0, values[1], values[2], values[3])
        fore = (0.0, 0.0, 0.0, values[4], values[5], values[6])
        apply(rig, rest, body, upper, fore, (0.0,) * 6)
        depsgraph.update()
        left = fist_centroid(rig, depsgraph, "BAS_PUNCH_Fist_L")
        bvh_now = body_bvh()
        penalty = sum(
            max(0.0, depth_into(p, bvh_now, stride) - rest_depths[p] - TOLERANCE[p])
            for p in PARTS
        )
        # Body pitch is not free: leaning forward to reach costs readability, so
        # it is priced rather than exploited without limit.
        return ((left - target).length + pitch_penalty * abs(values[0])
                + 12.0 * penalty)

    step = [0.20] * 7
    best = cost(params)
    for _ in range(60):
        improved = False
        for i in range(7):
            for direction in (+1.0, -1.0):
                trial = list(params)
                trial[i] = max(bounds[i][0],
                               min(bounds[i][1], trial[i] + direction * step[i]))
                if trial[i] == params[i]:
                    continue
                value = cost(trial)
                if value < best - 1e-6:
                    params, best, improved = trial, value, True
        if not improved:
            step = [s * 0.5 for s in step]
            if max(step) < 1e-4:
                break

    body = (0.0, 0.0, 0.0, params[0], 0.0, 0.0)
    upper = (0.0, 0.0, 0.0, params[1], params[2], params[3])
    fore = (0.0, 0.0, 0.0, params[4], params[5], params[6])
    apply(rig, rest, body, upper, fore, (0.0,) * 6)
    depsgraph.update()
    left = fist_centroid(rig, depsgraph, "BAS_PUNCH_Fist_L")
    right = fist_centroid(rig, depsgraph, "BAS_PUNCH_Fist_R")

    residuals = {}
    for label, (sx, sy, sz) in (("rock", ROCK), ("trophy", TROPHY)):
        per_slot = {}
        for slot in SLOTS:
            centre = Vector((slot, CARRY_Y, CARRY_Z))
            # Signed distance from the fist centroid to the box surface: negative
            # means the fist is inside the object volume.
            def sd(point):
                d = Vector((abs(point.x - centre.x) - sx / 2.0,
                            abs(point.y - centre.y) - sy / 2.0,
                            abs(point.z - centre.z) - sz / 2.0))
                outside = Vector((max(d.x, 0.0), max(d.y, 0.0), max(d.z, 0.0)))
                return outside.length + min(max(d.x, max(d.y, d.z)), 0.0)
            per_slot[f"{slot:+.2f}"] = {
                "left_signed_distance_m": sd(left),
                "right_signed_distance_m": sd(right),
            }
        residuals[label] = per_slot

    return {
        "body_rx_deg": math.degrees(params[0]),
        "upperarm": [round(math.degrees(v), 4) for v in params[1:4]],
        "forearm": [round(math.degrees(v), 4) for v in params[4:7]],
        "fist_left": list(left),
        "fist_right": list(right),
        "target_left": list(target),
        "residual_to_target_m": (left - target).length,
        "envelope_residuals": residuals,
    }
