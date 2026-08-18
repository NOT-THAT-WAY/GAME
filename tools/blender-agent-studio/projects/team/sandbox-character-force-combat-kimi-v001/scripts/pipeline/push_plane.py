"""Derive the SB_Push proxy plane from evaluated geometry. Batch, read-only.

The brief asks the hands to press a plane and forbids that plane from ever being
exported. It is therefore never created as an object: it is DERIVED from where
the fists actually are, frame by frame, on the evaluated meshes, and lives only
in this JSON.

The plane is the frontmost extent the fists reach, y = min over the cycle. What
matters for the verdict is how far the contact wanders from it: a hand that
pumps on a wall would swing back and forth against this plane.

Usage:
  blender -b --factory-startup <master.blend> --python push_plane.py -- <out.json>
"""
import bpy
import json
import sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
OUT = argv[0]
ACTION = "SB_Push"
PUMP_TOLERANCE_M = 0.010

scene = bpy.context.scene
rig = bpy.data.objects["BAS_PUNCH_Rig"]
action = bpy.data.actions[ACTION]
if rig.animation_data is None:
    rig.animation_data_create()
rig.animation_data.action = action
for slot in getattr(action, "slots", []):
    try:
        rig.animation_data.action_slot = slot
        break
    except Exception:
        pass

f0 = int(round(action.frame_range[0]))
f1 = int(round(action.frame_range[1]))
depsgraph = bpy.context.evaluated_depsgraph_get()

frames = []
for frame in range(f0, f1 + 1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    depsgraph.update()
    entry = {"frame": frame}
    for side in ("L", "R"):
        obj = bpy.data.objects[f"BAS_PUNCH_Fist_{side}"].evaluated_get(depsgraph)
        mesh = obj.to_mesh()
        verts = [obj.matrix_world @ v.co for v in mesh.vertices]
        front = min(v.y for v in verts)
        contact = [v for v in verts if v.y <= front + 0.01]
        centroid = sum(contact, Vector((0, 0, 0))) / len(contact)
        obj.to_mesh_clear()
        entry[side] = {"front_y": front, "contact_points": len(contact),
                       "contact_centroid": list(centroid)}
    frames.append(entry)

plane_y = min(min(f["L"]["front_y"], f["R"]["front_y"]) for f in frames)
report = {
    "action": ACTION,
    "plane": {"axis": "y", "value_m": plane_y,
              "derivation": "y minimal atteint par les poings evalues sur le cycle",
              "exported": False},
    "pump": {},
    "frames": frames,
}
for side in ("L", "R"):
    fronts = [f[side]["front_y"] for f in frames]
    lateral = [Vector(f[side]["contact_centroid"]) for f in frames]
    centre = sum(lateral, Vector((0, 0, 0))) / len(lateral)
    report["pump"][side] = {
        "distance_to_plane_min_m": min(fronts) - plane_y,
        "distance_to_plane_max_m": max(fronts) - plane_y,
        "pump_amplitude_m": max(fronts) - min(fronts),
        "contact_wander_m": max((p - centre).length for p in lateral),
        "pass": (max(fronts) - min(fronts)) <= PUMP_TOLERANCE_M,
    }
report["pump_tolerance_m"] = PUMP_TOLERANCE_M
report["pass"] = all(v["pass"] for v in report["pump"].values())

with open(OUT, "w") as handle:
    json.dump(report, handle, indent=1)
print("PUSH_PLANE_DONE " + OUT)
print(f"PUSH_PLANE_PASS {report['pass']} plane_y={plane_y:.6f} "
      f"L_pump={report['pump']['L']['pump_amplitude_m']:.6f} "
      f"R_pump={report['pump']['R']['pump_amplitude_m']:.6f}")
