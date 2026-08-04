# Initialiser GAME dans le bon ordre

Cette procédure est la référence pour le premier démarrage. On prépare **d'abord le Mac pilote**, on fige le résultat dans Git, puis seulement l'autre Mac et Windows ouvrent Unity.

## Ce qui est déjà prêt

- le repo privé `NOT-THAT-WAY/GAME` et la branche `main` ;
- Unity `6000.3.20f1`, URP et FishNet déclarés ;
- les scripts Mac/Windows ;
- Git LFS pour les binaires de build ;
- DVC pour les masters hors GitHub ;
- une scène de test FishNet générée au build ;
- la CI et les gardes-fous contre caches, secrets, gros fichiers et `.meta` manquants.

Le lockfile Unity est mergé depuis la PR #10, le test hôte/client local Mac est vert et le Mac pilote passe le doctor distant. Il reste à valider l'ouverture sur le second Mac, le build Windows et la connexion distante à trois. Le fournisseur du coffre DVC attend le premier master lourd.

## Initialisation assistée par Claude Code

Si la commande `claude` n'existe pas encore, installer Claude Code une seule fois :

```bash
# macOS
brew install --cask claude-code
```

```powershell
# Windows PowerShell
winget install Anthropic.ClaudeCode
```

Chaque membre lance ensuite `claude`, se connecte avec son propre compte et accepte la confiance du workspace après avoir lu `CLAUDE.md` et les skills du dépôt.

Après le clone, un membre peut lancer Claude depuis la racine :

```text
claude
> initialise l'environnement
```

Le fichier `CLAUDE.md` charge les règles du projet et le skill `setup-game` exécute le script correspondant à Mac ou Windows. `/setup-game` permet aussi de le déclencher explicitement. Les confirmations GitHub, Homebrew/winget, Unity Hub et Tailscale restent interactives ; Claude reprend ensuite le diagnostic. Aucun setup standard n'installe Wwise Authoring.

## 1. Ton Mac devient la machine pilote

### 1.1 Prérequis manuels

Prévoir un disque local avec au moins 40 Go libres et le mot de passe administrateur. Ne pas utiliser un dossier iCloud/Dropbox/OneDrive.

Si Git n'est pas disponible :

```bash
xcode-select --install
```

Installer ensuite Homebrew depuis [brew.sh](https://brew.sh). Cette étape reste manuelle car Apple et Homebrew demandent confirmation.

Le repo existe déjà sur cette machine dans `/Users/unrecorded/GAME`. Pour un nouveau clone, utiliser :

```bash
brew install git git-lfs gh
gh auth login --web
gh auth setup-git
gh repo clone NOT-THAT-WAY/GAME
cd GAME
```

Sur le Mac pilote actuel, vérifier simplement `gh auth status`.

### 1.2 Installer les outils communs

Depuis la racine du repo :

```bash
./scripts/setup-macos.sh --all --remote-play
```

Ce script installe ou vérifie : Git, Git LFS, GitHub CLI, Unity Hub, Visual Studio Code, l'extension Unity/C# et Tailscale. Il configure aussi Smart Merge, les hooks communs et le mode `pull --ff-only`. DVC est volontairement reporté.

Unity Hub s'ouvre sur `6000.3.20f1`. Choisir :

- architecture **Apple Silicon** ;
- support de build macOS inclus ;
- Windows Build Support (Mono) seulement si ce Mac doit faire des builds de fumée Windows ;
- aucune installation Wwise ou Steam pour l'instant.

Quand Hub a terminé, relancer :

```bash
./scripts/setup-macos.sh --remote-play
./scripts/doctor-macos.sh --remote-play
```

Le remote DVC, Wwise et Steam peuvent apparaître en avertissement. C'est normal à ce stade. Toute ligne `[FAIL]` doit être corrigée avant de déclarer la machine prête ; DVC ne produit un échec que lorsqu'un master est réellement référencé.

### 1.3 Premier import Unity — terminé

La PR #10 a enregistré le lockfile, les réglages migrés et la collection FishNet. Deux builds Mac successifs ainsi qu'un hôte et un client locaux ont été validés. Le Mac pilote doit désormais rester propre sur `main` ; les étapes actives reprennent à la section 3 pour donner accès aux autres membres.

## 2. Initialiser le coffre d'assets quand il est prêt

Cette étape attendra l'installation des amis : aucun pointeur DVC n'existe encore et son absence ne bloque ni le clone, ni Unity, ni le test réseau. GitHub LFS fournit 10 Gio de stockage et 10 Gio de téléchargement mensuel au plan actuel ; le projet en utilise actuellement zéro.

Ne rien configurer ici pour l'instant. Au premier master Blender/PSD/DAW lourd, choisir le fournisseur et suivre [ASSETS.md](ASSETS.md). D'ici là, les exports nécessaires au build passent par Git LFS et les sources de travail restent locales avec une sauvegarde personnelle.

## 3. Donner accès aux deux autres membres

Les trois comptes sont déjà membres actifs de `NOT-THAT-WAY` et ont accès au repo. Le droit nécessaire au quotidien est **Member + Write** ; le rôle Owner n'est pas requis pour coder, pousser une branche ou ouvrir une PR. Zak et Sean livrent leur branche et son résultat de test, sans devoir relire ni merger les PR ; Nils gère seul l'intégration. Après l'onboarding, garder idéalement un ou deux Owners maximum et retirer aux autres la création/suppression globale de dépôts.

Chaque membre configure son identité Git avec son propre nom/email :

```bash
git config --global user.name "PRENOM"
git config --global user.email "EMAIL_GITHUB"
```

Les handles GitHub sont nécessaires pour les assigner ensuite aux tickets M0.

Le tailnet actuel est le tailnet GitHub **personnel** de Nils, pas celui de l'organisation `NOT-THAT-WAY`. C'est suffisant pour le test immédiat, mais les membres GitHub ne le rejoignent pas automatiquement. Nils ouvre la page **Users** de la console Tailscale, choisit **Invite external users**, génère deux liens à usage unique avec le rôle **Member** et les transmet séparément à Zak et Sean. Un lien d'invitation est un secret temporaire : ne jamais le committer ou le coller dans Claude.

Chaque ami ouvre son lien, choisit **Sign up with GitHub**, sélectionne le tailnet invité et connecte sa propre machine. Le fait que le Mac mini de Zak héberge une session ne lui impose pas d'être administrateur du tailnet.

Le plan Personal accepte actuellement six utilisateurs, mais Tailscale le réserve à un usage non commercial. Pour un projet commercial, utiliser le plan Standard ou remplacer ce profil par le transport Steam ; à trois, le tarif Standard actuel est de 24 USD/mois. Ne pas créer un tailnet GitHub d'organisation par erreur : ce serait un réseau séparé et il ne récupérerait pas les machines déjà affichées ici.

## 4. Installer le deuxième Mac

Seulement après le merge du lockfile :

```bash
xcode-select --install  # uniquement si Git manque ; attendre la fin
brew install git git-lfs gh
gh auth login --web
gh auth setup-git
gh repo clone NOT-THAT-WAY/GAME
cd GAME
./scripts/setup-macos.sh --all --remote-play
```

Installer dans Hub la même version Apple Silicon, puis :

```bash
./scripts/setup-macos.sh --remote-play
./scripts/doctor-macos.sh --remote-play
```

Ouvrir puis fermer Unity sans rien modifier. `git status --short` doit rester vide. Si Unity veut mettre à jour le projet ou produit un gros diff, arrêter et comparer la version exacte avant de committer quoi que ce soit.

## 5. Installer Windows

Dans PowerShell sur le PC :

```powershell
winget install --id Git.Git --exact
winget install --id GitHub.GitLFS --exact
winget install --id GitHub.cli --exact
```

Fermer et rouvrir PowerShell, puis :

```powershell
gh auth login --web
gh auth setup-git
gh repo clone NOT-THAT-WAY/GAME
Set-Location GAME
powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1 -All -RemotePlay
```

Le script installe Git LFS, GitHub CLI, Unity Hub, Visual Studio 2022 avec les workloads Unity/C++, et Tailscale. Dans Unity Hub, installer `6000.3.20f1` avec **Windows Build Support (IL2CPP)**, puis accepter l'invitation Tailscale avec le compte individuel. DVC attendra le premier master lourd. Relancer :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1 -RemotePlay
powershell -ExecutionPolicy Bypass -File .\scripts\doctor-windows.ps1 -RemotePlay
```

Ouvrir/fermer Unity et vérifier que Git reste propre. Produire ensuite le build de preuve :

```powershell
.\scripts\first-test-windows.ps1 Manual -BuildOnly
```

## 6. Faire le premier test distant à trois

Zak peut héberger et jouer sur son Mac mini :

```bash
./scripts/remote-test-macos.sh host --name "Zak"
```

Le script affiche l'IP Tailscale `100.x.y.z`. Sur un client Mac :

```bash
./scripts/remote-test-macos.sh client --address "100.x.y.z" --name "Nils"
```

Sur Windows :

```powershell
.\scripts\remote-test-windows.ps1 Client -Address "100.x.y.z" -Name "Sean"
```

Le test est vert quand les trois noms apparaissent dans les trois fenêtres. Si les machines partagent exceptionnellement le même Wi-Fi, utiliser plutôt [FIRST_CONNECTION_TEST.md](FIRST_CONNECTION_TEST.md). Ensuite seulement : blockout du pivot, gate Wwise, puis Steam.

## Quel script utiliser

| Besoin | macOS | Windows |
|---|---|---|
| installer/configurer la machine | `setup-macos.sh` | `setup-windows.ps1` |
| vérifier l'environnement | `doctor-macos.sh` | `doctor-windows.ps1` |
| configurer/synchroniser les masters | `assets-macos.sh` | `assets-windows.ps1` |
| test sur le même réseau | `first-test-macos.sh` | `first-test-windows.ps1` |
| test depuis plusieurs lieux | `remote-test-macos.sh` | `remote-test-windows.ps1` |
| vérifier avant commit | `validate-repository.sh` + hook | hook Git via Git Bash |

Tous les scripts de setup peuvent être relancés. En cas d'échec, ne pas mettre Unity ou un package à jour au hasard : conserver la sortie du `doctor`, le commit courant et l'OS, puis traiter l'écart dans un ticket.

Une nouvelle machine est considérée intégrée lorsque son `doctor` affiche `0 erreur`, que `git status --short` reste vide après ouverture/fermeture de Unity et qu'elle peut rejoindre le test réseau. Le coffre DVC et Wwise restent optionnels tant que leurs jalons ne sont pas ouverts.
