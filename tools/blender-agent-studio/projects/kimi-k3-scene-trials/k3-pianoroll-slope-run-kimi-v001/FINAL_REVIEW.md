# FINAL_REVIEW — k3-pianoroll-slope-run-kimi-v001 (participant : kimi)

## Verdict : ship — 90/100

Un humanoïde pearl de 0,33 m court vers le haut du Piano Roll incliné à **46,34°** (mesuré,
non supposé), avec appuis calés sur les downbeats de la piste master (148,9 BPM), adhérence
contractuelle visible (semelles lime pulsées au contact, μ = 1,25) et tracking caméra
trois-quarts à distance strictement constante.

## Ce qui a été mesuré avant de construire

- 4 sommets de `USTUDIO_PIANO_ROLL_FLOOR` dans le repère `USTUDIO_BOX_FLOAT_ROOT` ;
- `SURFACE_NORMAL (0, −0,7235, 0,6904)`, `UPHILL_TANGENT (0, 0,6904, 0,7235)`,
  `CROSS_SLOPE_TANGENT (−1, 0, 0)` — jamais confondues avec la verticale monde ;
- pente réelle **46,34°**, longueur utile 2,419 m, largeur 7,56 m ;
- friction statique minimale théorique tan(46,34°) = **1,048** → contrat μ = 1,25.

## Méthode physique (le cœur de l'exercice)

L'armature du personnage est orientée dans le repère de surface : en espace armature,
le Piano Roll est le plan z = 0 et la montée = −Y. Les semelles sont donc coplanaires
**par construction**. Mais le corps n'est PAS tourné comme un objet collé au sol :
la chaîne hanches/colonne/torse contre-rotationne de ~68°, ce qui place le torse à
**19–24° vers l'amont depuis la verticale monde** — gouverné par la gravité, pas par la
normale. Les jambes sont résolues analytiquement (2-bone FK) à chaque frame : le pied
planté est strictement fixe pendant l'appui, la cheville compense pour garder la semelle
au plan, et l'allonge maximale de jambe borne la longueur de foulée (pas de 0,15 m,
bassin abaissé à −0,045 m pendant la course).

## Métriques (diagnostics/physical-validation.json, 240 frames)

| Métrique | Seuil | Mesuré |
|---|---|---|
| drift pied planté | ≤ 0,005 m | L 0,00002 / R 0,00494 m |
| pénétration | ≤ 0,002 m | 0,000 m |
| clearance orteils (swing) | ≥ 0,01 m | 0,060 m |
| erreur hauteur root/plan | ≤ 0,003 m | 0,000 m |
| variation distance caméra | ≤ 0,01 m | 0,000 m |
| clearance caméra/décor | ≥ 0,08 m | 0,534 m |
| torse en course (verticale monde) | 15–25° | 19,2–23,6° |
| frames noires | 0 | 0 (blackdetect propre) |
| MP4 | 240 f / 8 s / AAC | 240 f / 8,000 s / AAC ✓ |

## Corrections menées (une famille à la fois)

1. **physique/contact** : pas trop longs pour l'allonge des jambes → pied traîné par le
   clamp de distance (drift 0,039) ; corrigé par pas 0,15 m + bassin −0,045 m → drift ≤ 0,005 ;
2. **posture** : la contre-rotation était inversée (~16° au lieu de ~66°) : le personnage
   pendait vers l'aval ; corrigée vers 19–24° amont mesurés ;
3. **caméra** : deux frames noires (caméra dans le channel rack) → bascule côté −X ;
   élévation monde ~17° pour ramener la pente apparente de 46° à ~29° (20–35° exigé) ;
   anticipation K2/K4 déplacée sur le target pour une distance constante (0,000 m) ;
   cadrage final avec marge tête/pieds ;
4. **debout** : bassin de repos abaissé de 0,012 m (l'allonge exacte jambe tendue
   équivalait à une hyperextension de genou).

## Limites connues

- La grille de downbeats (57,41 + i·12,1034) vient d'une analyse de flux spectral ;
  elle n'a pas été confirmée à l'écoute (warning du fichier source).
- Le cycle de foulée est stylisé (mannequin sans visage, pas de pronation/supination).
- Quelques highlights chauds sur le corps blanc et un léger flare magenta en fin de course.
- La course couvre 1,6 m des 2,42 m de pente (marges 0,2 m bas / 0,62 m haut) — choix
  dicté par l'allonge des jambes, pas par la surface disponible.

## Preuves

- `scene/trial.blend` + `FL_Studio_PianoRoll_Slope_Run_Kimi.blend` (livrable nommé) ;
- `preview-pianoroll-slope-run-kimi.mp4` + `renders/preview.mp4` (H.264/AAC, 240 f, 8 s) ;
- `renders/frames/` (240 PNG) ;
- `gates/contact-sheet-narratif.png`, `contact-sheet-profil.png`, `contact-sheet-pieds.png`,
  `lighting-*.png` + `lighting-gate-manifest.json` ;
- `diagnostics/surface-analysis.json`, `physical-validation.json`, `scene-audit.json` ;
- `readiness.json`, `brief.json`, `scene-contract.json`, `shot-manifest.json`, `score.json`.
