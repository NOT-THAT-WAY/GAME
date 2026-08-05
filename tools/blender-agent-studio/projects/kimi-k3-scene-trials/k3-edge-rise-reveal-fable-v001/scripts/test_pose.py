"""Deformation smoke test: push the rig to the extremes the film needs."""
import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix, Vector

P = globals().get("UNRECORDED_PARAMS", {})
TRIAL = Path(P.get("trial_dir", ".")).resolve()
OUT = TRIAL / P.get("out", "iterations/it01-pose-test")
OUT.mkdir(parents=True, exist_ok=True)

arm = bpy.data.objects["K3_FABLE_MASCOT"]
arm_data = arm.data
REST = {b.name: b.matrix_local.copy() for b in arm_data.bones}
PARENT = {b.name: (b.parent.name if b.parent else None) for b in arm_data.bones}
DES = {}
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"

def set_pose(name, desired):
    pb = arm.pose.bones[name]
    parent = PARENT[name]
    if parent:
        basis = REST[name].inverted() @ REST[parent] @ DES[parent].inverted() @ desired
    else:
        basis = REST[name].inverted() @ desired
    DES[name] = desired.copy()
    pb.matrix_basis = basis

def mat_from_y_z(head, y_dir, z_hint):
    y = Vector(y_dir).normalized()
    z = Vector(z_hint) - y * y.dot(Vector(z_hint))
    if z.length < 1e-6:
        z = Vector((0, 0, 1)) - y * y.z
    z.normalize()
    x = y.cross(z)
    return Matrix(((x.x, y.x, z.x, head.x), (x.y, y.y, z.y, head.y),
                   (x.z, y.z, z.z, head.z), (0, 0, 0, 1)))

def solve_ik(hip, ankle, pole, l1, l2):
    e = ankle - hip
    d = max(min(e.length, l1 + l2 - 0.004), abs(l1 - l2) + 0.004)
    ehat = e.normalized()
    a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    r = math.sqrt(max(l1 * l1 - a * a, 1e-8))
    f = pole - ehat * ehat.dot(pole)
    if f.length < 1e-6:
        f = Vector((0, -1, 0)) - ehat * (-ehat.y)
    f.normalize()
    return hip + ehat * a + f * r

HIP = {"L": Vector((0.172, 0, 0.620)), "R": Vector((-0.172, 0, 0.620))}
L_THIGH = (Vector((0.238, 0, 0.352)) - Vector((0.172, 0, 0.620))).length
L_SHIN = (Vector((0.241, 0, 0.092)) - Vector((0.238, 0, 0.352))).length
SH = {"L": Vector((0.170, 0, 1.268)), "R": Vector((-0.170, 0, 1.268))}
L_UP = (Vector((0.6776, 0, 1.4706)) - SH["L"]).length
L_FORE = (Vector((1.0801, 0, 1.6374)) - Vector((0.6776, 0, 1.4706))).length

FRONT = Vector((0, -1, 0))  # asset front axis

def pose_character(pelvis, lean_deg, feet, arm_swing_deg, elbow_deg, head_pitch_deg):
    up = Vector((0, 0, 1))
    lean = math.radians(lean_deg)
    trunk = Vector((0, -math.sin(lean), math.cos(lean)))  # lean forward = -Y
    m_root = mat_from_y_z(pelvis, trunk, FRONT)
    set_pose("ROOT", m_root)
    delta = m_root @ REST["ROOT"].inverted()
    for name in ("SPINE", "CHEST", "HEAD"):
        head_pos = delta @ REST[name].translation
        d = trunk
        if name == "HEAD":
            pitch = math.radians(head_pitch_deg)
            d = Vector((0, -math.sin(lean + pitch), math.cos(lean + pitch)))
        m = mat_from_y_z(head_pos, d, FRONT)
        set_pose(name, m)
        delta = m @ REST[name].inverted()
    chest_delta = DES["CHEST"] @ REST["CHEST"].inverted()
    for side, sgn in (("L", 1), ("R", -1)):
        m_clav = mat_from_y_z(chest_delta @ REST[f"CLAV.{side}"].translation,
                              chest_delta.to_3x3() @ Vector((sgn, 0, 0)), Vector((0, 0, 1)))
        set_pose(f"CLAV.{side}", m_clav)
        shoulder = chest_delta @ SH[side]
        lat = Vector((sgn, 0, 0))
        down = Vector((0, 0, -1))
        swing = math.radians(arm_swing_deg)
        d_up = Matrix.Rotation(swing, 3, lat) @ down
        m_up = mat_from_y_z(shoulder, d_up, lat)
        set_pose(f"UPPERARM.{side}", m_up)
        elbow = shoulder + d_up * L_UP
        d_fore = Matrix.Rotation(math.radians(elbow_deg), 3, lat) @ d_up
        set_pose(f"FOREARM.{side}", mat_from_y_z(elbow, d_fore, lat))
        hip = DES["ROOT"] @ REST["ROOT"].inverted() @ HIP[side]
        ankle = feet[side]
        knee = solve_ik(hip, ankle, FRONT, L_THIGH, L_SHIN)
        set_pose(f"THIGH.{side}", mat_from_y_z(hip, knee - hip, FRONT))
        set_pose(f"SHIN.{side}", mat_from_y_z(knee, ankle - knee, FRONT))
        set_pose(f"FOOT.{side}", mat_from_y_z(ankle, Vector((0, -0.9, -0.44)), Vector((0, 0, 1))))

# isolate the character: hide every other renderable object
keep = {"K3_MECHA_BODY", "K3_MECHA_HEAD", "K3_FABLE_MASCOT"}
for obj in bpy.context.scene.objects:
    if obj.name not in keep:
        obj.hide_render = True
world = bpy.context.scene.world
if world and world.use_nodes:
    for node in world.node_tree.nodes:
        if node.type == "BACKGROUND":
            node.inputs[0].default_value = (0.05, 0.06, 0.08, 1.0)
            node.inputs[1].default_value = 1.0
key = bpy.data.lights.new("TEST_KEY", "AREA")
key.energy = 120
key.size = 2.0
key_obj = bpy.data.objects.new("TEST_KEY", key)
bpy.context.scene.collection.objects.link(key_obj)
key_obj.location = (-1.2, -1.6, 2.0)
key_obj.rotation_euler = (Vector((1.2, 1.6, -1.4))).to_track_quat("-Z", "Y").to_euler()

# temporary camera
cam_data = bpy.data.cameras.new("TEST_CAM_DATA")
cam_data.lens = 50
cam = bpy.data.objects.new("TEST_CAM", cam_data)
bpy.context.scene.collection.objects.link(cam)
scene = bpy.context.scene
scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = 640, 640
scene.render.image_settings.file_format = "PNG"

poses = {
    "a_stand": dict(pelvis=Vector((0, 0, 0.620)), lean_deg=4, arm_swing_deg=12, elbow_deg=8,
                    head_pitch_deg=0,
                    feet={"L": Vector((0.172, 0, 0.092)), "R": Vector((-0.172, 0, 0.092))}),
    "b_sit": dict(pelvis=Vector((0, 0.06, 0.300)), lean_deg=26, arm_swing_deg=155, elbow_deg=18,
                  head_pitch_deg=-14,
                  feet={"L": Vector((0.20, -0.34, 0.092)), "R": Vector((-0.20, -0.30, 0.092))}),
    "c_stride": dict(pelvis=Vector((0, 0, 0.520)), lean_deg=18, arm_swing_deg=42, elbow_deg=55,
                     head_pitch_deg=-8,
                     feet={"L": Vector((0.16, -0.24, 0.20)), "R": Vector((-0.18, 0.16, 0.092))}),
    "d_lookup": dict(pelvis=Vector((0, 0, 0.610)), lean_deg=-6, arm_swing_deg=16, elbow_deg=12,
                     head_pitch_deg=34,
                     feet={"L": Vector((0.172, 0, 0.092)), "R": Vector((-0.172, 0, 0.092))}),
}

views = {"front": Vector((0.0, -8.0, 2.4)), "side": Vector((-7.6, -2.0, 2.4))}
written = []
for pname, kwargs in poses.items():
    pose_character(**kwargs)
    for vname, offset in views.items():
        target = arm.matrix_world @ Vector((0, 0, 1.05))
        cam.location = arm.matrix_world @ offset
        direction = target - cam.location
        cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        path = OUT / f"{pname}_{vname}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        written.append(path.name)

print("UNRECORDED_RESULT=" + json.dumps({"rendered": written}, ensure_ascii=False))
