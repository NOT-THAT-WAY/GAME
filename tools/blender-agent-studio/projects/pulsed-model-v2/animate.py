"""Pulsed v2 — animation « demo fonctionnelle ».

L'objet reste cadre ; ce sont les CONTROLES qui jouent, et l'ecran repond
reellement (la waveform est pilotee par les memes valeurs que la molette et
le slider de gain, pas par une texture pre-calculee).

  blender -b scene/pulsed_v2.blend --python animate.py
"""

import math
import os
import sys

import bpy

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

import studio          # noqa: E402
import internals as I  # noqa: E402

OUT_BLEND = os.path.join(ROOT, "scene", "pulsed_v2_anim.blend")

FPS = 24
F_END = 192                     # 8 s


# --- Utilitaires de keyframing ---------------------------------------------

def key(obj, data_path, frame, value=None, index=-1, interp="BEZIER"):
    if value is not None:
        if index >= 0:
            getattr(obj, data_path)[index] = value
        else:
            setattr(obj, data_path, value)
    obj.keyframe_insert(data_path=data_path, frame=frame, index=index)
    _set_interp(obj, data_path, frame, interp)


def _set_interp(owner, data_path, frame, interp):
    # Pour un modificateur, l'action vit sur l'OBJET proprietaire, pas sur le
    # modificateur — et le data_path y devient modifiers["Wave"]["Socket_2"].
    holder = getattr(owner, "id_data", owner)
    ad = getattr(holder, "animation_data", None)
    if not ad or not ad.action:
        return
    for fc in _fcurves(ad.action):
        if data_path not in fc.data_path:
            continue
        for kp in fc.keyframe_points:
            if abs(kp.co.x - frame) < 0.5:
                kp.interpolation = interp


def _fcurves(action):
    """Blender 5.x : les fcurves vivent dans les channelbags des slots."""
    if hasattr(action, "fcurves"):
        return action.fcurves
    out = []
    for layer in getattr(action, "layers", []):
        for strip in getattr(layer, "strips", []):
            for cb in getattr(strip, "channelbags", []):
                out.extend(cb.fcurves)
    return out


def gn_sockets(mod):
    """{nom lisible: identifiant} des entrees d'un modificateur Geometry Nodes."""
    out = {}
    for item in mod.node_group.interface.items_tree:
        if getattr(item, "in_out", None) == "INPUT" and item.item_type == "SOCKET":
            out[item.name] = item.identifier
    return out


def key_gn(mod, ident, frame, value, interp="BEZIER"):
    mod[ident] = value
    path = f'["{ident}"]'
    mod.keyframe_insert(data_path=path, frame=frame)
    _set_interp(mod, path, frame, interp)


def key_visible(obj, frame, visible):
    """hide_render en marches : sert aux segments de jauge et aux textes."""
    obj.hide_render = not visible
    obj.hide_viewport = not visible
    for p in ("hide_render", "hide_viewport"):
        obj.keyframe_insert(data_path=p, frame=frame)
        _set_interp(obj, p, frame, "CONSTANT")


def O(name):
    o = bpy.data.objects.get(name)
    if o is None:
        raise KeyError(f"objet absent : {name}")
    return o


# --- Choregraphie -----------------------------------------------------------
#  1- 24  repos, la waveform defile deja
# 24- 60  la molette tourne          -> frequence monte, le Hz change
# 60- 96  le gain monte              -> amplitude + jauge DEPTH se remplit
# 96-132  le slider horizontal glisse -> MIX s'allume
# 132-156 appui D-pad droite
# 156-180 appui SYNC + flash ecran
# 180-192 retour au repos

def animate_wheel():
    """Rotation autour de son axe X (radians), avec anticipation et recovery."""
    w = O("PV2_wheel")
    w.rotation_mode = "XYZ"
    for f, rad in ((1, 0.0), (24, 0.0), (30, -0.14),
                   (56, 9.6), (60, 10.05), (192, 10.05)):
        key(w, "rotation_euler", f, rad, index=0)
    return w


def animate_gain():
    knob = O("PV2_gain_knob")
    z_lo, z_hi = 0.05, 1.95
    knob.location.z = z_lo
    for f, z in ((1, z_lo), (60, z_lo), (66, z_lo - 0.06),
                 (92, z_hi + 0.05), (96, z_hi), (192, z_hi)):
        key(knob, "location", f, z, index=2)
    return knob


def animate_hslider():
    cap = O("PV2_hslider_cap")
    x0 = cap.location.x
    x1 = x0 + 3.55                      # jamais jusqu'au bout du rail
    for f, x in ((1, x0), (96, x0), (102, x0 - 0.10),
                 (128, x1 + 0.08), (132, x1), (192, x1)):
        key(cap, "location", f, x, index=0)
    return cap


def animate_dpad():
    d = O("PV2_dpad")
    d.rotation_mode = "XYZ"
    # rotation autour de Z : le bras droit s'enfonce vers +Y
    for f, a in ((1, 0.0), (132, 0.0), (138, 7.0), (146, 7.0),
                 (152, 0.0), (192, 0.0)):
        key(d, "rotation_euler", f, math.radians(a), index=2)
    return d


def animate_sync():
    btn = O("PV2_sync")
    label = O("PV2_sync_label")
    label.parent = btn
    label.matrix_parent_inverse = btn.matrix_world.inverted()
    y0 = btn.location.y
    for f, y in ((1, y0), (156, y0), (161, y0 + 0.13), (170, y0 + 0.13),
                 (176, y0), (192, y0)):
        key(btn, "location", f, y, index=1)
    return btn


def animate_wave():
    """Le coeur : la waveform suit vraiment molette et gain."""
    wave = O("PV2_ui_wave")
    mod = wave.modifiers["Wave"]
    s = gn_sockets(mod)

    # defilement continu, lineaire, sur toute la duree
    key_gn(mod, s["Phase"], 1, 0.0, interp="LINEAR")
    key_gn(mod, s["Phase"], F_END, -14.0 * math.pi, interp="LINEAR")

    # frequence : suit la molette (24 -> 60)
    for f, v in ((1, 1.4), (24, 1.4), (60, 3.15), (192, 3.15)):
        key_gn(mod, s["Freq"], f, v)

    # amplitude : suit le gain (60 -> 96), puis respire avec le slider MIX
    for f, v in ((1, 0.34), (60, 0.34), (96, 0.86),
                 (132, 1.02), (156, 1.02), (163, 0.62), (176, 0.92), (192, 0.92)):
        key_gn(mod, s["Amp"], f, v)
    return wave


def animate_depth_bar():
    """Les 8 segments s'allument au fur et a mesure que le gain monte."""
    bars = [O(f"PV2_ui_bar{i}") for i in range(8)]
    for i, b in enumerate(bars):
        on = 60 + int(36 * (i + 1) / 8.0)     # etale sur la course du gain
        key_visible(b, 1, i < 2)
        key_visible(b, 59, i < 2)
        key_visible(b, on, True)
    return bars


def animate_hz_text(col):
    """Le texte de frequence change vraiment quand la molette tourne."""
    import controls as C
    base = O("PV2_ui_hz")
    mat = base.data.materials[0]
    variants = [(base, 1, 30)]
    for label, f_on, f_off in (("24.6Hz", 30, 46), ("38.2Hz", 46, F_END + 1)):
        t = C._emboss_text(
            f"PV2_ui_hz_{label}", label,
            I.SCREEN_CX - 1.86, I.SCREEN_CZ - 1.12, 0.24, col, mat,
            y=I.PANEL_Y - 0.012, extrude=0.004, align="LEFT")
        variants.append((t, f_on, f_off))

    for obj, f_on, f_off in variants:
        key_visible(obj, 1, f_on <= 1)
        if f_on > 1:
            key_visible(obj, f_on - 1, False)
            key_visible(obj, f_on, True)
        if f_off <= F_END:
            key_visible(obj, f_off, False)
    return [v[0] for v in variants]


def animate_mix_ring():
    """L'anneau MIX s'allume pendant la course du slider horizontal."""
    ring = O("PV2_ui_mixring")
    mat = ring.data.materials[0].copy()
    mat.name = "M_ui_mix_anim"
    ring.data.materials[0] = mat
    emit = mat.node_tree.nodes["Emission"]

    def k(frame, strength):
        emit.inputs["Strength"].default_value = strength
        emit.inputs["Strength"].keyframe_insert("default_value", frame=frame)

    k(1, 0.9); k(96, 0.9); k(120, 3.2); k(132, 3.2); k(150, 1.4); k(F_END, 1.4)
    return ring


def animate_screen_flash():
    """Flash de la dalle au moment de l'appui SYNC."""
    panel = O("PV2_screen_panel")
    emit = panel.data.materials[0].node_tree.nodes["Emission"]

    def k(frame, strength):
        emit.inputs["Strength"].default_value = strength
        emit.inputs["Strength"].keyframe_insert("default_value", frame=frame)

    k(1, 0.10); k(158, 0.10); k(162, 0.42); k(172, 0.14); k(F_END, 0.14)
    return panel


def animate_camera():
    """Cadre quasi fixe, leger rapprochement : c'est une demo, pas un turntable."""
    target = bpy.data.objects.new("PV2_anim_target", None)
    target.location = (0.1, 0.0, 0.35)
    bpy.context.scene.collection.objects.link(target)

    cam = studio.add_camera("PV2_anim_cam", (-19.0, -58.0, 14.0), lens=90)
    con = cam.constraints.new("TRACK_TO")
    con.target = target
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"

    # Rapprochement LEGER : l'objet doit rester entierement cadre du debut a
    # la fin — c'est une demo des controles, pas un travelling.
    for f, loc in ((1, (-19.0, -58.0, 14.0)),
                   (96, (-14.0, -54.0, 10.0)),
                   (F_END, (-9.0, -51.0, 6.5))):
        cam.location = loc
        cam.keyframe_insert(data_path="location", frame=f)
    for fc in _fcurves(cam.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
    return cam


def main():
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, F_END
    scene.render.fps = FPS

    studio.build_studio(samples=int(os.environ.get("PV2_SAMPLES", "72")))

    col_ui = bpy.data.collections.get("PV2_ui") or scene.collection

    animate_wheel()
    animate_gain()
    animate_hslider()
    animate_dpad()
    animate_sync()
    animate_wave()
    animate_depth_bar()
    animate_hz_text(col_ui)
    animate_mix_ring()
    animate_screen_flash()
    cam = animate_camera()
    scene.camera = cam

    # les fleches du D-pad doivent suivre le bouton quand il bascule
    dpad = O("PV2_dpad")
    for name in ("up", "down", "left", "right"):
        a = bpy.data.objects.get(f"PV2_dpad_arrow_{name}")
        if a:
            a.parent = dpad
            a.matrix_parent_inverse = dpad.matrix_world.inverted()

    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    print(f"[ok] anim {scene.frame_start}-{scene.frame_end} @ {FPS} fps -> {OUT_BLEND}")


if __name__ == "__main__":
    main()
