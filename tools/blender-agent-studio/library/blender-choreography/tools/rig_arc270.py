import bpy, math, json
sc = bpy.context.scene
prefs = bpy.context.preferences.edit
old = prefs.keyframe_new_interpolation_type
D = math.radians

# Reset : device au repos, anims précédentes purgées
dp = bpy.data.objects["choreo_device_pivot"]
if dp.animation_data: dp.animation_data_clear()
dp.location = (0, 0, 4.835); dp.rotation_euler = (0, 0, 0)

pivot = bpy.data.objects["choreo_pivot"]
cam = bpy.data.objects["choreo_cam_orbit"]
for o in (pivot, cam):
    if o.animation_data: o.animation_data_clear()
key = bpy.data.objects["key"]
if key.data.animation_data: key.data.animation_data_clear()
key.data.energy = 1400.0

# 5 s STRICT (pattern : 4s = saccade, 6s+ = stagne) — 120 f @ 24 fps
sc.frame_start, sc.frame_end = 1, 120

# Caméra : arc horizontal pur, axe vertical, ZERO push-in (anti-combinaison du pattern)
# élévation quasi nulle (<2°) : rel z 2.0 sur distance 62
cam.location = (0, -62, 2.0)
cam.data.lens = 70

prefs.keyframe_new_interpolation_type = 'BEZIER'

# BEATS (θ = rotation Z du pivot orbite ; négatif = la caméra part vers la 3/4 GAUCHE)
# Distances angulaires ∝ speed×durée : b2 90×1.5, b3 80×1.0, b4 130×1.0 → 141/83/136°
# B1 (f1-24)    HOLD front, θ=0                          — "breath held"
# B2 (f24-60)   θ 0 → −141   (front → 3qL, contemplatif)
# B3 (f60-84)   θ −141 → −224 (back glimpse, pace settles)
# B4 (f84-108)  θ −224 → −360 (retour rapide via 3qR, glow émerge)
# B5 (f108-120) θ −360 ≡ front, HELD STILL
for f, deg in ((1,0),(24,0),(60,-141),(84,-224),(108,-360),(120,-360)):
    pivot.rotation_euler = (0, 0, D(deg))
    pivot.keyframe_insert("rotation_euler", frame=f)

# GLOW PCB : dormant jusqu'au back glimpse, EMERGE beat 4, FULL BLOOM beat 5
pbsdf = bpy.data.materials["M_pcb"].node_tree.nodes["Principled BSDF"]
es = pbsdf.inputs["Emission Strength"]
for f, v in ((1,0.08),(84,0.08),(100,0.9),(108,1.6),(120,1.6)):
    es.default_value = v
    es.keyframe_insert("default_value", frame=f)

prefs.keyframe_new_interpolation_type = old
sc.camera = cam
print(json.dumps({"ok": True}))
