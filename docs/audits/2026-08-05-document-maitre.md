# Audit du document technique maître — 5 août 2026

## Résultat

Le dépôt possède un bon socle M0, mais le prototype de pivot ajouté sur `main`
contredit déjà trois invariantes centrales du document maître : mouvement calculé
par tick, état réseau incluant le tick de départ, et collisions générées depuis la
grille plutôt que depuis le maillage. La prochaine étape utile n'est donc pas
d'ajouter un nouveau verbe de gameplay : il faut d'abord sécuriser les sources
d'assets, terminer la preuve M0 et remettre le pivot sur une architecture rejouable.

Le document maître est une bonne base de recherche et de risques. Il ne doit pas
être copié tel quel comme contrat du dépôt : il contient des hypothèses, des
absolus techniques à nuancer, des données commerciales volatiles et au moins une
affirmation Steam fausse.

## Périmètre et instantané audité

- source : `NOT-THAT-WAY-document-maitre.md`, copie locale fournie depuis
  `Downloads/` ;
- empreinte SHA-256 :
  `08cfee207d6e1d892bd743f44e3e8d3633cda81de7f83b5a78f50f2e52f8090f` ;
- taille : 36 091 octets, 604 lignes ;
- modification locale : `2026-08-05T11:50:40+0200` ;
- dépôt audité : commit `6bff31ba87fa3c58eb4229f34c006a975d7ca8d6` ;
- branche d'audit : `docs/audit-document-maitre` ;
- état du dépôt avant l'audit : propre ;
- versions, scripts, Git/LFS/DVC, CI, réglages Unity, code runtime, documentation,
  build Mac local et état des contrôles GitHub inspectés.

Les numéros de ligne ci-dessous désignent cet instantané. Ils pourront bouger
après correction.

## Verdict exécutif

### À conserver

- Unity `6000.3.20f1`, URP `17.3.0`, Input System `1.20.0`, FishNet `4.7.2`,
  Multiplayer Play Mode `2.0.2` et Multiplayer Tools `2.2.10` sont bien figés ;
- Force Text, Visible Meta Files, LF, UnityYAMLMerge, Git LFS et les hooks partagés
  sont réellement configurés ;
- la cible Windows x86_64 IL2CPP et les éditeurs Mac Apple Silicon sont cohérents ;
- le renderer PC est bien en Forward+ et le projet en espace colorimétrique linéaire ;
- la CI légère passe sur `main` et vérifie politique de branche, contrat du dépôt et
  syntaxe PowerShell ;
- le décalage de Wwise et Steam derrière des gates est sain ;
- le choix d'une scène de playtest générée localement évite des conflits YAML et
  mérite d'être conservé ;
- le JSON actuel contient déjà la topologie utile : murs verticaux/horizontaux,
  17 pivots, entrées, trésor et seed. Il faut en faire la source runtime plutôt que
  repartir de zéro.

### À corriger avant d'étendre le gameplay réseau

1. Le pivot ne transporte qu'un `SyncList<byte>` d'orientations. Il manque au
   minimum un identifiant stable, l'état précédent/cible, `startTick`, une durée en
   ticks et une révision.
2. Le collider de chaque pivot tourne localement avec `Time.deltaTime` à partir du
   moment où le message arrive. Deux clients ont donc volontairement des colliders
   à des angles différents pendant la transition.
3. Le cooldown du pivot utilise `Time.time`, et la durée de poussée est décidée par
   le client. Le serveur ne valide ni la durée d'effort, ni le rayon de contact, ni
   le sens du couple, ni une ligne de vue.
4. Le déplacement utilise un `NetworkTransform` client-authoritative sans
   `Replicate`/`Reconcile`. Le serveur fait confiance à la position envoyée par le
   client ; ce n'est pas encore l'hôte autoritaire décrit par les contrats.
5. Les collisions sont des `MeshCollider` posés sur des objets du FBX, y compris
   les pivots et les props. La topologie JSON n'est lue que pour les dimensions et
   les points d'apparition.
6. Il n'existe aucun test EditMode ou PlayMode du projet et aucun profil réseau
   dégradé versionné.

### À décider, pas à appliquer silencieusement

- hauteur canonique du joueur : `1,40 m` dans le dépôt, `1,80 m` dans le document ;
- format de référence : map actuelle marquée `6-8 joueurs`, document demandant
  `4-6`, alors que la preuve immédiate doit être un duel à deux ;
- conséquence d'un mur qui se ferme sur un joueur : mouvement refusé, KO, ou autre ;
- Multipass dans une même build ou profils Tugboat/Steam séparés ;
- saut comme verbe réel ou simple contournement provisoire des props bloquants ;
- éclairage entièrement temps réel ou solution hybride mesurée ;
- tick rate et ordre exact de simulation mur/joueur/physique.

## État par domaine

| Domaine | État réel | Interprétation |
|---|---|---|
| Environnements Mac/Windows | partiel | Mac pilote validé ; second Mac, Windows IL2CPP et session distante à trois restent la sortie M0 |
| Stack et sérialisation Unity | conforme | versions, lockfile, Force Text et Visible Meta Files sont contrôlés automatiquement |
| Git et collaboration | conforme avec limite connue | hooks + PR + CI actifs ; pas de protection serveur absolue sur le plan actuel |
| Git LFS | conforme mais documentation périmée | deux objets LFS existent déjà, environ 38 Mo au total |
| DVC | devenu urgent | aucun remote ni pointeur alors que deux masters Blender sont déjà nécessaires pour régénérer les exports |
| CI | partiel et volontaire | contrôles statiques présents ; aucune compilation Unity, aucun test Unity, aucun scan gitleaks |
| Connexion Tugboat/Tailscale | partiel | roster et build Mac prouvés ; preuve distante à trois absente |
| Cible de connexion abstraite | absent | `ConnectionSmokeTest` manipule directement adresse et port Tugboat |
| Pivot réseau | non conforme | état discret présent, mais sans tick de départ et avec collider animé par frame |
| Déplacement réseau | prototype seulement | client-authoritative, sans prédiction/réconciliation FishNet |
| Topologie de labyrinthe | donnée présente, modèle runtime absent | JSON riche ; code runtime dépend encore du FBX, de ses noms et de ses MeshCollider |
| Input | partiel | Input System installé, mais lecture directe de `Keyboard.current`/`Mouse.current`, sans actions ni manette |
| Rendu | partiel | Forward+ et Linear corrects ; aucune baseline de performance ni préchauffage de shaders |
| Wwise/voix | correctement différé | intégration absente ; licence et spike de compatibilité à traiter séparément |
| Steam | correctement différé | aucun package Steam ; seam de connexion à créer avant la gate |
| Tests | absent | package Test Framework présent, aucune assembly ni cas de test du jeu |
| Documentation | incohérente | état LFS et gameplay périmés ; `MAZE_PLAYTEST.md` se contredit sur le pivot |

## Les écarts bloquants en détail

### P0 — finir réellement M0

Le projet reste M0 tant que les preuves binaires du dépôt ne sont pas satisfaites :

1. clone et ouverture/fermeture propres sur le second Mac ;
2. build Windows Development x86_64 IL2CPP lancé ;
3. même commit sur les trois machines ;
4. trois participants authentifiés par Tugboat depuis trois réseaux via Tailscale ;
5. résultat résumé dans une issue privée sans IP ni log nominatif brut.

Le build Mac local du profil `maze` a réussi le 5 août et le runtime local a trouvé
17 pivots côté serveur et client. Cela prouve la compilation Mac du commit audité,
pas la sortie M0 multi-OS.

### P0 — ouvrir le coffre DVC maintenant

Le texte du dépôt disait que DVC pouvait attendre « le premier master lourd ».
Cette condition est désormais arrivée :

- `Assets/_Project/Maze/Maze16x16.fbx` fait environ 38 Mo et dépend d'un `.blend`
  absent du dépôt ;
- `Assets/_Project/Player/PersoBoule.fbx` dépend lui aussi d'un master absent ;
- le registre indique explicitement « master hors dépôt en attente du coffre DVC ».

Actions précises :

1. choisir le remote privé avec versioning objet et comptes individuels ;
2. créer deux lots séparés, `ART-MAZE-001` et `ART-PERSO-001` ;
3. ajouter masters, scripts exacts, entrées, presets et README de régénération ;
4. enregistrer commit du générateur, version Blender, seed, paramètres d'export et
   empreintes des entrées ;
5. pousser DVC avant Git ;
6. restaurer les deux lots sur l'autre OS et reproduire au moins les exports ou
   leurs empreintes attendues.

Reporter encore ce gate crée un risque de perte de la seule source régénérable.

### P0 — ne plus étendre le pivot actuel

Dans `Assets/_Project/Runtime/Maze/PivotDirector.cs` :

- ligne 32 : `SyncList<byte>` ne contient que l'orientation ;
- lignes 75-89 : la rotation réelle du Transform et du collider dépend de
  `Time.deltaTime` ;
- lignes 102 et 115 : cooldown fondé sur `Time.time` ;
- lignes 96-117 : le RPC ne valide que l'index, un délai et une distance tolérée
  jusqu'à `3,9 m` ;
- ligne 116 : le nouvel état est appliqué dès réception, sans calendrier partagé.

Dans `Assets/_Project/Runtime/Player/PlayerMotor.cs` :

- lignes 117-172 : le client mesure seul la durée d'appui, choisit le mur et le sens ;
- lignes 98-109 et 211-254 : déplacement et saut sont exécutés par frame uniquement
  chez le propriétaire ;
- aucune énergie, contre-poussée, frappe ou conséquence de collision n'est encore
  autoritaire.

Conséquence concrète : le commentaire affirmant que deux angles intermédiaires
différents sont sans importance est faux tant que le maillage animé porte aussi le
collider. Une différence visuelle serait acceptable ; une différence de collision
ne l'est pas.

### P0 — séparer la preuve de fun de la map habillée

La map 16x16 actuelle est une bonne preuve d'import, d'échelle et de déplacement.
Elle n'est pas le bon banc de test pour décider si le duel central est amusant :

- elle contient 17 pivots et est annotée `6-8 joueurs` ;
- elle embarque végétation, jarres, colonnes, sable et éclairage ;
- le saut a été ajouté en partie pour se décoincer des props ;
- le M1 demandé est un duel compréhensible autour d'un pivot en cubes gris.

Conserver `MazePlaytest` comme scène d'intégration. Ajouter un profil séparé
`pivot` : une petite arène grise, un seul T, deux points d'apparition, aucune prop,
compteurs réseau visibles et redémarrage immédiat. Ce profil doit permettre de
tester en quelques secondes poussée, contre-poussée, énergie, collision et KO.

### P0 — remettre la documentation à l'heure

- `README.md:21` dit que le gameplay « vient juste après », alors qu'il existe ;
- `README.md:80` et `docs/ASSETS.md:5` annoncent zéro objet LFS et 164 Kio, alors
  que deux FBX LFS totalisent environ 38 Mo ;
- `docs/MAZE_PLAYTEST.md:13-16` dit que la rotation des pivots n'est pas prouvée,
  puis `docs/MAZE_PLAYTEST.md:67-90` la présente comme implémentée ;
- `docs/ROADMAP.md` ne reflète pas les PR de map, déplacement, saut et pivot ;
- la documentation des collisions présente les MeshCollider comme une optimisation,
  alors que le document maître les interdit pour la géométrie générée.

Cette correction est indépendante du refactor : la documentation doit décrire le
prototype tel qu'il est, avec la mention explicite « preuve locale non conforme au
contrat tick/collision, à remplacer avant Sprint B ».

## Architecture cible recommandée pour M1

Le point structurant du document est juste : une seule topologie doit alimenter
plusieurs systèmes. La frontière `NetworkBehaviour` proposée par le document ne
l'est pas. La simulation testable doit rester en C# pur, avec des adaptateurs
FishNet aux frontières.

```text
MazeDefinition JSON versionné
        |
        v
MazeTopology (entiers, IDs stables, checksum)
        |
        +--> colliders Box/Compound générés
        +--> snapshot réseau + interest management futur
        +--> graphe visibilité / A* futur
        +--> géométrie acoustique Wwise future
        |
        v
PivotSimulation par tick <--> PlayerSimulation par tick
        |                              |
        +----------- adaptateurs FishNet -----------+
                       |
             vues et interpolation cosmétique
```

### 1. Contrat de topologie

Créer un modèle runtime typé et versionné, consommé par l'éditeur et le jeu :

- `schemaVersion` ;
- largeur/hauteur ;
- `cellPitchMm`, `wallThicknessMm`, `wallHeightMm` en entiers ;
- tableaux de murs et pivots ;
- ID stable par mur/pivot, dérivé de la coordonnée et du bord ou enregistré
  explicitement ;
- orientation initiale ;
- entrées/spawns ;
- checksum du payload canonique.

Les décisions topologiques restent en entiers. La conversion en mètres flottants
est réservée à la vue et aux colliders après que la topologie a été décidée.

Le JSON actuel fait 6 340 octets non compressés. Ne documenter « quelques
centaines d'octets » qu'après avoir défini le format réseau, bit-packé les arêtes
et mesuré le payload réel.

### 2. Collisions depuis la grille

Remplacer `MazePlaytestBuild.cs:300-342` :

- le FBX devient uniquement visuel ;
- murs, sol bloquant et pivots obtiennent des `BoxCollider` ou colliders composés
  simples générés par `MazeTopology` ;
- les props décoratifs ne bloquent pas le duel gris, sauf décision explicite et
  collider proxy simple ;
- aucun nom de Transform du FBX ne définit une règle réseau ;
- le build échoue si un mesh visuel reçoit par erreur un `MeshCollider` dans une
  scène jouable.

Cela supprime aussi le besoin de « marteler Espace pour se décoincer » comme
solution de collision.

### 3. État du pivot rejouable

Un état de mouvement devrait contenir, conceptuellement :

```text
wallId          ushort ou ID compact stable
fromState       byte
toState         byte
startTick       uint
durationTicks   ushort
revision        ushort/uint
```

À un tick donné, la pose logique est une fonction de cet état. Le snapshot complet
sert aux arrivées tardives ; un événement compact sert aux changements. Le
cooldown devient `nextAllowedTick`, avec tests de wrap du compteur.

Ordre de simulation à figer dans un ADR :

1. appliquer l'état des murs pour le tick ;
2. évaluer la règle de fermeture (refus ou KO autoritaire) ;
3. simuler les inputs joueurs ;
4. réconcilier ;
5. interpoler seulement le rendu entre deux ticks.

`Time.deltaTime` reste légitime pour caméra, UI et interpolation purement visuelle.
Il ne pilote plus un cooldown, une énergie, une collision ou un état partagé.

### 4. Déplacement prédit, serveur autoritaire

Remplacer le `NetworkTransform` client-authoritative par le flux FishNet
`Replicate`/`Reconcile` :

- input compact par tick ;
- CharacterController simulé dans un ordre défini avec les murs ;
- état de réconciliation minimal ;
- sprint et énergie calculés en ticks ;
- seuils de correction instrumentés ;
- même test à 30, 60 et 120 fps de rendu ;
- test permanent à `80 ms RTT / 2 % perte / 20 ms jitter`.

Le `TimeManager` FishNet est actuellement laissé à ses valeurs implicites
(30 ticks/s, physique Unity). Le générateur de scène doit fixer explicitement le
tick rate et le mode de physique retenus, puis le validateur doit les contrôler.

### 5. Intents serveur plutôt que résultat client

Le client ne doit pas envoyer « tourne ce mur dans ce sens après 0,6 s ». Il envoie
un intent horodaté ; le serveur maintient l'effort et valide :

- joueur vivant et autorisé ;
- mur stable et atteignable ;
- portée et ligne de vue ;
- côté/bras de levier ;
- énergie disponible ;
- contestation éventuelle ;
- espace de fermeture ou résultat KO ;
- cooldown en ticks.

La prédiction locale peut afficher l'effort immédiatement, mais ne devient pas la
source de vérité.

### 6. Cible de connexion indépendante du transport

`ConnectionSmokeTest.cs:24-25`, `66-88` et `137-151` supposent directement une
adresse IP et un port. Introduire avant Steam :

```text
ConnectionTarget
  kind = TugboatEndpoint | SteamLobby
  address/port OU lobbyId

IConnectionConnector.Connect(ConnectionTarget target)
```

Le parseur CLI et l'UI deviennent des adaptateurs. Tugboat conserve la compatibilité
`--game-address`; Steam fournit plus tard un lobby/SteamID sans réécrire le flux de
connexion, le lobby ou les écrans d'erreur.

Multipass peut rester une décision de gate. L'abstraction de cible, elle, est
nécessaire dans les deux options.

### 7. Input Actions dès le graybox

Le package Input System est présent mais `PlayerMotor` lit directement
`Keyboard.current` et `Mouse.current`. Créer un asset `.inputactions` avec actions
Move, Look, Sprint, Jump/Interact, Push et Pause :

- clavier AZERTY/QWERTY ;
- manette ;
- rebinding futur ;
- séparation par joueur/instance ;
- base réelle pour Steam Deck.

Ne pas promettre Steam Deck tant qu'une partie complète n'est pas jouable à la
manette et testée sous Proton.

## Tests minimaux à ajouter avant la CI Unity

### EditMode / C# pur

- schéma invalide, version inconnue et dimensions incohérentes refusés ;
- IDs de murs stables indépendamment de l'ordre JSON ou des noms Blender ;
- checksum identique Mac/Windows ;
- calcul de pose du pivot aux ticks avant, début, milieu, fin et après ;
- cooldown et wrap de tick ;
- sérialisation explicite champ par champ ;
- aucune décision de grille fondée sur un float ou `UnityEngine.Random`.

### PlayMode / réseau

- host + client reçoivent le même snapshot et le même checksum ;
- late join au milieu d'une rotation ;
- deux joueurs de part et d'autre d'un mur ;
- collision au tick de fermeture selon la règle choisie ;
- perte/jitter/latence permanents ;
- framerates de rendu différents ;
- déconnexion propre ;
- absence de `MeshCollider` dans la scène pivot générée.

### Multi-OS

- Mac Mono et Windows IL2CPP au même commit ;
- même checksum de topologie et même suite d'états de pivot ;
- au moins une session réelle hors localhost ;
- preuve enregistrée sans données personnelles.

## CI et sécurité

La CI actuelle est cohérente avec la gate locale, mais elle ne compile pas le C#
Unity. La PR #19 est passée parce que les contrôles sont structurels ; sa
compilation n'a été prouvée que par le build Mac local.

Ordre recommandé :

1. ajouter les tests purs sans licence Unity ;
2. ajouter un scan de secrets avant d'introduire les credentials Unity/Wwise/Steam ;
3. terminer les builds manuels Mac + Windows au même commit ;
4. choisir le mécanisme de licence/runner ;
5. activer compilation, EditMode, PlayMode, puis build de vérification ;
6. réserver nightly/release, signature et publication à des workflows séparés.

`validate-repository.sh` détecte des chemins sensibles et des gros fichiers, mais
ne scanne ni le contenu ni l'historique comme gitleaks. Le dépôt n'autorise
actuellement que les Actions GitHub : une PR dédiée doit soit autoriser une Action
gitleaks auditée et figée par SHA, soit installer un binaire/version avec checksum
figé. Ne pas assouplir globalement la politique des Actions.

## Rendu et performance

Éléments prouvés :

- `Assets/Settings/PC_Renderer.asset:56` est en Forward+ ;
- `ProjectSettings/ProjectSettings.asset:50` active Linear ;
- ombres temps réel principales et additionnelles sont actives ;
- le renderer PC demande depth texture, opaque texture et SSAO ;
- aucun préchauffage de `ShaderVariantCollection` n'est configuré ;
- `macRetinaSupport` vaut `1`.

Le document maître demande de désactiver Mac Retina Support. Unity documente ce
champ comme un réglage du **player macOS**, plus coûteux mais plus net ; ce n'est
pas un interrupteur global de résolution de l'éditeur. Ne pas modifier le
ProjectSetting sans mesure. Pour le build Mac interne, comparer Retina activé,
Retina désactivé et render scale explicite, puis choisir une baseline. Dans
l'éditeur, contrôler séparément la résolution de la Game View.

Avant M4, fixer un budget mesurable pour GTX 1650 et MacBook Air M-série : temps
CPU/GPU, draw calls, triangles visibles, mémoire, ombres, nombre de lumières et
stutters de shaders. Le graphe de topologie pourra ensuite alimenter culling,
interest management, A* et audio ; il n'est pas nécessaire de construire ces
quatre consommateurs avant que le pivot soit amusant.

## Audio, Wwise et voix

La décision du dépôt est meilleure que la formulation définitive du document :
la chaîne Steam Voice vers Wwise Audio Input reste un spike.

Actions administratives immédiates, sans intégrer Wwise dans Unity :

1. enregistrer le projet Wwise Indie ;
2. conserver la preuve/licence dans l'espace administratif ;
3. vérifier Wwise `2025.1.4` + Unity `6000.3` sur une branche dédiée Mac/Windows ;
4. seulement ensuite passer `WWISE_ENABLED=1` avec un événement minimal.

Le plan Indie Wwise est bien annoncé gratuit jusqu'à 250 000 USD de budget de
production. La Free Trial est non commerciale et limitée à 200 médias. La demande
de licence ne doit donc pas attendre le gate d'intégration.

Steam Voice fournit capture, données compressées et décompression, mais la
documentation publique ne garantit pas un codec Opus comme contrat stable. Le
repo ne doit pas dépendre du nom du codec. Latence, périphériques, écho, mute,
indicateur de parole et injection PCM dans Wwise doivent être mesurés dans le spike.

## Corrections à apporter au document maître

### Erreur factuelle certaine

Le §12.4 affirme qu'un pack multi-copies est géré nativement par Steam. Valve dit
explicitement qu'il n'est plus possible de créer un package accordant plusieurs
copies d'une même application ; les « 4-packs » visibles sont historiques.

Source officielle : [Steamworks — Packages](https://partner.steamgames.com/doc/store/application/packages).

Retirer cette mitigation du plan commercial. Une remise de bundle ne remplace pas
un pack de quatre copies du même jeu.

### Formulations trop absolues

- « tout le code gameplay hérite de `NetworkBehaviour` » : à remplacer par
  « les frontières réseau sont des `NetworkBehaviour`; la simulation demeure
  testable en C# pur » ;
- « la fonction du tick élimine toute la classe de bugs » : elle élimine le délai
  d'arrivée comme source de pose, pas le non-déterminisme PhysX ni les erreurs
  d'ordre de simulation ;
- « Multipass maintenant » : l'abstraction de cible est obligatoire, Multipass
  reste optionnel selon le packaging retenu ;
- « éclairage baké mort » : les murs mobiles interdisent de dépendre d'un bake
  statique pour leur occlusion ; une solution hybride pour le décor fixe reste une
  hypothèse à mesurer ;
- « occlusion culling Unity inutilisable » : il ne suit pas la topologie mobile,
  mais cela ne prouve pas qu'aucun usage statique n'est rentable ;
- « Steam Voice = Opus » : codec non garanti par le contrat public ;
- « crossplay sans problème » : objectif, pas preuve ; plugins, Proton, input,
  voix et performances restent à tester ;
- « quelques centaines d'octets » : mesure à faire sur le format réel ;
- « désactiver Retina pour les éditeurs » : distinguer PlayerSetting macOS et
  résolution Game View de l'éditeur.

### Données externes à dater et sourcer

Les sections marché, wishlists, concurrence, prix, plans et licences doivent
porter pour chaque chiffre : source, URL, date d'accès, périmètre, devise et niveau
de confiance. Les seuils de wishlists ne sont pas une garantie algorithmique
Steam et ne doivent devenir un critère binaire que si l'équipe l'assume comme règle
business.

Points vérifiés au 5 août 2026 :

- Unity Personal : seuil officiel de 200 000 USD sur les douze derniers mois,
  selon la situation individuelle ou les finances agrégées de l'entreprise —
  [Unity Personal](https://unity.com/products/unity-personal) ;
- Wwise Indie : gratuit jusqu'à 250 000 USD de budget de production —
  [Wwise for Games](https://www.audiokinetic.com/en/wwise/pricing/for-games/) ;
- Tailscale Personal : six utilisateurs mais usage non commercial seulement ;
  Standard est annoncé à 8 USD/utilisateur/mois —
  [Tailscale Pricing](https://tailscale.com/pricing) ;
- GitHub Free : 10 Gio de stockage LFS et 10 Gio de bande passante incluse, avec
  facturation désormais mesurée plutôt que l'ancien pack fixe —
  [Git LFS billing](https://docs.github.com/en/billing/concepts/product-billing/git-lfs) ;
- IL2CPP : la cross-compilation est généralement non supportée ; le player cible
  doit être construit depuis un Editor de la même plateforme —
  [Unity — IL2CPP](https://docs.unity3d.com/6000.0/Documentation/Manual/il2cpp-introduction.html) ;
- Unity `6000.3` est bien la LTS actuelle, supportée jusqu'en décembre 2027 —
  [Unity 6 support](https://unity.com/releases/unity-6/support).

Le développement vise déjà un produit commercial. La note du dépôt disant de
quitter le plan Tailscale Personal « si le développement devient commercial »
doit être traitée maintenant : confirmer par écrit l'éligibilité ou passer au plan
approprié avant de prolonger son usage d'équipe.

## Source de vérité recommandée

Ne pas ajouter le fichier maître entier comme quatrième source concurrente. Le
répartir ainsi :

| Information | Source canonique |
|---|---|
| versions et flags de gate | `config/toolchain.env` + validation automatisée |
| décisions irréversibles | ADR numérotés |
| règles actuelles | `docs/PROJECT_RULES.md` |
| position et prochaines sorties | `docs/ROADMAP.md` |
| procédures reproductibles | docs de test/setup ciblées |
| hypothèses marché/licences | dossier recherche daté, sourcé, avec date de revalidation |
| catalogue des risques | checklist liée aux ADR/tests, pas prose isolée |

Ajouter un ADR sur la simulation réseau avant le refactor :

```text
ADR 0004 — Topologie autoritaire, ticks et murs mobiles
```

Il doit décider : IDs, format de snapshot, tick rate, ordre de simulation, état du
pivot, règle de collision, autorité joueur, distinction logique/rendu et tests de
réconciliation.

Mettre à jour ADR 0002 pour distinguer explicitement :

- abstraction de `ConnectionTarget` requise maintenant ;
- Multipass requis seulement si Tugboat et Steam doivent cohabiter dans le même
  exécutable ;
- profils de build séparés autorisés sinon.

## Ordre précis des prochaines PR

Les noms sont indicatifs mais respectent les conventions du dépôt.

1. `docs/update-project-state`
   - corriger README, ASSETS, MAZE_PLAYTEST et ROADMAP ;
   - enregistrer les décisions ouvertes sans modifier le gameplay.
2. `data/activate-asset-vault`
   - remote DVC, lots des deux masters, preuves de restauration Mac/Windows.
3. `docs/network-simulation-adr`
   - ADR 0004 et mise à jour ADR 0002 ;
   - choisir hauteur, tick rate et règle de collision.
4. `feat/maze-topology-runtime`
   - parser typé, schéma/version/checksum, IDs stables, colliders simples ;
   - tests EditMode ; aucun MeshCollider gameplay.
5. `feat/pivot-graybox`
   - profil à un seul pivot, deux spawns, reset immédiat, mesures visibles.
6. `feat/pivot-tick-state`
   - état avec `startTick`, snapshot late join, cooldown/énergie en ticks,
     validation serveur et tests réseau.
7. `feat/predicted-player-motor`
   - Replicate/Reconcile, ordre de simulation, profil réseau dégradé.
8. `feat/input-actions`
   - actions clavier/manette et compatibilité multi-instance.
9. `feat/connection-target`
   - seam Tugboat/Steam avant la gate transport.
10. `chore/unity-tests-ci`
    - tests Unity puis compilation/build CI seulement après preuve manuelle et
      décision de licence.

Les PR 4 à 8 peuvent être réordonnées légèrement par le pilote, mais le contrat
ADR et la sauvegarde des masters doivent précéder les refactors destructifs.

## Ce qu'il faut explicitement différer

- Wwise runtime, Spatial Audio et voix de proximité ;
- FishySteamworks, lobby Steam et Multipass concret ;
- interest management, culling de graphe, A* et bots ;
- pipeline art final, ShaderVariantCollection et optimisation avancée ;
- lobby/match complet, télémétrie et page Steam ;
- CI nightly/release, signature et publication.

Ces éléments restent dans l'architecture, mais aucun ne doit retarder le test du
duel gris ni masquer les écarts réseau actuels.

## Critère de sortie du correctif architectural M1

Le pivot peut être déclaré prêt pour le vrai playtest lorsque :

- deux machines calculent la même pose logique au même tick ;
- une arrivée tardive au milieu d'un mouvement voit immédiatement le bon état ;
- le serveur valide l'effort, l'énergie et la collision ;
- la règle de fermeture produit toujours le même résultat autoritaire ;
- le joueur est prédit puis réconcilié, pas client-authoritative ;
- aucun collider gameplay ne dépend du mesh visuel ;
- `80 ms / 2 % / 20 ms` reste jouable sans désynchronisation critique ;
- Mac Mono et Windows IL2CPP partagent checksum de grille et suite d'états ;
- deux joueurs peuvent enchaîner les duels sans relancer le processus ;
- deux personnes jouent vingt minutes et relancent volontairement.

Le dernier point reste la vraie sortie produit. Tous les autres empêchent que le
test de fun soit pollué par une architecture réseau déjà connue comme incorrecte.
