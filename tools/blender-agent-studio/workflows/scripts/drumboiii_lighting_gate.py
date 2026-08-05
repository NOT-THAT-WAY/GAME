"""Render cumulative A/B gates for a BAS or legacy USTUDIO layered-lighting rig."""
import bpy
import json
from pathlib import Path

P = globals().get("STUDIO_PARAMS", globals().get("UNRECORDED_PARAMS", {}))
scene = bpy.context.scene
output_value = str(P.get("output_dir", "")).strip()
if not output_value:
    raise RuntimeError("output_dir requis")
output_dir = Path(output_value).expanduser().resolve()
output_dir.mkdir(parents=True, exist_ok=True)

ordered = ["SUN_REFLECTION", "BACK_SHAPE", "SIDE_GLIMMER_A", "SIDE_GLIMMER_B", "DETAIL_RETURN"]
prefix = None
lights = {}
for candidate_prefix in (str(P.get("lighting_prefix", "BAS_LIGHTING_")), "BAS_LIGHTING_", "USTUDIO_LIGHTING_"):
    candidate_lights = {role: bpy.data.objects.get(candidate_prefix + role) for role in ordered}
    if all(obj and obj.type == "LIGHT" for obj in candidate_lights.values()):
        prefix = candidate_prefix
        lights = candidate_lights
        break
if len(lights) != len(ordered):
    missing = [name for name in ordered if name not in lights]
    raise RuntimeError("Rig Drumboiii incomplet: " + ", ".join(missing))
if not scene.camera:
    raise RuntimeError("Caméra active requise pour le gate lumière")

original = {name: obj.hide_render for name, obj in lights.items()}
original_path = scene.render.filepath
original_percentage = scene.render.resolution_percentage
original_frame = scene.frame_current
original_cycles_samples = scene.cycles.samples if hasattr(scene, "cycles") else None
frame = int(P.get("frame", scene.frame_current))
scene.frame_set(frame)
scene.render.resolution_percentage = int(P.get("resolution_percentage", 35))
if scene.render.engine.startswith("BLENDER_EEVEE"):
    pass
elif hasattr(scene, "cycles"):
    scene.cycles.samples = int(P.get("samples", 32))

stages = [("00_BASE_WORLD", [])]
active = []
for role in ordered:
    active = active + [role]
    stages.append((f"{len(active):02d}_{role}", list(active)))

renders = []
try:
    for label, enabled in stages:
        for role, obj in lights.items():
            obj.hide_render = role not in enabled
        destination = output_dir / f"{label}.png"
        scene.render.filepath = str(destination)
        bpy.ops.render.render(write_still=True)
        renders.append({"stage": label, "enabled": enabled, "path": str(destination)})
finally:
    for role, obj in lights.items():
        obj.hide_render = original[role]
    scene.render.filepath = original_path
    scene.render.resolution_percentage = original_percentage
    if original_cycles_samples is not None and hasattr(scene, "cycles"):
        scene.cycles.samples = original_cycles_samples
    scene.frame_set(original_frame)

manifest = {
    "schema_version": 1,
    "workflow": "drumboiii-lighting-gate",
    "source_tutorial": "drumboii-lighting-tutorial-2026-07-20",
    "frame": frame,
    "engine": scene.render.engine,
    "lighting_prefix": prefix,
    "order": ordered,
    "principle": "base environment, reflection sun, shape backlight, then only useful detail glimmers",
    "renders": renders,
    "temporary_state_restored": True,
    "saved": False,
}
manifest_path = output_dir / "lighting-gate-manifest.json"
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps({"workflow": manifest["workflow"], "manifest": str(manifest_path), "renders": len(renders), "saved": False}))
