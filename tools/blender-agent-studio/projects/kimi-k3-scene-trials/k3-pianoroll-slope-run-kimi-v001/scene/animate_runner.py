"""ETAPE E+F+G — animation complete de la course en pente (240 frames).

Strategie : en espace ARMATURE, le Piano Roll est le plan z=0 et la montee = -Y
(l'armature est orientee dans le repere de surface mesure). Toute la logique de
course est donc une course sur plat en local ; l'adaptation monde vient de :
- la rotation R de l'armature (semelles coplanaires par construction),
- la contre-rotation de la chaine spine (torse gouverne par la gravite monde,
  ~20 degre depuis la verticale monde au lieu de 46,34).

Jambes : resolution 2-bone analytique par frame (pas d'IK constraint) :
- pied plante strictement fixe pendant la phase d'appui (drift = 0 par construction),
- hanche lue sur la pose evaluee, cheville compensee (pied = rotation rest constante).

Grille audio : downbeats a 57,41 + i*12,1034 (148,9 BPM, cf audio-grid-estimate).
"""
import bpy
import json
from math import sin, cos, pi, acos, asin, sqrt
from mathutils import Vector, Matrix, Quaternion

TRIAL = "${BLENDER_AGENT_STUDIO_ROOT}/projects/kimi-k3-scene-trials/k3-pianoroll-slope-run-kimi-v001"
assert bpy.data.filepath == TRIAL + "/scene/trial.blend", bpy.data.filepath

sc = bpy.context.scene
root = bpy.data.objects["USTUDIO_BOX_FLOAT_ROOT"]
arm = bpy.data.objects["K3_RUNNER_RIG"]

surf = json.load(open(TRIAL + "/diagnostics/surface-analysis.json"))
N = Vector(surf["SURFACE_NORMAL"])
U = Vector(surf["UPHILL_TANGENT"])
C = Vector(surf["CROSS_SLOPE_TANGENT"])
LOW = Vector(surf["low_edge_local"])
S0 = 0.2
P0 = LOW + U * S0

# ---------------------------------------------------------------- grille
BEAT = 12.1034
STRIKES = [57.41 + i * BEAT for i in range(11)]   # 57,41 -> 190,45
L_STEP = 0.15
PLANT = [0.26 + i * L_STEP for i in range(11)]     # points de pose le long de U
S_END = 1.8
F_END = 240

def s_body(f):
    """Position du corps le long de U (marge basse S0 = 0.2)."""
    if f <= 17:
        return 0.2
    if f <= 48:  # transfert de poids vers l'amont
        t = (f - 17) / 31.0
        return 0.2 + 0.012 * (t * t * (3 - 2 * t))
    if f <= STRIKES[0]:
        return 0.212
    if f <= STRIKES[-1]:
        # progression lineaire par appui
        i = 0
        while i < len(STRIKES) - 1 and f > STRIKES[i + 1]:
            i += 1
        t = (f - STRIKES[i]) / (STRIKES[i + 1] - STRIKES[i])
        return (0.212 + i * L_STEP) + t * L_STEP
    if f <= 208:  # deceleration
        t = (f - STRIKES[-1]) / (208 - STRIKES[-1])
        t = t * t * (3 - 2 * t)
        return (0.212 + 10 * L_STEP) + t * (S_END - (0.212 + 10 * L_STEP))
    return S_END

# ---------------------------------------------------------------- phases pieds
def foot_phase(f):
    """Retourne {side: (mode, s_from, s_to, t)} : plant ou swing."""
    out = {}
    # etat initial : L a 0.22, R a 0.14
    seq = []  # (strike_frame, side, plant_s)
    for i, bf in enumerate(STRIKES):
        pass
    # reconstruit proprement : au strike i, le pied side_i se pose a PLANT[i]
    for i, bf in enumerate(STRIKES):
        side = "L" if i % 2 == 0 else "R"
        seq.append((bf, side, PLANT[i]))
    # arrivee finale : R rejoint L apres le dernier strike
    seq.append((201.0, "R", 1.72))

    events = {}
    for side in ("L", "R"):
        plants = [(fr, s) for fr, sd, s in seq if sd == side]
        events[side] = plants

    for side in ("L", "R"):
        plants = events[side]
        init_s = 0.22 if side == "L" else 0.14
        if f < 45.0 and side == "L":
            out[side] = ("plant", init_s, init_s, 0.0)
            continue
        if f < STRIKES[0] and side == "R":
            out[side] = ("plant", init_s, init_s, 0.0)
            continue
        # trouve l'appui courant : dernier plant <= f
        prev = None
        nxt = None
        for j, (fr, s) in enumerate(plants):
            if fr <= f:
                prev = (fr, s, j)
            elif nxt is None:
                nxt = (fr, s, j)
        if side == "L" and prev is None:
            # swing initial 45 -> strike0
            t = (f - 45.0) / (STRIKES[0] - 45.0)
            out[side] = ("swing", init_s, plants[0][1], t)
            continue
        if prev is None:
            out[side] = ("plant", init_s, init_s, 0.0)
            continue
        fr_p, s_p, j = prev
        # l'autre pied se pose au strike suivant -> fin d'appui
        lift_f = None
        for bf in STRIKES + [201.0]:
            if bf > fr_p + 0.01:
                lift_f = bf
                break
        if nxt is None:
            out[side] = ("plant", s_p, s_p, 0.0)
            continue
        fr_n, s_n, _ = nxt
        if lift_f is None or f <= lift_f:
            out[side] = ("plant", s_p, s_p, 0.0)
        else:
            t = (f - lift_f) / (fr_n - lift_f)
            out[side] = ("swing", s_p, s_n, min(max(t, 0.0), 1.0))
    return out

ANKLE_X = {"L": -0.029, "R": 0.029}
def ankle_arm(f, side):
    mode, s_from, s_to, t = foot_phase(f)[side]
    if mode == "plant":
        s = s_from
        lift = 0.0
    else:
        tt = t * t * (3 - 2 * t)
        s = s_from + (s_to - s_from) * tt
        lift = 0.030 * sin(pi * min(max(t, 0.0), 1.0))
    return Vector((ANKLE_X[side], -(s - S0), 0.022 + lift)), mode

def planted(f, side):
    return foot_phase(f)[side][0] == "plant"

# ---------------------------------------------------------------- poses
def smooth(a, b, f, f0, f1):
    if f <= f0:
        return a
    if f >= f1:
        return b
    t = (f - f0) / (f1 - f0)
    t = t * t * (3 - 2 * t)
    return a + (b - a) * t

# Contre-rotation euler X (degres, + = vers l'amont) : le corps au repos suit la
# normale (-46,34 deg depuis la verticale monde, c.-a-d. penche vers l'aval).
# Pour un torse a +15..25 deg vers l'AMONT depuis la verticale monde il faut
# donc une contre-rotation totale de ~61..71 deg, repartie hanches/colonne/torse.
# (hips, spine, chest, head)
WP_STILL = (10, 20, 31, 5)
WP_ANTIC = (12, 24, 36, 12)
WP_RUN   = (12, 23, 33, 12)
WP_DECEL = (10, 22, 34, 8)
WP_RECOV = (12, 30, 39, -16)
WP_FINAL = (12, 26, 40, 10)
WP = [(1, WP_STILL), (16, WP_STILL), (40, WP_ANTIC), (49, WP_ANTIC),
      (57, WP_RUN), (170, WP_RUN), (192, WP_RUN), (208, WP_DECEL),
      (224, WP_RECOV), (232, WP_RECOV), (240, WP_FINAL)]
WP_CROUCH = [(1, -0.012), (16, -0.012), (40, -0.045), (49, -0.045), (192, -0.045),
             (208, -0.012), (224, -0.012), (240, -0.012)]

def interp_wp(table, f):
    if f <= table[0][0]:
        return table[0][1]
    if f >= table[-1][0]:
        return table[-1][1]
    for i in range(len(table) - 1):
        f0, v0 = table[i]
        f1, v1 = table[i + 1]
        if f0 <= f <= f1:
            t = (f - f0) / (f1 - f0)
            t = t * t * (3 - 2 * t)
            if isinstance(v0, tuple):
                return tuple(a + (b - a) * t for a, b in zip(v0, v1))
            return v0 + (v1 - v0) * t
    return table[-1][1]

def pose_params(f):
    hips_p, spine, chest, head = interp_wp(WP, f)
    crouch = interp_wp(WP_CROUCH, f)
    arm_L = arm_R = 0.0
    elbow = smooth(0.0, -45.0, f, 33, 57)
    if f <= 16:  # respiration
        chest += 0.8 * sin(2 * pi * f / 45.0)
    if 49 <= f <= 200:
        w = 2 * pi * (f - STRIKES[0]) / (2 * BEAT)
        arm_L = -32 * sin(w)
        arm_R = 32 * sin(w)
        chest += 1.5 * sin(2 * w)
    if f > 200:  # relachement des bras
        arm_L = smooth(arm_L, 0.0, f, 200, 212)
        arm_R = smooth(arm_R, 0.0, f, 200, 212)
        elbow = smooth(elbow, -10.0, f, 200, 216)
    if 209 <= f <= 232:  # mains vers les genoux
        k = smooth(0.0, 1.0, f, 209, 224)
        arm_L = arm_L * (1 - k) + (-52) * k
        arm_R = arm_R * (1 - k) + (-52) * k
        elbow = elbow * (1 - k) + (-28) * k
    if f > 232:
        k = smooth(0.0, 1.0, f, 233, 240)
        arm_L = -52 * (1 - k) + (-6) * k
        arm_R = -52 * (1 - k) + (-6) * k
        elbow = -28 * (1 - k) + (-8) * k
    return hips_p, spine, chest, head, crouch, arm_L, arm_R, elbow

# ---------------------------------------------------------------- jambes analytiques
L1 = 0.09   # cuisse
L2 = 0.083  # tibia
FWD = Vector((0, -1, 0))
pb = {b.name: b for b in arm.pose.bones}
REST_FOOT_ROT = {s: arm.data.bones[f"foot.{s}"].matrix_local.to_3x3().to_4x4()
                 for s in ("L", "R")}

def solve_leg(H, A):
    v = A - H
    d = min(max(v.length, 0.03), (L1 + L2) - 0.002)
    v_hat = v.normalized()
    cos_a1 = min(max((L1 * L1 + d * d - L2 * L2) / (2 * L1 * d), -1.0), 1.0)
    a1 = acos(cos_a1)
    e = v_hat.cross(FWD)
    if e.length < 1e-6:
        e = Vector((-1, 0, 0))
    e.normalize()
    thigh_dir = v_hat.copy()
    thigh_dir.rotate(Quaternion(e, a1))
    K = H + thigh_dir * L1
    shin_dir = (A - K).normalized()
    return K, thigh_dir, shin_dir

def bone_matrix(head, direction):
    y = direction.normalized()
    xref = Vector((1, 0, 0))
    z = xref.cross(y)
    if z.length < 1e-6:
        xref = Vector((0, 0, 1))
        z = xref.cross(y)
    z.normalize()
    x = y.cross(z)
    M = Matrix(((x.x, y.x, z.x, head.x),
                (x.y, y.y, z.y, head.y),
                (x.z, y.z, z.z, head.z),
                (0.0, 0.0, 0.0, 1.0)))
    return M

def key_euler(bone, f):
    pb[bone].keyframe_insert("rotation_euler", frame=f)

def key_loc(bone, f):
    pb[bone].keyframe_insert("location", frame=f)

# ---------------------------------------------------------------- cameras
cam_main = bpy.data.objects["K3_CAM_MAIN"]
cam_profile = bpy.data.objects["K3_CAM_DIAG_PROFILE"]
cam_top = bpy.data.objects["K3_CAM_DIAG_TOP"]
cam_normal = bpy.data.objects["K3_CAM_DIAG_NORMAL"]
cam_target = bpy.data.objects["K3_CAM_MAIN_TARGET"]
cam_focus = bpy.data.objects["K3_CAM_MAIN_FOCUS"]
feet_target = bpy.data.objects.new("K3_CAM_DIAG_FEET_TARGET", None)
bpy.data.collections["K3_PIANOROLL_SLOPE_RUN_KIMI_V001_WORK"].objects.link(feet_target)
feet_target.parent = root
for c in (cam_profile, cam_top, cam_normal):
    c.constraints["Track To"].target = feet_target

def cam_u_offset(f):
    """Position camera : offset constant (distance personnage constante a 0)."""
    return 0.0

def target_u_offset(f):
    """K2/K4 Drumboiii portes par le TARGET (la distance camera reste constante) :
    anticipation 17-49 legerement en aval, overshoot 193-210 en amont, puis stop."""
    off = smooth(0.0, -0.030, f, 17, 30) - smooth(0.0, -0.030, f, 33, 49)
    off += smooth(0.0, 0.025, f, 193, 200) - smooth(0.0, 0.025, f, 200, 212)
    return off

def set_cam(f):
    sb = s_body(f)
    base = P0 + U * (sb - S0)
    # principale : trois-quarts cote -X monde (=+C, le cote +X est occupe par le
    # channel rack), elevee en monde : la declinaison ~17 deg ramene la pente
    # apparente de 46 a ~29 deg dans le cadre (horizon monde conserve, pas de roll)
    crouch_f = interp_wp(WP_CROUCH, f)
    pos = (base + C * 0.85 + U * (-0.30 + cam_u_offset(f)) + N * (0.42 + crouch_f)
           + Vector((0.0, 0.0, 0.22)))
    cam_main.location = pos
    cam_main.keyframe_insert("location", frame=f)
    # target avec retard de 2 frames, hauteur poitrine, geste K2/K4 ici
    sb_t = s_body(max(1, f - 2))
    cam_target.location = P0 + U * (sb_t - S0 + target_u_offset(f)) + N * 0.20
    cam_target.keyframe_insert("location", frame=f)
    cam_focus.location = P0 + U * (sb - S0) + N * 0.20
    cam_focus.keyframe_insert("location", frame=f)
    feet_target.location = P0 + U * (sb - S0) + N * 0.02
    feet_target.keyframe_insert("location", frame=f)
    # diagnostiques
    cam_profile.location = base - C * 1.00 + N * 0.10
    cam_profile.keyframe_insert("location", frame=f)
    cam_top.location = base - C * 0.35 + N * 0.75 - U * 0.05
    cam_top.keyframe_insert("location", frame=f)
    cam_normal.location = base + N * 0.80
    cam_normal.keyframe_insert("location", frame=f)

# ---------------------------------------------------------------- grip pulse
GRIP = {"L": bpy.data.materials["M_K3_GRIP_L"], "R": bpy.data.materials["M_K3_GRIP_R"]}
def key_grip(f):
    for side, mat in GRIP.items():
        bsdf = mat.node_tree.nodes["Principled BSDF"]
        idx = bsdf.inputs.find("Emission Strength")
        bsdf.inputs[idx].default_value = 6.0 if planted(f, side) else 0.15
        mat.node_tree.keyframe_insert(
            f'nodes["Principled BSDF"].inputs[{idx}].default_value', frame=f)

# ---------------------------------------------------------------- audio (API v5)
MASTER = "${BLENDER_AGENT_STUDIO_ROOT}/projects/fl-studio-box-semantic-template/media/current/master.mp4"
if not sc.sequence_editor:
    sc.sequence_editor_create()
try:
    sc.sequence_editor.strips.new_sound(
        name="K3_MASTER_AUDIO", filepath=MASTER, channel=1, frame_start=1)
    print("AUDIO_MOUNTED")
except Exception as e:
    print("AUDIO_MOUNT_FAILED", repr(e))

# ---------------------------------------------------------------- boucle principale
cam_main.data.lens = 52.0
from math import radians
for f in range(1, F_END + 1):
    sc.frame_set(f)
    hips_p, spine, chest, head, crouch, aL, aR, elbow = pose_params(f)
    # root : avance le long de -Y local, reste exactement sur le plan
    pb["root"].location = (0.0, 0.0, s_body(f) - S0)
    key_loc("root", f)
    pb["hips"].location = (0.0, crouch, 0.0)
    pb["hips"].rotation_euler = (radians(hips_p), 0, 0)
    key_loc("hips", f)
    key_euler("hips", f)
    pb["spine"].rotation_euler = (radians(spine), 0, 0)
    pb["chest"].rotation_euler = (radians(chest), 0, 0)
    pb["head"].rotation_euler = (radians(head), 0, 0)
    pb["upper_arm.L"].rotation_euler = (radians(aL), 0, radians(6))
    pb["upper_arm.R"].rotation_euler = (radians(aR), 0, radians(-6))
    pb["forearm.L"].rotation_euler = (radians(elbow), 0, 0)
    pb["forearm.R"].rotation_euler = (radians(elbow), 0, 0)
    for b in ("root",):
        pb[b].keyframe_insert("rotation_euler", frame=f)
    for b in ("spine", "chest", "head", "upper_arm.L", "upper_arm.R",
              "forearm.L", "forearm.R"):
        key_euler(b, f)
    bpy.context.view_layer.update()
    # jambes
    for side in ("L", "R"):
        A, mode = ankle_arm(f, side)
        H = arm.matrix_world.inverted() @ (arm.matrix_world @ pb[f"thigh.{side}"].head)
        H = pb[f"thigh.{side}"].head.copy()  # espace armature
        K, thigh_dir, shin_dir = solve_leg(H, A)
        pb[f"thigh.{side}"].matrix = bone_matrix(H, thigh_dir)
        bpy.context.view_layer.update()
        pb[f"shin.{side}"].matrix = bone_matrix(K, shin_dir)
        bpy.context.view_layer.update()
        M_foot = Matrix.Translation(A) @ REST_FOOT_ROT[side]
        pb[f"foot.{side}"].matrix = M_foot
        bpy.context.view_layer.update()
        key_euler(f"thigh.{side}", f)
        key_euler(f"shin.{side}", f)
        key_euler(f"foot.{side}", f)
    set_cam(f)
    key_grip(f)

# interpolation lineaire pour les canaux de transport (aucun glissement cache)
def set_linear(id_root, data_path_prefix=None):
    ad = id_root.animation_data
    if not ad or not ad.action:
        return
    for layer in ad.action.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                for fc in cb.fcurves:
                    for kp in fc.keyframe_points:
                        kp.interpolation = "LINEAR"

for ob in [arm, cam_main, cam_target, cam_focus, feet_target,
           cam_profile, cam_top, cam_normal]:
    set_linear(ob)

sc.frame_set(1)
bpy.ops.wm.save_mainfile()
print("ANIM_DONE frames=240 strikes=", [round(s, 1) for s in STRIKES])
