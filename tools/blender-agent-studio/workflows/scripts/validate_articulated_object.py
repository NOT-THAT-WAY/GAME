"""Prevalidate an articulated object with evaluated bounds; not a final BVH proof."""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector

P = globals().get("STUDIO_PARAMS", globals().get("UNRECORDED_PARAMS", {}))
contract_path = Path(P["contract"])
output_dir = Path(P["output_dir"])
output_dir.mkdir(parents=True, exist_ok=True)
contract = json.loads(contract_path.read_text(encoding="utf-8"))
scene = bpy.context.scene
original_frame = scene.frame_current


def evaluated_bounds(objects):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in objects:
        if obj.type not in {"MESH", "CURVE", "FONT", "SURFACE", "META"}:
            continue
        evaluated = obj.evaluated_get(depsgraph)
        points.extend(evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box)
    if not points:
        raise RuntimeError("No renderable bounds for requested object set")
    return {
        "min": [min(getattr(p, axis) for p in points) for axis in "xyz"],
        "max": [max(getattr(p, axis) for p in points) for axis in "xyz"],
    }


def resolve_side(rule, side):
    if f"{side}_object" in rule:
        return [bpy.data.objects[rule[f"{side}_object"]]]
    if f"{side}_objects" in rule:
        return [bpy.data.objects[name] for name in rule[f"{side}_objects"]]
    if f"{side}_collection" in rule:
        return list(bpy.data.collections[rule[f"{side}_collection"]].all_objects)
    if f"{side}_prefix" in rule:
        prefix = rule[f"{side}_prefix"]
        return [obj for obj in bpy.data.objects if obj.name.startswith(prefix)]
    raise KeyError(f"No {side} selector in {rule['name']}")


required_semantics = {
    "fixed_base", "moving_link", "information_surface", "interaction_surface",
    "closed_relation", "open_relation", "affordance",
}
missing_semantics = sorted(required_semantics - set(contract.get("semantics", {})))
checks = []
checks.append({
    "name": "semantic_contract_complete",
    "passed": not missing_semantics,
    "missing": missing_semantics,
})

joint = contract["joint"]
joint_obj = bpy.data.objects[joint["object"]]
axis_index = {"X": 0, "Y": 1, "Z": 2}[joint["axis"]]
reference = joint["reference_open_degrees"]
lower, upper = joint["delta_limits_degrees"]

for state in joint["states"]:
    scene.frame_set(state["frame"])
    actual = math.degrees(joint_obj.rotation_euler[axis_index]) - reference
    expected = state["expected_delta_degrees"]
    error = abs(actual - expected)
    checks.append({
        "name": "joint_state_" + state["name"],
        "frame": state["frame"],
        "actual_delta_degrees": round(actual, 5),
        "expected_delta_degrees": expected,
        "error_degrees": round(error, 5),
        "within_limits": lower - 1e-4 <= actual <= upper + 1e-4,
        "passed": error <= state["tolerance_degrees"] and lower - 1e-4 <= actual <= upper + 1e-4,
    })

main = joint["opening_main_action"]
samples = []
for frame in range(main["start_frame"], main["end_frame"] + 1):
    scene.frame_set(frame)
    samples.append(math.degrees(joint_obj.rotation_euler[axis_index]) - reference)
if main["monotonic"] == "decreasing":
    monotonic = all(b <= a + 1e-5 for a, b in zip(samples, samples[1:]))
else:
    monotonic = all(b >= a - 1e-5 for a, b in zip(samples, samples[1:]))
checks.append({
    "name": "joint_main_action_monotonic",
    "direction": main["monotonic"],
    "start_delta_degrees": round(samples[0], 5),
    "end_delta_degrees": round(samples[-1], 5),
    "passed": monotonic,
})

clearances = []
for rule in contract.get("clearance_rules", []):
    upper_objects = resolve_side(rule, "upper")
    lower_objects = resolve_side(rule, "lower")
    for frame in rule["frames"]:
        scene.frame_set(frame)
        upper_bounds = evaluated_bounds(upper_objects)
        lower_bounds = evaluated_bounds(lower_objects)
        gap = upper_bounds["min"][2] - lower_bounds["max"][2]
        passed = rule["min"] - 1e-4 <= gap <= rule["max"] + 1e-4
        entry = {
            "name": rule["name"],
            "frame": frame,
            "clearance_z": round(gap, 6),
            "allowed": [rule["min"], rule["max"]],
            "passed": passed,
        }
        clearances.append(entry)
        checks.append(entry)

report = {
    "schema_version": 2,
    "evidence_level": "preliminary",
    "blend": bpy.data.filepath,
    "contract": str(contract_path),
    "object_class": contract["object_class"],
    "passed": all(check["passed"] for check in checks),
    "checks": checks,
    "clearances": clearances,
    "method": {
        "evaluated_objects": True,
        "bounds_only": True,
        "clearance_axis": "world_Z",
        "triangle_overlap_or_bvh": False,
    },
    "limitations": [
        "AABB/bounds can miss real intersections or report false positives.",
        "Only the contract's single joint schema is supported.",
        "A passing result must be followed by physical-validation schema v2 for a final claim."
    ],
    "principle": "physics + articulation + affordance; no single layer is sufficient",
}
scene.frame_set(original_frame)
path = output_dir / "articulated-object-validation.json"
path.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps({"report": str(path), "passed": report["passed"]}))
if not report["passed"]:
    raise RuntimeError("Articulated object contract failed")
