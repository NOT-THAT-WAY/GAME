# ADR 0005 — Rotation continue d'un battant sous autorité de l'hôte

**Statut : accepté — 2026-08-10**

Complète l'ADR 0004, qu'il amende sur un seul point : la forme du segment répliqué d'un mur mobile.
Tout le reste de l'ADR 0004 — autorité de l'hôte, ordre du tick, topologie typée, `ConnectionTarget`,
séparation domaine/adaptateurs — reste inchangé.

## Contexte

L'ADR 0004 décrit un mur mobile comme un couple de poses déclarées et une transition
`wallId, fromState, toState, startTick, durationTicks, revision`. Le banc M1 l'a implémenté ainsi :
seuil d'effort à charger, puis bascule de durée fixe entre deux arêtes de la grille.

L'essai humain a rejeté ce modèle sur trois points concrets :

- la porte n'existe qu'entre deux poses, donc elle « se bloque dans une pose » dès qu'on veut
  continuer au-delà ;
- un seuil à charger crée une latence entre l'appui et le premier mouvement, que le joueur lit comme
  une touche morte ;
- une bascule de durée fixe ignore l'endroit où l'on pousse, alors qu'un battant se pousse
  évidemment plus facilement par son bord que par son gond.

La demande produit est explicite : rotation libre dans les deux sens sur 360°, départ au premier
appui, vitesse lente mais sans temps mort, contre-poussée possible, et puissance au prorata de la
position le long du battant — 30 % au gond, 100 % au bout.

## Décision

### L'état partagé devient un segment de mouvement angulaire

Un mur mobile réplique désormais :

```text
wallId, angleMilliDegrees, angularVelocityMilliDegreesPerTick, anchorTick, revision
```

La pose d'un tick reste une fonction pure du tick :

```text
angle(t) = normalize(angleMilliDegrees + angularVelocity × min(t − anchorTick, maxExtrapolation))
```

L'interdiction de l'ADR 0004 est conservée dans sa lettre comme dans son intention : **aucun
transform n'est diffusé, et jamais par image**. Un segment n'est émis que lorsque la vitesse change,
plus un battement périodique d'une seconde. La borne d'extrapolation empêche un segment perdu de
faire tourner le battant indéfiniment chez un observateur.

L'angle zéro est la pose initiale déclarée dans la topologie signée. Les poses déclarées restent
donc l'origine du référentiel — la donnée reste la seule source du repère — mais elles ne sont plus
des états atteignables ni des destinations à valider.

### Le couple net du tick donne directement la vitesse

Pas de seuil, pas d'inertie. À chaque tick l'hôte somme les couples signés des sources valides,
borne chaque source à la pleine puissance, borne la somme à la vitesse nominale, quantifie, et
applique le résultat comme vitesse angulaire du tick.

Conséquences voulues :

- le premier tick d'appui déplace déjà le battant, et le relâcher l'arrête au même tick ;
- deux sources opposées se retranchent exactement : la contre-poussée n'est pas une règle
  supplémentaire, c'est l'addition ;
- le sens vient du demi-plan occupé par le pousseur à l'angle courant, donc changer de face suffit à
  inverser la rotation, à n'importe quel angle du tour.

### La puissance est un bras de levier

Le couple d'une source vaut `min + (1000 − min) × abscisse / longueur` pour mille, où l'abscisse est
la projection entière du contact sur le battant. Le banc M1 fixe `min = 300`.

### Le couple est quantifié

La vitesse est calculée sur un couple net arrondi à 50 pour mille. Sans ce pas, le moindre pas de
côté du pousseur changerait la vitesse d'un milli-degré, ouvrirait un segment et déclencherait une
diffusion : le battant se synchroniserait de fait à chaque tick, ce que l'ADR 0004 interdit. La
mesure est directe — sur un même scénario, la quantification fait passer un push de 131 segments en
161 ticks à 10 segments.

### La trigonométrie du contact est entière

Un battant libre n'a plus de pose alignée sur la grille, mais côté, bras de levier et contact
restent des règles partagées. Elles utilisent un CORDIC entier en micro-degrés vers Q16 plutôt que
`Math.Sin`, dont l'égalité au dernier bit n'est pas garantie entre Mono et IL2CPP. Les quatre poses
cardinales sont exactes par construction, pour que le battant au repos coïncide au millimètre avec
les arêtes de la topologie.

### Le battant écarte, il ne bloque pas

Rien n'arrête la rotation : un joueur balayé reçoit une vitesse tangentielle bornée par le chemin
autoritaire, et le pousseur en est exclu — ses mains sont sur la porte par choix. Aucune butée
statique n'est implémentée : dans le graybox 2×2, les quatre directions du gond sont libres.

## Conséquences

- `WallStateMachine`, `WallTransition` et la gate de transition disparaissent du banc jouable. La
  politique `GrayboxDuel` et l'API discrète de `TopologyArena` restent pour le graybox à deux poses
  et ses tests.
- Le codec de snapshot passe en version de format 2 et le schéma réseau en version 3 : un client
  d'une version antérieure est refusé, pas mal interprété.
- Les scénarios réseau changent de vocabulaire : rotation cumulée, quarts de tour franchis,
  inversions, ticks de couple opposé et poussées subies remplacent transitions complétées et
  refusées.
- Un pousseur immobile perd le contact au bout de quelques dizaines de degrés. C'est voulu :
  accompagner la porte fait partie du geste. Les profils automatisés marchent et pivotent avec elle.

## Ce qui reste ouvert

- la vitesse nominale (900 milli-degrés par tick), le levier minimal (300 pour mille) et le pas de
  quantification (50 pour mille) sont des réglages de banc, pas des valeurs produit validées ;
- la conséquence d'un joueur coincé entre le battant et l'enceinte n'est toujours pas décidée ;
- aucune butée, aucun verrou, aucun coût d'énergie ;
- aucune preuve Windows IL2CPP ni essai réseau dégradé sur ce modèle.
