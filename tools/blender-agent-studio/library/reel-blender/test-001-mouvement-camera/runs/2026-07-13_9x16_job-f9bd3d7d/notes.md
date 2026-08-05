# notes — run 1 (job f9bd3d7d, 21 crédits, seedance_2_0 fast 720p 6s 9:16)

## Évaluation vs success criteria du brief (ligne par ligne)

| # | Critère | Verdict | Observation factuelle |
|---|---|---|---|
| 1 | Trajectoire = préviz | ❌ | P1 macro rasante ✓ (t0.4-1.5 : slider+D-pad au premier plan, contre-plongée) ; P4 rest frontal centré ✓ (t5.9 quasi plan-pour-plan avec le squelette) ; **P2/P3 ❌ : le device pivote en PORTRAIT au lieu que la caméra crane + la plongée overhead n'existe pas** (t2.6, t4.4). Aucune coupe ✓. |
| 2 | Identité device | ❌ | t5.9 quasi canonique (fader droite ✓, SYNC bas-gauche ✓, slider bas-centre ✓, D-pad bas-droite ✓, wordmark+U. ✓ ; molette mi-gauche au lieu de haut-gauche) ; **milieu du clip : contrôles re-brassés, double D-pad t2.6** ; matière améthyste translucide PCB ✓. |
| 3 | Écran OFF | ✓ | Sombre/réflectif sur les 5 frames, aucune waveform/UI. |
| 4 | Non opéré / pas de ports | ❌ | Contrôles non animés ✓ ; **ports fantômes sur la tranche gauche (t0.4/t1.5, prior link-port Game Boy)**. |
| 5 | Matière upgradée | ✓ | Void near-black + haze + rim froide ✓, satin translucide superbe, très cohérent panels ; légère brillance sur tranches (borderline). |

**Non validable** (critères 1, 2, 4 ❌) — mais la MÉTHODE est prouvée : là où aucun panel
drifté n'interférait (début/fin), Seedance a suivi le squelette Blender fidèlement.

## Diagnostic

Cause unique identifiée : les 4 panels storyboard envoyés en `image_references`
contenaient le drift NB connu (P2/P3 device portrait). Seedance a fusionné leur
composition avec le squelette → pivot portrait au milieu du clip.
Canonisé : `prompt-library/failure-patterns/v2v-drifted-panel-refs-override-motion-skeleton.md`
+ moteur use-case C″.

## Correctif appliqué au run 2

1. Image refs = canoniques UNIQUEMENT (01 front, 02 back, 03 side) + squelette vidéo.
2. MOTION SOURCE renforcée : « the device stays horizontal landscape at ALL times;
   never rotate the device; the camera does ALL the movement ».
3. CONSTRAINTS : rappel « nothing protrudes from the edges — no ports, no connectors ».
