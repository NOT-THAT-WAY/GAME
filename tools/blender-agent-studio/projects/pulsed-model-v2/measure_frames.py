"""Mesure numerique des frames de reference Pulse.

Segmente la coque violette par (B - G) > seuil : l'ombre portee est neutre
(B-G ~ -9 sur le fond creme) donc elle sort du masque toute seule. C'est la
correction de l'erreur v1 ou l'ombre entrait dans la bbox.

Lancer avec le python de Blender (numpy embarque) :
  /Applications/Blender.app/Contents/Resources/5.1/python/bin/python3.13 measure_frames.py
"""

import glob
import json
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
PURPLE_THRESHOLD = 10
MIN_RUN = 4  # pixels violets minimum sur une ligne/colonne pour la compter


def load_rgb(path):
    """Decode une image via ffmpeg en RGB brut (pas de PIL dispo)."""
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", path],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    w, h = (int(v) for v in probe.split("x"))
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo",
         "-pix_fmt", "rgb24", "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3).astype(np.int16)


def purple_bbox(img):
    """bbox de la coque violette, ombre exclue."""
    mask = (img[:, :, 2] - img[:, :, 1]) > PURPLE_THRESHOLD
    rows = mask.sum(axis=1) >= MIN_RUN
    cols = mask.sum(axis=0) >= MIN_RUN
    if not rows.any() or not cols.any():
        return None
    y0, y1 = np.flatnonzero(rows)[[0, -1]]
    x0, x1 = np.flatnonzero(cols)[[0, -1]]
    h, w = img.shape[:2]
    return {
        "x0": int(x0), "x1": int(x1), "y0": int(y0), "y1": int(y1),
        "w": int(x1 - x0 + 1), "h": int(y1 - y0 + 1),
        "ratio": round((x1 - x0 + 1) / (y1 - y0 + 1), 4),
        "area_frac": round(float(mask.sum()) / (w * h), 4),
        "touches_edge": bool(x0 == 0 or y0 == 0 or x1 == w - 1 or y1 == h - 1),
    }


def main():
    report = {}
    for slug in sorted(os.listdir(os.path.join(ROOT, "frames"))):
        d = os.path.join(ROOT, "frames", slug)
        if not os.path.isdir(d):
            continue
        entries = []
        for f in sorted(glob.glob(os.path.join(d, "f_*.jpg"))):
            bb = purple_bbox(load_rgb(f))
            if bb:
                bb["frame"] = os.path.basename(f)
                entries.append(bb)
        report[slug] = entries
        # Les vues entieres (objet non croppe) : celles qui ne touchent pas le bord.
        whole = [e for e in entries if not e["touches_edge"]]
        print(f"\n=== {slug} : {len(entries)} frames, {len(whole)} vues entieres ===")
        for e in whole:
            print(f"  {e['frame']}  {e['w']:4d}x{e['h']:4d}  ratio={e['ratio']:.3f}  "
                  f"aire={e['area_frac']:.3f}")
        if whole:
            widest = max(whole, key=lambda e: e["w"])
            narrowest = min(whole, key=lambda e: e["w"])
            print(f"  -> plus large (face/dos le plus frontal) : {widest['frame']} "
                  f"ratio={widest['ratio']:.3f}")
            print(f"  -> plus etroite (profil)                 : {narrowest['frame']} "
                  f"w={narrowest['w']}")

    out = os.path.join(ROOT, "audits", "frame-measurements.json")
    with open(out, "w") as fh:
        json.dump(report, fh, indent=1)
    print(f"\n-> {out}")


if __name__ == "__main__":
    sys.exit(main())
