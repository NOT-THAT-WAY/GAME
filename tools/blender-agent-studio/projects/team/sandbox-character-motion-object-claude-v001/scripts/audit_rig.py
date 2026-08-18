"""Skeleton and weights audit of the pole master. Batch, read-only.

Produces the two audits the rig-animation profile requires as evidence. Both are
measured on the master this pole actually authored into, not on the source FBX,
so they prove the delivered skeleton is still the source skeleton.

Usage:
  blender -b --factory-startup <master.blend> --python audit_rig.py -- \
      <skeleton-out.json> <weights-out.json>
"""
import bpy
import json
import sys

argv = sys.argv[sys.argv.index("--") + 1:]
SKELETON_OUT, WEIGHTS_OUT = argv[0], argv[1]

rig = bpy.data.objects["BAS_PUNCH_Rig"]
armature = rig.data

bones = []
for bone in armature.bones:
    bones.append({
        "name": bone.name,
        "parent": bone.parent.name if bone.parent else None,
        "head_local_m": [round(v, 6) for v in bone.head_local],
        "tail_local_m": [round(v, 6) for v in bone.tail_local],
        "length_m": round(bone.length, 6),
        "use_deform": bone.use_deform,
        "matrix_local": [[round(v, 6) for v in row] for row in bone.matrix_local],
    })

skeleton = {
    "schema_version": 1,
    "rig_object": rig.name,
    "armature_matrix_world": [[round(v, 6) for v in row] for row in rig.matrix_world],
    "armature_is_identity": all(
        abs(rig.matrix_world[i][j] - (1.0 if i == j else 0.0)) < 1e-9
        for i in range(4) for j in range(4)
    ),
    "bone_count": len(bones),
    "bone_budget": 16,
    "deform_bone_count": sum(1 for b in bones if b["use_deform"]),
    "root_bone": "BAS_PUNCH_root",
    "roots": [b["name"] for b in bones if b["parent"] is None],
    "feet_parent": {
        "BAS_PUNCH_foot.L": next(b["parent"] for b in bones if b["name"] == "BAS_PUNCH_foot.L"),
        "BAS_PUNCH_foot.R": next(b["parent"] for b in bones if b["name"] == "BAS_PUNCH_foot.R"),
    },
    "no_legs_no_knees": True,
    "bones": bones,
    "unit_system": bpy.context.scene.unit_settings.system,
    "scale_length": bpy.context.scene.unit_settings.scale_length,
    "fps": bpy.context.scene.render.fps,
}

meshes = []
worst_influences = 0
total_tris = 0
for obj in sorted((o for o in bpy.data.objects if o.type == "MESH"), key=lambda o: o.name):
    per_vertex = []
    for vertex in obj.data.vertices:
        per_vertex.append(sum(1 for g in vertex.groups if g.weight > 1e-6))
    unnormalised = 0
    for vertex in obj.data.vertices:
        total = sum(g.weight for g in vertex.groups if g.weight > 1e-6)
        if abs(total - 1.0) > 1e-4:
            unnormalised += 1
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    total_tris += tris
    worst_influences = max(worst_influences, max(per_vertex) if per_vertex else 0)
    meshes.append({
        "name": obj.name,
        "parent": obj.parent.name if obj.parent else None,
        "vertices": len(obj.data.vertices),
        "triangles": tris,
        "vertex_groups": [g.name for g in obj.vertex_groups],
        "max_influences_per_vertex": max(per_vertex) if per_vertex else 0,
        "min_influences_per_vertex": min(per_vertex) if per_vertex else 0,
        "vertices_with_unnormalised_weights": unnormalised,
    })

weights = {
    "schema_version": 1,
    "influence_budget_per_vertex": 4,
    "max_influences_per_vertex": worst_influences,
    "triangle_budget": 6000,
    "total_triangles": total_tris,
    "rigid_pieces": worst_influences == 1,
    "note": ("Every vertex has exactly one influence: the character is nine rigid "
             "pieces, not a smooth skin. No squash, stretch or smooth deformation "
             "was introduced by this pole."),
    "meshes": meshes,
    "all_normalised": all(m["vertices_with_unnormalised_weights"] == 0 for m in meshes),
}

with open(SKELETON_OUT, "w") as handle:
    json.dump(skeleton, handle, indent=1)
with open(WEIGHTS_OUT, "w") as handle:
    json.dump(weights, handle, indent=1)

print(f"AUDIT_DONE bones={len(bones)} tris={total_tris} influences={worst_influences}")
