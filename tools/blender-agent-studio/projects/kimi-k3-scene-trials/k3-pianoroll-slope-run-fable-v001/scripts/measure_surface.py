"""Measure USTUDIO_PIANO_ROLL_FLOOR in the local frame of USTUDIO_BOX_FLOAT_ROOT.

Read-only. Writes diagnostics/surface-analysis.json. Run via run_workflow.py with
UNRECORDED_PARAMS = {"output": "<path to surface-analysis.json>"}.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector

P = globals().get("UNRECORDED_PARAMS", {})
output_path = Path(P.get("output", "diagnostics/surface-analysis.json"))

scene = bpy.context.scene
scene.frame_set(1)
depsgraph = bpy.context.evaluated_depsgraph_get()

floor = bpy.data.objects["USTUDIO_PIANO_ROLL_FLOOR"]
root = bpy.data.objects["USTUDIO_BOX_FLOAT_ROOT"]

# Parent chain of the floor, to prove it is rigid with the float root.
chain = []
obj = floor
while obj is not None:
    chain.append(obj.name)
    obj = obj.parent

root_inv = root.matrix_world.inverted()

floor_eval = floor.evaluated_get(depsgraph)
mesh = floor_eval.to_mesh()
to_root = root_inv @ floor_eval.matrix_world
verts_local = [to_root @ v.co for v in mesh.vertices]

# Average polygon normal, transformed to root frame (normal matrix).
normal_matrix = to_root.to_3x3().inverted().transposed()
normal_sum = Vector((0.0, 0.0, 0.0))
for poly in mesh.polygons:
    normal_sum += normal_matrix @ poly.normal
normal = normal_sum.normalized()
if normal.z < 0:
    normal = -normal  # keep the up-facing side
floor_eval.to_mesh_clear()

up = Vector((0.0, 0.0, 1.0))
slope_rad = normal.angle(up)
slope_deg = math.degrees(slope_rad)

# Steepest-ascent tangent: projection of local up on the plane.
uphill = (up - normal * up.dot(normal)).normalized()
cross = normal.cross(uphill).normalized()  # right-handed: normal x uphill

# Plane coordinates (s along uphill, t along cross, h along normal) of all vertices.
origin = sum(verts_local, Vector()) / len(verts_local)
coords = []
for v in verts_local:
    d = v - origin
    coords.append((d.dot(uphill), d.dot(cross), d.dot(normal)))
s_vals = [c[0] for c in coords]
t_vals = [c[1] for c in coords]
h_vals = [c[2] for c in coords]
s_min, s_max = min(s_vals), max(s_vals)
t_min, t_max = min(t_vals), max(t_vals)

def plane_point(s, t):
    p = origin + uphill * s + cross * t
    return [round(p.x, 6), round(p.y, 6), round(p.z, 6)]

corners = {
    "bottom_left": plane_point(s_min, t_min),
    "bottom_right": plane_point(s_min, t_max),
    "top_left": plane_point(s_max, t_min),
    "top_right": plane_point(s_max, t_max),
}

# Planarity: spread of vertices along the normal.
planarity_error = max(h_vals) - min(h_vals)

# Clearance raycasts in world space at frame 1 (rigid distances are frame-invariant
# because every relevant object is a child of the float root).
root_mat = root.matrix_world
def to_world_dir(vec):
    return (root_mat.to_3x3() @ vec).normalized()

def cast(origin_local, direction_local, ignore=("USTUDIO_PIANO_ROLL_FLOOR",)):
    origin_world = root_mat @ origin_local
    direction_world = to_world_dir(direction_local)
    offset = origin_world + direction_world * 0.001
    hit, location, _, _, obj, _ = scene.ray_cast(depsgraph, offset, direction_world)
    while hit and obj.name in ignore:
        offset = location + direction_world * 0.002
        hit, location, _, _, obj, _ = scene.ray_cast(depsgraph, offset, direction_world)
    if not hit:
        return {"hit": False}
    return {"hit": True, "object": obj.name, "distance": round((location - origin_world).length, 4)}

mid = origin
clearances = {
    "along_normal_from_center": cast(mid, normal),
    "along_local_up_from_center": cast(mid, up),
    "cross_positive_from_center": cast(mid, cross),
    "cross_negative_from_center": cast(mid, -cross),
    "uphill_beyond_top": cast(origin + uphill * s_max, uphill),
    "downhill_beyond_bottom": cast(origin + uphill * s_min, -uphill),
    "along_normal_from_top_quarter": cast(origin + uphill * (s_max * 0.5), normal),
    "along_normal_from_bottom_quarter": cast(origin + uphill * (s_min * 0.5), normal),
}

# Context: bounds of the interior panels and shell in root frame, for the camera corridor.
context_bounds = {}
for name in sorted(o.name for o in scene.objects if o.type == "MESH"):
    obj = bpy.data.objects[name]
    obj_eval = obj.evaluated_get(depsgraph)
    to_root_obj = root_inv @ obj_eval.matrix_world
    pts = [to_root_obj @ Vector(c) for c in obj.bound_box]
    context_bounds[name] = {
        "min": [round(min(p[i] for p in pts), 4) for i in range(3)],
        "max": [round(max(p[i] for p in pts), 4) for i in range(3)],
    }

friction_required = math.tan(slope_rad)

payload = {
    "schema_version": 1,
    "trial_id": "k3-pianoroll-slope-run-fable-v001",
    "frame_of_reference": "USTUDIO_BOX_FLOAT_ROOT local space, meters",
    "measured_at_frame": 1,
    "surface_object": "USTUDIO_PIANO_ROLL_FLOOR",
    "parent_chain_of_surface": chain,
    "vertex_count": len(verts_local),
    "vertices_local_root": [[round(v.x, 6), round(v.y, 6), round(v.z, 6)] for v in verts_local[:8]],
    "plane_origin": [round(origin.x, 6), round(origin.y, 6), round(origin.z, 6)],
    "SURFACE_NORMAL": [round(normal.x, 6), round(normal.y, 6), round(normal.z, 6)],
    "UPHILL_TANGENT": [round(uphill.x, 6), round(uphill.y, 6), round(uphill.z, 6)],
    "CROSS_SLOPE_TANGENT": [round(cross.x, 6), round(cross.y, 6), round(cross.z, 6)],
    "WORLD_GRAVITY": [0.0, 0.0, -9.81],
    "gravity_note": "gravité monde -Z ; le float root oscille d'environ ±1°, la verticale locale reste la référence de posture à cette tolérance près",
    "slope_angle_degrees": round(slope_deg, 4),
    "planarity_error_m": round(planarity_error, 6),
    "usable_length_uphill_m": round(s_max - s_min, 6),
    "usable_width_cross_m": round(t_max - t_min, 6),
    "limits_plane_coords": {
        "s_min_bottom": round(s_min, 6),
        "s_max_top": round(s_max, 6),
        "t_min": round(t_min, 6),
        "t_max": round(t_max, 6),
    },
    "corners_local_root": corners,
    "clearances_m": clearances,
    "static_friction_required_no_grip": round(friction_required, 4),
    "grip_contract": {
        "property": "ustudio_grip_surface",
        "declared_friction_coefficient": 1.25,
        "minimum_required": round(friction_required, 4),
        "margin": round(1.25 - friction_required, 4),
        "visible_cause": "semelles grip lime avec pulse d'émission au contact uniquement",
    },
    "context_bounds_local_root": context_bounds,
}

output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps({
    "slope_angle_degrees": payload["slope_angle_degrees"],
    "usable_length_uphill_m": payload["usable_length_uphill_m"],
    "usable_width_cross_m": payload["usable_width_cross_m"],
    "SURFACE_NORMAL": payload["SURFACE_NORMAL"],
    "UPHILL_TANGENT": payload["UPHILL_TANGENT"],
    "plane_origin": payload["plane_origin"],
    "parent_chain": chain,
    "planarity_error_m": payload["planarity_error_m"],
    "clearances": clearances,
}, ensure_ascii=False))
