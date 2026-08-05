"""End-to-end example for the controlled Blender agent workflow."""
import bpy
import json
from pathlib import Path

root = Path(bpy.data.filepath).resolve().parent
demo_dir = Path(globals()["DEMO_OUTPUT"])
demo_dir.mkdir(parents=True, exist_ok=False)


def run(script_name, params):
    path = root / "workflows" / "scripts" / script_name
    namespace = {"UNRECORDED_PARAMS": params, "__name__": "__ustudio_workflow__"}
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), namespace)


scene = bpy.context.scene
original = {
    "resolution_x": scene.render.resolution_x,
    "resolution_y": scene.render.resolution_y,
    "resolution_percentage": scene.render.resolution_percentage,
    "filepath": scene.render.filepath,
    "file_format": scene.render.image_settings.file_format,
    "frame": scene.frame_current,
}

run("scene_spatial_graph.py", {
    "output_dir": str(demo_dir / "01-spatial"),
    "collection": "",
    "max_objects": 80,
    "relation_distance": 0.25,
})
run("scene_view_diagnostics.py", {
    "output_dir": str(demo_dir / "02-camera"),
    "collection": "",
    "camera": "",
    "frame": scene.frame_start,
})
run("iteration_manifest.py", {
    "output_dir": str(demo_dir / "03-iteration-continue"),
    "goal": "Produit centré, lisible, sans highlight blanc sur l'écran",
    "immutable": "proportions, logo, ports, écran",
    "category": "composition",
    "attempt": 1,
    "max_attempts": 3,
    "improved": True,
    "requires_human_taste": False,
    "threatens_invariant": False,
})
run("iteration_manifest.py", {
    "output_dir": str(demo_dir / "04-iteration-stop"),
    "goal": "Produit centré, lisible, sans highlight blanc sur l'écran",
    "immutable": "proportions, logo, ports, écran",
    "category": "composition",
    "attempt": 3,
    "max_attempts": 3,
    "improved": False,
    "requires_human_taste": False,
    "threatens_invariant": False,
})

scene.render.resolution_x = 640
scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except Exception:
    pass

renders = []
for index, preset in enumerate(("softbox-product", "dark-rim"), start=5):
    run("studio_lighting.py", {
        "preset": preset,
        "target_collection": "",
        "intensity": 1.0,
        "mute_existing_lights": True,
        "view_transform": "AgX",
    })
    scene.frame_set(scene.frame_start)
    filepath = demo_dir / f"0{index}-{preset}.png"
    scene.render.filepath = str(filepath)
    bpy.ops.render.render(write_still=True)
    renders.append(str(filepath))

summary = {
    "schema_version": 1,
    "source": bpy.data.filepath,
    "scene": scene.name,
    "camera": scene.camera.name if scene.camera else None,
    "saved": False,
    "artifacts": {
        "spatial_graph": "01-spatial/scene-spatial-graph.json",
        "camera_diagnostics": "02-camera/scene-view-diagnostics.json",
        "continue_manifest": "03-iteration-continue/iteration-manifest.json",
        "stop_manifest": "04-iteration-stop/iteration-manifest.json",
        "renders": renders,
    },
}
(demo_dir / "demo-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

scene.render.resolution_x = original["resolution_x"]
scene.render.resolution_y = original["resolution_y"]
scene.render.resolution_percentage = original["resolution_percentage"]
scene.render.filepath = original["filepath"]
scene.render.image_settings.file_format = original["file_format"]
scene.frame_set(original["frame"])
print("UNRECORDED_DEMO=" + json.dumps(summary, ensure_ascii=False))
