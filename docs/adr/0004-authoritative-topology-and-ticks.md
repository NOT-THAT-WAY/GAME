# ADR 0004 — Topologie, ticks et gameplay sous autorité de l'hôte

**Statut : accepté — 2026-08-05**, amendé le 2026-08-10 par
[l'ADR 0005](0005-continuous-wall-rotation.md) sur la seule forme du segment répliqué d'un mur
mobile : un battant libre réplique désormais un angle, une vitesse angulaire, un tick d'ancrage et
une révision, au lieu d'un couple de poses et d'une durée. L'interdiction de diffuser un transform
par image et tout le reste de cet ADR restent en vigueur.

## Contexte

Le premier playtest du labyrinthe a prouvé qu'un build Mac peut importer la map, connecter un hôte et un client, afficher leurs déplacements et demander la rotation des 17 pivots. Il ne prouve pas encore une simulation réseau correcte :

- `PlayerMotor` déplace le propriétaire localement puis laisse un `NetworkTransform` client-authoritative diffuser le résultat ;
- `PivotDirector` réplique seulement une orientation et anime localement le transform et son collider avec `Time.deltaTime` ;
- les cooldowns et durées d'effort dépendent de temps locaux ;
- `MazePlaytestBuild` génère les collisions depuis des objets du FBX avec des `MeshCollider`, alors que le JSON contient déjà la topologie de la grille ;
- la connexion manipule directement une adresse et un port Tugboat.

Ces choix restent utiles à un smoke test court, mais deux machines peuvent échantillonner des collisions différentes pendant une rotation et le serveur fait encore confiance à des décisions du client. Ils ne sont pas une base à étendre pour M1.

## Décision

### Une simulation partagée pilotée par ticks

L'hôte listen-server est autoritaire. Toute position, collision, transition de mur, énergie, cooldown, interaction, KO et règle de victoire avance sur le tick réseau FishNet. Le client envoie des commandes d'intention horodatées par tick ; le serveur les valide, simule le résultat et produit l'état de référence.

`Time.time`, `Time.deltaTime`, `Update` et l'instant local de réception peuvent piloter caméra, UI, audio ou interpolation visuelle. Ils ne déterminent jamais un résultat partagé. La fréquence exacte des ticks sera choisie et mesurée dans une PR de configuration dédiée ; le code de domaine ne la suppose pas en dur.

L'ordre autoritaire d'un tick est :

1. consommer et valider les intentions reçues pour le tick ;
2. démarrer les transitions de murs acceptées ;
3. échantillonner la pose logique des murs et mettre à jour la collision de la topologie ;
4. appliquer la politique explicite aux joueurs chevauchés par un mur ;
5. simuler les commandes des joueurs contre cette topologie ;
6. produire l'état et les révisions autoritaires ;
7. réconcilier les clients, puis seulement interpoler les visuels.

### Des murs décrits par leur état, pas par leur transform

Chaque mur ou pivot possède un identifiant entier stable fourni par la donnée. Une transition réseau contient au minimum l'équivalent de :

```text
wallId, fromState, toState, startTick, durationTicks, revision
```

La pose logique d'un mur est une fonction déterministe de cet état et du tick échantillonné. Un événement annonce une transition ; un snapshot restitue l'état complet aux arrivées tardives et reconnexions. Une révision plus ancienne ne peut pas écraser une plus récente.

Le serveur valide notamment : joueur connecté et actif, cible existante, portée, contact ou ligne de vue, côté et couple permis, durée d'effort, énergie, cooldown, contestation et espace de collision. Un RPC reçu par le serveur n'est pas, à lui seul, une validation autoritaire.

### Une topologie logique comme source de vérité

La map runtime utilise un schéma typé avec `schemaVersion`, des IDs entiers stables, des dimensions canoniques entières (`cellPitchMm`, `wallThicknessMm`, `wallHeightMm`), les ouvertures, les pivots, les apparitions et un checksum. Cette même donnée alimente collision, snapshot réseau, validation, tests puis, plus tard, navigation, intérêt réseau et propagation audio.

Le FBX fournit le rendu. Son nommage peut aider l'import ou diagnostiquer un export, mais ni un nom de GameObject, ni l'ordre de la hiérarchie, ni les triangles d'un `MeshCollider` ne définissent une règle gameplay ou un identifiant réseau. Les colliders autoritaires sont générés depuis la topologie avec des primitives simples ou une représentation déterministe équivalente.

### Un déplacement prédit et réconcilié

Le joueur produit une commande compacte par tick depuis les Input Actions. Le serveur simule la même logique pure et FishNet assure la prédiction/réconciliation avec `Replicate`/`Reconcile`. Les actions couvrent au minimum clavier/souris et manette afin de ne pas bloquer la cible portable future.

Le `NetworkTransform` client-authoritative actuel et les lectures directes de `Keyboard.current`/`Mouse.current` sont des dettes de prototype à remplacer, pas des conventions à recopier.

### Une frontière de connexion stable

Le démarrage reçoit un `ConnectionTarget` indépendant du transport. Aujourd'hui, il résout une adresse et un port Tugboat ; après la gate Steam, il pourra résoudre un lobby sans faire connaître Steam au gameplay. Multipass ne sera ajouté que si une build doit réellement exposer plusieurs transports à la fois.

### Des preuves sur une scène minimale

La preuve réseau de référence utilise une scène grise déterministe avec un pivot et deux joueurs. La map 16x16 reste un test d'import, de rendu et d'intégration, pas le banc principal de prédiction ou de collision.

Toute PR qui change un état partagé ajoute des tests du modèle pur et, selon le risque, vérifie : arrivée tardive pendant une rotation, reconnexion, 30/60/120 FPS, profil `80 ms RTT / 2 % perte / 20 ms jitter`, et même résultat sur Mac et Windows IL2CPP au même commit.

## Décisions encore ouvertes

Ces choix ne doivent pas être tranchés silencieusement dans une implémentation :

- conséquence d'un mur qui se referme sur un joueur : mouvement refusé, KO ou autre règle ;
- taux de tick et relation exacte avec la physique Unity ;
- hauteur canonique du joueur, actuellement 1,40 m dans le dépôt contre 1,80 m dans le document de référence ;
- saut comme verbe durable ou contournement provisoire des props ;
- profils Tugboat/Steam séparés ou Multipass dans une même build.

Chaque choix devient un amendement à cet ADR ou un ADR dédié, avec une preuve jouable.

## Migration

Les étapes sont indépendantes et doivent rester testables :

1. extraire et valider le schéma typé de topologie, ses IDs et son checksum ;
2. générer la collision simple de la scène grise depuis cette topologie ;
3. implémenter les transitions de murs par tick, snapshots et arrivée tardive ;
4. remplacer le déplacement client-authoritative par commandes, prédiction et réconciliation ;
5. brancher la map 16x16 comme test d'intégration ;
6. seulement ensuite ajouter énergie, contestation, trésor ou nouvelles interactions réseau.

## Conséquences

- davantage de code C# pur et de tests, moins de règles cachées dans les scènes et FBX ;
- un visuel peut rattraper l'état sans modifier la collision ou le résultat ;
- les maps deviennent vérifiables entre Mac, Windows, hôte et client par checksum ;
- Steam, Wwise et le contenu final restent découplés de la validation du duel ;
- les prototypes actuels peuvent subsister comme smoke tests tant qu'ils sont clairement étiquetés et ne sont pas étendus comme architecture de production.
