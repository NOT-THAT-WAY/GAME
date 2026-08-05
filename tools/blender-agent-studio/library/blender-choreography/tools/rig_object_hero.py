import bpy, math, json
sc = bpy.context.scene
prefs = bpy.context.preferences.edit
old = prefs.keyframe_new_interpolation_type

# Pivot device : parent de tous les meshes pulsed_* (keep transform)
dp = bpy.data.objects.get("choreo_device_pivot")
if dp:
    if dp.animation_data: dp.animation_data_clear()
else:
    dp = bpy.data.objects.new("choreo_device_pivot", None)
    dp.location = (0, 0, 4.835)
    sc.collection.objects.link(dp)
    for o in sc.objects:
        if o.name.startswith("pulsed_") and o.parent is None:
            o.parent = dp
            o.matrix_parent_inverse = dp.matrix_world.inverted()

# Caméra fixe de face (on désactive l'anim caméra/pivot orbite)
for n in ("choreo_pivot", "choreo_cam_orbit"):
    o = bpy.data.objects[n]
    if o.animation_data: o.animation_data_clear()
bpy.data.objects["choreo_pivot"].rotation_euler = (0, 0, 0)
cam = bpy.data.objects["choreo_cam_orbit"]
cam.location = (0, -62, 4.0)

key = bpy.data.objects["key"]
if key.data.animation_data: key.data.animation_data_clear()
key.data.energy = 1400.0

sc.frame_start, sc.frame_end = 144, 144  # temp, reset après
sc.frame_start, sc.frame_end = 1, 144

prefs.keyframe_new_interpolation_type = 'BEZIER'
D = math.radians

# CHORÉGRAPHIE OBJET — 6 s :
# B1 (f1-20)   : repos face, léger float montant
# B2 (f20-50)  : le device S'INCLINE vers l'arrière (pitch -18°) et monte — présentation
# B3 (f50-100) : yaw 360 continu PENDANT que le pitch revient à 0 — hero turn vissé
# B4 (f100-126): roll latéral doux +8° puis retour — respiration
# B5 (f126-144): redescend à la pose de repos exacte
def k(fr, loc_z, rx, ry, rz):
    dp.location = (0, 0, loc_z)
    dp.rotation_euler = (D(rx), D(ry), D(rz))
    dp.keyframe_insert("location", frame=fr)
    dp.keyframe_insert("rotation_euler", frame=fr)

k(1,   4.835, 0,   0, 0)
k(20,  5.1,   0,   0, 0)
k(50,  5.9, -18,   0, 0)
k(100, 5.9,   0,   0, 360)
k(113, 5.6,   0,   8, 360)
k(126, 5.3,   0,  -4, 360)
k(144, 4.835, 0,   0, 360)

prefs.keyframe_new_interpolation_type = old
sc.camera = cam
print(json.dumps({"ok": True, "children": [o.name for o in dp.children]}))
