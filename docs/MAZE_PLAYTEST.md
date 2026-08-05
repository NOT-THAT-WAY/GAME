# Test jouable du labyrinthe 16x16

Premier test où l'on marche réellement dans la map, seul ou à plusieurs. Il
remplace le roster nu du test de connexion sans le supprimer : les deux profils
coexistent et se lancent avec les mêmes scripts.

## Ce que le test prouve, et ce qu'il ne prouve pas

Prouve : la map Blender est importée à la bonne échelle, un personnage se déplace
avec un `CharacterController`, plusieurs joueurs se voient bouger via
FishNet/Tugboat, les 17 objets pivot sont trouvés et une demande produit une
orientation discrète partagée.

Ne prouve pas : l'autorité hôte du joueur, la prédiction/réconciliation, une
rotation ou une collision déterministe par tick, l'arrivée tardive, l'énergie,
le trésor ou le son. Le déplacement reste **côté client** et le collider d'un
pivot suit encore son animation locale par image. Ce profil est donc un smoke
test historique, pas le modèle à étendre. Toute suite sur joueur, murs ou
collisions suit [l'ADR 0004](adr/0004-authoritative-topology-and-ticks.md).

## Contenu

| Élément | Chemin | Origine |
|---|---|---|
| Labyrinthe | `Assets/_Project/Maze/Maze16x16.fbx` | `tools/maze-3d/build_maze.py` du dépôt de préproduction |
| Grille logique | `Assets/_Project/Maze/MazeGrid16x16.json` | `tools/maze-forge/maps/maze_16_16x16.json` (seed 1704) |
| Personnage | `Assets/_Project/Player/PersoBoule.fbx` | espèce « boule » du character creator |
| Déplacement | `Assets/_Project/Runtime/Player/PlayerMotor.cs` | — |
| Générateur de scène | `Assets/_Project/Editor/MazePlaytestBuild.cs` | — |

La scène `MazePlaytest.unity` et le prefab joueur ne sont **pas** versionnés : ils
sont régénérés par `MazePlaytestBuild` dans `Assets/_GeneratedLocal/`, comme la
scène du test de connexion. Personne n'a donc à revendiquer la scène.

## Échelle et orientation

Les FBX sortent de Blender avec la convention Unity (`axis_forward=-Z`,
`axis_up=Y`, 1 unité = 1 m) : aucune correction n'est appliquée à l'import.

- couloir 2,50 m, murs 3,00 m de haut et 0,25 m d'épaisseur, donc un **pas de
  grille de 2,75 m** ; emprise 44 x 44 m, map centrée sur l'origine ;
- conversion Blender `(x, y, z)` vers Unity `(-x, z, -y)` — l'export
  `axis_forward=-Z` fait pivoter la scène d'un demi-tour, **les deux** axes du
  plan changent de signe ;
- les **quatre** entrées sont côté **+Z**, le trésor côté **-Z** ;
- personnage 1,40 m, origine aux pieds, yeux à 1,05 m.

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
— `Murs_Statiques`, `Bras_Pivots`, `Pivot_*`, `Sol_Dalles`, `Sol_Sable`,
`Reperes_Gameplay` et `Props`. Seule `Vegetation` reste traversable : mousses,
lianes et buissons doivent pouvoir être longés.

Cette collision issue des triangles et des noms du FBX est une dette connue. La
cible M1 génère des primitives simples depuis la topologie JSON typée/versionnée,
avec IDs et checksum stables. Ne pas ajouter une nouvelle règle gameplay, un
spawn ou une validation réseau dépendant d'un nom de maillage ou de sa hiérarchie.

Conséquence utile au diagnostic : **les lianes et la mousse n'arrêtent jamais un
joueur**. Ce qui gêne dans un couloir, ce sont les `Props` — colonnes brisées,
caisses et jarres semées dans environ 15 % des cellules. Sauter suffit à les
passer.

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
| U | se dégager quand on est encastré dans un mur |
| Échap | libérer ou recapturer le curseur |
| Tab | masquer ou afficher le panneau réseau |
| F1 | basculer 1re / 3e personne (vue de contrôle) |

La vue de référence reste la première personne. La troisième personne est là pour
vérifier le gabarit du personnage, pas pour jouer.

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

Le smoke test réussit quand chaque participant voit les autres se déplacer et la
même orientation finale des pivots pendant plusieurs minutes. Les logs sont dans
`Logs/MazePlaytest/`.

Ne pas conclure « M1 autoritaire » à partir de ce verdict. Cette preuve exige la
scène grise à deux joueurs, les transitions par tick, le snapshot d'arrivée
tardive, `Replicate`/`Reconcile`, les checksums identiques et le profil réseau
dégradé détaillés dans l'ADR 0004.

En cas d'échec réseau, le diagnostic est le même que pour le test de connexion :
voir [REMOTE_CONNECTION_TEST.md](REMOTE_CONNECTION_TEST.md).

## Masters Blender

Les `.blend` d'origine ne sont pas dans ce dépôt : le contrat interdit les
masters éditables dans Git et le remote DVC n'est pas encore choisi. Seuls les
exports FBX consommés par Unity sont versionnés via Git LFS. L'ouverture du coffre
est désormais P0 : suivre et restaurer les deux masters avant de les partager ou
de les modifier.
