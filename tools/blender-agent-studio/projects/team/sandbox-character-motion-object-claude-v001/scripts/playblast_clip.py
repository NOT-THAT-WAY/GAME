"""Render the full clip as an image sequence for the playblast. Batch, isolated.

The whole range is rendered, never a hero subset: a clip is judged on every
frame. Loops are repeated downstream by ffmpeg so a seam pop has four chances to
show itself.

Usage:
  blender -b --factory-startup <checkpoint.blend> --python playblast_clip.py -- \
      <action> <out_dir>
"""
import bpy
import sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
ACTION, OUT_DIR = argv[0], argv[1]

scene = bpy.context.scene
rig = bpy.data.objects["BAS_PUNCH_Rig"]
action = bpy.data.actions[ACTION]
if rig.animation_data is None:
    rig.animation_data_create()
rig.animation_data.action = action
for slot in getattr(action, "slots", []):
    try:
        rig.animation_data.action_slot = slot
        break
    except Exception:
        pass

f_start = int(round(action.frame_range[0]))
f_end = int(round(action.frame_range[1]))
scene.frame_start = f_start
scene.frame_end = f_end
scene.render.fps = 30
scene.render.fps_base = 1.0

scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 640
scene.render.resolution_y = 480
scene.render.resolution_percentage = 100
shading = scene.display.shading
shading.light = "STUDIO"
shading.color_type = "SINGLE"
shading.single_color = (0.62, 0.62, 0.64)
shading.show_shadows = True
shading.show_cavity = True
scene.display.render_aa = "8"

mesh = bpy.data.meshes.new("BAS_CLAUDE_pb_ground")
mesh.from_pydata([(-8, -8, 0), (8, -8, 0), (8, 8, 0), (-8, 8, 0)], [], [(0, 1, 2, 3)])
ground = bpy.data.objects.new("BAS_CLAUDE_pb_ground", mesh)
scene.collection.objects.link(ground)

cam_data = bpy.data.cameras.new("BAS_CLAUDE_pb_cam")
cam_data.lens = 55.0
cam = bpy.data.objects.new("BAS_CLAUDE_pb_cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
# Three-quarter front view: it shows the stride, the foot contacts and the
# body/foot clearance at once, which the pure profile hides behind the sphere.
location = Vector((-3.1, -3.6, 1.45))
target = Vector((0.0, 0.0, 0.72))
cam.location = location
cam.rotation_euler = (target - location).to_track_quat("-Z", "Y").to_euler()

scene.render.image_settings.file_format = "PNG"
scene.render.filepath = f"{OUT_DIR}/{ACTION}_"
bpy.ops.render.render(animation=True)
print(f"PLAYBLAST_FRAMES {f_start}-{f_end} -> {OUT_DIR}")
