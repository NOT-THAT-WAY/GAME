"""Drumboiii layered lighting for the slope run, with a 6-state A/B gate.

Order: retained environment (template as-is) -> oblique Sun raking the ramp
-> dominant backlight -> lime glimmer on the soles / leading edge -> opposite
magenta glimmer -> detail return on the torso. The moving lights ride a rig
empty that follows the runner. Renders the 6 cumulative states at the hero
frame and writes gates/lighting-gate-manifest.json. Saves the blend.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix, Vector

P = globals().get("UNRECORDED_PARAMS", {})
TRIAL = Path(P.get("trial_dir", ".")).resolve()
HERO_FRAME = int(P.get("hero_frame", 120))

U = Vector((0.0, 0.690377, 0.723449))
C = Vector((-1.0, 0.0, 0.0))
N = Vector((0.0, -0.723449, 0.690377))
O = Vector((0.0, 0.415, 1.755))

scene = bpy.context.scene
root = bpy.data.objects["USTUDIO_BOX_FLOAT_ROOT"]
work_col = bpy.data.collections["K3_PIANOROLL_SLOPE_RUN_FABLE_V001_WORK"]

plan = json.loads((TRIAL / "diagnostics" / "motion-plan.json").read_text(encoding="utf-8"))
frames = plan["frames"]

def slope_to_root(s, y, h):
    return O + U * s + C * y + N * h

# light rig follows the runner (smoothed pelvis, no bob)
h_raw = [fr["pelvis"]["h"] for fr in frames]
def smooth_h(i, win=13):
    a = max(0, i - win // 2)
    b = min(len(h_raw), i + win // 2 + 1)
    return sum(h_raw[a:b]) / (b - a)

rig = bpy.data.objects.new("K3_FABLE_LIGHT_RIG", None)
rig.empty_display_size = 0.1
work_col.objects.link(rig)
rig.parent = root
for i, fr in enumerate(frames):
    rig.location = slope_to_root(fr["pelvis"]["s"], 0.0, smooth_h(i))
    rig.keyframe_insert("location", frame=fr["frame"])

def new_light(name, kind, energy, color=(1.0, 1.0, 1.0), size=0.5, parent=rig):
    data = bpy.data.lights.new(name + "_DATA", kind)
    data.energy = energy
    data.color = color
    if kind == "AREA":
        data.size = size
        data.shadow_soft_size = size if hasattr(data, "shadow_soft_size") else None
    obj = bpy.data.objects.new(name, data)
    work_col.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    return obj

def aim(obj, direction):
    """Point the light's -Z along direction (root/rig local)."""
    d = Vector(direction).normalized()
    quat = d.to_track_quat("-Z", "Y")
    obj.rotation_euler = quat.to_euler()

# L1 — oblique Sun raking the ramp surface, casts the runner's shadow up-slope
sun_dir = (-U * 0.55 - N * 0.42 + C * 0.72).normalized()
sun = new_light("K3_FABLE_SUN", "SUN", 2.2, color=(1.0, 0.96, 0.90), parent=root)
sun.location = O + N * 2.0
aim(sun, sun_dir)

# L2 — dominant backlight: behind and above the runner, up-slope, aimed at his back
back = new_light("K3_FABLE_BACKLIGHT", "AREA", 110.0, color=(0.85, 0.92, 1.0), size=0.9)
back.location = U * 0.85 + N * 0.55 - C * 0.15
aim(back, (-U * 0.8 - N * 0.5 + C * 0.1))

# L3 — lime glimmer, low near the surface on the camera side, brushing soles and leading edge
lime = new_light("K3_FABLE_GLIMMER_LIME", "AREA", 14.0, color=(0.55, 1.0, 0.15), size=0.35)
lime.location = C * 0.55 - U * 0.28 + N * 0.10
aim(lime, (U * 0.35 - C * 0.75 - N * 0.12))

# L4 — magenta counter-glimmer from the opposite side (echoes the purple LEDs)
magenta = new_light("K3_FABLE_GLIMMER_MAGENTA", "AREA", 11.0, color=(1.0, 0.15, 0.65), size=0.35)
magenta.location = -C * 0.60 + U * 0.12 + N * 0.28
aim(magenta, (-U * 0.1 + C * 0.8 - N * 0.3))

# L5 — detail return on the torso, soft, from the camera side, slightly high
detail = new_light("K3_FABLE_DETAIL_TORSO", "AREA", 22.0, color=(1.0, 1.0, 1.0), size=0.6)
detail.location = C * 0.9 - U * 0.55 + N * 0.75
aim(detail, (U * 0.5 - C * 0.62 - N * 0.55))

layers = [
    ("gate_00_env_retenu", None, "environnement du template seul : ecrans emissifs et lampes existantes"),
    ("gate_01_sun_oblique", sun, "Sun oblique rasant qui dessine la surface et projette l'ombre du coureur sur la pente"),
    ("gate_02_backlight", back, "Area arriere dominant : separation du contour pearl sur la rampe"),
    ("gate_03_glimmer_lime", lime, "glimmer lime sur les semelles et le bord montant"),
    ("gate_04_glimmer_magenta", magenta, "glimmer magenta oppose, echo des LEDs violettes"),
    ("gate_05_detail_torse", detail, "retour de detail doux sur le torse"),
]

for _, light, _ in layers:
    if light is not None:
        light.hide_render = True
        light.hide_viewport = True

gate_dir = TRIAL / "gates" / "lighting-gate"
gate_dir.mkdir(parents=True, exist_ok=True)
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
    "order": "env retenu -> sun oblique -> backlight dominant -> glimmer lime -> glimmer magenta -> retour torse",
    "energy_ratios_vs_backlight": {
        "K3_FABLE_BACKLIGHT": 1.0,
        "K3_FABLE_SUN": "2.2 W/m2 (soleil, echelle differente)",
        "K3_FABLE_GLIMMER_LIME": round(14.0 / 110.0, 3),
        "K3_FABLE_GLIMMER_MAGENTA": round(11.0 / 110.0, 3),
        "K3_FABLE_DETAIL_TORSO": round(22.0 / 110.0, 3),
    },
    "sole_pulse_rule": "l'emission lime des semelles est keyframee uniquement pendant les contacts ; aucune emission permanente sous les pieds",
    "renders": renders,
}
(TRIAL / "gates" / "lighting-gate-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

bpy.ops.wm.save_as_mainfile(filepath=str(TRIAL / "scene" / "trial.blend"))
print("UNRECORDED_RESULT=" + json.dumps({"renders": len(renders), "saved": True}, ensure_ascii=False))
