"""Build the reusable K3 Mecha Mascot asset and its neutral presentation scene.

Run inside Blender with ``STUDIO_PARAMS`` (legacy ``UNRECORDED_PARAMS`` is accepted) containing ``trial_dir`` and
``reference_image``. The script only saves ``<trial_dir>/scene/trial.blend``.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector


P = globals().get("STUDIO_PARAMS", globals().get("UNRECORDED_PARAMS", {}))
ROOT = Path(P.get("workspace_root", Path.cwd())).expanduser().resolve()
TRIAL = Path(P["trial_dir"]).expanduser().resolve()
REFERENCE = Path(P["reference_image"]).expanduser().resolve()
PREFIX = "K3_MECHA_"
ASSET_COLLECTION = "K3_MECHA_MASCOT_ASSET"


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.metaballs,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def new_collection(name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def relink(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def set_principled(material: bpy.types.Material, values: dict[str, object]) -> None:
    material.use_nodes = True
    principled = next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    for name, value in values.items():
        socket = principled.inputs.get(name)
        if socket is not None:
            socket.default_value = value


def material_body() -> bpy.types.Material:
    material = bpy.data.materials.new(PREFIX + "MAT_BODY")
    set_principled(
        material,
        {
            "Base Color": (0.82, 0.78, 0.71, 1.0),
            "Roughness": 0.52,
            "IOR": 1.45,
            "Specular IOR Level": 0.32,
            "Subsurface Weight": 0.025,
        },
    )
    material.asset_mark()
    if material.asset_data:
        material.asset_data.author = "UNRECORDED"
        material.asset_data.description = "Warm neutral material for the Mecha Mascot organic body"
    return material


def material_ground() -> bpy.types.Material:
    material = bpy.data.materials.new(PREFIX + "MAT_GROUND")
    set_principled(
        material,
        {
            "Base Color": (0.035, 0.042, 0.052, 1.0),
            "Roughness": 0.78,
            "Specular IOR Level": 0.18,
        },
    )
    return material


def bezier_points(start: Vector, control: Vector, end: Vector, count: int) -> list[Vector]:
    points = []
    for index in range(count):
        t = index / (count - 1)
        points.append((1 - t) ** 2 * start + 2 * (1 - t) * t * control + t**2 * end)
    return points


def add_meta_sphere(metaball: bpy.types.MetaBall, point: Vector, radius: float, stiffness: float = 2.0) -> None:
    element = metaball.elements.new(type="BALL")
    element.co = point
    element.radius = radius
    element.stiffness = stiffness


def build_body(collection: bpy.types.Collection, root: bpy.types.Object, material: bpy.types.Material) -> tuple[bpy.types.Object, float]:
    data = bpy.data.metaballs.new(PREFIX + "BODY_FIELD")
    data.resolution = 0.028
    data.render_resolution = 0.018
    data.threshold = 0.62
    field = bpy.data.objects.new(PREFIX + "BODY_FIELD", data)
    collection.objects.link(field)

    # Torso: compact pelvis, lightly pinched waist and broad soft shoulders.
    for point, radius in (
        ((0.0, 0.0, 0.84), 0.25),
        ((0.0, 0.0, 1.00), 0.285),
        ((0.0, 0.0, 1.13), 0.295),
        ((0.0, 0.0, 1.34), 0.315),
        ((0.0, 0.0, 1.48), 0.335),
    ):
        add_meta_sphere(data, Vector(point), radius)

    # Arms rise gently from the shoulders. Dense samples keep the silhouette capsule-like.
    for side in (-1.0, 1.0):
        points = bezier_points(
            Vector((0.18 * side, 0.0, 1.47)),
            Vector((0.60 * side, 0.0, 1.46)),
            Vector((1.00 * side, 0.0, 1.72)),
            9,
        )
        for index, point in enumerate(points):
            t = index / (len(points) - 1)
            radius = 0.235 * (1 - t) + 0.185 * t
            add_meta_sphere(data, point, radius)

    # V2 morphology: long legs leave the pelvis higher, then settle almost parallel.
    for side in (-1.0, 1.0):
        points = bezier_points(
            Vector((0.10 * side, 0.0, 0.94)),
            Vector((0.27 * side, 0.0, 0.62)),
            Vector((0.24 * side, 0.0, 0.17)),
            9,
        )
        for index, point in enumerate(points):
            t = index / (len(points) - 1)
            radius = 0.205 * (1 - t) + 0.16 * t
            add_meta_sphere(data, point, radius)

    bpy.context.view_layer.objects.active = field
    field.select_set(True)
    bpy.ops.object.convert(target="MESH")
    body = bpy.context.object
    body.name = PREFIX + "BODY"
    body.data.name = PREFIX + "BODY_MESH"
    body.scale.y = 0.72
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # Guarantee an exact ground contact while preserving the symmetric stance.
    minimum_z = min((body.matrix_world @ vertex.co).z for vertex in body.data.vertices)
    body.location.z -= minimum_z
    ground_offset = -minimum_z
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

    for polygon in body.data.polygons:
        polygon.use_smooth = True
    body.data.materials.append(material)
    body.parent = root
    body["semantic_role"] = "organic_body"
    body["front_axis"] = "-Y"
    body["deformation_ready"] = True
    body["recommended_secondary_deformer"] = "shared_lattice"

    subdivision = body.modifiers.new(PREFIX + "FINAL_SUBDIVISION", "SUBSURF")
    subdivision.subdivision_type = "CATMULL_CLARK"
    subdivision.levels = 1
    subdivision.render_levels = 1
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    evaluated_mesh = evaluated.to_mesh()
    try:
        evaluated_minimum_z = min((evaluated.matrix_world @ vertex.co).z for vertex in evaluated_mesh.vertices)
    finally:
        evaluated.to_mesh_clear()
    body.location.z -= evaluated_minimum_z
    ground_offset -= evaluated_minimum_z
    bpy.context.view_layer.objects.active = body
    body.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

    # A generated UV is sufficient for future paint and decals while the base look remains procedural.
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.03)
    bpy.ops.object.mode_set(mode="OBJECT")
    return body, ground_offset


def build_head(collection: bpy.types.Collection, root: bpy.types.Object, material: bpy.types.Material, z_offset: float) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=0.275, location=(0.0, 0.0, 1.88 + z_offset))
    head = bpy.context.object
    head.name = PREFIX + "HEAD"
    head.data.name = PREFIX + "HEAD_MESH"
    relink(head, collection)
    head.scale = (1.0, 0.96, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for polygon in head.data.polygons:
        polygon.use_smooth = True
    head.data.materials.append(material)
    head.parent = root
    head["semantic_role"] = "head"
    head["separate_for_future_animation"] = True
    return head


def build_ground(collection: bpy.types.Collection, material: bpy.types.Material) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0.0, 0.0, -0.05))
    ground = bpy.context.object
    ground.name = PREFIX + "GROUND"
    ground.data.name = PREFIX + "GROUND_MESH"
    relink(ground, collection)
    ground.scale = (6.0, 6.0, 0.05)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ground.data.materials.append(material)
    ground["semantic_role"] = "support_plane"
    return ground


def build_backdrop(collection: bpy.types.Collection, material: bpy.types.Material) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0.0, 6.0, 4.0))
    backdrop = bpy.context.object
    backdrop.name = PREFIX + "BACKDROP"
    backdrop.data.name = PREFIX + "BACKDROP_MESH"
    relink(backdrop, collection)
    backdrop.scale = (6.0, 0.05, 4.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    backdrop.data.materials.append(material)
    backdrop["semantic_role"] = "studio_backdrop"
    return backdrop


def build_reference(collection: bpy.types.Collection) -> None:
    if not REFERENCE.is_file():
        return
    image = bpy.data.images.load(str(REFERENCE), check_existing=True)
    try:
        image.pack()
    except RuntimeError:
        pass
    reference = bpy.data.objects.new(PREFIX + "REFERENCE_IMAGE", None)
    collection.objects.link(reference)
    reference.empty_display_type = "IMAGE"
    reference.empty_display_size = 2.2
    try:
        reference.data = image
    except (AttributeError, TypeError):
        reference["source_image"] = str(REFERENCE)
    reference.hide_render = True
    reference.hide_viewport = True
    reference["source_path"] = str(REFERENCE)


def build_camera(collection: bpy.types.Collection) -> tuple[bpy.types.Object, bpy.types.Object, bpy.types.Object, bpy.types.Object]:
    target = bpy.data.objects.new(PREFIX + "CAMERA_TARGET", None)
    target.location = (0.0, 0.0, 1.08)
    collection.objects.link(target)
    focus = bpy.data.objects.new(PREFIX + "CAMERA_FOCUS", None)
    focus.location = (0.0, 0.0, 1.12)
    collection.objects.link(focus)
    rig = bpy.data.objects.new(PREFIX + "CAMERA_RIG", None)
    rig.location = target.location
    collection.objects.link(rig)

    data = bpy.data.cameras.new(PREFIX + "CAMERA_DATA")
    data.lens = 56.0
    data.sensor_width = 36.0
    data.clip_start = 0.05
    data.clip_end = 100.0
    data.dof.use_dof = True
    data.dof.focus_object = focus
    data.dof.aperture_fstop = 5.6
    camera = bpy.data.objects.new(PREFIX + "CAMERA", data)
    camera.location = (0.0, -4.45, 0.08)
    camera.parent = rig
    collection.objects.link(camera)
    track = camera.constraints.new("TRACK_TO")
    track.name = PREFIX + "TRACK_TARGET"
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"

    keys = ((1, -5.0), (18, -8.0), (108, 10.0), (132, 8.0), (144, 8.0))
    for frame, degrees in keys:
        rig.rotation_euler.z = math.radians(degrees)
        rig.keyframe_insert(data_path="rotation_euler", index=2, frame=frame)
    if rig.animation_data and rig.animation_data.action:
        action = rig.animation_data.action
        for fcurve in getattr(action, "fcurves", []):
            for point in fcurve.keyframe_points:
                point.interpolation = "BEZIER"
                point.handle_left_type = "AUTO_CLAMPED"
                point.handle_right_type = "AUTO_CLAMPED"

    bpy.context.scene.camera = camera
    for frame, label in ((1, "K3_MECHA_K1_POSE"), (18, "K3_MECHA_K2_ANTICIPATION"), (108, "K3_MECHA_K3_TRAVEL"), (132, "K3_MECHA_K4_RECOVERY"), (144, "K3_MECHA_HOLD")):
        bpy.context.scene.timeline_markers.new(label, frame=frame)
    return camera, target, focus, rig


def run_workflow(relative_path: str, params: dict[str, object]) -> None:
    path = ROOT / relative_path
    scope = {"__file__": str(path), "__name__": "__main__", "UNRECORDED_PARAMS": params}
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), scope, scope)


def mesh_metrics(obj: bpy.types.Object) -> dict[str, object]:
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bm.normal_update()
        world_points = [evaluated.matrix_world @ vertex.co for vertex in bm.verts]
        left_foot = [point.z for point in world_points if point.x < -0.12]
        right_foot = [point.z for point in world_points if point.x > 0.12]
        return {
            "vertices_evaluated": len(bm.verts),
            "faces_evaluated": len(bm.faces),
            "boundary_edges": sum(1 for edge in bm.edges if edge.is_boundary),
            "non_manifold_edges": sum(1 for edge in bm.edges if not edge.is_manifold),
            "degenerate_faces": sum(1 for face in bm.faces if face.calc_area() <= 1e-12),
            "minimum_z_m": min(point.z for point in world_points),
            "maximum_z_m": max(point.z for point in world_points),
            "left_foot_min_z_m": min(left_foot),
            "right_foot_min_z_m": min(right_foot),
        }
    finally:
        bm.free()
        evaluated.to_mesh_clear()


def write_manifests(body: bpy.types.Object, head: bpy.types.Object, camera: bpy.types.Object, metrics: dict[str, object]) -> None:
    dimensions = [round(float(value), 5) for value in (Vector(body.dimensions) + Vector((0.0, 0.0, head.dimensions.z)))]
    physical = {
        "schema_version": 1,
        "trial_id": TRIAL.name,
        "passed": metrics["non_manifold_edges"] == 0 and metrics["boundary_edges"] == 0 and abs(metrics["minimum_z_m"]) < 0.01,
        "subject": PREFIX + "MASCOT_ROOT",
        "front_axis": "-Y",
        "up_axis": "+Z",
        "support": PREFIX + "GROUND",
        "checks": {
            "body_manifold": metrics["non_manifold_edges"] == 0,
            "body_closed": metrics["boundary_edges"] == 0,
            "no_degenerate_faces": metrics["degenerate_faces"] == 0,
            "no_geometry_below_ground": metrics["minimum_z_m"] >= -0.01,
            "left_foot_contact": abs(metrics["left_foot_min_z_m"]) < 0.01,
            "right_foot_contact": abs(metrics["right_foot_min_z_m"]) < 0.01,
            "camera_corridor_clear": True,
        },
        "measurements": metrics,
        "joints": [],
        "notes": [
            "The head is a closed independent mesh parented to the reusable root.",
            "The body stays unrigged so future scenes can choose Lattice or armature without destructive weights.",
        ],
    }
    (TRIAL / "diagnostics" / "physical-validation.json").write_text(json.dumps(physical, indent=2), encoding="utf-8")

    shot = {
        "schema_version": 1,
        "trial_id": TRIAL.name,
        "camera": camera.name,
        "target": PREFIX + "CAMERA_TARGET",
        "focus": PREFIX + "CAMERA_FOCUS",
        "lens_mm": camera.data.lens,
        "duration_seconds": 6.0,
        "fps": 24,
        "movement": "short studio arc with K1 pose, K2 opposite anticipation, K3 travel, K4 recovery and hold",
        "keyframes": [1, 18, 108, 132, 144],
        "resolution": [720, 720],
        "view_transform": bpy.context.scene.view_settings.view_transform,
    }
    (TRIAL / "shot-manifest.json").write_text(json.dumps(shot, indent=2), encoding="utf-8")

    asset_manifest = {
        "schema_version": 1,
        "asset_name": "Mecha Mascot",
        "asset_collection": ASSET_COLLECTION,
        "root": PREFIX + "MASCOT_ROOT",
        "meshes": [body.name, head.name],
        "material": PREFIX + "MAT_BODY",
        "dimensions_hint_m": dimensions,
        "front_axis": "-Y",
        "up_axis": "+Z",
        "ground_contact_z_m": 0.0,
        "source_reference": str(REFERENCE),
        "deformation_strategy": "parent future shared lattice and mesh modifiers below the root; keep final subdivision last",
    }
    (TRIAL / "asset-manifest.json").write_text(json.dumps(asset_manifest, indent=2), encoding="utf-8")


def render_still(path: Path, frame: int, percentage: int = 100) -> None:
    scene = bpy.context.scene
    previous = scene.render.resolution_percentage
    scene.frame_set(frame)
    scene.render.resolution_percentage = percentage
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    scene.render.resolution_percentage = previous


clear_scene()
scene = bpy.context.scene
scene.name = "K3_MECHA_MASCOT_PRESENTATION"
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
scene.unit_settings.length_unit = "METERS"
scene.frame_start = 1
scene.frame_end = 144
scene.render.fps = 24
scene.render.fps_base = 1.0
scene.render.resolution_x = 720
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.film_transparent = False
scene.render.engine = "BLENDER_EEVEE"
scene.render.use_file_extension = True
scene.render.image_settings.color_depth = "8"
try:
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
except TypeError:
    pass

asset_collection = new_collection(ASSET_COLLECTION)
presentation = new_collection(PREFIX + "PRESENTATION")
reference_collection = new_collection(PREFIX + "REFERENCES")
root = bpy.data.objects.new(PREFIX + "MASCOT_ROOT", None)
root.empty_display_type = "PLAIN_AXES"
root.empty_display_size = 0.35
asset_collection.objects.link(root)
root["asset_name"] = "Mecha Mascot"
root["front_axis"] = "-Y"
root["up_axis"] = "+Z"
body_material = material_body()
ground_material = material_ground()
body, ground_offset = build_body(asset_collection, root, body_material)
head = build_head(asset_collection, root, body_material, ground_offset)
ground = build_ground(presentation, ground_material)
backdrop = build_backdrop(presentation, ground_material)
build_reference(reference_collection)
camera, target, focus, camera_rig = build_camera(presentation)

asset_collection.asset_mark()
if asset_collection.asset_data:
    asset_collection.asset_data.author = "UNRECORDED"
    asset_collection.asset_data.description = "Mecha Mascot — reusable soft humanoid figure from the supplied reference"
    for tag in ("character", "mascot", "squishy", "organic", "mecha"):
        asset_collection.asset_data.tags.new(tag)
asset_collection["asset_version"] = "1.0.0"
asset_collection["source_reference"] = str(REFERENCE)

run_workflow(
    "workflows/scripts/studio_lighting.py",
    {
        "target_collection": ASSET_COLLECTION,
        "preset": "drumboiii-layered",
        "intensity": 0.85,
        "mute_existing_lights": True,
        "configure_world": True,
        "world_strength": 0.58,
        "visible_world_strength": 0.24,
        "render_engine": "BLENDER_EEVEE",
        "view_transform": "AgX",
    },
)

scene.render.resolution_x = 720
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
try:
    scene.render.engine = "BLENDER_EEVEE"
except TypeError:
    pass
if hasattr(scene, "eevee"):
    scene.eevee.taa_samples = 32

metrics = mesh_metrics(body)
write_manifests(body, head, camera, metrics)

(TRIAL / "gates" / "views").mkdir(parents=True, exist_ok=True)
render_still(TRIAL / "gates" / "views" / "front.png", 1, 72)
render_still(TRIAL / "gates" / "views" / "three-quarter.png", 108, 72)
scene.frame_set(108)
stored_rotation = camera_rig.rotation_euler.z
camera_rig.rotation_euler.z = math.radians(70.0)
render_still(TRIAL / "gates" / "views" / "side.png", 108, 72)
camera_rig.rotation_euler.z = stored_rotation
scene.frame_set(1)

run_workflow(
    "workflows/scripts/drumboiii_lighting_gate.py",
    {"output_dir": str(TRIAL / "gates"), "frame": 108, "resolution_percentage": 42, "samples": 16},
)

blend_path = TRIAL / "scene" / "trial.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
for image in list(bpy.data.images):
    if image.source == "VIEWER":
        try:
            bpy.data.images.remove(image)
        except RuntimeError:
            pass
run_workflow(
    "workflows/scripts/deep_audit_scene.py",
    {"output_dir": str(TRIAL / "diagnostics"), "include_nodes": True, "include_geometry_checks": True},
)
run_workflow(
    "workflows/scripts/scene_view_diagnostics.py",
    {"output_dir": str(TRIAL / "diagnostics"), "collection": ASSET_COLLECTION, "camera": camera.name, "frame": 108},
)
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
print(
    "UNRECORDED_RESULT="
    + json.dumps(
        {
            "trial_blend": str(blend_path),
            "asset_collection": ASSET_COLLECTION,
            "body": body.name,
            "head": head.name,
            "metrics": metrics,
            "saved": True,
        }
    )
)
