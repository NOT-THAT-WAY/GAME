# Essai Kimi K3 — k3-edge-rise-reveal-kimi-v001

Objectif : Le Reveil du Bord : assis sur le bord, le personnage se leve, marche vers le centre et contemple les ecrans, en un seul plan continu de l'intime vers le vaste

Ce dossier est autonome. Le `.blend` source reste immuable ; la seule scène sauvegardée doit
être `scene/trial.blend`. Commencer par compléter `brief.json` et `scene-contract.json`, puis :

```bash
python3 workflows/tools/validate_kimi_scene_trial.py \
  projects/kimi-k3-scene-trials/k3-edge-rise-reveal-kimi-v001 --stage scaffold
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
