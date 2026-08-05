"""Render the character in its bind pose and report head/body alignment."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

P = globals().get("UNRECORDED_PARAMS", {})
TRIAL = Path(P.get("trial_dir", ".")).resolve()
OUT = TRIAL / P.get("out", "iterations/it10-bind")
OUT.mkdir(parents=True, exist_ok=True)

scene = bpy.context.scene
arm = bpy.data.objects["K3_FABLE_MASCOT"]
body = bpy.data.objects["K3_MECHA_BODY"]
head = bpy.data.objects["K3_MECHA_HEAD"]
dg = bpy.context.evaluated_depsgraph_get()

def eval_bounds(obj):
    ev = obj.evaluated_get(dg)
    mesh = ev.to_mesh()
    pts = [ev.matrix_world @ v.co for v in mesh.vertices]
    lo = [round(min(p[i] for p in pts), 4) for i in range(3)]
    hi = [round(max(p[i] for p in pts), 4) for i in range(3)]
    ev.to_mesh_clear()
    return lo, hi

info = {
    "arm_matrix_world_translation": [round(c, 4) for c in arm.matrix_world.translation],
    "head_parent_type": head.parent_type,
    "head_parent_bone": head.parent_bone,
    "head_matrix_world_translation": [round(c, 4) for c in head.matrix_world.translation],
    "head_bounds": eval_bounds(head),
    "body_bounds": eval_bounds(body),
    "head_bone_head_local": [round(c, 4) for c in arm.data.bones["HEAD"].head_local],
    "head_bone_tail_local": [round(c, 4) for c in arm.data.bones["HEAD"].tail_local],
    "expected_head_center_world": [round(c, 4) for c in (arm.matrix_world @ Vector((0, 0, 1.798)))],
}

keep = {"K3_MECHA_BODY", "K3_MECHA_HEAD", "K3_FABLE_MASCOT"}
for obj in scene.objects:
    if obj.name not in keep:
        obj.hide_render = True
world = scene.world
if world and world.use_nodes:
    for node in world.node_tree.nodes:
        if node.type == "BACKGROUND":
            node.inputs[0].default_value = (0.05, 0.06, 0.08, 1.0)
            node.inputs[1].default_value = 1.0
light = bpy.data.lights.new("BIND_KEY", "AREA")
light.energy, light.size = 300, 3.0
lo = bpy.data.objects.new("BIND_KEY", light)
scene.collection.objects.link(lo)
lo.location = (-2.0, -3.0, 3.0)
lo.rotation_euler = Vector((2.0, 3.0, -2.0)).to_track_quat("-Z", "Y").to_euler()

cam_data = bpy.data.cameras.new("BIND_CAM_DATA")
cam_data.lens = 50
cam = bpy.data.objects.new("BIND_CAM", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = 512, 640
scene.render.image_settings.file_format = "PNG"

center = arm.matrix_world @ Vector((0, 0, 1.04))
for name, off in (("front", Vector((0, -3.0, 0.2))), ("side", Vector((-3.0, 0, 0.2)))):
    cam.location = center + off
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(OUT / f"bind_{name}.png")
    bpy.ops.render.render(write_still=True)

(TRIAL / "diagnostics" / "bind-check.json").write_text(
    json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps(info, ensure_ascii=False))
