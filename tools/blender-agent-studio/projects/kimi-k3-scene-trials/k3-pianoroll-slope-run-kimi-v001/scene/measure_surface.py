"""ETAPE C — mesure reelle de USTUDIO_PIANO_ROLL_FLOOR dans scene/trial.blend.

Tout est calcule dans le repere local de USTUDIO_BOX_FLOAT_ROOT (la boite flotte,
le personnage et la camera seront parentes a ce root).
Sortie : diagnostics/surface-analysis.json. Lecture seule, aucune sauvegarde.
"""
import bpy
import json
import math
from mathutils import Vector

TRIAL = "${BLENDER_AGENT_STUDIO_ROOT}/projects/kimi-k3-scene-trials/k3-pianoroll-slope-run-kimi-v001"
assert bpy.data.filepath.endswith("scene/trial.blend"), bpy.data.filepath

sc = bpy.context.scene
root = bpy.data.objects["USTUDIO_BOX_FLOAT_ROOT"]
floor = bpy.data.objects["USTUDIO_PIANO_ROLL_FLOOR"]

sc.frame_set(1)
bpy.context.view_layer.update()

# sommets en local FLOAT_ROOT
inv = root.matrix_world.inverted()
verts_local = [inv @ (floor.matrix_world @ Vector(c)) for c in floor.bound_box]
# le mesh a 4 vrais sommets : utiliser les vertices reels
verts_mesh = [inv @ (floor.matrix_world @ v.co) for v in floor.data.vertices]

def r3(v):
    return [round(v.x, 5), round(v.y, 5), round(v.z, 5)]

# plan : moyenne + normale par produit vectoriel des aretes du quad
pts = verts_mesh
center = sum(pts, Vector()) / len(pts)
n = Vector((0, 0, 0))
for i in range(len(pts)):
    n += (pts[i] - center).cross(pts[(i + 1) % len(pts)] - center)
n.normalize()
# orienter la normale vers le haut monde (composante z positive en local root ~ monde)
if n.z < 0:
    n = -n

WORLD_UP = Vector((0, 0, 1))
slope_deg = math.degrees(math.acos(max(-1.0, min(1.0, n.dot(WORLD_UP)))))

# axe montant : projection de +Z sur le plan
uphill = WORLD_UP - n * WORLD_UP.dot(n)
uphill.normalize()
# axe transversal
cross = n.cross(uphill)
cross.normalize()

# etendue du quad selon les deux axes
du = [ (p - center).dot(uphill) for p in pts ]
dv = [ (p - center).dot(cross) for p in pts ]
len_up = max(du) - min(du)
len_cross = max(dv) - min(dv)
low_pt = center + uphill * min(du)
high_pt = center + uphill * max(du)

# distance plafond / parois / mur du fond depuis le point haut et le centre
deps = bpy.context.evaluated_depsgraph_get()
def cast_down_from(origin_world, direction_world):
    return sc.ray_cast(deps, origin_world, direction_world)

# positions monde pour les mesures de clearance
root_mw = root.matrix_world
center_w = root_mw @ center
high_w = root_mw @ high_pt

def dist_to(name, origin, direction, max_d=20.0):
    ob = bpy.data.objects.get(name)
    if not ob:
        return None
    # distance approximative via plus proche point de la bounding box evaluee
    pts_b = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return round(min((p - origin).length for p in pts_b), 4)

clearances = {
    "high_point_to_back_wall": dist_to("USTUDIO_BACK_WALL", high_w, None),
    "center_to_ceiling": dist_to("USTUDIO_CEILING", center_w, None),
    "center_to_left_wall": dist_to("USTUDIO_BROWSER_LEFT_WALL", center_w, None),
    "center_to_right_wall": dist_to("USTUDIO_MIXER_RIGHT_WALL", center_w, None),
}

# pente effective le long de l'axe montant : dz/dy en local
run = Vector((uphill.x, uphill.y, 0)).length
slope_check = math.degrees(math.atan2(uphill.z, run))

out = {
    "measured_at_frame": 1,
    "reference_space": "USTUDIO_BOX_FLOAT_ROOT local",
    "surface_object": "USTUDIO_PIANO_ROLL_FLOOR",
    "vertices_local": [r3(p) for p in pts],
    "center_local": r3(center),
    "SURFACE_NORMAL": r3(n),
    "UPHILL_TANGENT": r3(uphill),
    "CROSS_SLOPE_TANGENT": r3(cross),
    "WORLD_GRAVITY": [0.0, 0.0, -9.81],
    "slope_degrees_from_world_horizontal": round(slope_deg, 3),
    "slope_degrees_crosscheck_atan2": round(slope_check, 3),
    "usable_length_uphill_m": round(len_up, 4),
    "usable_width_cross_m": round(len_cross, 4),
    "low_edge_local": r3(low_pt),
    "high_edge_local": r3(high_pt),
    "clearances_m": clearances,
    "static_friction_min_theoretical": round(math.tan(math.radians(slope_deg)), 4),
    "grip_contract": {
        "property": "ustudio_grip_surface",
        "friction_coefficient": 1.25,
        "justification": "tan(46.34°) ≈ 1.048 < 1.25 : marge dynamique ~19%",
    },
}
with open(TRIAL + "/diagnostics/surface-analysis.json", "w") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print("SLOPE", round(slope_deg, 3), "deg | up", r3(uphill), "| len_up", round(len_up, 3),
      "| len_cross", round(len_cross, 3), "| normal", r3(n))
print("CENTER", r3(center), "LOW", r3(low_pt), "HIGH", r3(high_pt))
