# Pulsed — Cartographie exacte de l'objet (mesures pixel)

> Source de vérité positionnelle pour la modélisation 3D et la génération d'assets.
> Méthode : extraction numérique des silhouettes (seuil de luminance), grilles 5 %/10 % superposées, crops natifs 5K. Mesures faites le 2026-06-10 sur `assets_blender/`.
> **Précision : ±2 % sur la face avant, ±3-5 % sur les tranches** (refs IA = variance inter-vues, voir §8).

## 1. Référentiel

- Coordonnées en **% du cadre device vu de face**, origine **coin haut-gauche**, X→droite, Y→bas.
- mm donnés à titre indicatif sous l'hypothèse **W = 160 mm** (non confirmée — voir §2).
- Convention Blender : 1 BU = 1 cm, X+ = droite de la face, Z+ = haut, face avant vers -Y.

## 2. ⚠️ Silhouette : ratio W/H NON tranché (conflit inter-refs)

| Source | Mesure W/H | Fiabilité |
|---|---|---|
| `02_back_canonical` (bbox numérique 1316×869 px) | **1,514** | meilleure candidate (vue posée, droite) |
| `closeup-02` back (bbox numérique) | 1,433 | float + léger tilt |
| `01_front_canonical` | ~1,67-1,74 | **croppée DANS la silhouette** (les 4 bords touchent) → inutilisable pour le ratio |

**Canon provisoire : W/H = 1,51** → H ≈ 106 mm, épaisseur ≈ 26 mm (profil : T/H = 0,246). À verrouiller par l'asset « front non croppée » (cf. prompts v2) ou des cotes réelles.

## 3. Face avant — positions mesurées (grid 5 % sur `01_front_canonical`)

| # | Élément | Zone (x0→x1 / y0→y1) | Centre | Taille | Relief | Confiance |
|---|---|---|---|---|---|---|
| 1 | **Rim externe** (bord surélevé) | cadre complet, largeur ~6 % W (≈10 mm) | — | — | +2-3 mm au-dessus de la faceplate | Haute |
| 2 | **Faceplate** (plaque en retrait) | inset dans le rim | — | — | -2-3 mm sous le rim (closeup-03/09) | Haute |
| 3 | **Wordmark « Pulsed »** (cursif, embossé) | 42→58 / 8→13 | (50, 10,5) | 16 % W | embossé ~0,3 mm | Haute |
| 4 | **Logo « U. »** (embossé) | 76→81 / 9→14 | (78,5, 11,5) | 5 % W | embossé | Haute |
| 5 | **Vis faceplate** (×4) | coins ≈ (6,8) (94,8) (6,92) (94,92) | — | Ø ~2 % W | creux | Moyenne (±2) |
| 6 | **Écran — tray** (renfoncement) | 26→72 / 15→62 | (49, 38,5) | 46 % W × 47 % H (≈74×50 mm) | -2 mm, bezel fin surélevé au bord | Haute |
| 7 | **Écran — zone active** | inset ~1,5 % dans le tray | — | ≈70×44 mm | teal-noir, OFF sur refs | Haute |
| 8 | **Molette** (puits + dôme + bague crantée) | puits : 8→17 / 18→33 | (12,5, 25,5) | puits Ø ≈15 % H (≈16 mm) ; bague grise ≈4,5 % W de large | **+4-5 mm AU-DESSUS de la faceplate** (bosse mesurée au profil : +16 % d'épaisseur locale) | Haute (structure) |
| 9 | **Slider gain vertical — slot** | 75→77 / 15→50 | (76, 32,5) | course ~35 % H (≈37 mm) | slot creux, lèvre embossée | Haute |
| 10 | **Slider gain — knob** | à y≈32 sur refs | — | Ø ≈3,5 % W, blanc, sommet concave | +2 mm | Haute |
| 11 | **Échelle graduée** (ticks embossés) | 78→80 / 16→49 | — | 15-18 ticks, à DROITE du slot | embossé | Haute |
| 12 | **Bouton SYNC** | 7,5→18 / 62→84 | (12,8, 73) | Ø 10,5 % W (≈17 mm) | +2-3 mm, dans anneau-puits ; « SYNC » embossé | Haute |
| 13 | **Slider horizontal — rail** | 21→62 / 68→78 | (41,5, 73) | course 41 % W (≈66 mm), rail h ~10 % H | rail creux | Haute |
| 14 | **Slider horizontal — poignée** | 22→26 (position refs : à gauche) | — | blanc, ~4 % W | +2 mm | Haute |
| 15 | **D-pad** (croix + dôme central) | 70→92 / 57→89 | (81, 73) | envergure 22 % W (≈35 mm), bras ~8 % W, dôme Ø ~6 % W | +3 mm, dans puits cruciforme, jeu ~1 mm, 4 flèches embossées | Haute |
| 16 | Groove/label bas (bande discrète) | 20→62 / 88→93 | — | faible relief | — | **Basse** |

Alignements remarquables (à exploiter en modé) : SYNC, slider horizontal et D-pad partagent le même axe **y = 73 %** ; molette (12,5) et SYNC (12,8) partagent le même axe **x ≈ 12,6 %**.

## 4. Tranche basse (canon : `closeup-10`)

| Élément | Position x (vue de face) | Détail |
|---|---|---|
| **USB-C** | centre ≈ **47 %** (±3) | oval métal, découpe arrondie ≈12×6 mm dans la coque |
| **Port trapèze multi-broches** | ≈ **58→64 %** | type micro-HDMI/propriétaire, broches dorées visibles, pads silkscreen blancs sur PCB dessous (par transparence) |
| Seam | toute la longueur | ligne de joint horizontale, lèvre coque avant sur coque arrière |

Note : `02_back` suggère un décalage différent (variance IA ±5 %) — **closeup-10 fait foi**.

## 5. Tranche haute — NUE (décision verrouillée 2026-06-10)

Contenu exact, rien d'autre :
- **Ligne de joint** (seam) sur toute la longueur, crown légèrement convexe.
- **2 petits clips/languettes gris bas-profil** à x ≈ **30 %** et ≈ **70 %** (±5, silhouette `02_back` ; saillie ≤1,5 mm).
- **Bossages de vis des coins** + connecteurs PCB internes **visibles par transparence uniquement**.
- ❌ PAS de switch, PAS de molette, PAS de port, PAS de bouton. (Le « slide power switch » de la spec v1 était une invention — annulé.)

## 6. Flancs

- **Flanc gauche** : la molette est en saillie du **plan de la face** (dôme + bague au-dessus de la faceplate). Dans mes refs locales (`closeup-01` crop natif), **aucune percée du flanc n'est visible** — le puits reste séparé du rim. La macro générée `closeup-11` (validée ✅ par Sliz) montre une **encoche du bord gauche** : c'est désormais le **canon** (cohérent avec « dépassant par le bord gauche » de extracted-data §2.2). → Modélisation : encoche discrète dans le rim gauche au droit de la molette.
- **Flanc droit** : nu — seam uniquement (canon : side-right gen iter3, après retrait du bossage parasite bas-gauche).

## 7. Profil / épaisseur (numérique, `03_side_clean`)

- Corps : **T/H = 0,246** (≈26 mm @ H=106). Dos bombé, roundovers du haut plus marqués côté dos.
- Saillies de face : molette (max, +16 % d'épaisseur locale), SYNC/D-pad/poignées +2-3 mm (bosses mesurées y 58→88 %).
- ⚠️ `03_side` n'est **pas un ortho strict** (device flotté/incliné : la bosse molette y apparaît à y≈38 % au lieu de 25,5 %). Utiliser pour ratios d'épaisseur et galbes, **jamais pour des positions y**.

## 8. Dos

- PCB plein cadre visible, **layouts incohérents entre les 3 vues dos** (variance IA) → décision : PCB = plaque simplifiée + **texture photo dérivée de `closeup-02`** (ancre désignée), composants majeurs (2-3 puces, molette, nappe) en très léger relief si besoin macro.
- Vis : 4 coins confirmés ≈ (7,9) (93,9) (7,91) (93,91) ; paire mi-hauteur possible (93,50)/(7,50) — confiance basse.

## 9. Incohérences IA recensées (et canon désigné par zone)

| Sujet | Variance constatée | Canon |
|---|---|---|
| Ratio W/H | 1,43 → 1,74 selon vue | **1,51** provisoire ; à verrouiller (asset front non croppée) |
| Position clips tranche haute | 30/70 vs 37/57 selon vue | symétrique **30/70** |
| Ports tranche basse | décalés ±5 % entre back et c10 | **closeup-10** |
| Layout PCB | différent sur les 3 vues dos | **closeup-02** (texture) |
| Side ortho | tilt → positions y faussées | épaisseur/galbes seulement |

## 10. Plan de reconstruction 3D (ordre de modé)

Collection `PULSED`, objets séparés, quads-first :

1. `pulsed_shell_front` — rim + faceplate en retrait ; empreintes (puits molette, anneau SYNC, slots sliders, puits cruciforme D-pad, tray écran) posées par **inset/boolean propre** aux positions de la table §3 ; encoche molette dans le rim gauche.
2. `pulsed_shell_back` — dôme arrière, lèvre de seam, découpes ports (§4), clips tranche haute (§5), bossages de vis internes (closeup-09).
3. `pulsed_screen` — tray + vitre (matériau émissif off/on).
4. `pulsed_wheel` — dôme + bague crantée (cylindre cranté, axe horizontal).
5. `pulsed_sync`, `pulsed_slider_gain` (slot insert + knob), `pulsed_hslider` (rail + poignée), `pulsed_dpad` (croix + dôme).
6. `pulsed_ports` — inserts USB-C + trapèze.
7. `pulsed_pcb` — plaque texturée (canon closeup-02).
8. Vis ×4, clips ×2, embossages (wordmark/logo/ticks : displacement léger ou normal map — décision Phase 5).

Échelle : bbox **16 × 10,6 × 2,6 BU** (W figé à 16, le reste en ratios mesurés) → un scale uniforme final suffit si cotes réelles fournies.
