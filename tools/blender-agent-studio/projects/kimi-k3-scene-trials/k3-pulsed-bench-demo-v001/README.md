# Essai Kimi K3 — k3-pulsed-bench-demo-v001

Objectif : Mini demo fonctionnelle de Pulsed pose sur un socle : molette, sliders et D-pad s'animent, l'ecran repond aux controles.

Ce dossier est autonome. Le `.blend` source reste immuable ; la seule scène sauvegardée doit
être `scene/trial.blend`. Commencer par compléter `brief.json` et `scene-contract.json`, puis :

```bash
python3 workflows/tools/validate_kimi_scene_trial.py \
  projects/kimi-k3-scene-trials/k3-pulsed-bench-demo-v001 --stage scaffold
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
