# Contribuer à GAME

## Avant de commencer

1. Exécuter le `doctor` de sa plateforme.
2. Mettre `main` à jour avec `git pull --ff-only`.
3. Si nécessaire, hydrater les masters avec le script `assets`.
4. Créer une branche courte avec le script `start-task` ; ne pas la créer depuis une branche en retard.
5. Revendiquer dans l'issue les scènes, prefabs, Work Units et lots DVC modifiés.

## Pendant le travail

- une tâche principale par personne et des branches de deux à quatre jours maximum ;
- `main` reste ouvrable et jouable ;
- une scène partagée n'a qu'un éditeur à la fois ;
- déplacer/renommer les assets Unity uniquement depuis Unity pour conserver leurs `.meta` ;
- ne jamais committer caches, builds, secrets, credentials DVC ou données personnelles ;
- ne jamais placer un master éditable dans Git, même sous LFS ;
- enregistrer source, version, auteur, licence, preuve et restrictions avant l'import d'un asset externe ou IA.

## Livrer un asset

1. `dvc add ExternalAssets/<Discipline>/<AssetId>` via le script fourni ;
2. exporter vers `Assets/_Project/<Feature>/...` ;
3. mettre à jour `docs/assets/ASSET_REGISTER.md` ;
4. lancer `dvc push` avant `git push` ;
5. committer pointeur `.dvc`, `.gitignore` généré, export, `.meta` et registre dans la même PR.

## Commits et PR

Une branche respecte exactement `TYPE/nom-court-en-minuscules`. Les types disponibles sont :

| Type | Usage |
|---|---|
| `feat/` | gameplay, réseau ou nouvelle capacité |
| `fix/` | bug ou régression |
| `art/` | visuel, animation, UI artistique ou export |
| `audio/` | Wwise, musique et effets sonores |
| `data/` | DVC, schéma, catalogue ou migration |
| `docs/` | documentation uniquement |
| `chore/` | dépendances, réglages, CI et maintenance |

Depuis un dépôt propre :

```bash
# macOS
./scripts/start-task.sh feat player-movement

# Windows PowerShell
.\scripts\start-task.ps1 feat player-movement
```

Exemples :

```text
feat: add local connection roster
fix: clamp pivot state before replication
art: add pivot blockout export
audio: add pivot effort prototype
data: document asset retention policy
docs: clarify LAN test procedure
chore: update repository checks
```

Le titre de PR reprend le type de la branche. Après le commit :

```bash
# macOS
./scripts/publish-task.sh "feat: add player movement"

# Windows PowerShell
.\scripts\publish-task.ps1 "feat: add player movement"
```

Le script vérifie le nom, refuse les changements non commités, pousse la branche et crée la PR avec GitHub CLI. Sans session `gh`, il donne le lien exact à ouvrir. La CI contrôle de nouveau le nom de branche et le titre de PR.

Une PR indique le résultat, les fichiers/lots touchés et les tests réalisés. Une tâche est terminée seulement lorsqu'un autre membre peut la tester depuis un clone ou une mise à jour propre.

## Définition de terminé

- résultat intégré dans une scène ou une build testable ;
- aucun cache, secret ou master brut ajouté à Git ;
- pointeurs DVC disponibles dans le remote ;
- validation par un second membre ;
- test sur l'autre OS si le changement touche plugin, réseau, audio, chemins ou build ;
- ADR/documentation mis à jour si un contrat partagé change.
