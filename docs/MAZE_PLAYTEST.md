# Test jouable du labyrinthe 16x16

Premier test où l'on marche réellement dans la map, seul ou à plusieurs. Il
remplace le roster nu du test de connexion sans le supprimer : les deux profils
coexistent et se lancent avec les mêmes scripts.

## Ce que le test prouve, et ce qu'il ne prouve pas

Prouve : la map Blender est importée à la bonne échelle, un personnage se déplace
avec un `CharacterController`, plusieurs joueurs se voient bouger via
FishNet/Tugboat, les 17 objets pivot sont trouvés et une demande produit une
orientation discrète partagée. Le profil importe aussi le clone riggé « boule »,
joue son clip Punch, fait valider portée/cône/ligne de vue par l'hôte, applique un
recul à la cible et fait marcher un bot d'entraînement piloté par l'hôte.

Ne prouve pas : l'autorité hôte du joueur, la prédiction/réconciliation, une
rotation ou une collision déterministe par tick, l'arrivée tardive, l'énergie,
les dégâts/KO, le trésor ou le son. Le déplacement et le recul d'un joueur restent
**côté client**, les cooldowns du punch utilisent encore le temps du prototype,
et le collider d'un pivot suit son animation locale par image. Ce profil est donc
un smoke test historique, pas le modèle de combat M1. Toute suite sur joueur,
murs ou collisions suit [l'ADR 0004](adr/0004-authoritative-topology-and-ticks.md).

## Contenu

| Élément | Chemin | Origine |
|---|---|---|
| Labyrinthe | `Assets/_Project/Maze/Maze16x16.fbx` | `tools/maze-3d/build_maze.py` du dépôt de préproduction |
| Grille logique | `Assets/_Project/Maze/MazeGrid16x16.json` | `tools/maze-forge/maps/maze_16_16x16.json` (seed 1704) |
| Personnage jouable + punch | `Assets/_Project/Player/PersoBouleRigged.fbx` | studio Blender `player-punch-rig-v001`, export validé sur `art/player-punch-rig` |
| Déplacement | `Assets/_Project/Runtime/Player/PlayerMotor.cs` | — |
| Punch | `Assets/_Project/Runtime/Player/PlayerPunch.cs` | intention cliente, validation hôte, animation et recul |
| Murs mobiles | `Assets/_Project/Runtime/Maze/MovableWall.cs`, `MovableWallDirector.cs` | découpés depuis `MazeGrid16x16.json`, état discret répliqué |
| Bot d'entraînement | `Assets/_Project/Runtime/Player/SimpleBot.cs` | marche et recul simulés par l'hôte |
| Générateur de scène | `Assets/_Project/Editor/MazePlaytestBuild.cs` | — |

La scène `MazePlaytest.unity`, les prefabs joueur/bot et le contrôleur Animator ne
sont **pas** versionnés : ils sont régénérés par `MazePlaytestBuild` dans
`Assets/_GeneratedLocal/`, comme la scène du test de connexion. Personne n'a donc
à revendiquer la scène.

## Échelle et orientation

Les FBX sortent de Blender avec la convention Unity (`axis_forward=-Z`,
`axis_up=Y`, 1 unité = 1 m) : aucune correction n'est appliquée à l'import.

- couloir 2,50 m, murs 3,00 m de haut et 0,25 m d'épaisseur, donc un **pas de
  grille de 2,75 m** ; emprise 44 x 44 m, map centrée sur l'origine ;
- conversion Blender `(x, y, z)` vers Unity `(-x, z, -y)` — l'export
  `axis_forward=-Z` fait pivoter la scène d'un demi-tour, **les deux** axes du
  plan changent de signe ;
- les **quatre** entrées sont côté **+Z**, le trésor côté **-Z** ;
- collider joueur 1,40 m, origine aux pieds, yeux à 1,05 m ; le clone riggé mesure
  1,34 m à l'export, dans la tolérance du prototype déclarée par le studio.

Ces cotes sont celles du tableau d'échelle physique du concept : elles ne se
règlent pas ici. Le pas de 2,75 m est la conséquence des deux premières valeurs,
pas un réglage indépendant.

Le `GridPitch` de `MazePlaytestBuild` duplique cette constante parce que la
grille JSON ne la transporte pas. S'il s'écarte de `build_maze.py`, les
apparitions tombent à côté des entrées.

Cette duplication est une dette, pas une consigne : le futur schéma porte
`cellPitchMm`, épaisseur/hauteur des murs, IDs et checksum. Son chargeur valide
les murs verticaux/horizontaux et les pivots au lieu de ne lire que dimensions et
points d'apparition.

## Collisions

Le FBX embarque de la végétation et des props denses. Pour ce smoke test,
`MazePlaytestBuild` ajoute un `MeshCollider` sur les objets qui arrêtent le joueur
— `Pivot_*`, `Sol_Dalles`, `Sol_Sable`, `Reperes_Gameplay` et `Props`. Seule
`Vegetation` reste traversable : mousses, lianes et buissons doivent pouvoir être
longés.

**Les murs statiques font exception depuis les murs mobiles** : ils ne
reçoivent plus de `MeshCollider` mais une `BoxCollider` aux cotes du design —
2,75 m de long, 0,25 m d'épaisseur, hauteur relevée sur le maillage découpé. Leur
collision vient donc de la topologie typée et non des triangles sculptés.

La collision restante, issue des triangles et des noms du FBX, est une dette
connue. La cible M1 génère des primitives simples depuis la topologie JSON
typée/versionnée, avec IDs et checksum stables. Ne pas ajouter une nouvelle règle
gameplay, un spawn ou une validation réseau dépendant d'un nom de maillage ou de
sa hiérarchie.

Conséquence utile au diagnostic : **les lianes et la mousse n'arrêtent jamais un
joueur**. Ce qui gêne dans un couloir, ce sont les `Props` — colonnes brisées,
caisses et jarres semées dans environ 15 % des cellules. Sauter suffit à les
passer.

## Murs mobiles

Deux façons de bouger un mur, une seule mécanique. **Marcher dedans** l'épaule la
première : l'effort monte, le battant cède et bascule au bout d'environ 2 s de
poussée continue. **Clic droit** : le coup emporte le quart de tour d'un seul
coup. Dans les deux cas le mur pivote **autour du bout opposé au contact**, comme
une porte lourde qu'on pousse par sa poignée. Il change donc d'axe — un mur
nord-sud devient est-ouest — et vient se poser exactement sur l'arête
perpendiculaire.

Pousser ne demande aucun bouton : avancer contre le mur suffit. Lâcher fait
retomber le battant, un peu plus vite qu'il n'était monté — un vantail de pierre
qu'on cesse d'épauler ne reste pas entrouvert. Le pourcentage d'effort s'affiche
dans le bandeau tant qu'on pousse.

Cette exactitude n'est pas un arrondi : la grille est carrée et un mur fait un
pas de long, donc un quart de tour autour d'un nœud mène toujours d'une arête de
la grille à une autre. Aucune pose intermédiaire n'existe, et le battement visible
n'est qu'une interpolation locale entre deux poses valides.

Le gond est le bout le plus éloigné du point touché, et le battant part du côté
où l'on pousse. Frapper le milieu d'un mur marche aussi : le gond est alors
simplement le bout le plus loin des deux.

Les 173 murs intérieurs de la map sont concernés ; seul le pourtour est fixe,
sans quoi le labyrinthe s'ouvrirait sur le sable. Un mur ne s'éloigne jamais de
plus de deux pas de son arête d'origine, sinon quelques coups suffiraient à le
promener à travers la map.

L'hôte décide seul. En frappant, **le client ne désigne même pas sa cible** : la
copie serveur du décor résout le mur touché, le gond et le sens. En poussant, il
ne désigne que le mur — ni le gond, ni le sens, ni la durée de son effort.
**C'est l'hôte qui mesure l'effort, à son propre rythme** : répéter l'intention
plus vite ne fait pas céder le mur plus tôt. Dans les deux cas il valide portée
mesurée sur le segment, repos du mur, éloignement de l'origine, occupation de
l'arête d'arrivée et absence de joueur dessous.

Une nuance entre les deux : la poussée exige d'aller franchement vers quelque
part, donc longer un mur ne le fait pas céder. Un coup de poing, lui, passe même
donné de biais.

**Règle de collision retenue : un mur ne se referme jamais sur quelqu'un.** Si un
joueur ou un bot occupe l'arête d'arrivée, la poussée est refusée — pas de KO,
pas de déplacement forcé. L'ADR 0004 laisse cette conséquence ouverte ; c'est le
choix explicite du prototype, à trancher pour de bon en M1. Un battant peut en
revanche frôler quelqu'un pendant sa course : `U` sert à se dégager si le mur
vous prend au passage.

### Découpe depuis la grille

Le FBX sort tous les murs statiques dans **un seul maillage fusionné**
(`Murs_Statiques`) : aucun d'eux ne pouvait bouger seul. `SplitStaticWalls` le
redécoupe en un objet par arête de `MazeGrid16x16.json`, chaque triangle
rejoignant l'arête dont son barycentre est le plus proche. Identifiant, case
d'origine et collider viennent tous de la grille typée ; le
maillage sculpté n'est plus qu'un habillage, conformément à l'ADR 0004. La
génération avertit si une arête pleine déclarée par le JSON ne reçoit aucun
triangle, ce qui signalerait un FBX désaccordé de la grille.

Les maillages découpés sont enregistrés dans `Assets/_GeneratedLocal/MazeWallMeshes.asset`,
comme le reste de la scène générée : rien de tout ça n'est versionné.

### Ce qui reste à faire

Ce qui circule est **un entier par mur** — son arête et son nombre de quarts de
tour empaquetés ensemble —, jamais un transform image par image, et les 106
arêtes interdites (pourtour et bras de pivot) voyagent dans le prefab du
director, donc à l'identique sur les trois machines.

Une réserve à connaître : l'effort d'une poussée en cours est lui aussi répliqué,
par paliers de 5 %, pour que tout le monde voie le battant céder pendant qu'on
s'appuie dessus. C'est un scalaire par mur poussé, pas un transform, mais c'est
un cran de plus que l'état purement discret des pivots. La migration le remplace
par une transition à `startTick`/`durationTicks`. Mais la transition
visible et le collider avancent avec `Time.deltaTime` sur chaque machine, comme
les pivots : deux joueurs peuvent rencontrer un mur à des positions
intermédiaires différentes. Le cooldown serveur se mesure encore sur `Time.time`
au lieu du tick FishNet. Même migration à faire que pour les pivots :
`startTick`, `durationTicks` et `revision`.

## Murs pivotants

Clic gauche maintenu en avançant contre un bras de pivot : le mur part d'un quart
de tour dans le sens où l'on appuie. Le sens vient du signe du couple `r x F`
autour de la verticale, donc pousser près du totem ne tourne rien et pousser dans
l'axe du bras non plus — il faut un bras de levier.

Le prototype fait circuler **un octet d'orientation par pivot**, jamais le
transform image par image. L'hôte vérifie seulement l'index, un cooldown et une
distance tolérante, puis chaque machine rattrape l'angle avec `Time.deltaTime` à
partir de la réception. Cela prouve la convergence vers quatre orientations,
mais pas l'autorité complète : le collider tourne avec le visuel local, donc deux
joueurs peuvent rencontrer des murs à des poses intermédiaires différentes.

La migration remplace cet octet seul par une transition contenant ID stable,
états source/cible, `startTick`, `durationTicks` et `revision`. La pose logique et
la collision sont échantillonnées au tick commun ; l'interpolation locale reste
strictement visuelle.

Le smoke test suppose encore que **chaque pivot soit un objet distinct dans le
FBX**, totem et bras réunis, origine sur son nœud. `tools/maze-3d/build_maze.py` le
garantit depuis qu'il ne fusionne plus les bras. Un export qui contiendrait encore
`Bras_Pivots` fait échouer la génération de scène avec le message qui explique
quoi ré-exporter — sans quoi on obtiendrait une map où faire tourner un pivot
ferait tourner les dix-sept. Ce garde d'import peut rester, mais les IDs et règles
runtime doivent venir de la topologie, pas de ces noms.

Les objets `Pivot_*` sont exclus des drapeaux statiques : un maillage marqué
statique est figé dans le batching et ne tournerait jamais à l'écran. La génération échoue si aucun de
ces noms n'existe, pour que le renommage d'un objet dans le générateur ne
produise pas silencieusement une map qu'on traverse.

## Lancer

Les joueurs se répartissent sur les quatre entrées, dans la cellule du seuil,
tournés vers le couloir le plus dégagé. Toutes les cellules d'entrée ne sont pas
ouvertes vers l'intérieur et le générateur sème des gravats jusque dans les
couloirs : la position et l'orientation sont donc mesurées sur la géométrie, pas
déduites de la grille. `MazePlaytestBuild` refuse de produire la scène si une
apparition n'a pas de sol, chevauche un collider ou n'a pas un pas de dégagement.
Le bot apparaît deux mètres devant la première entrée validée et avance dans le
couloir dès que le serveur démarre ; il tourne devant un obstacle et recule
brièvement lorsqu'un punch le touche. L'hôte peut donc tester le clic droit
immédiatement.

### Une seule machine

```bash
./scripts/first-test-macos.sh host --profile maze --name "Sean"
./scripts/first-test-macos.sh client --profile maze --address 127.0.0.1 --name "Test" --skip-build
```

### Réseaux différents (le cas de l'équipe)

L'hôte :

```bash
./scripts/remote-test-macos.sh host --profile maze --name "Zak"
```

Les autres, avec l'IPv4 Tailscale `100.x.y.z` communiquée par l'hôte :

```bash
./scripts/remote-test-macos.sh client --profile maze --address "IP_TAILSCALE_HOTE" --name "Nils"
```

```powershell
.\scripts\remote-test-windows.ps1 Client -Profile Maze -Address "IP_TAILSCALE_HOTE" -Name "Sean"
```

Le profil par défaut reste `connection` : les commandes existantes du jalon M0 ne
changent pas de comportement.

## Commandes en jeu

| Touche | Effet |
|---|---|
| ZQSD / WASD / flèches | se déplacer |
| Souris | regarder |
| Maj | sprint |
| Espace | sauter — contournement provisoire des gravats, statut gameplay à décider |
| Clic gauche maintenu + avancer | pousser un mur pivotant d'un quart de tour |
| Clic droit | coup de poing : joueur ou bot devant soi, sinon le mur touché pivote d'un quart de tour |
| Avancer contre un mur | le pousser à l'épaule : il cède au bout d'environ 2 s, et retombe si on lâche |
| U | se dégager quand on est encastré dans un mur |
| Échap | libérer ou recapturer le curseur |
| Tab | masquer ou afficher le panneau réseau |
| F1 | basculer 1re / 3e personne (vue de contrôle) |

La vue de référence reste la première personne. La troisième personne est là pour
vérifier le gabarit du personnage, pas pour jouer.

En première personne, le porteur voit ses propres avant-bras et ses poings ; le
corps et les pieds ne gardent que leur ombre, la caméra étant placée à hauteur des
yeux, à l'intérieur du volume du corps. Sans cette exception, un coup de poing ne
donnait aucun retour à l'écran tant qu'il ne touchait personne. La sélection se
fait sur le nom des meshes de l'export (`Forearm`, `Fist`) et ne concerne que le
rendu : aucune règle gameplay n'en dépend.

`U` replace le joueur sur le centre d'une cellule voisine libre : une case
d'abord, puis deux, puis trois. À chaque anneau, la cellule retenue est la plus
proche qui ait du sol sous elle et de quoi tenir debout. Si les trois anneaux
sont bouchés, le joueur repart de son entrée, seul point dont
`MazePlaytestBuild` garantit le sol et le dégagement.

Cette touche ne repousse **pas** le joueur hors du mur : `ComputePenetration` ne
résout rien contre un `MeshCollider` non convexe, et les murs du labyrinthe en
sont. La validation d'une cellule passe donc par un tir vers le sol et un
`CheckCapsule`, qui fonctionnent contre une géométrie concave. Pour la même
raison, le dégagement vise la grille au lieu de mémoriser la dernière position
« sûre » : un test de chevauchement qui ne détecte rien enregistrerait comme sûre
la position où l'on est encastré.

`RespawnGridPitch` duplique le pas de grille pour la même raison que le
`GridPitch` de `MazePlaytestBuild` : s'il s'en écarte, le dégagement vise entre
deux couloirs.

## Vérifier sans lancer de partie

```bash
/Applications/Unity/Hub/Editor/$(sed -n 's/^UNITY_VERSION=//p' config/toolchain.env)/Unity.app/Contents/MacOS/Unity \
  -batchmode -quit -projectPath "$(pwd)" \
  -executeMethod NotThatWay.Game.Editor.MazePlaytestBuild.RenderPreview \
  -logFile "$(pwd)/Logs/MazePlaytest/preview.log"
```

Deux images arrivent dans `Logs/MazePlaytest/` : une vue aérienne et une vue à
hauteur d'yeux devant une entrée. C'est le contrôle d'échelle et de matériaux à
joindre à une PR qui touche la map.

## Verdict

Le smoke test réussit quand chaque participant voit les autres se déplacer, voit
le même punch, reçoit le recul après un coup validé par l'hôte, peut faire reculer
le bot et voit la même orientation finale des pivots pendant plusieurs minutes.
Les logs sont dans `Logs/MazePlaytest/`.

Ne pas conclure « M1 autoritaire » à partir de ce verdict. Cette preuve exige la
scène grise à deux joueurs, les transitions par tick, le snapshot d'arrivée
tardive, `Replicate`/`Reconcile`, les checksums identiques et le profil réseau
dégradé détaillés dans l'ADR 0004.

En cas d'échec réseau, le diagnostic est le même que pour le test de connexion :
voir [REMOTE_CONNECTION_TEST.md](REMOTE_CONNECTION_TEST.md).

## Masters Blender

Les `.blend` d'origine ne sont pas dans Git : le contrat interdit les masters
éditables dans le dépôt et le remote DVC n'est pas encore choisi. Le master du
clone riggé reste dans `tools/blender-agent-studio/local_work/player-punch-rig-v001/`,
ignoré par Git ; ses preuves textuelles sont conservées sur `art/player-punch-rig`.
Seuls les exports FBX consommés par Unity sont versionnés via Git LFS. L'ouverture
du coffre est désormais P0 avant de partager ou modifier un master.
