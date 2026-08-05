"""Gate lumiere Drumboiii — appelle le script versionne du depot.

workflows/scripts/drumboiii_lighting_gate.py rend la base monde puis chaque
couche CUMULATIVEMENT (6 images), ce qui est la seule facon de juger l'apport
reel d'une lampe. On ne le reecrit pas.

  blender -b scene/trial.blend --python run_lighting_gate.py
"""

import json
import os

import bpy

TRIAL_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(TRIAL_DIR, "..", "..", ".."))
SCRIPT = os.path.join(REPO, "workflows", "scripts", "drumboiii_lighting_gate.py")
OUT = os.path.join(TRIAL_DIR, "gates", "lighting")

g = {
    "__name__": "__main__",
    "UNRECORDED_PARAMS": {
        "output_dir": OUT,
        "frame": 120,               # pose hero K3 : la lumiere doit y tenir
        "resolution_percentage": 60,
        "samples": 40,
    },
}
with open(SCRIPT) as fh:
    exec(compile(fh.read(), SCRIPT, "exec"), g)

# Le manifeste attendu par le validateur vit dans gates/, avec des chemins
# relatifs au dossier d'essai.
src = os.path.join(OUT, "lighting-gate-manifest.json")
with open(src) as fh:
    manifest = json.load(fh)
for item in manifest.get("renders", []):
    item["path"] = os.path.relpath(item["path"], TRIAL_DIR)
manifest["trial_id"] = "k3-pulsed-bench-demo-v001"
manifest["layer_functions"] = {
    "SUN_REFLECTION": "soleil oblique : dessine les reflets sur la coque translucide",
    "BACK_SHAPE": "backlight dominant : separe le volume du fond et allume la tranche",
    "SIDE_GLIMMER_A": "glimmer cote molette : revele les deux domes violets",
    "SIDE_GLIMMER_B": "glimmer cote D-pad : rend lisibles les fleches embossees",
    "DETAIL_RETURN": "retour frontal faible : redonne le PCB sous la coque",
}
dst = os.path.join(TRIAL_DIR, "gates", "lighting-gate-manifest.json")
with open(dst, "w") as fh:
    json.dump(manifest, fh, ensure_ascii=False, indent=2)
print(f"[gate] {len(manifest.get('renders', []))} rendus -> {dst}")
