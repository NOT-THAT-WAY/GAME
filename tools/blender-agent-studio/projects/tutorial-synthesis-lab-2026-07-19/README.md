# Tutorial Synthesis Lab — 19 juillet 2026

Campagne Blender progressive construite de manière autonome à partir des six tutoriels
ingérés et des assets DRUMBOII existants. Aucun asset source ni projet Pulsed n'a été
écrasé.

## Résultat rapide

- [Preview finale](final-preview.mp4) — 10 s, 240 frames, 24 fps;
- [Contact sheet finale](final-preview-contact-sheet.jpg);
- [Vue des six étapes](development-overview.jpg);
- [Scène finale Blender](stages/06-final-multishot/06-final-multishot.blend);
- [Journal complet](PRODUCTION_JOURNAL.md);
- [Rapport de validation](validation-report.json).

## Progression

| Étape | Ajout principal | Contrôle visuel |
|---|---|---|
| 01 | Blob Speaker, clay, mouvement objet | [contact sheet](stages/01-clay-object-motion/contact-sheet.jpg) |
| 02 | rig caméra K1–K4, target retardée, focus | [contact sheet](stages/02-camera-language/contact-sheet.jpg) |
| 03 | texture procédurale, roughness, néons | [contact sheet](stages/03-procedural-lookdev/contact-sheet.jpg) |
| 04 | GAMEBOII, convoyeur, transport + impact | [contact sheet](stages/04-mechanical-choreography/contact-sheet.jpg) |
| 05 | Blob Bike, route, arches, environnement | [contact sheet](stages/05-environment-shot/contact-sheet.jpg) |
| 06 | trois shots et changements de caméra | [contact sheet](stages/06-final-multishot/contact-sheet.jpg) |

Chaque dossier contient son `.blend`, ses snapshots PNG et son `manifest.json`.

## Reproduction

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background --factory-startup \
  --python workflows/tools/create_tutorial_synthesis_campaign.py \
  -- --stage 6

python3 workflows/tools/validate_tutorial_synthesis_campaign.py
```

Les stages acceptés vont de `1` à `6`. Le builder recharge toujours les collections depuis
`asset_library/imported/drumboii-y2k-assets.blend`.
