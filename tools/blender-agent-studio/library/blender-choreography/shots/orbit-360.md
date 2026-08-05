# Shot — orbit-360

Turntable : la caméra orbite à 360° autour du device (pivot `choreo_pivot` au centre,
z = 4,835), vitesse constante, léger point de vue en contre-plongée.

## Paramètres (état run 2026-07-12)

| Param | Valeur | Note |
|---|---|---|
| Durée | 120 frames @ 24 fps = 5 s | |
| Départ | azimut −30° (3/4 gauche) → +330° | interpolation LINEAR |
| Distance caméra | 42 BU | device entier + marge confortable |
| Hauteur caméra | z = 3,5 (pivot à 4,835) | contre-plongée douce |
| Focale | 70 mm | compression téléobjectif |
| Lumières | key 950 / fill 320 / rim 2000 | valeurs .blend d'origine : 1500/600/2200 |
| Monde | near-black (0.008, 0.008, 0.011) | studio void brand |
| Engine stills | EEVEE 1280×720 | translucide approximatif — suffisant pour squelette v2v |

## Gate keyframes

`runs/orbit-360-2026-07-12/keyframes/beat_f001/040/080/120.png` — en attente
validation Sliz avant render du clip.
