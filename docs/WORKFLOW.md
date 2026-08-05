# Travailler ensemble sans se bloquer

## Cycle quotidien

```text
issue courte → claim des fichiers/lots → branche courte → test → PR verte → intégration par Nils
```

Avant de commencer :

```bash
./scripts/start-task.sh feat nom-court
./scripts/assets-macos.sh pull   # seulement si la tâche utilise des masters
```

Sur Windows :

```powershell
.\scripts\start-task.ps1 feat nom-court
.\scripts\assets-windows.ps1 -Action Pull  # seulement si nécessaire
```

À la fin, fermer Unity/Wwise, examiner `git status` et `dvc status`, puis lancer le diagnostic. Pour un master modifié : **`dvc push` avant `git push`**.

Le hook partagé refuse les pushes directs vers `main` et les noms de branche hors contrat. Le chemin normal est toujours une pull request avec les contrôles verts, puis une décision d'intégration de Nils. Ce hook est un garde-fou local, pas une frontière de sécurité serveur.

Claude Code reçoit la même règle dans `CLAUDE.md` et le skill `git-task`. Une demande d'initialisation configure le hook, et aucune session ne doit utiliser `--no-verify`, modifier le hook ou pousser `main` depuis une autre interface.

## Branches et pull requests

| Préfixe | Quand l'utiliser | Exemple |
|---|---|---|
| `feat/` | fonctionnalité jouable ou réseau | `feat/player-movement` |
| `fix/` | bug ou régression | `fix/host-roster-sync` |
| `art/` | visuel, animation ou export | `art/pivot-blockout` |
| `audio/` | Wwise, musique ou SFX | `audio/pivot-effort` |
| `data/` | DVC, schéma ou migration | `data/asset-catalog` |
| `docs/` | documentation seule | `docs/windows-onboarding` |
| `chore/` | outils, packages, CI, réglages | `chore/unity-lockfile` |

Le titre de PR reprend le même type : `feat/player-movement` devient par exemple `feat: add player movement`. Après le commit :

```bash
./scripts/publish-task.sh "feat: add player movement"
```

```powershell
.\scripts\publish-task.ps1 "feat: add player movement"
```

Le contrôle `workflow-policy` répète ces validations dans GitHub. Sans protection serveur payante, l'équipe garde la règle simple : Zak et Sean publient une PR verte et Nils la relit, la teste au niveau de risque adapté, puis décide du squash merge. Une revue de Zak ou Sean peut être demandée pour leur expertise, mais elle n'est jamais obligatoire et ils n'ont pas à gérer l'interface des PR.

La matrice complète de ce qui est permis, coordonné, différé ou interdit se trouve dans [PROJECT_RULES.md](PROJECT_RULES.md). Les limites de la CI et l'ordre d'activation des builds automatisés se trouvent dans [CI_BUILDS.md](CI_BUILDS.md).

## Rôles temporaires

Chaque issue importante possède :

- un pilote qui tranche les détails de l'implémentation ;
- un binôme qui produit ou intègre réellement une partie ;
- un testeur externe qui suit uniquement la procédure livrée.

Les profils Zak/Sean/Nils orientent l'affectation mais ne créent aucun silo. Chaque système important doit être compris par deux personnes et testé par la troisième.

## Zones de conflit

| Type | Règle |
|---|---|
| scène `.unity` | un éditeur déclaré ; préférer les scènes additives |
| prefab | un prefab racine par feature ; éviter les prefabs géants |
| `ProjectSettings` | PR dédiée et validation Mac + Windows |
| manifest/lockfile | une seule PR de dépendance à la fois |
| master DVC | un lot et un éditeur déclarés dans l'issue |
| binaire runtime LFS | verrou LFS si l'édition directe est inévitable |
| Wwise Work Unit | Nils édite ; découpage par feature, jamais un Work Unit global |
| schéma ou donnée partagée | migration dédiée, compatible ou accompagnée d'un convertisseur |

UnityYAMLMerge réduit certains conflits mais ne rend pas sûres deux modifications simultanées de la même scène.

## Architecture Unity

```text
Assets/
├── _Project/        code et contenu du jeu, regroupés par feature
├── Scenes/          bootstrap temporaire du template
├── Settings/        réglages URP partagés
├── ThirdParty/      dépendances importées et licences
└── Wwise/           intégration générée par Audiokinetic Launcher
```

Dans `_Project`, regrouper par feature (`Core`, `Player`, `Pivot`, `Maze`, `Audio`, `UI`) plutôt que dans de grands dossiers globaux Scripts/Prefabs/Textures. Chaque feature possède ses petits prefabs, tests et scènes additives.

### Frontière gameplay réseau

Toute modification d'un joueur, d'un mur/pivot, d'une collision, d'une interaction, de la topologie ou de la connexion applique [l'ADR 0004](adr/0004-authoritative-topology-and-ticks.md). Avec Claude, le skill `network-gameplay` est obligatoire pour ces sujets.

Le code de domaine déterministe reste en C# pur et avance sur les ticks ; les `NetworkBehaviour` restent aux frontières de FishNet. Les clients envoient des intentions, l'hôte valide et simule. Les colliders viennent de la topologie versionnée, tandis que FBX, animation et interpolation restent visuels. Le prototype `PlayerMotor`/`PivotDirector`/`MazePlaytestBuild` ne constitue pas le patron d'architecture M1.

La preuve de référence est une scène grise à un pivot et deux joueurs. La map 16x16 sert ensuite de test d'intégration afin de ne pas confondre un bug réseau avec un import, un prop ou un maillage complexe.

Les masters correspondants restent hors GitHub :

```text
ExternalAssets/
├── Art/<AssetId>/
├── Audio/<AssetId>/
├── Narrative/<AssetId>/
└── References/<AssetId>/
```

Chaque `<AssetId>` est suivi séparément par DVC. Ne jamais lancer `dvc add ExternalAssets` sur la racine entière.

Nils possède seul Wwise Authoring au départ. Sean et Zak testent les événements existants depuis Unity ; ils reçoivent par Git/LFS la même intégration, les mêmes binaires de plateforme et les mêmes SoundBanks.

## Profils de test réseau

1. local rapide : Multiplayer Play Mode + Tugboat ;
2. LAN réel : trois machines sur le même réseau + Tugboat ;
3. distant équipe : Tailscale + Tugboat, sans modification du build ;
4. conditions dégradées : latence/perte/jitter avec Multiplayer Tools ;
5. Steam : deux comptes et deux machines après la gate distante.

Un changement d'état partagé vérifie aussi une arrivée tardive en cours de transition, un snapshot/reconnexion, 30/60/120 FPS et le profil `80 ms RTT / 2 % perte / 20 ms jitter`. Le résultat compare tick, checksum de topologie et révisions, pas seulement l'apparence à l'écran.

Un bug indique le commit, OS, rôle hôte/client, transport et conditions réseau. Les adresses privées et logs contenant des identifiants ne sont pas copiés dans une issue publique.

## Règles de données

- une seule source de vérité par type de donnée ;
- aucun secret, cache, build ou donnée personnelle dans Git ;
- provenance et licence avant import ;
- comptes individuels avec MFA ;
- le remote DVC est versionné et sauvegardé séparément ;
- test de restauration trimestriel ;
- toute collecte de playtest a un but et une date de suppression.

Voir [DATA_MANAGEMENT.md](DATA_MANAGEMENT.md) pour la politique complète.
