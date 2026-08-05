"""One continuous shot: intimate and low, then pulling back, rising and widening.

The camera is parented to USTUDIO_BOX_FLOAT_ROOT so the framing stays stable
while the box drifts. It tracks an independent TARGET that follows the mascot
with a short lag and, at the end, lifts toward the top of the screens so the
audience follows his gaze. Focal length is animated 38 → 17 mm: the pull-back
and the widening happen together, which is what turns "intimate" into "vast".
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector

P = globals().get("UNRECORDED_PARAMS", {})
TRIAL = Path(P.get("trial_dir", ".")).resolve()
FRAME_END = 360

scene = bpy.context.scene
root = bpy.data.objects["USTUDIO_BOX_FLOAT_ROOT"]
arm = bpy.data.objects["K3_FABLE_MASCOT"]
work = bpy.data.collections["K3_EDGE_RISE_REVEAL_FABLE_V001_WORK"]

for name in ("K3_FABLE_CAM", "K3_FABLE_CAM_TARGET", "K3_FABLE_CAM_FOCUS"):
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)

# ---- sample where the character actually is, from the baked animation
SCALE = 0.424
chest = {}
for f in range(1, FRAME_END + 1):
    scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    pb = arm.evaluated_get(dg).pose.bones["CHEST"]
    local = pb.matrix.translation * SCALE       # armature units → box-local meters
    chest[f] = Vector((local.x, local.y, local.z))

def smoothed_chest(f, win=9):
    lo, hi = max(1, f - win // 2), min(FRAME_END, f + win // 2)
    acc = Vector()
    for k in range(lo, hi + 1):
        acc += chest[k]
    return acc / (hi - lo + 1)

# ---- camera path: keyed poses, smooth Bezier between them
KEYS = [
    (1,   Vector((-1.95, -1.62, 0.95)), 38.0),
    (57,  Vector((-1.98, -1.69, 0.99)), 37.0),
    # he is at his tallest right here (end of the sit-to-stand): give the frame
    # a little more room or his head clips the top edge
    (106, Vector((-1.90, -2.02, 1.42)), 28.5),
    (160, Vector((-1.46, -2.16, 1.85)), 26.0),
    (210, Vector((-1.00, -2.36, 2.25)), 22.0),
    (251, Vector((-0.62, -2.52, 2.56)), 19.5),
    (299, Vector((-0.35, -2.62, 2.78)), 17.8),
    (330, Vector((-0.25, -2.65, 2.85)), 17.1),
    (360, Vector((-0.25, -2.65, 2.85)), 17.0),
]

cam_data = bpy.data.cameras.new("K3_FABLE_CAM_DATA")
cam_data.clip_start = 0.02
cam_data.clip_end = 120.0
cam_data.dof.use_dof = True
cam_data.dof.aperture_fstop = 4.0
cam = bpy.data.objects.new("K3_FABLE_CAM", cam_data)
work.objects.link(cam)
cam.parent = root

target = bpy.data.objects.new("K3_FABLE_CAM_TARGET", None)
target.empty_display_size = 0.08
work.objects.link(target)
target.parent = root

focus = bpy.data.objects.new("K3_FABLE_CAM_FOCUS", None)
focus.empty_display_size = 0.05
work.objects.link(focus)
focus.parent = root
cam_data.dof.focus_object = focus

track = cam.constraints.new("TRACK_TO")
track.target = target
track.track_axis = "TRACK_NEGATIVE_Z"
track.up_axis = "UP_Y"

for f, pos, lens in KEYS:
    cam.location = pos
    cam.keyframe_insert("location", frame=f)
    cam_data.lens = lens
    cam_data.keyframe_insert("lens", frame=f)

# ---- target: follows the chest with a 3-frame lag, then lifts to the screens
LOOKUP_START, LOOKUP_END = 299.4, 345.0
for f in range(1, FRAME_END + 1):
    lag = max(1, f - 3)
    aim = smoothed_chest(lag) + Vector((0, 0, 0.06))
    if f > LOOKUP_START:
        q = min(1.0, (f - LOOKUP_START) / (LOOKUP_END - LOOKUP_START))
        q = q * q * (3 - 2 * q)
        aim = aim.lerp(Vector((0.02, 1.10, 3.15)), 0.62 * q)
    target.location = aim
    target.keyframe_insert("location", frame=f)
    focus.location = smoothed_chest(f, win=5)
    focus.keyframe_insert("location", frame=f)

# Blender's default for new keys is already BEZIER / AUTO_CLAMPED, which is the
# easing this move wants (slow build, no overshoot, dead stop at the end).
scene.camera = cam
scene.frame_start, scene.frame_end = 1, FRAME_END
scene.render.resolution_x, scene.render.resolution_y = 640, 360
scene.render.fps = 30

# ---- clearance + framing check over the whole shot
box = json.loads((TRIAL / "diagnostics" / "box-analysis.json").read_text(encoding="utf-8"))
bounds = box["bounds_local_root"]
SKIP = {"USTUDIO_GROUND", "USTUDIO_PLAYHEAD_FLOOR", "USTUDIO_PIANO_ROLL_FLOOR"}

def aabb_distance(p, lo, hi):
    dx = max(lo[0] - p.x, 0.0, p.x - hi[0])
    dy = max(lo[1] - p.y, 0.0, p.y - hi[1])
    dz = max(lo[2] - p.z, 0.0, p.z - hi[2])
    return math.sqrt(dx * dx + dy * dy + dz * dz)

from bpy_extras.object_utils import world_to_camera_view

report = {"frames": [], "min_clearance": 9.9, "min_clearance_frame": None,
          "min_subject_height_fraction": 9.9, "subject_min_frame": None,
          "subject_out_of_frame": []}
body = bpy.data.objects["K3_MECHA_BODY"]
head_obj = bpy.data.objects["K3_MECHA_HEAD"]
for f in range(1, FRAME_END + 1):
    scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    cam_e = cam.evaluated_get(dg)
    cam_local = root.matrix_world.inverted() @ cam_e.matrix_world.translation
    clear = min(aabb_distance(cam_local, bounds[n][0], bounds[n][1])
                for n in bounds if n not in SKIP)
    # subject size on screen: lowest foot to top of head
    pts = []
    for obj in (body, head_obj):
        ev = obj.evaluated_get(dg)
        mesh = ev.to_mesh()
        pts.extend([ev.matrix_world @ v.co for v in mesh.vertices])
        ev.to_mesh_clear()
    uvs = [world_to_camera_view(scene, cam_e, p) for p in pts]
    ys = [uv.y for uv in uvs]
    xs = [uv.x for uv in uvs]
    height_fraction = max(ys) - min(ys)
    inside = min(xs) > -0.02 and max(xs) < 1.02 and min(ys) > -0.02 and max(ys) < 1.02
    if not inside:
        report["subject_out_of_frame"].append(f)
    if clear < report["min_clearance"]:
        report["min_clearance"], report["min_clearance_frame"] = clear, f
    if height_fraction < report["min_subject_height_fraction"]:
        report["min_subject_height_fraction"], report["subject_min_frame"] = height_fraction, f
    if f % 20 == 0 or f in (1, 360):
        report["frames"].append({"frame": f, "clearance_m": round(clear, 4),
                                 "subject_height_fraction": round(height_fraction, 4),
                                 "lens_mm": round(cam_data.lens, 2)})

report["min_clearance"] = round(report["min_clearance"], 4)
report["min_subject_height_fraction"] = round(report["min_subject_height_fraction"], 4)

manifest = {
    "schema_version": 1,
    "trial_id": "k3-edge-rise-reveal-fable-v001",
    "camera": "K3_FABLE_CAM",
    "camera_name": "K3_FABLE_CAM",
    "single_continuous_shot": True,
    "cuts": 0,
    "parenting": "enfant de USTUDIO_BOX_FLOAT_ROOT (cadrage stable pendant la derive de la boite)",
    "lens_mm_range": [17.0, 38.0],
    "aperture_fstop": 4.0,
    "target": "K3_FABLE_CAM_TARGET, poitrine lissee avec 3 frames de retard, puis montee vers le haut des ecrans",
    "focus": "K3_FABLE_CAM_FOCUS, poitrine sans retard",
    "keys": [{"frame": f, "location": [round(c, 3) for c in pos], "lens": lens} for f, pos, lens in KEYS],
    "framing_check": report,
}
(TRIAL / "shot-manifest.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

bpy.ops.wm.save_as_mainfile(filepath=str(TRIAL / "scene" / "trial.blend"))
print("UNRECORDED_RESULT=" + json.dumps({
    "min_clearance_m": report["min_clearance"], "at_frame": report["min_clearance_frame"],
    "min_subject_height_fraction": report["min_subject_height_fraction"],
    "at_frame_subject": report["subject_min_frame"],
    "out_of_frame_count": len(report["subject_out_of_frame"]),
    "saved": True}, ensure_ascii=False))
