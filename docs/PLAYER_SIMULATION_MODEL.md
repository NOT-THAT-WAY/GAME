# Simulation joueur pure — contrat PLY-01

`PlayerStateMachine` transforme exactement une `PlayerCommand` en un `PlayerState` à chaque tick. Le
modèle ne connaît ni `MonoBehaviour`, ni FishNet, ni `CharacterController`, ni temps de frame. Son
unique frontière externe est `IPlayerCollisionWorld.Move`, appelée une fois par tick accepté.

## État réconciliable

Un snapshot joueur contient tout l’état mutable nécessaire à une reprise exacte :

- tick traité, position, yaw et pitch en centièmes de degré ;
- vitesse horizontale contrôlée et vitesse verticale séparée ;
- vitesse de knockback restante ;
- contact au sol ;
- fenêtres coyote et buffer de saut restantes, exprimées en ticks.

`RestoreState` remplace cet ensemble atomiquement et fixe l’origine du tick suivant. Un tick dupliqué,
sauté ou ancien est refusé ; le passage `uint.MaxValue → 0` reste accepté par le modèle pur. FishNet
réserve toutefois le tick `0` et sa couche de prédiction devra gérer cette différence à sa frontière.

## Paramètres, pas décisions cachées

`PlayerSimulationConfig` est fourni explicitement à chaque instance. Il porte durée du tick, capsule,
vitesses, accélérations/décélérations sol-air, gravité, vitesse collée au sol, saut activé ou non,
fenêtres de saut, décroissance du knockback et limite de pitch.

Il n’existe ni preset global ni `ScriptableObject` canonique pour le moment. Le banc M1 peut donc
tester plusieurs gabarits et garder le saut désactivé sans inscrire prématurément une décision de
game design dans le moteur. DEC-01 choisira plus tard les valeurs sérialisées de l’adaptateur Unity.

## Ordre d’un tick

1. Valider le payload et la continuité du tick sans modifier l’état.
2. Appliquer yaw/pitch ; le mouvement utilise immédiatement le nouveau yaw.
3. Décoder et renormaliser les axes, choisir marche/sprint, puis accélérer vers une cible plus rapide
   ou décélérer vers une cible moins rapide, y compris lors d’une baisse de stick ou de sprint.
4. Ajouter l’impulsion horizontale externe du tick.
5. Résoudre saut/buffer/coyote, puis appliquer la gravité.
6. Construire un déplacement métrique et appeler une seule fois le monde de collision.
7. Prendre sa position résolue comme vérité ; traiter plafond et sol.
8. Mettre à jour événements et fenêtres, puis décroître le knockback pour le tick suivant.
9. Publier le nouvel état seulement lorsque toutes les étapes ont réussi.

Une exception de collision, une commande invalide ou un appel réentrant ne publie donc jamais un
demi-état. Réconcilier pendant un tick est également refusé.

## Fenêtres de saut

Avec `CoyoteTicks = N`, quitter le sol publie `N` opportunités sur les ticks futurs. Avec
`JumpBufferTicks = N`, un appui en l’air reste disponible pendant `N` ticks futurs ; s’il touche le
sol durant cette fenêtre, il est conservé sur le tick d’atterrissage et consommé au tick suivant.
Lorsque le saut est désactivé, l’appui est ignoré et les deux compteurs restent à zéro.

## Collision et réseau

Le modèle émet position de départ, déplacement désiré, yaw et dimensions de capsule. L’adaptateur
Unity convertira ce contrat en un unique `CharacterController.Move` et retournera position effective
ainsi que les drapeaux `Sides`, `Above` et `Below`.

Les calculs trigonométriques purs rendent les séquences indépendantes du framerate, mais ne promettent
pas un PhysX bit-identique entre macOS et Windows. Le serveur sera la référence et PLY-02 absorbera
les écarts par réconciliation. Son DTO FishNet mutable restera séparé des structures immuables du
domaine ; pendant un replay, les colliders des murs devront d’abord être replacés au tick rejoué.

## Preuve locale

Les tests EditMode couvrent configuration et états invalides, payload forgé, ordre et wrap des ticks,
mouvement/yaw, diagonale/sprint, paramètres d’accélération, collision unique, plafond/sol, saut
désactivé, bornes exactes coyote/buffer, knockback, restauration, indépendance aux lectures de rendu,
réentrance et échec atomique. La gate statique interdit `UnityEngine`, FishNet et les horloges Unity
dans ce dossier.
