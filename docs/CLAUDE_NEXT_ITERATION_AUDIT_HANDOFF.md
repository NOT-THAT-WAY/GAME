# Handoff Claude — audit gameplay, physique et animation du sandbox

Date de l'audit : 2026-08-16

Projet : `GAME` — Unity `6000.3.20f1`

Nature de cette passe : audit en lecture seule du jeu et des sources Blender, sans promotion d'asset canonique.

## Mission de reprise

Reprendre le prototype existant et faire une passe **intégration d'abord**. Le jeu est assez stable
pour continuer, mais il ne faut pas commander ou retoucher beaucoup de nouvelles animations avant
que les 7 clips combat/réaction déjà livrés soient réellement branchés dans Unity, que les phases
d'impact/release soient synchronisées au tick, et que les deux défauts physiques encore ouverts
soient traités.

Ordre recommandé :

1. préserver et revalider les sources Blender ;
2. intégrer le lot Kimi/Claude complet dans le contrôleur de playtest ;
3. corriger le lancer près d'un mur et les warnings Rigidbody ;
4. corriger la poussée saccadée par le mur, puis seulement ajouter la réaction animée ;
5. faire un playtest humain de goût et décider quelles animations méritent une seconde passe.

## Verdict rapide

| Zone | Verdict | Pourquoi |
|---|---|---|
| Base Unity/réseau | **saine pour continuer** | 125/125 tests EditMode, build macOS réussi, session manuelle sans exception ni divergence observée |
| Lot Claude mouvement/objets | **techniquement bon, intégration partielle** | 11/11 clips passent les portes ; ils sont utilisés dans le playtest, avec des réserves de rythme et de contact objet |
| Lot Kimi force/combat | **techniquement bon, non intégré** | 7/7 clips passent le contrat, mais le contrôleur Unity actuel ne les charge pas |
| Sources Blender | **récupérables, manifeste actuellement invalide** | les `.blend` maîtres ont été resauvegardés après livraison ; les `.blend1` conservent exactement les versions hashées |
| Lancer près d'un mur | **défaut encore ouvert** | le projectile est téléporté à `0,8 m` devant le joueur sans test de dégagement initial |
| Joueur balayé par le mur | **défaut de sensation encore ouvert** | correction de vitesse envoyée par impulsions toutes les 2 ticks ; une animation seule ne supprimera pas les saccades |
| Bot | **bon mannequin de test, pas une IA finale** | il frappe et fait tourner le mur, mais ses timers, son état réseau et sa poussée restent des raccourcis de prototype |
| Composition Blender | **paquet valide, choix créatif à goûter** | 13/13 fichiers validés ; la composition `arena-echo` reste une proposition de direction artistique |

Conclusion : **ne pas refaire les clips à zéro**. Les problèmes prioritaires sont surtout dans le
graphe d'animation, la synchronisation gameplay/visuel et la physique de release/poussée.

## Preuves de l'état actuel

### Unity

- Résultats : `Logs/M1PlaytestClaude/bot-editmode-results-20260816.xml` — **125 passés,
  0 échec, 0 ignoré**.
- Build : `Logs/M1PlaytestClaude/build-bot-final-20260816.log` — `Build Finished, Result: Success`.
- Binaire : `Builds/M1PlaytestClaude/macOS/GAME-M1-Claude-Animations.app`.
- SHA-256 de l'exécutable `Contents/MacOS/GAME` :
  `9f40802e76a27519c2ee3f6df389f05749da04a498a13e4aae6401d089c463aa`.
- Session humaine : `Logs/M1PlaytestClaude/runtime-bot-manual-20260816.log`, environ 138 s.
- Aucun `NullReferenceException`, `MissingReferenceException` ou `InvalidOperationException` trouvé.
- Heartbeats stables : `server=True`, `client=True`, `players=1`,
  `invalidSnapshots=0`, `historyMisses=0`.
- La rotation réelle du mur a démarré, atteint des quarts de tour et changé de direction.

### Bot pendant la session humaine

- 35 préparations de frappe ;
- 31 impacts ;
- 4 ratés, soit environ 88,6 % de réussite ;
- 11 phases `PushWall`, dont 7 avec contact/poussée effective ;
- un seul coup joueur reçu : santé 100 → 75 ;
- le chemin complet 4 coups → KO → récupération n'a donc **pas** été testé humainement.

### Blender Studio

Revalidation indépendante effectuée avec Blender `5.1.1` :

- composition `sandbox-character-composition-v001` : **valide**, 13 fichiers vérifiés ;
- mouvement/objets Claude : 35 fichiers sur 36 vérifiés, seul le `.blend` maître diffère ;
- force/combat Kimi : 25 fichiers sur 26 vérifiés, seul le `.blend` maître diffère ;
- les 11 FBX Claude copiés sous `Assets/_GeneratedLocal/SandboxAnimClaude` sont octet pour octet
  identiques aux exports livrés ;
- les 7 FBX Kimi copiés sous `Assets/_GeneratedLocal/SandboxAnimKimi` sont octet pour octet
  identiques aux exports livrés.

## Alerte d'intégrité Blender — à traiter avant toute édition

Les manifests ne doivent pas être déclarés valides dans leur état présent.

| Lot | `.blend` actuel | Version attendue par le manifeste | Sauvegarde exacte disponible |
|---|---|---|---|
| Claude | 431 508 octets, SHA `31bb26ea2c525f97869eab34fc40657a6909f242e5604a733496b7d24d5b7afc` | 433 281 octets, SHA `76e4ff91336bf3d979c1de68a4d0e40703d85bdb4d3f4f478e6fafd40a76fc3d` | `sandbox_character_claude_motion_object_master.blend1`, hash attendu exact |
| Kimi | 380 852 octets, SHA `fa2990551042fb43de526dde4f51917f07d3d1d85be4c6ab613d2d3d34e37713` | 379 901 octets, SHA `2b67611d0e44afbdd4a4df6be49b39ab0e34dd78754d78d8dff1a9a004fd791d` | `sandbox_character_kimi_force_combat_master.blend1`, hash attendu exact |

Une comparaison Blender en lecture seule a trouvé, pour chaque lot : mêmes actions, mêmes plages,
mêmes objets, même rig et **même digest de toutes les F-curves, clés, tangentes et interpolations**
entre `.blend` et `.blend1`. Il s'agit donc très probablement d'une resauvegarde binaire, pas d'une
retouche d'animation. Cela ne permet toutefois pas de falsifier le manifeste.

Procédure sûre pour Claude :

1. ne modifier ni le `.blend` ni le `.blend1` directement ;
2. créer une nouvelle copie de travail depuis le `.blend1` validé ;
3. si une retouche est réellement nécessaire, produire un nouveau master/version et un nouveau
   manifeste après toutes les portes ;
4. sinon conserver les FBX déjà validés et ne pas rouvrir Blender pour une simple intégration Unity.

## Inventaire exact des clips disponibles

Tous sont à 30 fps, Generic, in-place, root à l'identité.

| Clip | Images | Boucle | Repère utile | Usage prévu |
|---|---:|:---:|---|---|
| `SB_Idle` | 1–60 | oui | — | état neutre |
| `SB_Walk` | 1–30 | oui | lecture actuelle ×2 dans Unity | marche |
| `SB_Sprint` | 1–24 | oui | lecture actuelle ×2 | sprint |
| `SB_Airborne` | 1–24 | oui | — | maintien en l'air |
| `SB_JumpTakeoff` | 1–12 | non | f12 compatible `Airborne` f1 | départ saut |
| `SB_Land` | 1–12 | non | f12 compatible locomotion | réception |
| `SB_CarryIdle` | 1–60 | oui | — | objet actif immobile |
| `SB_CarryWalk` | 1–30 | oui | lecture actuelle ×2 | marche avec objet |
| `SB_Pickup` | 1–24 | non | prise visuelle f12 | ramassage |
| `SB_Throw` | 1–24 | non | release visuelle f12 | lancer |
| `SB_Drop` | 1–18 | non | release visuelle f9 | lâcher |
| `SB_Deposit` | 1–30 | non | release visuelle f15 | dépôt trophée |
| `SB_Punch` | 1–20 | non | impact visuel f10 | frappe |
| `SB_HitReact` | 1–18 | non | impact visuel f3 | réaction au coup |
| `SB_Push` | 1–30 | oui | contact proxy stable | pousser le mur |
| `SB_WallPushed` | 1–24 | oui | direction neutre | être balayé/poussé |
| `SB_KnockedOutLoop` | 1–60 | oui | boucle sol stable | maintien KO |
| `SB_Knockout` | 1–30 | non | premier contact sol f19 ; f30 = loop f1 | chute KO |
| `SB_Recover` | 1–36 | non | f1 = loop f1 ; f36 compatible Idle | relever |

## Écart principal du contrôleur Unity

Le script `Assets/_GeneratedLocal/Editor/ClaudeAnimationPlaytestBuild.cs` ne charge actuellement que
`SB_Idle`, les 11 clips Claude et le vieux `Punch` de
`Assets/_Project/Player/PersoBouleRigged.fbx`.

État exact du playtest actuel :

- `Punch` utilise encore le clip historique ;
- `Push` utilise une image figée de ce même vieux `Punch` (`speed=0`, `cycleOffset=0.45`) ;
- aucun des 7 FBX Kimi n'est chargé ;
- `Hit`, `Knockout`, `Recover` et `KnockedOut` sont envoyés par le gameplay, mais aucun état du
  contrôleur patché ne les consomme ;
- le bot déclenche les mêmes paramètres, puis masque leur absence avec une inclinaison de root.

### Graphe cible minimal

| Signal gameplay | État/clip | Sortie attendue |
|---|---|---|
| trigger `Punch` | `SB_Punch` | retour locomotion/carry compatible à la fin |
| trigger `Hit` | `SB_HitReact` | retour à l'état précédent si vivant |
| bool `Push` | `SB_Push` en boucle | sortie immédiate quand `Push=false` |
| nouveau bool `WallPushed` | `SB_WallPushed` en boucle | sortie quand la poussée physique lissée cesse |
| nouveau float `WallPushSpeed` | vitesse/intensité de `SB_WallPushed` | uniquement visuel, jamais autoritaire |
| trigger `Knockout` | `SB_Knockout` | enchaîner vers `SB_KnockedOutLoop` |
| bool `KnockedOut` | `SB_KnockedOutLoop` | rester au sol |
| trigger `Recover` | `SB_Recover` | retour Idle/locomotion à la fin |

Priorité des interruptions : `Knockout` > `Hit` > actions ponctuelles > `WallPushed` > `Push` >
locomotion. Un personnage KO ne doit pas entrer dans Punch, Push, Pickup ou Throw.

Critères d'acceptation :

- aucun fallback vers le vieux `Punch` dans ce contrôleur de playtest ;
- les 7 clips Kimi sont chargés par nom et hashés comme les candidats Claude ;
- toutes les boucles sont explicitement configurées ;
- root motion désactivé ;
- test automatique du graphe : Punch, Hit, KO, KO loop, Recover, Push et WallPushed ;
- test humain en vue troisième personne puis première personne.

## P0 — défaut du lancer près d'un mur

### Cause observée

`SandboxCarryable.ThrowFromServer()` calcule toujours :

`origine = position joueur + 0,9 m vers le haut + 0,8 m vers l'avant`.

`ReleaseToWorld()` téléporte ensuite directement le Rigidbody à cette origine et lui donne sa
vitesse. `ContinuousDynamic` protège le déplacement **après** la release, mais ne répare pas un
collider qui naît déjà dans le mur ou derrière lui. C'est exactement le cas décrit par le joueur
quand le lancer part très près d'une paroi.

### Correction attendue

- validation côté serveur avant toute dépense d'énergie ou suppression de l'inventaire ;
- cast du volume réel du carryable entre une origine poitrine sûre et l'origine de release voulue ;
- marge de peau explicite et contrôle final de non-pénétration ;
- si une position sûre existe, release du côté joueur et collision normale avec le mur ;
- si aucune position sûre n'existe, action refusée atomiquement : objet et énergie conservés ;
- ne pas corriger seulement par un offset plus court ni par un mode CCD différent.

Le flux actuel dépense l'énergie et retire l'objet avant `ThrowFromServer`; il faudra donc rendre la
validation transactionnelle, par exemple avec un `TryResolveThrow`/`TryThrowFromServer` qui ne
commit qu'après validation complète.

Tests à ajouter :

- lancer face à un mur avec moins d'un rayon de dégagement ;
- lancer exactement à la limite ;
- lancer parallèle au mur ;
- carryable déjà très proche d'un coin ;
- hôte et client observent le même côté du mur ;
- aucun dégât possible au travers du mur ;
- résultat identique à 30/60/120 fps.

## P0 — warnings Rigidbody au reset

La session contient 21 warnings de chaque type :

- `Setting linear velocity of a kinematic body is not supported.`
- `Setting angular velocity of a kinematic body is not supported.`

Cause : dans `SandboxCarryable.ResetFromServer()`, le code passe d'abord le body en
`isKinematic=true`, puis assigne ses vélocités. `DepositFromServer()` utilise déjà le bon ordre.

Correction attendue : remettre les vélocités à zéro avant le passage en kinematic, repositionner de
façon sûre, puis réactiver la simulation. Ajouter un smoke reset sans warning.

## P1 — poussée du joueur par le mur

L'animation proposée `SB_WallPushed` améliorera la lecture, mais elle ne supprimera pas le défaut
physique. Aujourd'hui `M1AuthoritativeWallDirector` échantillonne le balayage toutes les 2 ticks et
`PredictedPlayerMotor.ApplyPushVelocityFromServer()` injecte des corrections de knockback vers une
vitesse cible. Le propriétaire reçoit donc des corrections discrètes, puis la réconciliation peut
les rendre visibles sous forme de petits à-coups.

Correction recommandée :

1. représenter explicitement un contact de poussée avec une vitesse cible persistante ;
2. maintenir cette cible à chaque tick entre deux mesures, ou mesurer chaque tick dans ce banc réduit ;
3. prédire localement le même état à partir du tick du mur, puis réconcilier l'écart et non réinjecter
   une impulsion intermittente ;
4. garder collision/position autoritaires et appliquer le lissage seulement à la présentation ;
5. dériver `WallPushed` et `WallPushSpeed` de la vitesse physique lissée.

Tests attendus : courbe de déplacement sans alternance artificielle, résultat final identique selon
le framerate, aucun passage dans le mur, arrêt propre quand le contact cesse, test hôte + client.

## P1 — synchronisation des impacts et des objets

Les repères livrés sont visuels, sans `AnimationEvent`, ce qui est correct. En revanche le gameplay
agit actuellement trop tôt :

- le punch humain résout les dégâts dès le traitement serveur alors que l'impact visuel est f10 ;
- le bot attend `0,32 s`, proche de f10, mais via `Time.time` et non via le tick réseau ;
- Pickup/Throw/Drop/Deposit attachent ou libèrent l'objet au déclenchement alors que les poses de
  contact/release arrivent plus tard.

Créer une petite phase d'action autoritaire pilotée au tick : démarrage, tick de contact/impact,
recovery, fin. Le client propriétaire peut prédire la présentation à partir du tick de commande,
mais les dégâts, l'énergie, l'inventaire et la physique restent décidés par le serveur.

Repères de départ à 30 fps :

- Pickup contact f12 ;
- Throw release f12 ;
- Drop release f9 ;
- Deposit release f15 ;
- Punch impact f10.

Ne jamais utiliser un `AnimationEvent` comme source d'autorité. Il peut au plus déclencher un son,
une poussière ou un effet de caméra local.

## P1 — locomotion et carry

Le contrôleur ne reçoit qu'un `MoveSpeed` scalaire et joue toujours une marche/course vers l'avant.
Le joueur peut pourtant straffer et reculer relativement à son regard. Cela produit du foot sliding
et une intention corporelle incorrecte, surtout en troisième personne.

Décision à prendre :

- soit orienter le personnage vers sa direction de déplacement ;
- soit ajouter `MoveLocalX`/`MoveLocalY` et un blend tree directionnel avec clips avant/arrière/côtés.

Pour ce jeu, le second choix est recommandé si la visée reste indépendante du déplacement. Ne pas
masquer le problème uniquement avec la vitesse de lecture.

Autres limites :

- Walk, Sprint et CarryWalk ont été authored à environ la moitié du rythme de jeu ; le playtest les
  lit à ×2. Garder ce multiplicateur seulement comme hypothèse de test, puis décider entre retiming
  source et rythme gameplay ;
- `CarryKind` est publié par le gameplay, mais le contrôleur ne distingue pas caillou/trophée ;
- dans les slots latéraux, la main opposée reste à environ 13–19 cm de l'objet : il faudra soit une
  présentation par slot, soit ne montrer dans les mains que l'objet actif central.

## P1/P2 — bot de test

Le bot est utile pour sentir les coups. Il alterne environ 7,5 s d'attaque et 4,5 s de mur, possède
100 PV, prend 25 dégâts par punch, inflige 10 dégâts et se relève après 2,8 s.

Dette connue :

- timers `Time.time`, donc non déterministes au tick ;
- recherche de scène fréquente et steering direct, sans navigation ;
- la « poussée » du mur est simulée par des impulsions répétées de punch, pas par le contrat continu
  d'intention/énergie du joueur ;
- santé et état non publiés dans le même modèle snapshot que les joueurs : late join fragile ;
- les objets lancés ne ciblent pas le bot ;
- KO/récupération non validés en session humaine ;
- HUD surtout pensé pour l'hôte.

Première amélioration utile : rendre attaque, impact, KO et récupération tick-authoritaires, permettre
aux carryables de le toucher, puis brancher les vrais clips. Ne pas transformer ce mannequin en IA
de production avant que les interactions de base soient validées.

## P2 — revue créative après intégration

Points à regarder avec le joueur, dans cet ordre :

1. `SB_Knockout` contient un accent de 9,54° entre deux images à f5. Les portes contractuelles
   passent, mais le gate supplémentaire de continuité reste FAIL. Le conserver si cela lit comme une
   rupture d'équilibre ; le retoucher si cela lit comme un snap.
2. `SB_WallPushed` est direction-neutral. Commencer avec ce clip, piloté par intensité ; créer gauche/
   droite seulement si le sens du choc reste illisible.
3. Le gait actuel est volontairement large/chaloupé à cause de la géométrie du rig. Juger dans la
   caméra de jeu, pas seulement dans le playblast Blender.
4. En première personne, le corps et les bras occupent beaucoup l'image. À terme, prévoir une couche
   upper-body ou des bras de vue dédiés plutôt que déformer toutes les animations monde.
5. `arena-echo` est une direction de composition acceptée techniquement, pas encore une scène de jeu
   finalisée. Son cadrage centré et son rendu 64 samples sont des limites connues.

## Séquence de travail proposée à Claude

### Passe A — intégration sûre

- préserver le worktree sale ; ne jamais reset les modifications présentes ;
- charger et hasher les 7 FBX Kimi depuis `_GeneratedLocal` ;
- construire le graphe cible complet ;
- tester toutes les transitions sur joueur et bot ;
- ne promouvoir aucun asset canonique.

### Passe B — physique et timing

- rendre la release de projectile sûre et atomique ;
- supprimer les warnings de reset ;
- créer les phases d'action au tick ;
- rendre la poussée du mur continue dans la simulation, puis brancher `WallPushed`.

### Passe C — goût et finition

- playtest troisième personne puis première personne ;
- décider ×2 ou retiming ;
- décider KO f5 ;
- décider locomotion directionnelle et présentation des slots ;
- seulement ensuite rouvrir Blender pour les clips réellement insuffisants.

## Portes de sortie obligatoires

La prochaine passe n'est terminée que si :

- tests EditMode toujours verts ;
- nouveaux tests PlayMode du lancer proche du mur verts ;
- build macOS réussi ;
- zéro warning kinematic velocity au reset ;
- test joueur : Punch → Hit → Knockout → KnockedOutLoop → Recover visible ;
- test mur : Push visible et WallPushed visible, sans saccade de transform évidente ;
- test objet : attache/release sur les repères prévus sans dépendre d'un AnimationEvent autoritaire ;
- test bot : quatre coups produisent un KO et une récupération ;
- test multi-client : mêmes dégâts, inventaire, KO et côté du mur ;
- nouveau rapport de validation Blender uniquement si un `.blend`/FBX a réellement changé ;
- aucun fichier sous `_GeneratedLocal` n'est promu en canonique avant validation humaine.

## Fichiers à lire en premier

- `Assets/_GeneratedLocal/Editor/ClaudeAnimationPlaytestBuild.cs`
- `Assets/_Project/Runtime/Sandbox/SandboxCarryable.cs`
- `Assets/_Project/Runtime/Sandbox/SandboxPlayerGameplay.cs`
- `Assets/_Project/Runtime/Player/M1PlayerActions.cs`
- `Assets/_Project/Runtime/Player/PredictedPlayerMotor.cs`
- `Assets/_Project/Runtime/Maze/M1AuthoritativeWallDirector.cs`
- `Assets/_Project/Runtime/Player/SimpleBot.cs`
- `tools/blender-agent-studio/projects/team/sandbox-character-motion-object-claude-v001/FINAL_REVIEW.md`
- `tools/blender-agent-studio/projects/team/sandbox-character-force-combat-kimi-v001/FINAL_REVIEW.md`
- `Logs/M1PlaytestClaude/runtime-bot-manual-20260816.log`

## Prompt court de reprise

> Reprends le projet `GAME` depuis `docs/CLAUDE_NEXT_ITERATION_AUDIT_HANDOFF.md`. Respecte le
> worktree déjà sale et les règles Blender Studio/ADR réseau. Commence par la Passe A, puis traite
> les P0 de la Passe B. N'édite aucune source Blender tant que l'intégration Unity n'a pas démontré
> un défaut du clip. Les dégâts, releases, énergie, inventaire, collisions et KO doivent rester
> autoritaires au tick ; aucun AnimationEvent ne décide le gameplay. À chaque étape, ajoute les tests
> proportionnés, produis un build jouable et rapporte clairement ce qui relève encore d'une décision
> créative humaine. Ne promeus pas les candidats `_GeneratedLocal` sans accord.
