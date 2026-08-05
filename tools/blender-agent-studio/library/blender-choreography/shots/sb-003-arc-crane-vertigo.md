# Shot — sb-003-arc-crane-vertigo (1er shot composé depuis la grammaire caméra)

Chorégraphie composée depuis `prompt-library/motion-language/camera-grammar-object-staging.md`
(recherche 2026-07-13) : **ARC + CRANE + DOLLY-out + ZOOM-in** en un seul geste continu,
puis **swing back en PULLBACK REVEAL**, et **micro DOLLY-ZOOM (vertigo)** au settle.
Règles de fluidité appliquées (leçon run 2 saccadé vs run 3 fluide) :
still → move → still, AUCUN hold intermédiaire, ease Bezier partout.

## Timeline (144 f @ 24 fps = 6 s, 720×1280)

| Phase | Frames | Azimut | Cam (dist BU, z) | Focale | Grammaire |
|---|---|---|---|---|---|
| HOLD départ | 1→16 | −15° | (16, −3,5) | 35 mm | macro 3/4 gauche bas (still) |
| ARC+CRANE | 16→76 | −15 → −65° | →(30, +6) | 35→70 mm | orbit montant + dolly-out + zoom-in (wrap-around, partiel voulu) |
| SWINGBACK | 76→126 | −65 → 0° | →(58, 0) | 70→52 mm | pullback reveal — objet ENTIER ~f108 |
| VERTIGO settle | 126→140 | 0° | →(64, 0) | 52→57 mm | dolly-zoom subtil : 64/57 ≈ 58/52, taille ~constante, la perspective « respire » |
| HOLD final | 140→144 | 0° | (64, 0) | 57 mm | hero rest (still) |

## Rig / fichiers

- Script rejouable : `tools/rig_sb003.py` ; `.blend` sauvegardé avec marqueurs
  HOLD / ARC_CRANE / SWINGBACK / VERTIGO / REST.
- Préviz : `runs/sb-003-arc-crane-vertigo-2026-07-13/preview_sb003_6s.mp4`.

## Gate

En attente Sliz. Réglages à 1 valeur si demandé : objet plus gros au repos (dist 64→56),
arc plus/moins ample (azimut −65°), vertigo plus marqué (écart lens/dist), vitesse phases
(déplacer f76/f126). **Pas de génération Seedance avant validation du mouvement** —
ensuite : recette C″ VIDEO-FIRST (front seule + squelette).
