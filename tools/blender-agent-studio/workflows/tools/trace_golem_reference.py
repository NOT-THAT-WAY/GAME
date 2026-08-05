"""Calque du golem : extrait un spec complet depuis le turnaround, sans relevé
manuel. C'est la source d'autorité des formes ; le builder ne fait que la suivre.

Exécution dans Blender (pour numpy et le chargement d'image) :

    GOLEM_REFERENCE=/path/to/turnaround.png blender --background --factory-startup --python workflows/tools/trace_golem_reference.py

Ce qui est réellement tracé :
  - vue de face  -> demi-largeurs du corps, ligne moyenne et demi-largeur des bras,
                    position et largeur des jambes, taille/écart/hauteur des yeux ;
  - vue de profil -> profondeurs avant et arrière du corps, mesurées séparément
                    (la tête avance plus qu'elle ne recule).

Ce qui reste posé à la main, faute de donnée séparable dans la planche :
  - la profondeur des bras : de profil, le bras est dessiné à l'intérieur du
    contour du corps, donc sa profondeur n'est pas mesurable. Elle est déduite de
    sa largeur par ARM_DEPTH_RATIO.

Sortie : projects/golem-de-gres/golem-trace.json
"""

import json
import os
from pathlib import Path

import numpy as np

import bpy

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = os.environ.get("GOLEM_REFERENCE", str(ROOT / "projects" / "golem-de-gres" / "reference" / "golem-de-gres-turnaround.png"))
OUTPUT = str(ROOT / "projects" / "golem-de-gres" / "golem-trace.json")
if not Path(REFERENCE).is_file():
    raise RuntimeError("Référence golem absente; définir GOLEM_REFERENCE ou ajouter projects/golem-de-gres/reference/golem-de-gres-turnaround.png")

# Bornes en pixels de l'image d'origine (2048 x 2064), pas de son affichage.
# La vue de face est suivie d'une ombre portée : y1 s'arrête aux pieds.
# Chaque panneau est normalisé par SA propre hauteur de personnage : la planche
# dessine le profil environ 8 % plus grand que la face, et cette normalisation
# garde chaque vue cohérente avec elle-même.
PANELS = {
    "front": {"x0": 60, "x1": 945, "y0": 170, "y1": 845},
    "side": {"x0": 60, "x1": 945, "y0": 955, "y1": 1700},
}

LUMA_MAX = 0.84
DARK_MAX = 0.25
MIN_RUN = 8
ERODE = 3
SAMPLES = 64
ARM_DEPTH_RATIO = 1.08   # non mesurable sur la planche, cf. docstring


def _pixels():
    img = bpy.data.images.load(REFERENCE, check_existing=True)
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    return buf.reshape(h, w, 4)[::-1]


def erode_axis(mask, radius, axis):
    out = mask.copy()
    for k in range(1, radius + 1):
        out &= np.roll(mask, k, axis=axis)
        out &= np.roll(mask, -k, axis=axis)
    return out


def extract(px, panel):
    """Renvoie, par ligne, les plages occupées par le personnage, plus ses bornes."""
    region = px[panel["y0"]:panel["y1"], panel["x0"]:panel["x1"], :3]
    luma = region @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    mask = erode_axis(erode_axis(luma < LUMA_MAX, ERODE, 0), ERODE, 1)

    rows = []
    for y in range(mask.shape[0]):
        xs = np.flatnonzero(mask[y])
        if xs.size == 0:
            rows.append(None)
            continue
        splits = np.split(xs, np.flatnonzero(np.diff(xs) > 1) + 1)
        runs = [(int(s[0]), int(s[-1])) for s in splits if s.size >= MIN_RUN]
        rows.append(runs or None)

    filled = [(y, r) for y, r in enumerate(rows) if r is not None]
    if not filled:
        raise RuntimeError("Panneau vide : %s" % panel)
    top, bottom = filled[0][0], filled[-1][0]
    height = bottom - top
    centre = 0.5 * (min(r[0][0] for _, r in filled) + max(r[-1][1] for _, r in filled))

    if height < 0.5 * (panel["y1"] - panel["y0"]):
        raise RuntimeError("Silhouette trop courte, panneau mal cadré : %s" % panel)
    return rows, {"top": top, "bottom": bottom, "height": height, "centre": centre}


def sample(rows, meta, t):
    """Plages à la hauteur t (0 = pieds, 1 = sommet), en fraction de hauteur."""
    y = int(round(meta["bottom"] - t * meta["height"]))
    if not (0 <= y < len(rows)) or rows[y] is None:
        return None
    return [((a - meta["centre"]) / meta["height"],
             (b - meta["centre"]) / meta["height"]) for a, b in rows[y]]


def trace_eyes(px, meta):
    panel = PANELS["front"]
    region = px[panel["y0"]:panel["y1"], panel["x0"]:panel["x1"], :3]
    luma = region @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    dark = luma < DARK_MAX

    H, bottom, centre = meta["height"], meta["bottom"], meta["centre"]
    window = np.zeros_like(dark)
    window[max(int(bottom - 0.92 * H), 0):int(bottom - 0.72 * H),
           max(int(centre - 0.20 * H), 0):int(centre + 0.20 * H)] = True
    dark &= window

    ys, xs = np.nonzero(dark)
    if ys.size == 0:
        raise RuntimeError("Yeux introuvables")
    sides = []
    for sel in (xs < centre, xs >= centre):
        bx, by = xs[sel], ys[sel]
        sides.append({"x": abs(float(bx.mean()) - centre) / H,
                      "z": (bottom - float(by.mean())) / H,
                      "r": (float(bx.max() - bx.min() + 1) * 0.5) / H})
    return {k: round(sum(s[k] for s in sides) / 2.0, 5) for k in ("x", "z", "r")}


def find_arm_start(front_rows, front_meta):
    """Le bras rejoint la silhouette là où le contour s'élargit brutalement : la
    pente y dépasse largement celle du crâne juste au-dessus."""
    ts = [1.0 - i / SAMPLES for i in range(SAMPLES + 1)]
    widths = []
    for t in ts:
        runs = sample(front_rows, front_meta, t)
        widths.append(None if runs is None else (runs[-1][1] - runs[0][0]) * 0.5)

    pairs = [(t, w) for t, w in zip(ts, widths) if w is not None]
    for i in range(4, len(pairs) - 1):
        recent = [pairs[k][1] - pairs[k - 1][1] for k in range(max(1, i - 3), i)]
        base = sum(recent) / len(recent)
        step = pairs[i][1] - pairs[i - 1][1]
        if base > 1e-6 and step > 2.0 * base:
            return pairs[i][0]
    return 0.72


def trace():
    px = _pixels()
    front_rows, front_meta = extract(px, PANELS["front"])
    side_rows, side_meta = extract(px, PANELS["side"])
    print("FRONT", front_meta)
    print("SIDE ", side_meta)

    arm_start = find_arm_start(front_rows, front_meta)
    print("Depart des bras detecte a t =", arm_start)

    # Première passe : repérer la bande où bras et corps sont séparés de face.
    arm_low = None
    for i in range(SAMPLES + 1):
        t = i / SAMPLES
        f = sample(front_rows, front_meta, t)
        if f is not None and len(f) >= 3:
            arm_low = t if arm_low is None else min(arm_low, t)
    if arm_low is None:
        raise RuntimeError("Bras jamais separes du corps : cadrage a revoir")

    body, arm, legs = [], [], []
    for i in range(SAMPLES + 1):
        t = i / SAMPLES
        f = sample(front_rows, front_meta, t)
        s = sample(side_rows, side_meta, t)
        if f is None:
            continue

        if len(f) >= 3:
            mid = f[len(f) // 2]
            body_half = (mid[1] - mid[0]) * 0.5
            outer_l, outer_r = f[0], f[-1]
            arm.append({
                "t": round(t, 5),
                "centre": round((abs((outer_l[0] + outer_l[1]) * 0.5)
                                 + (outer_r[0] + outer_r[1]) * 0.5) * 0.5, 5),
                "half": round(((outer_l[1] - outer_l[0])
                               + (outer_r[1] - outer_r[0])) * 0.25, 5),
            })
        elif len(f) == 2 and t < 0.30:
            left, right = f[0], f[1]
            legs.append({
                "t": round(t, 5),
                "centre": round((abs((left[0] + left[1]) * 0.5)
                                 + (right[0] + right[1]) * 0.5) * 0.5, 5),
                "half": round(((left[1] - left[0]) + (right[1] - right[0])) * 0.25, 5),
            })
            body_half = None
        else:
            # Une seule plage : c'est le corps seul, soit au-dessus des bras (le
            # crâne), soit sous eux (le ventre qui ponte les jambes). Entre les
            # deux, la plage est le bord externe du bras et ne dit rien du corps.
            solo = t >= arm_start or t < arm_low
            body_half = (f[-1][1] - f[0][0]) * 0.5 if solo else None

        depth_front = depth_back = None
        if s is not None:
            # Panneau "Profil Gauche" : le personnage regarde vers les x croissants,
            # donc +x du panneau = avant du personnage = -Y dans Blender.
            depth_front = abs(s[-1][1])
            depth_back = abs(s[0][0])

        if body_half is not None:
            body.append({"t": round(t, 5), "half": round(body_half, 5),
                         "front": round(depth_front, 5) if depth_front else None,
                         "back": round(depth_back, 5) if depth_back else None})

    # Bande où les bras masquent le corps de face : on relie la dernière mesure
    # nette du tronc à la base du crâne. Le corps y est de toute façon caché.
    known = [b for b in body if b["t"] < arm_start or b["t"] >= arm_start]
    lo = max([b for b in body if b["t"] < 0.35], key=lambda b: b["t"], default=None)
    hi = min([b for b in body if b["t"] >= arm_start], key=lambda b: b["t"], default=None)
    if lo and hi:
        for i in range(SAMPLES + 1):
            t = i / SAMPLES
            if not (lo["t"] < t < hi["t"]):
                continue
            if any(abs(b["t"] - t) < 1e-6 for b in body):
                continue
            f = (t - lo["t"]) / (hi["t"] - lo["t"])
            s = sample(side_rows, side_meta, t)
            body.append({
                "t": round(t, 5),
                "half": round(lo["half"] + (hi["half"] - lo["half"]) * f, 5),
                "front": round(abs(s[-1][1]), 5) if s else None,
                "back": round(abs(s[0][0]), 5) if s else None,
            })
    body.sort(key=lambda b: b["t"])
    body = [b for b in body if b["front"] is not None]

    # Contour extérieur brut de la vue de face, toutes tranches confondues : dans
    # la bande où le bras se confond avec le corps, c'est le bord externe du bras,
    # donc la seule mesure disponible pour remonter la ligne du bras jusqu'à l'épaule.
    outline, depth = [], []
    for i in range(SAMPLES + 1):
        t = i / SAMPLES
        f = sample(front_rows, front_meta, t)
        if f is not None:
            outline.append({"t": round(t, 5),
                            "half": round((f[-1][1] - f[0][0]) * 0.5, 5)})
        s = sample(side_rows, side_meta, t)
        if s is not None:
            depth.append({"t": round(t, 5),
                          "front": round(abs(s[-1][1]), 5),
                          "back": round(abs(s[0][0]), 5)})

    spec = {
        "source": REFERENCE,
        "unit": "fraction de la hauteur du personnage (hauteur = 1.0)",
        "arm_start_t": round(arm_start, 5),
        "arm_depth_ratio": ARM_DEPTH_RATIO,
        "body": body,
        "outline": outline,
        "depth": depth,
        "arm": arm,
        "legs": legs,
        "eyes": trace_eyes(px, front_meta),
    }

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as fh:
        json.dump(spec, fh, indent=2)

    print("\nCorps : %d tranches, de t=%.3f a t=%.3f"
          % (len(body), body[0]["t"], body[-1]["t"]))
    print("Bras  : %d tranches, de t=%.3f a t=%.3f"
          % (len(arm), arm[0]["t"], arm[-1]["t"]) if arm else "Bras  : aucun")
    print("Jambes: %d tranches" % len(legs))
    print("Yeux  :", spec["eyes"])
    print("Ecrit ->", OUTPUT)
    return spec


SPEC = trace()
