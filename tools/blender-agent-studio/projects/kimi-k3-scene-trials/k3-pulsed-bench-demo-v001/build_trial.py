"""k3-pulsed-bench-demo-v001 — construction de la scene d'essai.

Contraintes appliquees (AGENTS.md + BLENDER_RULES_PRIORITY.md) :
  P0 - la source projects/pulsed-model-v2/scene/pulsed_v2.blend est APPEND,
       jamais ouverte ni ecrasee ; la scene ne se sauvegarde que dans
       scene/trial.blend.
  P0 - pas de levitation : Pulsed REPOSE sur un plan de travail. La hauteur du
       root est calculee depuis la geometrie evaluee, pas devinee.
  P0 - unites : le modele est en BU ou 1 BU = 1 cm. Le root porte un scale
       0.01 pour que les coordonnees monde soient des METRES, comme les seuils.
  P1 - camera en 4 poses (pose / anticipation opposee / travel / recovery),
       CAMERA, TARGET et FOCUS separes, target en retard de quelques frames.
  P1 - lumiere et monde construits par workflows/scripts/studio_lighting.py
       en preset drumboiii-layered (rig USTUDIO_LIGHTING_* + ciel separe de
       l'eclairage par Is Camera Ray).

  blender -b --python build_trial.py
"""

import json
import math
import os
import sys

import bpy
from mathutils import Vector

TRIAL_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(TRIAL_DIR, "..", "..", ".."))
SOURCE_BLEND = os.path.join(REPO, "projects", "pulsed-model-v2", "scene", "pulsed_v2.blend")
OUT_BLEND = os.path.join(TRIAL_DIR, "scene", "trial.blend")

TRIAL = "K3_PULSED_BENCH_V001"
FPS, F_END = 24, 144            # 6,0 s exactement
BU = 0.01                       # 1 BU du modele = 1 cm
BENCH_TOP = 0.0                 # plan de travail a z = 0


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def append_model():
    """Append la collection PULSED_V2 sans jamais ouvrir la source."""
    before = set(bpy.data.collections.keys())
    bpy.ops.wm.append(
        filepath=os.path.join(SOURCE_BLEND, "Collection", "PULSED_V2"),
        directory=os.path.join(SOURCE_BLEND, "Collection"),
        filename="PULSED_V2",
    )
    new = set(bpy.data.collections.keys()) - before
    name = next((n for n in new if n.startswith("PULSED_V2")), None)
    if name is None:
        raise RuntimeError("append de PULSED_V2 echoue")
    return bpy.data.collections[name]


def lowest_z(objs, deps):
    """Point le plus bas de la geometrie EVALUEE (modifiers compris)."""
    low = None
    for o in objs:
        if o.type != "MESH" or o.hide_render or o.hide_viewport:
            continue
        ev = o.evaluated_get(deps)
        me = ev.to_mesh()
        if me is None:
            continue
        mw = ev.matrix_world
        for v in me.vertices:
            z = (mw @ v.co).z
            low = z if low is None or z < low else low
        ev.to_mesh_clear()
    return low


def build_bench(root_col):
    """Plan de travail : c'est LE support, il doit exister avant l'objet."""
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    bench = bpy.context.active_object
    bench.name = f"{TRIAL}_BENCH"
    bench.scale = (1.6, 1.1, 0.06)
    bpy.ops.object.transform_apply(scale=True)
    bench.location = (0.0, 0.10, BENCH_TOP - 0.03)

    m = bpy.data.materials.new(f"{TRIAL}_M_bench")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.052, 0.050, 0.058, 1.0)
    b.inputs["Roughness"].default_value = 0.42
    bench.data.materials.append(m)

    bev = bench.modifiers.new("Bevel", "BEVEL")
    bev.width = 0.004
    bev.segments = 3
    for c in list(bench.users_collection):
        c.objects.unlink(bench)
    root_col.objects.link(bench)
    return bench


def place_model(model_col, root_col):
    """Pose Pulsed a plat, face vers le haut, en appui reel sur le plan."""
    root = bpy.data.objects.new(f"{TRIAL}_ROOT", None)
    root.empty_display_size = 0.05
    root_col.objects.link(root)

    for o in list(model_col.objects) + [o for c in model_col.children_recursive
                                        for o in c.objects]:
        if o.parent is None:
            o.parent = root
            o.matrix_parent_inverse = root.matrix_world.inverted()

    # face du modele = -Y ; on la tourne vers +Z pour la poser a plat
    root.rotation_euler = (math.radians(-90.0), 0.0, 0.0)
    root.scale = (BU, BU, BU)
    root.location = (0.0, 0.0, 0.05)
    bpy.context.view_layer.update()

    deps = bpy.context.evaluated_depsgraph_get()
    objs = [o for o in bpy.data.objects if o.type == "MESH"
            and o.name.startswith("PV2_")]
    low = lowest_z(objs, deps)
    if low is None:
        raise RuntimeError("geometrie du modele introuvable")
    # appui exact : le point le plus bas touche le plan, sans penetration
    root.location.z += (BENCH_TOP - low)
    bpy.context.view_layer.update()
    return root


def build_camera(root_col):
    """CAMERA / TARGET / FOCUS separes — regle Drumboiii."""
    target = bpy.data.objects.new(f"{TRIAL}_TARGET", None)
    target.empty_display_size = 0.02
    target.location = (0.0, 0.0, 0.014)
    root_col.objects.link(target)

    focus = bpy.data.objects.new(f"{TRIAL}_FOCUS", None)
    focus.empty_display_size = 0.015
    focus.location = (0.0, -0.01, 0.02)
    root_col.objects.link(focus)

    data = bpy.data.cameras.new(f"{TRIAL}_CAMERA")
    data.lens = 58.0
    data.dof.use_dof = True
    data.dof.focus_object = focus
    data.dof.aperture_fstop = 4.0
    cam = bpy.data.objects.new(f"{TRIAL}_CAMERA", data)
    root_col.objects.link(cam)

    track = cam.constraints.new("TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"
    return cam, target, focus


# --- Animation --------------------------------------------------------------

def key(obj, path, frame, value, index=-1, interp="BEZIER"):
    if index >= 0:
        getattr(obj, path)[index] = value
    else:
        setattr(obj, path, value)
    obj.keyframe_insert(data_path=path, frame=frame, index=index)
    set_interp(obj, path, frame, interp)


def fcurves(action):
    if hasattr(action, "fcurves"):
        return action.fcurves
    out = []
    for layer in getattr(action, "layers", []):
        for strip in getattr(layer, "strips", []):
            for cb in getattr(strip, "channelbags", []):
                out.extend(cb.fcurves)
    return out


def set_interp(owner, path, frame, interp):
    holder = getattr(owner, "id_data", owner)
    ad = getattr(holder, "animation_data", None)
    if not ad or not ad.action:
        return
    for fc in fcurves(ad.action):
        if path not in fc.data_path:
            continue
        for kp in fc.keyframe_points:
            if abs(kp.co.x - frame) < 0.5:
                kp.interpolation = interp
                kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"


def animate_camera(cam, target):
    """4 poses : pose -> anticipation OPPOSEE -> travel -> recovery."""
    # Hauteurs relevees apres la 1re passe de preuves : a z=0.074 la camera
    # passait a 74 mm du plateau, sous le seuil contractuel de 80 mm. On
    # remonte la trajectoire — on n'assouplit JAMAIS le seuil apres coup.
    poses = [
        (1,   (0.020, -0.360, 0.128)),   # K1 pose : bas mais degage
        (26,  (-0.055, -0.395, 0.116)),  # K2 anticipation : recule a l'oppose
        (120, (0.170, -0.298, 0.286)),   # K3 travel : arc principal
        (144, (0.140, -0.312, 0.258)),   # K4 recovery : absorbe et s'arrete
    ]
    for f, loc in poses:
        cam.location = loc
        cam.keyframe_insert(data_path="location", frame=f)
    for fc in fcurves(cam.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"

    # le target reagit avec 4 frames de retard, puis s'arrete : jamais de derive
    for f, y in ((1, 0.0), (30, 0.0), (124, 0.012), (144, 0.010)):
        key(target, "location", f, y, index=1)


def gn_sockets(mod):
    out = {}
    for item in mod.node_group.interface.items_tree:
        if getattr(item, "in_out", None) == "INPUT" and item.item_type == "SOCKET":
            out[item.name] = item.identifier
    return out


def key_gn(mod, ident, frame, value, interp="BEZIER"):
    mod[ident] = value
    path = f'["{ident}"]'
    mod.keyframe_insert(data_path=path, frame=frame)
    set_interp(mod, path, frame, interp)


def key_visible(obj, frame, visible):
    """UNIQUEMENT hide_render.

    Keyframer hide_viewport sort l'objet du depsgraph : sa matrice evaluee
    devient inutilisable et il pollue toute mesure geometrique. hide_render
    suffit pour le rendu.
    """
    obj.hide_render = not visible
    obj.keyframe_insert(data_path="hide_render", frame=frame)
    set_interp(obj, "hide_render", frame, "CONSTANT")


def O(name):
    o = bpy.data.objects.get(name)
    if o is None:
        raise KeyError(name)
    return o


def animate_controls():
    """Courses declarees au contrat d'objet. Amplitudes en BU (espace local)."""
    # molette : anticipation courte puis rotation continue
    w = O("PV2_wheel")
    w.rotation_mode = "XYZ"
    for f, rad in ((1, 0.0), (18, 0.0), (24, -0.12), (60, 7.4), (66, 7.7),
                   (144, 7.7)):
        key(w, "rotation_euler", f, rad, index=0)

    # slider de gain : course prismatique verticale, bornee par la fente
    knob = O("PV2_gain_knob")
    z0 = knob.location.z
    for f, z in ((1, z0), (60, z0), (66, z0 - 0.10),
                 (92, z0 + 1.06), (96, z0 + 1.00), (144, z0 + 1.00)):
        key(knob, "location", f, z, index=2)

    # slider horizontal : course prismatique, jamais jusqu'a la butee
    cap = O("PV2_hslider_cap")
    x0 = cap.location.x
    for f, x in ((1, x0), (96, x0), (101, x0 - 0.09),
                 (122, x0 + 1.62), (126, x0 + 1.55), (144, x0 + 1.55)):
        key(cap, "location", f, x, index=0)

    # D-pad : rotation autour de Z local, dans les limites du contrat
    d = O("PV2_dpad")
    d.rotation_mode = "XYZ"
    for f, deg in ((1, 0.0), (126, 0.0), (131, 6.5), (137, 6.5), (142, 0.0),
                   (144, 0.0)):
        key(d, "rotation_euler", f, math.radians(deg), index=2)
    # Reparentage QUI PRESERVE LA POSE MONDE. Poser seulement
    # matrix_parent_inverse = d.matrix_world.inverted() annule la chaine et
    # renvoie l'objet a ses coordonnees locales lues comme des metres.
    for name in ("up", "down", "left", "right"):
        a = bpy.data.objects.get(f"PV2_dpad_arrow_{name}")
        if a is None or (a.parent and a.parent.name == d.name):
            continue
        world = a.matrix_world.copy()
        a.parent = d
        a.matrix_parent_inverse = d.matrix_world.inverted()
        a.matrix_world = world


def animate_screen():
    """L'ecran repond aux memes valeurs que les controles."""
    wave = O("PV2_ui_wave")
    mod = wave.modifiers["Wave"]
    s = gn_sockets(mod)
    key_gn(mod, s["Phase"], 1, 0.0, interp="LINEAR")
    key_gn(mod, s["Phase"], F_END, -10.5 * math.pi, interp="LINEAR")
    for f, v in ((1, 1.35), (18, 1.35), (66, 3.05), (144, 3.05)):
        key_gn(mod, s["Freq"], f, v)
    for f, v in ((1, 0.32), (60, 0.32), (96, 0.84), (126, 0.98),
                 (137, 0.66), (144, 0.90)):
        key_gn(mod, s["Amp"], f, v)

    for i in range(8):
        bar = O(f"PV2_ui_bar{i}")
        on = 60 + int(36 * (i + 1) / 8.0)
        key_visible(bar, 1, i < 2)
        key_visible(bar, 59, i < 2)
        key_visible(bar, on, True)


# --- Assemblage -------------------------------------------------------------

def run_studio_lighting(model_col):
    script = os.path.join(REPO, "workflows", "scripts", "studio_lighting.py")
    g = {
        "__name__": "__main__",
        "UNRECORDED_PARAMS": {
            "preset": "drumboiii-layered",
            "target_collection": model_col.name,
            "world_strength": 0.7,
            "visible_world_strength": 0.30,
            # Les watts du tutoriel (1400/440/170/220) valent pour un sujet de
            # plusieurs metres. Ici le rayon est borne au plancher de 0,5 m du
            # script, donc les lampes sont ~1,7 m d'un objet de 16 cm : il faut
            # ramener les RATIOS a l'echelle, pas recopier les constantes.
            "intensity": 0.28,
            "configure_world": True,
            "mute_existing_lights": True,
            "view_transform": "AgX",
            "render_engine": "CYCLES",
        },
    }
    with open(script) as fh:
        exec(compile(fh.read(), script, "exec"), g)
    return bpy.data.collections.get("USTUDIO_LIGHTING")


def main():
    clear()
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.frame_start, scene.frame_end = 1, F_END
    scene.render.fps = FPS
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"

    root_col = bpy.data.collections.new(TRIAL)
    scene.collection.children.link(root_col)

    model_col = append_model()
    # tout vit sous une collection prefixee K3_ (regle de nommage AGENTS.md)
    scene.collection.children.unlink(model_col)
    root_col.children.link(model_col)

    build_bench(root_col)
    place_model(model_col, root_col)
    cam, target, focus = build_camera(root_col)
    scene.camera = cam

    animate_camera(cam, target)
    animate_controls()
    animate_screen()

    rig = run_studio_lighting(model_col)
    if rig and rig.name in {c.name for c in scene.collection.children}:
        scene.collection.children.unlink(rig)
        root_col.children.link(rig)

    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 12
    scene.cycles.transmission_bounces = 8
    scene.cycles.transparent_max_bounces = 8

    deps = bpy.context.evaluated_depsgraph_get()
    objs = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("PV2_")]
    low = lowest_z(objs, deps)
    print(f"[appui] point le plus bas du sujet = {low * 1000:.3f} mm "
          f"(plan a {BENCH_TOP * 1000:.3f} mm)")
    print(f"[rig] {sorted(o.name for o in rig.objects if o.type == 'LIGHT') if rig else 'ABSENT'}")

    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    print(f"[ok] -> {OUT_BLEND}")


if __name__ == "__main__":
    main()
