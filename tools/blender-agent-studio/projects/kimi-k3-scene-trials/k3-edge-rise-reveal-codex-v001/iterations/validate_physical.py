"""Dense physical/contact validation for the isolated K3 edge-rise trial."""
import bpy
import json
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

TRIAL = Path("${BLENDER_AGENT_STUDIO_ROOT}/projects/kimi-k3-scene-trials/k3-edge-rise-reveal-codex-v001")
scene = bpy.context.scene
body = bpy.data.objects["K3_EDGE_BODY_V2"]
head = bpy.data.objects["K3_EDGE_HEAD_V2"]
rig = bpy.data.objects["K3_EDGE_RIG"]
camera = bpy.data.objects["K3_EDGE_CAMERA"]


def floor_z(y):
    return 0.88 + (y + 0.42) * (1.75 / 1.67)


def distance(a, b):
    return (Vector(a) - Vector(b)).length


depsgraph = bpy.context.evaluated_depsgraph_get()
floor_samples = []
side_clearances = []
ceiling_clearances = []
for frame in range(110, 361):
    scene.frame_set(frame)
    depsgraph.update()
    evaluated = body.evaluated_get(depsgraph)
    points = [evaluated.matrix_world @ vertex.co for vertex in evaluated.data.vertices]
    relevant = [p for p in points if -0.50 <= p.y <= 1.30]
    min_clearance = min(p.z - floor_z(p.y) for p in relevant)
    floor_samples.append((frame, min_clearance))
    side_clearances.append((frame, min(3.65 + min(p.x for p in points), 3.65 - max(p.x for p in points))))
    ceiling_clearances.append((frame, 5.30 - max(p.z for p in points)))

stance_intervals = [
    (158, 169, "L", -0.18), (170, 181, "R", -0.09),
    (182, 193, "L", -0.01), (194, 206, "R", 0.07),
    (207, 218, "L", 0.15), (219, 230, "R", 0.24),
    (231, 242, "L", 0.32), (243, 255, "R", 0.41),
    (256, 360, "L", 0.50), (256, 360, "R", 0.41),
]
stance_results = []
for start, end, side, expected_y in stance_intervals:
    positions = []
    clearances = []
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        p = rig.matrix_world @ rig.pose.bones["foot." + side].tail
        positions.append(list(p))
        clearances.append(p.z - floor_z(p.y))
    origin = positions[0]
    slip = max(distance(p, origin) for p in positions)
    stance_results.append({
        "frames": [start, end], "side": side, "expected_y_m": expected_y,
        "max_slip_m": round(slip, 6),
        "clearance_range_m": [round(min(clearances), 6), round(max(clearances), 6)],
    })

hand_targets = {"L": Vector((0.18, -0.50, 0.78)), "R": Vector((-0.18, -0.50, 0.78))}
hand_errors = {"L": [], "R": []}
for frame in range(49, 74):
    scene.frame_set(frame)
    for side in ("L", "R"):
        p = rig.matrix_world @ rig.pose.bones["forearm." + side].tail
        hand_errors[side].append((p - hand_targets[side]).length)

camera_y = []
for frame in range(1, 361):
    scene.frame_set(frame)
    camera_y.append(camera.matrix_world.translation.y)
camera_to_front_shell = -1.08 - max(camera_y)

scene.frame_set(360)
depsgraph.update()
projected = []
for obj in (body, head):
    evaluated = obj.evaluated_get(depsgraph)
    for corner in evaluated.bound_box:
        world = evaluated.matrix_world @ Vector(corner)
        projected.append(world_to_camera_view(scene, camera, world))
ys = [p.y for p in projected if p.z > 0]
final_height = max(ys) - min(ys)

min_floor_frame, min_floor = min(floor_samples, key=lambda x: x[1])
min_side_frame, min_side = min(side_clearances, key=lambda x: x[1])
min_ceiling_frame, min_ceiling = min(ceiling_clearances, key=lambda x: x[1])
max_slip = max(item["max_slip_m"] for item in stance_results)
max_hand_error = max(max(values) for values in hand_errors.values())

checks = {
    "floor_penetration_within_tolerance": min_floor >= -0.025,
    "stance_slip_within_tolerance": max_slip <= 0.015,
    "hand_rim_contact_within_tolerance": max_hand_error <= 0.040,
    "side_wall_clearance_positive": min_side >= 0.10,
    "ceiling_clearance_positive": min_ceiling >= 0.10,
    "camera_corridor_clear": camera_to_front_shell >= 0.12,
    "final_character_frame_height": final_height >= 0.12,
}
payload = {
    "schema_version": 1,
    "trial_id": "k3-edge-rise-reveal-codex-v001",
    "passed": all(checks.values()),
    "checks": checks,
    "tolerances": {"floor_penetration_m": 0.025, "stance_slip_m": 0.015, "hand_contact_m": 0.040, "camera_clearance_m": 0.12, "final_frame_height": 0.12},
    "measurements": {
        "minimum_floor_clearance_m": round(min_floor, 6),
        "minimum_floor_clearance_frame": min_floor_frame,
        "maximum_stance_slip_m": round(max_slip, 6),
        "maximum_hand_contact_error_m": round(max_hand_error, 6),
        "minimum_side_wall_clearance_m": round(min_side, 6),
        "minimum_side_wall_clearance_frame": min_side_frame,
        "minimum_ceiling_clearance_m": round(min_ceiling, 6),
        "minimum_ceiling_clearance_frame": min_ceiling_frame,
        "camera_to_front_shell_minimum_m": round(camera_to_front_shell, 6),
        "final_character_frame_height_ratio": round(final_height, 6),
    },
    "stance_intervals": stance_results,
    "notes": [
        "Two added trial-only foot controls align the rounded V2 leg ends with the audited 46-degree floor normal; evaluated mesh clearance, not bone position alone, is the collision criterion.",
        "The floor is the audited inclined piano-roll plane; no flat surrogate floor is used.",
        "Seated frames use the front rim as support and are excluded from the floor-penetration sweep.",
        "Mesh topology and proportions are unchanged; only trial-copy weights and an armature were added.",
    ],
}
path = TRIAL / "diagnostics/physical-validation.json"
path.write_text(json.dumps(payload, indent=2) + "\n")
print("K3_PHYSICAL_VALIDATION=" + json.dumps(payload))
