"""Create a camera-projected FL Studio box template from the corrected box geometry."""

import bpy
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE_BLEND = ROOT / "projects" / "fl-studio-box-template" / "FL_Studio_Box_Template.blend"
SOURCE_VIDEO = Path(os.environ.get("FL_STUDIO_SOURCE_VIDEO", ROOT / "projects" / "fl-studio-box-semantic-template" / "media" / "current" / "master.mp4"))
PROJECT_DIR = ROOT / "projects" / "fl-studio-box-projection-template"
MEDIA_DIR = PROJECT_DIR / "media" / "current"
INCOMING_DIR = PROJECT_DIR / "incoming"
GATE_DIR = PROJECT_DIR / "sample-gate"
PROJECT_FILE = PROJECT_DIR / "FL_Studio_Box_Projection_Template.blend"

for directory in (PROJECT_DIR, MEDIA_DIR, INCOMING_DIR, GATE_DIR):
    directory.mkdir(parents=True, exist_ok=True)

master_video = MEDIA_DIR / "master.mp4"
controller_video = MEDIA_DIR / "controller.mp4"
if SOURCE_VIDEO.resolve() != master_video.resolve():
    shutil.copy2(SOURCE_VIDEO, master_video)
subprocess.run(
    [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(SOURCE_VIDEO),
        "-vf", "crop=0.406*iw:0.174*ih:0.516*iw:0.715*ih,scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(controller_video),
    ],
    check=True,
)

scene = bpy.context.scene
hero_camera = scene.camera
if not hero_camera:
    raise RuntimeError("Template source has no active camera")

projector_data = hero_camera.data.copy()
projector_data.name = "USTUDIO_FL_PROJECTOR_DATA"
projector = bpy.data.objects.new("USTUDIO_FL_PROJECTOR", projector_data)
projector.matrix_world = hero_camera.matrix_world.copy()
projector.hide_render = True
scene.collection.objects.link(projector)
projector["role"] = "fixed camera projector for continuous FL Studio master video"
projector["source_aspect"] = "1920x1080"

material = bpy.data.materials.get("M_FL_STUDIO_MASTER_PROJECTION") or bpy.data.materials.new("M_FL_STUDIO_MASTER_PROJECTION")
material.use_nodes = True
nodes = material.node_tree.nodes
links = material.node_tree.links
nodes.clear()
output = nodes.new("ShaderNodeOutputMaterial")
bsdf = nodes.new("ShaderNodeBsdfPrincipled")
texture = nodes.new("ShaderNodeTexImage")
texture.name = "USTUDIO_MASTER_MOVIE"
image = bpy.data.images.load(str(master_video), check_existing=False)
image.name = "USTUDIO_MASTER_FL_STUDIO_VIDEO"
image.source = "MOVIE"
texture.image = image
texture.image_user.frame_start = 1
texture.image_user.frame_duration = 406
texture.image_user.use_cyclic = True
texture.image_user.use_auto_refresh = True
links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
emission_input = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
if emission_input:
    links.new(texture.outputs["Color"], emission_input)
if bsdf.inputs.get("Emission Strength"):
    bsdf.inputs["Emission Strength"].default_value = 0.30
bsdf.inputs["Roughness"].default_value = 0.34
links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

projected_objects = (
    "USTUDIO_PLAYLIST_BACK_WALL",
    "USTUDIO_BROWSER_LEFT_WALL",
    "USTUDIO_MIXER_RIGHT_WALL",
    "USTUDIO_PIANO_ROLL_FLOOR",
)
for object_name in projected_objects:
    obj = bpy.data.objects.get(object_name)
    if not obj or obj.type != "MESH":
        raise RuntimeError(f"Projection surface missing: {object_name}")
    obj.data.materials.clear()
    obj.data.materials.append(material)
    uv_name = "USTUDIO_PROJECTED_UV"
    uv = obj.data.uv_layers.get(uv_name) or obj.data.uv_layers.new(name=uv_name)
    obj.data.uv_layers.active = uv
    uv.active_render = True
    for existing in [m for m in obj.modifiers if m.type == "UV_PROJECT"]:
        obj.modifiers.remove(existing)
    modifier = obj.modifiers.new("USTUDIO_MASTER_PROJECTION", "UV_PROJECT")
    modifier.uv_layer = uv_name
    modifier.projector_count = 1
    modifier.projectors[0].object = projector
    modifier.aspect_x = 1920
    modifier.aspect_y = 1080

# The real video already contains its playhead; remove the previous synthetic duplicate.
for name in ("USTUDIO_PLAYHEAD_BACK", "USTUDIO_PLAYHEAD_FLOOR"):
    obj = bpy.data.objects.get(name)
    if obj:
        obj.hide_render = True
        obj.hide_viewport = True

controller_material = bpy.data.materials.get("M_MOVIE_CHANNEL_RACK")
controller_texture = controller_material.node_tree.nodes.get("USTUDIO_FL_STUDIO_MOVIE") if controller_material and controller_material.node_tree else None
if not controller_texture:
    raise RuntimeError("Channel rack movie slot missing")
controller_image = bpy.data.images.load(str(controller_video), check_existing=False)
controller_image.name = "USTUDIO_CONTROLLER_FROM_MASTER"
controller_image.source = "MOVIE"
controller_texture.image = controller_image
controller_texture.image_user.frame_start = 1
controller_texture.image_user.frame_duration = 406
controller_texture.image_user.use_cyclic = True
controller_texture.image_user.use_auto_refresh = True

scene.name = "FL_STUDIO_BOX_PROJECTION_TEMPLATE"
scene.render.fps = 30
scene.frame_start = 1
scene.frame_end = 406
scene["ustudio_template"] = True
scene["ustudio_projection_template"] = True
scene["ustudio_mapping_mode"] = "single continuous camera-projected master video"
scene["ustudio_master_source"] = str(master_video)
scene["ustudio_projector"] = projector.name
scene["ustudio_legacy_five_crop_mode"] = False

controller = bpy.data.objects.get("USTUDIO_MEDIA_CONTROLLER")
if controller:
    controller["mapping_mode"] = "master projection"
    controller["source_video"] = str(master_video)
    controller["duration"] = 13.533333
    controller["fps"] = 30

scene.timeline_markers.clear()
for name, frame in (
    ("USTUDIO_MEDIA_IN", 1),
    ("USTUDIO_MEDIA_QUARTER", 102),
    ("USTUDIO_MEDIA_MIDDLE", 203),
    ("USTUDIO_MEDIA_THREE_QUARTERS", 305),
    ("USTUDIO_MEDIA_OUT", 406),
):
    scene.timeline_markers.new(name, frame=frame)

scene.frame_set(203)
bpy.ops.wm.save_as_mainfile(filepath=str(PROJECT_FILE))
scene.render.filepath = str(GATE_DIR / "projection-frame-0203.png")
bpy.ops.render.render(write_still=True)

manifest = {
    "template": str(PROJECT_FILE.relative_to(ROOT)),
    "created_at": datetime.now().astimezone().isoformat(),
    "mapping": "one 1920x1080 master movie projected continuously across four interior surfaces",
    "projector": projector.name,
    "projected_objects": list(projected_objects),
    "detached_surface": "channel rack uses one crop from the same master source",
    "synthetic_playheads": "disabled",
    "timeline": {"fps": 30, "frames": [1, 406], "duration": 13.533333},
    "workflow": "relink-fl-studio-box-media",
}
(PROJECT_DIR / "projection-manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps(manifest, ensure_ascii=False))
