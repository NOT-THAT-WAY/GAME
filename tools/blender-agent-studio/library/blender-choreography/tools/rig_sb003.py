import bpy, json, math
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 144
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'

pivot = bpy.data.objects["choreo_pivot"]
cam   = bpy.data.objects["choreo_cam_orbit"]

for ob in (pivot, cam):
    ob.animation_data_clear()
cam.data.animation_data_clear()

def key(f, az, d, z, lens):
    sc.frame_set(f)
    pivot.rotation_euler = (0.0, 0.0, math.radians(az))
    pivot.keyframe_insert("rotation_euler", frame=f)
    cam.location = (0.0, -d, z)
    cam.keyframe_insert("location", frame=f)
    cam.data.lens = lens
    cam.data.keyframe_insert("lens", frame=f)

# sb-003 "arc-crane-vertigo" — UN geste continu (still->move->still), grammaire officielle:
# ARC (orbit) + CRANE (pedestal) + DOLLY-out + ZOOM-in => wrap-around montant,
# puis swing back en PULLBACK REVEAL (objet entier ~f108),
# et micro DOLLY-ZOOM au settle (taille constante: lens/dist fixe, la perspective respire).
key(1,   -15, 16.0, -3.5, 35)   # hold départ — macro 3/4 gauche bas
key(16,  -15, 16.0, -3.5, 35)
key(76,  -65, 30.0,  6.0, 70)   # arc+crane+dolly-out+zoom-in (monumental, partiel voulu)
key(126,   0, 58.0,  0.0, 52)   # swing back + descente + pullback (entier ~f108)
key(140,   0, 64.0,  0.0, 57)   # vertigo settle: 64/57 ~= 58/52 (taille ~constante)
key(144,   0, 64.0,  0.0, 57)   # hold final

for m in list(sc.timeline_markers):
    sc.timeline_markers.remove(m)
for name, f in [("HOLD", 1), ("ARC_CRANE", 16), ("SWINGBACK", 76), ("VERTIGO", 126), ("REST", 140)]:
    sc.timeline_markers.new(name, frame=f)

sc.frame_set(1)
print(json.dumps({"rig": "sb-003-arc-crane-vertigo", "keys": [1, 16, 76, 126, 140, 144]}))
