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
- fenêtres coyote et buffer de saut restantes, exprimées en ticks ;
- phase de plongeon : en vol, ticks de relevé restants, ticks d'attente restants.

`RestoreState` remplace cet ensemble atomiquement et fixe l’origine du tick suivant. Un tick dupliqué,
sauté ou ancien est refusé ; le passage `uint.MaxValue → 0` reste accepté par le modèle pur. FishNet
réserve toutefois le tick `0` et sa couche de prédiction devra gérer cette différence à sa frontière.

## Paramètres, pas décisions cachées

`PlayerSimulationConfig` est fourni explicitement à chaque instance. Il porte durée du tick, capsule,
vitesses, accélérations/décélérations sol-air, gravité, vitesse collée au sol, saut activé ou non,
fenêtres de saut, décroissance du knockback, limite de pitch, et plongeon avant activé ou non avec
ses impulsions, son relevé et son attente.

Il n’existe ni preset global ni `ScriptableObject` canonique pour le moment. Le banc M1 peut donc
tester plusieurs gabarits et garder le saut désactivé sans inscrire prématurément une décision de
game design dans le moteur. DEC-01 choisira plus tard les valeurs sérialisées de l’adaptateur Unity.

## Ordre d’un tick

1. Valider le payload et la continuité du tick sans modifier l’état.
2. Appliquer yaw/pitch ; le mouvement utilise immédiatement le nouveau yaw.
3. Décoder et renormaliser les axes, choisir marche/sprint, puis accélérer vers une cible plus rapide
   ou décélérer vers une cible moins rapide, y compris lors d’une baisse de stick ou de sprint.
4. Ajouter l’impulsion horizontale externe du tick.
5. Résoudre le plongeon (lancement, vol ou relevé), puis saut/buffer/coyote, puis appliquer la
   gravité.
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
`JumpHeld` (bouton tenu) vaut un appui à chaque tick : garder Espace enfoncé enchaîne les sauts dès
que le sol revient, pendant un sprint comme à l'arrêt, sans dépendre d'un front par tick.

## Plongeon avant

`DivePressed` au sol, **sprint tenu et axe avant poussé**, hors relevé et hors attente, lance le
joueur dans la direction de son regard à `DiveForwardSpeed` avec `DiveUpwardSpeed` vers le haut,
sans passer par l'accélération. Marcher ne suffit pas : le plongeon prolonge une course. Pendant le
vol, les axes et le saut sont ignorés ; la vitesse horizontale est conservée telle quelle et le
knockback continue de s'ajouter. Au premier contact avec le sol, la vitesse horizontale est annulée
— le joueur s'étale — et `DiveRecoveryTicks` ticks de relevé immobilisent le déplacement et le saut.
`DiveCooldownTicks` court depuis le lancement. Un modificateur de vitesse à `0 ‰` (KO, gel) interdit
le lancement. Désactivé, l'appui est ignoré et les trois champs restent à zéro ; un état qui les
porte est alors refusé à la restauration, comme les fenêtres de saut.

Les valeurs du banc M1 (13 m/s, 4,2 m/s, 24 et 90 ticks à 60 Hz — un premier essai à 8,5/3,2 a
été jugé trop court) sont une baseline : le plongeon relève de la même décision DEC-01 que le saut
et n'est pas plus acquis que lui. La posture (corps basculé en vol, à plat puis redressé pendant le
relevé) est un composant cosmétique, `M1DivePresentation`, sans effet sur la capsule.

## Ramper

La même touche que le plongeon, au sol et hors sprint-avant, bascule à plat ventre ; la même touche
ou le saut relève (le tick du relevé ne saute pas). À plat ventre : vitesse plafonnée à
`CrawlSpeed`, sprint et saut coupés, plongeon impossible, et la capsule de collision du tick passe
à `CrawlHeightMeters` (au moins deux rayons — PhysX n'accepte pas moins ; 0,85 m au banc pour un
rayon de 0,40), pieds au sol. Se relever ne vérifie pas encore le dégagement au-dessus de la tête :
aucune géométrie basse n'existe dans les bancs, la contrainte est notée ici plutôt qu'inventée.
Baselines du banc : 1,7 m/s, capsule 0,85 m — même décision DEC-01 que le reste.
## Chute imposée par l'hôte

`PlayerTickForces` porte, en plus de l'impulsion horizontale, un nombre de ticks de chute
(`KnockdownTicks`, borné à 120) : la glissade sur une flaque d'huile l'utilise. Appliquée sur un
tick, elle met la vitesse contrôlée à zéro et arme la même fenêtre de relevé que l'atterrissage
d'un plongeon — mêmes verrous (déplacement et saut coupés), même posture. Sans plongeon configuré,
la fenêtre n'existe pas et la chute est ignorée plutôt qu'inventée. Le serveur la propage au
propriétaire comme le knockback : mise en file, prédite, corrigée au reconcile.

## Contexte de jeu du tick

Le filtre d'intention et le modificateur de vitesse ne dépendent pas que de la commande : ils lisent
aussi la vie, le trophée, l'énergie encore payable pour le sprint et l'objet tenu en main. Ces
quatre valeurs vivent dans des champs répliqués de `SandboxPlayerGameplay`, **pas** dans
`PlayerReconcileData`. Les relire pendant un rejeu de réconciliation resimulerait le tick N avec
l'état de maintenant : le propriétaire divergeait de l'hôte à chaque KO, prise ou perte de trophée,
panne d'énergie et lance-pierre dégainé ou lâché — un élastique visible juste après l'événement.

`SandboxCommandContext` fige ces quatre valeurs, plus la vitesse de base et le ralentissement de
visée, en une photographie par tick. `SandboxPlayerGameplay.ResolveContext(tick, replaying)`
l'enregistre au premier passage du tick et la relit pendant un rejeu ; l'hôte, qui ne rejoue jamais,
reste toujours sur l'état vivant, donc l'autorité ne change pas de main. L'anneau
(`SandboxCommandContextHistory`, 128 ticks ≈ 2 s à 60 Hz) répond « inconnu » plutôt que de rendre le
contexte d'un tick voisin : au-delà de la fenêtre, retomber sur l'état courant vaut mieux que mentir
sur un tick oublié.

Un joueur sans couche sandbox utilise `SandboxCommandContext.Unrestricted` : aucun filtre, pleine
vitesse — le comportement du banc gris minimal est inchangé.

La preuve EditMode porte sur les parties pures (filtre, ralentissement de visée, anneau qui rejoue
le tick au lieu de l'état courant). Le fait que la trajectoire rejouée colle désormais à
l'autoritaire reste à mesurer sur deux machines, avec le profil dégradé : ce n'est pas couvert ici.

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
