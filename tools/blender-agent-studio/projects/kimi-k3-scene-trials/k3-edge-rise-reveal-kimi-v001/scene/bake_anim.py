"""BAKE v2 — animation des 4 temps, frame par frame (1-360).
Assis genoux remontés sur le rim horizontal (la pente passe AU-DESSUS du bord :
les jambes pendantes sont impossibles), lever par bascule avant, marche sur la
pente réelle, appuis sur la grille 148.9 BPM, contemplation finale.
Espace armature = repère float-root local / 0.413, front +Y.
"""
import bpy, math
from mathutils import Vector, Matrix

S = 0.413
P0 = Vector((0, -0.4494 / S, 0.9722 / S))   # bas de la pente (armature)
U  = Vector((0, 0.6800, 0.7332))            # tangent montant
N  = Vector((0, -0.7332, 0.6800))           # normale surface
FO = 0.062                      # rayon capsule mesuré (~0.057 arm) + marge : contact réel
RIM_TOP = 0.931 / S             # 2.254
BEAT0, BEAT_T = 9.0, 12.089

L_THIGH, L_SHIN = 0.208, 0.405
L_UPA,  L_FORE  = 0.316, 0.323

def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)

def prof(keys, f):
    if f <= keys[0][0]: return keys[0][1]
    if f >= keys[-1][0]: return keys[-1][1]
    for (f0, v0), (f1, v1) in zip(keys, keys[1:]):
        if f0 <= f <= f1:
            return v0 + (v1 - v0) * smooth((f - f0) / (f1 - f0))
    return keys[-1][1]

def prof3(keys, f):
    return Vector((prof([(k, v[0]) for k, v in keys], f),
                   prof([(k, v[1]) for k, v in keys], f),
                   prof([(k, v[2]) for k, v in keys], f)))

def solve2(hip, target, l1, l2, bend):
    d = target - hip
    dist = min(d.length, (l1 + l2) * 0.999)
    dn = d.normalized()
    b = bend - dn * bend.dot(dn)
    if b.length < 1e-6:
        b = Vector((0, 0, 1)) - dn * dn.z
    b.normalize()
    ca = max(-1.0, min(1.0, (l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist)))
    sa = math.sqrt(max(0.0, 1 - ca * ca))
    return hip + dn * (ca * l1) + b * (sa * l1)

def bone_mat(head_p, tail_p, z_hint):
    y = (tail_p - head_p).normalized()
    z = z_hint - y * z_hint.dot(y)
    if z.length < 1e-6:
        z = Vector((1, 0, 0)) - y * y.x
    z.normalize()
    x = y.cross(z)
    M = Matrix((x, y, z)).transposed().to_4x4()
    M.translation = head_p
    return M

def frame_mat(yaw_deg, pitch_deg, roll_deg=0.0):
    yaw, pitch, roll = map(math.radians, (yaw_deg, pitch_deg, roll_deg))
    return (Matrix.Rotation(yaw, 3, 'Z') @ Matrix.Rotation(-pitch, 3, 'X')
            @ Matrix.Rotation(roll, 3, 'Y'))

def slope_pt(s, off=FO):
    return P0 + U * s + N * off

# ---------------------------------------------------------------- contacts
L_SIT_X, R_SIT_X = -0.29, 0.29     # assis genoux remontés
L_X, R_X = -0.17, 0.17             # marche : sous les hanches
RIM_FOOT = {'L': Vector((L_SIT_X, -1.20, RIM_TOP + FO)),
            'R': Vector((R_SIT_X, -1.20, RIM_TOP + FO))}
STEPS = [(130, 'L', 0.10), (154, 'R', 0.28), (178, 'L', 0.44), (203, 'R', 0.60),
         (227, 'L', 0.76), (251, 'R', 0.92), (275, 'L', 1.08), (299, 'R', 1.24)]

def contact_pos(st):
    p = slope_pt(st[2])
    p.x = L_X if st[1] == 'L' else R_X
    return p

def foot_state(f):
    """(pos_L, pos_R) espace armature. Zéro drift pendant les appuis."""
    pos = {}
    for side in ('L', 'R'):
        done   = [st for st in STEPS if st[1] == side and st[0] <= f]
        future = [st for st in STEPS if st[1] == side and st[0] > f]
        if not done:
            p = RIM_FOOT[side].copy()
            if side == 'R' and f < 68:
                # pied qui bat le tempo : contact PILE sur les beats, levé vertical
                tap = 0.0
                k = int((f - BEAT0) / BEAT_T)
                for kk in (k, k + 1):
                    b0 = BEAT0 + kk * BEAT_T
                    if b0 <= f <= b0 + BEAT_T:
                        tap = max(tap, math.sin(math.pi * (f - b0) / BEAT_T))
                p.z += 0.06 * tap
            pos[side] = p
            continue
        last = done[-1]
        if future:
            nxt = future[0]
            opp = [st for st in STEPS if st[1] != side and st[0] < nxt[0]]
            f_start = (opp[-1][0] + 4) if opp else nxt[0] - 20
            if f >= f_start:
                p0 = contact_pos(last)
                p1 = contact_pos(nxt)
                t = smooth((f - f_start) / max(1, nxt[0] - f_start))
                clear = 0.10 if nxt[0] == 130 else 0.085   # grande marche d'entrée
                pos[side] = p0.lerp(p1, t) + N * (clear * math.sin(math.pi * t))
                continue
        pos[side] = contact_pos(last)
    return pos['L'], pos['R']

# points d'appui pour le bassin : milieu des pieds posés à chaque contact
def support_keys():
    keys = [(100, Vector((0, -1.20, RIM_TOP + FO + 0.60)) + Vector((0, -0.02, 0.10)))]
    prev = {'L': RIM_FOOT['L'], 'R': RIM_FOOT['R']}
    extra = []
    for st in STEPS:
        prev[st[1]] = contact_pos(st)
        mid = (prev['L'] + prev['R']) / 2
        keys.append((st[0], Vector((0, mid.y - 0.02, mid.z + 0.60))))
        if st[0] == 203:
            extra.append((215, Vector((0, mid.y - 0.01, mid.z + 0.60))))
    keys.extend(extra)
    # pose finale : légère extension
    last_mid = (prev['L'] + prev['R']) / 2
    keys.append((315, Vector((0, last_mid.y - 0.02, last_mid.z + 0.605))))
    keys.append((330, Vector((0, last_mid.y - 0.02, last_mid.z + 0.625))))
    keys.append((360, Vector((0, last_mid.y - 0.02, last_mid.z + 0.625))))
    keys.sort(key=lambda k: k[0])
    return keys

SUPPORT = support_keys()

def pelvis_pos(f):
    if f <= 100:
        p = prof3([(1,   (0.0, -1.501, 2.484)),
                   (57,  (0.0, -1.501, 2.484)),
                   (68,  (0.0, -1.530, 2.430)),   # bascule arrière (élan)
                   (78,  (0.0, -1.340, 2.550)),   # bascule avant, fesses décollées
                   (90,  (0.0, -1.220, 2.900)),
                   (100, SUPPORT[0][1])], f)
    else:
        p = prof3(SUPPORT, f)
        bob = 0.0
        for c, _, _ in STEPS:
            d = (f - c) / 24.2
            if abs(d) < 1:
                bob = min(bob, -0.020 * (1 - abs(d)))
        sway = 0.045 * math.sin(2 * math.pi * (f - 106) / 48.4) if f < 305 else 0.0
        p = p + Vector((sway, 0, bob))
    p.z += 0.006 * math.sin(2 * math.pi * f / 45.0)   # respiration
    return p

def torso_pitch(f):
    return prof([(1, -6), (45, -6), (57, -2), (68, -14), (78, 28), (90, 18),
                 (106, 12), (130, 16), (154, 18), (299, 18), (315, 9),
                 (330, 5), (348, 4), (360, 4)], f)

def torso_yaw(f):
    return 2.5 * math.sin(2 * math.pi * (f - 106) / 48.4) if 106 < f < 305 else 0.0

def head_look(f):
    yaw = prof([(1, 12), (20, -18), (38, 10), (50, -4), (57, 0),
                (106, 0), (130, 22), (170, 26), (195, 4), (203, -14),
                (212, 8), (222, 16), (240, 0), (265, -16), (292, -6),
                (305, 0), (360, 0)], f)
    pitch = prof([(1, -4), (45, -4), (57, -12), (68, 4), (106, 2),
                  (250, -4), (299, -6), (315, -8), (330, -18), (348, -38),
                  (360, -38)], f)
    return yaw, pitch

def hand_target(side, f, shoulder, R_ch):
    sx = -1.0 if side == 'L' else 1.0
    if f <= 84:      # assis + début du lever : mains sur les genoux / poussée
        t = shoulder + R_ch @ Vector((sx * 0.12, 0.32, -0.42))
    elif f <= 100:   # élan d'équilibre, mains basses devant
        t = shoulder + R_ch @ Vector((sx * 0.18, 0.25, -0.45))
    else:            # marche : pendule opposé à la jambe
        phase = 2 * math.pi * (f - 106) / 48.4 + (math.pi if side == 'L' else 0.0)
        t = shoulder + R_ch @ Vector((sx * 0.10, 0.04 + 0.10 * math.sin(phase),
                                      -0.55 + (0.05 if f < 305 else 0.0)))
    if f >= 330:     # ouverture finale : recevoir la vue
        o = smooth((f - 330) / 18.0)
        t = t + R_ch @ Vector((sx * 0.10 * o, 0.04 * o, 0.03 * o))
    d = t - shoulder
    if d.length > 0.60:
        t = shoulder + d.normalized() * 0.60
    return t

# ---------------------------------------------------------------- bake
rig = bpy.data.objects["K3_EDGE_RIG"]
pb = {n: rig.pose.bones[n] for n in
      ("Pelvis", "Spine", "Chest", "Neck", "Head",
       "UpperArm.L", "Forearm.L", "UpperArm.R", "Forearm.R",
       "Thigh.L", "Shin.L", "Thigh.R", "Shin.R")}
for n in pb:
    pb[n].rotation_mode = 'QUATERNION'

ORDER = ["Pelvis", "Spine", "Chest", "Neck", "Head",
         "Thigh.L", "Shin.L", "Thigh.R", "Shin.R",
         "UpperArm.L", "Forearm.L", "UpperArm.R", "Forearm.R"]
PARENT = {"Spine": "Pelvis", "Chest": "Spine", "Neck": "Chest", "Head": "Neck",
          "Thigh.L": "Pelvis", "Thigh.R": "Pelvis",
          "Shin.L": "Thigh.L", "Shin.R": "Thigh.R",
          "UpperArm.L": "Chest", "UpperArm.R": "Chest",
          "Forearm.L": "UpperArm.L", "Forearm.R": "UpperArm.R"}

sc = bpy.context.scene
for f in range(1, 361):
    p_pel = pelvis_pos(f)
    pitch = torso_pitch(f)
    yaw = torso_yaw(f)
    h_yaw, h_pitch = head_look(f)
    extra_c = prof([(330, 0.0), (348, -5.0), (360, -5.0)], f)

    th_p, th_s, th_c = pitch / 3.0, pitch / 3.0, pitch / 3.0 + extra_c
    R_pel = frame_mat(yaw, th_p)
    d0 = R_pel @ Vector((0, 0, 1))
    M = {"Pelvis": bone_mat(p_pel, p_pel + d0 * 0.19, R_pel @ Vector((0, 1, 0)))}
    p1 = p_pel + d0 * 0.19
    R_s = frame_mat(yaw, th_p + th_s)
    d1 = R_s @ Vector((0, 0, 1))
    M["Spine"] = bone_mat(p1, p1 + d1 * 0.23, R_s @ Vector((0, 1, 0)))
    p2 = p1 + d1 * 0.23
    R_c = frame_mat(yaw, th_p + th_s + th_c)
    d2 = R_c @ Vector((0, 0, 1))
    M["Chest"] = bone_mat(p2, p2 + d2 * 0.17, R_c @ Vector((0, 1, 0)))
    p3 = p2 + d2 * 0.17
    R_n = frame_mat(yaw + 0.4 * h_yaw, th_p + th_s + th_c + 0.3 * h_pitch)
    d3 = R_n @ Vector((0, 0, 1))
    M["Neck"] = bone_mat(p3, p3 + d3 * 0.155, R_n @ Vector((0, 1, 0)))
    p4 = p3 + d3 * 0.155
    R_h = frame_mat(yaw + h_yaw, th_p + th_s + th_c + h_pitch)
    d4 = R_h @ Vector((0, 0, 1))
    M["Head"] = bone_mat(p4, p4 + d4 * 0.405, R_h @ Vector((0, 1, 0)))

    fwd = R_pel @ Vector((0, 1, 0))
    fL, fR = foot_state(f)
    # direction de pliage des genoux : haut/avant assis (genoux remontés) -> avant en marche
    up_b = Vector((0, 0.45, 0.9)).normalized()
    w_b = prof([(68, 0.0), (95, 1.0)], f)
    bend_leg = (fwd * w_b + up_b * (1.0 - w_b)).normalized()
    for side, foot, hx in (("L", fL, -0.19), ("R", fR, 0.19)):
        hip = p_pel + R_pel @ Vector((hx, 0, -0.14))
        knee = solve2(hip, foot, L_THIGH, L_SHIN, bend_leg)
        M[f"Thigh.{side}"] = bone_mat(hip, knee, bend_leg)
        M[f"Shin.{side}"] = bone_mat(knee, foot, bend_leg)

    for side, sx in (("L", -1.0), ("R", 1.0)):
        sho = p2 + R_c @ Vector((sx * 0.449, 0, 0.19))
        hand = hand_target(side, f, sho, R_c)
        bend = R_c @ Vector((sx * 0.85, 0.2, 0.1))
        elb = solve2(sho, hand, L_UPA, L_FORE, bend)
        M[f"UpperArm.{side}"] = bone_mat(sho, elb, bend)
        M[f"Forearm.{side}"] = bone_mat(elb, hand, bend)

    for name in ORDER:
        p = pb[name]
        parent = PARENT.get(name)
        if parent:
            basis = (p.bone.matrix_local.inverted() @ p.parent.bone.matrix_local
                     @ M[parent].inverted() @ M[name])
        else:
            basis = p.bone.matrix_local.inverted() @ M[name]
        loc, rot, _ = basis.decompose()
        p.location = loc
        p.rotation_quaternion = rot
        p.keyframe_insert("location", frame=f)
        p.keyframe_insert("rotation_quaternion", frame=f)

bpy.ops.wm.save_mainfile()
print("BAKE_OK frames 1-360")
