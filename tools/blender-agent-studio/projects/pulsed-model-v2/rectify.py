"""Redressement metrique d'une frame de reference Pulse.

Pourquoi : mesurer des positions en normalisant par la bbox alignee aux axes
d'un objet INCLINE et EN PERSPECTIVE est faux — la bbox d'un rectangle tourne
est plus grande que le rectangle, et la perspective comprime un cote par
rapport a l'autre. C'est le defaut de la carte v3 initiale.

Methode :
  1. masque violet -> contour
  2. angle du rectangle d'aire minimale (calipers en force brute)
  3. les 4 cotes droits sont ajustes par moindres carres totaux, en excluant
     les arcs de coin
  4. intersection des cotes adjacents -> les 4 coins projetes de la FACE
  5. points de fuite -> focale (contrainte d'orthogonalite) -> VRAI ratio W/H
  6. homographie -> image fronto-parallele, ou 1 px = 1/PPBU de BU

Sortie : PNG redresse + JSON avec ratio, focale et coins.

  /Applications/Blender.app/Contents/Resources/5.1/python/bin/python3.13 rectify.py <frame.jpg> <tag>
"""

import json
import math
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
PURPLE_THRESHOLD = 10
PPBU = 100          # pixels par BU dans l'image redressee


# --- I/O --------------------------------------------------------------------

def load_rgb(path):
    wh = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", path],
        capture_output=True, text=True, check=True).stdout.strip()
    w, h = (int(v) for v in wh.split("x"))
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo",
         "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3).astype(np.float64)


def save_rgb(arr, path):
    h, w = arr.shape[:2]
    data = np.clip(arr, 0, 255).astype(np.uint8).tobytes()
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{w}x{h}", "-i", "-", path],
        input=data, check=True)


# --- Contour et cotes -------------------------------------------------------

def purple_mask(img):
    return (img[:, :, 2] - img[:, :, 1]) > PURPLE_THRESHOLD


def boundary_points(mask):
    m = mask
    inner = np.zeros_like(m)
    inner[1:-1, 1:-1] = (m[1:-1, 1:-1] & m[:-2, 1:-1] & m[2:, 1:-1]
                         & m[1:-1, :-2] & m[1:-1, 2:])
    edge = m & ~inner
    ys, xs = np.nonzero(edge)
    return np.stack([xs, ys], axis=1).astype(np.float64)


def min_area_angle(pts):
    """Angle du rectangle englobant d'aire minimale, balayage grossier puis fin."""
    best, best_area = 0.0, None
    for coarse in np.arange(0.0, 90.0, 0.5):
        a = math.radians(coarse)
        c, s = math.cos(a), math.sin(a)
        u = pts[:, 0] * c + pts[:, 1] * s
        v = -pts[:, 0] * s + pts[:, 1] * c
        area = (u.max() - u.min()) * (v.max() - v.min())
        if best_area is None or area < best_area:
            best, best_area = coarse, area
    for fine in np.arange(best - 0.6, best + 0.6, 0.02):
        a = math.radians(fine)
        c, s = math.cos(a), math.sin(a)
        u = pts[:, 0] * c + pts[:, 1] * s
        v = -pts[:, 0] * s + pts[:, 1] * c
        area = (u.max() - u.min()) * (v.max() - v.min())
        if area < best_area:
            best, best_area = fine, area

    # L'objet est en PAYSAGE : l'axe u doit porter la largeur. Sans ca, un
    # angle sorti a ~88 deg intervertit les axes et on mesure H/W.
    a = math.radians(best)
    c, s = math.cos(a), math.sin(a)
    u = pts[:, 0] * c + pts[:, 1] * s
    v = -pts[:, 0] * s + pts[:, 1] * c
    if (v.max() - v.min()) > (u.max() - u.min()):
        best += 90.0
    return math.radians(best)


def fit_line(pts):
    """Moindres carres totaux -> droite homogene (a, b, c) avec a x + b y + c = 0."""
    mean = pts.mean(axis=0)
    d = pts - mean
    _, _, vt = np.linalg.svd(d, full_matrices=False)
    direction = vt[0]
    normal = np.array([-direction[1], direction[0]])
    c = -normal.dot(mean)
    return np.array([normal[0], normal[1], c])


def side_lines(pts, angle, keep=0.55, band=0.16):
    """Ajuste les 4 cotes droits, en jetant les arcs de coin."""
    c, s = math.cos(angle), math.sin(angle)
    u = pts[:, 0] * c + pts[:, 1] * s
    v = -pts[:, 0] * s + pts[:, 1] * c
    u0, u1, v0, v1 = u.min(), u.max(), v.min(), v.max()
    du, dv = u1 - u0, v1 - v0

    lines = {}
    # cotes gauche/droite : selection sur u, centrage sur v
    for name, ref, sel in (("left", u0, u < u0 + band * du),
                           ("right", u1, u > u1 - band * du)):
        mid = (v > v0 + (1 - keep) / 2 * dv) & (v < v1 - (1 - keep) / 2 * dv)
        lines[name] = fit_line(pts[sel & mid])
    for name, ref, sel in (("top", v0, v < v0 + band * dv),
                           ("bottom", v1, v > v1 - band * dv)):
        mid = (u > u0 + (1 - keep) / 2 * du) & (u < u1 - (1 - keep) / 2 * du)
        lines[name] = fit_line(pts[sel & mid])
    return lines


def intersect(l1, l2):
    p = np.cross(l1, l2)
    return p[:2] / p[2]


# --- Ratio metrique ---------------------------------------------------------

def rectangle_ratio(corners, img_shape):
    """Vrai ratio W/H d'un rectangle vu en perspective.

    corners = [TL, TR, BL, BR] en pixels. Principal point suppose au centre,
    pixels carres. La contrainte d'orthogonalite des deux points de fuite
    donne la focale, dont on deduit le ratio.
    """
    h, w = img_shape[:2]
    cx, cy = w / 2.0, h / 2.0

    def hom(p):
        return np.array([p[0] - cx, p[1] - cy, 1.0])

    m1, m2, m3, m4 = (hom(c) for c in corners)   # TL, TR, BL, BR

    k2 = np.cross(m1, m4).dot(m3) / np.cross(m2, m4).dot(m3)
    k3 = np.cross(m1, m4).dot(m2) / np.cross(m3, m4).dot(m2)

    n2 = k2 * m2 - m1
    n3 = k3 * m3 - m1

    denom = n2[2] * n3[2]
    if abs(denom) < 1e-12:
        # vue quasi orthographique : pas de perspective exploitable
        f2 = None
        ratio = np.linalg.norm(n2[:2]) / np.linalg.norm(n3[:2])
        return ratio, None

    f2 = -(n2[0] * n3[0] + n2[1] * n3[1]) / denom
    if f2 <= 0:
        f2 = None
        ratio = np.linalg.norm(n2[:2]) / np.linalg.norm(n3[:2])
        return ratio, None

    f = math.sqrt(f2)
    num = (n2[0] ** 2 + n2[1] ** 2) / f2 + n2[2] ** 2
    den = (n3[0] ** 2 + n3[1] ** 2) / f2 + n3[2] ** 2
    return math.sqrt(num / den), f


# --- Homographie ------------------------------------------------------------

def homography(src, dst):
    A = []
    for (x, y), (X, Y) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -X * x, -X * y, -X])
        A.append([0, 0, 0, x, y, 1, -Y * x, -Y * y, -Y])
    _, _, vt = np.linalg.svd(np.array(A))
    return (vt[-1] / vt[-1][-1]).reshape(3, 3)


def warp(img, H, out_w, out_h):
    Hi = np.linalg.inv(H)
    yy, xx = np.mgrid[0:out_h, 0:out_w]
    ones = np.ones_like(xx)
    P = np.stack([xx, yy, ones], axis=-1).astype(np.float64)
    S = P @ Hi.T
    sx = S[..., 0] / S[..., 2]
    sy = S[..., 1] / S[..., 2]

    h, w = img.shape[:2]
    x0 = np.clip(np.floor(sx).astype(int), 0, w - 2)
    y0 = np.clip(np.floor(sy).astype(int), 0, h - 2)
    fx = np.clip(sx - x0, 0, 1)[..., None]
    fy = np.clip(sy - y0, 0, 1)[..., None]

    out = (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
           + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)
    bad = (sx < 0) | (sx > w - 1) | (sy < 0) | (sy > h - 1)
    out[bad] = 245.0
    return out


def main():
    frame = sys.argv[1]
    tag = sys.argv[2] if len(sys.argv) > 2 else "rect"

    img = load_rgb(frame)
    mask = purple_mask(img)
    pts = boundary_points(mask)
    angle = min_area_angle(pts)
    lines = side_lines(pts, angle)

    tl = intersect(lines["top"], lines["left"])
    tr = intersect(lines["top"], lines["right"])
    bl = intersect(lines["bottom"], lines["left"])
    br = intersect(lines["bottom"], lines["right"])
    corners = [tl, tr, bl, br]

    ratio, focal = rectangle_ratio(corners, img.shape)

    out_w = int(round(16.0 * PPBU))
    out_h = int(round(out_w / ratio))
    dst = [(0, 0), (out_w - 1, 0), (0, out_h - 1), (out_w - 1, out_h - 1)]
    H = homography(corners, dst)
    rect = warp(img, H, out_w, out_h)

    out_dir = os.path.join(ROOT, "audits", "rectified")
    os.makedirs(out_dir, exist_ok=True)
    png = os.path.join(out_dir, f"{tag}.png")
    save_rgb(rect, png)

    meta = {
        "frame": os.path.basename(frame),
        "angle_deg": round(math.degrees(angle), 3),
        "corners_px": {k: [round(float(v[0]), 2), round(float(v[1]), 2)]
                       for k, v in zip(("TL", "TR", "BL", "BR"), corners)},
        "ratio_wh": round(float(ratio), 4),
        "focal_px": round(float(focal), 1) if focal else None,
        "out_size": [out_w, out_h],
        "px_per_bu": PPBU,
    }
    with open(os.path.join(out_dir, f"{tag}.json"), "w") as fh:
        json.dump(meta, fh, indent=1)

    print(json.dumps(meta, indent=1))
    print(f"-> {png}")


if __name__ == "__main__":
    main()
