"""Render a list of frames through a named camera to PNG files.

UNRECORDED_PARAMS: camera=<object name>, frames=57,120,203, out=<dir>, prefix=<str>
Optional: rx=640 ry=360 samples=16
"""
import bpy
import json
from pathlib import Path

P = globals().get("UNRECORDED_PARAMS", {})
cam_name = P["camera"]
frames = [int(x) for x in P["frames"].split(",")]
out = Path(P["out"]).resolve()
prefix = P.get("prefix", cam_name)
out.mkdir(parents=True, exist_ok=True)

scene = bpy.context.scene
scene.camera = bpy.data.objects[cam_name]
scene.render.resolution_x = int(P.get("rx", 640))
scene.render.resolution_y = int(P.get("ry", 360))
scene.render.image_settings.file_format = "PNG"
if hasattr(scene.eevee, "taa_render_samples"):
    scene.eevee.taa_render_samples = int(P.get("samples", 16))

written = []
for f in frames:
    scene.frame_set(f)
    path = out / f"{prefix}_f{f:03d}.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    written.append(str(path))

print("UNRECORDED_RESULT=" + json.dumps({"rendered": written}, ensure_ascii=False))
