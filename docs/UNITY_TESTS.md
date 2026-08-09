# Tests Unity locaux

Cette fondation exécute séparément les tests EditMode et PlayMode avec Unity
`6000.3.20f1`. Elle prouve que les assemblies du projet compilent, que le Test Runner
trouve les tests et qu'un test PlayMode peut réellement avancer d'une frame. Elle ne
prouve pas encore le réseau, la scène 16x16, les colliders ni l'architecture M1.

État local au 9 août 2026 : Mac vert avec `5/5` EditMode et `1/1` PlayMode. La reproduction
Windows et l’activation d’une CI Unity restent à faire ; elles ne sont pas déduites de ce résultat.

## Prérequis

- ouvrir le dépôt avec la version Unity déclarée dans `config/toolchain.env` ;
- fermer toute instance Unity qui verrouille déjà ce projet avant un lancement batch ;
- sur macOS, installer l'éditeur avec Unity Hub à l'emplacement standard ;
- sur Windows, installer l'éditeur à l'emplacement standard de Unity Hub.

Un chemin non standard peut être fourni sans modifier le dépôt :

```bash
GAME_UNITY_EDITOR="/chemin/vers/Unity" ./scripts/unity-tests-macos.sh all
```

```powershell
$env:GAME_UNITY_EDITOR = "D:\Unity\6000.3.20f1\Editor\Unity.exe"
.\scripts\unity-tests-windows.ps1 -Suite All
```

## Commandes

Sur macOS :

```bash
./scripts/unity-tests-macos.sh all
./scripts/unity-tests-macos.sh editmode
./scripts/unity-tests-macos.sh playmode
```

Sur Windows PowerShell :

```powershell
.\scripts\unity-tests-windows.ps1 -Suite All
.\scripts\unity-tests-windows.ps1 -Suite EditMode
.\scripts\unity-tests-windows.ps1 -Suite PlayMode
```

Les deux wrappers :

1. lisent la version Unity attendue dans `config/toolchain.env` ;
2. lancent chaque plateforme de test dans un processus Unity batch distinct ;
3. conservent un XML NUnit et le log Unity complet ;
4. échouent si Unity retourne un code non nul, si le XML manque ou si la suite ne
   déclare pas `result="Passed"`.

Ils écrivent aussi `test-run.json` dans le même dossier. Ce manifeste fixe commit, état sale/propre,
version Unity, plateforme, suite demandée, code de sortie et compteurs par XML. C’est la synthèse à
joindre à une issue ; les XML et logs restent la preuve détaillée.

Les wrappers de player build produisent séparément un `build-manifest.json` à côté de l’exécutable :

- `Builds/ConnectionTest/<plateforme>/build-manifest.json` ;
- `Builds/MazePlaytest/<plateforme>/build-manifest.json`.

Ce manifeste de schéma 2 décrit le player réellement lancé : `buildId`, `buildSetId`, commit source,
worktree sale/propre, version Unity, cible, profil, méthode de build, hash SHA-256 et taille du
lanceur. Un `build-bundle-fingerprint.json` inventorie en plus tous les fichiers de l’application
macOS ou du dossier Windows avec chemins relatifs, tailles et hashes ; son manifeste canonique est
lui-même hashé. Le wrapper écrit d’abord l’état `building`, puis `passed` seulement après présence et
empreinte du bundle. Ainsi, l’échec d’une
reconstruction ne laisse pas un ancien manifeste vert accolé à un artifact potentiellement obsolète.
`--skip-build` / `-SkipBuild` ne réattribue jamais un ancien binaire au commit courant : le manifeste
existant est conservé, ou un avertissement signale que sa provenance manque.

Avant compilation, le même contrat est injecté sous `Resources` puis annoncé une fois au démarrage
par `[GAME-BUILD]`. Le rapport réseau compare ce marqueur au manifeste de chaque plateforme. Un log
ancien, un build sale, un mélange de builds ou une empreinte modifiée reste `INCOMPLETE` même si un
SHA plus récent est fourni manuellement à l’outil.

Par défaut, chaque exécution écrit dans un dossier horodaté sous
`Logs/Tests/macos/` ou `Logs/Tests/windows/`. Pour une sortie déterminée par un outil
ou une CI :

```bash
./scripts/unity-tests-macos.sh all --results-dir Logs/Tests/local-proof
```

```powershell
.\scripts\unity-tests-windows.ps1 -Suite All -ResultsDirectory Logs\Tests\local-proof
```

La variable `GAME_TEST_RESULTS_DIR` fournit la même surcharge. Les sorties restent
ignorées par Git ; joindre le XML et le log à la preuve du ticket ou à l'artifact CI.

## Où ajouter les prochains tests

- `Assets/_Project/Tests/EditMode/` : modèles C# purs, parseurs, checksums et
  validateurs qui n'ont pas besoin d'une scène en lecture ;
- `Assets/_Project/Tests/PlayMode/` : comportements qui exigent le cycle de vie
  Unity, une frame, de la physique ou plus tard une fixture réseau minimale.

Les payloads préparatoires de `TOP-01` sont sous
`Assets/_Project/Tests/Fixtures/Topology/`. Leur manifest couvre parsing JSON strict, version, IDs,
références et bornes. Il nomme explicitement comme différés connectivité, checksum, tick, gabarit,
énergie et manche ; ces fixtures ne servent donc pas à trancher une décision de design par défaut.

Les tests EditMode et PlayMode sont dans deux assemblies distinctes. Elles référencent
`Game.Runtime`, mais aucun test de fondation ne modifie une scène, un prefab, un FBX,
`ProjectSettings` ou un package.

## Preuve rouge puis verte

Avant de rendre TST-01 obligatoire en CI, faire sur une branche jetable une seule
modification volontairement fausse dans un smoke test, observer un code de sortie non
nul et le XML `Failed`, puis annuler cette modification et relancer les deux suites.
Ne jamais merger le test volontairement cassé.

Une exécution locale verte sur un seul Mac est une prévalidation. La sortie de TST-01
demande encore la même suite verte sur le PC Windows au même commit, ainsi qu'une
revue humaine des commandes et des artifacts.
