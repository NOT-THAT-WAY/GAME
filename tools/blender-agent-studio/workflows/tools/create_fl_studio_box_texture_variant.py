"""Create one procedural material variant of the FL Studio Box V2."""

import argparse
import bpy
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROJECT_DIR = ROOT / "projects" / "fl-studio-console-2026-07-19"
RUNS_DIR = PROJECT_DIR / "texture-runs"

VARIANTS = {
    "graphite-abs": {
        "label": "Graphite Soft-Touch ABS",
        "shell_colors": ((0.018, 0.024, 0.034, 1), (0.105, 0.090, 0.115, 1)),
        "shell_metallic": 0.18,
        "shell_roughness": 0.38,
        "shell_scale": 5.0,
        "shell_detail": 7.0,
        "shell_bump": 0.075,
        "liner_colors": ((0.002, 0.003, 0.005, 1), (0.018, 0.026, 0.034, 1)),
        "liner_roughness": 0.55,
        "accent": (0.24, 1.0, 0.06, 1),
    },
    "pearl-polycarbonate": {
        "label": "Pearl Polycarbonate",
        "shell_colors": ((0.34, 0.31, 0.39, 1), (0.76, 0.70, 0.82, 1)),
        "shell_metallic": 0.08,
        "shell_roughness": 0.23,
        "shell_scale": 12.0,
        "shell_detail": 4.0,
        "shell_bump": 0.032,
        "liner_colors": ((0.008, 0.010, 0.016, 1), (0.035, 0.045, 0.062, 1)),
        "liner_roughness": 0.43,
        "accent": (0.30, 1.0, 0.10, 1),
    },
    "machined-gunmetal": {
        "label": "Machined Gunmetal",
        "shell_colors": ((0.065, 0.075, 0.090, 1), (0.24, 0.27, 0.32, 1)),
        "shell_metallic": 0.86,
        "shell_roughness": 0.20,
        "shell_scale": 38.0,
        "shell_detail": 2.2,
        "shell_bump": 0.022,
        "liner_colors": ((0.002, 0.003, 0.006, 1), (0.020, 0.026, 0.038, 1)),
        "liner_roughness": 0.34,
        "accent": (0.18, 0.95, 0.04, 1),
    },
}


def configure_procedural(material, colors, metallic, roughness, scale, detail, bump_strength):
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    texcoord = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    ramp = nodes.new("ShaderNodeValToRGB")
    bump = nodes.new("ShaderNodeBump")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = detail
    noise.inputs["Roughness"].default_value = 0.62
    ramp.color_ramp.elements[0].position = 0.24
    ramp.color_ramp.elements[0].color = colors[0]
    ramp.color_ramp.elements[1].position = 0.78
    ramp.color_ramp.elements[1].color = colors[1]
    bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = 0.015
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    links.new(texcoord.outputs["Generated"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])


def set_simple_principled(material, color=None, metallic=None, roughness=None, emission=None):
    if not material or not material.node_tree:
        return
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if not bsdf:
        return
    if color is not None:
        bsdf.inputs["Base Color"].default_value = color
    if metallic is not None:
        bsdf.inputs["Metallic"].default_value = metallic
    if roughness is not None:
        bsdf.inputs["Roughness"].default_value = roughness
    if emission is not None:
        emission_input = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        if emission_input:
            emission_input.default_value = emission


parser = argparse.ArgumentParser()
parser.add_argument("--variant", required=True, choices=sorted(VARIANTS))
args = parser.parse_args(__import__("sys").argv[__import__("sys").argv.index("--") + 1 :])
variant_id = args.variant
config = VARIANTS[variant_id]

run_dir = RUNS_DIR / variant_id
gate_dir = run_dir / "gate"
run_dir.mkdir(parents=True, exist_ok=True)
gate_dir.mkdir(parents=True, exist_ok=True)

shell_material = bpy.data.materials.get("M_BOX_WARM_GREY")
liner_material = bpy.data.materials.get("M_BOX_DARK_LINER")
if not shell_material or not liner_material:
    raise RuntimeError("Open FL_Studio_Box_V2.blend before running this script")

configure_procedural(
    shell_material,
    config["shell_colors"],
    config["shell_metallic"],
    config["shell_roughness"],
    config["shell_scale"],
    config["shell_detail"],
    config["shell_bump"],
)
configure_procedural(
    liner_material,
    config["liner_colors"],
    0.045,
    config["liner_roughness"],
    7.0,
    5.0,
    0.10,
)
set_simple_principled(bpy.data.materials.get("M_SCREEN_FRAME"), metallic=config["shell_metallic"], roughness=config["shell_roughness"])
set_simple_principled(bpy.data.materials.get("M_PLAYBACK_GREEN"), emission=config["accent"])

scene = bpy.context.scene
scene.name = "FL_STUDIO_BOX_" + variant_id.upper().replace("-", "_")
scene["ustudio_texture_variant"] = variant_id
scene["ustudio_texture_label"] = config["label"]
scene.frame_set(120)
blend_path = run_dir / f"FL_Studio_Box_{variant_id}.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

for frame in (1, 60, 120, 180, 240):
    scene.frame_set(frame)
    scene.render.filepath = str(gate_dir / f"frame_{frame:04d}.png")
    bpy.ops.render.render(write_still=True)

manifest = {
    "run": variant_id,
    "label": config["label"],
    "created_at": datetime.now().astimezone().isoformat(),
    "source_blend": "projects/fl-studio-console-2026-07-19/FL_Studio_Box_V2.blend",
    "blend": str(blend_path.relative_to(ROOT)),
    "material": {
        "shell_colors": config["shell_colors"],
        "metallic": config["shell_metallic"],
        "roughness": config["shell_roughness"],
        "noise_scale": config["shell_scale"],
        "bump_strength": config["shell_bump"],
    },
    "gate_frames": [1, 60, 120, 180, 240],
    "status": "completed",
}
(run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps(manifest))
