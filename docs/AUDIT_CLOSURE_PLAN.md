# Plan de fermeture de l’audit — du smoke 16×16 au premier duel M1

> Baseline vérifiée : `main` à `6b565f0`, 9 août 2026. Le workspace courant est sale et contient
> notamment une suppression utilisateur stagée. Les preuves locales qui en sont issues restent des
> preuves de développement, pas des preuves distribuables attachées à un SHA propre.

Ce document resserre le [plan maître](EXECUTION_PLAN.md) autour du prochain résultat jouable. Il ne
remplace ni le [backlog détaillé](READY_BACKLOG.md), ni la [matrice QA](TEST_OWNERSHIP_MATRIX.md) : il
indique ce qui peut réellement démarrer maintenant, ce qui attend une décision précise et comment
fermer chaque famille de dettes relevée par [l’audit du 5 août](audits/2026-08-05-document-maitre.md).

## Verdict : oui, un mur isolé avant le labyrinthe complet

La prochaine preuve primaire ne doit pas être une nouvelle itération de la map 16×16. Cette map
reste utile pour l’import, l’échelle, le rendu et l’intégration finale, mais elle mélange aujourd’hui
17 pivots, 173 murs mobiles, plusieurs interactions, des props, des colliders issus du FBX, le saut,
un bot et le réseau. Un défaut observé dans cette scène ne permet pas d’identifier rapidement s’il
vient de la topologie, de la collision, du joueur, de l’effort, du réseau ou du level design.

« Tester un mur avant le labyrinthe » ne signifie pas polir un mur pendant des semaines. Cela
signifie construire le plus petit banc qui sépare ces responsabilités :

- arène grise de `2 × 2` cellules, fermée par des primitives ;
- deux spawns opposés et un détour toujours disponible ;
- un seul `wallId`, un pivot explicite et deux états stables à 90° ;
- une orientation ouvre le trajet direct, l’autre le ferme sans isoler un joueur ;
- reset immédiat et déterministe, sans recharger le processus ;
- aucun FBX, prop, végétation, saut, touche de déblocage, énergie ou `MeshCollider` gameplay ;
- couleurs et HUD de diagnostic seulement : état, tick, révision, checksum et code de refus ;
- commandes données explicitement au testeur, sans indice ni test de découverte.

La fixture `valid-minimal.json` actuelle reste adaptée au contrat du parseur. Elle ne devient pas la
graybox jouable : son mur central peut séparer ses deux cellules. Une seconde fixture `2 × 2` doit
porter la garantie de connectivité de la zone de duel.

Le prototype possède aussi deux familles concurrentes, `PivotDirector` et `MovableWallDirector`.
M1 doit converger vers un seul modèle logique de mur. La poussée continue et le punch peuvent être
deux sources d’un même effort signé ; ils ne doivent pas rester deux simulations différentes.

## Vérité vérifiée au 9 août

| Domaine | Acquis | Manque réel | Conséquence |
|---|---|---|---|
| Toolchain | Unity/FishNet/URP/Input System figés ; validation statique verte | preuve Windows de la baseline | développement Mac possible, sortie M0 impossible |
| Builds/tests | build Mac courant réussi ; `26/26` EditMode et `1/1` PlayMode ; rouge volontaire détecté | collisions/tick, Windows, SHA propre et CI Unity | topologie prouvée sur Mac, pas encore le gameplay M1 |
| HT-00 | caméra, mouvement, saut, punch et bot touché sans crash | aucune rotation de mur/pivot prouvée ; ancien binaire sans provenance ferme | conserver `INCOMPLETE`, ne pas forcer un faux PASS |
| Gameplay | map, joueur, pivots et murs forment un smoke intégré | temps par frame, autorité cliente, deux systèmes muraux, téléport `U` | ne plus étendre les classes legacy |
| Topologie | schéma v1, parseur strict, validation, IDs, canonicalisation, checksum et migration 16×16 verts sur Mac | checksum Windows et intégration snapshot | TOP-02/graybox peuvent démarrer |
| Collision | une partie des murs statiques reçoit des boîtes | le build annonce encore 21 `MeshCollider` ; pivots, props et restes dépendent du FBX/mesh ; arc non déterministe | graybox primitive avant réintégration |
| Réseau | Tugboat local et roster historique fonctionnels | tick, snapshot, late join, reconcile et preuve distante à trois | aucun claim M1 réseau |
| GitHub | workflow statique vert sur le SHA distant | dépôt public sans licence, ruleset désactivé, `main` non protégé, trois Admin, issues périmées | G0 reste rouge |
| DVC/assets | R2 choisi ; un master riggé existe localement | aucun pointeur/push/restore ; deux masters absents ; droits à confirmer | graybox autorisée, modification durable des masters bloquée |
| Preuves | identité runtime, bundle complet et rapports liés aux manifests verts sur Mac | parse/build Windows puis vraie session multi-machine | ancien log désormais `INCOMPLETE` |

Le rapport réseau historique à un participant est seulement une preuve du filtre d’anonymisation.
Il ne constitue ni une preuve du commit courant, ni une preuve multi-machine. Le prochain format doit
lier chaque log à un `buildId` embarqué, au commit, au profil et au manifest du binaire lancé. Le
manifest doit aussi couvrir le contenu complet du bundle `.app` ou du dossier Windows, pas seulement
l’exécutable principal.

HT-00 ne bloque pas la suite. Son instrumentation permet désormais un diagnostic plus précis, mais
rejouer trois à cinq minutes le système legacy n’est utile que si l’équipe veut conserver une démo
16×16 fonctionnelle avant sa migration. Pour avancer vers M1 avec le minimum de test humain, garder
le verdict `INCOMPLETE` et investir le prochain passage humain dans la graybox autoritaire.

## Dépendances assouplies

Le backlog précédent bloquait trop largement du travail réversible derrière `DEC-01`. La règle
corrigée est : une décision ne bloque que le comportement qu’elle fixe.

- `TOP-01A` peut démarrer maintenant : types, JSON strict, version, IDs, références et bornes.
- `TOP-01B` peut suivre sans choix de feel : bytes canoniques, checksum et migration structurelle de
  la map actuelle.
- `TICK-01A` peut définir maintenant une transition paramétrée par `startTick`, `durationTicks` et
  `revision`. Le taux de tick concret, l’ordre PhysX et la politique mur/joueur attendent `DEC-01`.
- `INP-01A` peut créer les actions Move, Look, Interact, Punch et Pause, ainsi que les schemes
  clavier/souris et manette. L’activation durable du saut et la sémantique finale tap/hold attendent
  la décision concernée.
- `CON-01A` peut définir la valeur `ConnectionTarget`, le parseur CLI et leurs tests purs. Le
  remplacement du bootstrap Tugboat attend la preuve `NET-00` afin de conserver une baseline connue.
- La graybox primitive n’attend ni DVC, ni Blender, ni art final. Elle attend le contrat topologique
  et les colliders simples.
- G0 et M0 peuvent avancer en parallèle du modèle pur local. Ils bloquent la diffusion, les preuves
  finales et les refactors destructifs, pas l’écriture de code C# pur testé.

## Décisions minimales proposées

Ces valeurs sont les baselines recommandées, pas encore des décisions `ACCEPTED` :

| Sujet | Baseline candidate | Ce qu’elle débloque |
|---|---|---|
| Tick | `60 Hz`, avec repli à `30 Hz` si la mesure cible l’exige | configuration mur/joueur |
| Physique | `PhysicsMode.TimeManager`, ordre de tick de l’ADR 0004 | collision et reconcile |
| Gabarit | profils comparables `1,40 m` et `1,80 m`, aucun choix caché | calibration courte puis moteur canonique |
| Saut | désactivé dans M1 ; conservé seulement dans le smoke historique | input et graybox sans contournement |
| Mur/joueur | refuser si destination ou arc balayé occupé | collision déterministe sans KO provisoire |
| Hébergement | listen-server M1 ; builds Tugboat/Steam séparées | architecture réseau immédiate |
| Connectivité | garantir la zone de duel et les deux spawns pour M1 | validation de la fixture graybox |
| Effort initial | effort signé sans énergie pour valider le réseau | mur/contestation avant équilibrage |
| Opposition | somme signée au même tick ; égalité = annulation, jamais ordre RPC/ClientId | résolution déterministe |
| Première manche | orientation tenue très courte ; passage ensuite si la route est comprise | premier test 1v1 puis M2 |

Le taux de tick, l’ordre physique et le refus mur/joueur doivent être acceptés avant l’intégration
PhysX/FishNet. L’énergie attend `INT-01`. La règle de manche attend G3. Les autres valeurs peuvent
rester des paramètres de test jusque-là.

## Ordre d’exécution

### 0 — livrer proprement la préparation actuelle

Avant une nouvelle feature, isoler les changements déjà produits : tests, manifests, rapports,
instrumentation HT-00, documentation et automatisation PR. La suppression stagée de
`tools/blender-agent-studio/KIMI_K3_HANDOFF.md` reste une décision utilisateur et ne doit pas être
absorbée dans une branche par défaut.

Sortie : branche courte, diff relu, tests verts, build propre reproductible et PR sans placeholders.

### 1 — deux voies immédiates en parallèle

Voie Codex/Unity :

1. `PROV-01` — embarquer `buildId`, commit, dirty flag, profil et version dans le runtime, manifester
   le bundle complet et obliger les rapports réseau à vérifier ces marqueurs au lieu d’accepter un
   SHA fourni seul ;
2. `TOP-01A` — types et parseur strict consommant les fixtures existantes ;
3. `TOP-01B` — canonicalisation/checksum, puis migration du JSON 16×16 sans encore brancher la map ;
4. `INP-01A` — asset Input Actions et encodage de commande indépendant du moteur joueur legacy ;
5. `GOV-03A` — scanner de secrets local et fixture factice ; l’activation GitHub reste humaine.

Voie équipe/machines :

1. Nils : visibilité/licence/ruleset/rôles/issues ;
2. Sean : second Mac et récupération/requalification des masters ;
3. Zak/propriétaire PC : build Windows IL2CPP ;
4. Nils + Zak : premier lot DVC, restore cache vide et seconde copie ;
5. les trois : session Tugboat/Tailscale après durcissement de provenance.

### 2 — collision logique et graybox

1. créer des specs pures de `BoxCollider` depuis la topologie ;
2. valider destination, arc balayé et code de refus stable ;
3. appliquer la connectivité de la zone de duel ;
4. générer la scène `2 × 2`, deux spawns, un mur, deux états et reset ;
5. vérifier automatiquement zéro `MeshCollider`, zéro FBX et zéro dépendance aux noms Unity ;
6. produire trois resets, deux rotations par sens et les refus d’occupation sans touche `U`.

### 3 — un mur autoritaire

1. modèle pur : état, transition, tick, révision, snapshot et wrap du compteur ;
2. agrégation d’intentions signées indépendante de leur ordre d’arrivée ;
3. adaptateur FishNet : validation, rate limit, snapshot, late join, reconnexion et révision ancienne ;
4. collision logique échantillonnée au tick ; interpolation visuelle séparée ;
5. mêmes résultats à `30/60/120 FPS` de rendu.

### 4 — joueur et interaction

1. modèle pur du joueur et commande compacte depuis Input Actions ;
2. `Replicate`/`Reconcile`, serveur faisant foi et diagnostics de correction ;
3. suppression du `NetworkTransform` client-authoritative et du déblocage `U` dans la graybox ;
4. cible, portée, ligne de vue, côté, punch et poussée recalculés depuis l’état autoritaire ;
5. énergie partagée seulement après validation du mur sans énergie.

### 5 — preuve technique M1

1. Mac et Windows au même SHA propre, mêmes schéma/checksum/tick ;
2. arrivée tardive pendant une transition et reconnexion ;
3. hôte Mac puis Windows ;
4. framerate séparé du profil `80 ms RTT / 2 % perte / 20 ms jitter` ;
5. session technique de 20 minutes sans divergence, blocage ou relance du processus.

### 6 — premier test humain essentiel

Ce test arrive après les tests automatiques et la preuve locale à deux instances. Il ne sert pas à
découvrir une panne de build.

- cinq minutes maximum pour comparer `1,40 m` et `1,80 m` si la différence reste indécidable par
  mesure ;
- duel 1v1 de 10–15 minutes sur le mur unique, objectif « orientation tenue », preset moyen ;
- commandes et objectif annoncés directement, aucun indice, tutoriel caché ou questionnaire long ;
- au moins une poussée, une opposition égale, une opposition inégale et une transition complète ;
- chaque joueur peut expliquer l’état courant et la raison d’un refus ;
- une seule hypothèse de correction est retenue après la session.

Arrêt immédiat si les instances divergent, si une transition n’est pas reproductible, si un joueur
reste coincé ou si une récupération manuelle est nécessaire.

### 7 — retour au labyrinthe 16×16

Seulement après la sortie technique et humaine du mur :

1. brancher la donnée 16×16 migrée sur le même parser et le même modèle ;
2. générer toute collision gameplay depuis la topologie, même si le visuel manque ;
3. attacher le FBX comme rendu `VisualOnly`, avec binding explicite et validation d’import ;
4. retirer les IDs d’ordre, constantes dupliquées, parser Regex et `MeshCollider` gameplay ;
5. remplacer puis supprimer les deux directeurs legacy ;
6. comparer checksum, collisions et états Mac/Windows ;
7. mesurer séparément coût graybox et coût du contenu 16×16.

## Registre complet des tâches restantes

### Dépôt, machines et données

| Lot | État | Prochaine sortie | Responsable réel |
|---|---|---|---|
| BASE-01 préparation locale | changements testés mais non livrés, arbre sale | branche/PR propre sans suppression utilisateur absorbée | Codex + Nils |
| GOV-01 | ouvert | visibilité, licence, ruleset actif, droits réduits | Nils + Zak |
| GOV-02 | code local prêt | PR humaine et Dependabot réels | Codex, preuve Nils |
| GOV-03 | non implémenté | scan local puis activation GitHub | Codex + Zak/Nils |
| RIGHTS-01 | inventaire partiel | preuve propriétaire/redistribution par asset | Sean + Zak, validation Nils |
| GOV-04 | issues `#1`–`#6` périmées | fermer/scinder/renommer selon backlog | Nils |
| ENV-01 | non prouvé | second Mac, deux ouvertures propres, doctor/build | Sean |
| ENV-02 | non prouvé | Windows x86_64 IL2CPP lancé et hashé | Zak/propriétaire PC |
| NET-00 | non prouvé | trois logs liés au même build, trois réseaux, reconnexion | trois membres |
| DVC-01 | remote choisi, aucun lot | push du master riggé et pointeur Git | Nils + Sean |
| DVC-02 | deux masters absents | `RECOVERED`, `REGENERABLE` prouvé ou `RUNTIME_EXPORT_ONLY` | Sean |
| DVC-03/04/05 | bloqué par lots | restore vide Mac/Windows, lecture métier, version antérieure, seconde copie | Nils + Zak + Sean |
| TST-01 | Mac local vert, tests smoke seulement | preuve propre Windows et tests de domaine | Codex + Zak |
| PROV-01 | nouveau défaut confirmé | lier runtime/logs/manifests au binaire réel | Codex, QA Nils |

### Contrat logique et duel autoritaire

| Lot | État | Dépendance exacte | Sortie |
|---|---|---|---|
| DEC-01 | recommandations prêtes | humain avant PhysX/FishNet canonique | tick, physique, gabarit, saut, mur/joueur, hébergement |
| DEC-02 | recommandation prête | humain avant validation connectivité | garantie zone de duel |
| DEC-03 | recommandation prête | humain avant `INT-01` | effort, énergie, égalité |
| DEC-04 | recommandation prête | G3 avant manche M2 | objectif/reset |
| TOP-01A | `IMPLEMENTED-LOCAL` | preuve Windows restante | types, JSON strict, IDs, références, bornes |
| TOP-01B | `IMPLEMENTED-LOCAL` | preuve Windows restante | canonicalisation, checksum, migration 16×16 |
| TOP-02 | après TOP-01 et DEC-02 pour la connectivité | politique mur/joueur avant intégration physique | colliders, arc balayé, graphe |
| GRY-01 | après specs collision | aucune dépendance Blender/DVC | arène 2×2 déterministe |
| ART-01 | après graybox stable | revue humaine de lisibilité | primitives lisibles puis seulement blockout éventuel |
| TICK-01A | après TOP-01A | aucune fréquence concrète | modèle paramétré, snapshot, wrap, tests |
| TICK-01B/WALL-01 | après DEC-01, TOP-02, GRY-01 | choix physique/mur-joueur | adaptateur FishNet et late join |
| INP-01A | `READY-CODEX` | aucune pour les actions de base | schemes clavier/manette et commande |
| INP-01B | après DEC-01 | statut saut/tap/hold | action map canonique |
| PLY-01 | après DEC-01 et TOP-02 | gabarit/ordre de simulation | modèle joueur pur |
| PLY-02 | après PLY-01, INP-01, GRY-01 | mur logique disponible | prédiction/réconciliation |
| INT-01 | après DEC-03, WALL-01, PLY-02 | règles d’effort | interaction autoritaire unique |
| CON-01A | `READY-CODEX` | aucune pour valeur/parseur purs | `ConnectionTarget` et tests sans branchement runtime |
| CON-01B | après preuve Tugboat NET-00 | comportement actuel gelé | adaptateur/bootstrap Tugboat, sans Steam concret |
| INTG-01 | après WALL-01 et PLY-02 | modèle M1 vert | map 16×16 comme intégration secondaire |
| QA-01 | après INT-01 et INTG-01 | builds propres Mac/Windows | matrice distribuée M1 |
| CI-01 | après preuve Windows et politique secrets/licence | runner Unity choisi | compilation/tests Unity CI |

### M2 et travaux conditionnels

| Lot | État | Ouvrir seulement quand |
|---|---|---|
| GAME-01/02 | bloqué | G3 vert et DEC-04 acceptée |
| UI-01 | bloqué | Input Actions et règle de manche stables |
| TEL-01 | bloqué | événements de manche définis et politique de données acceptée |
| PERF-00 | bloqué | build graybox + 16×16 réellement jouables |
| PLAY-01 | bloqué | QA-01, performance, UI et télémétrie verts |
| FIX-01 | conditionnel | une hypothèse prioritaire issue de PLAY-01 |
| AUD-01 Wwise | conditionnel | G3 vert et aucun retard du playtest |
| PLAY-02 | bloqué | vague 1 et éventuel correctif unique |

Steam concret, voix, matchmaking, serveur dédié, art final, variantes de labyrinthes, minimap, A*,
interest management, trésor, KO/extraction, signature et release restent différés jusqu’au verdict
M2. Ils ne ferment aucune dette nécessaire au premier duel.

## Répartition minimale des tests

| Preuve | Préparation/exécution | Validation indépendante |
|---|---|---|
| parseur, IDs, checksum, tick, règles | Codex, tests EditMode purs | Zak relit les invariants ; Mac/Windows comparent les sorties |
| scène, colliders, reset, zéro mesh gameplay | Codex + Sean | Nils depuis génération propre |
| FishNet local, late join, révision, spam | Codex sur deux instances | Zak reproduit le scénario ciblé |
| Windows IL2CPP | scripts Codex | propriétaire PC opère, Nils témoigne |
| trois réseaux/reconnexion | harness Codex | Zak/Sean/Nils tournent hôte et clients |
| DVC et import Blender→Unity | manifests/validateurs Codex | Nils pousse, Zak restaure, Sean valide le contenu |
| calibration gabarit | build Codex | une personne choisit seulement le feel |
| duel mur 1v1 | Sean modère sans indice | deux joueurs ; Nils sépare technique/compréhension/ressenti |

Principe : Codex épuise d’abord les tests automatisables. L’équipe n’est mobilisée que pour un
compte, une autre machine, un réseau réel, un droit, une décision produit ou un ressenti humain.

## Prochaine action autonome

Après livraison propre de la préparation actuelle, les deux premières tranches que Codex peut
réaliser seul sont `PROV-01`, puis `TOP-01A`, dans deux PR séparées. Elles ferment un défaut de preuve
réel puis transforment les fixtures existantes en contrat C# exécutable sans inventer de règle de
game design. `TOP-01B` et `INP-01A` suivent, tandis que l’équipe ferme G0, Windows et DVC en parallèle.
