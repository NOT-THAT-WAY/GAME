# Pulsed — Carte objet v4 (vue de face, 2026-07-30)

> **Autorité.** Remplace la v3 sur tout le layout de face et sur le ratio.
> Source : vue de face quasi orthographique d'une version plus avancée de
> Pulsed, fournie par Sliz. La v3 reste valable pour le dos, les tranches et
> le profil, que cette vue ne montre pas.

## L'erreur de la v3, et pourquoi

La v3 mesurait sur `refB f_0003`, une frame de vidéo **inclinée et en
perspective**, en normalisant par la **bbox alignée aux axes**. Deux biais qui
se cumulent :

1. Pour un objet paysage tourné de θ, la bbox alignée donne
   `bboxW/bboxH = (W·cosθ + H·sinθ) / (W·sinθ + H·cosθ)`, qui est **toujours
   inférieur** à `W/H`. Mes 1,619 et 1,726 étaient donc des **planchers**, pas
   des mesures — et je les ai lus comme confirmant 1,655.
2. La perspective comprimait le côté droit de l'objet, ce qui a tiré vers la
   gauche toutes les positions mesurées de ce côté (D-pad, slider gain).

Résultat : le boîtier était trop trapu et la moitié droite de la face décalée
de plus d'un centimètre.

**Règle à retenir : ne jamais mesurer un layout sur une vue en perspective.
Redresser d'abord, ou exiger une vue orthographique.**

## Cotes maîtresses

| Grandeur | v3 | **v4** |
|---|---|---|
| Ratio W/H | 1,655 | **1,740** |
| Largeur W | 16,0 BU | 16,0 BU (hypothèse inchangée) |
| Hauteur H | 9,667 | **9,195** |
| Rayon de coin | 2,30 | **2,10** |
| Épaisseur T | 2,70 | 2,70 (v3, pas revue ici) |

## La grille de design

C'est ce que la vue redressée révèle et que la perspective cachait :

- **deux colonnes** : u ≈ **0,202** (molette + SYNC) et u ≈ **0,787** (slider gain + D-pad + logo)
- **deux rangées** : v ≈ **0,394** (molette + knob de gain) et v ≈ **0,697** (SYNC + slider horizontal + D-pad)
- **écran centré en largeur** : centre u = 0,500

## Layout face (u, v)

| Élément | u | v | Taille | v3 → écart |
|---|---|---|---|---|
| Écran | 0,269 → 0,730 | 0,226 → 0,569 | 7,38 × 3,15 BU | était décentré à gauche |
| Molette | 0,200 | 0,394 | drum ⌀1,05 × 0,49 · ensemble 1,56 | dômes trop petits |
| SYNC | 0,205 | 0,697 | ⌀ 1,71 BU | **+0,45 BU à droite, plus bas** |
| Rail slider H | 0,321 → 0,675 | 0,697 | long 5,66 · haut 0,76 | **était 5,02, trop court** |
| Cap slider H | ≈ 40 % de la course | 0,697 | 0,51 × 0,99 | était en butée gauche |
| Fente gain | 0,784 | 0,274 → 0,546 | long 2,50 | **+0,74 BU à droite** |
| Knob gain | 0,784 | 0,394 | ⌀ ≈ 0,40 | aligné sur la molette |
| D-pad | 0,792 | 0,697 | 2,18 BU | **+1,20 BU à droite** |
| Wordmark | 0,417 → 0,578 | 0,150 → 0,202 | — | |
| Logo `U.` | 0,786 | 0,175 | — | |
| `LOW BATT` | 0,289 | 0,819 | — | |
| Plaque encastrée | 0,111 → 0,889 | 0,095 → 0,885 | — | |

**Supprimé :** la pastille « power » du coin haut-droit. Elle venait de
`refB f_0003` et n'apparaît pas sur la vue de face — on ne garde pas une
feature non vérifiée.

## Réserves

- Le fichier image n'était pas sur disque : ces valeurs sont **lues sur
  l'affichage**, pas extraites au pixel. L'ordre de grandeur des corrections
  (jusqu'à 1,2 BU) dépasse largement l'erreur de lecture, mais un passage au
  pixel affinerait la 3ᵉ décimale. Fichier bienvenu.
- La référence est une version **plus avancée** de l'objet : son écran et son
  UI diffèrent des vidéos. Sur demande de Sliz, **l'écran actuel est conservé
  pour l'instant** ; seules les proportions des contrôles sont reprises.
- Le wordmark et le logo utilisent encore la police par défaut de Blender.
  C'est faux et ça se voit — il faut les extraire de l'image source.
