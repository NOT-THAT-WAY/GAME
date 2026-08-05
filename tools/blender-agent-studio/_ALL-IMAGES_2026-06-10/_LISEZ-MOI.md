# Pulsed — toutes les images de la session (2026-06-10) + ré-interprétation

Tout ce qu'on a généré aujourd'hui (nano-banana-pro/edit 4K, fal.ai), trié et commenté.
Originaux immuables dans `_gen-runs/<id>/runs/…`. Rien n'a été déposé aux noms canoniques
dans `assets_blender/` (j'attends ta validation).

**Règle d'or actée (mise à jour 2026-06-10 après-midi) :** tous les contrôles (boutons) sont
sur la **FACE**. Les tranches et les côtés sont **LISSES** — seam seule, + USB-C/port trapèze
en tranche basse. ~~clips (haut)~~ et ~~fente de molette (bord gauche)~~ annulés : pas de
bouton/clip apparent sur les bords, pas de percée — la molette vit entièrement sur la face
(disque cranté axe horizontal, puits ovale, cf. `audits/pulsed-object-map.md` v2).

---

## 📁 01_RETENUES — les bonnes

### `P2_front-uncropped_BOUTONS-VISIBLES.png` — la face de référence (tous les boutons)
Vue frontale complète, marges sur les 4 côtés. **Tous les contrôles présents et lisibles** :
molette haut-gauche, wordmark « Pulsed » + logo « U. », écran, gain slider vertical (droite
écran), bouton **SYNC** rond bas-gauche, slider horizontal bas-centre, **D-pad** bas-droite,
clips de tranche haute, USB-C bas. ✅ layout fidèle à `01_front`.
⚠️ **Seul point ouvert = le RATIO** : mesuré ≈1,65 (comme tes refs dos en mesure identique) vs
ton « 1,51 » (autre seuillage). À trancher par ta cote mm réelle ou ton script. `_alt-seed` =
2e tirage pour comparer.

### `P5_material-neutral_BOUTONS-VISIBLES.png` — face 3/4, lumière neutre (tous les boutons)
Mêmes contrôles, tous visibles, fond gris neutre, zéro dominante chaude, violet améthyste
fidèle, PCB par transparence. ✅

### ~~`MACRO_molette_closeup-11.jpeg`~~ — ❌ REJETÉE puis SUPPRIMÉE (Sliz, 2026-06-10)
La roue traversait le bord gauche par une fente + pin blanc sur la tranche : faux. Canon
(`01_front`/`00_front`) : molette = disque cranté à axe horizontal, **entièrement sur la
face**, bords lisses et intacts. Remplacement : prompt M1 dans
`audits/pulsed-asset-prompts-v2.md` §v2.1.

### `P1_top-edge_NUE.png` — tranche haute
Tranche **nue** : crown convexe + 2 clips gris affleurants à ⅓/⅔ + PCB par transparence.
**Aucun bouton, aucune roulette.** ✅ (c'est la correction du bug initial.)

### `P3_side-right_NU_corrige.png` — flanc droit
Flanc droit **lisse**, aucun relief. Molette parasite retirée (régénéré sans ref de profil +
rabotage pixel du dernier bump). Contour certifié : gauche ≤8px / droite ≤2px. Les marques
sombres = PCB interne par transparence, **pas des boutons**. ✅

### `P4_bottom-edge_USBC+port.png` — tranche basse
USB-C (~46 %) + port trapèze (~62 %), chacun dans sa découpe, seam. Rien d'autre. ✅

### `P6_hero-back-top.png` — hero dos + dessus
Dos (PCB visible) + tranche haute nue (2 clips) + flanc droit nu. Cohérent P1/P3. ✅
(Vue dos → pas de boutons de face, normal.)

---

## 📁 02_iterations-ecartees — pour la traçabilité (ne pas utiliser)

| Fichier | Pourquoi écarté |
|---|---|
| `top-edge_v1_KO_ROULETTE-SUR-DESSUS.png` | **le bug** : roulette inventée sur le dessus (spec v1 inventait un switch). |
| `side-right_v1_KO_molette-depasse.png` | molette qui dépasse du flanc droit. |
| `side-right_v1_KO_couche-horizontal.png` | mauvaise orientation (device couché). |
| `side-right_v1_KO_bump-bas-gauche.png` | bon profil mais bosse parasite. |
| `side-right_v2_KO_molette-encore.png` | edit a reconduit la molette. |
| `side-right_v2_KO_molette-mi-gauche.png` | molette mi-gauche encore présente. |
| `side-right_v2_brut-avant-rabotage.png` | le bon tirage, AVANT rabotage du bump 18px (= source de la retenue). |
| `bottom-edge_v1_doublon.png` | doublon d'un tirage antérieur, identique à la retenue. |

---

## Ce qu'il me reste à savoir de toi
1. **Ratio P2** : ta cote mm réelle (largeur suffit) ou passe mon P2 dans ton seuillage.
2. Valides-tu les 7 retenues ? Si oui, je les copie aux noms canoniques dans `assets_blender/`.
