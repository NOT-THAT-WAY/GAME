"""Export one clip to FBX from a saved checkpoint. Batch, isolated.

One FBX carries exactly one take, named after the Action. Blender's FBX writer
derives the take name from the SCENE name when `bake_anim_use_all_actions` is
False (`export_fbx_bin.py`), so the scene is renamed to the action before
writing. That is the only reason the scene name is touched, and nothing is saved
back.

Preflight assertions run before the write rather than after, so a scene carrying
a stray camera, light, helper or proxy fails loudly instead of shipping.

Usage:
  blender -b --factory-startup <checkpoint.blend> --python export_clip.py -- \
      <action> <out.fbx>
"""
import bpy
import sys

argv = sys.argv[sys.argv.index("--") + 1:]
ACTION, OUT_FBX = argv[0], argv[1]

EXPECTED_MESHES = {
    "BAS_PUNCH_Body", "BAS_PUNCH_Fist_L", "BAS_PUNCH_Fist_R",
    "BAS_PUNCH_Foot_L", "BAS_PUNCH_Foot_R", "BAS_PUNCH_Forearm_L",
    "BAS_PUNCH_Forearm_R", "BAS_PUNCH_UpperArm_L", "BAS_PUNCH_UpperArm_R",
}
EXPECTED_TRIS = 5664
EXPECTED_BONES = 10

scene = bpy.context.scene
rig = bpy.data.objects["BAS_PUNCH_Rig"]
action = bpy.data.actions[ACTION]

# -------------------------------------------------------------------- preflight
cameras = [o.name for o in bpy.data.objects if o.type == "CAMERA"]
lights = [o.name for o in bpy.data.objects if o.type == "LIGHT"]
meshes = {o.name for o in bpy.data.objects if o.type == "MESH"}
others = [o.name for o in bpy.data.objects
          if o.type not in ("MESH", "ARMATURE")]
assert not cameras, f"camera(s) dans la scene: {cameras}"
assert not lights, f"light(s) dans la scene: {lights}"
assert not others, f"objet(s) non exportables: {others}"
assert meshes == EXPECTED_MESHES, f"meshes inattendus: {meshes ^ EXPECTED_MESHES}"
assert len(rig.data.bones) == EXPECTED_BONES, f"os: {len(rig.data.bones)}"

total_tris = 0
max_influences = 0
for name in EXPECTED_MESHES:
    obj = bpy.data.objects[name]
    total_tris += sum(len(p.vertices) - 2 for p in obj.data.polygons)
    for vert in obj.data.vertices:
        count = sum(1 for g in vert.groups if g.weight > 1e-6)
        max_influences = max(max_influences, count)
assert total_tris == EXPECTED_TRIS, f"triangles: {total_tris}"
assert max_influences <= 4, f"influences par vertex: {max_influences}"

frame_start = int(round(action.frame_range[0]))
frame_end = int(round(action.frame_range[1]))

if rig.animation_data is None:
    rig.animation_data_create()
rig.animation_data.action = action
for slot in getattr(action, "slots", []):
    try:
        rig.animation_data.action_slot = slot
        break
    except Exception:
        pass

# Every other action must be off the exporter's radar: only the active one is
# baked, and the take inherits the scene name.
for other in bpy.data.actions:
    if other is not action:
        other.use_fake_user = True

scene.name = ACTION
scene.render.fps = 30
scene.render.fps_base = 1.0
scene.frame_start = frame_start
scene.frame_end = frame_end

for obj in bpy.data.objects:
    obj.select_set(obj.type in ("MESH", "ARMATURE"))
bpy.context.view_layer.objects.active = rig

bpy.ops.export_scene.fbx(
    filepath=OUT_FBX,
    use_selection=True,
    apply_unit_scale=True,
    global_scale=1.0,
    apply_scale_options="FBX_SCALE_NONE",
    axis_forward="-Z",
    axis_up="Y",
    object_types={"ARMATURE", "MESH"},
    use_mesh_modifiers=False,
    mesh_smooth_type="FACE",
    add_leaf_bones=False,
    primary_bone_axis="Y",
    secondary_bone_axis="X",
    armature_nodetype="NULL",
    bake_anim=True,
    bake_anim_use_all_bones=True,
    bake_anim_use_nla_strips=False,
    bake_anim_use_all_actions=False,
    bake_anim_force_startend_keying=True,
    bake_anim_step=1.0,
    bake_anim_simplify_factor=0.0,
    path_mode="COPY",
    embed_textures=False,
)

print(f"EXPORT_DONE {OUT_FBX}")
print(f"EXPORT_TAKE {ACTION} frames {frame_start}-{frame_end} "
      f"tris {total_tris} bones {len(rig.data.bones)} inf {max_influences}")
