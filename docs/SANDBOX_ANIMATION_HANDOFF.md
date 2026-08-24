# Handoff animations — personnage sandbox

Ce document est le contrat de travail pour l'agent Blender. Le gameplay est déjà autoritaire et les
paramètres Animator sont créés par `M1PlaytestBuild` ; l'animation doit présenter ces décisions,
jamais les prendre.

## Prompts de production par pôle

Les deux agents exécutent chacun leur lot complet dans une seule mission, sans attendre une
validation humaine entre les clips. La validation reste néanmoins individuelle : un clip en échec
n'est jamais présenté comme accepté et ne bloque les clips suivants que si la cause est systémique.

- Claude / Opus 5 : `docs/CLAUDE_SANDBOX_ANIMATION_POLE_PROMPT.md` ;
- Kimi : `docs/KIMI_SANDBOX_ANIMATION_POLE_PROMPT.md`.

Les deux prompts ont priorité sur l'ancien mode « un clip puis arrêt ». Chaque pôle possède un seul
projet Studio, un seul master `.blend` versionné par checkpoints et une Action distincte par clip.

## Audit du FBX actuel

Source runtime : `Assets/_Project/Player/PersoBouleRigged.fbx`.

- rig Generic, échelle d'armature `(1,1,1)`, origine `(0,0,0)` ;
- 10 os : `root`, `body`, deux chaînes `upperarm/forearm/hand`, deux pieds rattachés au root ;
- 9 meshes skinnés, 2 870 vertices et 5 664 triangles au total ;
- une Action importée : `BAS_PUNCH_Rig|BAS_PUNCH_Rig|BAS_PUNCH_punch`, images 1–20 à 24 fps ;
- Unity importe actuellement une seule animation et le générateur l'utilise comme `Punch` ;
- le FBX ne contient aucun Cube, Camera ou Light ; ce contrôle doit malgré tout être rejoué sur
  chaque candidat pour empêcher l'ajout de parasites de scène ;
- limite Unity actuelle : 6 000 triangles, 16 os, 4 influences par vertex, personnage haut de
  1,30 à 1,45 m ;
- `applyRootMotion = false` et aucun collider n'est autorisé dans le visuel.

Les dix os portent réellement le préfixe `BAS_PUNCH_`. Le personnage est composé de pièces rigides,
chaque vertex n'ayant qu'une influence, et ne possède ni jambes ni genoux : les pieds sont rattachés
directement au root. Aucun agent ne doit inventer une articulation ou du squash/stretch absent du
rig. Le clip de poing existant est un placeholder utile. Il faut préserver sa lisibilité, mais le
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
| `Push` | bool | pose/boucle du joueur qui pousse le mur tant que son intention reste active |
| `WallPushed` | bool, à ajouter | réaction durable du joueur déplacé par le volume balayé du mur |
| `WallPushSpeed` | float, à ajouter | vitesse tangentielle externe décidée par le serveur, en m/s, de 0 à 3,5 |
| `Jump`, `Land` | trigger | transitions verticales |
| `Dive` | trigger | décollage du plongeon avant (remplace `Jump` sur ce décollage) |
| `Diving` | bool | vol du plongeon, jusqu'au contact sol |
| `DiveRecovering` | bool | relevé au sol après le plongeon, joueur immobile |
| `Punch`, `Throw` | trigger | actions primaires acceptables localement puis validées serveur |
| `Hit`, `Knockout`, `Recover` | trigger | réactions décidées par le serveur |
| `Pickup`, `Drop`, `Deposit` | trigger | présentation des changements d'objet décidés par le serveur |

Les paramètres sont validés lors de la génération de scène. L'agent Blender ne doit ni les renommer
ni écrire de script pour les piloter. `WallPushed` et `WallPushSpeed` sont réservés par ce contrat,
mais ne sont pas encore exposés par le code. L'intégration des motions dans le contrôleur généré se
fait après livraison des clips ; aujourd'hui seuls `Idle`, `Punch` et la pose `Push` de secours
existent.

## Règles communes à tous les clips

- 30 fps ; Action Blender distincte ; un clip par Action ; préfixe exact `SB_`.
- Animation in-place : `root` ne se translate ni ne pivote. Les déplacements viennent du moteur.
- Pour `Walk`, `Sprint` et `CarryWalk`, déclarer une vitesse nominale de cycle et contrôler le pied
  d'appui dans un repère reconstruit qui ajoute cette translation virtuelle. Un pied n'a pas à rester
  immobile dans le repère local d'un clip in-place ; il doit rester stable dans le monde reconstruit.
- Pas d'AnimationEvent nécessaire au gameplay. Un marqueur optionnel `SFX_*` ou `VFX_*` est
  documentaire et ne conditionne jamais dégâts, dépense, lancer, ramassage ou dépôt.
- Les boucles n'embarquent pas une dernière pose dupliquée perceptible ; vérifier position et
  vitesse à la couture.
- Garder le volume sphérique lisible, les pieds en contact, les poings hors du corps et limiter les
  auto-intersections. La caméra doit rester correcte en première comme en troisième personne.
- Le même jeu de clips sert d'abord au caillou et au trophée. `CarryKind` permet une variante future,
  mais aucune duplication n'est demandée pour cette passe.
- Les objets sont attachés par le code, pas par contrainte exportée depuis Blender.

## Liste canonique de première passe — 19 clips

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
| 8 | `SB_WallPushed` | 1–24 | oui | déséquilibre entretenu par le mur, petits pas de rattrapage, root in-place |
| 9 | `SB_Punch` | 1–20 | non | anticipation courte, impact visuel vers l'image 10, récupération nette |
| 10 | `SB_Pickup` | 1–24 | non | lecture vers le sol puis retour en port, sans translation root |
| 11 | `SB_CarryIdle` | 1–60 | oui | objet tenu devant, respiration compatible avec l'attache code |
| 12 | `SB_CarryWalk` | 1–30 | oui | marche in-place avec mains stables autour du volume porté |
| 13 | `SB_Throw` | 1–24 | non | armé, projection, release visuel vers l'image 12, suivi du geste |
| 14 | `SB_Drop` | 1–18 | non | ouverture des mains et retrait léger, objet libéré par le code |
| 15 | `SB_HitReact` | 1–18 | non | réaction franche mais courte, centre de masse restant in-place |
| 16 | `SB_Knockout` | 1–30 | non | perte d'équilibre et arrivée au sol sans téléportation du root |
| 17 | `SB_KnockedOutLoop` | 1–60 | oui | pose au sol quasi immobile, couture et contacts stables |
| 18 | `SB_Recover` | 1–36 | non | retour debout depuis la pose KO, fin compatible avec Idle |
| 19 | `SB_Deposit` | 1–30 | non | geste de présentation/dépôt du trophée vers l'avant |

Cette liste est exhaustive pour la première passe du gameplay actuel. Elle exclut volontairement
les strafes directionnels, le recul, la rotation sur place, `CarrySprint`, les variantes
caillou/trophée et les réactions de poussée gauche/droite. La première passe réutilise
`SB_CarryWalk` avec une vitesse de lecture pilotée par `MoveSpeed`, et une seule réaction
`SB_WallPushed` indépendante de la direction. Ces variantes ne doivent pas être inventées par un
agent sans nouveau contrat.

## Fiches de mouvement concrètes

Les images citées sont des poses de lecture, pas des AnimationEvents de gameplay.

1. **`SB_Idle` — 1–60, boucle.** Respiration très légère, transfert de poids lent et décalage
   secondaire des bras. Les deux pieds restent plantés ; l'image 60 n'est pas une copie visible de
   l'image 1 et la vitesse reste continue à la couture. Ce clip est déjà candidat validé et sert de
   référence de proportions et d'amplitude.
2. **`SB_Walk` — 1–30, boucle.** Contact gauche image 1, passage image 8, contact droit image 16,
   second passage image 23. Marche volontaire et compacte, sans translation du root ; les pieds
   plantés ne glissent pas dans le repère reconstruit à la vitesse nominale déclarée.
3. **`SB_Sprint` — 1–24, boucle.** Contact gauche image 1, suspension/passage image 7, contact droit
   image 13, seconde suspension image 19. Inclinaison et amplitude nettement supérieures à Walk,
   mais silhouette toujours lisible et root immobile.
4. **`SB_JumpTakeoff` — 1–12, one-shot.** Pose prête image 1, compression maximale image 4,
   extension maximale images 8–9, pose aérienne compatible image 12. Les pieds quittent le sol par
   la pose, jamais par translation du root.
5. **`SB_Airborne` — 1–24, boucle.** Pose aérienne stable avec faible balancier des pieds et des
   bras, sans pédalage. La boucle doit pouvoir durer plusieurs ticks et rejoindre Land sans pop.
6. **`SB_Land` — 1–12, one-shot.** Le gameplay déclenche le clip après le contact : image 1 déjà au
   sol, compression maximale vers l'image 5, retour prêt à Idle/Walk image 12. Aucun faux saut avant
   le contact.
7. **`SB_Push` — 1–30, boucle.** Le joueur agit : pieds écartés, volume du corps légèrement abaissé
   et penché vers le mur autour de son vrai pivot, mains stables devant. L'effort respire sans faire
   pomper les mains ni faire glisser les appuis.
8. **`SB_WallPushed` — 1–24, boucle.** Le joueur subit : volume du corps en retard sur le
   déplacement, bascule amortie autour de son pivot, bras en contrepoids et petits pas alternés de
   rattrapage avec les deux pieds détachés. Le rig n'ayant pas de genoux, aucun pli de jambe ne doit
   être simulé. Le root reste in-place ; la translation vient uniquement de la simulation. Le clip
   ne contient pas un nouvel impact à chaque boucle et doit rester crédible entre 1 et 3,5 m/s.
9. **`SB_Punch` — 1–20, one-shot.** Garde image 1, anticipation images 3–5, extension/impact visuel
   image 10, suivi images 11–13, récupération image 20. Les poings ne traversent jamais le corps.
10. **`SB_Pickup` — 1–24, one-shot.** Lecture vers le sol, flexion et portée basse vers l'image 8,
    prise visuelle vers l'image 12, remontée images 13–20, fin compatible CarryIdle image 24.
11. **`SB_CarryIdle` — 1–60, boucle.** Même calme que Idle, mais avant-bras et mains entourent un
    volume porté devant le torse. Les mains dérivent très peu ; aucun contact exact avec un prop
    Blender n'est exporté.
12. **`SB_CarryWalk` — 1–30, boucle.** Phases de pieds identiques à Walk, corps un peu plus stable,
    mains conservant le volume porté. Le clip couvre marche et sprint porté lors de cette passe via
    sa vitesse de lecture, sans créer `SB_CarrySprint`.
13. **`SB_Throw` — 1–24, one-shot.** Pose portée image 1, armé images 4–7, accélération images 8–11,
    release visuel image 12, suivi images 13–17, récupération image 24. Aucun projectile ni
    événement de dégâts n'est exporté.
14. **`SB_Drop` — 1–18, one-shot.** Pose portée image 1, ouverture des mains vers l'image 6,
    release visuel images 8–9, léger retrait des bras, retour neutre image 18.
15. **`SB_HitReact` — 1–18, one-shot.** Impact perceptible images 2–3, recul du haut du corps et
    protection du visage jusqu'à l'image 8, récupération courte jusqu'à l'image 18. Pas de chute et
    pas de root motion.
16. **`SB_Knockout` — 1–30, one-shot.** Rupture d'équilibre images 1–8, descente contrôlée,
    premier contact au sol avant l'image 22, stabilisation image 30 dans exactement la pose de
    départ de `SB_KnockedOutLoop`.
17. **`SB_KnockedOutLoop` — 1–60, boucle.** Corps au sol, contacts stables, respiration à peine
    visible, aucune dérive. La pose reste lisible comme KO et non comme Idle couché.
18. **`SB_Recover` — 1–36, one-shot.** Image 1 identique à la boucle KO, appui des mains puis
    redressement, reprise des pieds sous le corps, image 36 compatible avec `SB_Idle`.
19. **`SB_Deposit` — 1–30, one-shot.** Présentation du trophée images 1–10, extension vers la zone,
    release visuel vers l'image 15, retrait des mains et retour sans objet image 30.

## Répartition recommandée sans conflit

| Agent | Lot cohérent | Clips |
| --- | --- | --- |
| Claude / Opus 5 | locomotion, verticalité et interactions d'objet | `SB_Walk`, `SB_Sprint`, `SB_JumpTakeoff`, `SB_Airborne`, `SB_Land`, `SB_Pickup`, `SB_CarryIdle`, `SB_CarryWalk`, `SB_Throw`, `SB_Drop`, `SB_Deposit` |
| Kimi | forces, combat et états de vie | `SB_Push`, `SB_WallPushed`, `SB_Punch`, `SB_HitReact`, `SB_Knockout`, `SB_KnockedOutLoop`, `SB_Recover` |

`SB_Idle` reste la référence commune déjà validée ; aucun agent ne le régénère. Chaque agent crée
un projet et un workspace distincts par pôle, ne sauvegarde jamais dans le master de l'autre agent
et ne modifie pas le FBX runtime. Chaque clip reste une Action et un FBX candidat séparés. Les FBX
candidats sont fusionnés seulement par l'intégrateur après validation individuelle.

### Ordre de branchement Unity après livraison

1. Locomotion au sol : `Idle`, `Walk`, `Sprint`, puis leurs variantes `CarryIdle/CarryWalk` selon
   `Carrying` ; seuils pilotés par `MoveSpeed` et `Sprinting`.
2. Air : `JumpTakeoff -> Airborne -> Land`, piloté par `Grounded`, `Jump` et `Land`.
3. `Push` maintient `SB_Push` pour le pousseur. `WallPushed` maintient `SB_WallPushed` pour la
   victime ; `WallPushSpeed` module seulement l'intensité ou la vitesse de lecture.
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

Dans chaque pôle, l'agent continue automatiquement jusqu'au dernier clip après chaque validation.
Après trois corrections sans amélioration sur un clip, il le marque `FAIL`, conserve les preuves et
passe au suivant. Il arrête tout le pôle uniquement pour une panne systémique : source/hash faux,
rig cassé, workspace non isolé, session MCP étrangère ou dépendance indispensable indisponible. Le
contrôleur actuel reste le fallback tant que l'intégrateur n'a pas accepté les candidats.
