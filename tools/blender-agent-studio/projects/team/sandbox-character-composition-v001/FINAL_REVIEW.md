# Revue finale — sandbox-character-composition-v001

Deux passes successives. La passe technique (GPT) a produit une baseline neutre et vérifiée. Cette
passe-ci est la **direction artistique** posée par-dessus, appelée `arena-echo`.

## Intention créative

> La mascotte se tient dans son terrain de jeu : un sol d'arène chaud éclairé par-dessus, un fond
> froid qui recule, et l'orange de la zone de dépôt qui revient en accent au dos du personnage.

Deux décisions ont été prises par la revue humaine avant l'itération, pas par l'agent :
la direction (`écho de l'arène`) et le **maintien du contrat de cadrage** (composition centrée
±0,08, profondeur de champ interdite). `validate_composition_scene.py` n'a donc pas été modifié :
aucun seuil n'a été élargi pour faire passer un résultat.

## Verdict

`arena-echo` est **candidat accepté sous revue humaine**. Les onze contrôles de cadrage passent sur
60/60 images. Aucun échec critique. Rien n'a été commité, poussé, ni écrit sous `Assets/_Project/`.

| Gate | Verdict |
|---|---|
| Physique (root, contact sol, safe frame) | PASS |
| Composition clay / silhouette | PASS |
| Poses clés | PASS |
| Corridor caméra | PASS |
| Focus | PASS (DOF volontairement désactivée) |
| Couches de lumière | PASS |
| Réponse matière | PASS |
| Preview mouvement complet | PASS |
| Contact sheets | PASS |
| ffprobe | PASS |

## La palette n'est pas inventée

Chaque couleur est dérivée du jeu lui-même, `Assets/_Project/Editor/M1PlaytestBuild.cs` :

| Rôle | Valeur linéaire | Source |
|---|---|---|
| Accent (rim) | `1.00, 0.28, 0.04` | `:1102` `SandboxDeposit` — la zone de dépôt |
| Key | `1.00, 0.92, 0.82` | `:838` |
| Fill | `0.62, 0.72, 0.95` | `:849` |
| Fond | teinte de `0.16, 0.19, 0.26` | `:91` `HorizonColor`, valeur abaissée |
| Sol lointain | dérivé de `0.10, 0.11, 0.14` | `:1144` `M1DecorGround` |
| Argile près des pieds | dérivé de `0.24, 0.21, 0.20` | `:1147` `M1DecorPillarWarm` |

## Mesures, baseline C → arena-echo

| Mesure | Baseline C | arena-echo | Seuil |
|---|---|---|---|
| Images dans le safe frame | 60/60 | 60/60 | toutes |
| Couverture hauteur | 0,766–0,779 | 0,729–0,742 | 0,64–0,82 |
| Couverture largeur | 0,500 | 0,504 | ≤ 0,70 |
| Offset centre | 0,0068 / 0,0188 | **0,0038** / 0,0308 | ≤ 0,08 |
| Marge haute | 0,123 | **0,154** | — |
| Marge basse | 0,098 | **0,105** | — |
| Clearance caméra | 5,110 m | 4,814 m | ≥ 0,08 |
| Sol / root | 0,000000 / 0,000000 | 0,000000 / 0,000000 | ≈ 0 |

## Deux défauts trouvés et corrigés, dont un hérité

1. **Le rim de la baseline n'éclairait pas le personnage.** Mesure sur le mesh du décor : le mur du
   cyclorama est vertical à `y = 2,80` au-dessus de `z = 1,0`. Le rim de la baseline était à
   `y = 3,70`, donc **derrière le mur**. C'est pourquoi, dans sa contact sheet lumière, « key+fill »
   et « lumière complète » étaient presque identiques. Mon premier essai reproduisait la même erreur
   à `y = 3,15`. Le rim final est à `y = 1,30`, devant le mur, et grave une arête réelle.
2. **Le bras écran-gauche se noyait dans le corps.** Défaut géométrique, pas d'éclairage : à
   `x = 2,55` l'angle trois-quarts était assez fort pour que le bras passe devant le corps. Réduit à
   `x = 1,75`, les deux bras se détachent.

## Itérations, une catégorie à la fois

| Catégorie | Essais | Rejets |
|---|---|---|
| Décor et palette | 2 / 3 | Essai 1 : anneau orange peint dont la rampe ne redescendait jamais à zéro (`sin(1)≈0,84` constant au-delà de 2,30 m) — tout le sol et le fond viraient rose, séparation **pire** que la baseline. |
| Éclairage | 3 / 3 | Essai 1 : rim derrière le mur. Essai 2 : rim devant le mur mais à 300 W, inondant le sol d'orange. |
| Caméra hero | 1 / 3 | — |

Détail complet et daté : `evidence/iteration-log-claude.json`.

## Livrables

- master : `local_work/.../work/sandbox_character_composition_claude_v001.blend`
- image finale : `local_work/.../renders/claude-final/final/neutral-design-baseline.png`
- comparaison : `.../final/comparison-baseline-c-vs-claude-arena-echo.png`
- contact sheets hero / contrôles / lumière : `.../final/contact-sheet-*.png`
- boucle ×4 : `.../final/sb-idle-arena-echo-loop-x4.mp4` — 960×540, 30 fps, 240 images, 8,0 s
- étapes d'itération conservées : `claude_L1_stage.blend`, `claude_L2_light.blend`, `claude_L3_camera.blend`

## Ce qui reste verrouillé et intact

Personnage, rig, Actions et matériaux du personnage : non touchés. Master d'animation intact
(`864807e9…0464`). `Assets/_Project/Player/PersoBouleRigged.fbx` intact (`4503459d…1cce1`).
Budgets déclarés tenus : **0** mesh de présentation ajouté, **0** lumière ajoutée, **0** caméra
ajoutée — l'existant a été modifié, jamais complété.

## Limites et décision humaine

1. **Le fond est moins neutre qu'avant, volontairement.** Le rebond orange s'étale sur le sol et le
   bas-droit du cadre. C'est le prix de l'accent narratif ; si la cible devient une vue de revue
   technique plutôt qu'une image de présentation, la baseline C reste le meilleur choix.
2. **L'éclairage a consommé ses 3 essais.** Le résultat est bon mais n'a pas été poussé au-delà ;
   un quatrième essai demanderait une nouvelle passe déclarée.
3. **Cadrage centré assumé.** Sur décision humaine, aucune composition asymétrique ni profondeur de
   champ n'a été tentée. Ces deux leviers restent disponibles via un contrat explicitement redéclaré.
4. **Le grain d'Eevee à 64 samples** reste visible dans les ombres douces du sol. Non corrigé :
   monter les samples dépasserait `render_samples_max` déclaré.
5. **Le jugement de goût n'est pas délégable.** Les gates prouvent le cadrage, les contacts et la
   séparation. Le choix entre la neutralité de la baseline et le parti pris `arena-echo` appartient
   à la revue humaine devant `comparison-baseline-c-vs-claude-arena-echo.png`.
