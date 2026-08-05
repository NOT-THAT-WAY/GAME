import bpy, json, math
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 144
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'

pivot = bpy.data.objects["choreo_pivot"]
cam   = bpy.data.objects["choreo_cam_orbit"]

# reset ancienne animation (sb-001) — le rig sb-001 reste rejouable via tools/rig_arc270-style scripts
for ob in (pivot, cam):
    ob.animation_data_clear()
cam.data.animation_data_clear()
pivot.rotation_euler = (0.0, 0.0, 0.0)

def key_cam(f, d, z, lens):
    sc.frame_set(f)
    cam.location = (0.0, -d, z)
    cam.keyframe_insert("location", frame=f)
    cam.data.lens = lens
    cam.data.keyframe_insert("lens", frame=f)

def key_az(f, deg):
    sc.frame_set(f)
    pivot.rotation_euler = (0.0, 0.0, math.radians(deg))
    pivot.keyframe_insert("rotation_euler", frame=f)

# sb-002 "lowrise-orbit" — mouvement continu validé par Sliz sur le run 2 :
# contre-plongée rasante -> la caméra TOURNE (3/4 gauche) en remontant -> retour frontal
# en s'éloignant jusqu'à l'objet ENTIER dans le cadre 9:16 (>=55 BU @70mm) -> repos.
# B1 hold contre-plongée (signature aimée)
key_az(1, 0);    key_cam(1, 13.0, -4.8, 28)
key_az(20, 0);   key_cam(20, 13.0, -4.8, 28)
# B2 turn + rise (azimut file vers -45, focale 28->70, ca s'eloigne)
key_az(64, -45); key_cam(64, 32.0, -1.0, 70)
# B3 le retour: azimut revient a 0 pendant le pull-back (objet entier ~f110)
key_az(120, 0);  key_cam(120, 58.0, 0.0, 70)
# B4 settle + hold
key_az(144, 0);  key_cam(144, 66.0, 0.0, 70)

# marqueurs
for m in list(sc.timeline_markers):
    sc.timeline_markers.remove(m)
for name, f in [("B1_LOW", 1), ("B2_TURN", 64), ("B3_RETURN", 120), ("B4_REST", 144)]:
    sc.timeline_markers.new(name, frame=f)

sc.frame_set(1)
print(json.dumps({"rig": "sb-002-lowrise-orbit", "frames": [1, 20, 64, 120, 144]}))
