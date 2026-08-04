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

Le lockfile Unity est mergé depuis la PR #10 et le test hôte/client local Mac est vert. Il reste à valider l'ouverture sur le second Mac, le build Windows, la connexion LAN à trois et, indépendamment, le fournisseur du coffre DVC.

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

Ce script installe ou vérifie : Git, Git LFS, GitHub CLI, DVC, Unity Hub, Visual Studio Code, l'extension Unity/C# et Tailscale. Il configure aussi Smart Merge, les hooks communs et le mode `pull --ff-only`.

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

Le remote DVC, Wwise et Steam peuvent apparaître en avertissement. C'est normal à ce stade. Une ligne `[FAIL]` sur Git, LFS, DVC ou Unity doit être corrigée avant d'ouvrir le projet.

### 1.3 Premier import Unity — terminé

La PR #10 a enregistré le lockfile, les réglages migrés et la collection FishNet. Deux builds Mac successifs ainsi qu'un hôte et un client locaux ont été validés. Le Mac pilote doit désormais rester propre sur `main` ; les étapes actives reprennent à la section 3 pour donner accès aux autres membres.

## 2. Initialiser le coffre d'assets quand il est prêt

Cette étape peut se faire avant ou après le premier test LAN.

L'administrateur du stockage prépare :

- un bucket privé S3-compatible ou un autre remote supporté par DVC ;
- chiffrement et versioning objet ;
- une deuxième sauvegarde ;
- trois comptes individuels avec MFA et sans suppression permanente au quotidien ;
- une URL commune et une méthode locale d'authentification.

Ne jamais partager les clés dans Git ou Discord. Configurer les credentials avec le profil/outil du fournisseur, puis sur le Mac pilote :

```bash
git switch main
git pull --ff-only
git switch -c chore/asset-vault-smoke
./scripts/assets-macos.sh configure "REMPLACER_PAR_URL_DVC"
./scripts/assets-macos.sh smoke-init
```

Pour un service S3-compatible avec endpoint :

```bash
./scripts/assets-macos.sh configure "s3://NOM_DU_BUCKET/game" \
  --endpoint "https://ENDPOINT_DU_FOURNISSEUR" \
  --profile "game-assets"
./scripts/assets-macos.sh smoke-init
```

Le script crée une preuve minuscule, l'envoie dans le remote et laisse seulement son pointeur dans Git. Committer les fichiers indiqués par `git status`, pousser la branche et merger la PR.

Le test n'est réussi que lorsqu'une autre machine peut exécuter `smoke-verify` depuis un clone propre.

## 3. Donner accès aux deux autres membres

Dans GitHub : `Settings > Collaborators and teams > Add people`, ajouter leurs comptes avec le droit d'écriture. Chacun accepte son invitation et active MFA.

Chaque membre configure son identité Git avec son propre nom/email :

```bash
git config --global user.name "PRENOM"
git config --global user.email "EMAIL_GITHUB"
```

Les handles GitHub sont nécessaires pour les assigner ensuite aux tickets M0.

Un seul membre (Nils par défaut) crée aussi le tailnet Tailscale et envoie deux invitations privées. Le fait que le Mac mini de Zak héberge une session ne lui impose pas d'être administrateur du tailnet. Chaque personne rejoint avec son propre compte ; aucune clé d'authentification n'est créée pour les postes humains ni copiée dans le repo.

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

Si le coffre DVC est prêt :

```bash
./scripts/assets-macos.sh configure "REMPLACER_PAR_URL_DVC"
./scripts/assets-macos.sh smoke-verify
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

Le script installe Git LFS, GitHub CLI, DVC, Unity Hub, Visual Studio 2022 et Tailscale. Dans Unity Hub, installer `6000.3.20f1` avec **Windows Build Support (IL2CPP)**, puis accepter l'invitation Tailscale avec le compte individuel. Relancer :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1 -RemotePlay
powershell -ExecutionPolicy Bypass -File .\scripts\doctor-windows.ps1 -RemotePlay
```

Si le coffre est prêt :

```powershell
.\scripts\assets-windows.ps1 -Action Configure -RemoteUrl "REMPLACER_PAR_URL_DVC"
.\scripts\assets-windows.ps1 -Action SmokeVerify
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
