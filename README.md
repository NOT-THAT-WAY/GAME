# GAME — Labyrinthe PvP

Prototype multijoueur compétitif en vue subjective pour **2 à 12 joueurs**. Le premier objectif est de prouver qu'un duel autour d'un pivot de labyrinthe est amusant, lisible et réactif en réseau avant de produire le contenu final.

La cible joueur initiale est **Windows x86_64 IL2CPP**. Le développement se fait sur deux Mac Apple Silicon et un PC Windows ; le build Mac reste un outil de test interne. FishNet/Tugboat fournit aujourd'hui un listen-server de prototype, Tailscale relie uniquement les postes de l'équipe, et Steam/serveur dédié attendent leur gate.

## Où en est le projet

Le dépôt est au jalon **M0 — fondations**.

- [x] dépôt privé, projet Unity URP et conventions de travail préparés ;
- [x] versions Unity/FishNet figées et scène de connexion à trois générable ;
- [x] scripts d'installation, diagnostic, assets et tests local/distant Mac/Windows ;
- [x] séparation Git / Git LFS / coffre DVC externe / caches locaux ;
- [ ] coffre d'assets à choisir au premier master lourd — ne bloque pas le setup ;
- [x] premier import Unity Mac et `packages-lock.json` mergé ;
- [ ] ouverture propre sur le second Mac et build Windows IL2CPP ;
- [ ] Zak, Sean et Nils visibles dans la même session depuis leurs trois réseaux ;
- [ ] gate Wwise à ouvrir après le premier test distant — ne bloque pas le setup.

La machine pilote peut déjà construire et lancer le test. La prochaine action utile est un **clone propre sur le second Mac et sur Windows**, puis le test distant à trois. Le gameplay vient juste après.

Pour exécuter l'installation dans le bon ordre — d'abord sur le Mac pilote, ensuite sur l'autre Mac et Windows — suivre [ONBOARDING.md](docs/ONBOARDING.md).

Avec Claude Code, lancer `claude` depuis la racine puis écrire `initialise l'environnement`. Le skill projet `setup-game` détecte Mac ou Windows, installe aussi le client Tailscale de test distant, exécute le bon setup et rend le verdict du doctor. La connexion Tailscale reste un écran interactif individuel ; aucune clé n'est partagée avec Claude.

Pour intégrer Zak et Sean maintenant : Nils génère dans la console Tailscale deux liens **Invite external users** à usage unique avec le rôle Member, puis les envoie en privé. Le tailnet actuel est personnel et distinct de l'organisation GitHub. Après acceptation, chacun clone le repo et demande à Claude `initialise l'environnement pour jouer à distance`. Le coffre DVC peut attendre : aucun master n'est encore référencé.

`main` refuse les pushes directs sur chaque clone initialisé grâce au hook partagé, et Claude a la même interdiction. Les branches suivent `feat/...`, `fix/...`, `art/...`, `audio/...`, `data/...`, `docs/...` ou `chore/...` ; le script `publish-task` pousse ensuite la branche et ouvre sa PR. Le dépôt privé reste utilisable gratuitement par toute l'équipe sans protection serveur absolue.

## Installation rapide

Ne clonez pas le projet dans iCloud, OneDrive, Dropbox ou un dossier réseau.

### macOS

Après installation de Homebrew :

```bash
brew install git git-lfs gh
gh auth login --web
gh auth setup-git
gh repo clone NOT-THAT-WAY/GAME
cd GAME
./scripts/setup-macos.sh --all --remote-play
```

Le script installe Git/LFS, GitHub CLI, Unity Hub, Visual Studio Code, son extension Unity/C# et Tailscale, prépare Smart Merge et ouvre les installations interactives. DVC reste hors du setup initial. Une fois Unity et la connexion Tailscale terminés, relancer :

```bash
./scripts/setup-macos.sh --remote-play
```

### Windows — PowerShell

Sur une machine vierge, installer les outils nécessaires au clone puis rouvrir PowerShell :

```powershell
winget install --id Git.Git --exact
winget install --id GitHub.GitLFS --exact
winget install --id GitHub.cli --exact
```

Ensuite :

```powershell
gh auth login --web
gh auth setup-git
gh repo clone NOT-THAT-WAY/GAME
Set-Location GAME
powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1 -All -RemotePlay
```

Après l'installation de Unity et la connexion Tailscale, relancer `setup-windows.ps1 -RemotePlay`.

Les scripts sont idempotents. L'éditeur Unity reste une étape interactive parce que Hub doit confirmer l'architecture et les modules de build.

## Coffre d'assets hors GitHub

État actuel : environ 164 Kio dans `GAME`, zéro objet LFS et zéro lot DVC. Le plan GitHub Free de l'organisation inclut 10 Gio de stockage LFS et 10 Gio de téléchargement mensuel ; le budget interne du prototype est limité à 2 Gio d'exports actifs. Cela suffit pour installer l'équipe et commencer. Le coffre des masters est reporté au premier gros fichier source ; voir [la stratégie d'assets](docs/ASSETS.md).

Les masters lourds ne sont pas envoyés dans GitHub. Une fois l'URL privée communiquée par l'administrateur du stockage :

```bash
./scripts/setup-macos.sh --install-tools --with-assets
./scripts/assets-macos.sh configure "REMPLACER_PAR_URL_DVC"
./scripts/assets-macos.sh pull
```

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1 -InstallTools -WithAssets
.\scripts\assets-windows.ps1 -Action Configure -RemoteUrl "REMPLACER_PAR_URL_DVC"
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

Sur le même réseau local, après le premier import et le merge du lockfile :

```bash
# Mac hôte
./scripts/first-test-macos.sh host --name "TON_NOM"

# Second Mac
./scripts/first-test-macos.sh client --address "192.168.1.42" --name "NOM_MAC_2"
```

```powershell
# Windows
.\scripts\first-test-windows.ps1 Client -Address "192.168.1.42" -Name "NOM_WINDOWS"
```

Le succès est simple : les trois noms apparaissent dans les trois fenêtres. Voir [le protocole complet](docs/FIRST_CONNECTION_TEST.md).

Si chacun est chez soi, ne pas utiliser l'IP `192.168.x.x`. Le Mac mini de Zak peut héberger et jouer :

```bash
# Hôte distant
./scripts/remote-test-macos.sh host --name "Zak"

# Client Mac avec l'IP Tailscale 100.x.y.z affichée par l'hôte
./scripts/remote-test-macos.sh client --address "100.x.y.z" --name "Nils"
```

```powershell
# Client Windows
.\scripts\remote-test-windows.ps1 Client -Address "100.x.y.z" -Name "Sean"
```

Voir [le protocole distant](docs/REMOTE_CONNECTION_TEST.md). Aucun serveur dédié ni port de box n'est nécessaire ; la machine hôte doit simplement garder le jeu ouvert.

## Stack figée

| Couche | Choix actuel | État |
|---|---|---|
| Moteur | Unity `6000.3.20f1` LTS | dans le projet |
| Rendu | URP `17.3.0`, Forward+ | dans le projet |
| Input | Unity Input System `1.20.0` | dans le projet |
| Réseau local | FishNet `4.7.2` + Tugboat | dans le projet |
| Tests multi-instance | Multiplayer Play Mode `2.0.2` | dans le projet |
| Réseau de développement distant | Tailscale, hors du build | setup Mac/Windows |
| Masters lourds | DVC 3.x + stockage externe privé | scripts prêts, remote à choisir |
| Assets de build | Git LFS + UnityYAMLMerge | configuré |
| Audio | Wwise `2025.1.4` | après gate Mac/Windows |
| Steam | Steamworks.NET `2025.164.1` + FishySteamworks `4.1.1` | après validation distante |

FishyFacepunch n'est pas repris car son dépôt est archivé. Tugboat reste le profil quotidien ; Steam viendra en profil additionnel.

## Équipe flexible

Tout le monde touche au gameplay, au contenu et aux tests. Les profils indiquent le meilleur point de départ, pas une propriété permanente.

| Profil | Affinités | Prochain point d'appui naturel |
|---|---|---|
| Zak | technique, réseau, logique, juridique | test FishNet/Windows, règles réseau, licences |
| Sean | création, visuel, narration, illustration, design, Unity | blockout, lisibilité du pivot, pipeline art |
| Nils | technique + artistique, son, vision globale, IA | DVC, Wwise, cohérence d'intégration |

Le membre qui possède le PC prend la validation Windows. Les rôles pilote/binôme/testeur tournent à chaque lot afin qu'au moins deux personnes comprennent chaque système.

## Documentation

- [Contrat du jeu, permissions et interdictions](docs/PROJECT_RULES.md)
- [CI et builds Mac/Windows](docs/CI_BUILDS.md)
- [Roadmap et priorités](docs/ROADMAP.md)
- [Ordre d'installation des trois postes](docs/ONBOARDING.md)
- [Installation Mac/Windows](docs/SETUP.md)
- [Premier test de connexion](docs/FIRST_CONNECTION_TEST.md)
- [Test depuis des réseaux différents](docs/REMOTE_CONNECTION_TEST.md)
- [Travail à trois](docs/WORKFLOW.md)
- [Assets hors GitHub](docs/ASSETS.md)
- [Gestion des données](docs/DATA_MANAGEMENT.md)
- [Stack et versions](docs/STACK.md)
- [Règles de contribution](CONTRIBUTING.md)
- [Conception du jeu](https://github.com/NOT-THAT-WAY/brainstorm)

## Règle de priorité

**Environnements identiques → données fiables → connexion distante → pivot jouable → réseau dégradé → audio/visuel → playtests.** Si le duel ne fonctionne pas en cubes gris, l'habillage ne le sauvera pas.
