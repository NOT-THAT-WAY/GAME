"""Frame-to-frame continuity audit of a finished clip. Batch, read-only.

The arm-clearance pass in `pose_kernel.relax_arms` corrects each frame on its
own. That guarantees no frame collides, but nothing in it guarantees that two
neighbouring frames got similar corrections, and a clip can therefore pass every
physical gate while visibly snapping. This probe measures that directly: it
reports, per bone, the largest single-frame angular and positional step and
compares it to the clip's own median step.

A spike is defined relative to the clip rather than to a fixed number of degrees,
because a sprint legitimately moves far more per frame than a carry idle.

Usage:
  blender -b --factory-startup <checkpoint.blend> --python continuity_probe.py -- \
      <action> <out.json>
"""
import bpy
import json
import math
import statistics
import sys

argv = sys.argv[sys.argv.index("--") + 1:]
ACTION, OUT = argv[0], argv[1]

SPIKE_RATIO = 4.0
# A ratio alone is not well posed: a bone that is deliberately motionless for
# most of a clip has a median of ~0, so any movement at all divides by nothing
# and reports an infinite spike. A step must exceed BOTH the ratio and this
# absolute floor to count. 8 deg per frame at 30 fps is 240 deg/s, well above
# anything a secondary correction should produce.
SPIKE_ABSOLUTE_DEG = 8.0

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

f_start = int(round(action.frame_range[0]))
f_end = int(round(action.frame_range[1]))
bones = [b.name for b in rig.data.bones]

poses = {}
for frame in range(f_start, f_end + 1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    poses[frame] = {n: rig.pose.bones[n].matrix.copy() for n in bones}

report = {"action": ACTION, "range": [f_start, f_end],
          "spike_ratio_threshold": SPIKE_RATIO,
          "spike_absolute_deg": SPIKE_ABSOLUTE_DEG, "bones": {}}
worst = {"bone": None, "ratio": 0.0, "frame": None, "peak_deg": 0.0,
         "qualifies": False}

for name in bones:
    rot_steps, pos_steps = [], []
    for frame in range(f_start, f_end):
        a, b = poses[frame][name], poses[frame + 1][name]
        angle = abs(math.degrees(
            a.to_quaternion().rotation_difference(b.to_quaternion()).angle))
        # A quaternion and its negation are the same orientation, so the
        # difference can come back as the long way round. Reading it raw
        # reported 359.8 deg steps on a hand that had barely moved.
        if angle > 180.0:
            angle = 360.0 - angle
        rot_steps.append(angle)
        pos_steps.append((a.translation - b.translation).length)

    median = statistics.median(rot_steps) if rot_steps else 0.0
    peak = max(rot_steps) if rot_steps else 0.0
    peak_frame = f_start + rot_steps.index(peak) if rot_steps else f_start
    # A ratio needs a meaningful denominator: a bone that barely moves has a
    # near-zero median, and dividing by it would turn a fraction of a degree
    # into a fake spike.
    ratio = peak / median if median > 0.05 else (0.0 if peak < 0.5 else 999.0)

    report["bones"][name] = {
        "median_rotation_step_deg": median,
        "peak_rotation_step_deg": peak,
        "peak_frame": peak_frame,
        "peak_over_median_ratio": ratio,
        "max_position_step_m": max(pos_steps) if pos_steps else 0.0,
    }
    # Rank by whether the bone actually qualifies as a spike FIRST. Ranking by
    # ratio alone would elect a bone with ratio 999 and a 4 deg peak as "worst",
    # let it pass the absolute floor, and hide a genuinely snapping bone behind
    # it.
    qualifies = ratio > SPIKE_RATIO and peak > SPIKE_ABSOLUTE_DEG
    key = (1 if qualifies else 0, peak if qualifies else ratio)
    if key > (1 if worst.get("qualifies") else 0,
              worst["peak_deg"] if worst.get("qualifies") else worst["ratio"]):
        worst = {"bone": name, "ratio": ratio, "frame": peak_frame,
                 "peak_deg": peak, "qualifies": qualifies}

report["worst"] = worst
report["pass"] = not worst.get("qualifies", False)

with open(OUT, "w") as handle:
    json.dump(report, handle, indent=1)
print("CONTINUITY_DONE " + OUT)
print(f"CONTINUITY_PASS {report['pass']} worst={worst['bone']} "
      f"ratio={worst['ratio']:.2f} frame={worst['frame']}")
