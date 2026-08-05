# notes — run 2 v2 (job 4d962b86, 21 crédits) — correctif refs canoniques only

## Évaluation vs success criteria du brief (ligne par ligne)

| # | Critère | Verdict | Observation factuelle |
|---|---|---|---|
| 1 | Trajectoire = préviz | 🟡 | **Le fix orientation a marché : device PAYSAGE sur les 5 frames ✓.** P1 macro bas ✓ (moins « rasante grand-angle » que le squelette — Seedance adoucit le raccourci 28 mm) ; P2 hero 3/4 gauche monumental ✓ (t2.6) ; **P3 plongée ~50° adoucie en légère contre-plongée haute ❌** (Seedance résiste à l'overhead) ; P4 rest frontal centré ✓ plan-pour-plan (t5.9). Aucune coupe ✓. |
| 2 | Identité device | ✓ | Layout canonique tenu sur TOUT le clip : molette gauche écran ✓, fader vertical droite ✓, SYNC gravé bas-gauche ✓, slider bas-centre ✓, D-pad bas-droite ✓, wordmark top-center + U. top-right ✓ (police blocky, pas cursive — mineur, texte = POST de toute façon). PCB traversant ✓. |
| 3 | Écran OFF | ✓ | Sombre sur les 5 frames, aucune waveform/UI. |
| 4 | Non opéré / pas de ports | 🟡 | Contrôles non animés ✓ ; plus de ports francs sur les tranches ✓ ; **2 petits caps blancs apparaissent sur le bord HAUT aux angles hauts (t4.4, prior shoulder-buttons)** — visibles seulement quand la caméra monte. |
| 5 | Matière upgradée | ✓ | Satin translucide améthyste, void near-black, rim + key haut, haze ✓. Très supérieur à la préviz. |

**Verdict : quasi-validable** — le drift majeur (portrait) est éliminé, l'identité tient.
Restent 2 écarts pour une v3 éventuelle : plongée overhead adoucie + caps fantômes bord haut.

## Pistes v3 (si gate Sliz le demande)

1. Overhead : renforcer le beat 3 (« the camera looks STRAIGHT DOWN at the faceplate,
   a true top-down plunge ») et/ou accentuer la plongée dans le squelette Blender
   (z caméra plus haut, le v2v adoucit ~30 %).
2. Caps bord haut : ajouter au squelette un vrai passage montrant le bord haut nu
   (l'ambiguïté vient de ce que la préviz EEVEE écrase les détails du bord) +
   counter-prompt « the top edge is bare smooth plastic, nothing mounted on it ».
3. Wordmark cursive : non prioritaire (texte redessiné en POST, règle brand-name).
