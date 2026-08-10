# Modèle de mur par tick — contrat TICK-01

Ce lot remplace les décisions partagées fondées sur `Time.time`, `Time.deltaTime` ou l'ordre des RPC
par un modèle C# pur sous `Assets/_Project/Runtime/Maze/Simulation/`.

Depuis [l'ADR 0005](adr/0005-continuous-wall-rotation.md), un battant n'est plus une machine à deux
poses : c'est un intégrateur angulaire continu. Le reste du contrat de tick est inchangé.

## Invariants techniques fermés

- Un mur mobile possède un `wallId` stable et un angle entier en milli-degrés dans `[0, 360000)`.
  L'angle zéro est la pose initiale déclarée dans la topologie signée.
- Un appel `AdvanceTick` consomme exactement le tick suivant, y compris au wrap `uint.MaxValue → 0`.
  Un tick dupliqué, sauté ou antérieur est refusé sans muter l'état.
- Vitesse nominale, levier minimal, pas de quantification et borne d'extrapolation sont des entiers
  paramétrés. Aucun taux de tick concret n'est caché dans le code.
- Le couple net d'un tick est la somme des couples signés des sources, chaque source bornée à la
  pleine puissance et la somme bornée à la vitesse nominale, puis quantifiée. Il n'y a ni seuil à
  franchir ni inertie : la vitesse du tick est une fonction pure des intentions du tick.
- L'ordre d'arrivée des intentions, le `ClientId` et le rôle de host ne cassent jamais une égalité.
- La révision n'avance que sur un changement de segment, c'est-à-dire un changement de vitesse. Elle
  est modulo `uint`. Une révision ancienne ne peut pas écraser la plus récente ; une révision égale
  portant une vitesse différente est un conflit, pas un tie-break.
- À révision et segment identiques, un snapshot ancré plus tard avance l'horloge locale ; un ancrage
  égal est idempotent et un ancrage plus ancien ne peut pas la faire reculer.
- La pose logique d'un tick est `normalize(angle + vitesse × ticks écoulés depuis l'ancrage)`, avec
  les ticks écoulés bornés par l'extrapolation maximale. Un tick antérieur à l'ancrage rend
  l'ancrage : un replay n'invente aucun passé. L'échantillonnage visuel ne mute jamais l'état.
- Sinus et cosinus viennent d'un CORDIC entier (`FixedTrigonometry`) et non de `Math.Sin` : les
  règles de contact doivent rendre le même verdict sous Mono et sous Windows IL2CPP. Les quatre
  poses cardinales sont exactes par construction.

## Politique technique provisoire de couple

Pour rendre WALL-01 testable avant DEC-03, le banc courant applique une règle de porte simple : le
battant s'éloigne toujours de celui qui pousse, et la puissance suit le bras de levier — 400 pour
mille contre le gond, 1000 au bout, au prorata de l'abscisse du contact. Le sens vient du demi-plan
occupé par le pousseur à l'angle courant, jamais d'un axe codé en dur ni d'une pose de destination.

Ce comportement est une baseline technique réversible, pas une règle de game design acceptée. DEC-03
doit encore confirmer la vitesse, le levier minimal, les coûts et la contestation avant INT-01.

## Snapshot et late join

`WallSnapshot` capture le segment de mouvement : `wallId`, angle, vitesse angulaire, tick d'ancrage
et révision. Le codec v2 est binaire, little-endian, sans flottant : 21 octets, taille fixe. Il
rejette version inconnue, troncature, octets supplémentaires et angle hors domaine.

Un client tardif reconstruit sa machine avec `FromSnapshot`, échantillonne immédiatement le même
angle, puis extrapole jusqu'au segment suivant. Le snapshot ne suppose ni index de tableau dense ni
transform Unity.

Un segment n'est diffusé que lorsque la vitesse change, plus un battement d'une seconde. C'est ce
qui distingue ce modèle d'une synchronisation de transform : entre deux segments, chaque machine
calcule la même pose à partir du même tick.

## Frontière de l'adaptateur serveur

L'adaptateur FishNet doit :

1. regrouper les intentions validées par tick et par mur ;
2. appeler chaque machine une seule fois avec des ticks contigus ;
3. construire lui-même le contact depuis la topologie et les positions autoritaires des joueurs —
   aucun `wallId`, aucun côté et aucun levier ne vient d'un client ;
4. publier le segment et sa révision, puis des snapshots triés par `wallId` pour late join et resync ;
5. poser les colliders depuis l'échantillon logique avant de simuler les joueurs ;
6. laisser l'interpolation de rendu consommer les échantillons sans faire foi.

L'adaptateur ne doit pas donner directement `WallSnapshot` ou `WallState` au codegen FishNet : leurs
propriétés immuables ne constituent pas un DTO FishNet. WALL-01 transporte le `byte[]` produit par le
codec v2 (ou ajoute un serializer explicite prouvé AOT), puis appelle `TryFromBytes`. Il groupe aussi
les listes par `wallId` ; la machine n'alloue rien quand elle ne reçoit aucune intention correspondante.

## Décisions volontairement non prises

TICK-01 ne choisit ni 30/60 Hz, ni l'ordre PhysX final, ni énergie, coût du punch, cooldown, taille du
joueur ou règle de manche. Ces valeurs restent sous DEC-01/DEC-03. Les tests utilisent uniquement des
paramètres explicites et prouvent que des fréquences de rendu de 30, 60 ou 120 FPS ne changent pas le
segment final.
