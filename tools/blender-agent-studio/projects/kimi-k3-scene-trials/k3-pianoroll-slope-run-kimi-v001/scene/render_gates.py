"""Gates : cameras diagnostiques aux changements de pied + gate lumiere A/B.

1) DIAG_PROFILE / DIAG_TOP / DIAG_NORMAL aux 14 frames gate + frames de strikes.
2) Gate lumiere cumulative a f100 : monde -> +sun -> +backlight -> +lime -> +magenta
   -> +retour torse, avec manifest JSON.
Ne sauvegarde pas.
"""
import bpy
import json

TRIAL = "${BLENDER_AGENT_STUDIO_ROOT}/projects/kimi-k3-scene-trials/k3-pianoroll-slope-run-kimi-v001"
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"

GATE_FRAMES = [1, 17, 33, 49, 57, 81, 106, 130, 154, 178, 192, 203, 224, 240]
STRIKE_FRAMES = [57, 70, 82, 94, 106, 118, 130, 142, 154, 166, 178, 201]

for cam_name, frames in [("K3_CAM_DIAG_PROFILE", GATE_FRAMES),
                         ("K3_CAM_DIAG_TOP", STRIKE_FRAMES),
                         ("K3_CAM_DIAG_NORMAL", STRIKE_FRAMES)]:
    sc.camera = bpy.data.objects[cam_name]
    tag = cam_name.replace("K3_CAM_DIAG_", "").lower()
    for f in frames:
        sc.frame_set(f)
        sc.render.filepath = f"{TRIAL}/gates/diag-{tag}-f{f:03d}.png"
        bpy.ops.render.render(write_still=True)
print("DIAG_GATES_DONE")

# ---------------------------------------------------------------- gate lumiere
LIGHTS = ["K3_LIGHT_SUN", "K3_LIGHT_BACKLIGHT", "K3_LIGHT_GLIMMER_LIME",
          "K3_LIGHT_GLIMMER_MAGENTA", "K3_LIGHT_TORSO_RETURN"]
sc.camera = bpy.data.objects["K3_CAM_MAIN"]
sc.frame_set(100)
manifest = {"frame": 100, "camera": "K3_CAM_MAIN", "layers": []}
for n, ob in ((name, bpy.data.objects[name]) for name in LIGHTS):
    ob.hide_render = True
for i, name in enumerate(["00_world_only"] + LIGHTS):
    if i > 0:
        bpy.data.objects[name].hide_render = False
    tag = f"{i:02d}_{name.replace('K3_LIGHT_', '').lower()}" if i > 0 else name
    sc.render.filepath = f"{TRIAL}/gates/lighting-{tag}.png"
    bpy.ops.render.render(write_still=True)
    manifest["layers"].append({"step": tag, "enabled": LIGHTS[:i]})
for name in LIGHTS:
    bpy.data.objects[name].hide_render = False
with open(TRIAL + "/gates/lighting-gate-manifest.json", "w") as fp:
    json.dump(manifest, fp, indent=2, ensure_ascii=False)
print("LIGHTING_GATE_DONE")
