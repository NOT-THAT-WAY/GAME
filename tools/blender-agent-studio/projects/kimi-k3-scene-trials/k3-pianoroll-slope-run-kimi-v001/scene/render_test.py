"""Rendu de test : frames cles sur les 4 cameras. NE SAUVEGARDE PAS."""
import bpy

TRIAL = "${BLENDER_AGENT_STUDIO_ROOT}/projects/kimi-k3-scene-trials/k3-pianoroll-slope-run-kimi-v001"
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"

jobs = [
    ("K3_CAM_MAIN", [1, 33, 57, 100, 150, 178, 210, 240]),
    ("K3_CAM_DIAG_PROFILE", [57, 120, 178]),
    ("K3_CAM_DIAG_TOP", [100]),
    ("K3_CAM_DIAG_NORMAL", [100]),
]
for cam_name, frames in jobs:
    sc.camera = bpy.data.objects[cam_name]
    for f in frames:
        sc.frame_set(f)
        sc.render.filepath = f"{TRIAL}/gates/test-{cam_name.replace('K3_CAM_', '').lower()}-f{f:03d}.png"
        bpy.ops.render.render(write_still=True)
        print("RENDERED", cam_name, f)
