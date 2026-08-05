"""rig_flroom_hover.py — lévitation paramétrique du Pulsed dans FLROOM.

Le device flotte AU MILIEU de la boîte (avancé dans la profondeur, pas collé au fond)
et bouge en continu : bob vertical + dérives latérales + yaw/pitch/roll doux, comme
s'il réagissait aux paramètres en temps réel. Contrôles NON animés (device montré,
pas opéré).

TOUS les réglages sont dans PARAMS. Cycles = entiers → boucle parfaite sur la durée.
Relancer le script réécrit l'animation (idempotent).
"""
import bpy, json, math

PARAMS = dict(
    seconds=10, fps=24,
    # ⚠ l'origine du mesh Pulsed est au BAS du device : +6.3 BU (scale 1.3) jusqu'au centre réel.
    # base z = centre voulu (10.5) - 6.3 = 4.2 → centre géométrique du device à 10.5.
    base=(0.0, -10.0, 4.2),   # X centre, Y à ~2.5 BU du plan de sortie, Z compensé origine-bas
    bob_amp=0.9,  bob_cycles=2,    # respiration verticale (BU)
    swx_amp=0.5,  swx_cycles=1,    # dérive latérale X (BU)
    swy_amp=0.35, swy_cycles=2,    # dérive profondeur Y (BU)
    yaw_amp=7.0,  yaw_cycles=1,    # lacet (°, rot Z)
    pitch_amp=3.5, pitch_cycles=2, # tangage (°, rot X)
    roll_amp=2.0, roll_cycles=1,   # roulis (°, rot Y)
)
PHASE = dict(bob=0.0, swx=0.25, swy=0.6, yaw=0.5, pitch=0.15, roll=0.75)  # tours (0-1)

P = PARAMS
sc = bpy.data.scenes["FLROOM"]
bpy.context.window.scene = sc
frames = P["seconds"] * P["fps"]
sc.frame_start, sc.frame_end = 1, frames
sc.render.fps = P["fps"]

piv = bpy.data.objects["flroom_device_pivot"]
piv.animation_data_clear()
piv.rotation_mode = 'XYZ'

def osc(amp, cycles, phase, f):
    return amp * math.sin(2*math.pi * (cycles * (f-1)/frames + phase))

for f in range(1, frames+1):
    piv.location = (P["base"][0] + osc(P["swx_amp"], P["swx_cycles"], PHASE["swx"], f),
                    P["base"][1] + osc(P["swy_amp"], P["swy_cycles"], PHASE["swy"], f),
                    P["base"][2] + osc(P["bob_amp"], P["bob_cycles"], PHASE["bob"], f))
    piv.rotation_euler = (math.radians(osc(P["pitch_amp"], P["pitch_cycles"], PHASE["pitch"], f)),
                          math.radians(osc(P["roll_amp"], P["roll_cycles"], PHASE["roll"], f)),
                          math.radians(osc(P["yaw_amp"], P["yaw_cycles"], PHASE["yaw"], f)))
    piv.keyframe_insert("location", frame=f)
    piv.keyframe_insert("rotation_euler", frame=f)

# sortie séquence PNG (ce build Blender n'a pas de sortie FFMPEG) — assemblage ffmpeg ensuite
OUT = "${LEGACY_VISUAL_AI_HUB_ROOT}/unrecorded-marketing/blender-choreography/runs/flroom-scene-2026-07-14/"
sc.camera = bpy.data.objects["flroom_cam_front"]
sc.render.image_settings.file_format = 'PNG'
sc.render.filepath = OUT + "hover_frames_v2/f_"

sc.frame_set(1)
bpy.ops.wm.save_mainfile()
print(json.dumps({"rig": "flroom-hover", "frames": frames, "base": P["base"],
                  "loop": "parfaite (cycles entiers)", "saved": True}))
