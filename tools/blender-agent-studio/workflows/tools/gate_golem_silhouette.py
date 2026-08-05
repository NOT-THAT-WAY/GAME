"""Gate de silhouette : compare le golem construit à la silhouette réellement
présente dans le turnaround, au lieu de relevés au pixel faits à l'œil.

Exécution dans Blender (MCP ou console) :

    blender --background projects/golem-de-gres/scene/golem.blend --python workflows/tools/gate_golem_silhouette.py

Côté référence : segmentation de la vue de face par luminance, avec filtre de
longueur de plage pour ignorer la trame et le cadre (traits de 1 à 3 px).
Côté modèle : silhouette orthographique obtenue par raycast, donc exacte, bras
et jambes compris.

Les deux profils sont normalisés par la hauteur du personnage, ce qui rend la
comparaison indépendante de l'échelle du panneau.
"""

import os
from pathlib import Path

import numpy as np

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = os.environ.get("GOLEM_REFERENCE", str(ROOT / "projects" / "golem-de-gres" / "reference" / "golem-de-gres-turnaround.png"))
if not Path(REFERENCE).is_file():
    raise RuntimeError("Référence golem absente; définir GOLEM_REFERENCE ou ajouter projects/golem-de-gres/reference/golem-de-gres-turnaround.png")
PREFIX = "K3_GOLEMGRES_"

# Vue de face : quart supérieur gauche de la planche, marges rentrées pour
# exclure le cadre du panneau et le cartouche "Vue de Face".
PANEL = {"x0": 60, "x1": 945, "y0": 170, "y1": 845}
LUMA_MAX = 0.84
MIN_RUN = 8          # px : un trait de trame ne fait jamais 8 px de large
ERODE = 3            # rayon : supprime tout trait de moins de 7 px d'épaisseur
ROWS = 40            # nombre de tranches comparées


def erode_axis(mask, radius, axis):
    out = mask.copy()
    for k in range(1, radius + 1):
        out &= np.roll(mask, k, axis=axis)
        out &= np.roll(mask, -k, axis=axis)
    return out


def reference_profile():
    img = bpy.data.images.load(REFERENCE, check_existing=True)
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    px = buf.reshape(h, w, 4)[::-1]  # Blender stocke de bas en haut

    region = px[PANEL["y0"]:PANEL["y1"], PANEL["x0"]:PANEL["x1"], :3]
    luma = region @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    mask = luma < LUMA_MAX
    # Le cadre du panneau et la trame sont des traits fins : une érosion 2D les
    # efface sans entamer une masse aussi large que le personnage.
    mask = erode_axis(erode_axis(mask, ERODE, 0), ERODE, 1)

    rows = []
    for y in range(mask.shape[0]):
        xs = np.flatnonzero(mask[y])
        if xs.size == 0:
            rows.append(None)
            continue
        # Plages contiguës ; on ne garde que celles assez larges pour être le corps.
        splits = np.split(xs, np.flatnonzero(np.diff(xs) > 1) + 1)
        runs = [(int(s[0]), int(s[-1])) for s in splits if s.size >= MIN_RUN]
        rows.append(runs if runs else None)

    filled = [(y, r) for y, r in enumerate(rows) if r is not None]
    if not filled:
        raise RuntimeError("Aucune silhouette détectée dans le panneau de face")

    top = filled[0][0]
    bottom = filled[-1][0]
    height = bottom - top
    # Centre pris sur les extrêmes (bras symétriques), pas sur la moyenne des
    # milieux de ligne, qui dérive dès qu'une ligne est asymétrique.
    centre = 0.5 * (min(r[0][0] for _, r in filled) + max(r[-1][1] for _, r in filled))

    profile = {}
    for i in range(ROWS + 1):
        t = i / ROWS  # 0 = pieds, 1 = sommet
        y = int(round(bottom - t * height))
        r = rows[y] if 0 <= y < len(rows) else None
        if r is None:
            continue
        profile[round(t, 4)] = [((a - centre) / height, (b - centre) / height)
                                for a, b in r]
    meta = {"top_px": top, "bottom_px": bottom, "height_px": height,
            "centre_px": round(float(centre), 1),
            "largeur_max_px": max(r[-1][1] - r[0][0] for _, r in filled)}
    # Contrôle de plausibilité : le perso doit occuper l'essentiel du panneau sans
    # le saturer, sinon c'est que le cadre ou la trame est encore dans le masque.
    span = PANEL["x1"] - PANEL["x0"]
    if height > 0.97 * (PANEL["y1"] - PANEL["y0"]) or meta["largeur_max_px"] > 0.95 * span:
        raise RuntimeError("Segmentation suspecte, cadre probablement inclus : %s" % meta)
    return profile, meta


def model_profile():
    parts = [o for o in bpy.data.objects
             if o.name.startswith(PREFIX) and o.type == 'MESH'
             and not o.name.endswith("GROUND")]
    if not parts:
        raise RuntimeError("Aucune pièce du golem dans la scène")

    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for o in parts:
        for c in o.bound_box:
            p = o.matrix_world @ Vector(c)
            for k in range(3):
                lo[k] = min(lo[k], p[k])
                hi[k] = max(hi[k], p[k])
    height = hi.z - lo.z

    def extreme_x(z):
        """Silhouette orthographique : extrême en x sur toute la profondeur."""
        xmin, xmax = None, None
        ys = np.linspace(lo.y - 0.01, hi.y + 0.01, 24)
        for o in parts:
            inv = o.matrix_world.inverted()
            rot = inv.to_3x3()
            for y in ys:
                for sign in (1, -1):
                    origin = Vector((sign * 3.0, float(y), z))
                    direction = Vector((-sign, 0.0, 0.0))
                    ok, loc, _, _ = o.ray_cast(inv @ origin, rot @ direction, distance=6.0)
                    if not ok:
                        continue
                    x = (o.matrix_world @ loc).x
                    xmin = x if xmin is None else min(xmin, x)
                    xmax = x if xmax is None else max(xmax, x)
        return xmin, xmax

    profile = {}
    for i in range(ROWS + 1):
        t = i / ROWS
        z = lo.z + t * height
        # 2 mm de garde : à z exactement sur la semelle ou le sommet, le rayon
        # rase la surface et ne renvoie qu'un point.
        z = min(max(z, lo.z + 0.002), hi.z - 0.002)
        xmin, xmax = extreme_x(z)
        if xmin is None:
            continue
        profile[round(t, 4)] = (xmin / height, xmax / height)
    return profile, {"height_m": height, "min": list(lo), "max": list(hi)}


def reference_eyes(meta):
    """Yeux = pixels quasi noirs, cherchés uniquement dans le crâne. Sans cette
    restriction le trait de contour du personnage, presque aussi sombre, domine."""
    img = bpy.data.images.load(REFERENCE, check_existing=True)
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    px = buf.reshape(h, w, 4)[::-1]

    region = px[PANEL["y0"]:PANEL["y1"], PANEL["x0"]:PANEL["x1"], :3]
    luma = region @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    dark = luma < 0.25

    H, bottom, centre = meta["height_px"], meta["bottom_px"], meta["centre_px"]
    window = np.zeros_like(dark)
    y_hi = int(bottom - 0.92 * H)
    y_lo = int(bottom - 0.72 * H)
    x_lo = int(centre - 0.20 * H)
    x_hi = int(centre + 0.20 * H)
    window[max(y_hi, 0):y_lo, max(x_lo, 0):x_hi] = True
    dark &= window

    ys, xs = np.nonzero(dark)
    if ys.size == 0:
        return None
    out = {}
    for label, sel in (("gauche", xs < centre), ("droit", xs >= centre)):
        if not sel.any():
            continue
        bx, by = xs[sel], ys[sel]
        out[label] = {"cx": float(bx.mean()), "cy": float(by.mean()),
                      "diam_x": int(bx.max() - bx.min() + 1),
                      "diam_y": int(by.max() - by.min() + 1)}
    return out if len(out) == 2 else None


def run():
    ref, ref_meta = reference_profile()
    mod, mod_meta = model_profile()
    print("REF ", ref_meta)
    print("MODEL", {k: (round(v, 4) if isinstance(v, float) else [round(x, 4) for x in v])
                    for k, v in mod_meta.items()})
    eyes = reference_eyes(ref_meta)
    if eyes:
        H = ref_meta["height_px"]
        bottom, centre = ref_meta["bottom_px"], ref_meta["centre_px"]
        g, d = eyes["gauche"], eyes["droit"]
        print()
        print("Yeux de la reference, normalises par la hauteur du personnage :")
        print("  rayon      = %.4f  (moyenne des deux, sur diam_x)"
              % ((g["diam_x"] + d["diam_x"]) / 4.0 / H))
        print("  ecart 1/2  = %.4f  (|x| moyen depuis l'axe)"
              % ((abs(g["cx"] - centre) + abs(d["cx"] - centre)) / 2.0 / H))
        print("  hauteur z  = %.4f" % ((bottom - (g["cy"] + d["cy"]) / 2.0) / H))
        print("  diam px    = %d / %d" % (g["diam_x"], d["diam_x"]))

    print()
    print("Structure de la reference (plages par tranche, en fraction de hauteur)")
    print("  t     n   demi-corps   bras ext.   detail")
    for t in sorted(ref, reverse=True):
        runs = ref[t]
        if len(runs) >= 3:
            body = max(abs(runs[len(runs) // 2][0]), abs(runs[len(runs) // 2][1]))
            arm = max(abs(runs[0][0]), abs(runs[-1][1]))
        else:
            body = max(abs(runs[0][0]), abs(runs[-1][1]))
            arm = float("nan")
        detail = " ".join("[%+.3f %+.3f]" % r for r in runs)
        print(" %.3f  %d   %.4f      %s   %s"
              % (t, len(runs), body, "%.4f" % arm if arm == arm else "  -   ", detail))

    print()
    print("  t     silhouette ref   modele   ecart")
    worst = []
    for t in sorted(set(ref) & set(mod), reverse=True):
        rl = ref[t][0][0]
        rr = ref[t][-1][1]
        ml, mr = mod[t]
        rw = (rr - rl) * 0.5
        mw = (mr - ml) * 0.5
        d = (mw - rw) / rw * 100 if rw > 1e-6 else 0.0
        flag = "  <<<" if abs(d) > 12 else ""
        print(" %.3f      %.4f      %.4f   %+6.1f%%%s" % (t, rw, mw, d, flag))
        worst.append((abs(d), t, d))
    worst.sort(reverse=True)
    print()
    print("Pires ecarts :", [(t, "%+.1f%%" % d) for _, t, d in worst[:5]])
    return ref, mod


REF, MOD = run()
