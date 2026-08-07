# GAME — Labyrinthe PvP

Prototype multijoueur compétitif en vue subjective pour **2 à 12 joueurs**. Le premier objectif est de prouver qu'un duel autour d'un pivot de labyrinthe est amusant, lisible et réactif en réseau avant de produire le contenu final.

La cible joueur initiale est **Windows x86_64 IL2CPP**. Le développement se fait sur deux Mac Apple Silicon et un PC Windows ; le build Mac reste un outil de test interne. FishNet/Tugboat fournit aujourd'hui un listen-server de prototype, Tailscale relie uniquement les postes de l'équipe, et Steam/serveur dédié attendent leur gate.

## Où en est le projet

Le dépôt est au jalon **M0 — fondations**.

- [x] dépôt privé, projet Unity URP et conventions de travail préparés ;
- [x] versions Unity/FishNet figées et scène de connexion à trois générable ;
- [x] scripts d'installation, diagnostic, assets et tests local/distant Mac/Windows ;
- [x] séparation Git / Git LFS / masters DVC / caches locaux documentée ;
- [ ] remote DVC à choisir maintenant : deux exports FBX existent déjà sans leurs masters partagés ;
- [x] premier import Unity Mac et `packages-lock.json` mergé ;
- [ ] ouverture propre sur le second Mac et build Windows IL2CPP ;
- [ ] Zak, Sean et Nils visibles dans la même session depuis leurs trois réseaux ;
- [ ] gate Wwise à ouvrir après la première preuve distante autoritaire — ne bloque pas le setup.

La machine pilote peut construire le labyrinthe et lancer un smoke test où le joueur et les pivots sont visibles en réseau. Ce code est volontairement étiqueté prototype : déplacement client-authoritative, transition des colliders par image et collisions issues du FBX ne valident pas M1. Les prochaines actions sont le **clone propre sur le second Mac et Windows**, le test distant à trois, l'ouverture du coffre DVC, puis la migration décrite dans [l'ADR 0004](docs/adr/0004-authoritative-topology-and-ticks.md).

Pour exécuter l'installation dans le bon ordre — d'abord sur le Mac pilote, ensuite sur l'autre Mac et Windows — suivre [ONBOARDING.md](docs/ONBOARDING.md).

Le studio Blender compact est intégré dans `tools/blender-agent-studio/`. Il est versionné dans ce
repo sans son historique Git et sans les 7,82 Go d'assets sources : `catalog/assets.json` en conserve
l'inventaire vérifiable. Claude découvre automatiquement
`.claude/skills/blender-production-studio/` et Codex
`.agents/skills/blender-production-studio/` depuis la racine de `GAME`.

Avec Claude Code, lancer `claude` depuis la racine puis écrire `initialise l'environnement`. Le skill projet `setup-game` détecte Mac ou Windows, installe aussi le client Tailscale de test distant, exécute le bon setup et rend le verdict du doctor. La connexion Tailscale reste un écran interactif individuel ; aucune clé n'est partagée avec Claude.

Pour intégrer Zak et Sean : Nils envoie en privé des invitations Tailscale individuelles, jamais une clé d'authentification. Le tailnet actuel est personnel et distinct de l'organisation GitHub ; comme le jeu vise un usage commercial, son propriétaire doit confirmer ou adopter un plan compatible avant le prochain playtest structuré ([conditions des offres Tailscale](https://tailscale.com/pricing)). Après acceptation, chacun clone le repo et demande à Claude `initialise l'environnement pour jouer à distance`. L'absence de remote DVC ne bloque pas ce setup, mais bloque désormais toute modification ou transmission des masters des FBX actuels.

`main` refuse les pushes directs sur chaque clone initialisé grâce au hook partagé, et Claude a la même interdiction. Les branches suivent `feat/...`, `fix/...`, `art/...`, `audio/...`, `data/...`, `docs/...` ou `chore/...` ; le script `publish-task` pousse ensuite la branche et ouvre sa PR. Zak et Sean n'ont pas à administrer, relire ou merger les PR : ils livrent une branche testée et Nils gère seul l'intégration. Le dépôt privé reste utilisable gratuitement par toute l'équipe sans protection serveur absolue.

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

État mesuré le 5 août 2026 : deux objets LFS — le labyrinthe d'environ 38 Mo et le personnage d'environ 101 Ko — et zéro pointeur DVC. Le budget interne du prototype reste limité à 2 Gio d'exports actifs. Les clones et builds restent possibles, mais les masters correspondants ne sont pas récupérables depuis ce dépôt : le coffre DVC est maintenant prioritaire avant leur prochaine modification ; voir [la stratégie d'assets](docs/ASSETS.md).

Les masters lourds ne sont pas envoyés dans GitHub. Une fois l'URL privée communiquée par l'administrateur du stockage :

```bash
./scripts/setup-macos.sh --install-tools --with-assets
./scripts/assets-macos.sh configure "s3://ntw-assets/game" \
  --endpoint "https://<ID_DE_COMPTE>.r2.cloudflarestorage.com" \
  --region "auto" \
  --profile "game-assets"
./scripts/assets-macos.sh pull
```

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1 -InstallTools -WithAssets
.\scripts\assets-windows.ps1 -Action Configure -RemoteUrl "s3://ntw-assets/game" `
  -EndpointUrl "https://<ID_DE_COMPTE>.r2.cloudflarestorage.com" `
  -Region "auto" `
  -Profile "game-assets"
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
| Masters lourds | DVC 3.x + stockage externe privé | gate P0, remote à choisir |
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
- [Studio Blender intégré et skills](docs/BLENDER_STUDIO.md)
- [Premier test de connexion](docs/FIRST_CONNECTION_TEST.md)
- [Test depuis des réseaux différents](docs/REMOTE_CONNECTION_TEST.md)
- [Test jouable du labyrinthe](docs/MAZE_PLAYTEST.md)
- [Travail à trois](docs/WORKFLOW.md)
- [Assets hors GitHub](docs/ASSETS.md)
- [Gestion des données](docs/DATA_MANAGEMENT.md)
- [Stack et versions](docs/STACK.md)
- [Architecture autoritaire : topologie, ticks, murs et joueur](docs/adr/0004-authoritative-topology-and-ticks.md)
- [Audit du document maître du 5 août 2026](docs/audits/2026-08-05-document-maitre.md)
- [Règles de contribution](CONTRIBUTING.md)
- [Conception du jeu](https://github.com/NOT-THAT-WAY/brainstorm)

## Règle de priorité

**Environnements identiques → masters récupérables → connexion distante → topologie/collisions déterministes → murs et joueur par tick → réseau dégradé → audio/visuel → playtests.** Si le duel ne fonctionne pas dans la scène grise à un pivot, l'habillage 16x16 ne le sauvera pas.
