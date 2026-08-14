# Graybox M1 — contrat exécutable

Le banc M1 n'est pas le labyrinthe 16×16. Il part de
`Assets/_Project/Maze/GrayboxTopology2x2.v1.json` (nom historique conservé, la grille elle-même est
en 6×6 depuis l'Étape 1 de `docs/M1_WALL_HANDOFF.md`) et construit au runtime une arène 6×6 avec des
primitives Unity. C'est un instrument de mesure réseau : le présenter comme « le jeu » fausse l'avis
de la personne qui le lance.

## Ce qui est déjà verrouillé

- checksum runtime obligatoire : `b21e35…e0bc4e` ;
- copie runtime immuable des dimensions, IDs, états, pivots, ouvertures et spawns ;
- vingt-cinq murs à `BoxCollider` (vingt-quatre de périmètre + le battant), dont `wallId=10` mobile
  autour de `pivotId=100`, nœud central de la grille ;
- aucun FBX et aucun `MeshCollider` ;
- battant libre sur 360° : son angle est un entier en milli-degrés dont l'origine est la pose
  initiale déclarée dans la topologie ; les deux poses déclarées ne sont plus que des repères ;
- spawns reliés et périmètre entièrement fermé : aucune arête d'enceinte n'est ouverte, donc aucun
  joueur ne peut quitter le sol de l'arène, quel que soit l'angle du battant ;
- trigonométrie entière (CORDIC en micro-degrés vers Q16) pour que côté, bras de levier et contact
  produisent le même verdict sous Mono et sous Windows IL2CPP, y compris aux tangences ;
- reset exact vers les états initiaux ;
- collisions sol/murs isolées sur `GameplayWorld` (layer 8), joueurs sur `Player` (layer 9) ;
  seuls monde↔joueur et joueur↔joueur produisent des contacts parmi ces layers, tandis que
  `InteractionQuery` et `VisualOnly` n'en produisent aucun ;
- position et rotation de l'arène supportées, échelle monde différente de 1 refusée explicitement ;
- preuve PlayMode sur deux hiérarchies identiques, les colliders/layers, les deux sens de rotation,
  un rebuild sur la même instance et trois resets complets.

La convention du graybox est directe : grille `+X,+Y` vers monde Unity `+X,+Z`. La conversion
historique retournée du FBX 16×16 ne s'applique pas à cette scène.

## Règles de la porte

Ces valeurs et ces sens sont des décisions prises avec l'équipe, pas des constantes héritées.

- **Sens déduit de la face occupée** : le battant s'éloigne toujours de celui qui pousse. Le signe
  vient du côté du plan où se trouve le pousseur, calculé à l'angle courant — donc valable sur les
  360°, sans pose ni état de destination. Repasser derrière le battant suffit à inverser le sens.
- **Aucun seuil, aucune latence** : le couple net du tick donne directement la vitesse angulaire.
  Le premier tick d'appui déplace déjà le battant, et le relâcher l'arrête au même tick — pas
  d'inertie, donc pas de dérive après la main levée.
- **Bras de levier au prorata** : 400 pour mille de puissance au contact du gond, 1000 au bout du
  battant, interpolés linéairement sur l'abscisse du contact. À 60 Hz et 400 milli-degrés par tick,
  un quart de tour prend 3,75 s au bout et 9,4 s contre le gond (battant alourdi au retour du
  premier testeur, cf. `docs/M1_WALL_HANDOFF.md`).
- **Contre-poussée par addition** : les couples signés des sources s'additionnent, chaque source
  étant bornée à la pleine puissance et la somme à la vitesse nominale. Deux leviers égaux et
  opposés figent le battant ; celui qui s'éloigne du gond reprend la main à la différence exacte.
- **Couple quantifié par paliers de 50 pour mille** : sans ce pas, le moindre pas de côté du
  pousseur changerait la vitesse d'un milli-degré, ouvrirait un segment et diffuserait un snapshot —
  le battant se synchroniserait à chaque tick, ce que le contrat réseau interdit.
- **Indicateur de levier** : au contact, le pousseur voit localement son levier en pour-cent, la
  vitesse du battant et, en cas d'égalité, la mention d'une poussée opposée. Ce retour rejoue la
  règle pure sur la position locale et ne décide rien.
- **Le battant écarte, il ne traverse pas** : l'hôte mesure le recouvrement sur le segment
  déterministe du battant et maintient une vitesse tangentielle plafonnée à 3,5 m/s, afin que la
  capsule prenne de l'avance. Celui qui pousse en est exclu : ses mains sont sur la porte par choix.
- **Le poing pousse aussi** : un rayon serveur doit réellement toucher le battant dans l'axe du
  joueur. Chaque impact verse le même couple qu'un appui pendant 40 ticks, avec un cooldown de
  48 ticks ; le sens et le levier sont figés au moment de l'impact.
- **Accompagner la porte fait partie du geste** : un pousseur immobile perd le contact dès que le
  battant s'écarte, exactement comme une vraie porte. Les profils automatisés `push-left` et
  `push-right` marchent et pivotent avec elle pour le reproduire.
- La politique conservatrice `GrayboxDuel`, qui refuse toute transition dès qu'un obstacle est dans
  l'arc, reste celle du graybox à deux poses et de ses tests de modèle ; le banc jouable ne
  l'utilise plus.

## Rendu du banc

Le rendu ne change aucune règle, mais un banc illisible ne produit pas d'avis exploitable.

- Chaque objet rendu porte un matériau URP explicite, généré dans
  `Assets/_GeneratedLocal/M1Materials/` et sérialisé dans la scène. URP 17 n'expose plus de matériau
  par défaut hors éditeur : une primitive laissée au défaut du pipeline sort **magenta** dans un
  player alors que compilation, tests et logs restent verts.
- `M1PlaytestBuild` refuse à la génération tout renderer sans matériau ou dont le shader n'est pas
  celui du pipeline, y compris sur le prefab joueur et le ciel.
- Le joueur est `Assets/_Project/Player/PersoBouleRigged.fbx`, strictement visuel : layer
  `VisualOnly`, aucun collider, hauteur vérifiée dans `[1,30 ; 1,45] m` face à la capsule simulée de
  1,40 m. La collision reste le seul `CharacterController`.
- En vue subjective, le porteur voit ses `Forearm` et ses `Fist` ; le reste du corps ne garde que
  son ombre, la caméra étant à hauteur des yeux. `F1` bascule en troisième personne. La sélection se
  fait sur les noms de l'export et ne concerne que le rendu.
- La pose bras tendus pendant la poussée est le clip `Punch` figé sur son image d'extension, en
  attendant une animation dédiée produite sous Blender.
- `M1ControlsOverlay` rappelle en permanence les commandes en bas à gauche, repliable par bouton :
  un testeur qui cherche la touche ne teste plus le réseau. Aucune lecture clavier directe.
- `M1PlayerAppearance` teinte chaque personnage d'après l'identifiant de connexion partagé par le
  serveur, donc identique sur toutes les fenêtres, et masque le corps de son porteur en vue
  première personne en gardant son ombre.
- Le décor lointain, le sol d'horizon et le socle sont sur `VisualOnly` sans collider : ils ne créent
  aucune surface jouable. L'enceinte étant close, ils servent uniquement d'horizon.
- Contrôle visuel obligatoire avant tout build montré à un humain :
  `./scripts/m1-preview-macos.sh --player`, captures dans `Logs/M1Playtest/`. Cette option capture
  aussi l'écran du build macOS via
  `M1ScreenshotProbe`, refusé hors Development : l'éditeur résout des matériaux que le player ne
  résout pas, donc seule cette capture prouve l'image livrée.

## Ce qui n'est pas encore revendiqué

- le profil à 60 Hz reste une valeur de mesure M1, pas un réglage produit accepté ;
- la vitesse nominale, le levier minimal et le pas de quantification sont des réglages de banc, pas
  des valeurs produit validées ;
- rien n'arrête le battant : aucun mur statique, aucune butée, aucune conséquence sur un joueur
  coincé entre le battant et l'enceinte ;
- aucun preset produit d'énergie ou de cooldown choisi ;
- aucune preuve visuelle Windows/IL2CPP ni essai réseau distant, dégradé ou de longue durée ; le
  dernier essai Windows IL2CPP s'est fait éjecter sur le handshake FishNet et le garde correctif
  attend encore son verdict sur le PC, voir
  [WINDOWS_IL2CPP_BLOCKER.md](WINDOWS_IL2CPP_BLOCKER.md) ;
- aucune réintégration de ce socle dans le labyrinthe 16×16 ;
- aucun verdict humain sur la taille, la lisibilité ou le feel.

Le joueur prédit/réconcilié, le mur autoritaire FishNet et le late join local sont implémentés et
testés. Les absences ci-dessus séparent les décisions humaines encore ouvertes des invariants déjà
automatisés.

## Gates locales

```bash
./scripts/unity-tests-macos.sh all
python3 tests/topology-fixtures/test-fixtures.py
./scripts/validate-repository.sh
```

La gate PlayMode exige exactement un sol et vingt-cinq colliders de mur actifs, tous des
`BoxCollider`, et vérifie qu'un angle intermédiaire du battant recouvre bien la capsule d'un joueur
planté dans sa trajectoire — c'est ce recouvrement qui déclenche la poussée autoritaire.

Les trois scénarios réseau prouvent respectivement : la rotation continue avec un joueur écarté
(`occupancy`), la contre-poussée qui fige le battant (`opposition`), et l'arrivée tardive qui
reçoit le segment arrêté avec sa révision (`latejoin`).

```bash
./scripts/m1-network-tests-macos.sh all --build
```
