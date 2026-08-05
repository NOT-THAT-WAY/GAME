# Essai Kimi K3 — k3-transparent-audio-deck-git-v002

Objectif : Rebuild the transparent cassette-inspired audio deck from the supplied hero image using the permanent img2threejs clone, then produce a supported Blender asset, multi-angle gates, an 8-second camera preview, and a validated GLB without claiming unseen-side accuracy.

Ce dossier est autonome. Le `.blend` source reste immuable ; la seule scène sauvegardée doit
être `scene/trial.blend`. Commencer par compléter `brief.json` et `scene-contract.json`, puis :

```bash
python3 workflows/tools/validate_kimi_scene_trial.py \
  projects/kimi-k3-scene-trials/k3-transparent-audio-deck-git-v002 --stage scaffold
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

Avant de conclure, appliquer `knowledge/SCENE_TRIAL_EVALUATION_RULES.md`. Le validateur de package
contrôle la complétude ; il ne transforme pas automatiquement les mesures en vérité physique. Le
fichier `diagnostics/physical-validation.json` v2 doit mesurer les meshes évalués et le support réel.
