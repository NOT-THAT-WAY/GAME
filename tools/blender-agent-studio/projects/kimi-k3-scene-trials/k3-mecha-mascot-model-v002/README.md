# Essai Kimi K3 — k3-mecha-mascot-model-v002

Objectif : Reconstruire Mecha Mascot avec des jambes plus longues, plus fines et presque parallèles selon la nouvelle planche de poses, sans écraser la V1.

Ce dossier est autonome. Le `.blend` source reste immuable ; la seule scène sauvegardée doit
être `scene/trial.blend`. Commencer par compléter `brief.json` et `scene-contract.json`, puis :

```bash
python3 workflows/tools/validate_kimi_scene_trial.py \
  projects/kimi-k3-scene-trials/k3-mecha-mascot-model-v002 --stage scaffold
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

- `asset_library/characters/mecha-mascot-v002.blend` — V2 corrigée ;
- `asset_library/characters/mecha-mascot-v002.glb` — export portable validé ;
- `gates/v1-v2-comparison.jpg` — comparaison directe des proportions.
