"""Extract readable FL Studio windows from one synchronized master and relink the box."""

import bpy
import json
import subprocess
from fractions import Fraction
from pathlib import Path


P = globals().get("STUDIO_PARAMS", globals().get("UNRECORDED_PARAMS", {}))
output = Path(P["output_dir"]).resolve()
root = output.parent.parent.resolve()
source_value = str(P.get("source_video", "")).strip()
source = Path(source_value)
if not source.is_absolute():
    source = root / source
source = source.resolve()
if root != source and root not in source.parents:
    raise RuntimeError("La vidéo doit rester dans le dossier Blender")
if not source.is_file() or source.suffix.lower() not in {".mp4", ".mov", ".m4v"}:
    raise RuntimeError("Vidéo source MP4/MOV/M4V introuvable")

scene = bpy.context.scene
if not scene.get("ustudio_semantic_template"):
    raise RuntimeError("Ouvrir FL_Studio_Box_Semantic_Template.blend avant ce workflow")

start_time = max(0.0, float(P.get("start_time", 0.0)))
duration = max(1.0, min(60.0, float(P.get("duration", 10.0))))
fps = int(P.get("timeline_fps", 30))
fps = fps if fps in {24, 30, 60} else 30
loop = bool(P.get("loop", True))
frame_duration = max(1, round(duration * fps))
output.mkdir(parents=True, exist_ok=True)

probe = json.loads(subprocess.run(
    ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate,duration", "-of", "json", str(source)],
    check=True, capture_output=True, text=True,
).stdout)
stream = probe["streams"][0]
source_fps = float(Fraction(stream.get("r_frame_rate", "30/1")))

# Normalized from the supplied 1920x1080 reference, so the preset scales to any 16:9 source.
slots = {
    "playlist": ("M_MOVIE_PLAYLIST", "playlist.mp4", "crop=0.46875*iw:0.2315*ih:0.34375*iw:0.1435*ih"),
    # Dedicated kit-list crop: no toolbar, waveform, or neighbouring piano roll.
    "browser": ("M_MOVIE_BROWSER", "browser.mp4", "crop=0.1120*iw:0.5370*ih:0.08333*iw:0.2870*ih"),
    "mixer": ("M_MOVIE_MIXER", "mixer.mp4", "crop=0.2656*iw:0.4537*ih:0.6719*iw:0.2963*ih"),
    "piano_roll": ("M_MOVIE_PIANO_ROLL", "piano-roll.mp4", "crop=0.4688*iw:0.3981*ih:0.1979*iw:0.3519*ih"),
    "channel_rack": ("M_MOVIE_CHANNEL_RACK", "controller.mp4", "crop=0.4297*iw:0.1574*ih:0.5052*iw:0.7500*ih"),
}

generated = {}
for slot, (material_name, filename, crop) in slots.items():
    destination = output / filename
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(start_time), "-i", str(source), "-t", str(duration),
            "-vf", crop + f",scale=trunc(iw/2)*2:trunc(ih/2)*2,fps={fps}",
            "-an", "-c:v", "libx264", "-g", "1", "-keyint_min", "1",
            "-sc_threshold", "0", "-pix_fmt", "yuv420p", str(destination),
        ],
        check=True, capture_output=True, text=True,
    )
    material = bpy.data.materials.get(material_name)
    texture = material.node_tree.nodes.get("USTUDIO_FL_STUDIO_MOVIE") if material and material.node_tree else None
    if not texture:
        raise RuntimeError(f"Slot Blender manquant: {slot}")
    image = bpy.data.images.load(str(destination), check_existing=False)
    image.name = "USTUDIO_RUN_" + slot.upper()
    image.source = "MOVIE"
    texture.image = image
    texture.image_user.frame_start = 1
    texture.image_user.frame_duration = frame_duration
    texture.image_user.use_cyclic = loop
    texture.image_user.use_auto_refresh = True
    generated[slot] = str(destination)

scene.render.fps = fps
scene.frame_start = 1
scene.frame_end = frame_duration
scene.frame_set(1)
scene["ustudio_master_source"] = str(source)
scene["ustudio_media_status"] = "semantic panels relinked — unsaved"
scene["ustudio_media_output"] = str(output)

controller = bpy.data.objects.get("USTUDIO_MEDIA_CONTROLLER")
if controller:
    controller["source_video"] = str(source)
    controller["mapping_mode"] = "semantic panels"
    controller["duration"] = duration
    controller["fps"] = fps
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
    "source_fps": source_fps,
    "mapping": "five readable semantic crops from one synchronized master",
    "generated_slots": generated,
    "timeline": {"fps": fps, "frames": [1, frame_duration], "duration": duration},
    "loop": loop,
    "blend_saved": False,
    "next_step": "Check all five panels, render USTUDIO_MEDIA_ gates, then Save As",
}
(output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps(manifest, ensure_ascii=False))
