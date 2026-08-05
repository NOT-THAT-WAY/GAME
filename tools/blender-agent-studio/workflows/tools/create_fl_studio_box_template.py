"""Turn FL Studio Box V2 into a reusable media-slot template."""

import bpy
import json
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PROJECT = ROOT / "projects" / "fl-studio-console-2026-07-19"
SOURCE_CLIPS = SOURCE_PROJECT / "source-panel-clips"
PROJECT_DIR = ROOT / "projects" / "fl-studio-box-template"
MEDIA_DIR = PROJECT_DIR / "media" / "current"
INCOMING_DIR = PROJECT_DIR / "incoming"
GATE_DIR = PROJECT_DIR / "sample-gate"
PROJECT_FILE = PROJECT_DIR / "FL_Studio_Box_Template.blend"

SLOTS = {
    "playlist": ("M_MOVIE_PLAYLIST", "playlist.mp4", "mur du fond"),
    "browser": ("M_MOVIE_BROWSER", "browser.mp4", "paroi gauche"),
    "mixer": ("M_MOVIE_MIXER", "mixer.mp4", "paroi droite"),
    "piano_roll": ("M_MOVIE_PIANO_ROLL", "piano-roll.mp4", "plancher incliné"),
    "channel_rack": ("M_MOVIE_CHANNEL_RACK", "controller.mp4", "module avant"),
}

for folder in (PROJECT_DIR, MEDIA_DIR, INCOMING_DIR, GATE_DIR):
    folder.mkdir(parents=True, exist_ok=True)

for _slot, (_material, filename, _surface) in SLOTS.items():
    shutil.copy2(SOURCE_CLIPS / filename, MEDIA_DIR / filename)

for slot, (material_name, filename, _surface) in SLOTS.items():
    material = bpy.data.materials.get(material_name)
    if not material or not material.node_tree:
        raise RuntimeError(f"Material slot missing: {material_name}")
    texture = material.node_tree.nodes.get("USTUDIO_FL_STUDIO_MOVIE")
    if not texture:
        raise RuntimeError(f"Movie texture node missing: {material_name}")
    image = bpy.data.images.load(str(MEDIA_DIR / filename), check_existing=False)
    image.name = "USTUDIO_MEDIA_" + slot.upper()
    image.source = "MOVIE"
    texture.image = image
    texture.image_user.frame_duration = 36
    texture.image_user.frame_start = 1
    texture.image_user.use_cyclic = True
    texture.image_user.use_auto_refresh = True

scene = bpy.context.scene
scene.name = "FL_STUDIO_BOX_TEMPLATE"
scene["ustudio_template"] = True
scene["ustudio_template_version"] = 1
scene["ustudio_media_status"] = "demo media — ready to relink"
scene["ustudio_media_slots"] = json.dumps({slot: {"material": spec[0], "file": spec[1], "surface": spec[2]} for slot, spec in SLOTS.items()})
scene["ustudio_usage"] = "Run workflow relink-fl-studio-box-media, render gates, then save only after validation"

media_controller = bpy.data.objects.get("USTUDIO_MEDIA_CONTROLLER") or bpy.data.objects.new("USTUDIO_MEDIA_CONTROLLER", None)
if not media_controller.users_collection:
    scene.collection.objects.link(media_controller)
media_controller.empty_display_type = "CUBE"
media_controller.empty_display_size = 0.35
media_controller.hide_render = True
media_controller["source_video"] = "incoming/fl-studio-source.mp4"
media_controller["start_time"] = 0.0
media_controller["duration"] = 10.0
media_controller["loop"] = True
media_controller["slot_count"] = 5
media_controller["instruction"] = "Use Blender Studio workflow: Adapter une vidéo — FL Studio Box"

scene.timeline_markers.clear()
scene.timeline_markers.new("USTUDIO_MEDIA_IN", frame=1)
scene.timeline_markers.new("USTUDIO_MEDIA_QUARTER", frame=60)
scene.timeline_markers.new("USTUDIO_MEDIA_MIDDLE", frame=120)
scene.timeline_markers.new("USTUDIO_MEDIA_THREE_QUARTERS", frame=180)
scene.timeline_markers.new("USTUDIO_MEDIA_OUT", frame=240)
scene.frame_set(120)

text = bpy.data.texts.get("USTUDIO_TEMPLATE_GUIDE") or bpy.data.texts.new("USTUDIO_TEMPLATE_GUIDE")
text.clear()
text.write(
    "FL STUDIO BOX TEMPLATE\n\n"
    "1. Place a clean FL Studio screen recording under projects/fl-studio-box-template/incoming/.\n"
    "2. Run the controlled workflow 'Adapter une vidéo — FL Studio Box'.\n"
    "3. Check the five media slots and timeline.\n"
    "4. Run Gate de keyframes with prefix USTUDIO_MEDIA_.\n"
    "5. Save a copy only after visual validation.\n"
)

bpy.ops.wm.save_as_mainfile(filepath=str(PROJECT_FILE))
scene.render.filepath = str(GATE_DIR / "template-frame-0120.png")
bpy.ops.render.render(write_still=True)

slot_map = {
    "template": str(PROJECT_FILE.relative_to(ROOT)),
    "created_at": datetime.now().astimezone().isoformat(),
    "workflow": "relink-fl-studio-box-media",
    "incoming": str(INCOMING_DIR.relative_to(ROOT)),
    "slots": {slot: {"material": spec[0], "filename": spec[1], "surface": spec[2]} for slot, spec in SLOTS.items()},
    "default_timeline": {"start": 1, "end": 240, "fps": 24},
    "save_policy": "workflow never saves the blend; validate gates before Save As",
}
(PROJECT_DIR / "slot-map.json").write_text(json.dumps(slot_map, indent=2, ensure_ascii=False), encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps(slot_map, ensure_ascii=False))
