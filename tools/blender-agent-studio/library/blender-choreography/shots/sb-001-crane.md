# Shot — sb-001-crane (1er shot piloté par STORYBOARD Nano-Banana)

Première exécution complète de la boucle **storyboard IA → chorégraphie Blender** :
board généré par `tools/gen_storyboard.py` (4 panels, $0.60, nano-banana-pro/edit,
identité = `refs/01_canonical_front.png`), chaque panel interprété en pose caméra.

## Board source

`refs/storyboards/sb-001-2026-07-13/` — concept « crane macro→hero » :
réveil macro contre-plongée → hero 3/4 → plongée zénithale → repos frontal.

## Interprétation panel → pose Blender (règle : ANGLE + INTENTION, jamais l'objet)

| Panel | Lecture | Pose (azimut°, dist BU, z local cam, focale) | Frame |
|---|---|---|---|
| P1 macro-low | contre-plongée rasante bord bas, fort raccourci **grand-angle** | (0, 13, −4,8, **28 mm**) | 1-20 |
| P2 hero-3q-low | 3/4 gauche monumental, remplit le cadre | (−35, 30, −1,5, 70 mm) | 56-72 |
| P3 overhead | plongée ~50° au-dessus de la face | (−10, 20, +24, 70 mm) | 100-112 |
| P4 hero-rest | frontal à niveau, marges larges, symétrique | (0, 66, 0, 70 mm) | 144 |

Drift NB constaté et IGNORÉ (l'objet 3D est la vérité) : P1 contrôles déplacés,
P2/P3 device passé en portrait, P3 dutch tilt (non transposé — TRACK_TO ne roll pas ;
à ajouter via up-axis animé si demandé un jour).

Transition P1→P2 : la focale s'anime 28→70 mm pendant la montée = crane + zoom
(signature très cinéma, prime au raccourci du réveil).

Scène : void near-black (0.006, 0.006, 0.009), key 1100 / fill 180 / rim 2400,
exposure +0.6, PCB emission 0.25 constante, 144 f @ 24 fps, 720×1280.

## 🐛 Bug historique réglé ici (2026-07-13)

**Le device était décalé de +4,835 en Z depuis le parentage** (`matrix_parent_inverse`
calculé AVANT `view_layer.update()` → identity → enfants remontés de la hauteur du
pivot). C'était la cause du cadrage « tiers supérieur » de TOUS les renders 9:16
précédents. Fix : recalcul de l'inverse après update (cf. `tools/` / fixparent).
Leçon : **toujours `bpy.context.view_layer.update()` avant de lire `matrix_world`
d'un objet fraîchement créé/déplacé.**

## Gate

- Stills : `runs/sb-001-crane-2026-07-13/keyframes/P1…P4` (à comparer aux panels)
- Préviz : `runs/sb-001-crane-2026-07-13/preview_sb001_6s.mp4`
- En attente validation Sliz. Le .blend est sauvegardé avec cette chorégraphie
  active + marqueurs P1→P4 (modifiable directement en UI).
