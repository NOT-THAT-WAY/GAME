"""Fix S4 : orbite 360 resserree qui reste DANS la boite (plus de frame noire).

- Supprime la rotation de USTUDIO_CAM_S4_ORBIT et l'anim location de la camera.
- Re-key la camera sur une spirale circulaire clampee au volume interieur
  (y <= 1.25 cote fond, |x| <= 3.6), rayon 2.6 -> 1.0, hauteur 1.9 -> 0.02.
- Garde la montee de focale 32 -> 85 mm existante.
"""
import bpy
from math import sin, cos, pi
from mathutils import Vector

WORK_FILE = "${BLENDER_AGENT_STUDIO_ROOT}/projects/fl-studio-box-character-animation/FL_Studio_Box_Character_Anim.blend"
assert bpy.data.filepath == WORK_FILE

sc = bpy.context.scene
cam = bpy.data.objects["USTUDIO_CAM_SCENE4_COMMUNION"]
orbit = bpy.data.objects["USTUDIO_CAM_S4_ORBIT"]

# purge des anims fautives
orbit.animation_data_clear()
orbit.rotation_euler = (0.0, 0.0, 0.0)
cam.animation_data_clear()  # ne touche pas aux cles de lens (sur cam.data)

# recale la cible sur la POITRINE (3.15 visait les tibias ; sol ~3.08 + 0.24)
root_ob = bpy.data.objects["USTUDIO_BOX_FLOAT_ROOT"]
tgt = bpy.data.objects["USTUDIO_CAM_S4_TARGET"]
sc.frame_set(350)
bpy.context.view_layer.update()
tgt.location = root_ob.matrix_world.inverted() @ Vector((0.2, 0.5, 3.32))

frames = list(range(305, 407, 8)) + [406]
for f in frames:
    t = (f - 305) / 101.0
    theta = 2 * pi * t
    r = 2.6 + (1.0 - 2.6) * t
    h = 1.9 + (0.02 - 1.9) * t
    x = r * sin(theta)
    y = -r * cos(theta)
    # clamp LOCAL (centre orbite = perso a (0.2, 0.5)) : murs +-3.9, fond y<1.34
    x = max(-3.5, min(3.6, x))
    y = max(-3.5, min(0.80, y))
    cam.location = (x, y, h)
    cam.keyframe_insert("location", frame=f)

sc.frame_set(305)
bpy.context.view_layer.update()
bpy.ops.wm.save_mainfile()
print("S4_ORBIT_FIXED", len(frames), "cles camera")
