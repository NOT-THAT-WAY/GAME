"""Render key-pose reading views from a saved checkpoint. Batch, never MCP.

Loads a checkpoint copy, adds review cameras and a clay setup, renders the
requested frames in face / profile / three-quarter, and writes one PNG per view.
Nothing is ever saved back: the cameras and lights added here exist only for the
duration of the render, so they can never reach an export.

Clay Workbench rather than a lit render is deliberate — the standard requires
silhouette, line of action, spacing and contacts to be judged before materials
and lighting can flatter or hide them.

Usage:
  blender -b --factory-startup <checkpoint.blend> --python render_poses.py -- \
      <action> <out_dir> <frame> [<frame> ...]
"""
import sys
import math
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
ACTION, OUT_DIR = argv[0], argv[1]
FRAMES = [int(x) for x in argv[2:]]

scene = bpy.context.scene
rig = bpy.data.objects["BAS_PUNCH_Rig"]

# Activate the requested action so the render shows this clip and not whatever
# happened to be active when the checkpoint was written.
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

scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 540
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.film_transparent = False
shading = scene.display.shading
shading.light = "STUDIO"
shading.color_type = "SINGLE"
shading.single_color = (0.62, 0.62, 0.64)
shading.show_shadows = True
shading.show_cavity = True
scene.display.render_aa = "8"

# A real ground plane so foot contact is judged against a surface, not against
# an imagined z=0. It is added to the render scene only.
mesh = bpy.data.meshes.new("BAS_CLAUDE_review_ground")
mesh.from_pydata(
    [(-6, -6, 0), (6, -6, 0), (6, 6, 0), (-6, 6, 0)], [], [(0, 1, 2, 3)]
)
ground = bpy.data.objects.new("BAS_CLAUDE_review_ground", mesh)
scene.collection.objects.link(ground)

TARGET = Vector((0.0, 0.0, 0.70))
VIEWS = {
    # The character faces -Y, so the face view sits on -Y looking back at it.
    "face": Vector((0.0, -4.6, 0.86)),
    "profile": Vector((4.6, 0.0, 0.86)),
    "threequarter": Vector((-3.0, -3.4, 1.55)),
}

cam_data = bpy.data.cameras.new("BAS_CLAUDE_review_cam")
cam_data.lens = 62.0
cam = bpy.data.objects.new("BAS_CLAUDE_review_cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam


def aim(obj, location, target):
    obj.location = location
    direction = (target - location)
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


for view, location in VIEWS.items():
    aim(cam, location, TARGET)
    for frame in FRAMES:
        scene.frame_set(frame)
        scene.render.filepath = f"{OUT_DIR}/{ACTION}_{view}_f{frame:03d}.png"
        bpy.ops.render.render(write_still=True)
        print(f"RENDERED {scene.render.filepath}")

print("RENDER_POSES_DONE")
