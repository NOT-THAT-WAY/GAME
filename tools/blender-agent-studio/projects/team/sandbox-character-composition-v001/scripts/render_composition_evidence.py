"""Render deterministic visual evidence and the SB_Idle review preview.

This script mutates only the in-memory render session and never saves the .blend. It renders the
saved C composition with identical camera settings for the clay, light-layer and final comparisons.

Usage:
  blender --background --factory-startup <composition.blend> \
    --python render_composition_evidence.py -- <render-root> <evidence-root>
"""

from __future__ import annotations

import bpy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


PREFIX = "BAS_SANDBOX_CHARACTER_COMPOSITION_V001_"
STUDIO_ROOT = Path(__file__).resolve().parents[4]
HERO_FRAMES = [1, 11, 21, 31, 41, 51]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def workspace_path(path: Path) -> str:
    return path.resolve().relative_to(STUDIO_ROOT).as_posix()


def render_png(scene, path: Path, camera, frame: int, width: int, height: int, samples: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    scene.camera = camera
    scene.frame_set(frame)
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = samples
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    if not path.is_file():
        raise RuntimeError("render missing: " + str(path))
    print("RENDERED " + str(path))


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) != 2:
        raise SystemExit("expected: <render-root> <evidence-root>")
    render_root, evidence_root = map(lambda value: Path(value).expanduser().resolve(), argv)
    render_root.mkdir(parents=True, exist_ok=True)
    evidence_root.mkdir(parents=True, exist_ok=True)

    scene = bpy.context.scene
    hero = bpy.data.objects[PREFIX + "CAM_HERO_3Q"]
    front = bpy.data.objects[PREFIX + "CAM_FRONT_ORTHO"]
    profile = bpy.data.objects[PREFIX + "CAM_PROFILE_ORTHO"]
    lights = {
        "key": bpy.data.objects[PREFIX + "LIGHT_KEY"],
        "fill": bpy.data.objects[PREFIX + "LIGHT_FILL"],
        "rim": bpy.data.objects[PREFIX + "LIGHT_RIM"],
    }
    for light in lights.values():
        light.hide_render = False

    outputs = []

    # Final neutral baseline at the contracted delivery settings.
    final_path = render_root / "final" / "neutral-design-baseline.png"
    render_png(scene, final_path, hero, 1, 1920, 1080, 64)
    outputs.append({"role": "final_render", "path": workspace_path(final_path), "sha256": sha256(final_path)})

    # Same framing with the material category neutralized; stage remains unchanged.
    clay = bpy.data.materials.new(PREFIX + "TEMP_CLAY_GATE")
    clay.diffuse_color = (0.42, 0.44, 0.48, 1.0)
    clay.use_nodes = True
    principled = clay.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (0.42, 0.44, 0.48, 1.0)
    principled.inputs["Roughness"].default_value = 0.78
    view_layer = bpy.context.view_layer
    previous_override = view_layer.material_override
    view_layer.material_override = clay
    clay_path = render_root / "gates" / "clay-hero-f001.png"
    render_png(scene, clay_path, hero, 1, 960, 540, 32)
    outputs.append({"role": "clay_gate", "path": workspace_path(clay_path), "sha256": sha256(clay_path)})
    view_layer.material_override = previous_override

    # Attributable light layers, identical camera/frame/resolution.
    for light in lights.values():
        light.hide_render = True
    lights["key"].hide_render = False
    key_path = render_root / "gates" / "light-key-only-f001.png"
    render_png(scene, key_path, hero, 1, 960, 540, 32)
    outputs.append({"role": "lighting_gate", "path": workspace_path(key_path), "sha256": sha256(key_path)})
    lights["fill"].hide_render = False
    key_fill_path = render_root / "gates" / "light-key-fill-f001.png"
    render_png(scene, key_fill_path, hero, 1, 960, 540, 32)
    outputs.append({"role": "lighting_gate", "path": workspace_path(key_fill_path), "sha256": sha256(key_fill_path)})
    lights["rim"].hide_render = False
    full_path = render_root / "gates" / "light-full-f001.png"
    render_png(scene, full_path, hero, 1, 960, 540, 32)
    outputs.append({"role": "lighting_gate", "path": workspace_path(full_path), "sha256": sha256(full_path)})

    # Utility identity/contact gates.
    for camera, label in ((front, "front"), (profile, "profile")):
        for frame in (1, 31):
            path = render_root / "gates" / f"control-{label}-f{frame:03d}.png"
            render_png(scene, path, camera, frame, 720, 720, 32)
            outputs.append({"role": "control_gate", "path": workspace_path(path), "sha256": sha256(path)})

    # Hero pose tiles across the whole phase of the loop.
    for frame in HERO_FRAMES:
        path = render_root / "hero-tiles" / f"hero-f{frame:03d}.png"
        render_png(scene, path, hero, frame, 640, 360, 32)
        outputs.append({"role": "contact_tile", "path": workspace_path(path), "sha256": sha256(path)})

    # Every sampled frame for the complete neutral preview. No motion blur or DOF.
    for frame in range(scene.frame_start, scene.frame_end + 1):
        path = render_root / "preview-frames" / f"frame_{frame:04d}.png"
        render_png(scene, path, hero, frame, 960, 540, 24)
    outputs.append(
        {
            "role": "preview_frame_sequence",
            "path": workspace_path(render_root / "preview-frames"),
            "frames": scene.frame_end - scene.frame_start + 1,
        }
    )

    scene_audit = {
        "schema_version": 1,
        "project_id": "sandbox-character-composition-v001",
        "source": workspace_path(Path(bpy.data.filepath)),
        "source_sha256": sha256(Path(bpy.data.filepath)),
        "scene": scene.name,
        "frame_range": [scene.frame_start, scene.frame_end],
        "fps": scene.render.fps / scene.render.fps_base,
        "objects": len(scene.objects),
        "object_types": {kind: sum(1 for obj in scene.objects if obj.type == kind) for kind in sorted({obj.type for obj in scene.objects})},
        "collections": {collection.name: [obj.name for obj in collection.objects] for collection in scene.collection.children},
        "cameras": [obj.name for obj in scene.objects if obj.type == "CAMERA"],
        "lights": [obj.name for obj in scene.objects if obj.type == "LIGHT"],
        "materials": [material.name for material in bpy.data.materials if not material.name.endswith("TEMP_CLAY_GATE")],
        "actions": {action.name: [round(value, 6) for value in action.frame_range] for action in bpy.data.actions},
        "active_camera": hero.name,
        "missing_images": [image.name for image in bpy.data.images if image.source == "FILE" and not Path(bpy.path.abspath(image.filepath)).is_file()],
        "dirty": bpy.data.is_dirty,
        "saved_by_script": False,
        "runtime_export": scene.get("runtime_export"),
    }
    (evidence_root / "scene-audit.json").write_text(json.dumps(scene_audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    render_settings = {
        "schema_version": 1,
        "project_id": "sandbox-character-composition-v001",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine": scene.render.engine,
        "final_resolution": [1920, 1080, 100],
        "final_samples": 64,
        "preview_resolution": [960, 540, 100],
        "preview_samples": 24,
        "fps": scene.render.fps / scene.render.fps_base,
        "frame_range": [scene.frame_start, scene.frame_end],
        "image": {"format": "PNG", "color_mode": "RGB", "color_depth": "8", "compression": 15},
        "color_management": {
            "view_transform": scene.view_settings.view_transform,
            "look": scene.view_settings.look,
            "exposure": scene.view_settings.exposure,
            "gamma": scene.view_settings.gamma,
        },
        "camera": {
            "name": hero.name,
            "type": hero.data.type,
            "lens_mm": hero.data.lens,
            "sensor_width_mm": hero.data.sensor_width,
            "clip": [hero.data.clip_start, hero.data.clip_end],
            "dof_enabled": hero.data.dof.use_dof,
            "focus_object": hero.data.dof.focus_object.name if hero.data.dof.focus_object else None,
        },
        "lighting": {
            role: {
                "name": obj.name,
                "type": obj.data.type,
                "energy": obj.data.energy,
                "size": obj.data.size,
                "color": [round(value, 6) for value in obj.data.color],
            }
            for role, obj in lights.items()
        },
        "output_policy": "render and evidence only; blend never saved by this script",
    }
    (evidence_root / "render-settings.json").write_text(json.dumps(render_settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (evidence_root / "render-manifest.json").write_text(
        json.dumps({"schema_version": 1, "project_id": "sandbox-character-composition-v001", "outputs": outputs}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("EVIDENCE_RENDER_COMPLETE " + str(render_root))


if __name__ == "__main__":
    main()
