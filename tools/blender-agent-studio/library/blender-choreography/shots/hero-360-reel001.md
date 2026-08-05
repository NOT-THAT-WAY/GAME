# Shot — hero-360-reel001 (test lane, décalqué du brief reel-001)

Reprend les 5 beats de `pulsed-reels/reel-001-pulsed-hero-360/brief.md` en chorégraphie
Blender déterministe : APPARITION (light-snap) → FRONT REVEAL (push-in) → BACK GLIMPSE →
HERO TURN (360 continu) → REST POSE (retour pose frame 1).

## Paramètres (état run 2026-07-12)

| Param | Valeur |
|---|---|
| Format | 9:16 · 720×1280 · 144 frames @ 24 fps = 6 s |
| Beat 1 (f1-14) | light-snap : énergie `key` 30 → 1400 sur 6 frames, device de face |
| Beat 2 (f14-46) | push-in : distance caméra 68 → 50 BU (Bezier) |
| Beats 3-4 (f40-132) | rotation pivot 0° → 360° (Bezier ease in/out — le glimpse dos passe ~f86) |
| Beat 5 (f118-144) | dolly back 50 → 68 = rest pose ≡ frame 1 (boucle propre) |
| Focale | 70 mm · caméra z 2,0 → 3,5 |
| Monde | crème chaud (0.72, 0.65, 0.55) — backdrop reel-001 |
| Lumières | key 1400 / fill 500 / rim 1600 |
| Engine stills | EEVEE — squelette v2v, la matière finale vient de Seedance |

## Gate keyframes

`runs/hero-360-reel001-2026-07-12/keyframes/b1…b5` — en attente validation Sliz
avant render du clip 144 frames.

## Notes de cadrage 9:16

En portrait, Blender mappe le capteur 36 mm sur la hauteur → le champ horizontal est
réduit d'un facteur 720/1280. Distance pour tenir la largeur 16 BU à 70 mm :
`d ≈ 16×70/(36×720/1280) ≈ 55` + marge → 68 BU (plan large) / 50 BU (push-in).
