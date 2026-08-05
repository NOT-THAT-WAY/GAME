# Shot — sb-002-lowrise-orbit (rétro-ingénierie du run 2 aimé par Sliz)

Chorégraphie dérivée du mouvement RÉEL du run 2 Seedance de `reel-blender/test-001`
(gate Sliz 2026-07-13 : « le premier plan contre-plongée est très sympa… commence
contre-plongée, puis ça tourne et ça ramène à l'objet en vue d'ensemble »).
Un seul mouvement continu, et l'objet paysage finit **ENTIER dans le cadre 9:16**
(fix du défaut sb-001 : l'objet n'était jamais vu en entier → le v2v recomposait).

## Timeline (144 f @ 24 fps = 6 s, Bezier, 720×1280)

| Beat | Frames | Azimut pivot | Cam (dist BU, z local) | Focale |
|---|---|---|---|---|
| B1 LOW hold (contre-plongée rasante) | 1→20 | 0° | (13, −4,8) | 28 mm |
| B2 TURN + rise (3/4 gauche monumental) | 20→64 | 0 → −45° | →(32, −1,0) | 28→70 mm |
| B3 RETURN + pull-back (objet entier ~f110) | 64→120 | −45 → 0° | →(58, 0) | 70 mm |
| B4 REST (ensemble centré, marges) | 120→144 | 0° | →(66, 0) | 70 mm |

Rappel cadre : plein cadre horizontal 9:16 ⇔ dist ≥ ~55 BU @ 70 mm (16 BU de large).

## Rig / fichiers

- Script rejouable : `tools/rig_sb002.py` (reset anim sb-001 puis keyframes ci-dessus,
  marqueurs B1_LOW / B2_TURN / B3_RETURN / B4_REST). `.blend` sauvegardé 2026-07-13.
- Squelette : `runs/sb-002-lowrise-orbit-2026-07-13/preview_sb002_6s.mp4`
  (copie : `reel-blender/test-001-mouvement-camera/refs/09_blender_motion_skeleton_v2_6s.mp4`).

## Notes v2v (leçons test-001)

- Seedance ADOUCIT ~30 % les angles extrêmes → cette chorégraphie évite la plongée 50°
  (adoucie au run 2) et assume le turn latéral, mieux transposé.
- Refs images de la génération : canonical front SEULE (side = colonne verticale → signal
  portrait ; back = fond crème). Cf. use-case C″ du moteur.
