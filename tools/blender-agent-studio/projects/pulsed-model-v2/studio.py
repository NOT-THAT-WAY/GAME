"""Studio de gate : monde creme, lumieres, cameras — calque sur les videos de ref.

Les refs sont tournees sur un fond creme uni, cle douce venant du haut-avant-gauche,
rebond chaud a droite. On reproduit ca pour que les comparaisons A/B soient lisibles.
"""

import math

import bpy
from mathutils import Vector

CREAM = (0.945, 0.925, 0.878, 1.0)


def setup_world(lighting=0.8, backdrop=5.5):
    """Fond creme lumineux SANS inonder l'objet.

    Astuce Light Path : les rayons camera voient un creme fort (c'est l'image
    de fond), tous les autres rayons voient un creme faible (c'est l'ambiance).
    Sans ca, soit le fond est gris, soit l'interieur du boitier est delave.
    """
    world = bpy.data.worlds.get("PV2_world") or bpy.data.worlds.new("PV2_world")
    world.use_nodes = True
    nt = world.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_WORLD":
            nt.nodes.remove(n)
    out = nt.nodes["World Output"]

    bright = nt.nodes.new("ShaderNodeBackground"); bright.location = (-260, 140)
    bright.inputs["Color"].default_value = CREAM
    bright.inputs["Strength"].default_value = backdrop

    dim = nt.nodes.new("ShaderNodeBackground"); dim.location = (-260, -40)
    dim.inputs["Color"].default_value = CREAM
    dim.inputs["Strength"].default_value = lighting

    path = nt.nodes.new("ShaderNodeLightPath"); path.location = (-460, 320)
    mix = nt.nodes.new("ShaderNodeMixShader"); mix.location = (-60, 60)

    nt.links.new(path.outputs["Is Camera Ray"], mix.inputs["Fac"])
    nt.links.new(dim.outputs["Background"], mix.inputs[1])
    nt.links.new(bright.outputs["Background"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])

    bpy.context.scene.world = world
    return world


def setup_backdrop(size=400.0, floor_z=-13.0):
    """Sol shadow-catcher seul : le fond vient du monde (cf. setup_world).

    Le catcher se compose sur le creme vu par les rayons camera, donc on
    recupere l'ombre portee des refs sans plan de fond supplementaire.
    """
    m = bpy.data.materials.new("M_backdrop")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = CREAM
    b.inputs["Roughness"].default_value = 0.85

    bpy.ops.mesh.primitive_plane_add(size=size)
    floor = bpy.context.active_object
    floor.name = "PV2_floor"
    floor.location = (0, 0, floor_z)
    floor.data.materials.append(m)
    floor.is_shadow_catcher = True
    return floor


def _area(name, loc, rot, size, energy, color=(1, 1, 1)):
    data = bpy.data.lights.new(name, "AREA")
    data.shape = "RECTANGLE"
    data.size, data.size_y = size
    data.energy = energy
    data.color = color
    obj = bpy.data.objects.new(name, data)
    obj.location = loc
    obj.rotation_euler = rot
    bpy.context.scene.collection.objects.link(obj)
    return obj


def setup_lights():
    lights = [
        # cle douce haut-avant-gauche
        _area("PV2_key", (-22, -26, 20), (math.radians(52), 0, math.radians(-40)),
              (40, 30), 16000, (1.0, 0.97, 0.93)),
        # fill frontal large et faible, ouvre les ombres de la coque
        _area("PV2_fill", (18, -30, -4), (math.radians(84), 0, math.radians(30)),
              (50, 40), 4200, (0.95, 0.96, 1.0)),
        # rim arriere : fait chanter la translucidite violette
        _area("PV2_rim", (14, 26, 12), (math.radians(-58), 0, math.radians(150)),
              (26, 20), 11000, (1.0, 0.93, 0.85)),
    ]
    for lg in lights:
        lg.data.use_shadow = True
        # sinon les panneaux passent dans le champ et barrent l'image
        lg.visible_camera = False
    return lights


def _look_at(obj, target=Vector((0, 0, 0))):
    d = obj.location - target
    obj.rotation_euler = d.to_track_quat("Z", "Y").to_euler()


def add_camera(name, loc, lens=85.0, target=(0, 0, 0)):
    data = bpy.data.cameras.new(name)
    data.lens = lens
    obj = bpy.data.objects.new(name, data)
    obj.location = loc
    bpy.context.scene.collection.objects.link(obj)
    _look_at(obj, Vector(target))
    return obj


def add_ortho_camera(name, loc, scale, target=(0, 0, 0)):
    """Camera orthographique : indispensable pour comparer des PROPORTIONS.

    Un rendu en perspective compare a une reference orthographique introduit
    exactement le biais qu'on cherche a mesurer.
    """
    data = bpy.data.cameras.new(name)
    data.type = "ORTHO"
    data.ortho_scale = scale
    obj = bpy.data.objects.new(name, data)
    obj.location = loc
    bpy.context.scene.collection.objects.link(obj)
    _look_at(obj, Vector(target))
    return obj


def setup_cameras():
    """Cameras de gate, calquees sur les frames canon de la carte v3."""
    cams = {
        # face bien droite -> comparaison layout avec refB f_0003
        "gate_front": add_camera("gate_front", (0, -62, 0), lens=105),
        # 3/4 hero facon refB f_0001
        "gate_hero34": add_camera("gate_hero34", (-17, -46, 13), lens=90),
        # dos -> comparaison PCB / ports avec refB f_0027
        "gate_back": add_camera("gate_back", (0, 62, 0), lens=105),
        # profil gauche -> epaisseur, dome dorsal, depassement molette
        "gate_side": add_camera("gate_side", (-58, 4, 0), lens=105),
        # face ORTHOGRAPHIQUE -> comparaison de proportions sans biais
        "gate_ortho": add_ortho_camera("gate_ortho", (0, -60, 0), 16.6),
    }
    return cams


def setup_render(samples=96, res=(1280, 720), use_gpu=True):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 24
    scene.cycles.transmission_bounces = 20
    scene.cycles.transparent_max_bounces = 24
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Base Contrast"
    # Le cyclo emissif porte le fond ; l'expo neutre garde l'interieur sombre.
    scene.view_settings.exposure = 0.0

    if use_gpu:
        prefs = bpy.context.preferences.addons.get("cycles")
        if prefs:
            cprefs = prefs.preferences
            try:
                cprefs.compute_device_type = "METAL"
                cprefs.get_devices()
                for d in cprefs.devices:
                    d.use = True
                scene.cycles.device = "GPU"
            except Exception as exc:  # pragma: no cover
                print(f"  ! GPU indisponible, CPU : {exc}")
    return scene


def build_studio(samples=96, res=(1280, 720)):
    setup_world()
    setup_backdrop()
    setup_lights()
    cams = setup_cameras()
    setup_render(samples=samples, res=res)
    return cams
