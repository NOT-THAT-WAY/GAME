"""Project one continuous FL Studio video across the box interior."""

import bpy
import json
import subprocess
from fractions import Fraction
from pathlib import Path


P = globals().get("STUDIO_PARAMS", globals().get("UNRECORDED_PARAMS", {}))
output = Path(P["output_dir"]).resolve()
root = output.parent.parent.resolve()
source_value = str(P.get("source_video", "")).strip()
if not source_value:
    raise RuntimeError("La vidéo source est obligatoire")
source = Path(source_value)
if not source.is_absolute():
    source = root / source
source = source.resolve()
if root != source and root not in source.parents:
    raise RuntimeError("La vidéo doit rester dans le dossier Blender")
if not source.is_file() or source.suffix.lower() not in {".mp4", ".mov", ".m4v"}:
    raise RuntimeError("Vidéo MP4/MOV/M4V introuvable dans le dossier Blender")

scene = bpy.context.scene
if not scene.get("ustudio_projection_template"):
    raise RuntimeError("Ouvrir FL_Studio_Box_Projection_Template.blend avant ce workflow")

start_time = max(0.0, float(P.get("start_time", 0.0)))
duration = max(1.0, min(60.0, float(P.get("duration", 10.0))))
timeline_fps = int(P.get("timeline_fps", 30))
timeline_fps = timeline_fps if timeline_fps in {24, 30, 60} else 30
loop = bool(P.get("loop", True))
output.mkdir(parents=True, exist_ok=True)

probe = json.loads(
    subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate,duration", "-of", "json", str(source)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
)
stream = probe["streams"][0]
width = int(stream["width"])
height = int(stream["height"])
source_fps = float(Fraction(stream.get("r_frame_rate", "30/1")))
frame_duration = max(1, round(duration * timeline_fps))

master = output / "master.mp4"
controller_clip = output / "controller.mp4"
subprocess.run(
    [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(start_time), "-i", str(source), "-t", str(duration),
        "-vf", f"fps={timeline_fps},scale=trunc(iw/2)*2:trunc(ih/2)*2", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(master),
    ],
    check=True,
    capture_output=True,
    text=True,
)
subprocess.run(
    [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(start_time), "-i", str(source), "-t", str(duration),
        "-vf", f"crop=0.406*iw:0.174*ih:0.516*iw:0.715*ih,scale=trunc(iw/2)*2:trunc(ih/2)*2,fps={timeline_fps}",
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(controller_clip),
    ],
    check=True,
    capture_output=True,
    text=True,
)

master_material = bpy.data.materials.get("M_FL_STUDIO_MASTER_PROJECTION")
master_texture = master_material.node_tree.nodes.get("USTUDIO_MASTER_MOVIE") if master_material and master_material.node_tree else None
if not master_texture:
    raise RuntimeError("Matériau maître de projection introuvable")
master_image = bpy.data.images.load(str(master), check_existing=False)
master_image.name = "USTUDIO_RUN_MASTER_VIDEO"
master_image.source = "MOVIE"
master_texture.image = master_image
master_texture.image_user.frame_start = 1
master_texture.image_user.frame_duration = frame_duration
master_texture.image_user.use_cyclic = loop
master_texture.image_user.use_auto_refresh = True

projector = bpy.data.objects.get("USTUDIO_FL_PROJECTOR")
if not projector:
    raise RuntimeError("Caméra projecteur manquante")
projector["source_aspect"] = f"{width}x{height}"
for object_name in (
    "USTUDIO_PLAYLIST_BACK_WALL",
    "USTUDIO_BROWSER_LEFT_WALL",
    "USTUDIO_MIXER_RIGHT_WALL",
    "USTUDIO_PIANO_ROLL_FLOOR",
):
    obj = bpy.data.objects.get(object_name)
    modifier = obj.modifiers.get("USTUDIO_MASTER_PROJECTION") if obj else None
    if not modifier:
        raise RuntimeError(f"Projection modifier missing: {object_name}")
    modifier.aspect_x = width
    modifier.aspect_y = height
    modifier.projectors[0].object = projector

controller_material = bpy.data.materials.get("M_MOVIE_CHANNEL_RACK")
controller_texture = controller_material.node_tree.nodes.get("USTUDIO_FL_STUDIO_MOVIE") if controller_material and controller_material.node_tree else None
if not controller_texture:
    raise RuntimeError("Slot channel rack introuvable")
controller_image = bpy.data.images.load(str(controller_clip), check_existing=False)
controller_image.source = "MOVIE"
controller_texture.image = controller_image
controller_texture.image_user.frame_start = 1
controller_texture.image_user.frame_duration = frame_duration
controller_texture.image_user.use_cyclic = loop
controller_texture.image_user.use_auto_refresh = True

scene.render.fps = timeline_fps
scene.frame_start = 1
scene.frame_end = frame_duration
scene.frame_set(1)
scene["ustudio_master_source"] = str(source)
scene["ustudio_projection_output"] = str(output)
scene["ustudio_media_status"] = "master projection relinked — unsaved"

controller = bpy.data.objects.get("USTUDIO_MEDIA_CONTROLLER")
if controller:
    controller["source_video"] = str(source)
    controller["mapping_mode"] = "master projection"
    controller["duration"] = duration
    controller["fps"] = timeline_fps
    controller["loop"] = loop

scene.timeline_markers.clear()
for name, frame in (
    ("USTUDIO_MEDIA_IN", 1),
    ("USTUDIO_MEDIA_QUARTER", max(1, round(frame_duration * 0.25))),
    ("USTUDIO_MEDIA_MIDDLE", max(1, round(frame_duration * 0.50))),
    ("USTUDIO_MEDIA_THREE_QUARTERS", max(1, round(frame_duration * 0.75))),
    ("USTUDIO_MEDIA_OUT", frame_duration),
):
    scene.timeline_markers.new(name, frame=frame)

manifest = {
    "source": str(source),
    "source_probe": stream,
    "mapping": "single continuous camera projection",
    "master_video": str(master),
    "controller_crop": str(controller_clip),
    "projector": projector.name,
    "timeline": {"fps": timeline_fps, "frames": [1, frame_duration], "duration": duration},
    "loop": loop,
    "blend_saved": False,
    "next_step": "Render gates with USTUDIO_MEDIA_, then Save As after validation",
}
(output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps(manifest, ensure_ascii=False))
