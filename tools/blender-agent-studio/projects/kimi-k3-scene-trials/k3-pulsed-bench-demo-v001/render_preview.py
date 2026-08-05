"""Rend la preview et la planche contact de l'essai.

  blender -b scene/trial.blend --python render_preview.py
"""

import os
import subprocess

import bpy

TRIAL_DIR = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.path.join(TRIAL_DIR, "renders", "frames")
MP4 = os.path.join(TRIAL_DIR, "renders", "preview.mp4")
SHEET = os.path.join(TRIAL_DIR, "gates", "contact-sheet.jpg")
os.makedirs(FRAMES, exist_ok=True)
os.makedirs(os.path.dirname(SHEET), exist_ok=True)

scene = bpy.context.scene
scene.cycles.samples = int(os.environ.get("K3_SAMPLES", "64"))
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = 960, 540
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = os.path.join(FRAMES, "f_")

print(f"[preview] {scene.frame_start}-{scene.frame_end} @ {scene.render.fps} fps, "
      f"{scene.cycles.samples} samples")
bpy.ops.render.render(animation=True)

subprocess.run([
    "ffmpeg", "-v", "error", "-y",
    "-framerate", str(scene.render.fps),
    "-start_number", str(scene.frame_start),
    "-i", os.path.join(FRAMES, "f_%04d.png"),
    "-frames:v", str(scene.frame_end - scene.frame_start + 1),
    "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p",
    "-movflags", "+faststart", MP4,
], check=True)

# Planche contact : 6 poses reparties, pour lire le film d'un coup d'oeil.
picks = [1, 30, 60, 90, 120, 144]
inputs = []
for f in picks:
    inputs += ["-i", os.path.join(FRAMES, f"f_{f:04d}.png")]
filt = "".join(f"[{i}:v]scale=480:-2[v{i}];" for i in range(len(picks)))
filt += "".join(f"[v{i}]" for i in range(len(picks))) + f"xstack=inputs={len(picks)}:layout=0_0|w0_0|w0+w1_0|0_h0|w0_h0|w0+w1_h0[out]"
subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs,
                "-filter_complex", filt, "-map", "[out]",
                "-q:v", "3", SHEET], check=True)

print(f"[ok] {MP4}")
print(f"[ok] {SHEET}")
