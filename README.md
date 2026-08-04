# GAME — Labyrinthe PvP

Prototype multijoueur compétitif en vue subjective pour **2 à 12 joueurs**. Le premier objectif est de prouver qu'un duel autour d'un pivot de labyrinthe est amusant, lisible et réactif en réseau avant de produire le contenu final.

## Où en est le projet

Le dépôt est au jalon **M0 — fondations**.

- [x] dépôt privé, projet Unity URP et conventions de travail préparés ;
- [x] versions Unity/FishNet figées et scène de connexion à trois générable ;
- [x] scripts d'installation, diagnostic, assets et test Mac/Windows ;
- [x] séparation Git / Git LFS / coffre DVC externe / caches locaux ;
- [ ] URL du coffre d'assets choisie et restauration testée ;
- [ ] premier import Unity Mac et `packages-lock.json` mergé ;
- [ ] ouverture propre sur le second Mac et build Windows IL2CPP ;
- [ ] Zak, Sean et Nils visibles dans la même session LAN ;
- [ ] compatibilité Wwise 2025.1.4 validée sur Mac et Windows.

La prochaine action utile est un **clone propre sur les trois machines**, puis le test de connexion. Le gameplay vient juste après.

## Installation rapide

Ne clonez pas le projet dans iCloud, OneDrive, Dropbox ou un dossier réseau.

### macOS

```bash
git clone https://github.com/NOT-THAT-WAY/GAME.git
cd GAME
./scripts/setup-macos.sh --all
```

Le script installe Git/LFS, DVC, GitHub CLI et Unity Hub, prépare Smart Merge et ouvre l'installation exacte de Unity. Une fois Unity installé, relancer simplement :

```bash
./scripts/setup-macos.sh
```

### Windows — PowerShell

Sur une machine vierge, installer Git puis rouvrir PowerShell :

```powershell
winget install --id Git.Git --exact
```

Ensuite :

```powershell
git clone https://github.com/NOT-THAT-WAY/GAME.git
Set-Location GAME
powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1 -All
```

Après l'installation de Unity dans Hub, relancer `setup-windows.ps1` sans option.

Les scripts sont idempotents. L'éditeur Unity reste une étape interactive parce que Hub doit confirmer l'architecture et les modules de build.

## Coffre d'assets hors GitHub

Les masters lourds ne sont pas envoyés dans GitHub. Une fois l'URL privée communiquée par l'administrateur du stockage :

```bash
./scripts/assets-macos.sh configure "<URL_DVC>"
./scripts/assets-macos.sh pull
```

```powershell
.\scripts\assets-windows.ps1 -Action Configure -RemoteUrl "<URL_DVC>"
.\scripts\assets-windows.ps1 -Action Pull
```

GitHub garde seulement les pointeurs DVC, les exports nécessaires au jeu et les métadonnées. Les credentials restent propres à chaque membre et ne sont jamais commités.

| Donnée | Emplacement |
|---|---|
| code, scènes, réglages, documentation | GitHub privé |
| PNG/FBX/WAV nécessaires au build | Git LFS, avec budget |
| Blender/PSD/sessions DAW/sources brutes | remote DVC privé |
| secrets et preuves nominatives | gestionnaire dédié |
| `Library`, caches, logs et builds | local, ignoré |

## Premier test à trois

Après le premier import et le merge du lockfile :

```bash
# Mac hôte
./scripts/first-test-macos.sh host --name Nils

# Second Mac
./scripts/first-test-macos.sh client --address <IP_HOTE> --name Sean
```

```powershell
# Windows
.\scripts\first-test-windows.ps1 Client -Address <IP_HOTE> -Name Zak
```

Le succès est simple : les trois noms apparaissent dans les trois fenêtres. Voir [le protocole complet](docs/FIRST_CONNECTION_TEST.md).

## Stack figée

| Couche | Choix actuel | État |
|---|---|---|
| Moteur | Unity `6000.3.20f1` LTS | dans le projet |
| Rendu | URP `17.3.0`, Forward+ | dans le projet |
| Input | Unity Input System `1.20.0` | dans le projet |
| Réseau local | FishNet `4.7.2` + Tugboat | dans le projet |
| Tests multi-instance | Multiplayer Play Mode `2.0.2` | dans le projet |
| Masters lourds | DVC 3.x + stockage externe privé | scripts prêts, remote à choisir |
| Assets de build | Git LFS + UnityYAMLMerge | configuré |
| Audio | Wwise `2025.1.4` | après gate Mac/Windows |
| Steam | Steamworks.NET `2025.164.1` + FishySteamworks `4.1.1` | après validation LAN |

FishyFacepunch n'est pas repris car son dépôt est archivé. Tugboat reste le profil quotidien ; Steam viendra en profil additionnel.

## Équipe flexible

Tout le monde touche au gameplay, au contenu et aux tests. Les profils indiquent le meilleur point de départ, pas une propriété permanente.

| Profil | Affinités | Prochain point d'appui naturel |
|---|---|---|
| Zak | technique, réseau, logique, juridique | test FishNet/Windows, règles réseau, licences |
| Sean | création, visuel, narration, illustration, design, Unity | blockout, lisibilité du pivot, pipeline art |
| Nils | technique + artistique, son, vision globale, IA | premier import, DVC, Wwise, cohérence d'intégration |

Le membre qui possède le PC prend la validation Windows. Les rôles pilote/binôme/testeur tournent à chaque lot afin qu'au moins deux personnes comprennent chaque système.

## Documentation

- [Roadmap et priorités](docs/ROADMAP.md)
- [Installation Mac/Windows](docs/SETUP.md)
- [Premier test de connexion](docs/FIRST_CONNECTION_TEST.md)
- [Travail à trois](docs/WORKFLOW.md)
- [Assets hors GitHub](docs/ASSETS.md)
- [Gestion des données](docs/DATA_MANAGEMENT.md)
- [Stack et versions](docs/STACK.md)
- [Règles de contribution](CONTRIBUTING.md)
- [Conception du jeu](https://github.com/NOT-THAT-WAY/brainstorm)

## Règle de priorité

**Environnements identiques → données fiables → connexion LAN → pivot jouable → réseau dégradé → audio/visuel → playtests.** Si le duel ne fonctionne pas en cubes gris, l'habillage ne le sauvera pas.
