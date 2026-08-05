"""Validation visuelle du personnage — rend deux vues scratch, NE SAUVEGARDE PAS."""
import bpy
from mathutils import Vector

sc = bpy.context.scene

# camera scratch
cam_data = bpy.data.cameras.new("DEBUG_CAM_DATA")
cam_data.lens = 60
cam = bpy.data.objects.new("DEBUG_CAM", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam

# lumiere scratch
li_data = bpy.data.lights.new("DEBUG_LIGHT_DATA", type="AREA")
li_data.energy = 300
li_data.shape = "DISK"
li_data.size = 2.0
li = bpy.data.objects.new("DEBUG_LIGHT", li_data)
sc.collection.objects.link(li)
li.location = (1.5, -1.5, 2.0)
li.rotation_euler = (0.6, 0.0, 0.7)

# masque la boite pour isoler le perso (viewport+render, non sauvegarde)
for o in bpy.data.objects:
    if o.name.startswith("USTUDIO_") and not o.name.startswith("USTUDIO_CHAR"):
        o.hide_render = True

sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x = 480
sc.render.resolution_y = 540
sc.render.filepath = ""

def track(cam_obj, target):
    d = target - cam_obj.location
    cam_obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

views = {
    "char-front": Vector((0, -1.6, 0.22)),
    "char-side":  Vector((1.6, 0, 0.22)),
    "char-34":    Vector((1.1, -1.2, 0.55)),
}
for name, pos in views.items():
    cam.location = pos
    track(cam, Vector((0, 0, 0.17)))
    sc.render.filepath = f"${BLENDER_AGENT_STUDIO_ROOT}/projects/fl-studio-box-character-animation/analysis/{name}.png"
    bpy.ops.render.render(write_still=True)
    print("RENDERED", name)
