# CI et builds par plateforme

## Ce qui est actif maintenant

La CI actuelle est volontairement légère et sans secret Unity. Un seul contrôle,
`repository-checks`, exécute les familles d’étapes suivantes sur Ubuntu :

| Étape | Ce qu'elle prouve | Quand |
|---|---|---|
| Validate branch and pull request title | branche et titre de PR conformes | pull request |
| Validate repository contract | versions, métadonnées Unity, LFS/DVC, fichiers interdits et présence du contrat réseau/skill Claude | toujours |
| Validate tooling contracts | wrappers humains/Unity, workflow, manifests et rapports expurgés testés sans licence Unity | toujours |
| Validate data fixtures | topologie JSON et empreinte canonique des bundles | toujours |
| Parse Windows scripts | tous les scripts `.ps1` sont analysables par PowerShell | toujours |

Ces contrôles étaient auparavant répartis dans trois jobs, dont un sous Windows. GitHub facture chaque
job à la minute supérieure et double le tarif Windows : trente secondes de
travail réel coûtaient 4 minutes par pull request. Les regrouper ramène le coût à
1 minute par exécution, sans rien retirer aux contrôles. `pwsh` étant préinstallé
sur les runners Ubuntu et son parseur indépendant de la plateforme, analyser du
PowerShell n'y perd rien.

En contrepartie, la PR n'affiche plus qu'un seul check : l'étape en échec se lit
dans le log du job, pas dans la liste des contrôles. Ajouter un job pour
retrouver un nom distinct coûte au moins une minute par exécution, à peser contre
les 2 000 minutes mensuelles du plan Free.

Les jobs ont uniquement `contents: read`, ne téléchargent pas les payloads LFS et n'utilisent aucun secret de build. Le dépôt n'autorise actuellement que les Actions appartenant à GitHub et exige une empreinte SHA complète. Dependabot proposera séparément leurs mises à jour. Une future Action Unity externe devra être revue puis autorisée explicitement pendant sa gate.

Le contrôle `validate` empêche la suppression silencieuse de l'ADR 0004, du skill `network-gameplay` et de ses notions minimales (`startTick`, réconciliation, topologie/colliders, cible de connexion et profil dégradé). Il ne prouve pas que le code les respecte : cette preuve vient des tests EditMode/PlayMode et de la matrice réseau.

La CI ne prétend pas encore compiler Unity. La compilation de preuve actuelle est locale :

```bash
./scripts/first-test-macos.sh manual --build-only
```

```powershell
.\scripts\first-test-windows.ps1 Manual -BuildOnly
```

Le premier produit un build de développement macOS. Le second doit produire le build Windows x86_64 IL2CPP de référence.

## Matrice de validation

| Changement | Mac | Windows | CI Unity future |
|---|---:|---:|---:|
| docs, règles, scripts Bash | obligatoire | syntaxe PowerShell si touchée | non |
| gameplay C# pur | build/Play Mode | smoke test avant merge important | EditMode puis PlayMode |
| état gameplay partagé, murs ou joueur | scène grise + réseau dégradé | IL2CPP + autre machine au même commit | EditMode déterministe + PlayMode à deux |
| scène, prefab, URP, input | ouverture propre + build | ouverture/smoke test | PlayMode |
| `Packages`, `ProjectSettings`, plugin natif, réseau, Wwise | build obligatoire | build IL2CPP obligatoire | matrice Mac + Windows |
| release Windows | test secondaire | build signé sur poste/runner contrôlé | Windows uniquement |

## Ce qui n'est pas configuré exprès

- aucune licence Unity dans GitHub ;
- aucun certificat Windows ou Apple ;
- aucun upload automatique de builds ;
- aucun déploiement Steam ;
- aucun runner auto-hébergé ;
- aucun secret Wwise, DVC ou Tailscale ;
- aucun scan de contenu dédié aux secrets ; le validateur ne couvre pour l'instant que les chemins suspects.

Avant d'introduire des credentials DVC, Wwise, Steam, signature ou publication dans GitHub, ajouter une gate de détection de secrets compatible avec la politique d'Actions du dépôt, épinglée par SHA ou exécutée par un outil contrôlé avec checksum. Les secrets restent dans GitHub Environments ou le gestionnaire prévu, jamais dans un fichier de configuration versionné.

Ajouter un workflow qui attend un secret absent créerait une fausse CI rouge. Ces éléments restent donc documentés jusqu'à leur gate.

## Gate pour activer les builds Unity en CI

Ouvrir une PR `chore/unity-build-ci` seulement lorsque :

1. un test EditMode du modèle déterministe et un test PlayMode dans la scène grise à deux joueurs existent ;
2. le build Mac et le build Windows IL2CPP passent manuellement au même commit ;
3. l'équipe choisit le mode de licence Unity et le runner ;
4. les secrets sont stockés dans GitHub, jamais dans un fichier ou un log ;
5. les actions externes sont figées par SHA et disposent du minimum de permissions ;
6. les artifacts de PR sont non signés, privés et conservés peu de temps ;
7. signature, notarisation et publication utilisent un environnement séparé avec approbation manuelle.

Ordre recommandé : compilation des assemblies → EditMode → PlayMode du smoke test → build Mac de développement → build Windows IL2CPP → artifact interne. La signature et Steam restent un workflow de release distinct.

## Règle d'échec

Une CI rouge n'est jamais contournée par un merge puis « correction après ». Corriger sur la même branche ou documenter explicitement qu'un service externe est indisponible. Un build local vert ne remplace pas la syntaxe Windows ; une syntaxe CI verte ne remplace pas le premier build IL2CPP réel sur le PC.
