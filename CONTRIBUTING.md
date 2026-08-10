# Contribuer à GAME

## Avant de commencer

1. Exécuter le `doctor` de sa plateforme.
2. Mettre `main` à jour avec `git pull --ff-only`.
3. Hydrater les masters avec le script `assets` uniquement si la tâche référence déjà un lot DVC.
4. Créer une branche courte avec le script `start-task` ; ne pas la créer depuis une branche en retard.
5. Revendiquer dans l'issue les scènes, prefabs, Work Units et lots DVC modifiés.
6. Pour un joueur, mur/pivot, collision, topologie, interaction ou transport, lire [l'ADR 0004](docs/adr/0004-authoritative-topology-and-ticks.md) et appliquer le skill Claude `network-gameplay` avant de coder.

## Pendant le travail

- une tâche principale par personne et des branches de deux à quatre jours maximum ;
- `main` reste ouvrable et jouable ;
- une scène partagée n'a qu'un éditeur à la fois ;
- déplacer/renommer les assets Unity uniquement depuis Unity pour conserver leurs `.meta` ;
- ne jamais committer caches, builds, secrets, credentials DVC ou données personnelles ;
- ne jamais placer un master éditable dans Git, même sous LFS ;
- enregistrer source, version, auteur, licence, preuve et restrictions avant l'import d'un asset externe ou IA.

Un changement de gameplay partagé distingue toujours l'intention cliente de la décision de l'hôte. Il indique dans l'issue les IDs/schéma touchés, l'ordre de tick, la politique de collision, le snapshot d'arrivée tardive et le profil réseau de preuve. Les implémentations actuelles de `PlayerMotor`, `PivotDirector` et des colliders FBX sont des prototypes à migrer, pas des exemples à étendre.

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
./scripts/publish-task.sh "feat: add player movement" --body-file /chemin/vers/pr-body.md

# Windows PowerShell
.\scripts\publish-task.ps1 "feat: add player movement" -BodyFile C:\chemin\pr-body.md
```

Le script vérifie le nom et le corps, refuse les changements non commités, pousse la branche et crée
la PR avec GitHub CLI. Sans fichier de corps, `gh` ouvre l’édition interactive ; un contexte non
interactif exige `--body-file` / `-BodyFile`. Sans session `gh`, le script donne le lien exact à
ouvrir. La CI contrôle de nouveau le nom de branche, le titre et les contrats de workflow.

Une PR indique le résultat, les fichiers/lots touchés et les tests réalisés. Une tâche est terminée seulement lorsqu'un autre membre peut la tester depuis un clone ou une mise à jour propre.

## Définition de terminé

- résultat intégré dans une scène ou une build testable ;
- aucun cache, secret ou master brut ajouté à Git ;
- pointeurs DVC disponibles dans le remote si la tâche touche un master ;
- validation par un second membre ;
- test sur l'autre OS si le changement touche plugin, réseau, audio, chemins ou build ;
- pour un état gameplay partagé : tests du modèle pur, scène grise à deux joueurs, arrivée tardive et réseau dégradé selon l'ADR 0004 ;
- ADR/documentation mis à jour si un contrat partagé change.

Lire aussi [le contrat du projet](docs/PROJECT_RULES.md) pour les changements autorisés/différés et [la matrice CI/build](docs/CI_BUILDS.md) pour décider quels OS doivent valider la PR.
