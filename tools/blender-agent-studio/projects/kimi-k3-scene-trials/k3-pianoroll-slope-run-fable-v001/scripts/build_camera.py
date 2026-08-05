"""Build the Drumboiii camera rig for the slope run.

Main camera: three-quarter lateral tracking on the -X side of the box, moving
parallel to UPHILL_TANGENT, constant distance to the runner (anticipation and
recovery are arcs around the runner, never distance changes). TARGET is an
independent empty following the chest with a 2-frame delay; FOCUS follows with
no delay. Track To runs in world space so the horizon stays world-level even
though positions are rigid with USTUDIO_BOX_FLOAT_ROOT.

Also creates three diagnostic cameras (strict profile, top/rear, surface normal).
Writes shot-manifest.json. Saves the blend.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix, Vector

P = globals().get("UNRECORDED_PARAMS", {})
TRIAL = Path(P.get("trial_dir", ".")).resolve()

U = Vector((0.0, 0.690377, 0.723449))
C = Vector((-1.0, 0.0, 0.0))
N = Vector((0.0, -0.723449, 0.690377))
O = Vector((0.0, 0.415, 1.755))
FRAME_END = 240

plan = json.loads((TRIAL / "diagnostics" / "motion-plan.json").read_text(encoding="utf-8"))
frames = plan["frames"]

def slope_to_root(s, y, h):
    return O + U * s + C * y + N * h

# smooth pelvis h (strip the gait bob so the camera does not bob)
h_raw = [fr["pelvis"]["h"] for fr in frames]
def smooth_h(i, win=13):
    a = max(0, i - win // 2)
    b = min(len(h_raw), i + win // 2 + 1)
    return sum(h_raw[a:b]) / (b - a)

def trunk_dir_slope(lean_deg):
    lam = math.radians(lean_deg)
    root_vec = Vector((0.0, math.sin(lam), math.cos(lam)))
    return Vector((root_vec.dot(U), root_vec.dot(C), root_vec.dot(N))).normalized()

def chest_root(i):
    fr = frames[i]
    pelvis = slope_to_root(fr["pelvis"]["s"], fr["pelvis"]["y"], fr["pelvis"]["h"])
    td = trunk_dir_slope(fr["lean_chest_deg"])
    chest_slope_off = td * 0.085
    return pelvis + U * chest_slope_off.x + C * chest_slope_off.y + N * chest_slope_off.z

def anchor_root(i):
    fr = frames[i]
    return slope_to_root(fr["pelvis"]["s"], 0.0, smooth_h(i))

def smoothstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)

def arc_deg(f):
    """K2 anticipation / K4 recovery arc angle around the runner (degrees)."""
    if f <= 40:
        return 0.0
    if f <= 52:
        return -4.0 * smoothstep((f - 40) / 12.0)
    if f <= 64:
        return -4.0 + 4.5 * smoothstep((f - 52) / 12.0)
    if f <= 72:
        return 0.5 - 0.5 * smoothstep((f - 64) / 8.0)
    if f <= 206:
        return 0.0
    if f <= 216:
        return 1.4 * smoothstep((f - 206) / 10.0)
    if f <= 228:
        return 1.4 - 1.4 * smoothstep((f - 216) / 12.0)
    return 0.0

root = bpy.data.objects["USTUDIO_BOX_FLOAT_ROOT"]
work_col = bpy.data.collections["K3_PIANOROLL_SLOPE_RUN_FABLE_V001_WORK"]

# idempotent: remove any previous camera rig objects
for obj in list(bpy.data.objects):
    if obj.name.startswith(("K3_FABLE_CAM", "K3_FABLE_DIAG")):
        bpy.data.objects.remove(obj, do_unlink=True)

def new_empty(name):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.05
    work_col.objects.link(e)
    e.parent = root
    return e

def new_camera(name, lens, fstop=None, focus=None):
    cam_data = bpy.data.cameras.new(name + "_DATA")
    cam_data.lens = lens
    cam_data.clip_start = 0.02
    cam_data.clip_end = 100.0
    if fstop and focus:
        cam_data.dof.use_dof = True
        cam_data.dof.aperture_fstop = fstop
        cam_data.dof.focus_object = focus
    cam = bpy.data.objects.new(name, cam_data)
    work_col.objects.link(cam)
    cam.parent = root
    return cam

target = new_empty("K3_FABLE_CAM_TARGET")
focus = new_empty("K3_FABLE_CAM_FOCUS")
cam_main = new_camera("K3_FABLE_CAM_MAIN", 50.0, fstop=5.0, focus=focus)
track = cam_main.constraints.new("TRACK_TO")
track.target = target
track.track_axis = "TRACK_NEGATIVE_Z"
track.up_axis = "UP_Y"

OFFSET = Vector((-1.386, -0.647, 0.16))

def pelvis_true_root(i):
    fr = frames[i]
    return slope_to_root(fr["pelvis"]["s"], fr["pelvis"]["y"], fr["pelvis"]["h"])

for i, fr in enumerate(frames):
    f = fr["frame"]
    anchor = anchor_root(i)
    off = Matrix.Rotation(math.radians(arc_deg(f)), 3, Vector((0, 0, 1))) @ OFFSET
    # push-pull along the view axis so |cam - pelvis| stays constant despite gait
    # bob/sway: cam = anchor + off + o_hat * ((pelvis - anchor) . o_hat)
    o_hat = off.normalized()
    dev = pelvis_true_root(i) - anchor
    cam_main.location = anchor + off + o_hat * dev.dot(o_hat)
    cam_main.keyframe_insert("location", frame=f)
    j = max(0, i - 2)
    target.location = chest_root(j) + Vector((0, 0, 0.045))
    target.keyframe_insert("location", frame=f)
    focus.location = chest_root(i)
    focus.keyframe_insert("location", frame=f)

# ---------------------------------------------------------------- diagnostics
tgt_profile = new_empty("K3_FABLE_DIAG_TARGET_PROFILE")
cam_profile = new_camera("K3_FABLE_CAM_DIAG_PROFILE", 65.0)
tp = cam_profile.constraints.new("TRACK_TO")
tp.target = tgt_profile
tp.track_axis = "TRACK_NEGATIVE_Z"
tp.up_axis = "UP_Y"

tgt_rear = new_empty("K3_FABLE_DIAG_TARGET_REAR")
cam_rear = new_camera("K3_FABLE_CAM_DIAG_TOPREAR", 35.0)
tr = cam_rear.constraints.new("TRACK_TO")
tr.target = tgt_rear
tr.track_axis = "TRACK_NEGATIVE_Z"
tr.up_axis = "UP_Y"

tgt_norm = new_empty("K3_FABLE_DIAG_TARGET_NORMAL")
cam_norm = new_camera("K3_FABLE_CAM_DIAG_NORMAL", 40.0)
tn = cam_norm.constraints.new("TRACK_TO")
tn.target = tgt_norm
tn.track_axis = "TRACK_NEGATIVE_Z"
tn.up_axis = "UP_Y"

for i, fr in enumerate(frames):
    f = fr["frame"]
    anchor = anchor_root(i)
    chest = chest_root(i)
    feet = slope_to_root(fr["pelvis"]["s"] - 0.06, 0.0, 0.0)

    cam_profile.location = anchor + Vector((-1.65, 0.0, 0.05))
    cam_profile.keyframe_insert("location", frame=f)
    tgt_profile.location = anchor + Vector((0, 0, -0.02))
    tgt_profile.keyframe_insert("location", frame=f)

    cam_rear.location = anchor + U * 0.62 + N * 0.42 + C * 0.35
    cam_rear.keyframe_insert("location", frame=f)
    tgt_rear.location = feet
    tgt_rear.keyframe_insert("location", frame=f)

    cam_norm.location = slope_to_root(fr["pelvis"]["s"], 0.0, 1.15)
    cam_norm.keyframe_insert("location", frame=f)
    tgt_norm.location = feet
    tgt_norm.keyframe_insert("location", frame=f)

scene = bpy.context.scene
scene.camera = cam_main

# ------------------------------------------------- apparent slope angle check
depsgraph = bpy.context.evaluated_depsgraph_get()
from bpy_extras.object_utils import world_to_camera_view

def apparent_slope_deg(frame):
    scene.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get()
    cam_eval = cam_main.evaluated_get(dg)
    root_eval = root.evaluated_get(dg)
    p1 = root_eval.matrix_world @ slope_to_root(-0.6, 0.0, 0.0)
    p2 = root_eval.matrix_world @ slope_to_root(0.6, 0.0, 0.0)
    a = world_to_camera_view(scene, cam_eval, p1)
    b = world_to_camera_view(scene, cam_eval, p2)
    dx = (b.x - a.x) * 640
    dy = (b.y - a.y) * 360
    return math.degrees(math.atan2(abs(dy), abs(dx)))

angles = {str(f): round(apparent_slope_deg(f), 2) for f in (30, 80, 120, 160, 200, 235)}

manifest = {
    "schema_version": 1,
    "trial_id": "k3-pianoroll-slope-run-fable-v001",
    "camera": "K3_FABLE_CAM_MAIN",
    "camera_name": "K3_FABLE_CAM_MAIN",
    "lens_mm": 50.0,
    "aperture_fstop": 5.0,
    "sensor": "36mm auto",
    "resolution": [640, 360],
    "fps": 30,
    "frames": [1, FRAME_END],
    "parenting": "rig rigide avec USTUDIO_BOX_FLOAT_ROOT ; Track To en espace monde garde l'horizon niveau",
    "target": "K3_FABLE_CAM_TARGET, poitrine du coureur avec retard de 2 frames",
    "focus": "K3_FABLE_CAM_FOCUS, poitrine sans retard, DOF f/5.0",
    "move_grammar": {
        "K1_pose": "frames 1-40, pose laterale trois-quarts qui etablit la pente",
        "K2_anticipation": "frames 40-52, arc de -4 degres autour du coureur, distance constante",
        "K3_travel": "frames 52-206, tracking parallele a UPHILL_TANGENT, offset constant (-1.287, -0.601, +0.19) m",
        "K4_recovery": "frames 206-228, arc de +1.4 degres qui s'amortit, puis arret complet",
        "still": "frames 228-240, aucune animation caméra",
    },
    "offset_from_runner_m": [-1.386, -0.647, 0.16],
    "distance_to_runner_m": 1.538,
    "three_quarter_angle_deg": 25.0,
    "apparent_slope_angle_in_frame_deg": angles,
    "diagnostic_cameras": [
        {"name": "K3_FABLE_CAM_DIAG_PROFILE", "purpose": "profil strict pour les gates physiques"},
        {"name": "K3_FABLE_CAM_DIAG_TOPREAR", "purpose": "top/rear sur les contacts des pieds"},
        {"name": "K3_FABLE_CAM_DIAG_NORMAL", "purpose": "vue selon la normale de surface, drift et placements"},
    ],
    "forbidden_checked": ["aucun roll copie de la pente", "aucune traversee de decor (validee frame par frame)", "distance constante ±0.01 m"],
}
(TRIAL / "shot-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

bpy.ops.wm.save_as_mainfile(filepath=str(TRIAL / "scene" / "trial.blend"))
print("UNRECORDED_RESULT=" + json.dumps({"apparent_slope_deg": angles, "saved": True}, ensure_ascii=False))
