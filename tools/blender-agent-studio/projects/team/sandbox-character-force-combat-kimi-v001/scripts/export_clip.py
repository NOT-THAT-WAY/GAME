# Generic candidate FBX export for one Kimi pole clip.
#
# Contract: exactly one take named like the Action (take name = scene name),
# Bake Animation 30 fps step 1.0 Simplify 0, no leaf bones, only ARMATURE+MESH,
# no cameras/lights/helpers/proxy planes. Runs in batch on a SAVED checkpoint
# copy; never saves the .blend.
#
# Usage: blender -b <checkpoint.blend> --python export_clip.py -- <ACTION> <fstart> <fend> <out.fbx>

import bpy, sys, os, json

argv = sys.argv[sys.argv.index("--") + 1:]
ACTION, F_START, F_END, OUT_FBX = argv[0], int(argv[1]), int(argv[2]), argv[3]
sc = bpy.context.scene

objs = list(bpy.data.objects)
types = sorted({o.type for o in objs})
assert types == ["ARMATURE", "MESH"], "unexpected object types: %s" % types
assert len([o for o in objs if o.type == "ARMATURE"]) == 1
assert len([o for o in objs if o.type == "MESH"]) == 9, \
    "expected 9 meshes (helpers/proxies must be BAS_KIMI_ and absent or removed): %d" \
    % len([o for o in objs if o.type == "MESH"])
assert not bpy.data.cameras and not bpy.data.lights
for o in objs:
    assert not o.name.startswith("BAS_KIMI_"), "helper leaked into export: " + o.name
    assert not o.name.lower().startswith("cube"), o.name

arm = next(o for o in objs if o.type == "ARMATURE")
act = bpy.data.actions[ACTION]
if arm.animation_data is None:
    arm.animation_data_create()
arm.animation_data.action = act
try:
    arm.animation_data.action_slot = act.slots[0]
except Exception:
    pass

sc.render.fps = 30
sc.render.fps_base = 1.0
sc.frame_start, sc.frame_end = F_START, F_END
sc.name = ACTION  # single-take FBX: take name comes from the scene name

assert len(arm.data.bones) == 10
print("ACTIONS_IN_FILE " + json.dumps([a.name for a in bpy.data.actions]))
print("ACTIVE_ACTION " + arm.animation_data.action.name)
print("SCENE_NAME " + sc.name)

for o in objs:
    o.select_set(True)
bpy.context.view_layer.objects.active = arm
os.makedirs(os.path.dirname(OUT_FBX), exist_ok=True)

bpy.ops.export_scene.fbx(
    filepath=OUT_FBX,
    use_selection=False,
    use_visible=False,
    object_types={"ARMATURE", "MESH"},
    use_mesh_modifiers=False,
    mesh_smooth_type="FACE",
    use_tspace=False,
    use_custom_props=False,
    add_leaf_bones=False,
    primary_bone_axis="Y",
    secondary_bone_axis="X",
    use_armature_deform_only=False,
    armature_nodetype="NULL",
    bake_anim=True,
    bake_anim_use_all_bones=True,
    bake_anim_use_nla_strips=False,
    bake_anim_use_all_actions=False,
    bake_anim_force_startend_keying=True,
    bake_anim_step=1.0,
    bake_anim_simplify_factor=0.0,
    apply_unit_scale=True,
    global_scale=1.0,
    apply_scale_options="FBX_SCALE_NONE",
    use_space_transform=True,
    bake_space_transform=False,
    axis_forward="-Z",
    axis_up="Y",
    path_mode="AUTO",
)
print("FBX_EXPORTED " + OUT_FBX + " bytes=" + str(os.path.getsize(OUT_FBX)))
