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

Il reste deux initialisations réelles : laisser Unity créer le lockfile sur le Mac pilote, puis choisir le fournisseur du coffre DVC. Ces deux actions sont indépendantes ; le test réseau peut avancer sans coffre.

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

Le fichier `CLAUDE.md` charge les règles du projet et le skill `setup-game` exécute le script correspondant à Mac ou Windows. `/setup-game` permet aussi de le déclencher explicitement. Les confirmations GitHub, Homebrew/winget et Unity Hub restent interactives ; Claude reprend ensuite le diagnostic. Aucun setup standard n'installe Wwise Authoring.

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
./scripts/setup-macos.sh --all
```

Ce script installe ou vérifie : Git, Git LFS, GitHub CLI, DVC, Unity Hub, Visual Studio Code et l'extension Unity/C#. Il configure aussi Smart Merge, les hooks communs et le mode `pull --ff-only`.

Unity Hub s'ouvre sur `6000.3.20f1`. Choisir :

- architecture **Apple Silicon** ;
- support de build macOS inclus ;
- Windows Build Support (Mono) seulement si ce Mac doit faire des builds de fumée Windows ;
- aucune installation Wwise ou Steam pour l'instant.

Quand Hub a terminé, relancer :

```bash
./scripts/setup-macos.sh
./scripts/doctor-macos.sh
```

Le remote DVC, Wwise et Steam peuvent apparaître en avertissement. C'est normal à ce stade. Une ligne `[FAIL]` sur Git, LFS, DVC ou Unity doit être corrigée avant d'ouvrir le projet.

### 1.3 Faire le premier import Unity

Créer la branche **avant** d'ouvrir Unity :

```bash
git switch -c chore/first-unity-import
```

Dans Unity Hub, ajouter/ouvrir le dossier `GAME` avec la version exacte. Puis :

1. dans `Unity > Settings/Preferences > External Tools`, choisir Visual Studio Code ;
2. attendre la fin de l'import et de la résolution des packages ;
3. vérifier qu'il n'y a aucune erreur rouge dans la Console ;
4. lancer `GAME > Validate Project Setup` ;
5. ouvrir `Assets/Scenes/SampleScene.unity` ;
6. entrer puis sortir du Play Mode ;
7. fermer complètement Unity.

Contrôler le résultat :

```bash
./scripts/doctor-macos.sh
git status --short
```

Le changement principal attendu est `Packages/packages-lock.json`. Examiner toute autre migration au lieu de faire un `git add .` aveugle.

```bash
git add Packages/packages-lock.json
# Ajouter individuellement une éventuelle migration Unity vérifiée.
git diff --cached
git commit -m "chore: lock first Unity import"
git push -u origin HEAD
gh pr create --fill
```

Merger la PR après contrôle de la CI. Les deux autres machines ne doivent pas ouvrir Unity avant ce merge.

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

## 4. Installer le deuxième Mac

Seulement après le merge du lockfile :

```bash
xcode-select --install  # uniquement si Git manque ; attendre la fin
brew install git git-lfs gh
gh auth login --web
gh auth setup-git
gh repo clone NOT-THAT-WAY/GAME
cd GAME
./scripts/setup-macos.sh --all
```

Installer dans Hub la même version Apple Silicon, puis :

```bash
./scripts/setup-macos.sh
./scripts/doctor-macos.sh
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
powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1 -All
```

Le script installe Git LFS, GitHub CLI, DVC, Unity Hub et Visual Studio 2022. Dans Unity Hub, installer `6000.3.20f1` avec **Windows Build Support (IL2CPP)**. Puis relancer :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\doctor-windows.ps1
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

## 6. Faire le premier test réseau à trois

Sur le Mac pilote :

```bash
./scripts/first-test-macos.sh host --name "TON_NOM"
```

Le script affiche une IP probable, par exemple `192.168.1.42`. Sur le second Mac :

```bash
./scripts/first-test-macos.sh client --address "192.168.1.42" --name "NOM_MAC_2"
```

Sur Windows :

```powershell
.\scripts\first-test-windows.ps1 Client -Address "192.168.1.42" -Name "NOM_WINDOWS"
```

Le test est vert quand les trois noms apparaissent dans les trois fenêtres. Ensuite seulement : blockout du pivot, gate Wwise, puis Steam.

## Quel script utiliser

| Besoin | macOS | Windows |
|---|---|---|
| installer/configurer la machine | `setup-macos.sh` | `setup-windows.ps1` |
| vérifier l'environnement | `doctor-macos.sh` | `doctor-windows.ps1` |
| configurer/synchroniser les masters | `assets-macos.sh` | `assets-windows.ps1` |
| construire/lancer le test réseau | `first-test-macos.sh` | `first-test-windows.ps1` |
| vérifier avant commit | `validate-repository.sh` + hook | hook Git via Git Bash |

Tous les scripts de setup peuvent être relancés. En cas d'échec, ne pas mettre Unity ou un package à jour au hasard : conserver la sortie du `doctor`, le commit courant et l'OS, puis traiter l'écart dans un ticket.

Une nouvelle machine est considérée intégrée lorsque son `doctor` affiche `0 erreur`, que `git status --short` reste vide après ouverture/fermeture de Unity et qu'elle peut rejoindre le test réseau. Le coffre DVC et Wwise restent optionnels tant que leurs jalons ne sont pas ouverts.
