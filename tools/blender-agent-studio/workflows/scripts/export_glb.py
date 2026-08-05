"""Export a versioned GLB and restore selection, active object and interaction mode."""
import bpy
import json
from pathlib import Path


P = globals().get("STUDIO_PARAMS", globals().get("UNRECORDED_PARAMS", {}))
output = Path(P["output_dir"])
output.mkdir(parents=True, exist_ok=True)
collection_name = str(P.get("collection", "")).strip()
scene = bpy.context.scene
view_layer = bpy.context.view_layer
previous_selected = list(bpy.context.selected_objects)
previous_active = view_layer.objects.active
previous_mode = previous_active.mode if previous_active else "OBJECT"
exported_objects = []
collection_objects = []
dependency_objects = []
layer_states = []
object_states = []
temporary_scene_link = False
temporary_object_links = []


def layer_path(root, target, ancestors=()):
    path = ancestors + (root,)
    if root.collection == target:
        return path
    for child in root.children:
        found = layer_path(child, target, path)
        if found:
            return found
    return None


def layer_subtree(root):
    yield root
    for child in root.children:
        yield from layer_subtree(child)

try:
    if previous_active and previous_mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    if collection_name:
        collection = bpy.data.collections.get(collection_name)
        if not collection:
            raise RuntimeError("Collection introuvable: " + collection_name)
        path = layer_path(view_layer.layer_collection, collection)
        if not path:
            scene.collection.children.link(collection)
            temporary_scene_link = True
            view_layer.update()
            path = layer_path(view_layer.layer_collection, collection)
        if not path:
            raise RuntimeError("Impossible de rendre la collection accessible dans le View Layer")
        affected_layers = list(path[:-1]) + list(layer_subtree(path[-1]))
        seen_layers = set()
        for layer in affected_layers:
            if id(layer) in seen_layers:
                continue
            seen_layers.add(id(layer))
            layer_states.append((layer, layer.exclude, layer.hide_viewport))
            layer.exclude = False
            layer.hide_viewport = False
        view_layer.update()
        collection_candidates = [
            obj for obj in list(collection.all_objects) if obj.type in {"MESH", "EMPTY", "ARMATURE"}
        ]
        candidate_ids = {id(obj) for obj in collection_candidates}
        seen_dependencies = set()
        dependencies = []
        for obj in collection_candidates:
            parent = obj.parent
            while parent:
                if id(parent) not in candidate_ids and id(parent) not in seen_dependencies:
                    seen_dependencies.add(id(parent))
                    dependencies.append(parent)
                parent = parent.parent
        for obj in dependencies:
            if obj.name not in view_layer.objects and obj.name not in scene.collection.objects:
                scene.collection.objects.link(obj)
                temporary_object_links.append(obj)
        view_layer.update()
        for obj in dependencies + collection_candidates:
            object_states.append((obj, obj.hide_select, obj.hide_viewport, obj.hide_get()))
            obj.hide_select = False
            obj.hide_viewport = False
            obj.hide_set(False)
            if obj.name not in view_layer.objects:
                raise RuntimeError(f"Objet absent du View Layer après activation: {obj.name}")
            obj.select_set(True)
            exported_objects.append(obj.name)
        collection_objects = [obj.name for obj in collection_candidates]
        dependency_objects = [obj.name for obj in dependencies]
        if not exported_objects:
            raise RuntimeError("La collection ne contient aucun objet exportable")
        view_layer.objects.active = next(
            (view_layer.objects[name] for name in exported_objects if bpy.data.objects[name].type in {"MESH", "ARMATURE"}),
            view_layer.objects[exported_objects[0]],
        )
    filepath = output / ((collection_name or "scene").lower().replace(" ", "-") + ".glb")
    kwargs = {
        "filepath": str(filepath),
        "export_format": "GLB",
        "use_selection": bool(collection_name),
        "export_apply": bool(P.get("apply_modifiers", True)),
    }
    bpy.ops.export_scene.gltf(**kwargs)
finally:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in previous_selected:
        if obj.name in view_layer.objects:
            obj.select_set(True)
    if previous_active and previous_active.name in view_layer.objects:
        view_layer.objects.active = previous_active
        if previous_mode != "OBJECT":
            try:
                bpy.ops.object.mode_set(mode=previous_mode)
            except Exception:
                pass
    for obj, hide_select, hide_viewport, hidden in object_states:
        obj.hide_select = hide_select
        obj.hide_viewport = hide_viewport
        obj.hide_set(hidden)
    for layer, excluded, hidden in reversed(layer_states):
        layer.exclude = excluded
        layer.hide_viewport = hidden
    for obj in reversed(temporary_object_links):
        if obj.name in scene.collection.objects:
            scene.collection.objects.unlink(obj)
    if temporary_scene_link and collection.name in scene.collection.children:
        scene.collection.children.unlink(collection)
    view_layer.update()

manifest = {
    "schema_version": 2,
    "file": str(filepath),
    "bytes": filepath.stat().st_size,
    "collection": collection_name or None,
    "objects": exported_objects,
    "collection_objects": collection_objects,
    "dependency_objects": dependency_objects,
    "source": bpy.data.filepath,
    "apply_modifiers": bool(P.get("apply_modifiers", True)),
    "temporary_state_restored": True,
    "reimport_validated": False,
    "saved": False,
}
(output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print("UNRECORDED_RESULT=" + json.dumps(manifest))
