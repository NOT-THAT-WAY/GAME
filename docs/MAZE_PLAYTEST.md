# Test jouable du labyrinthe 16x16

Premier test où l'on marche réellement dans la map, seul ou à plusieurs. Il
remplace le roster nu du test de connexion sans le supprimer : les deux profils
coexistent et se lancent avec les mêmes scripts.

## Ce que le test prouve, et ce qu'il ne prouve pas

Prouve : la map Blender est importée à la bonne échelle, un personnage se déplace
avec un `CharacterController`, et plusieurs joueurs se voient bouger via
FishNet/Tugboat depuis des réseaux différents.

Ne prouve pas : la rotation des pivots, l'autorité hôte, l'énergie, le trésor, le
son. L'autorité de déplacement est **côté client** pour ce test ; le passage à
l'autorité hôte est le sprint B de la [roadmap](ROADMAP.md) et se fera dans sa
propre PR.

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

## Collisions

Le FBX embarque de la végétation et des props denses. Poser un MeshCollider sur
tout ferait cuire des millions de triangles pour rien : l'import ne génère aucun
collider, et `MazePlaytestBuild` en pose un sur les seuls objets qui arrêtent le
joueur — `Murs_Statiques`, `Bras_Pivots`, `Pivot_*`, `Sol_Dalles`, `Sol_Sable`,
`Reperes_Gameplay` et `Props`. Seule `Vegetation` reste traversable : mousses,
lierres et buissons doivent pouvoir être longés. La génération échoue si aucun de
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
| Échap | libérer ou recapturer le curseur |
| Tab | masquer ou afficher le panneau réseau |
| F1 | basculer 1re / 3e personne (vue de contrôle) |

La vue de référence reste la première personne. La troisième personne est là pour
vérifier le gabarit du personnage, pas pour jouer.

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

Le test réussit quand chaque participant voit les autres se déplacer dans les
couloirs pendant plusieurs minutes, sans téléportation ni traversée de mur. Les
logs sont dans `Logs/MazePlaytest/`.

En cas d'échec réseau, le diagnostic est le même que pour le test de connexion :
voir [REMOTE_CONNECTION_TEST.md](REMOTE_CONNECTION_TEST.md).

## Masters Blender

Les `.blend` d'origine ne sont pas dans ce dépôt : le contrat de dépôt interdit
les masters éditables dans Git et le remote DVC n'est pas encore choisi (priorité
P2 de la roadmap). Seuls les exports FBX consommés par Unity sont versionnés, via
Git LFS. Ouvrir le coffre DVC avant de partager ou de modifier les masters.
