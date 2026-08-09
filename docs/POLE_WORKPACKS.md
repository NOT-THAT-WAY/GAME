# Workpacks prémâchés par pôle

> Baseline : `main` à `6b565f0`, 9 août 2026. Trois agents ont inspecté en lecture seule les pôles
> Unity/réseau, design–art–assets–audio et QA/build/CI. Ce document intègre leur préparation sans
> modifier de scène, d’asset, de compte ou de service externe.

Ce document complète le [plan maître](EXECUTION_PLAN.md), le
[backlog issue-ready](READY_BACKLOG.md) et la
[matrice de tests](TEST_OWNERSHIP_MATRIX.md). Le backlog dit **quoi livrer** ; les workpacks ci-dessous
disent **comment démarrer sans réauditer le dépôt**.

## Règles d’utilisation

- Les chemins et noms de classes proposés constituent le claim initial. Le pilote peut les renommer
  avant le premier commit, mais ne peut pas élargir silencieusement le périmètre.
- Chaque workpack produit une ou plusieurs PR atomiques dans l’ordre indiqué.
- Deux PR de code maximum avancent en parallèle, plus une preuve matérielle.
- Les décisions `DEC-*` sont humaines. Codex prépare les options et encode le choix ; il ne choisit
  pas la règle produit.
- Une preuve finale utilise un clone ou worktree propre au SHA gelé. Le workspace courant contient
  déjà des changements de documentation et une suppression utilisateur stagée : il ne sert pas de
  preuve de gate.
- Les fichiers `.blend`, textures sources, vidéos, caches et autres masters restent dans DVC ou
  `tools/blender-agent-studio/local_work/`, jamais dans Git.

## Répartition des pôles

Les pôles sont des chapeaux temporaires, pas des silos.

| Pôle | Pilote naturel | Binôme | Travail Codex | Test indépendant naturel |
|---|---|---|---|---|
| pilotage/gouvernance | Nils | Zak | dossiers de décision, scripts et synchronisation | Sean |
| plateforme/réseau | Zak | Nils | architecture, code, fixtures et diagnostics | Sean puis rotation |
| design/level/art/UI | Sean | Zak | générateurs, contrats studio, audits/imports | Nils puis externes |
| données/DVC/audio | Nils | Sean | manifests, hashes, intégration et validateurs | Zak |
| QA/performance | rotation A/B/C | deuxième membre | harness, collecte et comparaison | troisième membre |

Le détail opérateur/témoin/approbateur est fixé dans
[TEST_OWNERSHIP_MATRIX.md](TEST_OWNERSHIP_MATRIX.md).

## Décisions à préparer avant les workpacks techniques

### DEC-01 — simulation M1

Pilote : Nils. Expertise : Zak pour réseau/physique, Sean pour gabarit/feel.

À fermer dans une PR documentaire avant le branchement gameplay :

- taux de tick FishNet ;
- mode et ordre de simulation avec la physique Unity ;
- gabarit et hauteur canonique du joueur ;
- saut durable, provisoire ou supprimé ;
- conséquence d’un mur rencontrant un joueur ;
- listen-server accepté comme limite M1 ou exigence dédiée immédiate.

Point FishNet : le tick rate n’est pas négocié automatiquement entre client et serveur. La même
valeur doit être configurée et vérifiée sur chaque build, puis inscrite dans le manifest.

### DEC-02 — connectivité garantie

Pilote : Sean. Expertise : Zak.

Avant `TOP-02`, choisir ce qu’un mouvement de mur doit laisser connecté :

- tous les spawns entre eux ;
- chaque spawn vers une zone/objective donnée ;
- uniquement la petite zone de duel ;
- ou aucune garantie globale, avec règle de reset/softlock explicite.

Le validateur topologique implémente le choix ; il ne doit pas inventer “pas de softlock” comme règle
de game design.

### DEC-03 — énergie et contestation

Pilote : Sean + Nils. Expertise : Zak.

Avant `INT-01`, fixer énergie max/régénération/coûts, accumulation d’effort, priorité push/punch,
contestation et tie-break au même tick. Ces valeurs vivent ensuite dans une source canonique et des
tests, jamais dupliquées dans prefabs et UI.

### DEC-04 — règle de manche M2

Pilote : Nils + Sean.

Trois prototypes à comparer sur papier/graybox avant choix :

1. **Orientation tenue** : maintenir une orientation cible pendant une durée ;
2. **Passage** : ouvrir une route et atteindre la zone adverse ;
3. **Score d’actions** : seulement si les deux règles précédentes ne testent pas l’hypothèse.

La première isole la mécanique ; la deuxième teste mieux navigation et lecture. Trésor, extraction
et santé ne sont pas ajoutés par défaut.

---

## Pôle pilotage, gouvernance et données

### WP-GOV — dépôt gouverné et backlog fiable

Tickets : `GOV-01` à `GOV-04`, `RIGHTS-01`.

Travail préparé :

- dossier d’options public/privé, licence open source ou notice propriétaire ;
- ruleset `main` exigeant `repository-checks`, sans bypass quotidien large ;
- un/deux Admin maximum, droits Write/Maintain pour le travail courant ;
- corrections de `publish-task`, corps de PR et compatibilité Dependabot ;
- scanner de secrets épinglé avec fixture factice ;
- matrice de droits : ID, auteur, source, date, droit de modifier/redistribuer, restrictions, preuve
  privée et verdict `autorisé / prototype privé / à remplacer / retiré` ;
- rebasage exact des issues `#1` à `#6` décrit dans `READY_BACKLOG.md`.

Décisions humaines : visibilité/licence, droit de publication, rôles GitHub, Tailscale commercial.

Sortie : G0 vert selon la matrice de tests. Le simple texte “propriété de l’équipe” ne suffit pas à
prouver une chaîne de droits ; `content-rights.json` reste à revue propriétaire jusqu’à signature.

### WP-ENV — trois environnements et trois hôtes

Tickets : `ENV-01`, `ENV-02`, `NET-00`.

Exécution :

1. Sean : second Mac, doctor, double ouverture/fermeture, build Development ;
2. Zak/propriétaire PC : Windows IL2CPP, lancement réel et hash du build ;
3. session distante à trois avec Zak hôte ;
4. Sean/propriétaire Windows devient hôte ;
5. Nils devient hôte ;
6. un client quitte/revient sur chaque famille d’OS.

Codex prépare le préflight, expurge les logs et corrige un défaut reproductible dans une PR séparée.
La sortie exige le même SHA et un arbre propre sur les trois machines.

### WP-DVC — droits, premier master et restauration

Tickets : `DVC-01`, `DVC-02`, `DVC-03`, `RIGHTS-01`.

Premier lot recommandé :

```text
ExternalAssets/Art/ART-PERSO-PUNCH-001/
├── master/BAS_PUNCH_player_proto.blend
├── references/                  # seulement après revue des droits
├── evidence-binaries/           # preuves utiles et approuvées
├── export-reference/BAS_PUNCH_player_punch.fbx
└── manifest.json
```

Constats vérifiés par l’agent art :

- master local : 173 302 octets, SHA-256 préfixe `54547e8e`, suffixe `0db71` ;
- export local et export Unity : 324 204 octets, même SHA-256 préfixe `4503459d`, suffixe `31cce1` ;
- la branche historique `art/player-punch-rig` possède des contrats réutilisables, mais son manifest
  présente à tort un réimport Blender comme preuve Unity ;
- Unity macOS a depuis mesuré 9 meshes skinnés, 5 664 triangles, 10 bones, 1,340 m et un clip de
  0,792 s à 24 fps ; Windows reste non prouvé.

À exclure du lot : `.DS_Store`, `.blend1` non déclaré, caches, duplications temporaires et chemins
machine. Ordre obligatoire : copie immuable → manifest/hashes → `dvc add` → `dvc push` → commit Git.

Pour `ART-MAZE-001` et `ART-PERSO-001`, un seul statut est accepté :

- `RECOVERED` : original retrouvé et hashé ;
- `REGENERABLE` : générateur, entrées, seed et versions réellement présents, deux reconstructions
  propres identiques ;
- `RUNTIME_EXPORT_ONLY` : export gelé comme prototype à remplacer.

Un FBX réimporté dans Blender ne devient jamais le “master original”. Une reconstruction reçoit un
nouvel ID `derived reconstruction`.

Restauration finale : cache vide Mac + cache vide Windows, même lot et mêmes hashes, puis ouverture
lecture seule par Sean. Tester séparément versioning objet et seconde copie indépendante de R2.

---

## Pôle Unity, architecture et réseau

### WP-U00 — fondation de tests

Ticket/PR : `TST-01` → `chore/unity-test-foundation`.

Propriété exclusive :

```text
Assets/_Project/Tests/EditMode/Game.EditMode.Tests.asmdef
Assets/_Project/Tests/EditMode/EditModeSmokeTests.cs
Assets/_Project/Tests/PlayMode/Game.PlayMode.Tests.asmdef
Assets/_Project/Tests/PlayMode/PlayModeSmokeTests.cs
scripts/unity-tests-macos.sh
scripts/unity-tests-windows.ps1
docs/UNITY_TESTS.md
```

Contrat : batch Unity avec `-runTests`, `-testPlatform`, XML, log et code non-zéro sous
`Logs/Tests/`. Cette PR ne touche aucune classe gameplay.

Preuve : smoke EditMode, `[UnityTest]` PlayMode, branche jetable volontairement rouge puis verte ;
Nils reproduit Mac, propriétaire du PC reproduit Windows.

État au 9 août 2026 : fichiers et wrappers produits, Mac vert (`5/5` EditMode, `1/1` PlayMode).
La preuve Windows et la démonstration rouge/verte restent à opérer par l’équipe.

### WP-U01 — topologie v1

Tickets : `TOP-01`. Deux PR séquentielles :

1. `data/topology-domain-v1` ;
2. `data/migrate-maze16-schema-v1`.

Fichiers proposés :

```text
Assets/_Project/Runtime/Maze/Topology/TopologyTypes.cs
Assets/_Project/Runtime/Maze/Topology/MazeTopologyJson.cs
Assets/_Project/Runtime/Maze/Topology/MazeTopologyValidator.cs
Assets/_Project/Runtime/Maze/Topology/MazeTopologyCanonicalizer.cs
Assets/_Project/Runtime/Maze/Topology/TopologyChecksum.cs
Assets/_Project/Maze/MazeTopology16x16.v1.json
Assets/_Project/Tests/EditMode/MazeTopologyContractTests.cs
Assets/_Project/Tests/Fixtures/Topology/*.json
```

API minimale :

```text
EdgeAxis, EdgeCoord, GridCell, GridNode
TopologyDimensions(widthCells, heightCells, cellPitchMm, wallThicknessMm, wallHeightMm)
WallDefinition(wallId, pivotId, initialStateId, states[])
WallStateDefinition(stateId, edge, quarterTurns)
PivotDefinition(pivotId, node, wallIds[])
SpawnDefinition(spawnId, cell, yawQuarterTurns)
MazeTopologyJson.TryParse(..., out topology, out issues[])
MazeTopologyValidator.Validate(...)
MazeTopologyCanonicalizer.WriteUtf8(...)
TopologyChecksum.ComputeSha256(...)
```

Règles : checksum sans son propre champ, UTF-8 sans BOM, entiers/culture invariants, tableaux
canonisés par ID. L’ID est dans la donnée, jamais dans l’index du tableau, le nom Unity ou l’ordre
FBX. Rejeter schéma inconnu, doublon, champ invalide, référence cassée, état/spawn hors grille et
ouverture incohérente.

Ne pas utiliser `JsonUtility` comme validateur strict. Si Newtonsoft devient dépendance directe,
modifier `Packages`, lockfile et asmdef dans cette PR seulement, avec rejet des membres inconnus et
des propriétés dupliquées ; vérifier IL2CPP/AOT.

Preuve : `fr-BE`/`en-US`, CRLF/LF et ordre JSON donnent les mêmes bytes/checksum sur Mac/Windows ;
la migration conserve coordonnées, 17 pivots, entrées/spawns et données utiles.

### WP-U02 — collision logique et scène grise

Tickets : `TOP-02`, puis `GRY-01`. Deux PR.

Collision :

```text
Assets/_Project/Runtime/Maze/Topology/TopologyGeometry.cs
Assets/_Project/Runtime/Maze/Topology/TopologyConnectivity.cs
Assets/_Project/Runtime/Maze/Collision/TopologyColliderFactory.cs
Assets/_Project/Runtime/Maze/Collision/TopologyCollisionWorld.cs
Assets/_Project/Runtime/Maze/Collision/WallSweepValidator.cs
Assets/_Project/Tests/EditMode/{TopologyGeometry,TopologyConnectivity,WallSweepValidator}Tests.cs
```

`BuildColliderSpecs(topology, snapshot)` retourne des specs pures centre/taille/yaw/layer ; l’adaptateur
Unity instancie uniquement des `BoxCollider`. `WallSweepValidator.CanTransition` décide analytiquement
l’arc ; PhysX ne choisit pas seul si un mouvement gameplay est permis. `TopologyConnectivity`
implémente DEC-02.

Réglages exclusifs de la PR : `ProjectSettings/TagManager.asset` et `DynamicsManager.asset` pour
`GameplayWorld`, `Player`, `InteractionQuery`, `VisualOnly` et leur matrice.

Graybox :

```text
Assets/_Project/Maze/GrayboxOnePivot.v1.json
Assets/_Project/Editor/PivotGrayboxBuild.cs
Assets/_Project/Runtime/Debug/GrayboxDebugHud.cs
Assets/_Project/Runtime/Debug/GrayboxResetController.cs
Assets/_Project/Tests/PlayMode/PivotGrayboxSceneTests.cs
Assets/_GeneratedLocal/PivotGraybox.*     # sortie ignorée
```

Deux générations propres doivent produire la même hiérarchie/IDs. Deux spawns libres, aucun FBX,
aucun `MeshCollider`, aucun bouton `U`, HUD avec map/checksum/tick/révision.

### WP-U03 — mur déterministe puis adaptateur FishNet

Tickets : `TICK-01`, puis `WALL-01`. Deux PR obligatoires.

Modèle pur :

```text
Runtime/Maze/Simulation/WallState.cs
Runtime/Maze/Simulation/WallTransition.cs
Runtime/Maze/Simulation/WallStateMachine.cs
Runtime/Maze/Simulation/WallSnapshot.cs
Runtime/Simulation/TickMath.cs
Tests/EditMode/{WallStateMachine,TickMath}Tests.cs
```

État minimal : `wallId`, `stateId`, `revision`, transition active ; transition : source, cible,
`startTick`, `durationTicks`, `revision`. Progression = fraction entière de ticks, avec comparaison
compatible wrap-around ; jamais accumulation `deltaTime`.

Adaptateur réseau :

```text
Runtime/Maze/Network/AuthoritativeWallDirector.cs
Runtime/Maze/Network/WallNetworkMessages.cs
Runtime/Maze/Network/WallRegistry.cs
Runtime/Maze/Network/WallVisualPresenter.cs
Runtime/Maze/Network/WallSystemSpawner.cs
Tests/PlayMode/WallNetworkTests.cs
```

Contrat : intention compacte, validation serveur, transition fiable/révision, handshake
`schemaVersion+checksum`, snapshot trié à late join/reconnect et resync sur trou de révision. Aucun
tableau ne suppose des IDs denses.

Risques FishNet à tester : `RequireOwnership=false` rate-limité par connexion, host appliquant deux
fois, ordre indéfini des callbacks, structs AOT primitives, tick rate non synchronisé, perte
unreliable, wrap `uint`, topologie pas prête au spawn. Collision mur échantillonnée idempotemment au
tick avant déplacement, puis `Physics.SyncTransforms` selon le contrat retenu.

Limite : avant `PLY-02`, utiliser un acteur serveur de fixture pour portée/LOS. WALL prouve
transition/snapshot, pas encore une protection anti-triche complète contre la pose cliente actuelle.

### WP-U04 — Input Actions et simulation joueur pure

Tickets : `INP-01`, `PLY-01`. Développement parallèle possible ; merge coordonné.

Simulation :

```text
Runtime/Player/Simulation/PlayerCommand.cs
Runtime/Player/Simulation/PlayerState.cs
Runtime/Player/Simulation/PlayerSimulationConfig.cs
Runtime/Player/Simulation/IPlayerCollisionWorld.cs
Runtime/Player/Simulation/PlayerSimulation.cs
Settings/M1SimulationSettings.asset
Tests/EditMode/PlayerSimulationTests.cs
```

Commande quantifiée : axes `sbyte`, delta yaw borné, bitflags sprint/jump/interact/punch. État :
position/yaw/vitesse/knockback/grounded/fenêtres en ticks. L’adaptateur CharacterController retourne
le résultat de déplacement. Ne pas promettre PhysX bit-identique Mac/Windows : le serveur est la
référence et la réconciliation absorbe l’écart.

Input :

```text
Assets/_Project/Input/GameControls.inputactions
Runtime/Input/PlayerInputSource.cs
Runtime/Input/PlayerCommandEncoder.cs
Tests/EditMode/PlayerInputSourceTests.cs
Editor/PlaytestPlayerPrefabFactory.cs
```

Actions Player : Move, Look, Sprint, Interact, Punch, Jump si retenu, Pause ; actions UI : Navigate,
Submit, Cancel, Point, Click, Scroll. Clavier/souris et manette. Accumuler les edges entre frames et
les consommer une seule fois au tick ; distinguer unités souris/stick.

`PlayerMotor.cs`, `PlayerPunch.cs`, `MazePlaytestBuild.cs` et `PivotGrayboxBuild.cs` ne reçoivent que
le branchement minimal vers la source/factory. Aucun workpack PLY-02/INT ne travaille en parallèle
sur ces fichiers.

### WP-U05 — prédiction/réconciliation joueur

Ticket/PR : `PLY-02` → `feat/predicted-player-motor`.

Propriété exclusive :

```text
Runtime/Player/PlayerMotor.cs
Runtime/Player/Network/PlayerPredictionData.cs
Runtime/Player/UnityCharacterControllerWorld.cs
Runtime/Player/PlayerVisualSmoother.cs
Editor/PlaytestPlayerPrefabFactory.cs
Editor/PivotGrayboxBuild.cs
Tests/PlayMode/PredictedPlayerMotorTests.cs
```

Implémentation ciblée : `TickNetworkBehaviour`, callbacks tick, `IReplicateData`, `IReconcileData`,
méthodes `[Replicate]`/`[Reconcile]`, `TimeManager.TickDelta`. Le root porte simulation ; un enfant
porte lissage/caméra. Désactiver/réactiver `CharacterController` lors du repositionnement de reconcile,
conformément au sample FishNet local.

Retirer le `NetworkTransform` client-authoritative. Le téléport `U` disparaît du gameplay ; un outil
debug éventuel est serveur, Development Build et journalisé. Le reconcile contient position, yaw,
vitesses internes et diagnostic de révision/checksum topologique.

Risque principal du programme : CharacterController prédit contre murs mobiles. Prévoir un spike
borné et une réserve de 30–50 %. Preuve humaine sous `80 ms / 2 % / 20 ms` avec mesures des
corrections, pas seulement appréciation visuelle.

### WP-U06 — interactions autoritaires

Ticket/PR : `INT-01` → `feat/authoritative-pivot-interactions`, après DEC-03.

```text
Runtime/Interaction/InteractionIntent.cs
Runtime/Interaction/InteractionState.cs
Runtime/Interaction/InteractionRules.cs
Runtime/Interaction/AuthoritativeTargetResolver.cs
Runtime/Interaction/InteractionPresenter.cs
Tests/EditMode/InteractionRulesTests.cs
Tests/PlayMode/AuthoritativeInteractionTests.cs
```

Le serveur recalcule cible, portée, LOS, côté et direction depuis `PlayerState` autoritaire et les
layers topologiques. Résolution triée distance puis ID stable. Effort/énergie en unités entières,
cooldowns en ticks, intents triées par `actorId`. Knockback intégré à l’état serveur puis reconcile.

Retirer input/RPC/queries globales de `PlayerPunch.cs` ; le conserver éventuellement comme
présentation seulement. Tests : duplicate sequence, spam, hors portée, LOS, énergie, cooldown,
pousseurs opposés, ordre inversé, punch joueur/mur et politique mur/joueur.

### WP-U07 — frontière de connexion

Ticket/PR : `CON-01` → `feat/connection-target`. Peut avancer après `NET-00` sans toucher gameplay.

```text
Runtime/Networking/ConnectionTarget.cs
Runtime/Networking/IConnectionConnector.cs
Runtime/Networking/TugboatConnectionConnector.cs
Runtime/Networking/ConnectionBootstrap.cs
Runtime/Networking/ConnectionStatus.cs
Tests/EditMode/{ConnectionTarget,ConnectionBootstrap}Tests.cs
```

API : `ConnectionTarget.DirectUdp(host,port)`, parsing CLI strict ; connector avec StartHost,
StartServer, StartClient, Stop ; état Idle/Starting/Connected/Stopping/Failed. Pas de faux lobby ou
type Steam en v1. `ConnectionSmokeTest` devient affichage/roster seulement.

Tests : host/client, double start, stop/retry/reconnect, timeout, callbacks FishNet tardifs et double
événement host. Aucun type gameplay ne référence Tugboat ou Steam.

### WP-U08 — intégration 16x16 et suppression legacy

Ticket/PR : `INTG-01` → `feat/maze16-topology-integration`. Dernière PR fonctionnelle ; elle possède
seule le gros builder.

```text
Editor/MazePlaytestBuild.cs                       # refactor exclusif
Editor/MazeVisualImporter.cs
Editor/MazeIntegrationValidator.cs
Maze/Maze16VisualBindings.v1.json                 # si binding explicite nécessaire
Tests/EditMode/Maze16IntegrationTests.cs
```

À retirer : parser Regex, IDs incrémentaux, dimensions dupliquées, `NetworkTransform` joueur et tout
collider gameplay issu du mesh. Créer la collision depuis la donnée même si aucun triangle visuel
n’existe ; attacher ensuite le rendu par binding, et faire échouer le build sur pièce absente ou
dupliquée.

Après migration totale, supprimer les systèmes legacy : `PivotDirector`, `PivotDirectorSpawner`,
`PivotWall`, `MovableWallDirector`, `MovableWall`, puis l’ancien JSON. Props et mesh divers restent
`VisualOnly`. Le collider géant disparaît.

Preuve : reorder de la hiérarchie FBX sans changement d’ID/checksum, aucun `MeshCollider` gameplay,
aucune query `~0`, build rouge sur pièce visuelle manquante, zéro référence legacy et aucun warning
sur mesh > 2 097 152 triangles.

### WP-U09 — CI Unity

Ticket/PR : `CI-01` → `chore/unity-build-ci`.

```text
.github/workflows/unity-checks.yml
scripts/unity-ci-macos.sh et/ou unity-ci-windows.ps1
Editor/UnityCiEntrypoints.cs
Editor/BuildManifestWriter.cs
docs/UNITY_TESTS.md
```

Préparer après WP-U00, activer seulement après ENV-02 et preuve G3. Commencer compilation + EditMode
+ PlayMode ; build Windows artifact ensuite. Permissions lecture seule, pas de
`pull_request_target`, timeouts, concurrence annulable, Actions épinglées par SHA, rétention courte.

Manifest : commit complet, dirty=false, Unity/FishNet/InputSystem, OS/target/backend,
schemaVersion/checksum/tickRate et résultat des suites. LFS doit être disponible à Unity. PR cassée
rouge puis corrigée verte ; aucun secret/licence dans logs. Runner/licence reste décision humaine.

---

## Pôle design, art, UX et audio

### WP-A01 — graybox et contrat de lisibilité

Tickets : côté design de `GRY-01`, puis `ART-01`.

La fixture grise contient seulement un pivot logique, deux spawns, volumes primitifs, reset, HUD
debug et distance mesurable. Sean signe layout/distances ; Codex produit générateur/tests ; Zak relit
topologie ; Nils reproduit depuis clone propre.

Projet studio art conseillé : `pivot-readability-v001`, type `game-asset`, profil `game-unity`, style
`neutral-production`.

Objectif observable : à distance gameplay, identifier le pivot, son axe, le côté manipulable et les
états disponible/bloqué/contesté dans quatre orientations, sans information portée par la seule
couleur. Origine au nœud logique ; mesh sans ID ni collider autoritaire ; état visuel consommant
l’état Unity.

Budgets maintenus `UNRESOLVED` jusqu’à décision : triangles/LOD, assets visibles, matériaux/textures,
mémoire, texel density, UV lightmap, overdraw/draw calls, distance LOD, éclairage, PC minimum et frame
budget. Les dimensions 2,75 × 0,25 × 3 m et le joueur 1,40 m sont des faits du prototype, pas des
budgets reconduits automatiquement.

Preuves : source/DVC, vues identité, quatre orientations et trois états caméra/lumière identiques,
import Unity exact, vues FPS proche/moyenne/lointaine, niveaux de gris/déficience colorée, testeurs
non auteurs et rapport performance dans la fixture.

### WP-A02 — personnage riggé prototype

Après WP-DVC, compléter les preuves Unity :

- même hash Mac/Windows ;
- 9 meshes, 5 664 triangles, 10 bones, 1,340 m ;
- clip one-shot 24 fps, 0,792 s, non bouclé, root motion absent ;
- influences réellement importées, normales, tangentes, UV, matériaux, compression et LOD ;
- poses garde/anticipation/extension/contact/retrait contre master ;
- pénétrations et déformations dans Unity ;
- bras visibles du propriétaire, silhouette complète des autres ;
- timing de hit contrôlé par gameplay, aucun double déclenchement après reconcile.

Sean valide silhouette/déformation, Nils import Mac, Zak import Windows/performance, Codex mesure et
consolide le projet studio. Statut final de ce lot : `prototype seulement` jusqu’aux preuves complètes.

### WP-GAME — manche, UI et télémétrie

Tickets : `GAME-01`, `GAME-02`, `UI-01`, `TEL-01`.

Statechart cible après DEC-04 :

```text
Waiting → Countdown → Playing → RoundResult → Reset
                 ↘ DisconnectPolicy ↗
RoundResult → MatchResult ou nouveau Countdown
```

Tous les timers/résultats sont autoritaires par tick. Tester timeout, égalité, résultat simultané,
reset positions/pivot/énergie/cooldowns/HUD, ordre ancien après reset, snapshot et politique
late join/reconnexion.

HUD : objectif, manche/score/temps, réticule, feedback, pivot, effort/énergie, raison de refus et
connexion. Réglages : sensibilité souris/manette, FOV, inversion Y, volumes, bindings/rebind,
navigation sans souris. UI en lecture seule du modèle ; pause sans désynchroniser.

Événements télémétrie proposés : session/round, première intention, tentatives/refus/transitions de
pivot, contestation, énergie, punch, résultat/reset, disconnect/reconnect et agrégats de reconcile.
Champs : schemaVersion, build, session pseudonyme, round, slot/team, tick et payload allowlisté.
Interdits : IP, nom réel, compte plateforme, voix, adresse ou texte libre non filtré.

### WP-AUD — gate audio minimale

Ticket : `AUD-01`, conditionnel après G3 et hors chemin critique.

Premier événement recommandé : verrouillage/fin de transition du pivot, émis sur confirmation
autoritaire. Il est plus stable qu’une boucle d’effort pour la première gate.

Contrat : Nils seul Authoring ; Work Unit `Pivot` ; sources sous
`ExternalAssets/Audio/AUD-PIVOT-001` ; Originals/SoundBanks approuvés via les stockages prévus ; PR
exclusive pour Packages/ProjectSettings ; licence/version au registre.

Tests : banque reproductible, Mac/Windows même commit, événement unique hôte/clients, aucun doublon
prediction/reconcile, late join sans replay historique, banque absente sans crash, volume UI et
mémoire/taille consignées. Si licence/compatibilité bloque, garder un son Unity temporaire.

### WP-PLAY — deux vagues et une seule correction

Tickets : `PLAY-01`, `FIX-01`, `PLAY-02`.

Vague 1v1 : build/commit gelés, préflight 24 h avant, première manche sans aide, protocole identique,
incidents classés technique/compréhension/équilibre/plaisir, questionnaire court et aucune voix
enregistrée par défaut.

Sean modère, Nils observe/agrège, Zak surveille la technique. Un modérateur externe est préférable
si Sean a conçu le brief. Les vrais testeurs sont externes.

Après la vague : une hypothèse, une catégorie, une métrique avant/après, trois essais maximum. Puis
vague 2v2 sur compréhension d’équipe, rôles, contestation, communication, snowball/stalemate,
équité et envie de rejouer. Taille d’échantillon et seuils `GO/ITERATE/STOP` restent `UNRESOLVED`
jusqu’à DEC-04.

---

## Verrous de fichiers et ordre de merge

| Zone | Ordre exclusif | Pourquoi |
|---|---|---|
| `PlayerMotor.cs` | INP minimal → PLY-02 → INT | trois refactors incompatibles |
| `PlayerPunch.cs` | INP minimal → INT | input/RPC doivent disparaître une fois |
| `MazePlaytestBuild.cs` | factory INP → verrou INTG | fichier monolithique et générateur principal |
| `PivotGrayboxBuild.cs` | GRY → WALL → PLY-02 → INT → CON | composition de systèmes séquentielle |
| `AuthoritativeWallDirector.cs` | WALL → INT | l’interaction enrichit le serveur existant |
| `Packages/*` et asmdefs | TOP JSON éventuel, puis CI, puis Wwise | aucune dépendance mêlée à une feature |
| `ProjectSettings` physique/layers | TOP-02 seulement | matrice de collision partagée |
| `.github/workflows/*` | CI seulement | permissions/secrets contrôlés |
| systèmes legacy | suppression INTG seulement | smoke test conservé jusqu’à migration complète |
| lot DVC | un éditeur et claim daté | source immuable et hash stable |

## Parallélisation sûre

```text
Vague A : GOV/ENV/DVC humains  ||  Codex WP-U00
Vague B : DEC + WP-U01        ||  préparation ART lecture seule
Vague C : TOP collision       ||  TICK modèle pur || Input Actions
Vague D : GRY → WALL          ||  Player simulation pure
Vague E : PLY prediction → INT ; CON en parallèle hors fichiers gameplay
Vague F : INTG exclusif       ||  préparation CI désactivée
Vague G : QA G3 → GAME/UI/TEL/PERF → PLAY
```

Ne jamais dépasser deux branches de code actives. Une session de test gèle le SHA ; aucun merge
pendant son exécution.

## File immédiatement exécutable par Codex

Sans attendre DEC-01, Codex peut produire dans cet ordre :

1. `GOV-02` — fixtures et correction PR/Dependabot ;
2. généralisation du manifest de build hors HT-00 (`test-run.json` est produit) ;
3. modèles de rapport DVC restore et Blender→Unity ;
4. collecte expurgée des logs réseau ;
5. dossier d’options DEC-01/02/03/04 ;
6. fixtures du schéma topologique, sans coder les valeurs encore non décidées.

`WP-U00` est produit et vert sur Mac ; sa reproduction Windows reste dans la file humaine TST-01.

État local du 9 août 2026 : les six points sont préparés. Les wrappers Mac/Windows écrivent un
manifest de player build invalidé avant reconstruction puis signé par le hash du binaire seulement
après succès. Les rapports DVC restore et Blender→Unity ont des modèles JSON et un validateur qui
refuse les faux `PASS`. Le collecteur réseau ne publie que des événements allowlistés, compteurs et
hashes de logs privés. Le dossier DEC-01/02/03/04 fournit options, critique, baseline proposée et
preuve minimale sans figer le code. Les fixtures topologiques couvrent seulement les invariants déjà
acceptés ; l’implémentation TOP-01 attend toujours les décisions et sa branche dédiée.

Le premier workpack gameplay autorisé après décisions est WP-U01. Cette séparation permet aux
agents de prémâcher le travail sans prolonger par défaut l’architecture du smoke test.
