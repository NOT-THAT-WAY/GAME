"""Rotate only the arms, everything else at rest: isolates arm skinning."""
import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix, Vector

P = globals().get("UNRECORDED_PARAMS", {})
TRIAL = Path(P.get("trial_dir", ".")).resolve()
OUT = TRIAL / P.get("out", "iterations/it14-arms")
OUT.mkdir(parents=True, exist_ok=True)

arm = bpy.data.objects["K3_FABLE_MASCOT"]
REST = {b.name: b.matrix_local.copy() for b in arm.data.bones}
PARENT = {b.name: (b.parent.name if b.parent else None) for b in arm.data.bones}
DES = {name: m.copy() for name, m in REST.items()}   # unposed bones stay at rest
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"

def set_pose(name, desired):
    pb = arm.pose.bones[name]
    parent = PARENT[name]
    basis = (REST[name].inverted() @ REST[parent] @ DES[parent].inverted() @ desired
             if parent else REST[name].inverted() @ desired)
    DES[name] = desired.copy()
    pb.matrix_basis = basis

def desired_matrix(name, head_pos, direction):
    base = REST[name].to_3x3()
    y_ref = (base @ Vector((0, 1, 0))).normalized()
    q = y_ref.rotation_difference(Vector(direction).normalized())
    return Matrix.Translation(head_pos) @ (q.to_matrix() @ base).to_4x4()

L_UPARM = (Vector((0.6776, 0, 1.4706)) - Vector((0.170, 0, 1.268))).length
SH = {"L": Vector((0.170, 0, 1.268)), "R": Vector((-0.170, 0, 1.268))}

scene = bpy.context.scene
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
light = bpy.data.lights.new("K", "AREA")
light.energy, light.size = 300, 3.0
lo = bpy.data.objects.new("K", light)
scene.collection.objects.link(lo)
lo.location = (-2.0, -3.0, 3.0)
lo.rotation_euler = Vector((2.0, 3.0, -2.0)).to_track_quat("-Z", "Y").to_euler()
cam_data = bpy.data.cameras.new("C_DATA")
cam_data.lens = 50
cam = bpy.data.objects.new("C", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = 512, 640
scene.render.image_settings.file_format = "PNG"
center = arm.matrix_world @ Vector((0, 0, 1.04))
cam.location = center + Vector((0, -3.0, 0.2))
cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()

written = []
for deg in (0, 40, 80, 110, 140):
    for side, sgn in (("L", 1), ("R", -1)):
        lat = Vector((sgn, 0, 0))
        rest_dir = (Vector((0.6776, 0, 1.4706)) - SH["L"]).normalized()
        rest_dir = Vector((rest_dir.x * sgn, 0, rest_dir.z))
        d = Matrix.Rotation(math.radians(deg) * sgn, 3, Vector((0, 1, 0))) @ rest_dir
        set_pose(f"CLAV.{side}", desired_matrix(f"CLAV.{side}",
                 REST[f"CLAV.{side}"].translation, lat))
        shoulder = SH[side]
        set_pose(f"UPPERARM.{side}", desired_matrix(f"UPPERARM.{side}", shoulder, d))
        elbow = shoulder + d * L_UPARM
        set_pose(f"FOREARM.{side}", desired_matrix(f"FOREARM.{side}", elbow, d))
    scene.view_layers[0].update()
    path = OUT / f"arm_{deg:03d}.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    written.append(path.name)

print("UNRECORDED_RESULT=" + json.dumps({"rendered": written}, ensure_ascii=False))
