"""Create a tiny generic Blender fixture for repository smoke tests."""
from __future__ import annotations

import sys
from pathlib import Path

import bpy


def move_to_collection(obj, collection):
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    collection.objects.link(obj)


def main() -> None:
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(arguments) != 1:
        raise SystemExit("usage: blender --python create_blender_fixture.py -- OUTPUT.blend")
    output = Path(arguments[0]).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.name = "SMOKE_TEAM_STUDIO"
    scene.frame_start = 1
    scene.frame_end = 48
    scene.render.fps = 24
    scene.render.resolution_x = 320
    scene.render.resolution_y = 240
    scene.render.resolution_percentage = 25

    stage = bpy.data.collections.new("SMOKE_STAGE")
    scene.collection.children.link(stage)
    bpy.ops.mesh.primitive_cube_add(location=(-0.75, 0.0, 0.6), scale=(0.6, 0.6, 0.6))
    cube = bpy.context.object
    cube.name = "SMOKE_STAGE_CUBE"
    move_to_collection(cube, stage)
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.45, depth=1.2, location=(0.8, 0.0, 0.6))
    cylinder = bpy.context.object
    cylinder.name = "SMOKE_STAGE_CYLINDER"
    move_to_collection(cylinder, stage)

    material = bpy.data.materials.new("SMOKE_MATERIAL")
    material.diffuse_color = (0.18, 0.42, 0.8, 1.0)
    cube.data.materials.append(material)
    cylinder.data.materials.append(material)

    camera_data = bpy.data.cameras.new("SMOKE_CAMERA_DATA")
    camera = bpy.data.objects.new("SMOKE_CAMERA", camera_data)
    camera.location = (0.0, -7.0, 3.0)
    camera.rotation_euler = (1.17, 0.0, 0.0)
    scene.collection.objects.link(camera)
    scene.camera = camera

    light_data = bpy.data.lights.new("SMOKE_KEY_DATA", "AREA")
    light_data.energy = 700
    light_data.shape = "DISK"
    light_data.size = 4.0
    light = bpy.data.objects.new("SMOKE_KEY", light_data)
    light.location = (3.0, -4.0, 5.0)
    scene.collection.objects.link(light)

    # Export fixture: its collection is excluded and its parent dependency is intentionally unlinked.
    export_collection = bpy.data.collections.new("SMOKE_ASSET")
    scene.collection.children.link(export_collection)
    dependency = bpy.data.objects.new("SMOKE_DEPENDENCY", None)
    for index, x in enumerate((-0.55, 0.55), start=1):
        mesh = bpy.data.meshes.new(f"SMOKE_EXPORT_MESH_{index}")
        mesh.from_pydata(
            [(x - 0.35, -0.35, 0.0), (x + 0.35, -0.35, 0.0), (x, 0.35, 0.0), (x, 0.0, 0.8)],
            [],
            [(0, 1, 2), (0, 3, 1), (1, 3, 2), (2, 3, 0)],
        )
        mesh.update()
        obj = bpy.data.objects.new(f"SMOKE_EXPORT_PART_{index}", mesh)
        obj.parent = dependency
        export_collection.objects.link(obj)

    bpy.context.view_layer.layer_collection.children[export_collection.name].exclude = True

    bpy.ops.object.select_all(action="DESELECT")
    cube.select_set(True)
    cylinder.select_set(True)
    bpy.context.view_layer.objects.active = cube
    bpy.ops.wm.save_as_mainfile(filepath=str(output), check_existing=False)
    print(f"SMOKE_FIXTURE={output}")


if __name__ == "__main__":
    main()
