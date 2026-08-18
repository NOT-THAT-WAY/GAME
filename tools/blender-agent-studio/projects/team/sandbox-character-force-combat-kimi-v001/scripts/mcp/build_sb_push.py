# SB_Push — anchor 3. MCP session only.
# 1-30 loop: the player ACTS. Wide stable stance (feet planted, never slide),
# body hinged forward about its real pivot, hands pressed on a vertical proxy
# plane derived from evaluated fist geometry at f1. Cyclic effort = harmonic
# body pitch/bob; a deterministic 2-link numeric solve keeps the fists glued
# to their targets (no pumping, no drift). Period-30 harmonics => pose(f+30)
# == pose(f), continuous seam in position and velocity.
exec(open("projects/team/sandbox-character-force-combat-kimi-v001/scripts/mcp/kimi_anim_lib.py").read())

guard()
arm = get_arm()
sc = bpy.context.scene
sc.render.fps = 30
sc.render.fps_base = 1.0
sc.frame_start, sc.frame_end = 1, 30
PERIOD = 30.0

REST = rest_mats(arm)
UA_L, FA_L, HA_L = CHAINS[0]
UA_R, FA_R, HA_R = CHAINS[1]

# fist mesh centres at rest (world), and their offset from the hand bone head
FIST_CENTRE_REST = {}
HAND_HEAD_REST = {}
for side, hn in (("L", HA_L), ("R", HA_R)):
    o = bpy.data.objects["BAS_PUNCH_Fist_%s" % side]
    c = sum((v.co for v in o.data.vertices), Vector()) / len(o.data.vertices)
    FIST_CENTRE_REST[side] = o.matrix_world @ c
    HAND_HEAD_REST[side] = (REST[hn]).translation.copy()

# ---- stance: feet wider and slightly staggered; translation only, soles flat
FOOT_OFF = {"BAS_PUNCH_foot.L": Vector((0.08, -0.05, 0.0)),
            "BAS_PUNCH_foot.R": Vector((-0.08, 0.05, 0.0))}

# ---- push targets for the fist centres (reachable, clear of the body sphere)
TARGET = {"L": Vector((0.775, -0.655, 1.005)), "R": Vector((-0.775, -0.655, 1.005))}
YAW_0 = {"L": -35.0, "R": 35.0}
ELBOW_OUT = {"L": 0.0, "R": 0.0}  # fixed outward horizontal fold at the elbow    # initial guess for the solve
A1_0, A2_0 = -75.0, -5.0          # initial guess for the solve (deg, world X)


def body_spec(f):
    th = 2.0 * math.pi * (f - 1) / PERIOD
    pitch = 10.0 + 1.0 * math.sin(th)
    yaw = 0.6 * math.sin(th + 0.9)
    dz = -0.055 + 0.007 * math.sin(th + 0.4)
    dy = -0.030 + 0.004 * math.sin(th + 1.7)
    return ([(X, pitch), (Z, yaw)], Vector((0.0, dy, dz)))


def pose_body_feet(f):
    reset_pose(arm)
    rots, off = body_spec(f)
    pb = arm.pose.bones[BODY]
    q = Quaternion()
    for axis, ang in rots:
        q = Quaternion(axis, math.radians(ang)) @ q
    m = rot_about_head(pb.matrix.copy(), q)
    pb.matrix = Matrix.Translation(off) @ m
    for fn, fo in FOOT_OFF.items():
        pf = arm.pose.bones[fn]
        pf.matrix = Matrix.Translation(fo) @ pf.matrix.copy()
    bpy.context.view_layer.update()


def fist_world(side):
    hn = HA_L if side == "L" else HA_R
    m = arm.pose.bones[hn].matrix
    rest_m = REST[hn]
    return (m @ rest_m.inverted()) @ FIST_CENTRE_REST[side]


def solve_arm(side, target, yaw, a1, a2):
    """UA: yaw about Z then a1 about X (world, about its head); FA: a2 about X.
    Newton-solve the three angles so the fist centre hits target (x,y,z)."""
    ua, fa, ha = {"L": CHAINS[0], "R": CHAINS[1]}[side]

    def build(yawv, a1v, a2v):
        for bn in (ua, fa, ha):
            arm.pose.bones[bn].matrix_basis = Matrix.Identity(4)
        bpy.context.view_layer.update()
        pb_u = arm.pose.bones[ua]
        m = pb_u.matrix.copy()
        q = Quaternion(X, math.radians(a1v)) @ Quaternion(Z, math.radians(yawv))
        pb_u.matrix = rot_about_head(m, q)
        bpy.context.view_layer.update()
        pb_f = arm.pose.bones[fa]
        qf = Quaternion(X, math.radians(a2v)) @ Quaternion(
            Z, math.radians(ELBOW_OUT[side]))
        pb_f.matrix = rot_about_head(pb_f.matrix.copy(), qf)
        bpy.context.view_layer.update()
        return fist_world(side)

    for _ in range(60):
        f0 = build(yaw, a1, a2)
        err = target - f0
        if err.length < 1e-6:
            break
        eps = 0.4
        cols = []
        for d in ((eps, 0, 0), (0, eps, 0), (0, 0, eps)):
            fv = build(yaw + d[0], a1 + d[1], a2 + d[2])
            cols.append([(fv[i] - f0[i]) / eps for i in range(3)])
        # solve J . da = err by Cramer
        a11, a12, a13 = cols[0][0], cols[1][0], cols[2][0]
        a21, a22, a23 = cols[0][1], cols[1][1], cols[2][1]
        a31, a32, a33 = cols[0][2], cols[1][2], cols[2][2]
        det = (a11 * (a22 * a33 - a23 * a32)
               - a12 * (a21 * a33 - a23 * a31)
               + a13 * (a21 * a32 - a22 * a31))
        if abs(det) < 1e-9:
            break
        b1, b2, b3 = err.x, err.y, err.z
        dyaw = (b1 * (a22 * a33 - a23 * a32) - a12 * (b2 * a33 - a23 * b3)
                + a13 * (b2 * a32 - a22 * b3)) / det
        da1 = (a11 * (b2 * a33 - a23 * b3) - b1 * (a21 * a33 - a23 * a31)
               + a13 * (a21 * b3 - b2 * a31)) / det
        da2 = (a11 * (a22 * b3 - b2 * a32) - a12 * (a21 * b3 - b2 * a31)
               + b1 * (a21 * a32 - a22 * a31)) / det
        yaw += max(-12.0, min(12.0, dyaw))
        a1 += max(-12.0, min(12.0, da1))
        a2 += max(-12.0, min(12.0, da2))
    f_end = build(yaw, a1, a2)
    # ride-out: slide forearm+hand 1.5 mm along the arm axis so the elbow
    # socket keeps its rest depth (socket = source construction overlap)
    pb_u = arm.pose.bones[ua]
    pb_f = arm.pose.bones[fa]
    d = (pb_f.matrix.translation - pb_u.matrix.translation).normalized() * 0.0015
    pb_f.matrix = Matrix.Translation(d) @ pb_f.matrix.copy()
    bpy.context.view_layer.update()
    pb_h = arm.pose.bones[ha]
    pb_h.matrix = Matrix.Translation(d) @ pb_h.matrix.copy()
    bpy.context.view_layer.update()
    f_end = fist_world(side)
    return yaw, a1, a2, f_end


# drop any stray auto-keyed action from earlier attempts, then author fresh
detach_action(arm)
for a in list(bpy.data.actions):
    if a.name not in ("SB_Idle", "BAS_PUNCH_Rig|BAS_PUNCH_Rig|BAS_PUNCH_punch",
                      "SB_Punch", "SB_HitReact", "SB_Push"):
        bpy.data.actions.remove(a)
act = new_action(arm, "SB_Push")
report = {"fist_track": {"L": [], "R": []}}
for f in range(1, 31):
    sc.frame_set(f)
    pose_body_feet(f)
    for side in ("L", "R"):
        yaw, a1, a2, fw = solve_arm(side, TARGET[side], YAW_0[side], A1_0, A2_0)
        report["fist_track"][side].append([round(v, 5) for v in fw])
    key_all(arm, f)

force_linear(act)
sc.frame_set(1)

# plane proxy derived from evaluated fist geometry at f1 (front surface, min Y)
sc.frame_set(1)
dg = bpy.context.evaluated_depsgraph_get()
front = 1e9
for side in ("L", "R"):
    o = bpy.data.objects["BAS_PUNCH_Fist_%s" % side]
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    mw = ev.matrix_world
    front = min(front, min((mw @ v.co).y for v in me.vertices))
    ev.to_mesh_clear()
report["proxy_plane_y"] = round(front, 6)
report["action"] = act.name
report["frame_range"] = list(act.frame_range)
print(json.dumps(report))
