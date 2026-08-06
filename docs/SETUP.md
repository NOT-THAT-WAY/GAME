# Installation de l'équipe — macOS et Windows

L'objectif est que les trois machines ouvrent le même projet avec les mêmes versions, sans partager les caches. Le premier import est verrouillé sur `main` depuis la PR #10 ; les deux autres machines peuvent maintenant ouvrir Unity après leur setup.

## Ordre recommandé

| Étape | Qui | Résultat attendu |
|---|---|---|
| 0. Accès | les trois | accès GitHub, MFA, clone sur disque local |
| 1. Outils | les trois | Git/LFS, Unity Hub, IDE, Tailscale |
| 2. Coffre externe | plus tard | DVC seulement au premier master lourd |
| 3. Premier import | terminé sur Mac pilote | packages résolus et lockfile commité |
| 4. Validation croisée | Windows + second Mac | aucun changement parasite, build Windows IL2CPP |
| 5. Connexion | les trois | roster FishNet partagé depuis leurs réseaux via Tailscale |
| 6. Wwise | Nils puis builds Mac/Windows | Authoring centralisé, runtime identique pour tous |
| 7. Steam | après LAN | transport ajouté sans casser Tugboat |

## Outils installés maintenant

Commun aux trois postes :

- Git et Git LFS ;
- Unity Hub et Unity `6000.3.20f1` ;
- un éditeur C# avec son intégration Unity ;
- Tailscale pour le réseau privé de développement lorsque chacun travaille depuis chez soi ;
- accès individuel au GitHub privé.

Sur les Mac Apple Silicon, le script installe Visual Studio Code et l'extension Unity de Microsoft, puis ouvre l'éditeur Unity Apple Silicon attendu. Un seul Mac a besoin du module Windows Build Support (Mono) si l'équipe veut produire un build de fumée non officiel depuis macOS.

Sur Windows, ajouter Windows Build Support (IL2CPP) et Visual Studio 2022 avec « Game development with Unity » **et** les outils C++/Windows SDK de « Desktop development with C++ ». Le PC reste la source de vérité des builds Windows natifs.

Wwise et Steam ne sont pas nécessaires au premier test. Tailscale ne remplace pas Steam dans le jeu final : il relie seulement les machines de développement distantes.

## macOS

```bash
brew install git git-lfs gh
gh auth login --web
gh auth setup-git
gh repo clone NOT-THAT-WAY/GAME
cd GAME
./scripts/setup-macos.sh --all --remote-play
```

Le coffre de l'équipe est un bucket Cloudflare R2. Nils communique l'endpoint par le canal privé ; il n'est pas écrit dans le dépôt :

```bash
./scripts/setup-macos.sh --all \
  --remote-play \
  --with-assets \
  --asset-remote "s3://ntw-assets/game" \
  --asset-endpoint "https://<ID_DE_COMPTE>.r2.cloudflarestorage.com" \
  --asset-region "auto" \
  --asset-profile "game-assets"
```

`--asset-region` n'est pas optionnel sur R2 : un endpoint S3-compatible ne déduit pas sa région, et la valeur attendue par Cloudflare est littéralement `auto`. Sans elle, l'échec survient à la signature de la requête, pas à la connexion, et le message d'erreur ne désigne pas la cause.

Le script :

- installe ou vérifie Git, LFS, GitHub CLI, Unity Hub et Visual Studio Code via Homebrew ;
- installe l'extension Unity pour VS Code, qui apporte les dépendances C# ;
- installe et ouvre Tailscale sans créer ni stocker de clé d'authentification ;
- récupère les objets Git LFS ; DVC n'est installé et synchronisé qu'avec `--with-assets` ;
- configure UnityYAMLMerge ;
- ouvre Unity Hub sur la version exacte ;
- lance le diagnostic.

Après avoir terminé l'installation de Unity dans Hub :

```bash
./scripts/setup-macos.sh --remote-play
./scripts/doctor-macos.sh --remote-play
```

## Windows

Installer les outils du clone si nécessaire, puis rouvrir PowerShell :

```powershell
winget install --id Git.Git --exact
winget install --id GitHub.GitLFS --exact
winget install --id GitHub.cli --exact
```

Après avoir accepté l'invitation GitHub :

```powershell
gh auth login --web
gh auth setup-git
gh repo clone NOT-THAT-WAY/GAME
Set-Location GAME
powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1 -All -RemotePlay
```

Avec le remote :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1 `
  -All `
  -RemotePlay `
  -WithAssets `
  -AssetRemote "s3://ntw-assets/game" `
  -AssetEndpoint "https://<ID_DE_COMPTE>.r2.cloudflarestorage.com" `
  -AssetRegion "auto" `
  -AssetProfile "game-assets"
```

Le script installe via `winget` Git/LFS, GitHub CLI, Unity Hub, Visual Studio et Tailscale, puis prépare LFS et Smart Merge. DVC n'est ajouté qu'avec `-WithAssets`. Visual Studio, Unity et l'extension VPN peuvent demander une élévation ou une confirmation interactive.

Après l'installation Unity :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1 -RemotePlay
powershell -ExecutionPolicy Bypass -File .\scripts\doctor-windows.ps1 -RemotePlay
```

## Credentials du coffre

Chaque membre reçoit son propre accès avec le minimum de droits. Les clés ne doivent pas être passées comme arguments des scripts, car l'historique du terminal peut les conserver.

- utiliser le profil local du fournisseur ou ses variables d'environnement ;
- l'URL, l'endpoint et la région sont stockés dans `.dvc/config.local` ;
- ce fichier est ignoré par Git, et `scripts/validate-repository.sh` refuse un commit qui le suivrait ;
- ne jamais copier le dossier `.dvc/cache` entre membres comme méthode principale de partage.

`GAME` est un dépôt **public**. C'est la raison pour laquelle la définition du remote reste locale : même l'endpoint, qui n'est pas un secret, désignerait publiquement la cible du coffre et resterait dans l'historique Git après tout correctif. Les identifiants R2 déposés comme secrets d'organisation servent aux workflows GitHub Actions ; ils ne configurent aucun poste de développement.

Pour les clés R2 elles-mêmes, préférer un profil AWS local plutôt que `dvc remote modify --local … access_key_id`, afin qu'aucune clé n'apparaisse dans l'historique du terminal :

```bash
aws configure --profile game-assets   # ou éditer ~/.aws/credentials à la main
```

Le responsable réalise un test de restauration sur un clone propre avant d'y déposer des masters irremplaçables.

## Premier import Unity — terminé

La PR #10 a figé `Packages/packages-lock.json` et les migrations déterministes de Unity `6000.3.20f1`. Sur chaque nouvelle machine : faire `git pull --ff-only`, exécuter le setup, puis ouvrir Unity avec cette version exacte. Si Unity propose une montée de version ou produit un gros diff après une simple ouverture/fermeture, arrêter et comparer la version avant tout commit.

## Validation croisée et connexion

Chaque machine ouvre puis ferme le projet sans erreur ni resérialisation massive. Windows produit ensuite le build IL2CPP du test. Suivre [FIRST_CONNECTION_TEST.md](FIRST_CONNECTION_TEST.md) pour connecter les trois postes.

Lorsque les membres ne partagent pas le même Wi-Fi, suivre [REMOTE_CONNECTION_TEST.md](REMOTE_CONNECTION_TEST.md). Chaque poste doit être connecté au même tailnet avec un compte individuel ; aucune clé d'authentification n'est stockée dans le projet.

## Gates Wwise et Steam

Wwise `2025.1.4` est intégré sur une branche dédiée seulement après une compilation propre. Nils est le seul poste Wwise Authoring au départ. Il versionne dans la même PR l'intégration runtime et les SoundBanks approuvées via Git LFS ; Sean et Zak les récupèrent comme les autres assets et ne lancent jamais une intégration locale. Un événement minimal doit fonctionner dans un build Mac et Windows avant le merge.

Steamworks.NET/FishySteamworks arrive après un test distant Tugboat vert. Tugboat reste toujours disponible, notamment parce que les tests Steam multi-instance locaux sont limités par les comptes Steam.

## Quand une machine est intégrée

Une machine Mac ou Windows rejoint le travail partagé seulement lorsque :

1. son `doctor` termine avec `0 erreur` ;
2. Unity utilise exactement la version de `config/toolchain.env` ;
3. `git status --short` est vide sur `main` après une ouverture et fermeture de Unity ;
4. elle récupère un lot test DVC si le coffre est déjà activé ;
5. elle construit ou rejoint le test de connexion correspondant à son rôle.

Les avertissements Wwise, Steam ou coffre DVC sont acceptables uniquement tant que le jalon concerné n'a pas commencé.

## En cas d'écart

Ne pas mettre un package à jour sur une seule machine. Noter la commande, le commit et l'erreur ; vérifier `config/toolchain.env`, puis traiter tout changement de version dans une PR unique avec tests Mac et Windows.
