"""Vues de preuve : elles doivent montrer le CONTACT et l'espace libre,
pas seulement le produit (SCENE_TRIAL_EVALUATION_RULES.md).

  blender -b scene/trial.blend --python proof_views.py
"""

import math
import os

import bpy
from mathutils import Vector

TRIAL_DIR = os.path.dirname(os.path.abspath(__file__))
GATES = os.path.join(TRIAL_DIR, "gates")
os.makedirs(GATES, exist_ok=True)

scene = bpy.context.scene
scene.cycles.samples = 24
scene.render.resolution_x, scene.render.resolution_y = 720, 405
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
original_cam = scene.camera


def cam(name, loc, target, lens=50.0, ortho=None):
    data = bpy.data.cameras.new(name)
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = loc
    d = Vector(loc) - Vector(target)
    obj.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    return obj


shots = [
    # appui : rasant le plateau, on doit VOIR la ligne de contact
    ("proof-support", cam("PROOF_SUPPORT", (0.0, -0.22, 0.012),
                          (0.0, 0.0, 0.010), lens=85), 1),
    # profil orthographique : epaisseur et assise, sans perspective
    ("proof-side", cam("PROOF_SIDE", (0.45, 0.0, 0.014),
                       (0.0, 0.0, 0.014), ortho=0.26), 72),
    # hero : la pose reelle du plan, pour recouper avec le film
    ("proof-hero", original_cam, 120),
]

for name, camera, frame in shots:
    scene.frame_set(frame)
    scene.camera = camera
    scene.render.filepath = os.path.join(GATES, f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print(f"[proof] {name} (frame {frame}) -> {scene.render.filepath}")

scene.camera = original_cam
print("[ok] vues de preuve rendues")
