"""Re-import a generated GLB in factory-startup Blender and audit its payload."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--glb", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--prefix", default="K3_TAD_")
    parser.add_argument("--minimum-meshes", type=int, default=20)
    return parser.parse_args(argv)


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def evaluated_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    minimum = Vector((math.inf, math.inf, math.inf))
    maximum = Vector((-math.inf, -math.inf, -math.inf))
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            for vertex in mesh.vertices:
                world = evaluated.matrix_world @ vertex.co
                minimum.x = min(minimum.x, world.x)
                minimum.y = min(minimum.y, world.y)
                minimum.z = min(minimum.z, world.z)
                maximum.x = max(maximum.x, world.x)
                maximum.y = max(maximum.y, world.y)
                maximum.z = max(maximum.z, world.z)
        finally:
            evaluated.to_mesh_clear()
    return minimum, maximum


def main() -> int:
    args = parse_args()
    glb = args.glb.expanduser().resolve()
    output = args.out.expanduser().resolve()
    if not glb.is_file():
        raise FileNotFoundError(glb)
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(glb))
    objects = list(bpy.context.scene.objects)
    meshes = [obj for obj in objects if obj.type == "MESH"]
    empties = [obj for obj in objects if obj.type == "EMPTY"]
    minimum, maximum = evaluated_bounds(meshes)
    size = maximum - minimum
    prefix_violations = [obj.name for obj in objects if not obj.name.startswith(args.prefix)]
    checks = {
        "minimum_mesh_count": len(meshes) >= args.minimum_meshes,
        "named_root_present": any(obj.name == args.prefix + "ROOT" for obj in objects),
        "positive_volume": all(value > 0.001 for value in size),
        "prefix_preserved": not prefix_violations,
        "materials_present": len(bpy.data.materials) >= 5,
        "no_cameras_exported": not any(obj.type == "CAMERA" for obj in objects),
        "no_lights_exported": not any(obj.type == "LIGHT" for obj in objects),
    }
    report = {
        "schema_version": 1,
        "status": "completed",
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "blender_version": bpy.app.version_string,
        "source_glb": str(glb),
        "source_bytes": glb.stat().st_size,
        "object_count": len(objects),
        "mesh_count": len(meshes),
        "empty_count": len(empties),
        "material_count": len(bpy.data.materials),
        "bounds_m": {
            "min": [round(value, 6) for value in minimum],
            "max": [round(value, 6) for value in maximum],
            "size": [round(value, 6) for value in size],
        },
        "prefix_violations": prefix_violations,
        "checks": checks,
        "passed": all(checks.values()),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("K3_GLTF_VALIDATION=" + json.dumps(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
