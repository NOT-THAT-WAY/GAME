# Pulsed — Carte objet v3 (source : vidéos, 2026-07-30)

> **Autorité.** Cette carte remplace `audits/pulsed-object-map.md` (v2) partout où elles
> divergent. La v2 était mesurée sur des **images générées par IA** (variance inter-vues,
> pas de cohérence 3D). La v3 est lue sur **deux vidéos d'un rendu 3D cohérent** qui font
> le tour de l'objet : chaque face est vue, et les vues se recoupent physiquement.

## Sources

| Slug | Fichier | Nature | Sert à |
|---|---|---|---|
| `refA` | `source-videos/pulse_ref_A.mp4` | 960×960, 24 fps, 8,06 s | macros : molette, D-pad, sliders, tranche basse, texte `LOW BATT` |
| `refB` | `source-videos/pulse_ref_B.mp4` | 1280×720, 24 fps, 8,10 s | **tour complet** : face, dos, profil + UI écran allumée |

Frames à 4 img/s dans `frames/<slug>/`, mesures dans `audits/frame-measurements.json`
(script `measure_frames.py`).

**Frames canon :**

- `refB/f_0003.jpg` — **face canon** (vue entière la plus frontale, aire 0,559) → tout le layout
- `refB/f_0027.jpg` — **dos canon** → PCB, ports tranche basse, tabs tranche haute
- `refB/f_0025.jpg` — **profil** → épaisseur, dôme dorsal, dépassement molette/SYNC
- `refB/f_0001.jpg` — 3/4 face, écran allumé net → UI
- `refA/f_0013→f_0024` — macros contrôles

## Méthode de mesure

Segmentation par `(B − G) > 10` : la coque violette passe, **l'ombre portée est neutre et
sort du masque toute seule**. C'est la correction directe du bug v1 (l'ombre entrait dans
la bbox et faisait diverger le ratio entre 1,43 et 1,74).

## Cotes maîtresses

| Grandeur | Valeur v3 | Origine | Écart v1 |
|---|---|---|---|
| Ratio W/H face | **1,655** | vues entières 1,619→1,726, encadrent la valeur v2 | inchangé ✅ |
| Largeur W | 16,0 BU (160 mm) | hypothèse conservée | inchangé |
| Hauteur H | 9,67 BU | W / 1,655 | inchangé |
| Épaisseur totale T | **2,70 BU** | `f_0025` : T/H apparent 0,316 avec lacet → 0,279 corrigé | **v1 = 2,18 → trop plat** |
| Rayon de coin | 2,30 BU (≈14 % W) | `f_0003` | inchangé |

1 BU = 1 cm. Repère : X = largeur, Y = épaisseur (face vers −Y), Z = hauteur.

## Layout face — coordonnées normalisées (u, v)

u = fraction de W depuis le bord gauche · v = fraction de H depuis le bord haut.

| Élément | u | v | Taille (u × v) | Note |
|---|---|---|---|---|
| Plaque encastrée (faceplate) | 0,109 → 0,893 | 0,108 → 0,822 | — | rebord translucide épais tout autour |
| Écran (dalle noire) | 0,256 → 0,690 | 0,219 → 0,544 | 0,434 × 0,325 | ≈ 6,94 × 3,14 BU |
| Molette (centre) | 0,210 | 0,399 | drum ⌀ ≈ 1,05 BU, largeur 0,55 | axe **horizontal** (X), crans verticaux |
| Dômes de molette | ±0,04 de la molette | 0,399 | ⌀ ≈ 0,55 BU chacun | violets translucides, brillants |
| SYNC (centre) | 0,177 | 0,656 | ⌀ 0,103 u ≈ 1,65 BU | texte `SYNC` embossé |
| Rail slider horizontal | 0,300 → 0,614 | 0,663 | long 5,02 BU, haut 0,69 BU | **capsule SURÉLEVÉE**, jamais creusée |
| Cap du slider horizontal | 0,300 (butée gauche) | 0,663 | 0,60 × 0,98 BU | à cheval, **ne va jamais au bout du rail** |
| Fente slider gain | 0,738 | 0,259 → 0,537 | long 2,70 BU | verticale, **creusée** |
| Knob du slider gain | 0,738 | 0,370 | ⌀ ≈ 0,45 BU | ne touche jamais le D-pad |
| D-pad (centre) | 0,717 | 0,648 | 2,04 BU d'envergure | flèches embossées + creux central |
| Wordmark `Pulsed` | 0,413 → 0,560 | 0,163 → 0,211 | — | concorde avec la correction v2 |
| Logo `U.` | 0,751 | 0,179 | — | |
| Pastille ronde (power) | 0,817 | 0,140 | — | coin haut-droit |
| Texte `LOW BATT` | ≈ 0,25 | ≈ 0,88 | — | sérigraphie fine, bas-gauche |

## Tranches — **la v1 avait tort**

> ⚠️ La décision v1 « **toutes les tranches sont lisses, les ports ne sont PAS modélisés** »
> est **annulée**. Sur `f_0027` et `f_0003`, la tranche basse porte deux connecteurs nets,
> vus sous deux angles cohérents. Ce n'était pas un artefact d'image fixe.

| Tranche | Contenu | u |
|---|---|---|
| Basse | port **USB-C** (trapèze arrondi) | 0,404 |
| Basse | second connecteur rectangulaire | 0,530 |
| Haute | 2 tabs clairs (charnières/contacts) | 0,363 et 0,662 |
| Gauche / droite | lisses — seuls la molette et le SYNC dépassent | — |

Ce qui reste vrai de la v1 : pas de vis apparentes au dos, pas de bouton sur les tranches
latérales, dos en dôme continu.

## Dos

`f_0027` : coque arrière translucide, **PCB visible sur presque toute la surface**.
Carte sombre (bleu-noir), traces cuivre visibles, **2 gros QFP** au centre, **1 SOIC**
à droite, un gros condensateur rond à gauche, nombreux passifs, plots de vis dans les
coins et à mi-hauteur. Le corps de la molette traverse le PCB côté droit (vu du dos).
Deux nappes/fils sombres longent les bords gauche et droit.

## Écran — UI (canon `refB/f_0001` et `f_0003`)

Fond quasi noir. De haut en bas :

1. **Barre de titre** : `‹ Default* ›` centré, deux petites icônes à droite (disquette, clé)
2. **Waveform** teal (#3FE0D0 environ), sinusoïde à amplitude variable, ~3 périodes
3. **Barre d'état** : `FREE  11.7Hz` à gauche · pastille ronde `MIX` au centre ·
   `∿ DEPTH` + **barregraphe de 8 segments** à droite

C'est une vraie UI, pas une simple waveform émissive : le v1 ne modélisait que la courbe.

## À trancher plus tard

- Cote réelle en mm toujours inconnue — W = 160 mm reste une hypothèse.
- Le second connecteur de la tranche basse n'est pas identifiable avec certitude
  (jack ? port propriétaire ?) — modélisé comme un rectangle arrondi neutre.
