"""Audit technique de la scene d'essai + shot-manifest.

Utilise le script versionne workflows/scripts/deep_audit_scene.py, qui ecrit
diagnostics/scene-audit.json.

  blender -b scene/trial.blend --python run_audit.py
"""

import json
import os

import bpy

TRIAL_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(TRIAL_DIR, "..", "..", ".."))
SCRIPT = os.path.join(REPO, "workflows", "scripts", "deep_audit_scene.py")
DIAG = os.path.join(TRIAL_DIR, "diagnostics")

g = {
    "__name__": "__main__",
    "UNRECORDED_PARAMS": {
        "output_dir": DIAG,
        "include_nodes": True,
        "include_geometry_checks": True,
    },
}
with open(SCRIPT) as fh:
    exec(compile(fh.read(), SCRIPT, "exec"), g)

scene = bpy.context.scene
cam = scene.camera
poses = []
for f in (1, 26, 120, 144):
    scene.frame_set(f)
    poses.append({
        "frame": f,
        "role": {1: "K1_pose", 26: "K2_anticipation",
                 120: "K3_travel", 144: "K4_recovery"}[f],
        "camera_location_m": [round(v, 4) for v in cam.matrix_world.translation],
    })
scene.frame_set(scene.frame_start)

shot = {
    "schema_version": 1,
    "trial_id": "k3-pulsed-bench-demo-v001",
    "camera": cam.name,
    "camera_name": cam.name,
    "target": "K3_PULSED_BENCH_V001_TARGET",
    "focus": "K3_PULSED_BENCH_V001_FOCUS",
    "lens_mm": round(cam.data.lens, 2),
    "dof": {
        "enabled": bool(cam.data.dof.use_dof),
        "focus_object": cam.data.dof.focus_object.name if cam.data.dof.focus_object else None,
        "f_stop": round(cam.data.dof.aperture_fstop, 2),
    },
    "frame_start": scene.frame_start,
    "frame_end": scene.frame_end,
    "fps": scene.render.fps,
    "duration_seconds": round((scene.frame_end - scene.frame_start + 1) / scene.render.fps, 3),
    "resolution": [scene.render.resolution_x, scene.render.resolution_y],
    "engine": scene.render.engine,
    "samples": scene.cycles.samples,
    "view_transform": scene.view_settings.view_transform,
    "camera_poses": poses,
    "move": "arc unique montant, 4 poses Drumboiii : pose, anticipation opposee, travel, recovery",
    "outputs": {
        "preview": "renders/preview.mp4",
        "contact_sheet": "gates/contact-sheet.jpg",
        "lighting_gate": "gates/lighting-gate-manifest.json",
        "physical_validation": "diagnostics/physical-validation.json",
    },
}
path = os.path.join(TRIAL_DIR, "shot-manifest.json")
with open(path, "w") as fh:
    json.dump(shot, fh, ensure_ascii=False, indent=2)
print(f"[shot] -> {path}")
print(f"[audit] -> {os.path.join(DIAG, 'scene-audit.json')}")
