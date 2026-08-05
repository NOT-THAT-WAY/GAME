"""Render keyframe gates and restore every temporary render setting afterwards."""
import bpy
import json
from pathlib import Path


P = globals().get("STUDIO_PARAMS", globals().get("UNRECORDED_PARAMS", {}))
scene = bpy.context.scene
if not scene.camera:
    raise RuntimeError("Aucune caméra active")
output = Path(P["output_dir"])
output.mkdir(parents=True, exist_ok=True)

original = {
    "engine": scene.render.engine,
    "resolution_x": scene.render.resolution_x,
    "resolution_y": scene.render.resolution_y,
    "resolution_percentage": scene.render.resolution_percentage,
    "file_format": scene.render.image_settings.file_format,
    "filepath": scene.render.filepath,
    "frame": scene.frame_current,
    "cycles_samples": scene.cycles.samples if hasattr(scene, "cycles") else None,
    "eevee_samples": getattr(getattr(scene, "eevee", None), "taa_render_samples", None),
}

marker_prefix = str(P.get("marker_prefix", "BAS_")).strip() or "BAS_"
markers = sorted({marker.frame for marker in scene.timeline_markers if marker.name.startswith(marker_prefix)})
frames = markers or sorted({scene.frame_start, (scene.frame_start + scene.frame_end) // 2, scene.frame_end})
rendered = []
used_engine = None
try:
    scene.render.resolution_x = int(P.get("resolution_x", 720))
    scene.render.resolution_y = int(P.get("resolution_y", 1280))
    scene.render.resolution_percentage = 100
    requested_engine = str(P.get("engine", "BLENDER_EEVEE_NEXT"))
    engine_errors = []
    for candidate in dict.fromkeys(
        (requested_engine, "BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH")
    ):
        try:
            scene.render.engine = candidate
            used_engine = scene.render.engine
            break
        except Exception as exc:
            engine_errors.append(f"{candidate}: {exc}")
    if used_engine is None:
        raise RuntimeError("Aucun moteur de preview disponible: " + "; ".join(engine_errors))
    samples = int(P.get("samples", 32))
    if used_engine == "CYCLES" and hasattr(scene, "cycles"):
        scene.cycles.samples = samples
    elif hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = samples
    scene.render.image_settings.file_format = "PNG"

    for frame in frames:
        scene.frame_set(frame)
        destination = output / f"frame_{frame:04d}.png"
        scene.render.filepath = str(destination)
        bpy.ops.render.render(write_still=True)
        rendered.append(str(destination))
finally:
    scene.render.engine = original["engine"]
    scene.render.resolution_x = original["resolution_x"]
    scene.render.resolution_y = original["resolution_y"]
    scene.render.resolution_percentage = original["resolution_percentage"]
    scene.render.image_settings.file_format = original["file_format"]
    scene.render.filepath = original["filepath"]
    if original["cycles_samples"] is not None and hasattr(scene, "cycles"):
        scene.cycles.samples = original["cycles_samples"]
    if original["eevee_samples"] is not None and hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = original["eevee_samples"]
    scene.frame_set(original["frame"])

manifest = {
    "schema_version": 2,
    "scene": scene.name,
    "camera": scene.camera.name,
    "engine": used_engine,
    "marker_prefix": marker_prefix,
    "frames": frames,
    "files": rendered,
    "source": bpy.data.filepath,
    "temporary_state_restored": True,
    "saved": False,
}
(output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps(manifest))
