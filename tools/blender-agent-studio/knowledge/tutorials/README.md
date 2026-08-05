# Tutoriels Lab — contrat d’ingestion et d’analyse

Cet espace transforme une vidéo de formation en connaissance de production vérifiable.
La vidéo originale n’est jamais modifiée.

## Pipeline

```text
source vidéo
→ ffprobe technique
→ frames régulières + changements de plan + contact sheet
→ audio WAV mono 16 kHz
→ transcript SRT/VTT/TXT normalisé
→ analyse IA structurée et sourcée
→ recette Blender reproductible
→ test dans une copie ou une scène non sauvegardée
→ gate visuel
→ promotion éventuelle en workflow ou asset
```

## Structure d’un tutoriel

```text
knowledge/tutorials/<titre>-<id>/
├── source.mp4
├── manifest.json
├── probe.json
├── contact-sheet.jpg
├── audio.wav
├── transcript-source.srt
├── transcript.json
├── frames/
│   ├── regular/
│   └── scenes/
├── ANALYSIS_BRIEF.md
├── analysis.json
└── ANALYSIS.md
```

## Règle de preuve

Une analyse doit distinguer trois niveaux:

- **observé**: visible dans une frame ou énoncé dans le transcript;
- **inféré**: conclusion probable, explicitement marquée comme telle;
- **validé**: reproduit dans Blender et passé par un gate.

Les conseils d’un tutoriel ne deviennent pas automatiquement des standards internes. Ils
doivent être testés avec la version Blender du projet, ses unités, son moteur et ses assets.

## Transcription

Le Studio accepte directement `.srt`, `.vtt`, `.txt` et `.md`. Sans transcript, il prépare
`audio.wav` pour un moteur local ou approuvé. Whisper peut produire le texte et des segments
horodatés; les noms propres Blender doivent être relus avant analyse.

## Promotion en workflow

Une technique n’entre dans `workflows/catalog/` que si elle possède:

1. des entrées typées et bornées;
2. un script idempotent ou un namespace unique;
3. un manifeste de sortie;
4. un mode opératoire visible dans l’app;
5. un gate reproductible;
6. aucun enregistrement silencieux du `.blend`;
7. un test sur une copie ou en background.

## Corpus indexés

| Corpus | Preuve | Savoir principal |
|---|---|---|
| Drumboiii Camera | transcript + frames | anticipation, recovery, target et focus |
| Drumboiii Lighting | transcript + frames + valeurs UI | HDRI retenu, Sun de reflet, backlight et glimmers évalués en A/B |
| Drumboiii HDRI Setup | transcript local + lecture visuelle | séparer HDRI/reflets et ciel caméra, fond Noise + Gradient ajusté à la focale |
| Drumboiii Squishy | transcript local + lecture visuelle | pop de Scale, Lattice en overlap et subdivision finale |
| Drumboiii Chains & Movements | transcript local + valeurs UI relevées | maillon Torus, Array relatif puis Curve, mouvement d'ambiance par déformeurs déphasés d'un quart de période, driver `#frame/fps` en radians |
| Beginner Blender 2026 | transcript + frames | modélisation, UV, matières, scatter, lumière |
| Ray-Ban Product Animation | transcript + frames | reveal d'assemblage multi-pièces |
| Factory Animation | transcript + frames | convoyeur Array/Curve et boucle exacte |
| Quick Animation Blender 4 | frames uniquement | asset automobile dans un environnement |
| Wireless Pods Animation | transcript + frames | charnière, parenting et cascade produit |

La méthode croisée est maintenue dans `ANIMATION_WORKFLOW_PLAYBOOK.md`. Le corpus Quick
Animation ne possède pas de narration exploitable; son transcript automatique est conservé
comme trace mais explicitement rejeté comme preuve.

Pour la direction artistique des nouvelles réalisations, appliquer en priorité
[`DRUMBOIII_DIRECTION.md`](DRUMBOIII_DIRECTION.md), sans jamais contourner les contrats
physiques ou fonctionnels des objets.

L'ordre d'autorité complet entre Drumboiii et les autres corpus se trouve dans
[`../BLENDER_RULES_PRIORITY.md`](../BLENDER_RULES_PRIORITY.md).
