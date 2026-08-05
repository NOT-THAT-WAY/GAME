"""Rend les vues de gate depuis scene/pulsed_v2.blend.

  blender -b scene/pulsed_v2.blend --python render_gate.py -- <tag> [cams...]
"""

import os
import sys

import bpy

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import studio  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TAG = argv[0] if argv else "gate"
WANTED = argv[1:] or ["gate_ortho", "gate_front", "gate_hero34", "gate_back", "gate_side"]

out_dir = os.path.join(ROOT, "gates", TAG)
os.makedirs(out_dir, exist_ok=True)

cams = studio.build_studio(samples=int(os.environ.get("PV2_SAMPLES", "96")))
scene = bpy.context.scene

for name in WANTED:
    cam = cams.get(name) or bpy.data.objects.get(name)
    if cam is None:
        print(f"  ! camera inconnue : {name}")
        continue
    scene.camera = cam
    scene.render.filepath = os.path.join(out_dir, f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print(f"[gate] {scene.render.filepath}")

print(f"[ok] gates -> {out_dir}")
