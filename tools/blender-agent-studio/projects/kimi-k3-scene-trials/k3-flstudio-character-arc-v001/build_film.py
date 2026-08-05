"""Build the USTUDIO character film non-destructively inside scene/trial.blend.

Phases are deliberately separated so clay, camera and lighting can be gated.
The script saves only the already-created trial copy.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

import bpy
from mathutils import Vector


TRIAL = Path(__file__).resolve().parent
PHASE = os.environ.get("USTUDIO_BUILD_PHASE", "clay")
EXPECTED_BLEND = (TRIAL / "scene" / "trial.blend").resolve()
PREFIX = "USTUDIO_"
WORK_COLLECTION = "K3_FLSTUDIO_CHARACTER_ARC_V001_WORK"

if Path(bpy.data.filepath).resolve() != EXPECTED_BLEND:
    raise RuntimeError(f"Refusing to save outside trial copy: {bpy.data.filepath}")

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = 406
scene.render.fps = 30
scene.render.fps_base = 1.0


def remove_collection(name: str) -> None:
    collection = bpy.data.collections.get(name)
    if not collection:
        return
    for child in list(collection.children):
        remove_collection(child.name)
    for obj in list(collection.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(collection)


def new_collection(name: str, parent=None):
    collection = bpy.data.collections.new(name)
    (parent or scene.collection).children.link(collection)
    return collection


def material_principled(name, base, roughness=0.5, metallic=0.0, emission=None, emission_strength=0.0, transmission=0.0, alpha=1.0):
    old = bpy.data.materials.get(name)
    if old:
        bpy.data.materials.remove(old)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = transmission
    if emission is not None:
        socket = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        if socket:
            socket.default_value = (*emission, 1.0)
        strength = bsdf.inputs.get("Emission Strength")
        if strength:
            strength.default_value = emission_strength
    mat.diffuse_color = (*base, alpha)
    if alpha < 1.0:
        mat.surface_render_method = "DITHERED"
    return mat


def link_object(obj, collection):
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)
    return obj


def cube(name, collection, location, dimensions, material=None, parent=None, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    link_object(obj, collection)
    if parent:
        matrix = obj.matrix_world.copy()
        obj.parent = parent
        obj.matrix_world = matrix
    if material:
        obj.data.materials.append(material)
    if bevel > 0:
        modifier = obj.modifiers.new(name + "_BEVEL", "BEVEL")
        modifier.width = bevel
        modifier.segments = 3
    return obj


def sphere(name, collection, parent, local_location, scale, material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, location=(0, 0, 0))
    obj = bpy.context.object
    obj.name = name
    link_object(obj, collection)
    obj.parent = parent
    obj.location = local_location
    obj.scale = scale
    obj.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return obj


def capsule(name, collection, parent, local_location, radius, length, material, axis="Z"):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, location=(0, 0, 0))
    obj = bpy.context.object
    obj.name = name
    link_object(obj, collection)
    obj.parent = parent
    obj.location = local_location
    if axis == "Z":
        obj.scale = (radius, radius, length / 2 + radius)
    elif axis == "X":
        obj.scale = (length / 2 + radius, radius, radius)
    else:
        obj.scale = (radius, length / 2 + radius, radius)
    obj.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return obj


def empty(name, collection, parent=None, location=(0, 0, 0), display="PLAIN_AXES"):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = display
    obj.empty_display_size = 0.025
    collection.objects.link(obj)
    obj.parent = parent
    obj.location = location
    return obj


def key_value(obj, path, frame, value, interpolation="BEZIER"):
    setattr(obj, path, value)
    obj.keyframe_insert(data_path=path, frame=frame)
    animation = obj.animation_data
    if not animation or not animation.action:
        return
    curves = []
    action = animation.action
    try:
        curves = list(action.fcurves)
    except Exception:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    curves.extend(bag.fcurves)
    for curve in curves:
        if curve.data_path == path:
            for point in curve.keyframe_points:
                if abs(point.co.x - frame) < 0.01:
                    point.interpolation = interpolation
                    if interpolation == "BEZIER":
                        point.handle_left_type = "AUTO_CLAMPED"
                        point.handle_right_type = "AUTO_CLAMPED"


def key_location(obj, frame, value, interpolation="BEZIER"):
    key_value(obj, "location", frame, value, interpolation)


def key_rotation(obj, frame, degrees, interpolation="BEZIER"):
    value = tuple(math.radians(v) for v in degrees)
    key_value(obj, "rotation_euler", frame, value, interpolation)


def key_scale(obj, frame, value, interpolation="BEZIER"):
    key_value(obj, "scale", frame, value, interpolation)


def track_to(obj, target):
    constraint = obj.constraints.new("TRACK_TO")
    constraint.name = obj.name + "_TRACK"
    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"
    return constraint


def point_light_at(obj, target):
    direction = target.matrix_world.translation - obj.matrix_world.translation
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def build_clay():
    remove_collection(WORK_COLLECTION)
    work = new_collection(WORK_COLLECTION)
    work["ustudio_schema"] = 1
    work["ustudio_trial"] = "k3-flstudio-character-arc-v001"
    float_root = bpy.data.objects.get("USTUDIO_BOX_FLOAT_ROOT")
    if not float_root:
        raise RuntimeError("USTUDIO_BOX_FLOAT_ROOT missing")

    matte = material_principled("M_USTUDIO_CHARACTER_PEARL", (0.52, 0.56, 0.62), roughness=0.62)
    glass = material_principled("M_USTUDIO_INTERFACE_GLASS", (0.055, 0.11, 0.12), roughness=0.2, metallic=0.05, transmission=0.24, alpha=0.68)
    lime = material_principled("M_USTUDIO_INTERFACE_LIME", (0.15, 0.5, 0.025), roughness=0.28, emission=(0.34, 1.0, 0.04), emission_strength=5.0)
    magenta = material_principled("M_USTUDIO_INTERFACE_MAGENTA", (0.42, 0.03, 0.26), roughness=0.3, emission=(1.0, 0.05, 0.55), emission_strength=3.5)

    bridge = cube("USTUDIO_INTERFACE_BRIDGE", work, (0.0, 0.18, 1.91), (6.5, 0.86, 0.07), glass, float_root, 0.035)
    bridge["ustudio_role"] = "visible_horizontal_support"
    bridge["ustudio_top_z_local"] = 1.945
    for x, color_mat, suffix in [(-3.17, lime, "L"), (3.17, magenta, "R")]:
        rail = cube(f"USTUDIO_INTERFACE_BRIDGE_EDGE_{suffix}", work, (x, 0.18, 1.955), (0.045, 0.88, 0.045), color_mat, float_root, 0.015)
        rail["ustudio_role"] = "support_edge_and_contact_readability"
    for index, (x, y) in enumerate([(-2.85, -0.08), (2.85, -0.08), (-2.85, 0.44), (2.85, 0.44)], 1):
        anchor = cube(f"USTUDIO_INTERFACE_BRIDGE_ANCHOR_{index:02d}", work, (x, y, 1.48), (0.08, 0.08, 0.88), lime if x < 0 else magenta, float_root, 0.02)
        anchor["ustudio_role"] = "visible_structural_anchor"

    rig_root = empty("USTUDIO_CHARACTER_ROOT", work, float_root, (0.0, 0.14, 1.945), "CIRCLE")
    rig_root["ustudio_role"] = "faceless_humanoid_rig_root"
    rig_root["ustudio_height_m"] = 0.31
    rig_root["ustudio_support"] = "USTUDIO_INTERFACE_BRIDGE"
    hips = empty("USTUDIO_CHAR_RIG_HIPS", work, rig_root, (0, 0, 0.145))
    torso = empty("USTUDIO_CHAR_RIG_TORSO", work, hips, (0, 0, 0.015))
    neck = empty("USTUDIO_CHAR_RIG_NECK", work, torso, (0, 0, 0.105))

    sphere("USTUDIO_CHAR_PELVIS", work, hips, (0, 0, 0.0), (0.046, 0.032, 0.035), matte)
    sphere("USTUDIO_CHAR_TORSO", work, torso, (0, 0, 0.05), (0.055, 0.035, 0.072), matte)
    sphere("USTUDIO_CHAR_HEAD", work, neck, (0, -0.002, 0.03), (0.041, 0.038, 0.046), matte)

    joints = {"ROOT": rig_root, "HIPS": hips, "TORSO": torso, "NECK": neck}
    for side, sign in [("L", -1), ("R", 1)]:
        shoulder = empty(f"USTUDIO_CHAR_RIG_SHOULDER_{side}", work, torso, (sign * 0.052, 0, 0.075))
        elbow = empty(f"USTUDIO_CHAR_RIG_ELBOW_{side}", work, shoulder, (0, 0, -0.062))
        wrist = empty(f"USTUDIO_CHAR_RIG_WRIST_{side}", work, elbow, (0, 0, -0.055))
        capsule(f"USTUDIO_CHAR_UPPER_ARM_{side}", work, shoulder, (0, 0, -0.031), 0.015, 0.048, matte)
        capsule(f"USTUDIO_CHAR_FOREARM_{side}", work, elbow, (0, 0, -0.028), 0.013, 0.043, matte)
        sphere(f"USTUDIO_CHAR_HAND_{side}", work, wrist, (0, -0.002, -0.007), (0.015, 0.012, 0.019), matte)

        hip = empty(f"USTUDIO_CHAR_RIG_HIP_{side}", work, hips, (sign * 0.029, 0, -0.012))
        knee = empty(f"USTUDIO_CHAR_RIG_KNEE_{side}", work, hip, (0, 0, -0.066))
        ankle = empty(f"USTUDIO_CHAR_RIG_ANKLE_{side}", work, knee, (0, 0, -0.061))
        capsule(f"USTUDIO_CHAR_THIGH_{side}", work, hip, (0, 0, -0.033), 0.019, 0.052, matte)
        capsule(f"USTUDIO_CHAR_SHIN_{side}", work, knee, (0, 0, -0.031), 0.016, 0.049, matte)
        capsule(f"USTUDIO_CHAR_FOOT_{side}", work, ankle, (0, -0.018, -0.003), 0.014, 0.036, matte, axis="Y")
        joints.update({f"SHOULDER_{side}": shoulder, f"ELBOW_{side}": elbow, f"WRIST_{side}": wrist, f"HIP_{side}": hip, f"KNEE_{side}": knee, f"ANKLE_{side}": ankle})

    # S1: awake — stable feet, head and torso carry all expression.
    for frame, root_loc in [(1, (0, 0.14, 1.945)), (9, (0, 0.14, 1.945)), (105, (0, 0.14, 1.945))]:
        key_location(rig_root, frame, root_loc, "CONSTANT" if frame in (1, 105) else "BEZIER")
    key_rotation(torso, 9, (15, 0, 0))
    key_rotation(torso, 57, (0, 0, -8))
    key_rotation(torso, 105, (-4, 0, 9))
    key_rotation(neck, 9, (28, 0, -12))
    key_rotation(neck, 45, (2, 0, -22))
    key_rotation(neck, 75, (-12, 0, 18))
    key_rotation(neck, 105, (-5, 0, 4))
    key_rotation(joints["SHOULDER_L"], 9, (5, 0, 8))
    key_rotation(joints["SHOULDER_R"], 9, (5, 0, -8))
    key_rotation(joints["SHOULDER_L"], 105, (-6, 0, 14))
    key_rotation(joints["SHOULDER_R"], 105, (-6, 0, -14))

    # S2: seated on the real lower frame; thighs forward, shins vertical.
    for frame in (106, 202):
        key_location(rig_root, frame, (0, -1.06, 0.615), "CONSTANT")
        key_location(hips, frame, (0, 0, 0.145))
        key_rotation(torso, frame, (-10, 0, 0))
        key_rotation(neck, frame, (-5, 0, 0))
        for side in ("L", "R"):
            key_rotation(joints[f"HIP_{side}"], frame, (-88, 0, 0))
            key_rotation(joints[f"KNEE_{side}"], frame, (88, 0, 0))
            key_rotation(joints[f"SHOULDER_{side}"], frame, (20, 0, -18 if side == "L" else 18))
    # Beat the right foot, with the knee as the causal hinge.
    for frame, angle in [(106, 88), (118, 72), (130, 88), (142, 72), (154, 88), (166, 72), (178, 88), (190, 72), (202, 88)]:
        key_rotation(joints["KNEE_R"], frame, (angle, 0, 0), "BEZIER")

    # S3: compact physical run; the character starts ahead of the real playhead.
    key_location(rig_root, 203, (0.50, 0.16, 1.945), "LINEAR")
    key_location(rig_root, 251, (1.07, 0.16, 1.945), "LINEAR")
    key_location(rig_root, 260, (1.07, 0.16, 1.945), "CONSTANT")
    key_location(rig_root, 270, (1.12, 0.16, 1.945), "LINEAR")
    key_location(rig_root, 298, (1.70, 0.16, 1.945), "LINEAR")
    for frame in [203, 215, 227, 239, 251, 270, 282, 294]:
        phase = 1 if ((frame - 203) // 12) % 2 == 0 else -1
        key_rotation(joints["HIP_L"], frame, (phase * 38, 0, 0), "BEZIER")
        key_rotation(joints["HIP_R"], frame, (-phase * 38, 0, 0), "BEZIER")
        key_rotation(joints["KNEE_L"], frame, (32 if phase < 0 else 8, 0, 0), "BEZIER")
        key_rotation(joints["KNEE_R"], frame, (32 if phase > 0 else 8, 0, 0), "BEZIER")
        key_rotation(joints["SHOULDER_L"], frame, (-phase * 35, 0, 0), "BEZIER")
        key_rotation(joints["SHOULDER_R"], frame, (phase * 35, 0, 0), "BEZIER")
        key_rotation(torso, frame, (10, 0, 0), "BEZIER")
    key_rotation(neck, 227, (0, 0, -32))
    key_rotation(neck, 239, (0, 0, 0))
    # Impact, slump, recovery.
    for frame in (251, 260):
        key_rotation(joints["HIP_L"], frame, (4, 0, 0))
        key_rotation(joints["HIP_R"], frame, (-4, 0, 0))
        key_rotation(joints["KNEE_L"], frame, (8, 0, 0))
        key_rotation(joints["KNEE_R"], frame, (8, 0, 0))
    key_rotation(torso, 251, (18, 0, 0))
    key_rotation(torso, 260, (30, 0, 0))
    key_rotation(neck, 260, (18, 0, 0))
    key_rotation(torso, 270, (12, 0, 0))
    key_rotation(neck, 270, (5, 0, 0))

    # Face the travel direction during the chase; cuts use constant orientation
    # changes so no hidden spin or drift occurs between scenes.
    for frame, rotation in [(1, 0), (105, 0), (106, 0), (202, 0), (203, 90), (298, 90), (299, 0), (406, 0)]:
        key_rotation(rig_root, frame, (0, 0, rotation), "CONSTANT")

    # S4: crouch/contact → rise → hero. The right hand visibly reaches the deck.
    key_location(rig_root, 299, (0, 0.16, 1.945), "CONSTANT")
    key_location(rig_root, 348, (0, 0.16, 1.945))
    key_location(rig_root, 396, (0, 0.16, 1.945))
    key_location(hips, 299, (0, 0, 0.095))
    key_location(hips, 348, (0, 0, 0.135))
    key_location(hips, 386, (0, 0, 0.145))
    key_location(hips, 396, (0, 0, 0.145))
    for side, sign in [("L", -1), ("R", 1)]:
        key_rotation(joints[f"HIP_{side}"], 299, (-48, sign * 4, 0))
        key_rotation(joints[f"KNEE_{side}"], 299, (92, 0, 0))
        key_rotation(joints[f"HIP_{side}"], 348, (-18, 0, 0))
        key_rotation(joints[f"KNEE_{side}"], 348, (34, 0, 0))
        key_rotation(joints[f"HIP_{side}"], 386, (0, 0, 0))
        key_rotation(joints[f"KNEE_{side}"], 386, (0, 0, 0))
        key_rotation(joints[f"HIP_{side}"], 396, (0, 0, 0))
        key_rotation(joints[f"KNEE_{side}"], 396, (0, 0, 0))
    key_rotation(torso, 299, (38, 0, -10))
    key_rotation(neck, 299, (18, 0, 12))
    key_rotation(joints["SHOULDER_R"], 299, (-28, 0, 8))
    key_rotation(joints["ELBOW_R"], 299, (12, 0, 0))
    key_rotation(joints["SHOULDER_L"], 299, (22, 0, -20))
    key_rotation(torso, 348, (8, 0, 0))
    key_rotation(neck, 348, (-10, 0, 0))
    key_rotation(joints["SHOULDER_R"], 348, (-8, 0, 12))
    key_rotation(joints["SHOULDER_L"], 348, (-8, 0, -12))
    key_rotation(torso, 386, (-4, 0, 0))
    key_rotation(neck, 386, (-16, 0, 0))
    key_rotation(joints["SHOULDER_R"], 386, (-34, 0, 28))
    key_rotation(joints["SHOULDER_L"], 386, (-34, 0, -28))
    key_rotation(torso, 396, (0, 0, 0))
    key_rotation(neck, 396, (-10, 0, 0))
    key_rotation(joints["SHOULDER_R"], 396, (-28, 0, 24))
    key_rotation(joints["SHOULDER_L"], 396, (-28, 0, -24))

    # Musical markers derived from the source audio; media markers remain untouched.
    for marker in list(scene.timeline_markers):
        if marker.name.startswith("USTUDIO_MUSIC_") or marker.name.startswith("USTUDIO_SCENE_"):
            scene.timeline_markers.remove(marker)
    for number, frame in enumerate([9, 57, 106, 154, 203, 251, 299, 348, 396], 1):
        scene.timeline_markers.new(f"USTUDIO_MUSIC_BAR_{number:02d}", frame=frame)
    scene.timeline_markers.new("USTUDIO_MUSIC_DROP", frame=251)
    for name, frame in [("AWAKENING", 9), ("PAUSE", 106), ("RUN", 203), ("COMMUNION", 299), ("FINAL_HOLD", 397)]:
        scene.timeline_markers.new(f"USTUDIO_SCENE_{name}", frame=frame)

    scene["ustudio_character_arc"] = "discovery > contemplation > resistance > communion"
    scene["ustudio_physics_rule"] = "visible horizontal interface bridge; no invisible floor"
    scene["ustudio_audio_grid_status"] = "148.8 BPM heuristic; downbeats checked by waveform and require final listening gate"
    scene.frame_set(9)
    bpy.ops.wm.save_as_mainfile(filepath=str(EXPECTED_BLEND))


def camera_object(name, collection, parent, lens, clip=0.008, fstop=3.2):
    data = bpy.data.cameras.new(name + "_DATA")
    data.lens = lens
    data.clip_start = clip
    data.clip_end = 100.0
    data.dof.use_dof = True
    data.dof.aperture_fstop = fstop
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    obj.parent = parent
    return obj


def build_cameras():
    work = bpy.data.collections.get(WORK_COLLECTION)
    float_root = bpy.data.objects.get("USTUDIO_BOX_FLOAT_ROOT")
    char_root = bpy.data.objects.get("USTUDIO_CHARACTER_ROOT")
    if not work or not float_root or not char_root:
        raise RuntimeError("Clay phase missing")
    old = bpy.data.collections.get("USTUDIO_CHARACTER_CAMERAS")
    if old:
        remove_collection(old.name)
    cameras = new_collection("USTUDIO_CHARACTER_CAMERAS", work)

    # S1 — child of float root, worm-eye push and delayed target tilt.
    target1 = empty("USTUDIO_TARGET_SCENE1_AWAKENING", cameras, float_root, (0, 0.14, 2.09))
    focus1 = empty("USTUDIO_FOCUS_SCENE1_AWAKENING", cameras, float_root, (0, 0.14, 2.12))
    cam1 = camera_object("USTUDIO_CAM_SCENE1_AWAKENING", cameras, float_root, 18, 0.005, 3.5)
    track_to(cam1, target1)
    cam1.data.dof.focus_object = focus1
    for frame, loc, target in [
        (1, (0.06, -0.72, 1.985), (0, 0.14, 2.07)),
        (9, (0.06, -0.72, 1.985), (0, 0.14, 2.07)),
        (18, (0.08, -0.76, 1.98), (0, 0.14, 2.06)),
        (91, (-0.04, -0.43, 2.005), (0, 0.14, 2.18)),
        (105, (-0.02, -0.45, 2.005), (0, 0.14, 2.17)),
    ]:
        key_location(cam1, frame, loc)
        key_location(target1, frame, target)
        key_location(focus1, frame, target)
    for frame, lens in [(1, 18), (18, 17.5), (91, 20), (105, 20)]:
        cam1.data.lens = lens
        cam1.data.keyframe_insert("lens", frame=frame)

    # S2 — world-space macro foot, opposite anticipation, then crane/pull-back reveal.
    target2 = empty("USTUDIO_TARGET_SCENE2_PAUSE", cameras, None, (0, -1.0, 2.05))
    focus2 = empty("USTUDIO_FOCUS_SCENE2_PAUSE", cameras, None, (0.03, -1.12, 1.92))
    cam2 = camera_object("USTUDIO_CAM_SCENE2_PAUSE", cameras, None, 55, 0.01, 2.8)
    track_to(cam2, target2)
    cam2.data.dof.focus_object = focus2
    s2 = [
        (106, (0.10, -2.10, 2.08), (0.04, -1.08, 2.10), 55),
        (116, (0.16, -2.02, 2.06), (0.04, -1.08, 2.11), 58),
        (188, (0.20, -15.2, 4.25), (0, 0.10, 4.10), 48),
        (202, (0.0, -15.0, 4.18), (0, 0.10, 4.08), 50),
    ]
    for frame, loc, target, lens in s2:
        key_location(cam2, frame, loc)
        key_location(target2, frame, target)
        key_location(focus2, frame, target)
        cam2.data.lens = lens
        cam2.data.keyframe_insert("lens", frame=frame)

    # S3 — frontal relative to +X run direction, matched retreat plus bounded shake.
    target3 = empty("USTUDIO_TARGET_SCENE3_RUN", cameras, char_root, (0, 0, 0.155))
    focus3 = empty("USTUDIO_FOCUS_SCENE3_RUN", cameras, char_root, (0, 0, 0.155))
    cam3 = camera_object("USTUDIO_CAM_SCENE3_RUN", cameras, char_root, 48, 0.008, 4.0)
    track_to(cam3, target3)
    cam3.data.dof.focus_object = focus3
    run_frames = [203, 215, 227, 239, 251, 260, 270, 282, 294, 298]
    for index, frame in enumerate(run_frames):
        shake_y = 0.0 if frame in (203, 251, 260, 298) else (0.018 if index % 2 else -0.018)
        shake_z = 0.0 if frame in (203, 251, 260, 298) else (0.012 if index % 2 else -0.012)
        key_location(cam3, frame, (shake_y, -1.25, 0.165 + shake_z), "BEZIER")
        key_location(target3, frame, (0, 0, 0.155), "CONSTANT")
        key_location(focus3, frame, (0, 0, 0.155), "CONSTANT")
    cam3["ustudio_shake_max_m"] = 0.018
    cam3["ustudio_drift_rule"] = "camera is structurally parented to character root; local forward offset is 1.25m"

    # S4 — 3D spiral: high/wide, short opposite anticipation, 360 travel, hard settle.
    pivot4 = empty("USTUDIO_PIVOT_SCENE4_COMMUNION", cameras, float_root, (0, 0.16, 2.10), "SPHERE")
    target4 = empty("USTUDIO_TARGET_SCENE4_COMMUNION", cameras, float_root, (0, 0.16, 2.08))
    focus4 = empty("USTUDIO_FOCUS_SCENE4_COMMUNION", cameras, float_root, (0, 0.16, 2.08))
    cam4 = camera_object("USTUDIO_CAM_SCENE4_COMMUNION", cameras, pivot4, 35, 0.008, 2.4)
    track_to(cam4, target4)
    cam4.data.dof.focus_object = focus4
    orbit_keys = [
        (299, 0, (0, -1.02, 2.45), 35, (0, 0.16, 2.05)),
        (307, -12, (0, -1.04, 2.50), 34, (0, 0.16, 2.04)),
        (386, 348, (0, -1.16, 0.18), 82, (0, 0.16, 2.15)),
        (396, 360, (0, -1.25, 0.12), 85, (0, 0.16, 2.17)),
        (406, 360, (0, -1.25, 0.12), 85, (0, 0.16, 2.17)),
    ]
    for frame, angle, local, lens, target in orbit_keys:
        key_rotation(pivot4, frame, (0, 0, angle))
        key_location(cam4, frame, local)
        key_location(target4, frame, target)
        key_location(focus4, frame, target)
        cam4.data.lens = lens
        cam4.data.keyframe_insert("lens", frame=frame)
    pivot4["ustudio_corridor"] = "radius 0.76-1.04m; y back limit 1.20; sampled every 45deg"

    # Bind cuts to the existing scene rather than duplicating scenes.
    bindings = [("USTUDIO_CUT_SCENE1", 1, cam1), ("USTUDIO_CUT_SCENE2", 106, cam2), ("USTUDIO_CUT_SCENE3", 203, cam3), ("USTUDIO_CUT_SCENE4", 299, cam4)]
    for marker in list(scene.timeline_markers):
        if marker.name.startswith("USTUDIO_CUT_"):
            scene.timeline_markers.remove(marker)
    for name, frame, camera in bindings:
        marker = scene.timeline_markers.new(name, frame=frame)
        marker.camera = camera
    scene.camera = cam1
    scene.frame_set(9)

    manifest = {
        "schema_version": 1,
        "camera": cam1.name,
        "camera_names": [cam1.name, cam2.name, cam3.name, cam4.name],
        "cuts": [{"frame": frame, "camera": camera.name} for _, frame, camera in bindings],
        "style": "Drumboiii K1 pose, K2 anticipation, K3 travel, K4 recovery",
        "saved": True,
    }
    (TRIAL / "shot-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(EXPECTED_BLEND))


def add_area(name, collection, parent, location, energy, size, color, target):
    data = bpy.data.lights.new(name + "_DATA", "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    obj.parent = parent
    obj.location = location
    track_to(obj, target)
    return obj


def build_look():
    work = bpy.data.collections.get(WORK_COLLECTION)
    float_root = bpy.data.objects.get("USTUDIO_BOX_FLOAT_ROOT")
    char_root = bpy.data.objects.get("USTUDIO_CHARACTER_ROOT")
    if not work or not float_root or not char_root:
        raise RuntimeError("Previous phases missing")
    old = bpy.data.collections.get("USTUDIO_CHARACTER_LIGHTING")
    if old:
        remove_collection(old.name)
    lights = new_collection("USTUDIO_CHARACTER_LIGHTING", work)
    target = empty("USTUDIO_LIGHTING_CHARACTER_TARGET", lights, float_root, (0, 0.16, 2.10))

    # Ratios preserve Drumboiii 1 / .314 / .121 / .157, adapted to this miniature.
    back = add_area("USTUDIO_LIGHTING_BACK_SHAPE", lights, float_root, (0, 0.95, 2.75), 150, 1.0, (0.92, 0.96, 1.0), target)
    glimmer_a = add_area("USTUDIO_LIGHTING_SIDE_GLIMMER_A", lights, float_root, (-1.2, -0.35, 2.35), 47, 0.65, (0.45, 1.0, 0.08), target)
    glimmer_b = add_area("USTUDIO_LIGHTING_SIDE_GLIMMER_B", lights, float_root, (1.15, -0.25, 2.28), 18, 0.55, (1.0, 0.07, 0.55), target)
    detail = add_area("USTUDIO_LIGHTING_DETAIL_RETURN", lights, float_root, (0.25, -0.85, 2.42), 24, 0.45, (0.72, 0.82, 1.0), target)
    sun_data = bpy.data.lights.new("USTUDIO_LIGHTING_SUN_REFLECTION_DATA", "SUN")
    sun_data.energy = 0.7
    sun_data.angle = math.radians(3.0)
    sun_data.color = (0.82, 0.9, 1.0)
    sun = bpy.data.objects.new("USTUDIO_LIGHTING_SUN_REFLECTION", sun_data)
    lights.objects.link(sun)
    sun.parent = float_root
    sun.rotation_euler = (math.radians(32), math.radians(-18), math.radians(-42))

    reveal = add_area("USTUDIO_PLAYHEAD_REVEAL_LIGHT", lights, float_root, (-2.2, 0.55, 2.65), 0, 0.42, (0.3, 1.0, 0.04), target)
    reveal["ustudio_source"] = "USTUDIO_PLAYHEAD_BACK position and audio glow"
    for frame, energy in [(1, 0), (9, 2), (45, 18), (57, 35), (75, 15), (105, 6), (203, 8), (239, 28), (251, 80), (258, 9), (299, 5), (348, 25), (386, 48), (396, 60), (406, 48)]:
        reveal.data.energy = energy
        reveal.data.keyframe_insert("energy", frame=frame)
    # The light follows the character in the chase/communion rather than becoming collision geometry.
    for frame, x in [(1, -2.2), (105, -1.6), (203, 0.0), (251, 0.95), (298, 1.55), (299, -0.5), (348, 0), (396, 0)]:
        key_location(reveal, frame, (x, 0.55, 2.65))
    for frame, z in [(299, 2.05), (348, 2.10), (396, 2.18), (406, 2.18)]:
        key_location(target, frame, (0, 0.16, z))

    # Keep the existing UI lights: they are story light, not redundant studio fill.
    for obj in scene.objects:
        if obj.type == "LIGHT" and obj.name.startswith("USTUDIO_") and obj.name not in lights.objects:
            obj["ustudio_preserved_reason"] = "canonical FL Studio screen/box lighting"

    # Character pearl becomes subtly emissive only during communion.
    mat = bpy.data.materials.get("M_USTUDIO_CHARACTER_PEARL")
    if mat and mat.node_tree:
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        emission = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        strength = bsdf.inputs.get("Emission Strength")
        if emission and strength:
            emission.default_value = (0.8, 0.95, 1.0, 1.0)
            for frame, value in [(1, 0.0), (298, 0.0), (299, 0.02), (348, 0.08), (386, 0.28), (396, 0.42), (406, 0.32)]:
                strength.default_value = value
                strength.keyframe_insert("default_value", frame=frame)

    # World remains dark and neutral; colored screens and glimmers do the design work.
    world = scene.world or bpy.data.worlds.new("USTUDIO_CHARACTER_WORLD")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    if background:
        background.inputs["Color"].default_value = (0.003, 0.005, 0.012, 1)
        background.inputs["Strength"].default_value = 0.22

    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.15

    # Try to mount the source audio in the working copy only.
    master = Path(bpy.path.abspath("//../../fl-studio-box-semantic-template/media/current/master.mp4")).resolve()
    try:
        editor = scene.sequence_editor_create()
        existing = [strip for strip in editor.sequences_all if strip.name == "USTUDIO_MASTER_AUDIO"]
        for strip in existing:
            if hasattr(editor, "sequences"):
                editor.sequences.remove(strip)
        strips = getattr(editor, "strips", None) or getattr(editor, "sequences", None)
        if strips and master.exists():
            strips.new_sound("USTUDIO_MASTER_AUDIO", str(master), channel=1, frame_start=1)
            scene["ustudio_audio_mounted"] = True
    except Exception as exc:
        scene["ustudio_audio_mounted"] = False
        scene["ustudio_audio_mount_error"] = str(exc)

    # Animate bridge edge pulse at impact and communion.
    for name in ("M_USTUDIO_INTERFACE_LIME", "M_USTUDIO_INTERFACE_MAGENTA"):
        edge_mat = bpy.data.materials.get(name)
        if not edge_mat or not edge_mat.node_tree:
            continue
        bsdf = edge_mat.node_tree.nodes.get("Principled BSDF")
        strength = bsdf.inputs.get("Emission Strength")
        if not strength:
            continue
        for frame, value in [(1, 2.5), (239, 3.5), (251, 10.0), (258, 2.8), (299, 3.0), (348, 6.0), (396, 12.0), (406, 8.0)]:
            strength.default_value = value
            strength.keyframe_insert("default_value", frame=frame)

    scene.frame_set(299)
    bpy.ops.wm.save_as_mainfile(filepath=str(EXPECTED_BLEND))


if PHASE == "clay":
    build_clay()
elif PHASE == "camera":
    build_cameras()
elif PHASE == "look":
    build_look()
else:
    raise RuntimeError(f"Unknown phase: {PHASE}")

print("USTUDIO_BUILD=" + json.dumps({"phase": PHASE, "blend": str(EXPECTED_BLEND), "saved": True}))
