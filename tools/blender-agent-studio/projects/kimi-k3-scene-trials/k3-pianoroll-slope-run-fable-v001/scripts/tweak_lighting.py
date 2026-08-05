"""Lighting iteration 1: tame the backlight specular wash on the glossy ramp.

Single family touched (lighting). Re-renders the 6 cumulative gate states and
rewrites the manifest. Saves the blend.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector

P = globals().get("UNRECORDED_PARAMS", {})
TRIAL = Path(P.get("trial_dir", ".")).resolve()
HERO_FRAME = int(P.get("hero_frame", 120))

U = Vector((0.0, 0.690377, 0.723449))
C = Vector((-1.0, 0.0, 0.0))
N = Vector((0.0, -0.723449, 0.690377))

scene = bpy.context.scene

def aim(obj, direction):
    obj.rotation_euler = Vector(direction).normalized().to_track_quat("-Z", "Y").to_euler()

back = bpy.data.objects["K3_FABLE_BACKLIGHT"]
back.data.energy = 58.0
back.location = U * 1.15 + N * 0.85 - C * 0.12
aim(back, (-U * 0.62 - N * 0.78 + C * 0.08))
if hasattr(back.data, "spread"):
    back.data.spread = math.radians(70)

detail = bpy.data.objects["K3_FABLE_DETAIL_TORSO"]
detail.data.energy = 13.0
detail.data.size = 0.5
if hasattr(detail.data, "spread"):
    detail.data.spread = math.radians(90)

lime = bpy.data.objects["K3_FABLE_GLIMMER_LIME"]
magenta = bpy.data.objects["K3_FABLE_GLIMMER_MAGENTA"]
sun = bpy.data.objects["K3_FABLE_SUN"]

layers = [
    ("gate_00_env_retenu", None, "environnement du template seul : ecrans emissifs et lampes existantes"),
    ("gate_01_sun_oblique", sun, "Sun oblique rasant qui dessine la surface et projette l'ombre du coureur sur la pente"),
    ("gate_02_backlight", back, "Area arriere dominant remonte et resserre : contour sans lavage speculaire"),
    ("gate_03_glimmer_lime", lime, "glimmer lime sur les semelles et le bord montant"),
    ("gate_04_glimmer_magenta", magenta, "glimmer magenta oppose, echo des LEDs violettes"),
    ("gate_05_detail_torse", detail, "retour de detail doux sur le torse"),
]

for _, light, _ in layers:
    if light is not None:
        light.hide_render = True
        light.hide_viewport = True

gate_dir = TRIAL / "gates" / "lighting-gate"
scene.camera = bpy.data.objects["K3_FABLE_CAM_MAIN"]
scene.render.image_settings.file_format = "PNG"
if hasattr(scene.eevee, "taa_render_samples"):
    scene.eevee.taa_render_samples = 24
scene.frame_set(HERO_FRAME)

renders = []
for name, light, purpose in layers:
    if light is not None:
        light.hide_render = False
        light.hide_viewport = False
    path = gate_dir / f"{name}.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    renders.append({
        "path": str(path.relative_to(TRIAL)),
        "layer": name,
        "light": light.name if light else "template",
        "purpose": purpose,
        "frame": HERO_FRAME,
    })

manifest = {
    "schema_version": 1,
    "trial_id": "k3-pianoroll-slope-run-fable-v001",
    "style_source": "knowledge/tutorials/drumboii-lighting-tutorial-2026-07-20/analysis.json",
    "hero_frame": HERO_FRAME,
    "iteration": "lighting-01 : backlight 110W->58W, remonte (+N 0.85), spread 70deg — suppression du lavage speculaire coin amont",
    "order": "env retenu -> sun oblique -> backlight dominant -> glimmer lime -> glimmer magenta -> retour torse",
    "energy_ratios_vs_backlight": {
        "K3_FABLE_BACKLIGHT": 1.0,
        "K3_FABLE_SUN": "2.2 W/m2 (soleil, echelle differente)",
        "K3_FABLE_GLIMMER_LIME": round(14.0 / 58.0, 3),
        "K3_FABLE_GLIMMER_MAGENTA": round(11.0 / 58.0, 3),
        "K3_FABLE_DETAIL_TORSO": round(13.0 / 58.0, 3),
    },
    "sole_pulse_rule": "l'emission lime des semelles est keyframee uniquement pendant les contacts ; aucune emission permanente sous les pieds",
    "renders": renders,
}
(TRIAL / "gates" / "lighting-gate-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

bpy.ops.wm.save_as_mainfile(filepath=str(TRIAL / "scene" / "trial.blend"))
print("UNRECORDED_RESULT=" + json.dumps({"renders": len(renders), "saved": True}, ensure_ascii=False))
