# Export the SB_Idle candidate FBX for Unity.
#
# Contract: Bake Animation on, 30 fps, step 1.0, Simplify 0.0, Unity axes
# (-Z forward / Y up), no leaf bones (they would add *_end bones and change the
# skeleton Unity sees), only the ACTIVE action (the Punch placeholder must not
# be re-exported), only ARMATURE and MESH objects.
#
# The single-take name is taken from the scene name by Blender's exporter, which
# is why the master .blend names its scene SB_Idle.
#
# Usage: blender -b <master.blend> --python export_sb_idle_fbx.py -- <out.fbx>

import bpy, sys, os, json

OUT_FBX = sys.argv[sys.argv.index("--") + 1:][0]
sc = bpy.context.scene

# ---- preflight assertions: nothing unexpected may leave this file ----
objs = list(bpy.data.objects)
types = sorted({o.type for o in objs})
assert types == ["ARMATURE", "MESH"], "unexpected object types in master: %s" % types
assert len([o for o in objs if o.type == "ARMATURE"]) == 1
assert len([o for o in objs if o.type == "MESH"]) == 9
assert not bpy.data.cameras, "camera datablock present"
assert not bpy.data.lights, "light datablock present"
for o in objs:
    assert not o.name.lower().startswith("cube"), o.name

arm = next(o for o in objs if o.type == "ARMATURE")
act = arm.animation_data.action
assert act.name == "SB_Idle", "active action is %r, expected SB_Idle" % act.name
assert sc.render.fps == 30 and sc.render.fps_base == 1.0
assert sc.frame_start == 1 and sc.frame_end == 60
assert len(arm.data.bones) == 10

# Only SB_Idle may be exported. The Punch placeholder stays in the .blend
# (fake user, contents untouched) but is not the active action, and
# bake_anim_use_all_actions=False exports the active action only.
print("ACTIONS_IN_FILE " + json.dumps([a.name for a in bpy.data.actions]))
print("ACTIVE_ACTION " + act.name)
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
    use_mesh_modifiers=False,          # keep raw mesh + skin deformer
    mesh_smooth_type="FACE",
    use_tspace=False,
    use_custom_props=False,
    add_leaf_bones=False,              # no *_end bones: skeleton stays 10 bones
    primary_bone_axis="Y",
    secondary_bone_axis="X",
    use_armature_deform_only=False,
    armature_nodetype="NULL",
    bake_anim=True,                    # Bake Animation
    bake_anim_use_all_bones=True,
    bake_anim_use_nla_strips=False,
    bake_anim_use_all_actions=False,   # active action only -> no Punch
    bake_anim_force_startend_keying=True,
    bake_anim_step=1.0,
    bake_anim_simplify_factor=0.0,     # Simplify 0
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
