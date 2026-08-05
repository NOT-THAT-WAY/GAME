# Shot — object-hero (automation OBJET, caméra fixe)

Inverse de l'orbit : la **caméra est fixe**, c'est le **device qui bouge** via
`choreo_device_pivot` (empty parent des 12 meshes `pulsed_*`, transforms conservés).
Donne un mouvement « objet vivant qui se présente » impossible à obtenir proprement
en orbite caméra — et 100 % conforme à la règle « montré, pas opéré » (le device
entier bouge, aucun contrôle n'est animé).

## Chorégraphie (144 f @ 24 fps = 6 s, Bezier ease)

| Beat | Frames | Mouvement pivot (loc z / rot XYZ °) |
|---|---|---|
| B1 repos→float | 1→20 | 4,835→5,1 / 0,0,0 |
| B2 présentation | 20→50 | →5,9 / **pitch −18°** (s'incline vers l'arrière en montant) |
| B3 hero turn | 50→100 | 5,9 / pitch→0 **pendant** yaw 0→360° (vissé) |
| B4 respiration | 100→126 | →5,3 / roll +8° puis −4° |
| B5 rest | 126→144 | →4,835 / 0,0,360 ≡ pose frame 1 (boucle) |

## Caméra / scène

- `choreo_cam_orbit` fixe à (0, −62, 4) rel. pivot orbite, 70 mm,
  TRACK_TO retargeté sur `choreo_device_pivot` (suit le float).
- Monde crème (0.72, 0.65, 0.55), key 1400 / fill 500 / rim 1600, EEVEE 720×1280.

## Apprentissages workflow (2026-07-12)

1. **Parent-pivot** = la bonne primitive pour l'automation objet : un seul empty animé,
   les 12 meshes suivent, zéro risque de désynchroniser un contrôle.
2. En 9:16 le champ horizontal est ÷1,78 vs paysage → distances à recalculer
   (`d ≈ largeur×focale/(36×720/1280)`).
3. Blender 5 : plus de `action.fcurves` → poser l'interpolation via
   `preferences.edit.keyframe_new_interpolation_type` AVANT `keyframe_insert`.
4. EEVEE rend le dos translucide laiteux — OK pour squelette v2v, passer Cycles
   si le clip doit être présentable seul.

## Gate keyframes

`runs/object-hero-2026-07-12/keyframes/b1…b5` — en attente validation Sliz.
Question ouverte : composition actuelle = device tiers supérieur, bas de cadre
très dégagé (UI plateforme). Descendre au tiers médian si préféré.
