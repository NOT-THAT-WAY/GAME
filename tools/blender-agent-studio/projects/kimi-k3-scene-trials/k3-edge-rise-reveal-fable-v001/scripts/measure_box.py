"""Measure the FL Studio box for the edge-rise-reveal shot (read-only).

Everything in the local frame of USTUDIO_BOX_FLOAT_ROOT. Measures the interior
height, the front bottom rim (the seat), the sloped Piano Roll floor plane, the
playhead sweep cycle, and the clearances that constrain the camera path.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector

P = globals().get("UNRECORDED_PARAMS", {})
out_path = Path(P.get("output", "diagnostics/box-analysis.json"))

scene = bpy.context.scene
scene.frame_set(1)
dg = bpy.context.evaluated_depsgraph_get()
root = bpy.data.objects["USTUDIO_BOX_FLOAT_ROOT"]
root_inv = root.matrix_world.inverted()

def bounds_local(obj):
    obj_e = obj.evaluated_get(dg)
    m = root_inv @ obj_e.matrix_world
    pts = [m @ Vector(c) for c in obj.bound_box]
    return ([round(min(p[i] for p in pts), 4) for i in range(3)],
            [round(max(p[i] for p in pts), 4) for i in range(3)])

bounds = {}
for obj in scene.objects:
    if obj.type == "MESH":
        bounds[obj.name] = bounds_local(obj)

# ---- sloped floor plane
floor = bpy.data.objects["USTUDIO_PIANO_ROLL_FLOOR"]
floor_e = floor.evaluated_get(dg)
mesh = floor_e.to_mesh()
to_root = root_inv @ floor_e.matrix_world
vlocal = [to_root @ v.co for v in mesh.vertices]
nm = to_root.to_3x3().inverted().transposed()
nsum = Vector()
for poly in mesh.polygons:
    nsum += nm @ poly.normal
normal = nsum.normalized()
if normal.z < 0:
    normal = -normal
floor_e.to_mesh_clear()
up = Vector((0, 0, 1))
slope_rad = normal.angle(up)
uphill = (up - normal * up.dot(normal)).normalized()
cross = normal.cross(uphill).normalized()
origin = sum(vlocal, Vector()) / len(vlocal)
s_vals = [(v - origin).dot(uphill) for v in vlocal]
t_vals = [(v - origin).dot(cross) for v in vlocal]

# ---- the seat: top face of the front bottom rim
rim = bpy.data.objects["USTUDIO_FRONT_BOTTOM_RIM"]
rim_min, rim_max = bounds["USTUDIO_FRONT_BOTTOM_RIM"]

# where does the ramp start relative to the rim top?
ramp_front_edge_z = origin.z + uphill.z * min(s_vals)
ramp_front_edge_y = origin.y + uphill.y * min(s_vals)

# ---- interior height: from ramp surface up to the ceiling, along world up
ceiling_min = bounds["USTUDIO_CEILING"][0]
interior_panels = ["USTUDIO_BACK_WALL", "USTUDIO_BROWSER_LEFT_WALL", "USTUDIO_MIXER_RIGHT_WALL"]
panel_z = [bounds[n] for n in interior_panels]
interior_height_panels = max(b[1][2] for b in panel_z) - min(b[0][2] for b in panel_z)

def ray(origin_local, direction_local, ignore=()):
    ow = root.matrix_world @ origin_local
    dw = (root.matrix_world.to_3x3() @ direction_local).normalized()
    off = ow + dw * 0.001
    hit, loc, _, _, obj, _ = scene.ray_cast(dg, off, dw)
    while hit and obj.name in ignore:
        off = loc + dw * 0.002
        hit, loc, _, _, obj, _ = scene.ray_cast(dg, off, dw)
    return {"hit": bool(hit), "object": obj.name if hit else None,
            "distance": round((loc - ow).length, 4) if hit else None}

center_floor = origin
headroom = ray(center_floor, up, ignore=("USTUDIO_PIANO_ROLL_FLOOR",))

# ---- playhead sweep: sample its x position over the timeline
playhead = bpy.data.objects.get("USTUDIO_PLAYHEAD_BACK")
sweep = []
if playhead:
    for f in range(1, scene.frame_end + 1, 4):
        scene.frame_set(f)
        dgf = bpy.context.evaluated_depsgraph_get()
        p = root.matrix_world.inverted() @ playhead.evaluated_get(dgf).matrix_world.translation
        sweep.append({"frame": f, "x": round(p.x, 4), "z": round(p.z, 4)})
scene.frame_set(1)

# frames where the playhead crosses x = 0
crossings = []
for a, b in zip(sweep, sweep[1:]):
    if a["x"] <= 0 <= b["x"] or b["x"] <= 0 <= a["x"]:
        span = b["x"] - a["x"]
        t = 0.0 if abs(span) < 1e-9 else (0 - a["x"]) / span
        crossings.append(round(a["frame"] + t * (b["frame"] - a["frame"]), 1))

payload = {
    "schema_version": 1,
    "frame_of_reference": "USTUDIO_BOX_FLOAT_ROOT local, meters",
    "scene_frame_range": [scene.frame_start, scene.frame_end],
    "scene_fps": scene.render.fps,
    "floor": {
        "object": "USTUDIO_PIANO_ROLL_FLOOR",
        "slope_degrees": round(math.degrees(slope_rad), 4),
        "normal": [round(c, 6) for c in normal],
        "uphill_tangent": [round(c, 6) for c in uphill],
        "cross_tangent": [round(c, 6) for c in cross],
        "plane_origin": [round(c, 6) for c in origin],
        "s_range": [round(min(s_vals), 4), round(max(s_vals), 4)],
        "t_range": [round(min(t_vals), 4), round(max(t_vals), 4)],
        "front_edge_y": round(ramp_front_edge_y, 4),
        "front_edge_z": round(ramp_front_edge_z, 4),
        "static_friction_required_direct": round(math.tan(slope_rad), 4),
    },
    "seat": {
        "object": "USTUDIO_FRONT_BOTTOM_RIM",
        "top_z": rim_max[2],
        "y_range": [rim_min[1], rim_max[1]],
        "x_range": [rim_min[0], rim_max[0]],
        "step_up_to_ramp_front": round(ramp_front_edge_z - rim_max[2], 4),
    },
    "interior": {
        "panel_height_m": round(interior_height_panels, 4),
        "ceiling_underside_z": ceiling_min[2],
        "headroom_at_floor_center": headroom,
        "front_opening_x": [bounds["USTUDIO_FRONT_LEFT_RIM"][1][0], bounds["USTUDIO_FRONT_RIGHT_RIM"][0][0]],
        "front_opening_z": [bounds["USTUDIO_FRONT_BOTTOM_RIM"][1][2], bounds["USTUDIO_FRONT_TOP_RIM"][0][2]],
        "front_opening_y": bounds["USTUDIO_FRONT_BOTTOM_RIM"][0][1],
        "back_wall_y": bounds["USTUDIO_BACK_WALL"][0][1],
    },
    "playhead": {
        "object": "USTUDIO_PLAYHEAD_BACK" if playhead else None,
        "x_range": [min(s["x"] for s in sweep), max(s["x"] for s in sweep)] if sweep else None,
        "z_range": [min(s["z"] for s in sweep), max(s["z"] for s in sweep)] if sweep else None,
        "center_crossing_frames": crossings,
        "sweep_samples": sweep,
    },
    "bounds_local_root": bounds,
}
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps({
    "slope_deg": payload["floor"]["slope_degrees"],
    "seat": payload["seat"],
    "interior": payload["interior"],
    "playhead_crossings": crossings,
}, ensure_ascii=False))
