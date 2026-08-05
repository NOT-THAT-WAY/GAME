"""Bitmap -> geometrie embossee, pour le logo et le wordmark.

Une police systeme ne reproduira jamais le glyphe UNRECORDED. On trace donc le
bitmap : marching squares -> contours fermes -> courbe Blender (une spline par
contour, trous compris) -> extrusion. Blender remplit les courbes en regle
pair-impair, donc les contre-formes du « u » se creusent toutes seules.

Reutilisable tel quel pour le wordmark « Pulsed ».
"""

import os
import subprocess

import bpy
import numpy as np

import pulsed_lib as L


# --- Lecture et binarisation ------------------------------------------------

def load_gray(path):
    wh = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", path],
        capture_output=True, text=True, check=True).stdout.strip()
    w, h = (int(v) for v in wh.split("x"))
    # On lit en RGBA et on aplatit sur blanc DANS NUMPY.
    # Surtout pas via un filtre `color=` : c'est une source infinie, elle
    # remplit le pipe sans fin et le process se fait tuer (exit 137).
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-frames:v", "1",
         "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
        capture_output=True, check=True).stdout
    rgba = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 4).astype(np.float32)
    alpha = rgba[:, :, 3:4] / 255.0
    rgb = rgba[:, :, :3] * alpha + 255.0 * (1.0 - alpha)
    gray = rgb[:, :, 0] * 0.299 + rgb[:, :, 1] * 0.587 + rgb[:, :, 2] * 0.114
    return gray.astype(np.int16)


def glyph_mask(gray, threshold=128):
    """True = glyphe. La polarite est deduite du bord de l'image (= fond)."""
    dark = gray < threshold
    border = np.concatenate([dark[0, :], dark[-1, :], dark[:, 0], dark[:, -1]])
    if border.mean() > 0.5:          # bord sombre -> le fond est sombre
        dark = ~dark
    return dark


# --- Marching squares -------------------------------------------------------

_SEGMENTS = {
    1: [("L", "B")], 2: [("B", "R")], 3: [("L", "R")], 4: [("T", "R")],
    5: [("L", "T"), ("B", "R")], 6: [("T", "B")], 7: [("L", "T")],
    8: [("T", "L")], 9: [("T", "B")], 10: [("T", "R"), ("L", "B")],
    11: [("T", "R")], 12: [("L", "R")], 13: [("B", "R")], 14: [("L", "B")],
}


def contours(mask):
    """Contours fermes du masque, en coordonnees pixel (sub-pixel sur les aretes)."""
    m = mask.astype(np.uint8)
    h, w = m.shape
    tl, tr = m[:-1, :-1], m[:-1, 1:]
    bl, br = m[1:, :-1], m[1:, 1:]
    idx = tl * 8 + tr * 4 + br * 2 + bl

    def pt(x, y, side):
        if side == "T":
            return (x + 0.5, float(y))
        if side == "B":
            return (x + 0.5, y + 1.0)
        if side == "L":
            return (float(x), y + 0.5)
        return (x + 1.0, y + 0.5)

    adj = {}
    ys, xs = np.nonzero((idx > 0) & (idx < 15))
    for y, x in zip(ys, xs):
        for a, b in _SEGMENTS[int(idx[y, x])]:
            p, q = pt(x, y, a), pt(x, y, b)
            adj.setdefault(p, []).append(q)
            adj.setdefault(q, []).append(p)

    loops, seen = [], set()
    for start in list(adj):
        if start in seen:
            continue
        loop, cur, prev = [start], start, None
        seen.add(start)
        while True:
            nxt = None
            for cand in adj.get(cur, ()):
                if cand != prev and (cand not in seen or cand == start):
                    nxt = cand
                    break
            if nxt is None or nxt == start:
                break
            loop.append(nxt)
            seen.add(nxt)
            prev, cur = cur, nxt
        if len(loop) >= 8:
            loops.append(loop)
    return loops


# --- Simplification ---------------------------------------------------------

def simplify(points, tol=0.6):
    """Douglas-Peucker iteratif (pas de recursion : certains contours sont longs)."""
    n = len(points)
    if n < 4:
        return points
    pts = np.asarray(points, dtype=float)
    keep = np.zeros(n, dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = pts[i], pts[j]
        ab = b - a
        norm = np.hypot(*ab)
        seg = pts[i + 1:j]
        if norm < 1e-9:
            d = np.hypot(*(seg - a).T)
        else:
            d = np.abs(np.cross(ab, seg - a)) / norm
        k = int(np.argmax(d))
        if d[k] > tol:
            k += i + 1
            keep[k] = True
            stack.append((i, k))
            stack.append((k, j))
    return [tuple(p) for p in pts[keep]]


# --- Construction Blender ---------------------------------------------------

def build(path, name, x, z, width_bu, col, mat, y=None, depth=0.012,
          bevel=0.0, tol=0.6, threshold=128):
    """Cree l'objet embosse a partir du bitmap. Renvoie l'objet mesh."""
    gray = load_gray(path)
    mask = glyph_mask(gray, threshold)
    loops = contours(mask)
    if not loops:
        raise ValueError(f"aucun contour trouve dans {path}")

    ys, xs = np.nonzero(mask)
    x0, x1 = xs.min(), xs.max() + 1
    y0, y1 = ys.min(), ys.max() + 1
    scale = width_bu / (x1 - x0)
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0

    curve = bpy.data.curves.new(f"{name}_curve", "CURVE")
    curve.dimensions = "2D"
    curve.fill_mode = "BOTH"
    curve.extrude = depth / 2.0
    if bevel:
        curve.bevel_depth = bevel
        curve.bevel_resolution = 2

    for loop in loops:
        pts = simplify(loop, tol)
        if len(pts) < 3:
            continue
        spline = curve.splines.new("POLY")
        spline.points.add(len(pts) - 1)
        for i, (px, py) in enumerate(pts):
            # image : y vers le bas · Blender : z vers le haut
            spline.points[i].co = ((px - cx) * scale, -(py - cy) * scale, 0.0, 1.0)
        spline.use_cyclic_u = True

    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.active_object

    # la courbe est construite en XY ; on la redresse dans le plan XZ, face vers -Y
    obj.rotation_euler = (1.5707963, 0.0, 0.0)
    bpy.ops.object.transform_apply(rotation=True)

    L.move(obj, x, y if y is not None else 0.0, z)
    L.link_only(obj, col)
    obj.data.materials.append(mat)
    return obj
