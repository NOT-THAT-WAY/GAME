# Pulsed — Plan de modélisation Blender (complet, exécutable phase par phase)

> **✅ EXÉCUTÉ le 2026-06-10 (v1 du modèle).** Les 7 phases sont passées avec gates screenshot/render.
> Livrables : `Pulsed_3D_model.blend` (racine projet) + `exports/pulsed.glb` (3,38 Mo, 6 304 tris,
> réimport vérifié). Écarts et choix consignés dans le rapport de session et `pulsed-object-map.md`
> (wordmark re-positionné, conflit bosse molette des vues side, slot gain à étendre, embossages en
> bump texture plutôt qu'en géométrie, PCB avec émission 0,38 pour la lisibilité interne).

> Établi le 2026-06-10 sur la carte v2 (`pulsed-object-map.md`) et l'index des assets
> (`assets_blender/INDEX.md`). Workflow du brief : **phases atomiques, gate screenshot vs ref
> à la fin de CHAQUE phase, jamais enchaîner sans OK Sliz.** Aucune opération destructive sans
> screenshot préalable.

## A. Conventions (verrouillées)

- **1 BU = 1 cm.** Scène METRIC, `scale_length = 1.0`.
- Orientation finale : device **debout**, face avant vers **−Y**, X+ = droite de la face,
  Z+ = haut. **Base (tranche basse) posée sur Z = 0**, centré en X, mi-épaisseur sur Y = 0.
- Bbox cible : **W 16,00 × T 2,15 × H 9,67 BU** (corps ; 2,7 BU au sommet de la molette).
  Hypothèse W = 160 mm signalée — tout est en ratios, un scale uniforme final suffira.
- Export glTF : −Y forward, +Z up (défaut glTF) → cohérent avec l'orientation ci-dessus.
- Collection `PULSED`. Noms canoniques du brief : `pulsed_shell`, `pulsed_screen`,
  `pulsed_dpad`, `pulsed_knob` — déclinés en granulaire : `pulsed_shell_front`,
  `pulsed_shell_back`, `pulsed_wheel`, `pulsed_sync`, `pulsed_slider_gain`,
  `pulsed_hslider`, `pulsed_ports`, `pulsed_pcb`, `pulsed_screws`.
- Quads-first, low-to-mid poly + Subsurf. **Budget : ≤ 100 k tris exportés, glb ≤ 10 Mo,
  textures ≤ 2K.** Pas de génération image-to-mesh (Rodin/Hunyuan) comme base.

## B. Table de conversion — positions en BU (calculées depuis la carte v2)

Formules : `X = x%/100 × 16 − 8` ; `Z = 9,67 × (1 − y%/100)`. Face avant ≈ plan Y = −1,075.

| Élément | Centre (X, Z) | Étendue BU | Relief Y |
|---|---|---|---|
| Faceplate (plaque interne) | (0, 5,01) | X −5,84→+5,79 ; Z 1,58→8,45 | −0,2 à −0,3 sous le rim |
| Écran zone active | (0, 5,87) | X −3,55→+3,52 ; Z 4,35→7,39 (7,07×3,04) | tray −0,2 |
| Molette — bande crantée | (−4,77, 5,98) | larg. 0,46 ; haut. 1,08 | jante **−0,4/−0,5 devant la face** |
| Molette — puits stadium + lobes | (−4,72, 5,95) | X −5,60→−3,84 ; Z 5,12→6,77 | creux + lobes bombés |
| Slot gain | (+4,44, 5,80) | X 4,32→4,56 ; Z 4,06→7,54 (course 3,48) | creux −0,15 |
| Knob gain | (+4,51, 5,78) | Ø 0,24 | +0,15 |
| Ticks gradués | x 79→80,3 → X 4,64→4,85 | le long du slot | embossés |
| SYNC | (−4,66, 3,09) | Ø 1,54 | +0,25, anneau-puits |
| Slider horizontal — rail | (−0,56, 2,90) | X −2,72→+1,60 ; Z 2,32→3,48 | creux −0,15 |
| Slider horizontal — poignée | (−2,34, 3,07) | larg. 0,46 | +0,2 |
| D-pad | (+4,51, 3,11) | envergure 1,92 | +0,3, puits cruciforme |
| Wordmark « Pulsed » | (−1,52, 8,51) | larg. ≈1,3 | embossé +0,03 |
| Logo « U. » | (+4,16, 8,46) | larg. ≈0,5 | embossé |
| USB-C (tranche basse) | X ≈ −0,56, Z = 0 | découpe ≈1,2×0,6 | encastré |
| Port trapèze (tranche basse) | X +1,92, Z = 0 | X 1,28→2,24 | encastré |
| Rayon de coin silhouette | — | **R ≈ 2,2** (4 coins quasi égaux) | — |
| Vis dos ×4 | (±6,9, ±0,87 du centre) ≈ coins (7/93 %, 9/91 %) | Ø ≈0,3 | creux |

Alignements de contrôle : SYNC / poignée / D-pad sur **Z ≈ 3,1** ; molette+SYNC sur
**X ≈ −4,7** ; knob gain + D-pad sur **X = +4,51** ; écran centré X = 0.

## C. Phases

### Phase 1 — Scène & plans de référence (≈ simple)
1. Vérifier la connexion MCP + `get_scene_info`. ⚠️ Le .blend ouvert est
   `~/unrecorded/Pulsed_3D_model.blend` → **Save As immédiat vers
   `~/unrecorded/Blender/Pulsed_3D_model.blend`** (résout le conflit des deux fichiers).
2. Scène propre : purger les objets de test, METRIC/1.0, collection `PULSED` + collection
   `REFS` (non exportée).
3. Plans image (empties « image ») :
   - `00_front_uncropped` : le device y est exactement centré (bbox px 796→4260 / 648→2744,
     centre = centre image). Plan de **23,35 × 15,66 BU** centré sur (0, 4,835) en X/Z,
     posé à **Y = +3** (derrière le device, visible en vue Front).
   - `04_side_right` : calibrer la bbox device du plan sur T×H = 2,15×9,67 (mesure px au
     moment de l'import), posé à **X = −9**, visible en vue Right.
   - `05_top` / `06_bottom` en plans auxiliaires masqués (servent aux Phases 3-4).
4. Cube de calage 16×2,15×9,67 posé base Z=0 (wireframe, non exporté).
- **Gate 1** : screenshots vue Front + Right — le cube de calage coïncide avec la silhouette
  des deux plans image. STOP → validation Sliz.

### Phase 2 — Blocking coque (silhouette + profil)
1. `pulsed_shell_blocking` : cube 16×2,15×9,67 → bevel **R 2,2** sur les 4 arêtes verticales
   (8-10 segments, quads), crown convexe de la tranche haute et fond arrondi par loops + ajustement
   sur `04_side`, roundovers face/dos (dos plus bombé — lire le galbe sur P3).
2. Lire la **position Y du seam** sur `04_side` (provisoire : Y ≈ −0,3, coque avant moins
   profonde que le dos) → marquer la loop de seam.
3. Renflement local de la zone molette (quart haut-gauche, cf. profil P3 : +0,4-0,5 max).
- **Gate 2** : overlay screenshot vs `00_front` (silhouette ±1 %) et vs `04_side` (profil).
  Vérification ratio : bbox mesh = 16×~2,15×9,67. STOP.

### Phase 3 — Coque détaillée (empreintes, AVANT les contrôles)
1. Split au seam → `pulsed_shell_front` / `pulsed_shell_back` (lèvre d'emboîtement légère).
2. Shell front : rim périphérique + **faceplate en retrait** (−0,25) aux bornes §B ;
   loops placées aux X/Z des empreintes puis insets/extrusions (boolean propre uniquement si
   l'inset quad est déraisonnable) :
   tray écran (−0,2), puits stadium molette, anneau-puits SYNC, slot gain, rail h-slider,
   puits cruciforme D-pad.
3. Shell back : découpes USB-C + trapèze en tranche basse, dôme, bossages internes discrets.
4. **Tranches : lisses partout** — aucune autre découpe, aucun clip (décision verrouillée).
   Vérifier sur `00_front` la « groove » basse (confiance basse v1) : si invisible → ne pas
   la modéliser.
- **Gate 3** : screenshots Front/Right/Bottom vs refs + un 3/4 vs `closeup-01`. STOP.

### Phase 4 — Contrôles (objets séparés)
1. `pulsed_wheel` : disque cranté **axe X horizontal** (cylindre Ø ≈1,1, crantage par
   modulation de la jante ou bump Phase 6 — choisir au poly-budget), jante dépassant de
   0,4-0,5 devant la face ; **2 lobes-capots violets** (quart-sphères écrasées) de part et
   d'autre dans le stadium.
2. `pulsed_sync` : bouton rond Ø 1,54, +0,25, dans son anneau.
3. `pulsed_slider_gain` : knob Ø 0,24 à (+4,51, 5,78) coulissant dans le slot.
4. `pulsed_hslider` : poignée 0,46 à (−2,34, 3,07) sur son rail.
5. `pulsed_dpad` : croix 1,92 + dôme central, +0,3 dans le puits cruciforme.
6. `pulsed_ports` : insert USB-C métal + insert trapèze à broches.
7. `pulsed_screen` : plaque tray + vitre légèrement en retrait.
- **Gate 4** : Front vs `00_front` (positions ±1 % → ±0,16 BU), Bottom vs `06`, 3/4 vs
  `closeup-01`. Vérifier les 3 alignements §B. STOP.

### Phase 5 — Micro-détail & embossages
1. Wordmark + logo + ticks + flèches D-pad + « SYNC » : **décision ici** — displacement léger
   (si budget ok) vs normal map bakée. Position selon §B.
2. Vis ×4 (dos) + bossages internes.
3. `pulsed_pcb` : plaque mince sous la coque, **texture dérivée de `closeup-02`**
   (redressement perspective + crop → 2K), composants majeurs (2-3 puces, nappe) en relief
   très léger.
- **Gate 5** : closeups viewport vs `closeup-03/09/10` + compte de polys. STOP.

### Phase 6 — Matériaux (cible : violet translucide + PCB par transparence)
1. `M_shell_purple` : Principled — couleur échantillonnée sur **`08_material_neutral`**
   (canon couleur), Transmission ≈0,7, Roughness 0,15-0,25, IOR 1,45.
   ⚠️ **Décision web** : Transmission exporte en `KHR_materials_transmission` (supporté
   three.js, coûteux) vs Alpha Blend (léger, moins fidèle) → trancher selon la cible
   image-sequence (rendu Blender, transmission OK) ou temps réel.
2. `M_pcb` (texture closeup-02), `M_screen` (off sombre + variante émissive depuis
   `07_screen_best_single`), `M_controls_grey` (gris clair, roughness ~0,4), `M_metal_usbc`.
3. Éclairage de validation neutre (type `08`).
- **Gate 6** : render viewport vs `08` (couleur/matière) et vs `00_front`. STOP.

### Phase 7 — QA topologie & export
1. QA : transforms appliqués, origines posées (shell : base Z=0), normales, noms/hiérarchie,
   UVs propres, poly-budget ≤ 100 k tris.
2. Exports : **`Pulsed_3D_model.blend`** (projet) + **`pulsed.glb`** (−Y forward/+Z up,
   textures embarquées ≤ 2K, Draco optionnel selon pipeline web).
3. Test de réimport du .glb (round-trip) + screenshots finaux 6 vues.
- **Gate 7 (finale)** : 6 vues vs 6 refs + poids des fichiers. Livraison.

## D. Risques / décisions ouvertes (signalés, non bloquants)

| Sujet | État | Quand |
|---|---|---|
| Cote réelle (W mm) | hypothèse 160 — rescale uniforme trivial | dès que Sliz fournit |
| Position Y exacte du seam | à lire sur `04_side` | Phase 2 |
| Groove basse de la face (confiance basse) | vérifier sur `00_front`, sinon abandonner | Phase 3 |
| Crantage molette : géométrie vs bump | selon poly-budget | Phase 4/6 |
| Embossages : displacement vs normal map | selon poly-budget | Phase 5 |
| Transmission glTF vs alpha (perf web) | selon pipeline `/pulsed` | Phase 6 |
| Macro molette M1 (regen) | utile Phase 4-5 pour le détail, non bloquante | quand Sliz génère |
