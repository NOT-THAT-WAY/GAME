"""Bone-by-bone comparison of the knockout interface poses. Batch, read-only.

The brief requires three poses to be the SAME pose, not merely similar:

    SB_Knockout   frame 30  ==  SB_KnockedOutLoop frame 1
    SB_Recover    frame 1   ==  SB_KnockedOutLoop frame 1

They were authored from one shared constant, but the clearance pass in
`pose_kernel.relax_arms` edits poses frame by frame AFTER authoring, so the
equality has to be re-measured on the finished clips rather than assumed from
the source. This probe compares armature-space matrices bone by bone.

Usage:
  blender -b --factory-startup <master.blend> --python interface_poses.py -- <out.json>
"""
import bpy
import json
import math
import sys

argv = sys.argv[sys.argv.index("--") + 1:]
OUT = argv[0]

# Tolerances: a millimetre and a hundredth of a degree are far below anything an
# engine transition could show, while leaving room for float round-tripping.
POSITION_TOLERANCE_M = 0.001
ROTATION_TOLERANCE_DEG = 0.01

PAIRS = [
    ("SB_Knockout", 30, "SB_KnockedOutLoop", 1),
    ("SB_Recover", 1, "SB_KnockedOutLoop", 1),
]

rig = bpy.data.objects["BAS_PUNCH_Rig"]
scene = bpy.context.scene
bones = [b.name for b in rig.data.bones]


def sample(action_name, frame):
    action = bpy.data.actions[action_name]
    if rig.animation_data is None:
        rig.animation_data_create()
    rig.animation_data.action = action
    for slot in getattr(action, "slots", []):
        try:
            rig.animation_data.action_slot = slot
            break
        except Exception:
            pass
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    return {name: rig.pose.bones[name].matrix.copy() for name in bones}


report = {"tolerances": {"position_m": POSITION_TOLERANCE_M,
                         "rotation_deg": ROTATION_TOLERANCE_DEG},
          "pairs": []}

for from_action, from_frame, to_action, to_frame in PAIRS:
    a = sample(from_action, from_frame)
    b = sample(to_action, to_frame)
    per_bone = {}
    worst_pos, worst_rot = 0.0, 0.0
    for name in bones:
        position = (a[name].translation - b[name].translation).length
        angle = abs(math.degrees(
            a[name].to_quaternion().rotation_difference(
                b[name].to_quaternion()).angle))
        if angle > 180.0:
            angle = 360.0 - angle
        per_bone[name] = {"position_delta_m": position,
                          "rotation_delta_deg": angle}
        worst_pos = max(worst_pos, position)
        worst_rot = max(worst_rot, angle)
    report["pairs"].append({
        "from": f"{from_action} f{from_frame}",
        "to": f"{to_action} f{to_frame}",
        "worst_position_delta_m": worst_pos,
        "worst_rotation_delta_deg": worst_rot,
        "bones": per_bone,
        "pass": (worst_pos <= POSITION_TOLERANCE_M
                 and worst_rot <= ROTATION_TOLERANCE_DEG),
    })

report["pass"] = all(p["pass"] for p in report["pairs"])
with open(OUT, "w") as handle:
    json.dump(report, handle, indent=1)

print("INTERFACE_DONE " + OUT)
print("INTERFACE_PASS " + str(report["pass"]))
for pair in report["pairs"]:
    print(f"  {pair['from']} -> {pair['to']}: "
          f"pos={pair['worst_position_delta_m']:.7f} m "
          f"rot={pair['worst_rotation_delta_deg']:.5f} deg pass={pair['pass']}")
