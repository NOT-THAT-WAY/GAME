"""Cumulative A/B lighting gate: six states at a hero frame."""
import bpy
import json
from pathlib import Path

P = globals().get("UNRECORDED_PARAMS", {})
TRIAL = Path(P.get("trial_dir", ".")).resolve()
HERO = int(P.get("hero_frame", 300))

scene = bpy.context.scene
scene.camera = bpy.data.objects["K3_FABLE_CAM"]
scene.render.image_settings.file_format = "PNG"
scene.render.resolution_x, scene.render.resolution_y = 640, 360
scene.frame_set(HERO)

rim = bpy.data.objects["K3_FABLE_LIGHT_RIM"]
fill = bpy.data.objects["K3_FABLE_LIGHT_FILL"]
bounce = bpy.data.objects["K3_FABLE_LIGHT_BOUNCE"]
notes = [o for o in bpy.data.objects if o.name.startswith("K3_FABLE_NOTE")]

states = [
    ("gate_00_screens_only", "les ecrans du template seuls : la source principale du film"),
    ("gate_01_rim", "rim froid arriere : decoupe la silhouette blanche sur la rampe"),
    ("gate_02_fill", "fill bas cote camera : empeche le corps de virer au noir"),
    ("gate_03_bounce", "rebond chaud faible : rend son volume au pearl"),
    ("gate_04_notes", "notes du Piano Roll declenchees par ses appuis (idee personnelle)"),
    ("gate_05_final", "etat final du plan"),
]

for obj in (rim, fill, bounce, *notes):
    obj.hide_render = True

out = TRIAL / "gates" / "lighting-gate"
out.mkdir(parents=True, exist_ok=True)
renders = []
for i, (name, purpose) in enumerate(states):
    if i == 1:
        rim.hide_render = False
    elif i == 2:
        fill.hide_render = False
    elif i == 3:
        bounce.hide_render = False
    elif i == 4:
        for n in notes:
            n.hide_render = False
    path = out / f"{name}.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    renders.append({"path": str(path.relative_to(TRIAL)), "layer": name,
                    "purpose": purpose, "frame": HERO})

base = json.loads((TRIAL / "gates" / "lighting-manifest.json").read_text(encoding="utf-8"))
base["hero_frame"] = HERO
base["renders"] = renders
(TRIAL / "gates" / "lighting-gate-manifest.json").write_text(
    json.dumps(base, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps({"renders": len(renders)}, ensure_ascii=False))
