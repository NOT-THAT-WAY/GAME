"""Primitives geometriques pour la reconstruction Pulsed v2.

Repere : X = largeur, Y = epaisseur (la face regarde -Y), Z = hauteur.
1 BU = 1 cm. Toutes les cotes viennent de audits/pulsed-object-map-v3.md.
"""

import math

import bpy
import bmesh
from mathutils import Vector

# --- Cotes maitresses (carte v3) -------------------------------------------

W = 16.0            # largeur
RATIO = 1.74        # W/H mesure sur la vue de face orthographique (carte v4)
H = W / RATIO       # 9.195
R_CORNER = 2.10     # rayon de coin de la silhouette
HW, HH = W / 2.0, H / 2.0

# --- Layout de la face, SOURCE UNIQUE ---------------------------------------
# u = fraction de W depuis la gauche · v = fraction de H depuis le haut.
# Mesure sur la vue de face fournie par Sliz (2026-07-30), quasi orthographique.
# La grille de design : deux colonnes (u 0.202 / 0.787) et deux rangees
# (v 0.394 / 0.697) — c'est elle qui cale tout le reste.
COL_L, COL_R = 0.202, 0.787
ROW_HI, ROW_LO = 0.394, 0.697

LAYOUT = {
    "screen":   {"u": (0.269, 0.730), "v": (0.226, 0.569)},
    "wheel":    {"u": 0.200, "v": ROW_HI},
    "sync":     {"u": 0.205, "v": ROW_LO},
    "dpad":     {"u": 0.792, "v": ROW_LO},
    "rail":     {"u": (0.321, 0.675), "v": ROW_LO},
    "gain":     {"u": 0.784, "v": (0.274, 0.546), "knob_v": ROW_HI},
    "wordmark": {"u": (0.417, 0.578), "v": (0.150, 0.202)},
    "logo":     {"u": 0.786, "v": 0.175},
    "lowbatt":  {"u": 0.289, "v": 0.819},
    "faceplate": {"u": (0.111, 0.889), "v": (0.095, 0.885)},
    "port_usbc": {"u": 0.404},
    "port_aux":  {"u": 0.530},
    "tabs":      {"u": (0.363, 0.662)},
}


def span(key, axis):
    """(debut, fin, longueur, centre) d'un element, en BU."""
    a, b = LAYOUT[key][axis]
    scale = W if axis == "u" else H
    p0 = -HW + a * W if axis == "u" else HH - a * H
    p1 = -HW + b * W if axis == "u" else HH - b * H
    return p0, p1, abs(p1 - p0), (p0 + p1) / 2.0

Y_SEAM = -0.45      # plan de joint des deux demi-coques

# demi-coque avant : mur droit -> conge -> jonc plat -> marche -> plaque
F_WALL, F_FILLET, F_STEP = 0.30, 0.60, 0.14
# demi-coque arriere : mur droit -> conge -> dome
B_WALL, B_FILLET, B_DOME = 0.45, 0.85, 0.50

WALL_THICKNESS = 0.18

# plaque encastree (faceplate) — derivee du layout, plus de valeur en dur
_FU0, _FU1 = LAYOUT["faceplate"]["u"]
_FV0, _FV1 = LAYOUT["faceplate"]["v"]
FP_HW = (_FU1 - _FU0) / 2.0 * W
FP_HH = (_FV1 - _FV0) / 2.0 * H
FP_CZ = HH - (_FV0 + _FV1) / 2.0 * H
FP_R = 1.25

N_CORNER, N_SIDE = 14, 9   # -> 92 points par anneau


def uv_to_xz(u, v):
    """Coordonnees normalisees de la carte v3 -> BU."""
    return -HW + u * W, HH - v * H


# --- Silhouette -------------------------------------------------------------

def rounded_rect(hw, hh, r, n_corner=N_CORNER, n_side=N_SIDE, cz=0.0):
    """Rectangle arrondi dans le plan XZ, parcours anti-horaire.

    Toujours le meme nombre de points quel que soit (hw, hh, r), pour que deux
    anneaux differents restent loftables sans reindexation.
    """
    r = max(min(r, hw, hh), 1e-4)
    ax, az = hw - r, hh - r          # centres des arcs de coin
    pts = []

    def edge(x0, z0, x1, z1):
        for i in range(n_side):
            t = i / n_side
            pts.append((x0 + (x1 - x0) * t, z0 + (z1 - z0) * t))

    def corner(cx, cz_, a0):
        for i in range(n_corner):
            a = math.radians(a0 + 90.0 * i / n_corner)
            pts.append((cx + r * math.cos(a), cz_ + r * math.sin(a)))

    edge(hw, -az, hw, az)
    corner(ax, az, 0)
    edge(ax, hh, -ax, hh)
    corner(-ax, az, 90)
    edge(-hw, az, -hw, -az)
    corner(-ax, -az, 180)
    edge(-ax, -hh, ax, -hh)
    corner(ax, -az, 270)
    return [(x, z + cz) for x, z in pts]


def offset_body(o):
    """Silhouette du corps retrecie de `o` vers l'interieur."""
    return rounded_rect(HW - o, HH - o, R_CORNER - o)


def faceplate_outline(o=0.0):
    return rounded_rect(FP_HW - o, FP_HH - o, FP_R - o, cz=FP_CZ)


# --- Loft -------------------------------------------------------------------

def ring(points_2d, y):
    return [(x, y, z) for x, z in points_2d]


def loft(rings, cap_last=False, cap_first=False):
    """Coud une pile d'anneaux fermes de meme longueur. -> (verts, faces)"""
    n = len(rings[0])
    verts, faces = [], []
    for rg in rings:
        assert len(rg) == n, "anneaux de longueurs differentes"
        verts.extend(rg)
    for k in range(len(rings) - 1):
        a, b = k * n, (k + 1) * n
        for j in range(n):
            j2 = (j + 1) % n
            faces.append((a + j, a + j2, b + j2, b + j))
    if cap_first:
        faces.append(tuple(range(n - 1, -1, -1)))
    if cap_last:
        base = (len(rings) - 1) * n
        faces.append(tuple(range(base, base + n)))
    return verts, faces


def fan_to_point(last_ring_start, n, apex_index):
    return [(last_ring_start + j, last_ring_start + (j + 1) % n, apex_index)
            for j in range(n)]


# --- Objets -----------------------------------------------------------------

def make_object(name, verts, faces, collection=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.validate(verbose=False)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj


def recalc_normals(obj, inward=False):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if inward:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()


def shade_smooth(obj, angle_deg=38.0):
    for p in obj.data.polygons:
        p.use_smooth = True
    mod = obj.modifiers.new("SmoothByAngle", "NODES")
    ng = bpy.data.node_groups.get("Smooth by Angle")
    if ng is None:
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        obj.modifiers.remove(mod)
        bpy.ops.object.shade_auto_smooth(angle=math.radians(angle_deg))
    else:
        mod.node_group = ng


def solidify(obj, thickness=WALL_THICKNESS, offset=1.0):
    m = obj.modifiers.new("Solidify", "SOLIDIFY")
    m.thickness = thickness
    m.offset = offset
    # even_offset produit des pointes enormes sur les aretes issues des booleens
    m.use_even_offset = False
    m.use_rim = True
    m.use_rim_only = False
    return m


def boolean(obj, cutter, operation="DIFFERENCE", solver="EXACT"):
    m = obj.modifiers.new(f"Bool_{cutter.name}", "BOOLEAN")
    m.operation = operation
    m.object = cutter
    m.solver = solver
    cutter.display_type = "WIRE"
    cutter.hide_render = True
    return m


def bevel(obj, width, segments=3, angle_deg=32.0):
    m = obj.modifiers.new("Bevel", "BEVEL")
    m.width = width
    m.segments = segments
    m.limit_method = "ANGLE"
    m.angle_limit = math.radians(angle_deg)
    m.harden_normals = False
    return m


def apply_all_modifiers(obj):
    bpy.context.view_layer.objects.active = obj
    for m in list(obj.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=m.name)
        except RuntimeError as exc:
            print(f"  ! modifier {m.name} sur {obj.name} : {exc}")


def rounded_box(name, sx, sy, sz, r, segments=6, collection=None):
    """Boite arrondie, utilisee comme decoupe booleenne ou comme volume simple."""
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    m = obj.modifiers.new("Bevel", "BEVEL")
    m.width = r
    m.segments = segments
    m.limit_method = "NONE"
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=m.name)
    if collection is not None and obj.name not in collection.objects:
        for c in obj.users_collection:
            c.objects.unlink(obj)
        collection.objects.link(obj)
    return obj


def cylinder(name, radius, depth, axis="Y", verts=48, collection=None):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, vertices=verts)
    obj = bpy.context.active_object
    obj.name = name
    if axis == "Y":
        obj.rotation_euler = (math.radians(90), 0, 0)
    elif axis == "X":
        obj.rotation_euler = (0, math.radians(90), 0)
    bpy.ops.object.transform_apply(rotation=True)
    if collection is not None and obj.name not in collection.objects:
        for c in obj.users_collection:
            c.objects.unlink(obj)
        collection.objects.link(obj)
    return obj


def move(obj, x=0.0, y=0.0, z=0.0):
    obj.location = (x, y, z)
    return obj


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.curves,
                  bpy.data.images, bpy.data.node_groups, bpy.data.actions):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def get_collection(name, parent=None):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(col)
    return col


def link_only(obj, collection):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection.objects.link(obj)
