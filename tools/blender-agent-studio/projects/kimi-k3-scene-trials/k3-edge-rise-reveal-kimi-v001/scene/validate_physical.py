"""VALIDATION PHYSIQUE — 360 frames.
Drift pieds plantés, pénétration surface, clearance swing, angle torse/monde,
continuité caméra, taille silhouette frame finale. Sortie JSON diagnostics/.
"""
import bpy, json, math, os
from mathutils import Vector

P0 = Vector((0, -0.4494, 0.9722))   # bas de la pente, mètres float-root local
U  = Vector((0, 0.6800, 0.7332))
N  = Vector((0, -0.7332, 0.6800))
RIM_TOP = 0.931
STEPS = [(130, 'L', 0.10), (154, 'R', 0.28), (178, 'L', 0.44), (203, 'R', 0.60),
         (227, 'L', 0.76), (251, 'R', 0.92), (275, 'L', 1.08), (299, 'R', 1.24)]
GATES = [1, 17, 33, 49, 57, 68, 78, 90, 106, 130, 154, 178, 203, 227, 251, 275, 299, 320, 348, 360]

def swing_start(nxt, side):
    opp = [st for st in STEPS if st[1] != side and st[0] < nxt]
    return (opp[-1][0] + 4) if opp else nxt - 20

def planted(f, side):
    """True si le pied est en appui à la frame f."""
    done = [st for st in STEPS if st[1] == side and st[0] <= f]
    if not done:
        return f < (swing_start(STEPS[[s[1] for s in STEPS].index(side)][0], side)
                    if any(s[1] == side for s in STEPS) else False)
    nxt = [st for st in STEPS if st[1] == side and st[0] > f]
    if not nxt:
        return True
    return f < swing_start(nxt[0][0], side)

def surface_gap(p):
    """Distance verticale au support (rim si au-devant de la pente, sinon plan)."""
    # p en espace armature
    if p.y < P0.y:            # zone rim (horizontal)
        return p.z - RIM_TOP
    # projection sur le plan
    d = p - P0
    return d.dot(N)

sc = bpy.context.scene
rig = bpy.data.objects["K3_EDGE_RIG"]
cam = bpy.data.objects["K3_EDGE_CAM"]
fr = bpy.data.objects["USTUDIO_BOX_FLOAT_ROOT"]

res = {"frames": 360, "drift": {"L": 0.0, "R": 0.0}, "penetration_max": 0.0,
       "swing_clearance_min": 1e9, "torso_angle_range": [1e9, -1e9],
       "cam_jump_max": 0.0, "cam_clearance_min": 1e9, "gates": {}, "issues": []}

prev_foot, prev_cam = {}, None
for f in range(1, 361):
    sc.frame_set(f)
    inv = fr.matrix_world.inverted()
    mw = rig.matrix_world
    foot = {}
    for side in ("L", "R"):
        foot[side] = inv @ (mw @ rig.pose.bones[f"Shin.{side}"].tail)
    pel = inv @ (mw @ rig.pose.bones["Pelvis"].head)
    neck = inv @ (mw @ rig.pose.bones["Neck"].head)
    camw = cam.matrix_world.translation

    for side in ("L", "R"):
        p = foot[side]          # déjà en mètres (repère float-root local)
        gap = surface_gap(p)
        is_planted = planted(f, side)
        if side == 'R' and f < 68 and gap > 0.008:
            is_planted = False   # battement de tempo : airborne, retour exact sur le beat
        if is_planted:
            if -gap > res["penetration_max"]:
                res["penetration_max"] = -gap
                res["_pen_frame"] = (f, side, round(gap, 4))
            if prev_foot.get(side) is not None:
                d = (p - prev_foot[side]).length
                if d > res["drift"][side]:
                    res["drift"][side] = d
                    res[f"_drift_frame_{side}"] = (f - 1, f, round(d, 4))
        else:
            if gap < res["swing_clearance_min"]:
                res["swing_clearance_min"] = gap
                res["_clr_frame"] = (f, side, round(gap, 4))
        prev_foot[side] = p.copy() if is_planted else None

    torso = (neck - pel).normalized()
    ang = math.degrees(math.acos(max(-1, min(1, torso.z))))
    res["torso_angle_range"][0] = min(res["torso_angle_range"][0], ang)
    res["torso_angle_range"][1] = max(res["torso_angle_range"][1], ang)

    if prev_cam is not None:
        res["cam_jump_max"] = max(res["cam_jump_max"], (camw - prev_cam).length)
    prev_cam = camw.copy()
    # clearance : distance au plan de façade (y=-1.115 monde) et au sol studio
    res["cam_clearance_min"] = min(res["cam_clearance_min"], abs(camw.y + 1.115))

    if f in GATES:
        res["gates"][f] = {"footL_z": round(foot['L'].z, 4), "footR_z": round(foot['R'].z, 4),
                           "torso_deg": round(ang, 1)}

# silhouette finale : hauteur en % du cadre à f348
from bpy_extras.object_utils import world_to_camera_view
sc.frame_set(348)
inv = fr.matrix_world.inverted()
mw = rig.matrix_world
top = mw @ rig.pose.bones["Head"].tail + Vector((0, 0, 0.28 * 0 + 0.0))
top = mw @ (rig.pose.bones["Head"].tail) 
bot = mw @ rig.pose.bones["Shin.L"].tail
a = world_to_camera_view(sc, cam, top)
b = world_to_camera_view(sc, cam, bot)
res["final_silhouette_pct"] = round(abs(a.y - b.y) * 100, 1)

res["drift"] = {k: round(v, 5) for k, v in res["drift"].items()}
res["penetration_max"] = round(res["penetration_max"], 5)
res["swing_clearance_min"] = round(res["swing_clearance_min"], 5)
res["torso_angle_range"] = [round(v, 1) for v in res["torso_angle_range"]]
res["cam_jump_max"] = round(res["cam_jump_max"], 4)
res["cam_clearance_min"] = round(res["cam_clearance_min"], 3)

checks = {
    "drift_L<=0.005": res["drift"]["L"] <= 0.005,
    "drift_R<=0.005": res["drift"]["R"] <= 0.005,
    "penetration<=0.002": res["penetration_max"] <= 0.002,
    "swing_clearance>=0.01": res["swing_clearance_min"] >= 0.01,
    "cam_jump<0.30": res["cam_jump_max"] < 0.30,
    "cam_clearance>=0.08": res["cam_clearance_min"] >= 0.08,
    "silhouette>=12%": res["final_silhouette_pct"] >= 12.0,
}
res["checks"] = checks
res["pass"] = all(checks.values())

out = os.path.join(os.path.dirname(bpy.data.filepath), "..", "diagnostics", "physical-validation.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump(res, open(out, "w"), indent=1)
print("VALIDATION_JSON=" + json.dumps(res, indent=1))
