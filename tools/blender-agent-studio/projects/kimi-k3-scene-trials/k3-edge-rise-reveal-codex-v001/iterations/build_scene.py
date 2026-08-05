"""Build the isolated K3 Edge Rise Reveal trial from audited source assets."""
from __future__ import annotations

import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix, Vector


ROOT = Path("${BLENDER_AGENT_STUDIO_ROOT}")
TRIAL = ROOT / "projects/kimi-k3-scene-trials/k3-edge-rise-reveal-codex-v001"
ASSET = ROOT / "asset_library/characters/mecha-mascot-v002.blend"
PREFIX = "K3_EDGE_"
SCALE = 0.43
FOOT_PAD = 0.030


def smooth(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def floor_z(y: float) -> float:
    return 0.88 + (y + 0.42) * (1.75 / 1.67)


def ensure_collection(name: str):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def link_only(obj, collection):
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    collection.objects.link(obj)


def key(obj, path: str, frame: int, index: int = -1):
    obj.keyframe_insert(data_path=path, frame=frame, index=index)


def set_linear(owner):
    ad = getattr(owner, "animation_data", None)
    action = getattr(ad, "action", None) if ad else None
    if not action:
        return
    fcurves = list(getattr(action, "fcurves", []))
    if not fcurves:
        for layer in getattr(action, "layers", []):
            for strip in layer.strips:
                for bag in strip.channelbags:
                    fcurves.extend(bag.fcurves)
    for fc in fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


def clear_k3():
    for obj in list(bpy.data.objects):
        if obj.name.startswith(PREFIX):
            bpy.data.objects.remove(obj, do_unlink=True)
    for col in list(bpy.data.collections):
        if col.name.startswith(PREFIX):
            bpy.data.collections.remove(col)


scene = bpy.context.scene
clear_k3()
scene.name = "K3_EDGE_RISE_REVEAL"
scene.frame_start = 1
scene.frame_end = 360
scene.render.fps = 30
scene.render.fps_base = 1.0
scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.render.use_file_extension = True
scene.render.filepath = str(TRIAL / "renders/frames/frame_")
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except Exception:
    scene.render.engine = "BLENDER_EEVEE"
if hasattr(scene, "eevee"):
    try:
        scene.eevee.taa_render_samples = 24
    except Exception:
        pass
scene.view_settings.view_transform = "AgX"
try:
    scene.view_settings.look = "AgX - Medium High Contrast"
except Exception:
    pass
scene.view_settings.exposure = 0.15
scene.render.image_settings.color_mode = "RGBA"

# Freeze the inherited floating product-shot rig. The interior becomes the physical world.
float_root = bpy.data.objects.get("USTUDIO_BOX_FLOAT_ROOT")
if not float_root:
    raise RuntimeError("Audited template root missing")
float_root.animation_data_clear()
float_root.location = (0.0, 0.0, 0.0)
float_root.rotation_euler = (0.0, 0.0, 0.0)
float_root.scale = (1.0, 1.0, 1.0)

# Original camera/target are retained as source evidence but not used.
for name in ("USTUDIO_BOX_CAMERA", "USTUDIO_BOX_TARGET"):
    obj = bpy.data.objects.get(name)
    if obj:
        obj.hide_viewport = True
        obj.hide_render = True

# Keep interface panels dominant; inherited product lights become a restrained ambient bed.
for obj in scene.objects:
    if obj.type == "LIGHT" and obj.name.startswith("USTUDIO_"):
        obj.data.energy *= 0.18

# Audio from the audited master capture.
audio_path = str(ROOT / "projects/fl-studio-box-semantic-template/media/current/master.mp4")
if scene.sequence_editor:
    scene.sequence_editor_clear()
seq = scene.sequence_editor_create()
try:
    sound_strip = seq.strips.new_sound(PREFIX + "AUDIO_148BPM", audio_path, channel=1, frame_start=1)
except AttributeError:
    sound_strip = seq.sequences.new_sound(PREFIX + "AUDIO_148BPM", audio_path, channel=1, frame_start=1)
sound_strip.frame_final_duration = 360
sound_strip.volume = 1.0

# Append only the two validated V2 meshes.
with bpy.data.libraries.load(str(ASSET), link=False) as (src, dst):
    requested = [name for name in ("K3_MECHA_BODY", "K3_MECHA_HEAD") if name in src.objects]
    if len(requested) != 2:
        raise RuntimeError("Validated V2 body/head missing")
    dst.objects = requested
body_src, head_src = dst.objects
character_col = ensure_collection(PREFIX + "CHARACTER")
body = body_src
head = head_src
body.name = PREFIX + "BODY_V2"
head.name = PREFIX + "HEAD_V2"
body.parent = None
head.parent = None
link_only(body, character_col)
link_only(head, character_col)
body.location = (0.0, 0.0, 0.0)
body.rotation_euler = (0.0, 0.0, 0.0)
body.scale = (1.0, 1.0, 1.0)
head.location = (0.0, 0.0, 1.798016)
head.rotation_euler = (0.0, 0.0, 0.0)
head.scale = (1.0, 1.0, 1.0)
body["source_asset"] = "asset_library/characters/mecha-mascot-v002.blend"
body["source_object"] = "K3_MECHA_BODY"
head["source_asset"] = "asset_library/characters/mecha-mascot-v002.blend"
head["source_object"] = "K3_MECHA_HEAD"

# Slightly more receptive white while preserving the canonical material identity.
for mat in {slot.material for obj in (body, head) for slot in obj.material_slots if slot.material}:
    if mat.use_nodes and mat.node_tree:
        bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.92, 0.94, 0.98, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.38

# Root keeps the asset scale and canonical 180-degree turn toward +Y.
root = bpy.data.objects.new(PREFIX + "CHARACTER_ROOT", None)
root.empty_display_type = "PLAIN_AXES"
root.scale = (SCALE, SCALE, SCALE)
root.rotation_euler = (0.0, 0.0, math.pi)
character_col.objects.link(root)
body.parent = root
head.parent = root

# Deformation-only armature. Mesh topology remains unchanged.
arm_data = bpy.data.armatures.new(PREFIX + "RIG_DATA")
rig = bpy.data.objects.new(PREFIX + "RIG", arm_data)
character_col.objects.link(rig)
rig.parent = root
rig.location = (0.0, 0.0, 0.0)
rig.rotation_euler = (0.0, 0.0, 0.0)

rest_bones = {
    "pelvis": ((0.0, 0.0, 0.55), (0.0, 0.0, 0.95)),
    "spine": ((0.0, 0.0, 0.95), (0.0, 0.0, 1.38)),
    "thigh.L": ((-0.18, 0.0, 0.68), (-0.18, 0.0, 0.36)),
    "shin.L": ((-0.18, 0.0, 0.36), (-0.18, 0.0, 0.0)),
    "foot.L": ((-0.18, 0.0, 0.20), (-0.18, 0.0, 0.0)),
    "thigh.R": ((0.18, 0.0, 0.68), (0.18, 0.0, 0.36)),
    "shin.R": ((0.18, 0.0, 0.36), (0.18, 0.0, 0.0)),
    "foot.R": ((0.18, 0.0, 0.20), (0.18, 0.0, 0.0)),
    "upper_arm.L": ((-0.18, 0.0, 1.36), (-0.62, 0.0, 1.36)),
    "forearm.L": ((-0.62, 0.0, 1.36), (-1.08, 0.0, 1.36)),
    "upper_arm.R": ((0.18, 0.0, 1.36), (0.62, 0.0, 1.36)),
    "forearm.R": ((0.62, 0.0, 1.36), (1.08, 0.0, 1.36)),
}
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
for name, (a, b) in rest_bones.items():
    eb = arm_data.edit_bones.new(name)
    eb.head = a
    eb.tail = b
    eb.use_deform = True
bpy.ops.object.mode_set(mode="OBJECT")
rig.select_set(False)

# Deterministic regional weights, stored only on the trial copy.
groups = {name: body.vertex_groups.new(name=name) for name in rest_bones}
for v in body.data.vertices:
    x, y, z = v.co
    weights = {}
    ax = abs(x)
    if z < 0.77 and ax < 0.46:
        side = "L" if x < 0 else "R"
        blend = smooth((z - 0.28) / 0.24)
        weights[f"shin.{side}"] = 1.0 - blend
        weights[f"thigh.{side}"] = blend
        if z > 0.66:
            p = smooth((z - 0.66) / 0.11)
            weights[f"thigh.{side}"] *= 1.0 - 0.45 * p
            weights["pelvis"] = 0.45 * p
        foot_weight = 1.0 - smooth((z - 0.02) / 0.43)
        if foot_weight > 0.0:
            for existing in list(weights):
                weights[existing] *= 1.0 - foot_weight
            weights[f"foot.{side}"] = foot_weight
    elif z > 1.12 and ax > 0.22:
        side = "L" if x < 0 else "R"
        blend = smooth((ax - 0.48) / 0.30)
        weights[f"upper_arm.{side}"] = 1.0 - blend
        weights[f"forearm.{side}"] = blend
        shoulder_blend = 1.0 - smooth((ax - 0.22) / 0.20)
        weights[f"upper_arm.{side}"] *= 1.0 - 0.35 * shoulder_blend
        weights["spine"] = 0.35 * shoulder_blend
    else:
        blend = smooth((z - 0.82) / 0.32)
        weights["pelvis"] = 1.0 - blend
        weights["spine"] = blend
    total = sum(weights.values()) or 1.0
    for name, value in weights.items():
        if value > 0.0001:
            groups[name].add([v.index], value / total, "REPLACE")

arm_mod = body.modifiers.new(PREFIX + "ARMATURE_DEFORM", "ARMATURE")
arm_mod.object = rig
try:
    body.modifiers.move(len(body.modifiers) - 1, 0)
except Exception:
    pass
body["rig_addition"] = "procedural armature and regional weights; no topology change"


def root_plan(frame: int):
    if frame <= 48:
        y, z = -0.62, 0.55
    elif frame <= 61:
        t = smooth((frame - 48) / 13.0)
        y, z = lerp(-0.62, -0.53, t), lerp(0.55, 0.52, t)
    elif frame <= 110:
        t = smooth((frame - 61) / 49.0)
        y, z = lerp(-0.53, -0.34, t), lerp(0.52, floor_z(-0.34) + 0.012, t)
    elif frame <= 158:
        t = smooth((frame - 110) / 48.0)
        y = lerp(-0.34, -0.18, t)
        z = floor_z(y) + lerp(0.012, -0.090, t)
    elif frame <= 256:
        t = (frame - 158) / 98.0
        y = lerp(-0.18, 0.48, t)
        z = floor_z(y) - 0.090 + 0.010 * math.sin(t * math.pi * 8.0)
    elif frame <= 304:
        t = smooth((frame - 256) / 48.0)
        y = lerp(0.48, 0.50, t)
        z = floor_z(y) - 0.090
    else:
        y, z = 0.50, floor_z(0.50) - 0.090
    return Vector((0.0, y, z))


def world_to_root(point: Vector, root_loc: Vector) -> Vector:
    # Root rotation is exactly pi around Z and root scale is uniform.
    d = point - root_loc
    return Vector((-d.x / SCALE, -d.y / SCALE, d.z / SCALE))


def solve_two_bone(a: Vector, target: Vector, l1: float, l2: float, pole: Vector):
    d = target - a
    dist = max(1e-5, min(d.length, l1 + l2 - 1e-4))
    u = d.normalized()
    pole_dir = pole - u * pole.dot(u)
    if pole_dir.length < 1e-5:
        pole_dir = Vector((0.0, 1.0, 0.0))
    pole_dir.normalize()
    along = (l1 * l1 - l2 * l2 + dist * dist) / (2.0 * dist)
    height = math.sqrt(max(0.0, l1 * l1 - along * along))
    elbow = a + u * along + pole_dir * height
    return elbow


def bone_matrix_from_segment(name: str, head_pos: Vector, tail_pos: Vector):
    rest_a = Vector(rest_bones[name][0])
    rest_b = Vector(rest_bones[name][1])
    rest_vec = (rest_b - rest_a).normalized()
    target_vec = (tail_pos - head_pos).normalized()
    rot = rest_vec.rotation_difference(target_vec)
    rest_matrix = arm_data.bones[name].matrix_local.copy()
    m = rot.to_matrix() @ rest_matrix.to_3x3()
    result = m.to_4x4()
    result.translation = head_pos
    return result


def set_segment(name: str, head_pos: Vector, tail_pos: Vector, frame: int):
    pb = rig.pose.bones[name]
    pb.rotation_mode = "QUATERNION"
    pb.matrix = bone_matrix_from_segment(name, head_pos, tail_pos)
    pb.keyframe_insert(data_path="location", frame=frame)
    pb.keyframe_insert(data_path="rotation_quaternion", frame=frame)
    pb.keyframe_insert(data_path="scale", frame=frame)


def stand_pose(arm_swing=0.0, lean=0.0, bob=0.0):
    pose = {}
    pelvis_a = Vector((0.0, 0.0, 0.55 + bob))
    pelvis_b = Vector((0.0, -lean * 0.10, 0.95 + bob))
    spine_a = Vector((0.0, -lean * 0.05, 0.95 + bob))
    spine_b = Vector((0.0, -lean * 0.23, 1.38 + bob))
    pose["pelvis"] = (pelvis_a, pelvis_b)
    pose["spine"] = (spine_a, spine_b)
    for side, sx in (("L", -1.0), ("R", 1.0)):
        hip = Vector((0.18 * sx, 0.0, 0.68 + bob))
        knee = Vector((0.18 * sx, -0.015, 0.36 + bob))
        foot = Vector((0.18 * sx, 0.0, 0.0 + bob))
        pose[f"thigh.{side}"] = (hip, knee)
        pose[f"shin.{side}"] = (knee, foot)
        pose[f"foot.{side}"] = (Vector((0.18 * sx, 0.0, 0.20 + bob)), foot)
        shoulder = Vector((0.18 * sx, -lean * 0.15, 1.36 + bob))
        swing = arm_swing * (-sx)
        elbow = shoulder + Vector((0.14 * sx, swing, -0.415))
        hand = elbow + Vector((0.05 * sx, swing * 0.45, -0.455))
        pose[f"upper_arm.{side}"] = (shoulder, elbow)
        pose[f"forearm.{side}"] = (elbow, hand)
    return pose


def seated_pose(root_loc: Vector, beat=0.0, lean=0.12):
    pose = {}
    pose["pelvis"] = (Vector((0, 0, 0.55)), Vector((0, -0.08 * lean, 0.95)))
    pose["spine"] = (Vector((0, -0.04, 0.95)), Vector((0, -0.20 * lean - 0.05, 1.37)))
    feet = {
        "L": Vector((-0.18, 0.43, 0.18)),
        "R": Vector((0.18, 0.39 + 0.05 * beat, 0.18 + 0.12 * max(0.0, beat))),
    }
    for side, sx in (("L", -1.0), ("R", 1.0)):
        hip = Vector((0.18 * sx, 0.0, 0.68))
        knee = solve_two_bone(hip, feet[side], 0.32, 0.36, Vector((0, 1, 0.15)))
        pose[f"thigh.{side}"] = (hip, knee)
        pose[f"shin.{side}"] = (knee, feet[side])
        foot_head = feet[side] + (knee - feet[side]).normalized() * 0.20
        pose[f"foot.{side}"] = (foot_head, feet[side])
        world_hand = Vector((-0.18 * sx, -0.50, 0.78))
        hand_local = world_to_root(world_hand, root_loc)
        shoulder = Vector((0.18 * sx, -0.03, 1.36))
        elbow = solve_two_bone(shoulder, hand_local, 0.44, 0.46, Vector((0, 0.25, 0.2)))
        pose[f"upper_arm.{side}"] = (shoulder, elbow)
        pose[f"forearm.{side}"] = (elbow, hand_local)
    return pose


def blend_poses(a, b, t):
    out = {}
    for name in rest_bones:
        aa, ab = a[name]
        ba, bb = b[name]
        out[name] = (aa.lerp(ba, t), ab.lerp(bb, t))
    return out


def walk_feet(frame: int):
    contacts = [
        (158, "L", -0.18, "R", -0.23, 170, -0.09),
        (170, "R", -0.09, "L", -0.18, 182, -0.01),
        (182, "L", -0.01, "R", -0.09, 194, 0.07),
        (194, "R", 0.07, "L", -0.01, 207, 0.15),
        (207, "L", 0.15, "R", 0.07, 219, 0.24),
        (219, "R", 0.24, "L", 0.15, 231, 0.32),
        (231, "L", 0.32, "R", 0.24, 243, 0.41),
        (243, "R", 0.41, "L", 0.32, 256, 0.50),
    ]
    for start, stance_side, stance_y, swing_side, swing_from, end, swing_to in contacts:
        if start <= frame <= end:
            t = smooth((frame - start) / (end - start))
            swing_y = lerp(swing_from, swing_to, t)
            lift = 0.050 * math.sin(math.pi * t)
            result = {
                stance_side: Vector(((0.075 if stance_side == "L" else -0.075), stance_y, floor_z(stance_y) + FOOT_PAD)),
                swing_side: Vector(((0.075 if swing_side == "L" else -0.075), swing_y, floor_z(swing_y) + FOOT_PAD + lift)),
            }
            return result, stance_side
    return {
        "L": Vector((0.075, 0.50, floor_z(0.50) + FOOT_PAD)),
        "R": Vector((-0.075, 0.41, floor_z(0.41) + FOOT_PAD)),
    }, "BOTH"


def slope_foot_segment(side: str, foot_world: Vector, root_loc: Vector):
    slope = 1.75 / 1.67
    normal_up = Vector((0.0, -slope, 1.0)).normalized()
    head_world = foot_world + normal_up * (0.20 * SCALE)
    return world_to_root(head_world, root_loc), world_to_root(foot_world, root_loc)


def pose_for_frame(frame: int, root_loc: Vector):
    standing = stand_pose()
    if frame <= 48:
        beat_phase = math.sin(max(0.0, frame - 1) / 12.162 * math.pi)
        return seated_pose(root_loc, beat=max(0.0, beat_phase) * 0.45, lean=0.15), None
    if frame <= 61:
        t = smooth((frame - 48) / 13.0)
        return seated_pose(root_loc, beat=0.0, lean=lerp(0.15, 1.0, t)), None
    if frame <= 110:
        t = smooth((frame - 61) / 49.0)
        seat = seated_pose(root_loc, beat=0.0, lean=1.0)
        base = blend_poses(seat, standing, t)
        if frame <= 94:
            # Re-solve arms to keep the hand bones fixed on the rim during the load phase.
            for side, sx in (("L", -1.0), ("R", 1.0)):
                world_hand = Vector((-0.18 * sx, -0.50, 0.78))
                hand_local = world_to_root(world_hand, root_loc)
                shoulder = Vector((0.18 * sx, -0.12 * (1.0 - t), 1.36))
                elbow = solve_two_bone(shoulder, hand_local, 0.44, 0.46, Vector((0, 0.25, 0.2)))
                base[f"upper_arm.{side}"] = (shoulder, elbow)
                base[f"forearm.{side}"] = (elbow, hand_local)
        return base, None
    if frame < 158:
        t = smooth((frame - 110) / 48.0)
        pose = stand_pose(arm_swing=0.015 * math.sin(t * math.pi), lean=0.08 * (1.0 - t))
        feet_world = {
            "L": Vector((0.075, root_loc.y + 0.018, floor_z(root_loc.y + 0.018) + FOOT_PAD)),
            "R": Vector((-0.075, root_loc.y - 0.018, floor_z(root_loc.y - 0.018) + FOOT_PAD)),
        }
        for side, sx in (("L", -1.0), ("R", 1.0)):
            hip = Vector((0.18 * sx, 0.0, 0.68))
            foot_local = world_to_root(feet_world[side], root_loc)
            knee = solve_two_bone(hip, foot_local, 0.32, 0.36, Vector((0, -1, 0.08)))
            pose[f"thigh.{side}"] = (hip, knee)
            pose[f"shin.{side}"] = (knee, foot_local)
            pose[f"foot.{side}"] = slope_foot_segment(side, feet_world[side], root_loc)
        return pose, "BOTH"
    if frame <= 256:
        feet_world, stance = walk_feet(frame)
        phase = (frame - 158) / 24.5 * math.pi
        pose = stand_pose(arm_swing=0.11 * math.sin(phase), lean=0.10, bob=0.0)
        for side, sx in (("L", -1.0), ("R", 1.0)):
            hip = Vector((0.18 * sx, 0.0, 0.68))
            foot_local = world_to_root(feet_world[side], root_loc)
            knee = solve_two_bone(hip, foot_local, 0.32, 0.36, Vector((0, -1, 0.08)))
            pose[f"thigh.{side}"] = (hip, knee)
            pose[f"shin.{side}"] = (knee, foot_local)
            pose[f"foot.{side}"] = slope_foot_segment(side, feet_world[side], root_loc)
        return pose, stance
    t = smooth((frame - 256) / 48.0) if frame <= 304 else 1.0
    pose = stand_pose(arm_swing=0.0, lean=lerp(0.08, -0.06, t))
    feet_world = {
        "L": Vector((0.075, 0.50, floor_z(0.50) + FOOT_PAD)),
        "R": Vector((-0.075, 0.41, floor_z(0.41) + FOOT_PAD)),
    }
    for side, sx in (("L", -1.0), ("R", 1.0)):
        hip = Vector((0.18 * sx, 0.0, 0.68))
        foot_local = world_to_root(feet_world[side], root_loc)
        knee = solve_two_bone(hip, foot_local, 0.32, 0.36, Vector((0, -1, 0.08)))
        pose[f"thigh.{side}"] = (hip, knee)
        pose[f"shin.{side}"] = (knee, foot_local)
        pose[f"foot.{side}"] = slope_foot_segment(side, feet_world[side], root_loc)
    if frame >= 304:
        open_t = smooth((frame - 304) / 49.0)
        for side, sx in (("L", -1.0), ("R", 1.0)):
            shoulder = Vector((0.18 * sx, 0.0, 1.36))
            elbow = shoulder + Vector((0.20 * sx * (1 + 0.35 * open_t), 0.01, -0.39))
            hand = elbow + Vector((0.09 * sx * (1 + 0.45 * open_t), -0.02, -0.44))
            pose[f"upper_arm.{side}"] = (shoulder, elbow)
            pose[f"forearm.{side}"] = (elbow, hand)
    return pose, "BOTH"


# Dense root and body animation ensures planted contacts do not depend on Bezier interpolation.
stance_log = {}
for frame in range(1, 361):
    rloc = root_plan(frame)
    root.location = rloc
    key(root, "location", frame)
    pose, stance = pose_for_frame(frame, rloc)
    if stance:
        stance_log[str(frame)] = stance
    for name, (a, b) in pose.items():
        set_segment(name, a, b, frame)
    # Separate head control: breath first, operator-like lag, then slow upward look.
    if frame <= 61:
        head.location = (0.0, -0.025 * math.sin(frame / 24.0), 1.798016 + 0.012 * math.sin(frame / 18.0))
        head.rotation_euler = (0.02, 0.0, 0.0)
    elif frame <= 256:
        t = smooth((frame - 61) / 195.0)
        head.location = (0.0, lerp(-0.025, -0.045, t), 1.798016 + 0.008 * math.sin(frame / 12.0))
        head.rotation_euler = (lerp(0.02, -0.05, t), 0.0, 0.025 * math.sin(frame / 30.0))
    else:
        t = smooth((frame - 280) / 73.0)
        head.location = (0.0, -0.045, 1.798016 + 0.025 * t)
        head.rotation_euler = (lerp(-0.05, -0.34, t), 0.0, lerp(0.0, -0.035, t))
    key(head, "location", frame)
    key(head, "rotation_euler", frame)

set_linear(root)
set_linear(head)
for pb in rig.pose.bones:
    set_linear(pb)

# Single continuous CAMERA / TARGET / FOCUS rig.
camera_col = ensure_collection(PREFIX + "CAMERA_RIG")
camera_data = bpy.data.cameras.new(PREFIX + "CAMERA_DATA")
camera = bpy.data.objects.new(PREFIX + "CAMERA", camera_data)
camera_col.objects.link(camera)
target = bpy.data.objects.new(PREFIX + "CAMERA_TARGET", None)
focus = bpy.data.objects.new(PREFIX + "CAMERA_FOCUS", None)
camera_col.objects.link(target)
camera_col.objects.link(focus)
track = camera.constraints.new("TRACK_TO")
track.name = PREFIX + "TRACK_TARGET"
track.target = target
track.track_axis = "TRACK_NEGATIVE_Z"
track.up_axis = "UP_Y"
camera_data.dof.use_dof = True
camera_data.dof.focus_object = focus
camera_data.dof.aperture_fstop = 4.5
camera_data.clip_start = 0.08
camera_data.clip_end = 100.0
scene.camera = camera

camera_keys = {
    1: ((0.95, -3.00, 1.45), (0.0, -0.53, 1.08), (0.0, -0.55, 1.18), 55.0),
    61: ((1.02, -2.86, 1.37), (0.0, -0.48, 1.14), (0.0, -0.47, 1.22), 56.0),
    110: ((0.80, -3.60, 1.82), (0.0, -0.28, 1.48), (0.0, -0.30, 1.52), 50.0),
    207: ((0.42, -5.25, 2.62), (0.0, 0.10, 2.05), (0.0, 0.10, 2.08), 42.0),
    256: ((0.20, -6.55, 3.25), (0.0, 0.34, 2.36), (0.0, 0.40, 2.30), 37.0),
    304: ((0.00, -7.85, 3.90), (0.0, 0.43, 2.56), (0.0, 0.48, 2.55), 34.0),
    353: ((-0.08, -8.25, 4.18), (0.0, 0.49, 2.69), (0.0, 0.50, 2.65), 32.0),
    360: ((-0.08, -8.25, 4.18), (0.0, 0.49, 2.69), (0.0, 0.50, 2.65), 32.0),
}
for frame, (cam_loc, tar_loc, foc_loc, lens) in camera_keys.items():
    camera.location = cam_loc
    target.location = tar_loc
    focus.location = foc_loc
    camera_data.lens = lens
    key(camera, "location", frame)
    key(target, "location", frame)
    key(focus, "location", frame)
    camera_data.keyframe_insert(data_path="lens", frame=frame)
for owner in (camera, target, focus, camera_data):
    ad = getattr(owner, "animation_data", None)
    action = getattr(ad, "action", None) if ad else None
    if action:
        fcurves = list(getattr(action, "fcurves", []))
        if not fcurves:
            for layer in action.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        fcurves.extend(bag.fcurves)
        for fc in fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"

# Re-time the inherited 3D playhead into four musical two-bar sweeps.
playhead = bpy.data.objects.get("USTUDIO_PLAYHEAD_BACK")
if playhead:
    playhead.animation_data_clear()
    original_y, original_z = 1.24, 3.91
    for frame, x in ((1, -2.82), (62, 0.0), (110, 2.82), (111, -2.82), (159, 0.0),
                     (207, 2.82), (208, -2.82), (256, 0.0), (304, 2.82), (305, -2.82),
                     (353, 0.0), (360, 0.42)):
        playhead.location = (x, original_y, original_z)
        key(playhead, "location", frame)
    set_linear(playhead)

# Apply the repository's versioned Drumboiii light rig, then recalibrate it for screen light.
scene.frame_set(304)
lighting_globals = {"UNRECORDED_PARAMS": {
    "target_collection": PREFIX + "CHARACTER",
    "preset": "drumboiii-layered",
    "intensity": 0.22,
    "mute_existing_lights": False,
    "configure_world": True,
    "world_strength": 0.28,
    "visible_world_strength": 0.05,
    "render_engine": "KEEP",
    "view_transform": "AgX",
}}
exec(compile((ROOT / "workflows/scripts/studio_lighting.py").read_text(), "studio_lighting.py", "exec"), lighting_globals)
drum_col = bpy.data.collections.get("USTUDIO_LIGHTING")
if drum_col:
    drum_col.name = PREFIX + "LIGHTING_DRUMBOIII"
color_map = {
    "USTUDIO_LIGHTING_SUN_REFLECTION": (0.65, 0.82, 1.0),
    "USTUDIO_LIGHTING_BACK_SHAPE": (0.92, 0.18, 1.0),
    "USTUDIO_LIGHTING_SIDE_GLIMMER_A": (0.32, 1.0, 0.42),
    "USTUDIO_LIGHTING_SIDE_GLIMMER_B": (0.18, 0.58, 1.0),
    "USTUDIO_LIGHTING_DETAIL_RETURN": (1.0, 0.34, 0.68),
}
for name, color in color_map.items():
    obj = bpy.data.objects.get(name)
    if obj:
        obj.data.color = color

# Personal playhead interaction: a narrow acid-lime spot follows the 3D line.
fx_col = ensure_collection(PREFIX + "LIGHT_FX")
scan_data = bpy.data.lights.new(PREFIX + "PLAYHEAD_SCAN_DATA", "SPOT")
scan_data.energy = 220.0
scan_data.color = (0.48, 1.0, 0.08)
scan_data.spot_size = math.radians(24)
scan_data.spot_blend = 0.35
scan = bpy.data.objects.new(PREFIX + "PLAYHEAD_SCAN", scan_data)
fx_col.objects.link(scan)
scan_track = scan.constraints.new("TRACK_TO")
scan_track.name = PREFIX + "SCAN_TRACK"
scan_track.target = root
scan_track.track_axis = "TRACK_NEGATIVE_Z"
scan_track.up_axis = "UP_Y"
for frame, x in ((1, -2.82), (62, 0.0), (110, 2.82), (111, -2.82), (159, 0.0),
                 (207, 2.82), (208, -2.82), (256, 0.0), (304, 2.82), (305, -2.82),
                 (353, 0.0), (360, 0.42)):
    scan.location = (x, 0.95, 4.25)
    key(scan, "location", frame)
set_linear(scan)

# Markers drive the versioned render-keyframes gate.
for marker in list(scene.timeline_markers):
    scene.timeline_markers.remove(marker)
for name, frame in (
    ("K3_EDGE_SEATED", 1), ("K3_EDGE_ANTICIPATION", 61), ("K3_EDGE_STAND", 110),
    ("K3_EDGE_WALK", 207), ("K3_EDGE_STOP", 256), ("K3_EDGE_LOOK", 304),
    ("K3_EDGE_CLIMAX", 353), ("K3_EDGE_FINAL", 360),
):
    scene.timeline_markers.new(name, frame=frame)

# Shot manifest and analytical build record.
shot_manifest = {
    "schema_version": 1,
    "trial_id": "k3-edge-rise-reveal-codex-v001",
    "camera": camera.name,
    "target": target.name,
    "focus": focus.name,
    "frame_range": [1, 360],
    "fps": 30,
    "continuous_single_shot": True,
    "lens_mm": {str(f): values[3] for f, values in camera_keys.items()},
    "camera_positions": {str(f): list(values[0]) for f, values in camera_keys.items()},
    "move": "K1 intimate low, K2 opposing dip, K3 dolly-crane out/up, K4 short wide recovery",
    "audio_bpm": 148.0,
    "downbeats": [12, 61, 110, 158, 207, 256, 304, 353],
    "personal_idea": "Acid-lime playhead scan crosses the white body on frame 353.",
}
(TRIAL / "shot-manifest.json").write_text(json.dumps(shot_manifest, indent=2) + "\n")
(TRIAL / "diagnostics/build-record.json").write_text(json.dumps({
    "source_template": "projects/fl-studio-box-semantic-template/FL_Studio_Box_Semantic_Template.blend",
    "source_character": "asset_library/characters/mecha-mascot-v002.blend",
    "mesh_topology_changed": False,
    "rig_added": True,
    "rig_bones": list(rest_bones),
    "character_scale": SCALE,
    "stance_schedule": stance_log,
}, indent=2) + "\n")

scene.frame_set(1)
trial_blend = TRIAL / "scene/trial.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(trial_blend), check_existing=False, relative_remap=True)
print("K3_BUILD_RESULT=" + json.dumps({
    "trial_blend": str(trial_blend),
    "objects": len(scene.objects),
    "camera": camera.name,
    "character": [body.name, head.name],
    "rig": rig.name,
    "saved": True,
}))
