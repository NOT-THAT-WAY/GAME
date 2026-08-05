"""Controles, serigraphie et tranches de Pulsed v2.

Positions issues de audits/pulsed-object-map-v3.md (coordonnees u,v mesurees
sur refB f_0003), converties en BU par L.uv_to_xz.
"""

import math

import bpy

import pulsed_lib as L

Y_RIM = L.Y_SEAM - L.F_WALL - L.F_FILLET        # face exterieure : -1.35
Y_FACE = Y_RIM + L.F_STEP                       # plaque encastree : -1.21

LOGO_PNG = ("${LEGACY_VISUAL_AI_HUB_ROOT}/assets/"
            "logo final/unrecorded_logo_black_background_no.png")

_LY = L.LAYOUT
WHEEL_X, WHEEL_Z = L.uv_to_xz(_LY["wheel"]["u"], _LY["wheel"]["v"])
SYNC_X, SYNC_Z = L.uv_to_xz(_LY["sync"]["u"], _LY["sync"]["v"])
DPAD_X, DPAD_Z = L.uv_to_xz(_LY["dpad"]["u"], _LY["dpad"]["v"])
RAIL_X0, RAIL_Z = L.uv_to_xz(_LY["rail"]["u"][0], _LY["rail"]["v"])
RAIL_X1, _ = L.uv_to_xz(_LY["rail"]["u"][1], _LY["rail"]["v"])
GAIN_X, GAIN_ZTOP = L.uv_to_xz(_LY["gain"]["u"], _LY["gain"]["v"][0])
_, GAIN_ZBOT = L.uv_to_xz(_LY["gain"]["u"], _LY["gain"]["v"][1])
_, GAIN_ZKNOB = L.uv_to_xz(_LY["gain"]["u"], _LY["gain"]["knob_v"])


def _emboss_text(name, body, x, z, size, col, mat, y=Y_FACE - 0.012,
                 extrude=0.012, align="CENTER"):
    bpy.ops.object.text_add()
    t = bpy.context.active_object
    t.name = name
    t.data.body = body
    t.data.size = size
    t.data.align_x = align
    t.data.align_y = "CENTER"
    t.data.extrude = extrude
    t.rotation_euler = (math.radians(90), 0, 0)
    bpy.ops.object.convert(target="MESH")
    t = bpy.context.active_object
    L.move(t, x, y, z)
    L.link_only(t, col)
    t.data.materials.append(mat)
    return t


# --- Molette ----------------------------------------------------------------

def build_wheel(col, mats):
    """Tambour crante a axe HORIZONTAL + les deux domes violets."""
    teeth = 30
    r_out, r_in, half = 0.525, 0.452, 0.245
    verts, faces = [], []
    for sign, x in ((0, -half), (1, half)):
        for i in range(teeth * 2):
            a = 2 * math.pi * i / (teeth * 2)
            r = r_out if i % 2 == 0 else r_in
            verts.append((x, r * math.sin(a), r * math.cos(a)))
    n = teeth * 2
    for j in range(n):
        j2 = (j + 1) % n
        faces.append((j, j2, n + j2, n + j))
    faces.append(tuple(range(n - 1, -1, -1)))
    faces.append(tuple(range(n, 2 * n)))

    drum = L.make_object("PV2_wheel", verts, faces, col)
    L.recalc_normals(drum)
    L.move(drum, WHEEL_X, -1.05, WHEEL_Z)
    drum.data.materials.append(mats["grey"])
    L.shade_smooth(drum, angle_deg=24.0)

    domes = []
    for i, sx in enumerate((-1, 1)):
        # Sur la vue de face les domes sont gros et bombes : l'ensemble
        # molette + domes fait ~1,55 BU de large.
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.40, segments=32, ring_count=16)
        d = bpy.context.active_object
        d.name = f"PV2_wheel_dome_{'L' if sx < 0 else 'R'}"
        d.scale = (0.72, 1.0, 1.0)
        bpy.ops.object.transform_apply(scale=True)
        L.move(d, WHEEL_X + sx * 0.47, -1.12, WHEEL_Z)
        L.link_only(d, col)
        d.data.materials.append(mats["shell_glossy"])
        L.shade_smooth(d)
        domes.append(d)
    return drum, domes


# --- SYNC -------------------------------------------------------------------

def build_sync(col, mats):
    btn = L.cylinder("PV2_sync", 0.855, 0.34, axis="Y", verts=64, collection=col)
    L.move(btn, SYNC_X, -1.30, SYNC_Z)
    L.bevel(btn, 0.09, segments=4, angle_deg=40.0)
    btn.data.materials.append(mats["grey"])
    L.shade_smooth(btn, angle_deg=30.0)

    label = _emboss_text("PV2_sync_label", "SYNC", SYNC_X, SYNC_Z, 0.30, col,
                         mats["grey_dark"], y=-1.474, extrude=0.008)
    return btn, label


# --- D-pad ------------------------------------------------------------------

def build_dpad(col, mats):
    arm, thick, depth = 2.18, 0.77, 0.32
    y_c = -1.30
    h = L.rounded_box("PV2_dpad", arm, depth, thick, 0.10, segments=4, collection=col)
    L.move(h, DPAD_X, y_c, DPAD_Z)
    v = L.rounded_box("PV2_dpad_v", thick, depth, arm, 0.10, segments=4, collection=col)
    L.move(v, DPAD_X, y_c, DPAD_Z)
    L.boolean(h, v, operation="UNION")

    # Creux central
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.32, segments=24, ring_count=12)
    dimple = bpy.context.active_object
    dimple.name = "CUT_dpad_dimple"
    L.move(dimple, DPAD_X, y_c - depth / 2 - 0.16, DPAD_Z)
    L.link_only(dimple, col)
    L.boolean(h, dimple)

    h.data.materials.append(mats["grey"])
    L.shade_smooth(h, angle_deg=34.0)

    # Fleches embossees
    arrows = []
    y_top = y_c - depth / 2 - 0.004
    for name, dx, dz, rot in (("up", 0, 0.68, 0), ("down", 0, -0.68, 180),
                              ("left", -0.68, 0, 90), ("right", 0.68, 0, -90)):
        s = 0.17
        tri = [(-s, 0.0, -s * 0.8), (s, 0.0, -s * 0.8), (0.0, 0.0, s * 0.9)]
        a = math.radians(rot)
        tri = [(x * math.cos(a) - z * math.sin(a), y, x * math.sin(a) + z * math.cos(a))
               for x, y, z in tri]
        vs = [(x, y, z) for x, y, z in tri] + [(x, y - 0.03, z) for x, y, z in tri]
        fs = [(0, 1, 2), (5, 4, 3), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)]
        o = L.make_object(f"PV2_dpad_arrow_{name}", vs, fs, col)
        L.recalc_normals(o)
        L.move(o, DPAD_X + dx, y_top, DPAD_Z + dz)
        o.data.materials.append(mats["grey"])
        arrows.append(o)
    return h, arrows


# --- Sliders ----------------------------------------------------------------

def build_hslider(col, mats):
    """Capsule SURELEVEE (jamais creusee) + cap a cheval, butee gauche."""
    length = RAIL_X1 - RAIL_X0
    cx = (RAIL_X0 + RAIL_X1) / 2
    rail = L.rounded_box("PV2_hslider_rail", length, 0.46, 0.76, 0.24,
                         segments=6, collection=col)
    L.move(rail, cx, -1.34, RAIL_Z)
    rail.data.materials.append(mats["shell_thin"])
    L.shade_smooth(rail, angle_deg=40.0)

    cap = L.rounded_box("PV2_hslider_cap", 0.51, 0.50, 0.99, 0.09,
                        segments=4, collection=col)
    L.move(cap, RAIL_X0 + 0.28 + 0.40 * (RAIL_X1 - RAIL_X0 - 0.56), -1.38, RAIL_Z)
    cap.data.materials.append(mats["grey"])
    L.shade_smooth(cap, angle_deg=34.0)
    return rail, cap


def build_gain(col, mats):
    knob = L.rounded_box("PV2_gain_knob", 0.34, 0.34, 0.40, 0.10,
                         segments=4, collection=col)
    L.move(knob, GAIN_X, -1.28, GAIN_ZKNOB)
    knob.data.materials.append(mats["grey"])
    L.shade_smooth(knob, angle_deg=34.0)
    return knob


# --- Serigraphie face -------------------------------------------------------

def build_silkscreen(col, mats):
    items = []
    x, z = L.uv_to_xz(0.4975, 0.176)         # centre du wordmark
    items.append(_emboss_text("PV2_wordmark", "Pulsed", x, z, 0.60, col,
                              mats["shell"]))
    # Vrai glyphe UNRECORDED, trace depuis le PNG de marque : aucune police
    # systeme ne s'en approche.
    x, z = L.uv_to_xz(_LY["logo"]["u"], _LY["logo"]["v"])
    try:
        import logo_trace
        items.append(logo_trace.build(
            LOGO_PNG, "PV2_logo_u", x, z, 0.74, col, mats["shell"],
            y=Y_FACE - 0.012, depth=0.024, tol=0.5))
    except Exception as exc:
        print(f"  ! trace du logo impossible ({exc}) — repli sur du texte")
        items.append(_emboss_text("PV2_logo_u", "U.", x, z, 0.46, col,
                                  mats["shell"]))

    # Pas de pastille « power » : elle venait de refB f_0003 et n'apparait pas
    # sur la vue de face. On n'invente pas une feature non verifiee.

    x, z = L.uv_to_xz(_LY["lowbatt"]["u"], _LY["lowbatt"]["v"])
    items.append(_emboss_text("PV2_lowbatt", "LOW BATT", x, z, 0.20, col,
                              mats["shell"], extrude=0.006))

    # Bloc connecteur blanc a droite du slider gain
    x, z = L.uv_to_xz(0.883, 0.394)
    blk = L.rounded_box("PV2_connector_white", 0.42, 0.34, 0.46, 0.05,
                        segments=2, collection=col)
    L.move(blk, x, -1.02, z)
    blk.data.materials.append(mats["white"])
    items.append(blk)
    return items


# --- Tranches ---------------------------------------------------------------

def build_edges(col, cut_col, mats):
    """Ports de la tranche basse + tabs de la tranche haute.

    Annule la decision v1 « toutes les tranches sont lisses » : les deux
    connecteurs du bas sont nets et coherents sur refB f_0027 et f_0003.
    """
    z_bot = -L.HH
    z_top = L.HH
    cutters, inserts = [], []

    # USB-C (u 0.404) et connecteur secondaire (u 0.530)
    for name, u, sx, sz in (("usbc", _LY["port_usbc"]["u"], 1.02, 0.44),
                            ("aux", _LY["port_aux"]["u"], 0.78, 0.40)):
        x, _ = L.uv_to_xz(u, 0.0)
        c = L.rounded_box(f"CUT_port_{name}", sx, 0.62, sz + 0.5, 0.14,
                          segments=4, collection=cut_col)
        L.move(c, x, L.Y_SEAM + 0.05, z_bot + sz / 2 - 0.06)
        cutters.append(c)

        ins = L.rounded_box(f"PV2_port_{name}", sx - 0.14, 0.44, sz - 0.10, 0.09,
                            segments=3, collection=col)
        L.move(ins, x, L.Y_SEAM + 0.05, z_bot + sz / 2 + 0.02)
        ins.data.materials.append(mats["metal"])
        inserts.append(ins)

    # Tabs clairs de la tranche haute (u 0.363 et 0.662)
    for i, u in enumerate(_LY["tabs"]["u"]):
        x, _ = L.uv_to_xz(u, 0.0)
        tab = L.rounded_box(f"PV2_tab_{i}", 0.62, 0.40, 0.30, 0.06,
                            segments=3, collection=col)
        L.move(tab, x, L.Y_SEAM + 0.02, z_top - 0.08)
        tab.data.materials.append(mats["white"])
        inserts.append(tab)

    return cutters, inserts
