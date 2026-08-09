# Modèle de mur par tick — contrat TICK-01

Ce lot remplace les décisions partagées fondées sur `Time.time`, `Time.deltaTime` ou l'ordre des RPC
par un modèle C# pur sous `Assets/_Project/Runtime/Maze/Simulation/`.

## Invariants techniques fermés

- Un mur graybox possède un `wallId` stable et deux `stateId` non nécessairement denses.
- Un appel `AdvanceTick` consomme exactement le tick suivant, y compris au wrap `uint.MaxValue → 0`.
- Les durées restent inférieures à `2^31` ticks ; l'écart exactement égal à `2^31`, ambigu dans un
  compteur modulo, est rejeté.
- Seuil, limite par source, decay, effort conservé après refus et durée de transition sont tous des
  entiers paramétrés. Aucun taux de tick concret n'est caché dans le code.
- La gate autoritaire est appelée uniquement au seuil. Un refus porte un code stable, n'altère pas la
  pose et applique la rétention d'effort configurée. Une acceptation crée une transition datée.
- La gate est synchrone et non réentrante : pendant son exécution, la machine refuse un second
  `AdvanceTick` ainsi que l'application d'un snapshot. Une exception laisse tick et état inchangés.
- Si le mur est en transition à l'entrée du tick, les nouvelles intentions sont observées mais non
  accumulées. Cela vaut aussi au tick exact de complétion : il ferme uniquement l'ancienne transition,
  et une intention ne peut repartir en sens inverse qu'au tick suivant.
- La pose logique est un échantillon entier `from/to/elapsed/duration/progressQ16`. L'échantillonnage
  visuel ne mute jamais l'état.
- Chaque mutation autoritaire incrémente une révision modulo `uint`. Une révision ancienne ne peut pas
  écraser la plus récente ; une révision égale mais différente est un conflit, pas un tie-break.
- À état et révision identiques, un snapshot capturé plus tard avance l'horloge locale ; un tick égal
  est idempotent et un tick plus ancien ne peut pas la faire reculer.

## Politique technique provisoire d'effort

Pour rendre WALL-01 testable avant DEC-03, le banc courant applique la recommandation A du paquet de
décision : toutes les intentions d'un tick sont sommées par source, bornées par source, puis agrégées
avant mutation. Le signe positif vise la pose positive, le négatif la pose négative, et un changement
de signe ramène d'abord l'effort vers zéro. L'ordre RPC, le `ClientId` et le rôle de host ne cassent
jamais une égalité.

Ce comportement est une baseline technique réversible, pas une règle de game design acceptée. DEC-03
doit encore confirmer l'accumulation, le decay, les coûts et la contestation avant INT-01 ou un test
humain de feel.

## Snapshot et late join

`WallSnapshot` capture la pose stable ou la transition active, l'effort, le tick et la révision. Le
codec v1 est binaire, little-endian, sans flottant : 22 octets pour un état stable, 46 pour une
transition. Il rejette version inconnue, troncature, booléen invalide et octets supplémentaires.

Un client tardif reconstruit sa machine avec `FromSnapshot`, échantillonne immédiatement la même pose
Q16, puis reprend au tick suivant. Le snapshot ne suppose ni index de tableau dense ni transform Unity.

## Frontière de l'adaptateur serveur

Le futur adaptateur FishNet doit :

1. regrouper les intentions validées par tick et par mur ;
2. appeler chaque machine une seule fois avec des ticks contigus ;
3. construire lui-même la gate depuis la topologie, les états de tous les murs et les obstacles
   joueurs autoritaires ;
4. publier la transition/révision, puis des snapshots triés par `wallId` pour late join et resync ;
5. poser les colliders depuis l'échantillon logique avant de simuler les joueurs ;
6. laisser l'interpolation de rendu consommer les échantillons sans faire foi.

L'adaptateur ne doit pas donner directement `WallSnapshot`, `WallState` ou `WallTransition` au
codegen FishNet : leurs propriétés immuables ne constituent pas un DTO FishNet. WALL-01 transporte le
`byte[]` produit par le codec v1 (ou ajoute un serializer explicite prouvé AOT), puis appelle
`TryFromBytes`. Il groupe aussi les listes par `wallId`; la machine n'alloue aucun dictionnaire quand
elle ne reçoit aucune intention correspondante.

## Décisions volontairement non prises

TICK-01 ne choisit ni 30/60 Hz, ni l'ordre PhysX final, ni énergie, coût du punch, cooldown, taille du
joueur ou règle de manche. Ces valeurs restent sous DEC-01/DEC-03. Les tests utilisent uniquement des
paramètres explicites et prouvent que des fréquences de rendu de 30, 60 ou 120 FPS ne changent pas le
snapshot final.
