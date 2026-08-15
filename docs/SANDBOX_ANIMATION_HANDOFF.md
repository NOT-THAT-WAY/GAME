# Handoff animations — personnage sandbox

Ce document est le contrat de travail pour l'agent Blender. Le gameplay est déjà autoritaire et les
paramètres Animator sont créés par `M1PlaytestBuild` ; l'animation doit présenter ces décisions,
jamais les prendre.

## Prompt complet à donner à l'agent Blender

```text
Utilise obligatoirement $blender-production-studio dans le dépôt GAME.

Objectif : produire, une animation à la fois et dans l'ordre indiqué par
docs/SANDBOX_ANIMATION_HANDOFF.md, les clips minimaux du personnage sandbox à partir de
Assets/_Project/Player/PersoBouleRigged.fbx. Commence uniquement par SB_Idle et arrête-toi après son
export, sa réimportation indépendante et son rapport de validation ; j'autoriserai ensuite le clip
suivant. Ne modifie aucune règle gameplay, aucun collider, aucun script réseau et aucun paramètre
Animator.

Contraintes : Blender 5.1.1, Unity 6000.3.20f1, rig Generic existant, 30 fps, unités métriques,
root motion nul, squelette et noms d'os conservés, maximum 4 influences par vertex, aucun nouvel os
de déformation sans justification. Supprime de l'export les objets parasites Cube/Camera/Light.
Les sources .blend et rendus lourds restent dans tools/blender-agent-studio/local_work ; seul un FBX
runtime validé peut entrer dans Assets/_Project/Player, sans changer le GUID du .meta existant.

Pour chaque clip : respecte exactement le nom, la plage, le mode loop/non-loop et les contacts
décrits dans le document ; vérifie silhouettes et pénétrations en vues face/profil/3-4 ; pour une
boucle, vérifie la couture sans dupliquer visiblement la première pose ; exporte avec Bake Animation
à 30 fps et Simplify 0 ; réimporte le FBX dans une scène Blender propre ; vérifie ensuite l'import
dans Unity Generic, le nom du clip, sa durée, son loop flag, le root immobile et l'absence d'erreur.

Rends à la fin de chaque clip : chemin source local, chemin export, nom d'Action, plage/fps/durée,
loop flag, os animés, contrôles de contact, captures face/profil/3-4, résultat de réimport Blender,
résultat d'import Unity, limites restantes et statut PASS/FAIL. N'ajoute aucun AnimationEvent de
gameplay : les éventuels marqueurs ne servent qu'aux futurs sons/VFX.
```

## Audit du FBX actuel

Source runtime : `Assets/_Project/Player/PersoBouleRigged.fbx`.

- rig Generic, échelle d'armature `(1,1,1)`, origine `(0,0,0)` ;
- 10 os : `root`, `body`, deux chaînes `upperarm/forearm/hand`, deux pieds rattachés au root ;
- 9 meshes skinnés, 2 870 vertices et 5 664 triangles au total ;
- une Action importée : `BAS_PUNCH_Rig|BAS_PUNCH_Rig|BAS_PUNCH_punch`, images 1–20 à 24 fps ;
- Unity importe actuellement une seule animation et le générateur l'utilise comme `Punch` ;
- le FBX contient aussi un Cube non skinné de 12 triangles ainsi que Camera/Light. Ils ne doivent
  pas revenir dans le prochain export runtime ;
- limite Unity actuelle : 6 000 triangles, 16 os, 4 influences par vertex, personnage haut de
  1,30 à 1,45 m ;
- `applyRootMotion = false` et aucun collider n'est autorisé dans le visuel.

Le clip de poing existant est un placeholder utile. Il faut préserver sa lisibilité, mais le
réexporter au nouveau contrat 30 fps et au nom canonique `SB_Punch` avant de le considérer final.

## Paramètres déjà exposés par le code

| Paramètre Animator | Type | Propriétaire / sens |
| --- | --- | --- |
| `MoveSpeed` | float | vitesse horizontale de la simulation, en m/s |
| `Grounded` | bool | contact sol simulé |
| `Sprinting` | bool | présentation locomotion rapide |
| `Carrying` | bool | la case active contient un objet |
| `CarryKind` | int | `0` vide, `1` caillou, `2` trophée |
| `KnockedOut` | bool | état KO durable |
| `Push` | bool | pose/boucle de poussée tant que l'intention reste autorisée |
| `Jump`, `Land` | trigger | transitions verticales |
| `Punch`, `Throw` | trigger | actions primaires acceptables localement puis validées serveur |
| `Hit`, `Knockout`, `Recover` | trigger | réactions décidées par le serveur |
| `Pickup`, `Drop`, `Deposit` | trigger | présentation des changements d'objet décidés par le serveur |

Les paramètres sont validés lors de la génération de scène. L'agent Blender ne doit ni les renommer
ni écrire de script pour les piloter. L'intégration des motions dans le contrôleur généré se fait
après livraison des clips ; aujourd'hui seuls `Idle`, `Punch` et la pose `Push` de secours existent.

## Règles communes à tous les clips

- 30 fps ; Action Blender distincte ; un clip par Action ; préfixe exact `SB_`.
- Animation in-place : `root` ne se translate ni ne pivote. Les déplacements viennent du moteur.
- Pas d'AnimationEvent nécessaire au gameplay. Un marqueur optionnel `SFX_*` ou `VFX_*` est
  documentaire et ne conditionne jamais dégâts, dépense, lancer, ramassage ou dépôt.
- Les boucles n'embarquent pas une dernière pose dupliquée perceptible ; vérifier position et
  vitesse à la couture.
- Garder le volume sphérique lisible, les pieds en contact, les poings hors du corps et limiter les
  auto-intersections. La caméra doit rester correcte en première comme en troisième personne.
- Le même jeu de clips sert d'abord au caillou et au trophée. `CarryKind` permet une variante future,
  mais aucune duplication n'est demandée pour cette passe.
- Les objets sont attachés par le code, pas par contrainte exportée depuis Blender.

## Liste d'exécution, un clip à la fois

Les plages sont inclusives et représentent le nombre de poses échantillonnées à 30 fps.

| Ordre | Action / clip | Plage | Loop | Intention et contrôle principal |
| ---: | --- | ---: | :---: | --- |
| 1 | `SB_Idle` | 1–60 | oui | respiration/poids subtil, pieds fixes, couture invisible |
| 2 | `SB_Walk` | 1–30 | oui | marche énergique in-place, contacts gauche/droite stables |
| 3 | `SB_Sprint` | 1–24 | oui | cycle plus penché et plus ample, silhouette distincte de Walk |
| 4 | `SB_JumpTakeoff` | 1–12 | non | compression puis extension, fin compatible avec Airborne |
| 5 | `SB_Airborne` | 1–24 | oui | pose aérienne vivante, sans battement excessif des membres |
| 6 | `SB_Land` | 1–12 | non | réception lisible, pieds sans glisse, retour compatible locomotion |
| 7 | `SB_Push` | 1–30 | oui | mains en appui stable devant, effort continu, couture sans saut |
| 8 | `SB_Punch` | 1–20 | non | anticipation courte, impact visuel vers l'image 10, récupération nette |
| 9 | `SB_Pickup` | 1–24 | non | lecture vers le sol puis retour en port, sans translation root |
| 10 | `SB_CarryIdle` | 1–60 | oui | objet tenu devant, respiration compatible avec l'attache code |
| 11 | `SB_CarryWalk` | 1–30 | oui | marche in-place avec mains stables autour du volume porté |
| 12 | `SB_Throw` | 1–24 | non | armé, projection, release visuel vers l'image 12, suivi du geste |
| 13 | `SB_Drop` | 1–18 | non | ouverture des mains et retrait léger, objet libéré par le code |
| 14 | `SB_HitReact` | 1–18 | non | réaction franche mais courte, centre de masse restant in-place |
| 15 | `SB_Knockout` | 1–30 | non | perte d'équilibre et arrivée au sol sans téléportation du root |
| 16 | `SB_KnockedOutLoop` | 1–60 | oui | pose au sol quasi immobile, couture et contacts stables |
| 17 | `SB_Recover` | 1–36 | non | retour debout depuis la pose KO, fin compatible avec Idle |
| 18 | `SB_Deposit` | 1–30 | non | geste de présentation/dépôt du trophée vers l'avant |

### Ordre de branchement Unity après livraison

1. Locomotion au sol : `Idle`, `Walk`, `Sprint`, puis leurs variantes `CarryIdle/CarryWalk` selon
   `Carrying` ; seuils pilotés par `MoveSpeed` et `Sprinting`.
2. Air : `JumpTakeoff -> Airborne -> Land`, piloté par `Grounded`, `Jump` et `Land`.
3. `Push` maintient `SB_Push` et rend la main à la locomotion au relâchement.
4. `Punch`, `Throw`, `Pickup`, `Drop`, `Deposit` sont des one-shots qui reviennent vers la bonne
   locomotion ; aucune transition ne porte une règle de dégâts.
5. `Hit` interrompt les actions ordinaires. `Knockout` est prioritaire sur tout, mène à
   `KnockedOutLoop`, puis `Recover` ramène vers `Idle`.

## Gates de réception de chaque clip

Un clip est accepté uniquement si les cinq verdicts suivants sont PASS :

1. **Contrat** : bon nom, 30 fps, bonne plage, loop flag exact, root immobile.
2. **Physique visuelle** : contacts et arcs crédibles, pas de glisse ou pénétration importante.
3. **Réimport Blender** : FBX rouvert dans une scène vide, Action et pose retrouvées.
4. **Import Unity** : rig Generic valide dans Unity 6000.3.20f1, aucun warning, budget respecté.
5. **Preuve** : captures face/profil/3-4 et mini preview de boucle ou de l'action complète.

La production peut s'arrêter après n'importe quel clip sans rendre le gameplay inutilisable : le
contrôleur actuel reste un fallback. C'est volontaire pour permettre la validation réellement
« un par un » demandée pour cette passe.
