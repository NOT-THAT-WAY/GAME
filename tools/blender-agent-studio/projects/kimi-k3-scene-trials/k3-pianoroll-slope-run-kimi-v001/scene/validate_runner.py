"""ETAPE I — validation physique frame par frame (240 frames).

Mesures dans le repere de surface (U, N, C) rattache a USTUDIO_BOX_FLOAT_ROOT :
- hauteur du root et du bassin suivant SURFACE_NORMAL
- pied porteur par frame, drift tangent du pied plante
- penetration sous le plan, clearance des orteils en swing
- inclinaison du torse vs verticale monde
- distance camera/personnage, clearance camera/decor
Sortie : diagnostics/physical-validation.json. Aucune sauvegarde.
"""
import bpy
import json
import math
from mathutils import Vector

TRIAL = "${BLENDER_AGENT_STUDIO_ROOT}/projects/kimi-k3-scene-trials/k3-pianoroll-slope-run-kimi-v001"
assert bpy.data.filepath == TRIAL + "/scene/trial.blend"

sc = bpy.context.scene
root = bpy.data.objects["USTUDIO_BOX_FLOAT_ROOT"]
arm = bpy.data.objects["K3_RUNNER_RIG"]
cam = bpy.data.objects["K3_CAM_MAIN"]

surf = json.load(open(TRIAL + "/diagnostics/surface-analysis.json"))
N = Vector(surf["SURFACE_NORMAL"])
U = Vector(surf["UPHILL_TANGENT"])
C = Vector(surf["CROSS_SLOPE_TANGENT"])
LOW = Vector(surf["low_edge_local"])
SLOPE = surf["slope_degrees_from_world_horizontal"]
PLANE_P = LOW  # un point du plan (local root)

SHELL = [o for o in bpy.data.objects
         if o.name.startswith("USTUDIO_") and o.type == "MESH"
         and o.name != "USTUDIO_PIANO_ROLL_FLOOR" and not o.hide_render]

def to_surface_coords(p_local):
    d = p_local - PLANE_P
    return d.dot(U), d.dot(N), d.dot(C)

frames = []
# fenetres d'appui contractuelles (grille d'animation) : (debut, fin, pied)
BEAT = 12.1034
STRIKES = [57.41 + i * BEAT for i in range(11)]
WINDOWS = [(1, 44, "L"), (1, STRIKES[0], "R")]
for i, bf in enumerate(STRIKES):
    side = "L" if i % 2 == 0 else "R"
    end = STRIKES[i + 1] if i + 1 < len(STRIKES) else 240
    WINDOWS.append((bf, end, side))
WINDOWS.append((201.0, 240, "R"))
stance_pts = {side: {} for side in ("L", "R")}  # side -> {frame: (s, c)}

max_pen = 0.0
min_swing_clear = 1e9
cam_dists = []
cam_clear_min = 1e9
torso_pitches = []

ANKLE_LOCAL = {"L": Vector((-0.029, 0, 0.022)), "R": Vector((0.029, 0, 0.022))}
TOE_OFF = Vector((0, -0.045, -0.016))  # orteil relatif a la cheville (repos, espace armature)

for f in range(1, 241):
    sc.frame_set(f)
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    inv = root.matrix_world.inverted()

    # root (pied de l'armature) dans le repere de surface
    root_local = inv @ arm.matrix_world.translation
    s_r, h_r, c_r = to_surface_coords(root_local)
    # root pose-bone offset ajoute le deplacement de course : utiliser la hanche
    hips_w = arm.matrix_world @ arm.pose.bones["hips"].head
    s_h, h_h, c_h = to_surface_coords(inv @ hips_w)

    entry = {"frame": f, "root_s": round(s_r, 4), "root_h": round(h_r, 4),
             "pelvis_h_normal": round(h_h, 4)}

    planted_now = []
    for side in ("L", "R"):
        fb = arm.pose.bones[f"foot.{side}"]
        ankle_w = arm.matrix_world @ fb.head
        toe_w = arm.matrix_world @ (fb.matrix @ TOE_OFF)
        a_local = inv @ ankle_w
        t_local = inv @ toe_w
        s_a, h_a, c_a = to_surface_coords(a_local)
        s_t, h_t, c_t = to_surface_coords(t_local)
        for (w0, w1, ws) in WINDOWS:
            if ws == side and w0 <= f <= w1:
                stance_pts[side][f] = (s_a, c_a)
                planted_now.append(side)
        pen = -(h_t)  # penetration = orteil sous le plan
        max_pen = max(max_pen, pen)
        if h_a > 0.030:  # pied en swing
            min_swing_clear = min(min_swing_clear, h_t)
        entry[f"ankle_{side}_h"] = round(h_a, 4)
        entry[f"toe_{side}_h"] = round(h_t, 4)
    entry["support"] = planted_now or ["L" if entry["ankle_L_h"] < entry["ankle_R_h"] else "R"]

    # torse vs verticale monde
    chest_dir = (arm.matrix_world.to_3x3() @ arm.pose.bones["chest"].vector).normalized()
    pitch = math.degrees(math.acos(max(-1.0, min(1.0, chest_dir.z))))
    # signe : projection sur l'axe montant monde (U ~ +Y/+Z)
    uphill_world = Vector((0, 0.6904, 0.7235))
    sign = 1.0 if chest_dir.dot(uphill_world) > 0 else -1.0
    torso_pitches.append(sign * pitch)
    entry["torso_vs_world_vertical_deg"] = round(sign * pitch, 2)

    # camera
    cam_w = cam.matrix_world.translation
    char_w = hips_w
    dist = (cam_w - char_w).length
    cam_dists.append(dist)
    entry["cam_dist"] = round(dist, 4)
    # clearance camera/decor : raycasts dans 6 directions
    clear = 1e9
    for dvec in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
        hit, loc, *_ = sc.ray_cast(deps, cam_w, Vector(dvec), distance=1.0)
        if hit:
            clear = min(clear, (loc - cam_w).length)
    if clear < 1e9:
        cam_clear_min = min(cam_clear_min, clear)
    entry["cam_clearance"] = round(clear if clear < 1e9 else 1.0, 4)
    frames.append(entry)

dists = [e["cam_dist"] for e in frames]
# drift : ecart max a la position moyenne de chaque fenetre d'appui
max_drift = {"L": 0.0, "R": 0.0}
for side in ("L", "R"):
    for (w0, w1, ws) in WINDOWS:
        if ws != side:
            continue
        pts = [stance_pts[side][f] for f in sorted(stance_pts[side]) if w0 <= f <= w1]
        if len(pts) < 2:
            continue
        ms, mc = pts[0]  # reference : premier contact de la fenetre
        for p in pts:
            d = math.sqrt((p[0] - ms) ** 2 + (p[1] - mc) ** 2)
            max_drift[side] = max(max_drift[side], d)

report = {
    "slope_degrees_measured": SLOPE,
    "frames_evaluated": len(frames),
    "root_height_error_max_m": round(max(abs(e["root_h"]) for e in frames), 5),
    "pelvis_h_range_m": [round(min(e["pelvis_h_normal"] for e in frames), 4),
                         round(max(e["pelvis_h_normal"] for e in frames), 4)],
    "planted_drift_max_m": {"L": round(max_drift["L"], 5), "R": round(max_drift["R"], 5)},
    "penetration_max_m": round(max_pen, 5),
    "swing_toe_clearance_min_m": round(min_swing_clear, 5),
    "torso_pitch_run_deg": {
        "min": round(min(torso_pitches[56:192]), 2),
        "max": round(max(torso_pitches[56:192]), 2)},
    "cam_distance": {"min": round(min(dists), 4), "max": round(max(dists), 4),
                     "variation": round(max(dists) - min(dists), 4)},
    "cam_clearance_min_m": round(cam_clear_min, 4),
    "thresholds": {
        "planted_drift_max_m": 0.005,
        "penetration_max_m": 0.002,
        "swing_toe_clearance_min_m": 0.01,
        "root_height_error_max_m": 0.003,
        "cam_distance_variation_m": 0.01,
        "cam_clearance_min_m": 0.08,
    },
    "per_frame": frames,
}
ok = {
    "planted_drift": max(max_drift.values()) <= 0.005,
    "penetration": max_pen <= 0.002,
    "swing_clearance": min_swing_clear >= 0.01,
    "root_height": report["root_height_error_max_m"] <= 0.003,
    "cam_distance": (max(dists) - min(dists)) <= 0.01,
    "cam_clearance": cam_clear_min >= 0.08,
    "torso_run_in_15_25": 10 <= report["torso_pitch_run_deg"]["min"] and report["torso_pitch_run_deg"]["max"] <= 30,
}
report["checks_pass"] = ok
report["all_pass"] = all(ok.values())
with open(TRIAL + "/diagnostics/physical-validation.json", "w") as fp:
    json.dump(report, fp, indent=1, ensure_ascii=False)
print("VALIDATION", json.dumps(ok))
print("drift", round(max_drift['L'], 5), round(max_drift['R'], 5),
      "| pen", round(max_pen, 5), "| swing", round(min_swing_clear, 5),
      "| root_h_err", report["root_height_error_max_m"],
      "| cam_var", report["cam_distance"]["variation"],
      "| cam_clear", round(cam_clear_min, 4),
      "| torso_run", report["torso_pitch_run_deg"])
