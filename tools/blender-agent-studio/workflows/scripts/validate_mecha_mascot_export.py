"""Re-import the published Mecha Mascot GLB and write an independent integrity report."""
import json
from pathlib import Path

import bpy
import bmesh


P = globals().get("STUDIO_PARAMS", globals().get("UNRECORDED_PARAMS", {}))
source = Path(P["glb"]).expanduser().resolve()
output = Path(P["output"]).expanduser().resolve()
output.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(source), merge_vertices=True)
meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
checks = []
for obj in meshes:
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.normal_update()
        checks.append(
            {
                "object": obj.name,
                "vertices": len(bm.verts),
                "faces": len(bm.faces),
                "boundary_edges": sum(1 for edge in bm.edges if edge.is_boundary),
                "non_manifold_edges": sum(1 for edge in bm.edges if not edge.is_manifold),
                "materials": [slot.material.name for slot in obj.material_slots if slot.material],
            }
        )
    finally:
        bm.free()
passed = len(meshes) == 2 and all(item["boundary_edges"] == 0 and item["non_manifold_edges"] == 0 for item in checks)
payload = {
    "schema_version": 1,
    "workflow": "validate-mecha-mascot-export",
    "source": str(source),
    "bytes": source.stat().st_size,
    "passed": passed,
    "mesh_count": len(meshes),
    "objects": [obj.name for obj in bpy.context.scene.objects],
    "mesh_checks": checks,
}
output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps(payload))
if not passed:
    raise RuntimeError("GLB re-import integrity failed")
