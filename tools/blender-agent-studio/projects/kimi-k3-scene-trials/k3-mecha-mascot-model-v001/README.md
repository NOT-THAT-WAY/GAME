# Essai Kimi K3 — k3-mecha-mascot-model-v001

Objectif : Créer depuis la référence model 3D mecha.png une mascotte humanoïde organique, manifold, propre et réutilisable dans les futures scènes Blender.

Ce dossier est autonome. Le `.blend` source reste immuable ; la seule scène sauvegardée doit
être `scene/trial.blend`. Commencer par compléter `brief.json` et `scene-contract.json`, puis :

```bash
python3 workflows/tools/validate_kimi_scene_trial.py \
  projects/kimi-k3-scene-trials/k3-mecha-mascot-model-v001 --stage scaffold
```

Arborescence attendue à la fin :

```text
brief.json
scene-contract.json
trial-manifest.json
shot-manifest.json
score.json
FINAL_REVIEW.md
scene/trial.blend
diagnostics/scene-audit.json
diagnostics/physical-validation.json
gates/contact-sheet.jpg
gates/lighting-gate-manifest.json
renders/preview.mp4
iterations/
```

## Asset publié

- `asset_library/characters/mecha-mascot-v001.blend` — collection Asset Browser `Mecha Mascot` ;
- `asset_library/characters/mecha-mascot-v001.glb` — export portable validé par réimport ;
- catalogue : `Characters/Mascots`.
