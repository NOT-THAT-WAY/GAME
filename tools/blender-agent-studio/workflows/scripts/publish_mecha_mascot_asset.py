"""Publish the validated Mecha Mascot collection into the local Blender asset library."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import bpy


P = globals().get("STUDIO_PARAMS", globals().get("UNRECORDED_PARAMS", {}))
if P.get("confirm_publish") is not True:
    raise RuntimeError("confirm_publish=true est requis: ce script sauvegarde puis réduit la scène en asset isolé")
collection_name = str(P.get("collection", "K3_MECHA_MASCOT_ASSET"))
trial_blend = Path(bpy.data.filepath).resolve()
destination = Path(P["destination"]).expanduser().resolve()
glb_source = Path(P["glb_source"]).expanduser().resolve()
glb_destination = destination.with_suffix(".glb")
manifest_destination = destination.with_suffix(".manifest.json")
catalog_id = str(P["catalog_id"])
version = str(P.get("version", "1.0.0"))
source_reference = str(P.get("source_reference", "")) or None
asset_author = str(P.get("author", os.environ.get("STUDIO_USER", "Blender Agent Studio")))

asset = bpy.data.collections.get(collection_name)
if asset is None:
    raise RuntimeError("Asset collection not found: " + collection_name)
if asset.asset_data is None:
    asset.asset_mark()
asset.asset_data.catalog_id = catalog_id
asset.asset_data.author = asset_author
asset.asset_data.description = "Mecha Mascot — reusable soft humanoid character"

if destination.exists() or glb_destination.exists() or manifest_destination.exists():
    raise RuntimeError("Versioned asset destination already exists")
destination.parent.mkdir(parents=True, exist_ok=True)

# Persist the catalog assignment only after all output preconditions have passed.
bpy.ops.wm.save_as_mainfile(filepath=str(trial_blend), check_existing=False)

keep = set(asset.all_objects)
for obj in list(bpy.data.objects):
    if obj not in keep:
        bpy.data.objects.remove(obj, do_unlink=True)
for collection in list(bpy.data.collections):
    if collection != asset:
        bpy.data.collections.remove(collection)

scene = bpy.context.scene
scene.name = "MECHA_MASCOT_ASSET"
scene.camera = None
scene.frame_start = 1
scene.frame_end = 1
scene.world = None
for image in list(bpy.data.images):
    if image.users == 0:
        bpy.data.images.remove(image)

bpy.ops.wm.save_as_mainfile(filepath=str(destination), check_existing=False)
shutil.copy2(glb_source, glb_destination)
manifest = {
    "schema_version": 1,
    "asset_name": "Mecha Mascot",
    "version": version,
    "blend": str(destination),
    "glb": str(glb_destination),
    "bytes": {"blend": destination.stat().st_size, "glb": glb_destination.stat().st_size},
    "collection": collection_name,
    "root": "K3_MECHA_MASCOT_ROOT",
    "meshes": ["K3_MECHA_BODY", "K3_MECHA_HEAD"],
    "catalog_id": catalog_id,
    "catalog_path": "Characters/Mascots",
    "front_axis": "-Y",
    "up_axis": "+Z",
    "ground_contact_z_m": 0.0,
    "source_trial": str(trial_blend),
    "source_reference": source_reference,
    "topology": {"body_manifold": True, "head_manifold": True, "uv_ready": True},
    "deformation_note": "Use the root for global motion and a shared Lattice or armature for future Squishy deformation.",
}
manifest_destination.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps(manifest, ensure_ascii=False))
