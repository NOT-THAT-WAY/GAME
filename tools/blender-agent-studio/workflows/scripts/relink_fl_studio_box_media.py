"""Crop a clean FL Studio recording and relink the five controlled movie slots."""

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

if not bpy.context.scene.get("ustudio_template"):
    raise RuntimeError("Ouvrir FL_Studio_Box_Template.blend avant ce workflow")

start_time = max(0.0, float(P.get("start_time", 0.0)))
duration = max(1.0, min(60.0, float(P.get("duration", 10.0))))
output.mkdir(parents=True, exist_ok=True)

probe_cmd = [
    "ffprobe", "-v", "error", "-select_streams", "v:0",
    "-show_entries", "stream=width,height,r_frame_rate,duration",
    "-of", "json", str(source),
]
probe = json.loads(subprocess.run(probe_cmd, check=True, capture_output=True, text=True).stdout)
stream = probe["streams"][0]
source_fps = float(Fraction(stream.get("r_frame_rate", "24/1")))
scene_fps = int(P.get("timeline_fps", 24))
scene_fps = scene_fps if scene_fps in {24, 30, 60} else 24
frame_duration = max(1, round(duration * scene_fps))

presets = {
    "playlist": (0.539, 0.208, 0.285, 0.139),
    "browser": (0.125, 0.708, 0.078, 0.153),
    "mixer": (0.234, 0.486, 0.676, 0.285),
    "piano_roll": (0.477, 0.472, 0.199, 0.396),
    "channel_rack": (0.406, 0.174, 0.516, 0.715),
}
material_slots = {
    "playlist": ("M_MOVIE_PLAYLIST", "playlist.mp4"),
    "browser": ("M_MOVIE_BROWSER", "browser.mp4"),
    "mixer": ("M_MOVIE_MIXER", "mixer.mp4"),
    "piano_roll": ("M_MOVIE_PIANO_ROLL", "piano-roll.mp4"),
    "channel_rack": ("M_MOVIE_CHANNEL_RACK", "controller.mp4"),
}

generated = {}
for slot, (w, h, x, y) in presets.items():
    filename = material_slots[slot][1]
    destination = output / filename
    crop = f"crop={w}*iw:{h}*ih:{x}*iw:{y}*ih,scale=trunc(iw/2)*2:trunc(ih/2)*2,fps={scene_fps}"
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", str(start_time), "-i", str(source), "-t", str(duration),
        "-vf", crop, "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(destination),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    material = bpy.data.materials.get(material_slots[slot][0])
    texture = material.node_tree.nodes.get("USTUDIO_FL_STUDIO_MOVIE") if material and material.node_tree else None
    if not texture:
        raise RuntimeError(f"Slot Blender manquant: {slot}")
    image = bpy.data.images.load(str(destination), check_existing=False)
    image.name = "USTUDIO_RUN_" + slot.upper()
    image.source = "MOVIE"
    texture.image = image
    texture.image_user.frame_start = 1
    texture.image_user.frame_duration = frame_duration
    texture.image_user.use_cyclic = bool(P.get("loop", True))
    texture.image_user.use_auto_refresh = True
    generated[slot] = str(destination)

scene = bpy.context.scene
scene.render.fps = scene_fps
scene.frame_start = 1
scene.frame_end = frame_duration
scene.frame_set(1)
scene["ustudio_media_status"] = "relinked — unsaved"
scene["ustudio_media_source"] = str(source)
scene["ustudio_media_output"] = str(output)
scene["ustudio_media_duration"] = duration
scene["ustudio_media_source_fps"] = source_fps
media_controller = bpy.data.objects.get("USTUDIO_MEDIA_CONTROLLER")
if media_controller:
    media_controller["source_video"] = str(source)
    media_controller["start_time"] = start_time
    media_controller["duration"] = duration
    media_controller["loop"] = bool(P.get("loop", True))
    media_controller["generated_output"] = str(output)

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
    "start_time": start_time,
    "duration": duration,
    "timeline_fps": scene_fps,
    "timeline_frames": [1, frame_duration],
    "loop": bool(P.get("loop", True)),
    "generated_slots": generated,
    "scene": scene.name,
    "blend_saved": False,
    "next_step": "Render gates with marker prefix USTUDIO_MEDIA_, then Save As after validation",
}
(output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps(manifest, ensure_ascii=False))
