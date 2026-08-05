"""Repair the left kit browser and add an audio-reactive 3D playhead glow."""

import array
import bpy
import json
import math
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROJECT_DIR = ROOT / "projects" / "fl-studio-box-semantic-template"
MEDIA_DIR = PROJECT_DIR / "media" / "current"
SOURCE = Path(os.environ.get("FL_STUDIO_SOURCE_VIDEO", MEDIA_DIR / "master.mp4"))
PROJECT_FILE = PROJECT_DIR / "FL_Studio_Box_Semantic_Template.blend"


def transcode_crop(filename, crop):
    destination = MEDIA_DIR / filename
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(SOURCE),
            "-vf", crop + ",scale=trunc(iw/2)*2:trunc(ih/2)*2,fps=30",
            "-an", "-c:v", "libx264", "-g", "1", "-keyint_min", "1",
            "-sc_threshold", "0", "-pix_fmt", "yuv420p", str(destination),
        ],
        check=True,
    )
    return destination


def relink(material_name, path, image_name):
    material = bpy.data.materials.get(material_name)
    texture = material.node_tree.nodes.get("USTUDIO_FL_STUDIO_MOVIE")
    image = bpy.data.images.load(str(path), check_existing=False)
    image.name = image_name
    image.source = "MOVIE"
    texture.image = image
    texture.interpolation = "Linear"
    texture.extension = "CLIP"
    texture.image_user.frame_start = 1
    texture.image_user.frame_duration = 406
    texture.image_user.use_cyclic = True
    texture.image_user.use_auto_refresh = True


def bilinear_grid(name, corners, columns=20, rows=40):
    p00, p10, p11, p01 = corners
    vertices = []
    for row in range(rows + 1):
        v = row / rows
        for column in range(columns + 1):
            u = column / columns
            vertices.append(tuple(
                (1 - v) * ((1 - u) * p00[axis] + u * p10[axis])
                + v * ((1 - u) * p01[axis] + u * p11[axis])
                for axis in range(3)
            ))
    stride = columns + 1
    faces = []
    for row in range(rows):
        for column in range(columns):
            a = row * stride + column
            faces.append((a, a + 1, a + 1 + stride, a + stride))
    mesh = bpy.data.meshes.new(name + "_GRID_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for polygon in mesh.polygons:
        for loop_index in polygon.loop_indices:
            vertex_index = mesh.loops[loop_index].vertex_index
            row, column = divmod(vertex_index, stride)
            uv_layer.data[loop_index].uv = (column / columns, row / rows)
    return mesh


def audio_envelope():
    raw = subprocess.check_output(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(SOURCE),
            "-vn", "-ac", "1", "-ar", "300", "-f", "f32le", "-",
        ]
    )
    samples = array.array("f")
    samples.frombytes(raw)
    values = []
    for frame in range(406):
        start = frame * 10
        chunk = samples[start:start + 10]
        values.append(math.sqrt(sum(value * value for value in chunk) / max(1, len(chunk))))
    ceiling = sorted(values)[round(len(values) * 0.92)] or 1.0
    return [min(1.0, value / ceiling) for value in values]


def linear_keys(obj):
    # Blender 5 uses layered Actions without the legacy action.fcurves member.
    # New keys inherit this preference, set immediately before insertion below.
    return None


scene = bpy.context.scene
if not scene.get("ustudio_semantic_template"):
    raise RuntimeError("Open FL_Studio_Box_Semantic_Template.blend first")

# Dedicated, stable kit list plus a wider playlist that retains the real playhead.
browser_path = transcode_crop("browser.mp4", "crop=215:580:160:310")
playlist_path = transcode_crop("playlist.mp4", "crop=900:250:660:155")
relink("M_MOVIE_BROWSER", browser_path, "USTUDIO_KIT_BROWSER_ALL_INTRA")
relink("M_MOVIE_PLAYLIST", playlist_path, "USTUDIO_PLAYLIST_ALL_INTRA")

browser = bpy.data.objects.get("USTUDIO_BROWSER_LEFT_WALL")
if browser:
    old_mesh = browser.data
    old_materials = list(old_mesh.materials) or [bpy.data.materials["M_MOVIE_BROWSER"]]
    browser.data = bilinear_grid(
        browser.name,
        [(-4.08, -0.36, 1.05), (-3.16, 1.28, 2.55),
         (-3.16, 1.28, 5.02), (-4.08, -0.36, 5.05)],
    )
    for material in old_materials:
        browser.data.materials.append(material)
    if old_mesh.users == 0:
        bpy.data.meshes.remove(old_mesh)
    browser["ustudio_mapping"] = "stable bilinear 20x40 grid; isolated kit list"

# Bright studio exposure remains independent from the emissive accents.
scene.view_settings.look = "AgX - Medium Low Contrast"
scene.view_settings.exposure = 0.55
if scene.world and scene.world.node_tree:
    background = scene.world.node_tree.nodes.get("Background")
    if background:
        background.inputs["Color"].default_value = (0.024, 0.030, 0.045, 1)
        background.inputs["Strength"].default_value = 0.38
for name, energy in {
    "USTUDIO_SOFT_KEY": 820,
    "USTUDIO_SOFT_FILL": 680,
    "USTUDIO_FRONT_KEY": 610,
    "USTUDIO_FRONT_FILL": 540,
    "USTUDIO_INTERIOR_FILL": 610,
}.items():
    light = bpy.data.objects.get(name)
    if light and light.type == "LIGHT":
        light.data.energy = energy

# Dedicated material: only the two playheads react to the soundtrack.
glow = bpy.data.materials.get("M_PLAYHEAD_AUDIO_GLOW") or bpy.data.materials.new("M_PLAYHEAD_AUDIO_GLOW")
glow.use_nodes = True
bsdf = glow.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = (0.04, 0.55, 0.005, 1)
bsdf.inputs["Metallic"].default_value = 0.0
bsdf.inputs["Roughness"].default_value = 0.16
emission_color = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
emission_strength = bsdf.inputs.get("Emission Strength")
emission_color.default_value = (0.12, 1.0, 0.015, 1)

envelope = audio_envelope()
if glow.node_tree.animation_data:
    glow.node_tree.animation_data_clear()
for frame in range(1, 407, 3):
    emission_strength.default_value = 4.5 + envelope[frame - 1] * 5.5
    emission_strength.keyframe_insert("default_value", frame=frame)
emission_strength.default_value = 4.5 + envelope[-1] * 5.5
emission_strength.keyframe_insert("default_value", frame=406)

# The tracked source line travels for 397 frames, then wraps at frame 398.
bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
for name, start_x, end_x in (
    ("USTUDIO_PLAYHEAD_BACK", -2.78, 2.78),
):
    obj = bpy.data.objects.get(name)
    if not obj:
        continue
    obj.hide_render = False
    obj.hide_viewport = False
    obj.animation_data_clear()
    obj.data.materials.clear()
    obj.data.materials.append(glow)
    for frame, x in (
        (1, start_x),
        (397, end_x),
        (398, start_x),
        (406, start_x + (end_x - start_x) * 8 / 396),
    ):
        obj.location.x = x
        obj.keyframe_insert("location", frame=frame)
    linear_keys(obj)
    obj["ustudio_sync"] = "source frames 1-397; wrap 398; audio-reactive emission"

# The Piano Roll clip already contains its own cursor. Do not double it with a
# second 3D overlay on the sloped floor.
floor_playhead = bpy.data.objects.get("USTUDIO_PLAYHEAD_FLOOR")
if floor_playhead:
    floor_playhead.hide_render = True
    floor_playhead.hide_viewport = True

# Fog Glow is composited after the neutral render, without crushing exposure.
group = bpy.data.node_groups.get("USTUDIO_FL_GLOW_COMPOSITOR")
if not group:
    group = bpy.data.node_groups.new("USTUDIO_FL_GLOW_COMPOSITOR", "CompositorNodeTree")
scene.compositing_node_group = group
nodes = group.nodes
nodes.clear()
group.interface.clear()
group.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
render_layers = nodes.new("CompositorNodeRLayers")
glare = nodes.new("CompositorNodeGlare")
glare.name = "USTUDIO_CONTROLLED_FOG_GLOW"
# Blender 5 exposes the redesigned Glare controls as input sockets.
glare.inputs["Type"].default_value = "Fog Glow"
glare.inputs["Quality"].default_value = "High"
glare.inputs["Threshold"].default_value = 1.0
glare.inputs["Smoothness"].default_value = 0.45
glare.inputs["Strength"].default_value = 0.70
glare.inputs["Saturation"].default_value = 1.05
glare.inputs["Size"].default_value = 0.62
composite = nodes.new("NodeGroupOutput")
group.links.new(render_layers.outputs["Image"], glare.inputs["Image"])
group.links.new(glare.outputs["Image"], composite.inputs["Image"])

scene["ustudio_browser_fix"] = "kit-list crop; all-intra; bilinear UV grid"
scene["ustudio_playhead_glow"] = "3D overlay synced to source reset plus audio envelope"
scene["ustudio_crop_contract"] = json.dumps({
    "playlist": "crop=900:250:660:155",
    "browser": "crop=215:580:160:310",
    "mixer": "crop=510:490:1290:320",
    "piano_roll": "crop=900:430:380:380",
    "channel_rack": "crop=825:170:970:810",
})
scene.frame_set(203)
bpy.ops.wm.save_as_mainfile(filepath=str(PROJECT_FILE))

result = {
    "blend": str(PROJECT_FILE),
    "browser": "isolated kit list, all-intra H.264, 20x40 bilinear UV grid",
    "playlist": "expanded crop with full playhead travel",
    "lighting": "bright neutral studio plus controlled compositor Fog Glow",
    "playhead": "3D green bars, source-position loop, audio-reactive emission",
}
print("UNRECORDED_RESULT=" + json.dumps(result, ensure_ascii=False))
