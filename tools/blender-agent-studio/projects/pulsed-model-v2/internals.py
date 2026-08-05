"""Internes Pulsed v2 : PCB, composants, module ecran et UI emissive.

L'UI est de la GEOMETRIE, pas une texture : la waveform est un Geometry Nodes
pilote par trois entrees (freq / amp / phase) qu'on peut keyframer, donc l'ecran
peut vraiment reagir aux controles pendant l'animation.
"""

import math
import random

import bpy

import pulsed_lib as L

# --- PCB --------------------------------------------------------------------

PCB_W, PCB_H, PCB_T = 13.9, 7.25, 0.12
PCB_CZ, PCB_Y = 0.10, -0.18

SCREEN_CX, SCREEN_CZ = 0.0, 0.94
SCREEN_W, SCREEN_H = 7.38, 3.15
PANEL_W, PANEL_H = 7.05, 2.86
PANEL_Y = -1.155


def build_pcb(col, mats):
    board = L.rounded_box("PV2_pcb", PCB_W, PCB_T, PCB_H, 0.06, segments=2, collection=col)
    L.move(board, 0.0, PCB_Y, PCB_CZ)
    board.data.materials.append(mats["pcb"])

    parts = [board]

    def chip(name, x, z, sx, sz, sy=0.22, mat="component", front=False):
        """front=True -> composant cote face (visible par la coque avant)."""
        o = L.rounded_box(name, sx, sy, sz, 0.02, segments=2, collection=col)
        side = -1 if front else 1
        L.move(o, x, PCB_Y + side * (PCB_T / 2 + sy / 2), z)
        o.data.materials.append(mats[mat])
        parts.append(o)
        return o

    # Les deux gros QFP centraux et le SOIC de droite (lus sur refB f_0027).
    chip("PV2_ic_qfp1", -1.05, 0.85, 1.55, 1.55)
    chip("PV2_ic_qfp2", 0.85, 0.90, 1.75, 1.60)
    chip("PV2_ic_soic", 2.95, 0.35, 1.10, 1.95)

    # Condensateur electrolytique rond, a gauche.
    cap = L.cylinder("PV2_cap_elec", 0.30, 0.34, axis="Y", verts=24, collection=col)
    L.move(cap, -2.30, PCB_Y + 0.23, -0.55)
    cap.data.materials.append(mats["metal"])
    parts.append(cap)

    # Plots de vis.
    for sx in (-1, 1):
        for sz in (-1, 1):
            p = L.cylinder(f"PV2_post_{sx}_{sz}", 0.24, 0.30, axis="Y",
                           verts=16, collection=col)
            L.move(p, sx * 5.75, PCB_Y + 0.21, PCB_CZ + sz * 2.85)
            p.data.materials.append(mats["component"])
            parts.append(p)

    # Le module ecran occupe ce rectangle cote face : rien ne peut y tenir.
    sx0, sx1 = SCREEN_CX - 3.60, SCREEN_CX + 3.60
    sz0, sz1 = SCREEN_CZ - 1.70, SCREEN_CZ + 1.70

    # Passifs sur LES DEUX faces : la coque avant est translucide, la ref montre
    # bien des composants et des connecteurs autour de l'ecran.
    rng = random.Random(20260730)
    for i in range(150):
        x = rng.uniform(-6.5, 6.5)
        z = rng.uniform(-3.4, 3.6)
        front = rng.random() < 0.45
        if front and sx0 < x < sx1 and sz0 < z < sz1:
            continue
        if not front:
            if abs(x + 1.05) < 1.1 and abs(z - 0.85) < 1.1:
                continue
            if abs(x - 0.85) < 1.2 and abs(z - 0.90) < 1.1:
                continue
        sx = rng.uniform(0.10, 0.30)
        sz = rng.uniform(0.08, 0.22)
        if rng.random() < 0.5:
            sx, sz = sz, sx
        h = rng.uniform(0.07, 0.13)
        o = L.rounded_box(f"PV2_smd_{i:03d}", sx, h, sz, 0.015,
                          segments=1, collection=col)
        L.move(o, x, PCB_Y + (-1 if front else 1) * (PCB_T / 2 + h / 2), z)
        o.data.materials.append(mats["copper"] if rng.random() < 0.22
                                else mats["component"])
        parts.append(o)

    # Connecteurs blancs cote face, comme sur refB f_0003.
    for i, (x, z) in enumerate(((-5.20, 2.85), (5.35, 2.60), (-5.55, -2.35))):
        o = L.rounded_box(f"PV2_conn_{i}", 0.55, 0.26, 0.34, 0.04,
                          segments=2, collection=col)
        L.move(o, x, PCB_Y - PCB_T / 2 - 0.13, z)
        o.data.materials.append(mats["white"])
        parts.append(o)

    return parts


# --- Module ecran -----------------------------------------------------------

def build_screen_module(col, mats):
    """Cadre noir + dalle sombre. L'UI vient par dessus."""
    bezel = L.rounded_box("PV2_screen_bezel", SCREEN_W + 0.16, 0.30,
                          SCREEN_H + 0.15, 0.05, segments=2, collection=col)
    L.move(bezel, SCREEN_CX, PANEL_Y + 0.15 + 0.005, SCREEN_CZ)
    bezel.data.materials.append(mats["glass"])

    bpy.ops.mesh.primitive_plane_add(size=1.0)
    panel = bpy.context.active_object
    panel.name = "PV2_screen_panel"
    panel.rotation_euler = (math.radians(90), 0, 0)
    panel.scale = (PANEL_W, PANEL_H, 1.0)
    bpy.ops.object.transform_apply(rotation=True, scale=True)
    L.move(panel, SCREEN_CX, PANEL_Y, SCREEN_CZ)
    L.link_only(panel, col)

    import materials as M
    # Le fond de dalle est quasi noir : c'est l'UI qui doit briller, pas l'ecran.
    panel.data.materials.append(M.screen_ui("M_screen_bg", strength=0.10))
    panel.data.materials[0].node_tree.nodes["Emission"].inputs["Color"] \
        .default_value = (0.020, 0.075, 0.085, 1.0)
    return bezel, panel


# --- UI : texte, jauges, waveform -------------------------------------------

TEAL = (0.16, 0.86, 0.78, 1.0)


def _ui_material(name, color=TEAL, strength=3.4):
    import materials as M
    m = M.screen_ui(name, strength=strength)
    m.node_tree.nodes["Emission"].inputs["Color"].default_value = color
    return m


def _text(name, body, x, z, size, col, mat, align="CENTER", extrude=0.004):
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
    L.move(t, SCREEN_CX + x, PANEL_Y - 0.012, SCREEN_CZ + z)
    L.link_only(t, col)
    t.data.materials.append(mat)
    return t


def build_ui(col, mats):
    # Assez bas pour rester teal apres AgX : au-dela l'emission clippe en blanc.
    teal = _ui_material("M_ui_teal", TEAL, 1.5)
    dim = _ui_material("M_ui_dim", (0.09, 0.48, 0.46, 1.0), 0.9)
    items = []

    # Barre de titre
    items.append(_text("PV2_ui_title", "< Default* >", 0.0, 1.14, 0.26, col, dim))
    for i, x in enumerate((2.02, 2.52)):
        ic = L.rounded_box(f"PV2_ui_icon{i}", 0.20, 0.008, 0.20, 0.03,
                           segments=1, collection=col)
        L.move(ic, SCREEN_CX + x, PANEL_Y - 0.012, SCREEN_CZ + 1.14)
        ic.data.materials.append(dim)
        items.append(ic)

    # Barre d'etat
    items.append(_text("PV2_ui_free", "FREE", -2.92, -1.12, 0.24, col, dim, "LEFT"))
    items.append(_text("PV2_ui_hz", "11.7Hz", -1.86, -1.12, 0.24, col, teal, "LEFT"))
    items.append(_text("PV2_ui_mix", "MIX", -0.05, -1.12, 0.17, col, teal))
    items.append(_text("PV2_ui_depth", "DEPTH", 1.42, -1.12, 0.22, col, dim, "LEFT"))

    # Pastille ronde autour de MIX
    ring = L.cylinder("PV2_ui_mixring", 0.30, 0.006, axis="Y", verts=32, collection=col)
    L.move(ring, SCREEN_CX - 0.05, PANEL_Y - 0.006, SCREEN_CZ - 1.12)
    ring.data.materials.append(dim)
    items.append(ring)

    # Barregraphe DEPTH : 8 segments, animables par visibilite
    for i in range(8):
        seg = L.rounded_box(f"PV2_ui_bar{i}", 0.085, 0.008, 0.30, 0.015,
                            segments=1, collection=col)
        L.move(seg, SCREEN_CX + 2.18 + i * 0.125, PANEL_Y - 0.012,
               SCREEN_CZ - 1.12)
        seg.data.materials.append(teal)
        items.append(seg)

    items.append(build_waveform(col, teal))
    return items


def build_waveform(col, mat):
    """Waveform en Geometry Nodes : freq / amp / phase keyframables."""
    bpy.ops.mesh.primitive_plane_add(size=0.01)
    obj = bpy.context.active_object
    obj.name = "PV2_ui_wave"
    obj.data.clear_geometry()
    L.move(obj, SCREEN_CX, PANEL_Y - 0.02, SCREEN_CZ + 0.28)
    L.link_only(obj, col)

    ng = bpy.data.node_groups.new("PV2_WaveNodes", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    for sock, default, lo, hi in (("Freq", 1.4, 0.2, 14.0),
                                  ("Amp", 0.55, 0.0, 1.30),
                                  ("Phase", 0.0, -100.0, 100.0)):
        s = ng.interface.new_socket(sock, in_out="INPUT", socket_type="NodeSocketFloat")
        s.default_value, s.min_value, s.max_value = default, lo, hi

    n = ng.nodes
    gin = n.new("NodeGroupInput"); gin.location = (-900, -200)
    gout = n.new("NodeGroupOutput"); gout.location = (700, 0)

    line = n.new("GeometryNodeCurvePrimitiveLine"); line.location = (-700, 0)
    line.inputs["Start"].default_value = (-3.02, 0, 0)
    line.inputs["End"].default_value = (3.02, 0, 0)

    resample = n.new("GeometryNodeResampleCurve"); resample.location = (-520, 0)
    resample.inputs["Count"].default_value = 220

    pos = n.new("GeometryNodeInputPosition"); pos.location = (-880, -420)
    sep = n.new("ShaderNodeSeparateXYZ"); sep.location = (-700, -420)

    mul = n.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.location = (-520, -420)
    add = n.new("ShaderNodeMath"); add.operation = "ADD"; add.location = (-360, -420)
    sine = n.new("ShaderNodeMath"); sine.operation = "SINE"; sine.location = (-200, -420)
    amp = n.new("ShaderNodeMath"); amp.operation = "MULTIPLY"; amp.location = (-40, -420)
    comb = n.new("ShaderNodeCombineXYZ"); comb.location = (120, -420)

    setpos = n.new("GeometryNodeSetPosition"); setpos.location = (-40, 0)
    profile = n.new("GeometryNodeCurvePrimitiveCircle"); profile.location = (-40, 260)
    profile.inputs["Resolution"].default_value = 8
    profile.inputs["Radius"].default_value = 0.035
    tomesh = n.new("GeometryNodeCurveToMesh"); tomesh.location = (300, 0)
    tomesh.inputs["Fill Caps"].default_value = True
    setmat = n.new("GeometryNodeSetMaterial"); setmat.location = (500, 0)
    setmat.inputs["Material"].default_value = mat

    lk = ng.links.new
    lk(line.outputs["Curve"], resample.inputs["Curve"])
    lk(resample.outputs["Curve"], setpos.inputs["Geometry"])
    lk(pos.outputs["Position"], sep.inputs["Vector"])
    lk(sep.outputs["X"], mul.inputs[0])
    lk(gin.outputs["Freq"], mul.inputs[1])
    lk(mul.outputs["Value"], add.inputs[0])
    lk(gin.outputs["Phase"], add.inputs[1])
    lk(add.outputs["Value"], sine.inputs[0])
    lk(sine.outputs["Value"], amp.inputs[0])
    lk(gin.outputs["Amp"], amp.inputs[1])
    lk(amp.outputs["Value"], comb.inputs["Z"])
    lk(comb.outputs["Vector"], setpos.inputs["Offset"])
    lk(setpos.outputs["Geometry"], tomesh.inputs["Curve"])
    lk(profile.outputs["Curve"], tomesh.inputs["Profile Curve"])
    lk(tomesh.outputs["Mesh"], setmat.inputs["Geometry"])
    lk(setmat.outputs["Geometry"], gout.inputs["Geometry"])

    mod = obj.modifiers.new("Wave", "NODES")
    mod.node_group = ng
    return obj
