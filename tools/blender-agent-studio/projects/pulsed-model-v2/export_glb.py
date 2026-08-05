"""Export .glb du modele v2 (sans studio ni cutters).

  blender -b scene/pulsed_v2.blend --python export_glb.py
"""

import os

import bpy

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "exports", "pulsed_v2.glb")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

# Les cutters booleens ne doivent pas partir dans l'export.
cut = bpy.data.collections.get("PV2_cutters")
keep = []
if cut:
    for o in cut.objects:
        o.hide_viewport = True
        keep.append(o)

bpy.ops.object.select_all(action="DESELECT")
for o in bpy.data.objects:
    if o.type == "MESH" and o.name.startswith("PV2_") and o not in keep:
        o.select_set(True)

bpy.ops.export_scene.gltf(
    filepath=OUT,
    export_format="GLB",
    use_selection=True,
    export_apply=True,
    export_materials="EXPORT",
    export_yup=True,
)

size = os.path.getsize(OUT) / 1e6
print(f"[ok] -> {OUT} ({size:.2f} Mo)")
