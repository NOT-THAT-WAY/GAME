"""Patch lisibilite : ajoute connecteurs cou/taille au mannequin (binding a la pose f1)."""
import bpy
from mathutils import Vector

TRIAL = "${BLENDER_AGENT_STUDIO_ROOT}/projects/kimi-k3-scene-trials/k3-pianoroll-slope-run-kimi-v001"
assert bpy.data.filepath == TRIAL + "/scene/trial.blend"

sc = bpy.context.scene
arm = bpy.data.objects["K3_RUNNER_RIG"]
coll = bpy.data.collections["K3_PIANOROLL_SLOPE_RUN_KIMI_V001_WORK"]
PEARL = bpy.data.materials["M_K3_RUNNER_PEARL"]
sc.frame_set(1)
bpy.context.view_layer.update()

ADDS = [
    ("K3_RUNNER_NECK",  "neck",  (0, 0, 0.296), (0.015, 0.015, 0.022)),
    ("K3_RUNNER_WAIST", "spine", (0, 0, 0.224), (0.042, 0.028, 0.030)),
    ("K3_RUNNER_HIP_L", "hips",  (-0.027, 0, 0.190), (0.018, 0.018, 0.018)),
    ("K3_RUNNER_HIP_R", "hips",  (0.027, 0, 0.190),  (0.018, 0.018, 0.018)),
]
AW = arm.matrix_world.copy()
for name, bone, loc, scale in ADDS:
    if name in bpy.data.objects:
        continue
    wloc = AW @ Vector(loc)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=1.0, location=wloc)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ob.data.materials.append(PEARL)
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    coll.objects.link(ob)
    ob.parent = arm
    ob.parent_type = "BONE"
    ob.parent_bone = bone
    m = ob.matrix_world.copy()
    ob.matrix_world = m
    for p in ob.data.polygons:
        p.use_smooth = True
    ob.select_set(False)

bpy.ops.wm.save_mainfile()
print("CONNECTORS_ADDED", len(ADDS))
