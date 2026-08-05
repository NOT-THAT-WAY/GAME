"""Build the Codex Piano Roll slope-running benchmark in isolated phases."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


TRIAL = Path(__file__).resolve().parent
BLEND = (TRIAL / "scene" / "trial.blend").resolve()
PHASE = os.environ.get("USTUDIO_BUILD_PHASE", "clay")
WORK_NAME = "K3_PIANOROLL_SLOPE_RUN_CODEX_V001_WORK"
CAM_COLLECTION = "USTUDIO_SLOPE_CAMERAS"
LIGHT_COLLECTION = "USTUDIO_SLOPE_LIGHTING"

if Path(bpy.data.filepath).resolve() != BLEND:
    raise RuntimeError("Refusing to save outside the isolated trial blend")

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = 240
scene.render.fps = 30
scene.render.fps_base = 1.0


def remove_collection(name):
    collection = bpy.data.collections.get(name)
    if not collection:
        return
    for child in list(collection.children):
        remove_collection(child.name)
    for obj in list(collection.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(collection)


def collection(name, parent=None):
    result = bpy.data.collections.new(name)
    (parent or scene.collection).children.link(result)
    return result


def relink(obj, target):
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    target.objects.link(obj)
    return obj


def principled(name, color, roughness=0.55, metallic=0.0, emission=None, strength=0.0):
    old = bpy.data.materials.get(name)
    if old:
        bpy.data.materials.remove(old)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission:
        (bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")).default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = strength
    return mat


def empty(name, target, parent=None, location=(0, 0, 0), display="PLAIN_AXES"):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = display
    obj.empty_display_size = 0.025
    target.objects.link(obj)
    obj.parent = parent
    obj.location = location
    return obj


def sphere(name, target, parent, scale, material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10)
    obj = relink(bpy.context.object, target)
    obj.name = name
    obj.parent = parent
    obj.location = (0, 0, 0)
    obj.scale = scale
    obj.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return obj


def segment(name, target, start, end, radius, material):
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=radius, depth=1.0)
    obj = relink(bpy.context.object, target)
    obj.name = name
    obj.data.materials.append(material)
    obj.rotation_mode = "QUATERNION"
    return obj


def foot_mesh(name, target, joint, material, grip_material):
    bpy.ops.mesh.primitive_cube_add()
    foot = relink(bpy.context.object, target)
    foot.name = name
    foot.parent = joint
    foot.location = (0, 0, 0)
    foot.dimensions = (0.042, 0.065, 0.016)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    foot.data.materials.append(material)
    bevel = foot.modifiers.new(name + "_BEVEL", "BEVEL")
    bevel.width = 0.006
    bevel.segments = 3

    bpy.ops.mesh.primitive_cube_add()
    sole = relink(bpy.context.object, target)
    sole.name = name.replace("FOOT", "GRIP_SOLE")
    sole.parent = joint
    sole.location = (0, 0, -0.010)
    sole.dimensions = (0.044, 0.067, 0.004)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    sole.data.materials.append(grip_material)
    bevel = sole.modifiers.new(sole.name + "_BEVEL", "BEVEL")
    bevel.width = 0.003
    bevel.segments = 2
    return foot, sole


def all_fcurves(owner):
    animation = getattr(owner, "animation_data", None)
    action = animation.action if animation else None
    if not action:
        return []
    curves = list(getattr(action, "fcurves", []))
    if curves:
        return curves
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                curves.extend(bag.fcurves)
    return curves


def linearize(owner, constant_paths=()):
    for curve in all_fcurves(owner):
        for point in curve.keyframe_points:
            point.interpolation = "CONSTANT" if curve.data_path in constant_paths else "LINEAR"


def surface_basis():
    floor = bpy.data.objects.get("USTUDIO_PIANO_ROLL_FLOOR")
    root = bpy.data.objects.get("USTUDIO_BOX_FLOAT_ROOT")
    if not floor or not root:
        raise RuntimeError("Required USTUDIO floor/root missing")
    matrix = root.matrix_world.inverted_safe() @ floor.matrix_world
    vertices = [matrix @ vertex.co for vertex in floor.data.vertices]
    if len(vertices) < 4:
        raise RuntimeError("Piano Roll floor needs at least four vertices")
    cross = (vertices[1] - vertices[0]).normalized()
    if cross.x < 0:
        cross.negate()
    uphill_raw = ((vertices[2] + vertices[3]) * 0.5) - ((vertices[0] + vertices[1]) * 0.5)
    uphill = uphill_raw.normalized()
    if uphill.y < 0:
        uphill.negate()
    normal = cross.cross(uphill).normalized()
    if normal.z < 0:
        normal.negate()
    low_center = (vertices[0] + vertices[1]) * 0.5
    high_center = (vertices[2] + vertices[3]) * 0.5
    slope = math.degrees(math.acos(max(-1.0, min(1.0, normal.dot(Vector((0, 0, 1)))))))
    return floor, root, vertices, low_center, high_center, cross, uphill, normal, slope


def basis_rotation(cross, uphill, normal):
    return Matrix((cross, uphill, normal)).transposed().to_euler()


def point_on_run(low_center, uphill, distance, cross, x=0.0):
    return low_center + uphill * distance + cross * x


def root_distance(frame, start, end):
    if frame <= 16:
        return start
    if frame <= 33:
        return start + 0.01 * (frame - 16) / 17
    if frame <= 49:
        return start + 0.02 * (frame - 33) / 16
    if frame <= 209:
        u = (frame - 49) / 160
        # Smooth acceleration/deceleration while keeping monotonic travel.
        eased = u * u * (3.0 - 2.0 * u)
        return start + (end - start) * eased
    return end


def contact_distance(frame, start, end):
    return root_distance(frame, start, end) + 0.025


def foot_state(frame, side, start, end):
    first = 49 if side == "L" else 41
    events = list(range(first, 210, 16))
    # The left foot begins exactly at its first scheduled contact; this avoids
    # a one-frame planted-foot teleport when the run starts.
    initial = start + (0.045 if side == "L" else -0.045)
    if frame < first:
        return initial, True, 0.0
    previous = max(value for value in events if value <= frame)
    old = contact_distance(previous, start, end) if previous >= 49 else initial
    opposite = previous + 8
    next_contact = previous + 16
    if frame <= opposite or next_contact > 209:
        return old, True, 0.0
    target = contact_distance(next_contact, start, end)
    u = min(1.0, max(0.0, (frame - opposite) / 8.0))
    smooth = u * u * (3.0 - 2.0 * u)
    clearance = math.sin(math.pi * u) * 0.032
    return old * (1.0 - smooth) + target * smooth, False, clearance


def runner_pose(frame, low_center, cross, uphill, normal, start, end):
    distance = root_distance(frame, start, end)
    surface = point_on_run(low_center, uphill, distance, cross)
    if frame <= 16:
        lean = 8.0
    elif frame <= 33:
        lean = 8.0 + 14.0 * (frame - 16) / 17
    elif frame <= 209:
        lean = 19.0 + 2.5 * math.sin((frame - 49) * math.tau / 16.0)
    elif frame <= 224:
        lean = 19.0 - 11.0 * (frame - 209) / 15
    else:
        lean = 8.0
    lean_radians = math.radians(lean)
    torso_direction = Vector((0.0, math.sin(lean_radians), math.cos(lean_radians))).normalized()
    pelvis = surface + normal * 0.148
    chest = pelvis + torso_direction * 0.105
    neck = chest + torso_direction * 0.045
    head = neck + torso_direction * 0.035
    pose = {"PELVIS": pelvis, "CHEST": chest, "NECK": neck, "HEAD": head}
    pose["SHOULDER_L"] = chest - cross * 0.052 + torso_direction * 0.018
    pose["SHOULDER_R"] = chest + cross * 0.052 + torso_direction * 0.018
    pose["HIP_L"] = pelvis - cross * 0.030
    pose["HIP_R"] = pelvis + cross * 0.030

    planted = {}
    clearance = {}
    for side, sign in (("L", -1.0), ("R", 1.0)):
        foot_distance, is_planted, lift = foot_state(frame, side, start, end)
        foot_surface = point_on_run(low_center, uphill, foot_distance, cross, sign * 0.034)
        foot = foot_surface + normal * (0.012 + lift)
        hip = pose[f"HIP_{side}"]
        knee = (hip + foot) * 0.5 + uphill * 0.032 + normal * 0.026
        pose[f"KNEE_{side}"] = knee
        pose[f"FOOT_{side}"] = foot
        planted[side] = is_planted
        clearance[side] = lift

    # Arms oppose the legs; active uphill swing without hyperextension.
    phase = math.sin((frame - 49) * math.tau / 16.0) if 49 <= frame <= 209 else 0.0
    for side, sign in (("L", -1.0), ("R", 1.0)):
        swing = (-phase if side == "L" else phase) * 0.042
        shoulder = pose[f"SHOULDER_{side}"]
        hand = shoulder - Vector((0, 0, 1)) * 0.105 + Vector((0, swing, 0))
        elbow = (shoulder + hand) * 0.5 + cross * sign * 0.012 + Vector((0, -swing * 0.18, 0.008))
        pose[f"ELBOW_{side}"] = elbow
        pose[f"HAND_{side}"] = hand
    return pose, planted, clearance, lean, distance


def build_clay():
    remove_collection(WORK_NAME)
    work = collection(WORK_NAME)
    work["ustudio_trial"] = "k3-pianoroll-slope-run-codex-v001"
    floor, float_root, vertices, low, high, cross, uphill, normal, slope = surface_basis()
    usable = (high - low).length
    start = 0.22
    end = usable - 0.25
    if end <= start:
        raise RuntimeError("Insufficient Piano Roll run length")

    analysis = {
        "schema_version": 1,
        "surface": floor.name,
        "reference": float_root.name,
        "vertices_local": [[round(float(v), 6) for v in vertex] for vertex in vertices],
        "surface_normal": [round(float(v), 8) for v in normal],
        "uphill_tangent": [round(float(v), 8) for v in uphill],
        "cross_slope_tangent": [round(float(v), 8) for v in cross],
        "world_gravity": [0.0, 0.0, -9.81],
        "slope_degrees": round(slope, 6),
        "usable_length_m": round(usable, 6),
        "run_start_m": start,
        "run_end_m": round(end, 6),
        "static_friction_min": round(math.tan(math.radians(slope)), 6),
        "authored_grip_coefficient": 1.25,
    }
    (TRIAL / "diagnostics" / "surface-analysis.json").write_text(json.dumps(analysis, indent=2) + "\n", encoding="utf-8")

    body_mat = principled("M_USTUDIO_SLOPE_PEARL", (0.48, 0.52, 0.58), 0.58)
    foot_mat = principled("M_USTUDIO_SLOPE_SHOE", (0.07, 0.09, 0.11), 0.72)
    grip_l = principled("M_USTUDIO_GRIP_L", (0.10, 0.42, 0.015), 0.42, emission=(0.28, 1.0, 0.03), strength=0.2)
    grip_r = principled("M_USTUDIO_GRIP_R", (0.10, 0.42, 0.015), 0.42, emission=(0.28, 1.0, 0.03), strength=0.2)

    rig = empty("USTUDIO_SLOPE_RUN_RIG", work, float_root, display="CIRCLE")
    rig["ustudio_grip_surface"] = "rubber-lime dynamic grip"
    rig["ustudio_grip_coefficient"] = 1.25
    rig["ustudio_surface_angle_deg"] = slope
    joint_names = [
        "PELVIS", "CHEST", "NECK", "HEAD",
        "SHOULDER_L", "ELBOW_L", "HAND_L", "SHOULDER_R", "ELBOW_R", "HAND_R",
        "HIP_L", "KNEE_L", "FOOT_L", "HIP_R", "KNEE_R", "FOOT_R",
    ]
    joints = {name: empty("USTUDIO_SLOPE_JOINT_" + name, work, rig) for name in joint_names}

    sphere("USTUDIO_SLOPE_CHAR_PELVIS", work, joints["PELVIS"], (0.045, 0.034, 0.038), body_mat)
    sphere("USTUDIO_SLOPE_CHAR_CHEST", work, joints["CHEST"], (0.052, 0.037, 0.052), body_mat)
    sphere("USTUDIO_SLOPE_CHAR_HEAD", work, joints["HEAD"], (0.039, 0.038, 0.044), body_mat)
    for name in ["SHOULDER_L", "ELBOW_L", "HAND_L", "SHOULDER_R", "ELBOW_R", "HAND_R", "HIP_L", "KNEE_L", "HIP_R", "KNEE_R"]:
        radius = 0.014 if "HAND" in name else 0.016
        sphere("USTUDIO_SLOPE_CHAR_" + name, work, joints[name], (radius, radius, radius), body_mat)

    segment_specs = [
        ("TORSO", "PELVIS", "CHEST", 0.035),
        ("NECK", "CHEST", "HEAD", 0.021),
        ("UPPER_ARM_L", "SHOULDER_L", "ELBOW_L", 0.014),
        ("FOREARM_L", "ELBOW_L", "HAND_L", 0.012),
        ("UPPER_ARM_R", "SHOULDER_R", "ELBOW_R", 0.014),
        ("FOREARM_R", "ELBOW_R", "HAND_R", 0.012),
        ("THIGH_L", "HIP_L", "KNEE_L", 0.018),
        ("SHIN_L", "KNEE_L", "FOOT_L", 0.015),
        ("THIGH_R", "HIP_R", "KNEE_R", 0.018),
        ("SHIN_R", "KNEE_R", "FOOT_R", 0.015),
    ]
    segments = {
        name: segment("USTUDIO_SLOPE_CHAR_" + name, work, joints[start_joint], joints[end_joint], radius, body_mat)
        for name, start_joint, end_joint, radius in segment_specs
    }
    foot_mesh("USTUDIO_SLOPE_CHAR_FOOT_L", work, joints["FOOT_L"], foot_mat, grip_l)
    foot_mesh("USTUDIO_SLOPE_CHAR_FOOT_R", work, joints["FOOT_R"], foot_mat, grip_r)

    rotation = basis_rotation(cross, uphill, normal)
    for side in ("L", "R"):
        joints[f"FOOT_{side}"].rotation_euler = rotation
        joints[f"FOOT_{side}"].keyframe_insert("rotation_euler", frame=1)
        joints[f"FOOT_{side}"]["ustudio_planted"] = True

    for frame in range(1, 241):
        pose, planted, clearance, lean, distance = runner_pose(frame, low, cross, uphill, normal, start, end)
        for name, position in pose.items():
            joints[name].location = position
            joints[name].keyframe_insert("location", frame=frame)
        for name, start_joint, end_joint, _ in segment_specs:
            link = segments[name]
            delta = pose[end_joint] - pose[start_joint]
            link.location = (pose[start_joint] + pose[end_joint]) * 0.5
            link.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(delta.normalized())
            link.scale = (1.0, 1.0, delta.length)
            link.keyframe_insert("location", frame=frame)
            link.keyframe_insert("rotation_quaternion", frame=frame)
            link.keyframe_insert("scale", frame=frame)
        for side in ("L", "R"):
            foot = joints[f"FOOT_{side}"]
            foot["ustudio_planted"] = int(planted[side])
            foot["ustudio_swing_clearance_m"] = float(clearance[side])
            foot.keyframe_insert('["ustudio_planted"]', frame=frame)
            foot.keyframe_insert('["ustudio_swing_clearance_m"]', frame=frame)
        rig["ustudio_torso_lean_world_deg"] = float(lean)
        rig["ustudio_root_surface_distance_m"] = float(distance)
        rig.keyframe_insert('["ustudio_torso_lean_world_deg"]', frame=frame)
        rig.keyframe_insert('["ustudio_root_surface_distance_m"]', frame=frame)

        for mat, side in ((grip_l, "L"), (grip_r, "R")):
            strength = mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
            strength.default_value = 3.8 if planted[side] else 0.12
            strength.keyframe_insert("default_value", frame=frame)

    for obj in list(joints.values()) + list(segments.values()) + [rig]:
        linearize(obj, ('["ustudio_planted"]',))
    for mat in (grip_l, grip_r):
        linearize(mat.node_tree)

    for marker in list(scene.timeline_markers):
        if marker.name.startswith("USTUDIO_SLOPE_"):
            scene.timeline_markers.remove(marker)
    for frame in [1, 17, 33, 49, 57, 81, 106, 130, 154, 178, 192, 203, 224, 240]:
        scene.timeline_markers.new(f"USTUDIO_SLOPE_GATE_{frame:04d}", frame=frame)

    scene["ustudio_slope_basis"] = json.dumps(analysis)
    scene["ustudio_participant"] = "codex"
    scene.frame_set(49)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))


def camera_obj(name, target, parent, lens=58, fstop=4.0):
    data = bpy.data.cameras.new(name + "_DATA")
    data.lens = lens
    data.clip_start = 0.008
    data.clip_end = 100.0
    data.dof.use_dof = True
    data.dof.aperture_fstop = fstop
    obj = bpy.data.objects.new(name, data)
    target.objects.link(obj)
    obj.parent = parent
    return obj


def track(obj, target):
    constraint = obj.constraints.new("TRACK_TO")
    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"


def build_camera():
    work = bpy.data.collections.get(WORK_NAME)
    rig = bpy.data.objects.get("USTUDIO_SLOPE_RUN_RIG")
    pelvis = bpy.data.objects.get("USTUDIO_SLOPE_JOINT_PELVIS")
    chest = bpy.data.objects.get("USTUDIO_SLOPE_JOINT_CHEST")
    float_root = bpy.data.objects.get("USTUDIO_BOX_FLOAT_ROOT")
    if not all((work, rig, pelvis, chest, float_root)):
        raise RuntimeError("Clay phase missing")
    remove_collection(CAM_COLLECTION)
    cams = collection(CAM_COLLECTION, work)
    floor, _, vertices, low, high, cross, uphill, normal, slope = surface_basis()
    start, end = 0.22, (high - low).length - 0.25

    target = empty("USTUDIO_SLOPE_CAM_TARGET", cams, float_root)
    focus = empty("USTUDIO_SLOPE_CAM_FOCUS", cams, float_root)
    main = camera_obj("USTUDIO_SLOPE_CAM_MAIN", cams, float_root, 58, 4.0)
    main.data.dof.focus_object = focus
    track(main, target)

    distances = []
    for frame in range(1, 241):
        pose, _, _, _, _ = runner_pose(frame, low, cross, uphill, normal, start, end)
        delayed_frame = max(1, frame - 2) if 49 <= frame <= 209 else frame
        delayed_pose, _, _, _, _ = runner_pose(delayed_frame, low, cross, uphill, normal, start, end)
        attention = delayed_pose["CHEST"] + Vector((0, 0, 0.012))
        current_focus = pose["CHEST"]
        # A lateral, world-stable profile keeps the true incline readable and
        # remains inside the box for the complete ascent.
        offset = cross * 1.25 + uphill * 0.25 + normal * 0.12
        if 17 <= frame <= 33:
            offset -= uphill * (0.008 * (frame - 17) / 16)
        elif 33 < frame < 49:
            offset -= uphill * (0.008 * (49 - frame) / 16)
        if 209 <= frame <= 224:
            offset += uphill * (0.008 * (frame - 209) / 15)
        elif frame > 224:
            offset += uphill * 0.008
        camera_position = current_focus + offset
        main.location = camera_position
        target.location = attention
        focus.location = current_focus
        main.keyframe_insert("location", frame=frame)
        target.keyframe_insert("location", frame=frame)
        focus.keyframe_insert("location", frame=frame)
        distances.append((camera_position - current_focus).length)
        main.data.lens = 54.0 if frame <= 33 else 58.0 if frame <= 209 else 60.0
        main.data.keyframe_insert("lens", frame=frame)
    for owner in (main, target, focus, main.data):
        linearize(owner)
    main["ustudio_distance_min_m"] = min(distances)
    main["ustudio_distance_max_m"] = max(distances)
    main["ustudio_horizon_rule"] = "world-stable up; no slope roll"

    # Diagnostic cameras are never active in the final edit.
    profile_target = empty("USTUDIO_SLOPE_DIAG_PROFILE_TARGET", cams, float_root, (0, 0.35, 1.85))
    profile = camera_obj("USTUDIO_SLOPE_CAM_DIAG_PROFILE", cams, float_root, 62, 4.5)
    profile.location = (2.6, 0.35, 1.85)
    track(profile, profile_target)
    top_target = empty("USTUDIO_SLOPE_DIAG_TOP_TARGET", cams, float_root, (0, 0.35, 1.85))
    top = camera_obj("USTUDIO_SLOPE_CAM_DIAG_TOP", cams, float_root, 45, 5.6)
    top.location = (0.25, -0.2, 5.0)
    track(top, top_target)
    normal_target = empty("USTUDIO_SLOPE_DIAG_NORMAL_TARGET", cams, float_root, (0, 0.35, 1.85))
    normal_cam = camera_obj("USTUDIO_SLOPE_CAM_DIAG_NORMAL", cams, float_root, 70, 5.6)
    normal_cam.location = normal_target.location + normal * 2.4
    track(normal_cam, normal_target)

    scene.camera = main
    manifest = {
        "schema_version": 1,
        "camera": main.name,
        "camera_names": [main.name, profile.name, top.name, normal_cam.name],
        "lens_range_mm": [54, 60],
        "target": target.name,
        "focus": focus.name,
        "move": "K1 pose, K2 opposite anticipation, K3 uphill track, K4 recovery",
        "distance_range_m": [round(min(distances), 6), round(max(distances), 6)],
        "saved": True,
    }
    (TRIAL / "shot-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    scene.frame_set(49)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))


def area(name, target_collection, parent, location, energy, size, color, target):
    data = bpy.data.lights.new(name + "_DATA", "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    target_collection.objects.link(obj)
    obj.parent = parent
    obj.location = location
    track(obj, target)
    return obj


def build_look():
    work = bpy.data.collections.get(WORK_NAME)
    float_root = bpy.data.objects.get("USTUDIO_BOX_FLOAT_ROOT")
    if not work or not float_root:
        raise RuntimeError("Previous phases missing")
    remove_collection(LIGHT_COLLECTION)
    lights = collection(LIGHT_COLLECTION, work)
    target = empty("USTUDIO_LIGHTING_TARGET", lights, float_root, (0, 0.38, 2.0))

    sun_data = bpy.data.lights.new("USTUDIO_LIGHTING_SUN_REFLECTION_DATA", "SUN")
    sun_data.energy = 0.55
    sun_data.angle = math.radians(3.5)
    sun_data.color = (0.82, 0.9, 1.0)
    sun = bpy.data.objects.new("USTUDIO_LIGHTING_SUN_REFLECTION", sun_data)
    lights.objects.link(sun)
    sun.parent = float_root
    sun.rotation_euler = (math.radians(36), math.radians(-16), math.radians(-38))
    area("USTUDIO_LIGHTING_BACK_SHAPE", lights, float_root, (-0.8, 1.0, 3.15), 125, 0.9, (0.92, 0.96, 1.0), target)
    area("USTUDIO_LIGHTING_SIDE_GLIMMER_A", lights, float_root, (1.2, -0.15, 2.25), 39, 0.55, (0.38, 1.0, 0.05), target)
    area("USTUDIO_LIGHTING_SIDE_GLIMMER_B", lights, float_root, (-1.1, 0.15, 2.35), 15, 0.5, (1.0, 0.06, 0.5), target)
    area("USTUDIO_LIGHTING_DETAIL_RETURN", lights, float_root, (0.6, -0.7, 2.55), 20, 0.45, (0.7, 0.82, 1.0), target)

    world = scene.world or bpy.data.worlds.new("USTUDIO_SLOPE_WORLD")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    if background:
        background.inputs["Color"].default_value = (0.004, 0.006, 0.012, 1)
        background.inputs["Strength"].default_value = 0.22
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.0
    scene.frame_set(106)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))


if PHASE == "clay":
    build_clay()
elif PHASE == "camera":
    build_camera()
elif PHASE == "look":
    build_look()
else:
    raise RuntimeError("Unknown phase: " + PHASE)

print("USTUDIO_SLOPE_BUILD=" + json.dumps({"phase": PHASE, "blend": str(BLEND), "saved": True}))
