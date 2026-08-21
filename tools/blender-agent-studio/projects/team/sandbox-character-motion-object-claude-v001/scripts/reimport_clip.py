"""Reopen an exported FBX in an empty factory scene and compare it to the master.

Independent reimport gate: the candidate must come back with the same skeleton,
the same frame count and the same poses. The comparison is offset-aware because
Blender's FBX *importer* renumbers a take starting at frame 2 while the exporter
wrote it from frame 1; testing offsets -1/0/+1 separates that numbering
convention from real drift instead of reporting it as a failure.

Usage:
  blender -b --factory-startup --python reimport_clip.py -- \
      <candidate.fbx> <master.blend> <action> <out.json>
"""
import bpy
import json
import math
import sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
FBX, MASTER, ACTION, OUT = argv[0], argv[1], argv[2], argv[3]

BONES = [
    "BAS_PUNCH_root", "BAS_PUNCH_body",
    "BAS_PUNCH_upperarm.L", "BAS_PUNCH_forearm.L", "BAS_PUNCH_hand.L",
    "BAS_PUNCH_upperarm.R", "BAS_PUNCH_forearm.R", "BAS_PUNCH_hand.R",
    "BAS_PUNCH_foot.L", "BAS_PUNCH_foot.R",
]


def wipe():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for collection in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights,
                       bpy.data.materials, bpy.data.armatures, bpy.data.actions,
                       bpy.data.objects):
        for block in list(collection):
            try:
                collection.remove(block)
            except Exception:
                pass


def sample(rig, frames):
    """Armature-space bone matrices for each frame."""
    out = {}
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        out[frame] = {
            name: rig.pose.bones[name].matrix.copy()
            for name in BONES if name in rig.pose.bones
        }
    return out


def activate(rig, action):
    if rig.animation_data is None:
        rig.animation_data_create()
    rig.animation_data.action = action
    for slot in getattr(action, "slots", []):
        try:
            rig.animation_data.action_slot = slot
            break
        except Exception:
            pass


# ------------------------------------------------------------------ master side
wipe()
bpy.ops.wm.open_mainfile(filepath=MASTER)
master_rig = bpy.data.objects["BAS_PUNCH_Rig"]
master_action = bpy.data.actions[ACTION]
activate(master_rig, master_action)
m_start = int(round(master_action.frame_range[0]))
m_end = int(round(master_action.frame_range[1]))
master_frames = list(range(m_start, m_end + 1))
master_poses = sample(master_rig, master_frames)
master_bones = sorted(b.name for b in master_rig.data.bones)
master_meshes = sorted(o.name for o in bpy.data.objects if o.type == "MESH")
master_tris = sum(
    sum(len(p.vertices) - 2 for p in bpy.data.objects[n].data.polygons)
    for n in master_meshes
)

# --------------------------------------------------------------- candidate side
wipe()
bpy.ops.import_scene.fbx(filepath=FBX)
cand_rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
cand_actions = [a.name for a in bpy.data.actions]
cand_action = bpy.data.actions[0]
activate(cand_rig, cand_action)
c_start = int(round(cand_action.frame_range[0]))
c_end = int(round(cand_action.frame_range[1]))
cand_frames = list(range(c_start, c_end + 1))
cand_poses = sample(cand_rig, cand_frames)
cand_bones = sorted(b.name for b in cand_rig.data.bones)
cand_meshes = sorted(o.name for o in bpy.data.objects if o.type == "MESH")
cand_tris = sum(
    sum(len(p.vertices) - 2 for p in bpy.data.objects[n].data.polygons)
    for n in cand_meshes
)
parasites = [o.name for o in bpy.data.objects
             if o.type not in ("MESH", "ARMATURE")]

# --------------------------------------------------------------------- compare
best = None
for offset in (0, 1, -1):
    pos_err = 0.0
    rot_err = 0.0
    matched = 0
    for frame in master_frames:
        target = frame + offset
        if target not in cand_poses:
            continue
        matched += 1
        for name in BONES:
            if name not in master_poses[frame] or name not in cand_poses[target]:
                continue
            a = master_poses[frame][name]
            b = cand_poses[target][name]
            pos_err = max(pos_err, (a.translation - b.translation).length)
            diff = a.to_quaternion().rotation_difference(b.to_quaternion())
            rot_err = max(rot_err, abs(math.degrees(diff.angle)))
    if matched == 0:
        continue
    entry = {"offset": offset, "matched_frames": matched,
             "max_position_delta_m": pos_err, "max_rotation_delta_deg": rot_err}
    if best is None or pos_err < best["max_position_delta_m"]:
        best = entry

report = {
    "candidate_fbx": FBX,
    "master_blend": MASTER,
    "action": ACTION,
    "master": {
        "frame_range": [m_start, m_end],
        "samples": len(master_frames),
        "bones": master_bones,
        "meshes": master_meshes,
        "triangles": master_tris,
    },
    "candidate": {
        "frame_range": [c_start, c_end],
        "samples": len(cand_frames),
        "actions": cand_actions,
        "bones": cand_bones,
        "meshes": cand_meshes,
        "triangles": cand_tris,
        "non_mesh_non_armature_objects": parasites,
    },
    "best_alignment": best,
    "checks": {
        "sample_count_equal": len(cand_frames) == len(master_frames),
        "bones_equal": cand_bones == master_bones,
        "triangles_equal": cand_tris == master_tris,
        "single_action": len(cand_actions) == 1,
        "no_parasites": not parasites,
        "pose_within_1e4_m": bool(best and best["max_position_delta_m"] < 1e-4),
        "rotation_within_0p05_deg": bool(best and best["max_rotation_delta_deg"] < 0.05),
    },
}
report["pass"] = all(report["checks"].values())

with open(OUT, "w") as handle:
    json.dump(report, handle, indent=1)
print("REIMPORT_DONE " + OUT)
print("REIMPORT_PASS " + str(report["pass"]))
print(json.dumps(report["checks"]))
