# Travailler ensemble sans se bloquer

## Cycle quotidien

```text
issue courte → claim des fichiers/lots → branche courte → test → revue → squash vers main
```

Avant de commencer :

```bash
git switch main
git pull --ff-only
./scripts/assets-macos.sh pull   # seulement si la tâche utilise des masters
git switch -c feat/nom-court
```

Sur Windows, remplacer la commande assets par `.\scripts\assets-windows.ps1 -Action Pull`.

À la fin, fermer Unity/Wwise, examiner `git status` et `dvc status`, puis lancer le diagnostic. Pour un master modifié : **`dvc push` avant `git push`**.

Le hook partagé refuse les pushes directs vers `main` : le chemin normal est toujours une pull request avec une revue. Ce hook est un garde-fou local, pas une frontière de sécurité serveur ; activer aussi la protection de branche GitHub dès que le plan du dépôt privé la permet.

Claude Code reçoit la même règle dans `CLAUDE.md` : une demande d'initialisation configure le hook, et aucune session ne doit utiliser `--no-verify` ou la variable de contournement administrateur. Tant que GitHub refuse la protection serveur sur ce dépôt privé, la protection dépend donc du hook installé et de cette discipline d'équipe.

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
2. LAN réel : trois machines + Tugboat ;
3. conditions dégradées : latence/perte/jitter avec Multiplayer Tools ;
4. Steam : deux comptes et deux machines après la gate LAN.

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
