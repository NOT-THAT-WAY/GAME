"""Keep the working rear playhead, remove the doubled floor overlay, add a Y2K color wash."""

import bpy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROJECT_DIR = ROOT / "projects" / "fl-studio-box-semantic-template"
PROJECT_FILE = PROJECT_DIR / "FL_Studio_Box_Semantic_Template.blend"
scene = bpy.context.scene

if not scene.get("ustudio_semantic_template"):
    raise RuntimeError("Open FL_Studio_Box_Semantic_Template.blend first")

# The floor movie already contains its real playhead. A second 3D line creates a
# visible double/V-shaped trajectory because the sloped crop has a different homography.
floor_playhead = bpy.data.objects.get("USTUDIO_PLAYHEAD_FLOOR")
if floor_playhead:
    floor_playhead.hide_render = True
    floor_playhead.hide_viewport = True
    floor_playhead["ustudio_status"] = "disabled — real Piano Roll playhead remains in movie texture"

back_playhead = bpy.data.objects.get("USTUDIO_PLAYHEAD_BACK")
if back_playhead:
    back_playhead.hide_render = False
    back_playhead.hide_viewport = False
    back_playhead["ustudio_status"] = "active — 3D audio-reactive overlay"

# Bright base plus saturated edge washes: color comes from light direction rather
# than from crushing the grade or painting every material neon.
scene.view_settings.look = "AgX - Medium Low Contrast"
scene.view_settings.exposure = 0.48
if scene.world and scene.world.node_tree:
    background = scene.world.node_tree.nodes.get("Background")
    if background:
        background.inputs["Color"].default_value = (0.018, 0.024, 0.045, 1)
        background.inputs["Strength"].default_value = 0.34

light_settings = {
    # Y2K color washes matching the useful green/magenta language of the reference.
    "USTUDIO_SOFT_KEY": (520, (0.42, 1.00, 0.20)),
    "USTUDIO_SOFT_FILL": (500, (1.00, 0.20, 0.58)),
    # Neutral support keeps the box readable and prevents the old dark result.
    "USTUDIO_FRONT_KEY": (690, (1.00, 0.88, 0.76)),
    "USTUDIO_FRONT_FILL": (620, (0.66, 0.80, 1.00)),
    "USTUDIO_INTERIOR_FILL": (590, (0.82, 0.88, 1.00)),
    "USTUDIO_GREEN_BOUNCE": (75, (0.42, 1.00, 0.16)),
}
for name, (energy, color) in light_settings.items():
    light = bpy.data.objects.get(name)
    if light and light.type == "LIGHT":
        light.data.energy = energy
        light.data.color = color


def principled(material_name):
    material = bpy.data.materials.get(material_name)
    if not material or not material.node_tree:
        return None
    return material.node_tree.nodes.get("Principled BSDF")


shell = principled("M_BOX_WARM_GREY")
if shell:
    shell.inputs["Base Color"].default_value = (0.16, 0.095, 0.17, 1)
    shell.inputs["Metallic"].default_value = 0.30
    shell.inputs["Roughness"].default_value = 0.34
    if shell.inputs.get("Coat Weight"):
        shell.inputs["Coat Weight"].default_value = 0.26
    if shell.inputs.get("Coat Roughness"):
        shell.inputs["Coat Roughness"].default_value = 0.20

liner = principled("M_BOX_DARK_LINER")
if liner:
    liner.inputs["Base Color"].default_value = (0.010, 0.016, 0.032, 1)
    liner.inputs["Metallic"].default_value = 0.20
    liner.inputs["Roughness"].default_value = 0.38

screen_frame = principled("M_SCREEN_FRAME")
if screen_frame:
    screen_frame.inputs["Base Color"].default_value = (0.012, 0.020, 0.040, 1)
    screen_frame.inputs["Metallic"].default_value = 0.34
    screen_frame.inputs["Roughness"].default_value = 0.26

purple = principled("M_SIDE_PURPLE")
if purple:
    purple.inputs["Base Color"].default_value = (0.55, 0.015, 0.22, 1)
    emission_color = purple.inputs.get("Emission Color") or purple.inputs.get("Emission")
    if emission_color:
        emission_color.default_value = (1.00, 0.025, 0.42, 1)
    if purple.inputs.get("Emission Strength"):
        purple.inputs["Emission Strength"].default_value = 7.5

green = principled("M_PLAYBACK_GREEN")
if green:
    green.inputs["Base Color"].default_value = (0.08, 0.62, 0.01, 1)
    emission_color = green.inputs.get("Emission Color") or green.inputs.get("Emission")
    if emission_color:
        emission_color.default_value = (0.20, 1.00, 0.025, 1)
    if green.inputs.get("Emission Strength"):
        green.inputs["Emission Strength"].default_value = 8.0

group = bpy.data.node_groups.get("USTUDIO_FL_GLOW_COMPOSITOR")
glare = group.nodes.get("USTUDIO_CONTROLLED_FOG_GLOW") if group else None
if glare:
    glare.inputs["Threshold"].default_value = 1.05
    glare.inputs["Strength"].default_value = 0.62
    glare.inputs["Saturation"].default_value = 1.16
    glare.inputs["Size"].default_value = 0.58

scene["ustudio_palette"] = "V6 pearl plum + acid lime left + hot magenta right + neutral support"
scene["ustudio_floor_playhead"] = "3D overlay disabled; source movie playhead only"
scene.frame_set(203)
bpy.ops.wm.save_as_mainfile(filepath=str(PROJECT_FILE))

print("UNRECORDED_RESULT=" + json.dumps({
    "blend": str(PROJECT_FILE),
    "floor_playhead": "removed — source video line retained",
    "rear_playhead": "active and audio-reactive",
    "palette": "pearl plum, acid lime, hot magenta, neutral support",
    "exposure": 0.48,
}, ensure_ascii=False))
