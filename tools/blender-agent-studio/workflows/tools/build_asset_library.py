"""Build a reusable Blender Asset Library without modifying the source .blend."""
import bpy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "asset_library" / "products" / "pulsed-assets.blend"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

CAT_PRODUCT = "7b3e5ed6-6adb-4fe9-918f-4f7240cb1a31"
CAT_MATERIAL = "b4c8a972-ddf5-49be-8f4c-4ee72639fc48"
CAT_WORLD = "126d6c69-e05a-4a9f-9cde-ad27c6ea40be"

marked = []
product = bpy.data.collections.get("PULSED")
if not product:
    raise RuntimeError("Collection PULSED introuvable")
product.asset_mark()
product.asset_data.description = "Pulsed handheld device — collection complète, échelle 1 BU = 1 cm"
product.asset_data.author = "Unrecorded"
product.asset_data.catalog_id = CAT_PRODUCT
marked.append(product.name)

for material in bpy.data.materials:
    if material.name.startswith("M_"):
        material.asset_mark()
        material.asset_data.description = "Pulsed / Unrecorded material"
        material.asset_data.author = "Unrecorded"
        material.asset_data.catalog_id = CAT_MATERIAL
        marked.append(material.name)

world = bpy.data.worlds.get("flroom_world")
if world:
    world.asset_mark()
    world.asset_data.description = "FLROOM near-black studio world"
    world.asset_data.author = "Unrecorded"
    world.asset_data.catalog_id = CAT_WORLD
    marked.append(world.name)

bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT), copy=True, compress=True, relative_remap=True)
print("UNRECORDED_ASSET_LIBRARY=" + json.dumps({"file": str(OUTPUT), "assets": marked}))
