"""Build reusable camera and lighting collection assets in a standalone .blend."""
import bpy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "asset_library" / "production" / "unrecorded-production-assets.blend"
MANIFEST = OUTPUT.with_suffix(".manifest.json")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

CAT_ORBIT = "ad1a0464-04f1-4a7a-9370-85d8081ff0c1"
CAT_DOLLY = "f3d49d45-02ca-40ee-9489-a3a513844f4e"
CAT_LIGHT = "f8cdacb9-d009-4bc2-8c61-d99776635626"

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for collection in list(bpy.data.collections):
    bpy.data.collections.remove(collection)


def collection_asset(name, description, catalog_id, tags):
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    collection.asset_mark()
    collection.asset_data.description = description
    collection.asset_data.author = "Unrecorded"
    collection.asset_data.catalog_id = catalog_id
    for tag in tags:
        collection.asset_data.tags.new(tag)
    collection["ustudio_schema"] = 1
    collection["ustudio_asset_type"] = "rig"
    return collection


def empty(collection, name, location=(0, 0, 0)):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.location = location
    collection.objects.link(obj)
    return obj


def camera(collection, name, parent, target, location=(0, -8, 0), lens=70):
    data = bpy.data.cameras.new(name + "_DATA")
    data.lens = lens
    data.show_passepartout = True
    data.passepartout_alpha = 0.85
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    obj.parent = parent
    obj.location = location
    constraint = obj.constraints.new("TRACK_TO")
    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"
    return obj


orbit = collection_asset(
    "USTUDIO_RIG_ORBIT",
    "Rig caméra orbit: déplacer ROOT sur le sujet, animer PIVOT en Z, régler CAMERA et TARGET.",
    CAT_ORBIT,
    ["camera", "orbit", "product", "reusable"],
)
orbit_root = empty(orbit, "USTUDIO_ORBIT_ROOT")
orbit_pivot = empty(orbit, "USTUDIO_ORBIT_PIVOT")
orbit_target = empty(orbit, "USTUDIO_ORBIT_TARGET")
orbit_pivot.parent = orbit_root
orbit_target.parent = orbit_root
camera(orbit, "USTUDIO_ORBIT_CAMERA", orbit_pivot, orbit_target)

dolly = collection_asset(
    "USTUDIO_RIG_DOLLY",
    "Rig dolly/reveal: caméra trackée vers TARGET, contrôles ROOT et CAMERA indépendants.",
    CAT_DOLLY,
    ["camera", "dolly", "reveal", "product", "reusable"],
)
dolly_root = empty(dolly, "USTUDIO_DOLLY_ROOT")
dolly_target = empty(dolly, "USTUDIO_DOLLY_TARGET")
dolly_target.parent = dolly_root
camera(dolly, "USTUDIO_DOLLY_CAMERA", dolly_root, dolly_target, location=(0, -5, 0), lens=50)

lighting = collection_asset(
    "USTUDIO_LIGHTS_PRODUCT_3PT",
    "Rig lumière produit trois points: key, fill et rim, parentés à un contrôle ROOT.",
    CAT_LIGHT,
    ["lighting", "studio", "product", "three-point"],
)
light_root = empty(lighting, "USTUDIO_LIGHT_ROOT")
for name, location, energy, size, color in (
    ("KEY", (4, -4, 5), 900, 4.0, (1.0, 0.82, 0.68)),
    ("FILL", (-4, -2, 2), 350, 5.0, (0.68, 0.82, 1.0)),
    ("RIM", (1, 4, 4), 700, 3.0, (1.0, 1.0, 1.0)),
):
    data = bpy.data.lights.new("USTUDIO_LIGHT_" + name + "_DATA", "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    obj = bpy.data.objects.new("USTUDIO_LIGHT_" + name, data)
    lighting.objects.link(obj)
    obj.parent = light_root
    obj.location = location
    constraint = obj.constraints.new("TRACK_TO")
    constraint.target = light_root
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"

assets = [
    {"name": orbit.name, "type": "collection", "catalog": "Rigs/Camera/Orbit", "usage": "Append (Reuse Data) puis déplacer ROOT"},
    {"name": dolly.name, "type": "collection", "catalog": "Rigs/Camera/Dolly", "usage": "Append (Reuse Data) puis animer CAMERA"},
    {"name": lighting.name, "type": "collection", "catalog": "Lighting/Studio/Product", "usage": "Append puis régler énergie, taille et couleur"},
]

bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT), compress=True, relative_remap=True)
MANIFEST.write_text(json.dumps({
    "schema_version": 1,
    "version": "1.0.0",
    "file": str(OUTPUT),
    "blender_version": bpy.app.version_string,
    "assets": assets,
}, ensure_ascii=False, indent=2), encoding="utf-8")
print("UNRECORDED_PRODUCTION_ASSETS=" + json.dumps({"file": str(OUTPUT), "assets": assets}, ensure_ascii=False))
