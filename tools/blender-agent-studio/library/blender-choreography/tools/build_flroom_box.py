"""build_flroom_box.py — scène FLROOM : boîte-room clay (proportions plate fond-flroom-001)
+ copie du Pulsed en lévitation au centre. Zéro texture, zéro props : la matière sera
fournie par la vidéo/scène ref au v2v (couche SCÈNE, use-case C″).

Proportions mesurées sur refs/04_plate_start_frame_room.png :
interieur W:H ~ 1.87 (700x375 px), coque épaisse ~9% de W, front ouvert, boîte posée sur void.
"""
import bpy, bmesh, json, math

# ---------- 0. reset : rebuild idempotent ----------
if "FLROOM" in bpy.data.scenes:
    sc_old = bpy.data.scenes["FLROOM"]
    for ob in list(sc_old.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.scenes.remove(sc_old)

src = bpy.data.scenes["Scene"]
sc = bpy.data.scenes.new("FLROOM")
bpy.context.window.scene = sc

# ---------- 1. dimensions ----------
W, H, D = 48.0, 25.0, 30.0        # intérieur (X, Z, Y) — W:H = 1.92
T = 3.5                            # épaisseur coque
BEV = 2.2                          # rayon arrondi coque

def link(ob):
    sc.collection.objects.link(ob)
    return ob

def cube(name, sx, sy, sz, loc):
    # dims cuites dans le mesh (scale objet = 1) : les modifiers (bevel) travaillent
    # en espace local — un ob.scale fausserait le width du bevel
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()
    ob = bpy.data.objects.new(name, mesh)
    ob.location = loc
    return link(ob)

# ---------- 2. coque : cube arrondi MOINS cutter (front ouvert) ----------
# intérieur : sol z=0, plafond z=H ; face interne fond y=+D/2 ; ouverture y=-D/2
outer = cube("flroom_shell", W + 2*T, D + 2*T, H + 2*T, (0, 0, H/2))
bev = outer.modifiers.new("bevel", 'BEVEL')
bev.width = BEV
bev.segments = 5
bev.limit_method = 'ANGLE'

cutter = cube("flroom_cutter", W, D + T + 8, H, (0, -(T + 8)/2, H/2))
boo = outer.modifiers.new("open_front", 'BOOLEAN')
boo.operation = 'DIFFERENCE'
boo.object = cutter
cutter.hide_render = True
cutter.display_type = 'WIRE'
cutter.hide_set(True)

mat_shell = bpy.data.materials.get("flroom_clay") or bpy.data.materials.new("flroom_clay")
mat_shell.use_nodes = True
bsdf = mat_shell.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.62, 0.60, 0.57, 1.0)  # gris chaud neutre
bsdf.inputs["Roughness"].default_value = 0.65
outer.data.materials.append(mat_shell)

# ---------- 3. sol void (shadow catch, near-black) ----------
ground = cube("void_ground", 400, 400, 0.2, (0, 0, -T - 0.1))
mat_void = bpy.data.materials.get("void_dark") or bpy.data.materials.new("void_dark")
mat_void.use_nodes = True
vb = mat_void.node_tree.nodes["Principled BSDF"]
vb.inputs["Base Color"].default_value = (0.015, 0.016, 0.02, 1.0)
vb.inputs["Roughness"].default_value = 0.9
ground.data.materials.append(mat_void)

# ---------- 4. Pulsed : copie liée (mêmes meshes) au centre, en lévitation ----------
pivot = bpy.data.objects.new("flroom_device_pivot", None)
pivot.location = (0, -8, H/2 - 1.0)  # AVANCÉ vers l'ouverture (gate Sliz : « proche de sortir, pas au fond »)
pivot.scale = (1.3, 1.3, 1.3)        # device ~21 BU ≈ 43% de W : central avec de l'air tout autour
link(pivot)

src_pivot = bpy.data.objects["choreo_device_pivot"]
copied = []
for ch in src_pivot.children:
    if ch.type != 'MESH':
        continue
    dup = ch.copy()               # partage le mesh data + matériaux
    dup.name = ch.name + "_flroom"
    dup.animation_data_clear()
    dup.parent = pivot
    dup.matrix_parent_inverse.identity()
    dup.location = (0, 0, 0)
    link(dup)
    copied.append(dup.name)

# ---------- 5. lumières (soft, AUCUN spot du haut) ----------
def area(name, loc, rot, size, energy):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.size = size
    ob = bpy.data.objects.new(name, data)
    ob.location = loc
    ob.rotation_euler = rot
    return link(ob)

# key frontal large (comme une softbox face à l'ouverture, léger offset gauche)
area("fl_key", (-18, -55, 22), (math.radians(65), 0, math.radians(-15)), 45, 9000)
# fill frontal droit, plus faible
area("fl_fill", (22, -50, 12), (math.radians(75), 0, math.radians(18)), 35, 3500)
# douce lueur interne basse (déboucher l'intérieur sans cône)
area("fl_bounce", (0, 0, 1.2), (0, 0, 0), 30, 1400)
# softbox frontale à travers l'ouverture, braquée sur le device (lisibilité du héros)
area("fl_device_key", (0, -26, 13), (math.radians(88), 0, 0), 22, 2600)

world = bpy.data.worlds.get("flroom_world") or bpy.data.worlds.new("flroom_world")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.008, 0.009, 0.012, 1.0)
sc.world = world

# ---------- 6. caméras (cible = centre volume) ----------
target = bpy.data.objects.new("flroom_target", None)
target.location = (0, 0, H/2 - 1.0)
link(target)

def camera(name, loc, lens):
    data = bpy.data.cameras.new(name)
    data.lens = lens
    ob = bpy.data.objects.new(name, data)
    ob.location = loc
    tc = ob.constraints.new('TRACK_TO')
    tc.target = target
    tc.track_axis = 'TRACK_NEGATIVE_Z'
    tc.up_axis = 'UP_Y'
    return link(ob)

cam_front = camera("flroom_cam_front", (0, -140, 14), 50)  # cadrage plate (boîte entière ~65% du cadre)
cam_34    = camera("flroom_cam_34", (-80, -110, 42), 50)   # 3/4 gauche léger haut
cam_in    = camera("flroom_cam_inside", (0, -36, 13.5), 30)  # à l'ouverture, device héros
sc.camera = cam_front

# ---------- 7. réglages scène ----------
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
sc.render.fps = 24
sc.frame_start, sc.frame_end = 1, 240
eng = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
sc.render.engine = eng

print(json.dumps({"scene": "FLROOM", "interior_WHD": [W, H, D], "shell_T": T,
                  "device_parts": len(copied), "engine": eng}))
