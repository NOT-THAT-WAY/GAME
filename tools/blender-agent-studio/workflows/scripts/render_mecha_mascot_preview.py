"""Render the six-second Mecha Mascot camera presentation without saving the blend."""
from pathlib import Path

import bpy


P = globals().get("STUDIO_PARAMS", globals().get("UNRECORDED_PARAMS", {}))
trial = Path(P["trial_dir"]).expanduser().resolve()
frames = trial / "renders" / "frames"
frames.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = 144
scene.render.fps = 24
scene.render.fps_base = 1.0
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 720
scene.render.resolution_y = 720
scene.render.resolution_percentage = 75
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.render.image_settings.color_depth = "8"
scene.render.filepath = str(frames / "frame_")
scene.render.use_file_extension = True
bpy.ops.render.render(animation=True)
print("UNRECORDED_RESULT=" + str({"frames": str(frames), "count": 144, "saved": False}))
