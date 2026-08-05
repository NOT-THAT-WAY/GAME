"""Configure the open FL Studio projection template like the Drumboiii camera tutorial."""

import bpy
import json
from datetime import datetime
from pathlib import Path


PROJECT_DIR = Path(bpy.data.filepath).resolve().parent
MANIFEST = PROJECT_DIR / "workspace-manifest.json"

window = bpy.context.window
screen = bpy.context.screen
if not window or not screen:
    raise RuntimeError("This workspace setup must run in Blender with a visible GUI")

workspace = window.workspace
workspace.name = "USTUDIO Camera Lab"


def split(area, direction, factor):
    before = set(screen.areas)
    with bpy.context.temp_override(window=window, screen=screen, area=area):
        bpy.ops.screen.area_split(direction=direction, factor=factor)
    with bpy.context.temp_override(window=window, screen=screen):
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=2)
    created = [candidate for candidate in screen.areas if candidate not in before]
    if not created:
        raise RuntimeError(f"Unable to split area {direction}")
    return created[0]


# Start from the largest 3D viewport in the default Layout workspace.
view_areas = [area for area in screen.areas if area.type == "VIEW_3D"]
if not view_areas:
    raise RuntimeError("No 3D viewport found")
largest = max(view_areas, key=lambda area: area.width * area.height)

# Reserve the lower third for the Dope Sheet, as in the 17:57 Drumboiii tutorial.
split(largest, "HORIZONTAL", 0.32)
split_views = sorted([area for area in screen.areas if area.type == "VIEW_3D"], key=lambda area: area.y)
if len(split_views) < 2:
    raise RuntimeError("Horizontal camera/keyframe split failed")
bottom = split_views[0]
top_main = split_views[-1]
bottom.type = "DOPESHEET_EDITOR"
bottom_space = bottom.spaces.active
bottom_space.mode = "DOPESHEET"
bottom_space.show_region_ui = False
bottom_space.show_region_channels = True

# Split the upper area into a narrow live camera preview and a large working viewport.
split(top_main, "VERTICAL", 0.27)
upper_views = [area for area in screen.areas if area.type == "VIEW_3D"]
upper_views.sort(key=lambda area: area.x)
if len(upper_views) < 2:
    raise RuntimeError("Upper camera/work view split failed")
camera_area = upper_views[0]
work_area = max(upper_views[1:], key=lambda area: area.width)

camera_space = camera_area.spaces.active
camera_space.shading.type = "RENDERED"
camera_space.overlay.show_overlays = False
camera_space.region_3d.view_perspective = "CAMERA"
camera_space.lock_camera = False
camera_space.show_region_toolbar = False
camera_space.show_region_ui = False

work_space = work_area.spaces.active
work_space.shading.type = "SOLID"
work_space.overlay.show_overlays = True
work_space.overlay.show_relationship_lines = True
work_space.show_region_toolbar = True
work_space.show_region_ui = False

# Keep the existing right-hand Outliner and Properties editors from the default workspace.
scene = bpy.context.scene
scene["ustudio_workspace"] = workspace.name
scene["ustudio_workspace_layout"] = "left live rendered camera | center object+camera | bottom dope sheet | right outliner+properties"
scene.frame_set(max(scene.frame_start, min(scene.frame_current, scene.frame_end)))
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)

areas = sorted(
    [
        {"type": area.type, "x": area.x, "y": area.y, "width": area.width, "height": area.height}
        for area in screen.areas
    ],
    key=lambda item: (-item["y"], item["x"]),
)
manifest = {
    "workspace": workspace.name,
    "created_at": datetime.now().astimezone().isoformat(),
    "blend": bpy.data.filepath,
    "layout": {
        "left": "VIEW_3D camera view, Rendered, overlays off",
        "center": "VIEW_3D object and camera rig, Solid, relationship lines on",
        "bottom": "Dope Sheet with channels and keyframes",
        "right": "Outliner and Properties preserved",
    },
    "areas": areas,
    "tutorial_reference": "knowledge/tutorials/drumboii-camera-tutorial-2026-07-18 — 00:00–01:32",
}
MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps(manifest, ensure_ascii=False))
