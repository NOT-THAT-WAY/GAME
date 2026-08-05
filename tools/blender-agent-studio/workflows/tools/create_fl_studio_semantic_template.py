"""Create a readable semantic-panel FL Studio box with soft studio lighting."""

import bpy
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE_VIDEO = Path(os.environ.get("FL_STUDIO_SOURCE_VIDEO", ROOT / "projects" / "fl-studio-box-semantic-template" / "media" / "current" / "master.mp4"))
PROJECT_DIR = ROOT / "projects" / "fl-studio-box-semantic-template"
MEDIA_DIR = PROJECT_DIR / "media" / "current"
INCOMING_DIR = PROJECT_DIR / "incoming"
GATE_DIR = PROJECT_DIR / "sample-gate"
PROJECT_FILE = PROJECT_DIR / "FL_Studio_Box_Semantic_Template.blend"

SLOTS = {
    "playlist": {"material": "M_MOVIE_PLAYLIST", "filename": "playlist.mp4", "crop": "crop=900:250:660:155"},
    # Keep only the useful kit list. The former 235x870 crop also contained the
    # toolbar and waveform, which became stretched across the trapezoidal wall.
    "browser": {"material": "M_MOVIE_BROWSER", "filename": "browser.mp4", "crop": "crop=215:580:160:310"},
    "mixer": {"material": "M_MOVIE_MIXER", "filename": "mixer.mp4", "crop": "crop=510:490:1290:320"},
    "piano_roll": {"material": "M_MOVIE_PIANO_ROLL", "filename": "piano-roll.mp4", "crop": "crop=900:430:380:380"},
    "channel_rack": {"material": "M_MOVIE_CHANNEL_RACK", "filename": "controller.mp4", "crop": "crop=825:170:970:810"},
}

for directory in (PROJECT_DIR, MEDIA_DIR, INCOMING_DIR, GATE_DIR):
    directory.mkdir(parents=True, exist_ok=True)
master = MEDIA_DIR / "master.mp4"
if SOURCE_VIDEO.resolve() != master.resolve():
    shutil.copy2(SOURCE_VIDEO, master)

for slot, spec in SLOTS.items():
    destination = MEDIA_DIR / spec["filename"]
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(SOURCE_VIDEO),
            "-vf", spec["crop"] + ",scale=trunc(iw/2)*2:trunc(ih/2)*2",
            # Every frame is a keyframe: Blender can scrub/reverse the movie
            # texture without briefly decoding an unrelated GOP.
            "-an", "-c:v", "libx264", "-g", "1", "-keyint_min", "1",
            "-sc_threshold", "0", "-pix_fmt", "yuv420p", str(destination),
        ],
        check=True,
    )
    material = bpy.data.materials.get(spec["material"])
    texture = material.node_tree.nodes.get("USTUDIO_FL_STUDIO_MOVIE") if material and material.node_tree else None
    if not texture:
        raise RuntimeError(f"Movie slot missing: {slot}")
    image = bpy.data.images.load(str(destination), check_existing=False)
    image.name = "USTUDIO_SEMANTIC_" + slot.upper()
    image.source = "MOVIE"
    texture.image = image
    texture.image_user.frame_start = 1
    texture.image_user.frame_duration = 406
    texture.image_user.use_cyclic = True
    texture.image_user.use_auto_refresh = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Roughness"].default_value = 0.38
        if bsdf.inputs.get("Emission Strength"):
            bsdf.inputs["Emission Strength"].default_value = 0.35

scene = bpy.context.scene
scene.name = "FL_STUDIO_BOX_SEMANTIC_TEMPLATE"
scene.render.fps = 30
scene.frame_start = 1
scene.frame_end = 406
scene.view_settings.look = "AgX - Medium Low Contrast"
scene.view_settings.exposure = 0.35
scene["ustudio_template"] = True
scene["ustudio_semantic_template"] = True
scene["ustudio_mapping_mode"] = "five readable semantic crops from one synchronized master"
scene["ustudio_master_source"] = str(master)
scene["ustudio_crop_contract"] = json.dumps({slot: spec["crop"] for slot, spec in SLOTS.items()})


def bilinear_panel_mesh(name, corners, columns=20, rows=40):
    """Build a dense UV grid so a movie maps cleanly to a trapezoid.

    A single Blender quad is triangulated internally. On a strong trapezoid,
    the two affine triangles create a visible diagonal discontinuity. A dense
    bilinear grid approximates the intended projective deformation smoothly.
    """
    p00, p10, p11, p01 = corners
    vertices = []
    for row in range(rows + 1):
        v = row / rows
        for column in range(columns + 1):
            u = column / columns
            vertices.append(tuple(
                (1 - v) * ((1 - u) * p00[axis] + u * p10[axis])
                + v * ((1 - u) * p01[axis] + u * p11[axis])
                for axis in range(3)
            ))
    faces = []
    stride = columns + 1
    for row in range(rows):
        for column in range(columns):
            a = row * stride + column
            faces.append((a, a + 1, a + 1 + stride, a + stride))
    mesh = bpy.data.meshes.new(name + "_GRID_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for polygon in mesh.polygons:
        for loop_index in polygon.loop_indices:
            vertex_index = mesh.loops[loop_index].vertex_index
            row, column = divmod(vertex_index, stride)
            uv_layer.data[loop_index].uv = (column / columns, row / rows)
    return mesh


# Replace the original four-vertex trapezoid with a stable UV grid.
browser_panel = bpy.data.objects.get("USTUDIO_BROWSER_LEFT_WALL")
if browser_panel:
    old_mesh = browser_panel.data
    old_materials = list(old_mesh.materials)
    browser_panel.data = bilinear_panel_mesh(
        browser_panel.name,
        [(-4.08, -0.36, 1.05), (-3.16, 1.28, 2.55),
         (-3.16, 1.28, 5.02), (-4.08, -0.36, 5.05)],
    )
    for material in old_materials:
        browser_panel.data.materials.append(material)
    if old_mesh.users == 0:
        bpy.data.meshes.remove(old_mesh)
    browser_panel["ustudio_mapping"] = "bilinear UV grid 20x40 — kit list only"

# The source videos already contain the real playhead.
for name in ("USTUDIO_PLAYHEAD_BACK", "USTUDIO_PLAYHEAD_FLOOR"):
    obj = bpy.data.objects.get(name)
    if obj:
        obj.hide_render = True
        obj.hide_viewport = True

# Replace the dark neon-heavy grade with broad, neutral studio illumination.
if scene.world and scene.world.node_tree:
    background = scene.world.node_tree.nodes.get("Background")
    if background:
        background.inputs["Color"].default_value = (0.020, 0.025, 0.038, 1)
        background.inputs["Strength"].default_value = 0.30

light_settings = {
    "USTUDIO_FRONT_KEY": {"energy": 520, "color": (1.0, 0.88, 0.78), "radius": 3.5},
    "USTUDIO_FRONT_FILL": {"energy": 460, "color": (0.72, 0.82, 1.0), "radius": 3.2},
    "USTUDIO_GREEN_BOUNCE": {"energy": 55, "color": (0.55, 1.0, 0.35), "radius": 2.2},
    "USTUDIO_INTERIOR_FILL": {"energy": 520, "color": (0.82, 0.88, 1.0), "radius": 2.8},
}
for name, settings in light_settings.items():
    obj = bpy.data.objects.get(name)
    if obj and obj.type == "LIGHT":
        obj.data.energy = settings["energy"]
        obj.data.color = settings["color"]
        obj.data.shadow_soft_size = settings["radius"]

def add_area(name, location, energy, size, color, target):
    data = bpy.data.lights.new(name + "_DATA", "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    scene.collection.objects.link(obj)
    con = obj.constraints.new("TRACK_TO")
    con.target = target
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    return obj

target = bpy.data.objects.get("USTUDIO_BOX_TARGET")
if target:
    add_area("USTUDIO_SOFT_KEY", (-4.6, -5.8, 7.5), 720, 5.5, (1.0, 0.86, 0.76), target)
    add_area("USTUDIO_SOFT_FILL", (4.8, -4.5, 5.3), 580, 5.0, (0.68, 0.80, 1.0), target)

shadow_target = bpy.data.objects.new("USTUDIO_SHADOW_TARGET", None)
shadow_target.location = (0, 0.4, 0.0)
shadow_target.empty_display_type = "SPHERE"
shadow_target.empty_display_size = 0.18
scene.collection.objects.link(shadow_target)
add_area("USTUDIO_FLOAT_SHADOW_KEY", (0, -0.8, 8.5), 760, 4.5, (0.88, 0.92, 1.0), shadow_target)

shell_material = bpy.data.materials.get("M_BOX_WARM_GREY")
if shell_material and shell_material.node_tree:
    bsdf = shell_material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.12, 0.105, 0.13, 1)
        bsdf.inputs["Metallic"].default_value = 0.22
        bsdf.inputs["Roughness"].default_value = 0.42

floor_material = bpy.data.materials.get("M_STAGE_FLOOR")
if floor_material and floor_material.node_tree:
    floor_bsdf = floor_material.node_tree.nodes.get("Principled BSDF")
    if floor_bsdf:
        floor_bsdf.inputs["Base Color"].default_value = (0.030, 0.040, 0.060, 1)
        floor_bsdf.inputs["Metallic"].default_value = 0.08
        floor_bsdf.inputs["Roughness"].default_value = 0.58

# Raise the entire box and animate it as one massive floating object.
float_root = bpy.data.objects.new("USTUDIO_BOX_FLOAT_ROOT", None)
float_root.empty_display_type = "CUBE"
float_root.empty_display_size = 0.45
float_root.location = (0, 0, 0.0)
scene.collection.objects.link(float_root)

for collection_name in ("BOX_SHELL", "FL_STUDIO_INTERIOR", "PLAYBACK_MOTION"):
    collection = bpy.data.collections.get(collection_name)
    if not collection:
        continue
    for obj in list(collection.objects):
        if obj.name == "USTUDIO_GROUND" or obj.parent is not None:
            continue
        matrix = obj.matrix_world.copy()
        obj.parent = float_root
        obj.matrix_world = matrix

float_keys = (
    (1, (0.00, 0.00, 1.20), (-1.0, 0.8, -0.6)),
    (102, (0.10, 0.02, 1.38), (1.0, -0.8, 0.8)),
    (203, (-0.08, -0.01, 1.18), (-0.7, 1.0, -0.5)),
    (305, (0.06, 0.02, 1.34), (0.9, -0.6, 0.6)),
    (406, (0.00, 0.00, 1.20), (-1.0, 0.8, -0.6)),
)
for frame, location, rotation_deg in float_keys:
    float_root.location = location
    float_root.rotation_euler = tuple(__import__("math").radians(value) for value in rotation_deg)
    float_root.keyframe_insert("location", frame=frame)
    float_root.keyframe_insert("rotation_euler", frame=frame)

# Camera reacts a few frames late, following the tutorial's operator-like target delay.
camera = scene.camera
if camera:
    camera.animation_data_clear()
    camera_keys = (
        (1, (0.40, -20.00, 5.10), 46.0),
        (18, (-0.10, -20.30, 5.00), 47.0),
        (120, (0.35, -18.80, 5.35), 44.0),
        (150, (0.22, -19.10, 5.25), 45.0),
        (220, (0.35, -19.20, 5.25), 45.5),
        (238, (0.55, -19.50, 5.35), 46.5),
        (330, (-0.30, -18.50, 4.95), 43.5),
        (360, (-0.18, -18.80, 5.00), 44.5),
        (406, (0.40, -20.00, 5.10), 46.0),
    )
    for frame, location, lens in camera_keys:
        camera.location = location
        camera.data.lens = lens
        camera.keyframe_insert("location", frame=frame)
        camera.data.keyframe_insert("lens", frame=frame)
    camera.data.dof.use_dof = True
    camera.data.dof.aperture_fstop = 4.5

if target:
    target.animation_data_clear()
    target_keys = (
        (1, (0.00, 0.25, 4.18)),
        (108, (0.08, 0.27, 4.34)),
        (209, (-0.06, 0.24, 4.20)),
        (311, (0.05, 0.27, 4.31)),
        (406, (0.00, 0.25, 4.18)),
    )
    for frame, location in target_keys:
        target.location = location
        target.keyframe_insert("location", frame=frame)
    if camera:
        camera.data.dof.focus_object = target

controller = bpy.data.objects.get("USTUDIO_MEDIA_CONTROLLER")
if controller:
    controller["mapping_mode"] = "semantic panels"
    controller["source_video"] = str(master)
    controller["duration"] = 13.533333
    controller["fps"] = 30

scene.timeline_markers.clear()
for name, frame in (
    ("USTUDIO_MEDIA_IN", 1),
    ("USTUDIO_MEDIA_QUARTER", 102),
    ("USTUDIO_MEDIA_MIDDLE", 203),
    ("USTUDIO_MEDIA_THREE_QUARTERS", 305),
    ("USTUDIO_MEDIA_OUT", 406),
):
    scene.timeline_markers.new(name, frame=frame)

scene.frame_set(203)
bpy.ops.wm.save_as_mainfile(filepath=str(PROJECT_FILE))
scene.render.filepath = str(GATE_DIR / "semantic-frame-0203.png")
bpy.ops.render.render(write_still=True)

manifest = {
    "template": str(PROJECT_FILE.relative_to(ROOT)),
    "created_at": datetime.now().astimezone().isoformat(),
    "mapping": "five isolated semantic panels, synchronized from one master video",
    "source": str(SOURCE_VIDEO),
    "slots": SLOTS,
    "lighting": "soft neutral key/fill, brighter world, reduced green bounce, medium-low contrast",
    "floating_rig": "USTUDIO_BOX_FLOAT_ROOT with delayed camera target and Drumboiii four-key camera gestures",
    "timeline": {"fps": 30, "frames": [1, 406], "duration": 13.533333},
    "workflow": "relink-fl-studio-box-media",
}
(PROJECT_DIR / "semantic-manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps(manifest, ensure_ascii=False))
