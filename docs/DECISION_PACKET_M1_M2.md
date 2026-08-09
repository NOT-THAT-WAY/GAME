# Dossier de décisions M1–M2

Ce dossier ferme les questions qui changent réellement la simulation ou le but du jeu. Les
recommandations sont des baselines à accepter, amender ou refuser par les propriétaires indiqués ;
elles ne donnent pas à Codex l’autorisation de les transformer silencieusement en constantes.

## État technique observé

- Le prototype génère une capsule de `1,40 m` de haut, `0,45 m` de rayon et des yeux à `1,05 m`.
- Le saut, les efforts et cooldowns actuels utilisent encore le temps de frame du prototype.
- FishNet `4.7.2` a un `TimeManager` à `30 ticks/s` et `PhysicsMode.Unity` par défaut. Son code local
  précise que le tick rate n’est pas synchronisé automatiquement.
- En `PhysicsMode.TimeManager`, FishNet appelle `OnTick`, simule ensuite PhysX avec `TickDelta`, puis
  appelle `OnPostTick`. Il remplace aussi `Time.fixedDeltaTime` par `TickDelta`.
- L’ADR 0004 fixe déjà l’autorité hôte, les transitions par tick, la topologie logique et la
  prédiction/réconciliation ; les décisions ci-dessous complètent ce cadre.
- HT-00 a validé caméra, déplacement, saut et punch sans crash. Il ne fournit aucune mesure de feel
  suffisante pour choisir hauteur, tick rate, énergie ou règle de manche.

## DEC-01 — simulation M1

Propriétaires : Nils (pilote), Zak (réseau/physique), Sean (gabarit/feel).

### Taux de tick

| Option | Gain | Coût/risque | Verdict proposé |
|---|---|---|---|
| `30 Hz` | coût CPU/réseau bas, valeur FishNet actuelle | pas logique de `33,3 ms`, collision de pivot moins fine | repli mesuré |
| `60 Hz` | pas de `16,7 ms`, cohérent avec un duel FPS réactif | environ deux fois plus de simulations/envois que 30 | **baseline recommandée** |
| `120 Hz` | pas de `8,3 ms` | coût disproportionné pour un prototype 2–12 joueurs | écarté pour M1 |

La baseline `60 Hz` n’est acceptée que si le PC Windows hôte et les deux Mac tiennent une session de
20 minutes sans tick drop persistant. Le test compare d’abord `30` et `60`; `120` sert seulement de
stress ponctuel. Le manifest de build et le handshake enregistreront la valeur choisie, car FishNet
ne la négocie pas.

### Ordre physique

Options : laisser Unity simuler dans `FixedUpdate`, désactiver PhysX et tout calculer analytiquement,
ou faire simuler PhysX par le `TimeManager` FishNet.

Recommandation M1 : `PhysicsMode.TimeManager`. Dans `OnTick`, après lecture réseau et reconcile :

1. valider les intentions du tick ;
2. résoudre les transitions de murs ;
3. poser tous les colliders logiques et appeler une seule fois `Physics.SyncTransforms()` ;
4. appliquer la politique mur/joueur ;
5. simuler les commandes joueur ;
6. laisser FishNet exécuter `Physics.Simulate(TickDelta)` ;
7. produire snapshots/révisions dans `OnPostTick`.

Cette recommandation aligne réseau et physique, mais ne promet pas PhysX bit-identique entre ARM et
x86. Le serveur reste la vérité ; checksum et état logique portent sur les données discrètes, pas sur
les flottants bruts de PhysX.

### Gabarit du joueur

| Option | Avantage | Risque |
|---|---|---|
| conserver `1,40 m / 0,45 m / yeux 1,05 m` | correspond à l’asset et au smoke actuel | caméra très basse, référence concept à `1,80 m` non respectée |
| passer à `1,80 m` | échelle humaine et référence concept | silhouette/asset de `1,34 m` désaccordés, collisions et cadrage à reprendre |
| choisir une troisième valeur | possibilité de meilleur feel | compromis arbitraire sans preuve |

Pas de valeur inventée ici. Sean prépare dans la graybox deux capsules `1,40 m` et `1,80 m`, même
rayon, même vitesse et même FOV : ce premier passage isole hauteur et position des yeux. Rayon,
`stepOffset` ou pente ne changent ensuite que dans un test séparé à une variable. Le gabarit retenu
devient une donnée canonique unique, jamais une copie dans le prefab et le générateur.

### Saut

- **Durable** : mobilité expressive, mais état vertical prédit, anti-bunny-hop et contournement du
  labyrinthe entrent immédiatement dans le périmètre.
- **Absent de M1** : la graybox teste pivot, contestation et prédiction horizontale sans que les
  gravats du FBX imposent un verbe de production.
- **Mantle/contextuel** : peut mieux servir les obstacles, mais constitue une feature distincte.

Recommandation : retirer le saut du banc M1 et le conserver seulement dans le smoke historique. Le
réintroduire exige un test montrant qu’il sert le duel plutôt qu’un bouton de déblocage.

### Mur contre joueur

| Option | Propriété | Dette créée |
|---|---|---|
| refuser la transition | pas d’écrasement ni déplacement forcé | body-block et stalemate possibles |
| déplacer le joueur | la transition gagne | résolution de sweep/reconcile complexe, risque de clipping |
| KO | conséquence immédiatement lisible | santé, respawn et règle de manche deviennent prérequis |

Recommandation M1 : refuser la transition si le volume d’arrivée ou l’arc balayé est occupé, avec
raison autoritaire journalisée. Mesurer les refus et rouvrir le choix si le body-block domine le
playtest ; ne pas introduire KO avant DEC-04.

### Hébergement et transport

Recommandation M1 : listen-server accepté comme limite explicite, profils Tugboat et Steam séparés,
aucun Multipass. Une build multi-transport n’a de valeur que si le même exécutable doit choisir son
transport à l’exécution ; ce besoin n’existe pas encore.

### Sortie DEC-01

La décision complète renseigne : `tickRate`, `physicsMode`, ordre de callbacks, gabarit complet,
statut du saut, politique mur/joueur, modèle d’hébergement et profils de transport. Elle amende
l’ADR 0004 et définit les champs futurs de `M1SimulationSettings`; elle n’implémente pas encore le
joueur ou le mur.

## DEC-02 — garantie de connectivité

Propriétaires : Sean (pilote), Zak (validation topologique), Nils (preuve).

| Option | Ce qu’elle garantit | Limite |
|---|---|---|
| A — tous les spawns reliés | aucun joueur isolé de tous les autres | peut interdire des mouvements tactiques intéressants |
| B — spawn vers objectif | la manche reste gagnable | impossible tant que l’objectif DEC-04 n’est pas fixé |
| C — zone de duel seulement | preuve M1 simple et bornée | ne protège pas toute la map 16x16 |
| D — aucune garantie, reset | liberté maximale | softlock accepté puis réparé, mauvais signal pour un duel compétitif |

Recommandation : **C pour M1**, avec les deux cellules de spawn de la graybox mutuellement
accessibles après chaque état accepté. Au passage M2, remplacer C par B dès que DEC-04 nomme les
zones de départ et d’arrivée. Ne pas appliquer A aux quatre entrées de la map 16x16 avant d’avoir
mesuré combien de transitions elle élimine.

Fixture acceptée minimale : le pivot change de pose et les deux spawns gardent un chemin. Fixture
refusée : la transition ferme l’unique arête entre un spawn et la zone de duel. Le refus porte un
code stable (`connectivity_would_break_duel_region`), jamais un texte dépendant de l’UI.

## DEC-03 — énergie, effort et contestation

Propriétaires : Sean + Nils (règle/feel), Zak (résolution au tick), testeur non auteur.

### Modèle de ressource

| Option | Lecture | Risque |
|---|---|---|
| A — effort sans énergie | isole le pivot, très facile à équilibrer | maintien/spam sans arbitrage long terme |
| B — énergie partagée sprint/push/punch | décisions tactiques lisibles, une seule jauge | chaque verbe peut rendre les autres inutiles |
| C — ressources séparées | réglage indépendant | UI et règles plus lourdes qu’un premier duel |

Recommandation : A pour valider d’abord le modèle réseau `WALL-01`, puis B pour `INT-01`. C est
écarté tant qu’un test ne démontre pas que la jauge unique empêche une stratégie utile.

### Résolution simultanée

Recommandation de contrat déterministe :

- toutes les intentions valides d’un même tick sont agrégées avant mutation ;
- la poussée fournit un effort signé continu ; le punch fournit une impulsion signée plus forte ;
- des efforts exactement opposés s’annulent : le mur reste en place et les deux joueurs paient le
  coût de leur action ;
- aucun `ClientId`, ordre d’arrivée RPC ou rôle d’hôte ne départage une égalité ;
- en cas de changement de signe net, l’effort accumulé revient d’abord vers zéro avant de repartir ;
- cooldown, énergie, effort et régénération sont des entiers ou fractions rationnelles par tick.

Trois presets de graybox suffisent avant de choisir les nombres : rapide (`2 s / 2 punches`), moyen
(`3 s / 3 punches`, proche du mur actuel) et lourd (`4 s / 4 punches`). Les secondes sont converties
en ticks après DEC-01. Le test compare compréhension et possibilité de contre-pousser ; il ne cherche
pas encore un équilibrage final.

### Sortie DEC-03

Enregistrer énergie max, régénération, coût par verbe, effort par tick, impulsion du punch, seuil de
transition, perte d’effort, cooldowns, résolution de signe et égalité. Un tableau de séquences couvre
au minimum : push seul, punches seuls, combinaison, opposition égale, opposition inégale, deux
intentions au même tick, énergie insuffisante et déconnexion en effort.

## DEC-04 — règle de manche M2

Propriétaires : Nils + Sean ; Zak vérifie que le résultat est autoritaire et réinitialisable.

| Prototype | Hypothèse testée | Risque |
|---|---|---|
| orientation tenue | la contestation du pivot est amusante en soi | navigation presque absente, camping possible |
| passage vers zone adverse | le pivot crée une route lisible et tactique | rush, spawn et connectivité deviennent critiques |
| score d’actions | les joueurs aiment manipuler/contrer souvent | récompense le spam et mesure un proxy plutôt qu’un but |

Recommandation : utiliser **orientation tenue** comme round de calibration très court dans la
graybox, puis choisir **passage** comme candidat principal M2 si les joueurs comprennent la route.
Le score d’actions ne devient une règle qu’en dernier recours ; ses compteurs restent utiles comme
télémétrie, pas comme objectif par défaut.

Chaque option doit définir avant code : état initial, countdown, condition de victoire, durée/timeout,
égalité au même tick, déconnexion, late join, respawn éventuel, nombre de rounds et reset complet.
Trésor, santé, KO et extraction restent hors scope tant que la règle minimale fonctionne sans eux.

## Session de décision minimale

Une séance de 45 minutes suffit si les propriétaires arrivent avec ce dossier lu :

1. 15 min — DEC-01 : choisir baseline tick/physique, sélectionner le test de gabarit, fermer
   saut/mur/listen-server ;
2. 8 min — DEC-02 : choisir la portée de connectivité M1 puis M2 ;
3. 12 min — DEC-03 : choisir modèle A/B et règle simultanée, sélectionner deux presets à tester ;
4. 10 min — DEC-04 : choisir le round de calibration et le candidat de manche.

La sortie est un compte rendu avec `ACCEPTED`, `REJECTED` ou `NEEDS-MEASURE` pour chaque ligne. Une
ligne `NEEDS-MEASURE` nomme exactement la graybox, la métrique, l’opérateur et la date ; elle ne se
transforme pas en constante provisoire cachée.

## Tests humains réellement nécessaires après décision

- gabarit `1,40` contre `1,80` : une personne, cinq minutes, même graybox ;
- deux presets d’effort maximum : deux joueurs, trois rounds chacun ;
- orientation tenue contre passage : deux joueurs, deux rounds chacun ;
- tout le reste est d’abord couvert par tests EditMode/PlayMode, replay de séquences de ticks,
  arrivée tardive et comparaison Mac/Windows.

Ces tests ne demandent ni questionnaire long, ni découverte sans consigne. L’opérateur exécute les
actions prévues ; Codex collecte les événements et la personne ne tranche que le feel impossible à
déduire des tests automatisés.
