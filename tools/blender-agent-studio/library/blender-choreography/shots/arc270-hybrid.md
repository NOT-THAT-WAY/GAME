# Shot — arc270-hybrid (adaptation Blender du pattern validé)

Transposition en **axes caméra Blender** du pattern
`prompt-library/motion-language/270-hybrid-orbital-arc-5-beats.md` — le seul mouvement
validé empiriquement (iter-003-cinema, Sliz 2026-05-09). En Blender le pattern devient
déterministe : plus d'interprétation Seedance, les beats sont des keyframes.

## Traduction motion-language → axes Blender

| Terme prompt | Implémentation Blender |
|---|---|
| lateral arc, axis perfectly vertical | rotation Z de `choreo_pivot` (caméra parentée), élévation fixe ~1,8° |
| speed % per beat | distances angulaires ∝ speed×durée : b2 141° / b3 83° / b4 136° |
| HOLDS / HELD STILL | keyframes plates (même valeur aux 2 bornes du beat) |
| camera REVERSES rapidly | même sens de rotation mais 136° en 1 s (vs 83°/s beat 3) — lecture « retour » |
| internal glow EMERGES | `M_pcb` Principled Emission Strength keyframée 0.08 → 1.6 |
| NO push-in additionnel | distance caméra constante 62 BU, focale fixe 70 mm |
| tilt > 5° interdit | élévation 1,8°, aucune rotation X/Y caméra |

## Timeline (120 f @ 24 fps = 5 s STRICT — 4 s = saccade, 6 s+ = stagne)

| Beat | Frames | θ pivot | Glow PCB |
|---|---|---|---|
| B1 APPEARANCE | 1→24 | 0° hold | 0.08 |
| B2 ROTATION | 24→60 | 0 → −141° (front → 3qL → profil) | 0.08 |
| B3 BACK GLIMPSE | 60→84 | −141 → −224° | 0.08 |
| B4 RAPID RETURN | 84→108 | −224 → −360° (via 3qR) | → 0.9 (f100) → 1.6 (f108) |
| B5 REST BLOOM | 108→120 | −360° hold | 1.6 hold |

Scène : monde crème (0.72, 0.65, 0.55), key 1400 / fill 500 / rim 1600, 720×1280,
device statique au repos (`choreo_device_pivot` resetté), écran SOMBRE (identité —
le glow = PCB uniquement).

## Gate keyframes

`runs/arc270-hybrid-2026-07-12/keyframes/b1…b5` — en attente validation Sliz.
Composition actuelle : device tiers supérieur. Recentrage tiers médian = 1 valeur
(`cam.data.shift_y` ou z du pivot) si demandé.

## Notes

- Le sens négatif (θ vers −) fait partir la caméra vers la 3/4 GAUCHE (fidèle au pattern).
- L'aller 210°+ / retour 150° du pattern = ici une rotation continue 360° asymétrique
  en vitesse — même lecture à l'écran, boucle parfaite.
- Pour un rendu final présentable seul : passer Cycles (transmission fidèle),
  EEVEE = préviz/gates.
