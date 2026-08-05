"""Rend la sequence et l'assemble en mp4.

  blender -b scene/pulsed_v2_anim.blend --python render_anim.py -- <tag>
"""

import os
import subprocess
import sys

import bpy

ROOT = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TAG = argv[0] if argv else "v1"

frames_dir = os.path.join(ROOT, "renders", f"anim_{TAG}", "frames")
os.makedirs(frames_dir, exist_ok=True)

scene = bpy.context.scene
scene.cycles.samples = int(os.environ.get("PV2_SAMPLES", "64"))
scene.cycles.use_denoising = True
# Scene en transmission : ce sont les rebonds qui coutent. 8 suffisent
# largement (coque avant + coque arriere = 4 traversees au plus).
scene.cycles.max_bounces = 12
scene.cycles.transmission_bounces = 8
scene.cycles.transparent_max_bounces = 8
scene.cycles.glossy_bounces = 4
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = os.path.join(frames_dir, "f_")

print(f"[anim] {scene.frame_start}-{scene.frame_end} @ {scene.cycles.samples} samples")
bpy.ops.render.render(animation=True)

mp4 = os.path.join(ROOT, "renders", f"anim_{TAG}", f"pulsed-v2-demo-{TAG}.mp4")
subprocess.run([
    "ffmpeg", "-v", "error", "-y",
    "-framerate", str(scene.render.fps),
    "-i", os.path.join(frames_dir, "f_%04d.png"),
    "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p",
    "-movflags", "+faststart", mp4,
], check=True)
print(f"[ok] -> {mp4}")
