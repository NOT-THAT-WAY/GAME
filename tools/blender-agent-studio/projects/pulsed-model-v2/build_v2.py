"""Pulsed v2 — reconstruction complete depuis les videos de reference.

Source de verite : audits/pulsed-object-map-v3.md (mesuree sur refA/refB).
N'ouvre ni ne modifie jamais Pulsed_3D_model.blend (racine du depot).

  blender -b --python build_v2.py
"""

import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

import pulsed_lib as L        # noqa: E402
import materials as M         # noqa: E402
import controls as C          # noqa: E402
import internals as I         # noqa: E402

OUT_BLEND = os.path.join(ROOT, "scene", "pulsed_v2.blend")

N_FILLET = 7
N_DOME = 6


# --- Coques -----------------------------------------------------------------

def build_front_shell(col):
    rings = [L.ring(L.offset_body(0.0), L.Y_SEAM),
             L.ring(L.offset_body(0.0), L.Y_SEAM - L.F_WALL)]
    for i in range(1, N_FILLET + 1):
        a = math.radians(90.0 * i / N_FILLET)
        rings.append(L.ring(L.offset_body(L.F_FILLET * (1.0 - math.cos(a))),
                            L.Y_SEAM - L.F_WALL - L.F_FILLET * math.sin(a)))
    y_face = L.Y_SEAM - L.F_WALL - L.F_FILLET
    rings.append(L.ring(L.faceplate_outline(0.0), y_face))
    rings.append(L.ring(L.faceplate_outline(0.0), y_face + L.F_STEP))

    verts, faces = L.loft(rings, cap_last=True)
    obj = L.make_object("PV2_shell_front", verts, faces, col)
    L.recalc_normals(obj)
    return obj


def build_back_shell(col):
    rings = [L.ring(L.offset_body(0.0), L.Y_SEAM),
             L.ring(L.offset_body(0.0), L.Y_SEAM + L.B_WALL)]
    for i in range(1, N_FILLET + 1):
        a = math.radians(90.0 * i / N_FILLET)
        rings.append(L.ring(L.offset_body(L.B_FILLET * (1.0 - math.cos(a))),
                            L.Y_SEAM + L.B_WALL + L.B_FILLET * math.sin(a)))

    y_rim = L.Y_SEAM + L.B_WALL + L.B_FILLET
    rim = L.offset_body(L.B_FILLET)
    for i in range(1, N_DOME + 1):
        f = 1.0 - i / (N_DOME + 1.0)
        rings.append(L.ring([(x * f, z * f) for x, z in rim],
                            y_rim + L.B_DOME * (1.0 - f) ** 2))

    verts, faces = L.loft(rings)
    n = len(rings[0])
    apex = len(verts)
    verts.append((0.0, y_rim + L.B_DOME, 0.0))
    faces.extend(L.fan_to_point((len(rings) - 1) * n, n, apex))

    obj = L.make_object("PV2_shell_back", verts, faces, col)
    L.recalc_normals(obj)
    return obj


def build_front_cutters(col):
    y_face = L.Y_SEAM - L.F_WALL - L.F_FILLET
    y_mid, depth = y_face + 0.5, 3.0
    cutters = []

    su, sv = L.LAYOUT["screen"]["u"], L.LAYOUT["screen"]["v"]
    x0, z0 = L.uv_to_xz(su[0], sv[0])
    x1, z1 = L.uv_to_xz(su[1], sv[1])
    scr = L.rounded_box("CUT_screen", abs(x1 - x0), depth, abs(z1 - z0), 0.10)
    L.move(scr, (x0 + x1) / 2, y_mid, (z0 + z1) / 2)
    cutters.append(scr)

    x, z = L.uv_to_xz(L.LAYOUT["sync"]["u"], L.LAYOUT["sync"]["v"])
    cutters.append(L.move(L.cylinder("CUT_sync", 0.955, depth, axis="Y"), x, y_mid, z))

    x, z = L.uv_to_xz(L.LAYOUT["wheel"]["u"], L.LAYOUT["wheel"]["v"])
    cutters.append(L.move(L.rounded_box("CUT_wheel", 0.58, depth, 1.12, 0.14),
                          x, y_mid, z))

    gu, gv = L.LAYOUT["gain"]["u"], L.LAYOUT["gain"]["v"]
    x, z_top = L.uv_to_xz(gu, gv[0])
    _, z_bot = L.uv_to_xz(gu, gv[1])
    cutters.append(L.move(L.rounded_box("CUT_gain", 0.34, depth,
                                        abs(z_top - z_bot), 0.16),
                          x, y_mid, (z_top + z_bot) / 2))

    x, z = L.uv_to_xz(L.LAYOUT["dpad"]["u"], L.LAYOUT["dpad"]["v"])
    for name, sx, sz in (("CUT_dpad_h", 2.32, 0.91), ("CUT_dpad_v", 0.91, 2.32)):
        cutters.append(L.move(L.rounded_box(name, sx, depth, sz, 0.10), x, y_mid, z))

    for c in cutters:
        L.link_only(c, col)
    return cutters


# --- Assemblage -------------------------------------------------------------

def bbox_world(obj, deps):
    ev = obj.evaluated_get(deps)
    pts = [ev.matrix_world @ Vector(c) for c in ev.bound_box]
    return ((min(p.x for p in pts), max(p.x for p in pts)),
            (min(p.y for p in pts), max(p.y for p in pts)),
            (min(p.z for p in pts), max(p.z for p in pts)))


def main():
    L.clear_scene()
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"

    root = L.get_collection("PULSED_V2")
    col_shell = L.get_collection("PV2_shell", root)
    col_ctrl = L.get_collection("PV2_controls", root)
    col_int = L.get_collection("PV2_internals", root)
    col_ui = L.get_collection("PV2_ui", root)
    col_cut = L.get_collection("PV2_cutters", root)

    mats = M.build_all()

    front = build_front_shell(col_shell)
    back = build_back_shell(col_shell)

    # Solidify D'ABORD : les demi-coques sont des surfaces ouvertes, et un
    # booleen sur du non-manifold rend n'importe quoi. Le Solidify les ferme.
    for o in (front, back):
        L.solidify(o, L.WALL_THICKNESS, offset=-1.0)

    for c in build_front_cutters(col_cut):
        L.boolean(front, c)

    port_cutters, edge_parts = C.build_edges(col_ctrl, col_cut, mats)
    for c in port_cutters:
        L.boolean(front, c)
        L.boolean(back, c)

    for o in (front, back):
        L.shade_smooth(o)
        o.data.materials.append(mats["shell"])

    C.build_wheel(col_ctrl, mats)
    C.build_sync(col_ctrl, mats)
    C.build_dpad(col_ctrl, mats)
    C.build_hslider(col_ctrl, mats)
    C.build_gain(col_ctrl, mats)
    C.build_silkscreen(col_ctrl, mats)

    I.build_pcb(col_int, mats)
    I.build_screen_module(col_int, mats)
    I.build_ui(col_ui, mats)

    # Les cutters ne doivent jamais apparaitre au rendu. On ne touche PAS a
    # hide_viewport : ca les sort du depsgraph et les booleens sautent.
    for o in col_cut.objects:
        o.hide_render = True
        o.display_type = "WIRE"

    deps = bpy.context.evaluated_depsgraph_get()
    for o in (front, back):
        (x0, x1), (y0, y1), (z0, z1) = bbox_world(o, deps)
        print(f"[bbox] {o.name}: X={x1 - x0:.3f} Y={y0:+.3f}..{y1:+.3f} "
              f"Z={z1 - z0:.3f}")

    tris = sum(len(o.evaluated_get(deps).data.loop_triangles)
               for o in bpy.data.objects
               if o.type == "MESH" and not o.hide_render
               and o.evaluated_get(deps).data.loop_triangles is not None
               or False)
    print(f"[stats] objets rendus : "
          f"{len([o for o in bpy.data.objects if o.type == 'MESH' and not o.hide_render])}")

    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    print(f"[ok] -> {OUT_BLEND}")


if __name__ == "__main__":
    main()
