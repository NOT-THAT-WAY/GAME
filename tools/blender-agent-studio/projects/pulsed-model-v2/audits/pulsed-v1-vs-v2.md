# Pulsed v1 → v2 : ce qui change et pourquoi

**Date :** 2026-07-30 · **Source du v2 :** deux vidéos de référence (`refA`, `refB`)

## La cause racine

Le v1 n'était pas mal exécuté — il était mal **sourcé**. Ses références étaient
des images fixes générées par IA, produites indépendamment les unes des autres :
aucune ne partage la géométrie d'une autre. D'où la « variance inter-vues » notée
à l'époque, et un canon désigné *par zone* pour arbitrer les contradictions.

Les vidéos changent la nature de la preuve. `refB` fait le tour complet de
l'objet en une seule prise : face, profil, dos, retour. Chaque détail est vu
sous plusieurs angles **cohérents entre eux**. Ce qui était arbitrage devient
mesure.

## Corrections de fond

| Point | v1 | v2 | Preuve |
|---|---|---|---|
| **Ports de tranche** | supprimés — décision « toutes les tranches sont lisses » | **USB-C (u 0,404) + connecteur secondaire (u 0,530) sur la tranche basse** | `refB f_0027` et `f_0003`, deux angles concordants |
| Tabs tranche haute | absents | 2 tabs clairs (u 0,363 / 0,662) | `refB f_0027` |
| Épaisseur totale | 2,18 BU — lisait trop plat | **2,70 BU** | `refB f_0025`, T/H apparent 0,316 corrigé du lacet → 0,279 |
| Écran | plan émissif portant une simple waveform | **UI complète** : barre `‹ Default* ›`, waveform, `FREE / 11.7Hz`, pastille `MIX`, `∿ DEPTH` + barregraphe 8 segments | `refB f_0001`, `f_0003` |
| PCB | plaque + texture plate + émission 0,38 (triche de lisibilité) | carte dense : 2 QFP, SOIC, condensateur, plots de vis, ~150 passifs **sur les deux faces**, pistes procédurales | `refB f_0027` |
| Coque | 2 solides, dos 2 288 verts / face 835 verts (déséquilibre) | demi-coques **creuses** (paroi 0,18 BU) lofteés sur la même silhouette | — |
| Duplication | tout en double (`choreo_*` + `flroom_*`) | un seul jeu | — |

## Ce qui est confirmé du v1

Le v1 avait raison sur l'essentiel de la forme, et ça se vérifie :

- **Ratio W/H = 1,655** — les vues entières donnent 1,619 → 1,726, qui l'encadrent.
- **Molette = tambour cranté à axe horizontal** flanqué de deux dômes violets,
  sortant d'un simple trou, sans rond incrusté autour.
- **Slider horizontal = capsule surélevée**, jamais creusée, cap à cheval qui ne
  va jamais au bout du rail.
- **Slider gain vertical court**, v 0,26 → 0,54, ne touche jamais le D-pad.
- **Wordmark** à u 0,413→0,560 / v 0,163→0,211 (la correction v2 était bonne).
- Pas de vis apparentes au dos, dos en dôme continu, flancs lisses.

## Chiffres

| | v1 | v2 |
|---|---|---|
| Objets mesh rendus | 24 (12 × 2 jeux) | 176 |
| Triangles | ~9 500 | 36 160 |
| Matériaux | 7 | 14 |
| Reproductible depuis un script | non | **oui** (`build_v2.py` repart d'une scène vide) |

La hausse du nombre de triangles est assumée : elle va presque entièrement dans
le PCB et ses composants, c'est-à-dire dans ce qu'on voit *à travers* la coque —
exactement ce qui manquait au v1.

## Limites connues

- **W = 160 mm reste une hypothèse.** Aucune cote réelle n'a jamais été fournie ;
  tout le modèle est à l'échelle près. Une seule mesure physique verrouillerait
  l'ensemble.
- Le second connecteur de la tranche basse n'est pas identifiable avec certitude
  (jack ? port propriétaire ?) — modélisé en rectangle arrondi neutre.
- Les vidéos sont elles aussi des rendus, pas des photos d'un objet réel. Elles
  sont cohérentes en 3D, ce qui est le point décisif, mais elles ne prouvent pas
  un objet physique.
- Les pistes du PCB sont procédurales et plausibles, pas un décalque du tracé
  visible sur `f_0027`.
