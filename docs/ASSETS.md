# Pipeline des assets

## Capacité disponible au départ

Mesure du 4 août 2026 : le dépôt `GAME` fait environ **164 Kio**, ne contient encore **aucun objet Git LFS** et ne référence aucun lot DVC. Les deux autres machines peuvent donc cloner et construire le projet sans attendre le coffre de masters.

L'organisation GitHub est sur le plan Free : elle inclut actuellement [**10 Gio de stockage Git LFS** et **10 Gio de téléchargement LFS par mois**](https://docs.github.com/en/billing/concepts/product-billing/git-lfs), avec une [limite de **2 Gio par fichier**](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage). Ce quota couvre les exports nécessaires au build, pas les `.blend`, PSD, sessions DAW ou prises brutes. Comme deux nouveaux clones retéléchargent chacun les objets LFS, l'équipe garde un budget interne de **2 Gio maximum d'exports actifs** pendant le prototype et vérifie la page Billing avant tout gros lot.

Le remote DVC n'a pas encore de capacité partagée car aucun fournisseur n'est configuré. Ce n'est pas nécessaire pour installer les trois postes : aucun master n'est encore référencé. Le choix du coffre est reporté au premier gros fichier source ; Cloudflare R2 Standard reste un candidat économique à comparer à ce moment-là.

## Quatre niveaux, une vérité par niveau

| Zone | Contenu | Stockage de référence |
|---|---|---|
| `ExternalAssets/<discipline>/<asset-id>/` | masters Blender/PSD/Krita, sessions DAW, prises brutes, références HD, sources IA | remote DVC privé, hors GitHub |
| `Assets/_Project/<Feature>/` | FBX, textures, clips et prefabs optimisés réellement consommés par Unity | GitHub ; Git LFS pour les binaires |
| `WwiseProject/` | projet, Work Units et Originals prêts à être utilisés | GitHub ; Git LFS pour l'audio binaire |
| `Assets/StreamingAssets/Audio/GeneratedSoundBanks/` | SoundBanks runtime approuvées par Nils | Git LFS, identiques pour tous |
| `Library/`, caches, SoundBanks de travail, builds et exports temporaires | résultats reconstruisibles | local uniquement |

Un master n'est jamais l'asset de runtime. Exemple : `PivotDoor.blend` reste dans le coffre DVC ; `PivotDoor_LOD0.fbx`, ses textures compressées et son prefab arrivent dans `Assets/_Project/Pivot/`.

## Pourquoi DVC

DVC lie le contenu lourd à un commit Git par empreinte sans envoyer ce contenu sur GitHub. Le remote peut être un bucket S3 ou compatible S3, Azure, Google Cloud, Google Drive, SSH/WebDAV ou un stockage local partagé. Pour une équipe appelée à grandir, préférer un bucket privé avec versioning objet, comptes individuels et règles de rétention.

Le remote n'est jamais monté comme dossier Unity. Chaque machine possède une copie locale hydratée par DVC.

## Critères du remote commun

Avant de choisir un fournisseur, vérifier : bucket privé par défaut, chiffrement en transit et au repos, versioning objet, comptes individuels avec MFA, droits sans suppression permanente pour le travail quotidien, journal d'accès, alerte de budget, coût de sortie acceptable et export complet possible. Garder une deuxième sauvegarde dans un compte ou support distinct.

Pour la croissance, une API S3-compatible évite de lier les scripts à un fournisseur. Google Drive peut dépanner au prototype, mais ne doit pas devenir un dossier synchronisé contenant le projet Unity.

## Première configuration par machine

Le responsable du stockage communique uniquement l'URL du remote et la méthode d'authentification. Les credentials ne passent ni dans Git, ni dans Discord, ni dans une capture d'écran.

macOS :

```bash
./scripts/setup-macos.sh --install-tools --with-assets
./scripts/assets-macos.sh configure "s3://game-assets-production/dvc"
./scripts/assets-macos.sh pull
```

Windows :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1 -InstallTools -WithAssets
.\scripts\assets-windows.ps1 -Action Configure -RemoteUrl "s3://game-assets-production/dvc"
.\scripts\assets-windows.ps1 -Action Pull
```

Pour un fournisseur compatible S3 qui exige un endpoint spécifique, ajouter `--endpoint` sur Mac ou `-EndpointUrl` sur Windows. La configuration est écrite dans `.dvc/config.local`, explicitement ignoré par Git.

## Ajouter ou modifier un lot

Ne jamais suivre tout `ExternalAssets/` en un seul bloc. Un dossier DVC correspond à un asset ou à un petit lot cohérent.

1. Créer/assigner l'issue et inscrire l'ID, le responsable et la provenance dans `docs/assets/ASSET_REGISTER.md`.
2. Vérifier qu'aucun autre membre n'a revendiqué ce lot.
3. Créer `ExternalAssets/<Discipline>/<AssetId>/` et y travailler.
4. Produire les exports déterministes dans `Assets/_Project/<Feature>/...`.
5. Réindexer puis envoyer le master hors GitHub :

   ```bash
   ./scripts/assets-macos.sh track ExternalAssets/Art/ART-PIVOT-001
   ./scripts/assets-macos.sh push
   ```

   Équivalent Windows :

   ```powershell
   .\scripts\assets-windows.ps1 -Action Track -Path ExternalAssets\Art\ART-PIVOT-001
   .\scripts\assets-windows.ps1 -Action Push
   ```

6. Committer dans la même PR le pointeur `.dvc`, le `.gitignore` généré, le registre, l'export Unity et son `.meta`.
7. Un second membre fait `git pull`, puis `assets-*.{sh,ps1} pull` et vérifie l'export.

Ordre impératif : **`dvc push` avant `git push`**. Sinon les collègues récupèrent un pointeur vers un contenu encore absent.

## Concurrence et conflits

DVC versionne mais ne verrouille pas l'édition. Le verrou humain est l'issue GitHub avec une échéance courte. Si deux variantes sont nécessaires, créer deux lots (`ART-PIVOT-001-A`, `ART-PIVOT-001-B`) puis choisir ; ne pas écraser le même master.

Les scènes et prefabs restent découpés par feature. Un export binaire modifié directement dans Unity peut utiliser `git lfs lock`, mais la source DVC reste la référence et doit pouvoir le régénérer.

## Nommage

- `PascalCase` pour les assets et dossiers Unity : `PivotArm_A.fbx`, `PivotContest.prefab`.
- Pas d'accents, espaces, noms temporaires ou variantes `final_final2`.
- Suffixes lisibles : `_Albedo`, `_Normal`, `_Mask`, `_SFX`, `_VO`.
- Respect strict de la casse, même si Mac et Windows masquent souvent les différences.

## Wwise

À versionner dans Git/Git LFS :

- le `.wproj` ;
- les Work Units `.wwu` ;
- les `Originals/` nettoyés et prêts pour Wwise ;
- scripts, presets et configuration non sensible nécessaires à la génération.
- l'intégration Unity et ses binaires de plateforme ;
- les SoundBanks runtime validées sous `Assets/StreamingAssets/Audio/GeneratedSoundBanks/`.

À ignorer :

- `.cache/` et `.wsettings/` ;
- SoundBanks intermédiaires dans `WwiseProject/GeneratedSoundBanks/` ;
- préférences utilisateur ;
- fichiers temporaires de profilage.

Les Work Units sont découpés par feature (`Pivot`, `Player`, `Maze`, `UI`) et non par personne. Nils est le seul à utiliser Wwise Authoring au départ. Sean et Zak peuvent déclencher et tester les événements déjà publiés depuis Unity sans Wwise installé ; toute modification ou régénération de banque passe par Nils et une PR audio.

Les sessions de DAW, prises multicanales, stems de travail et rendus haute définition restent dans `ExternalAssets/Audio/<AssetId>/`. Wwise ne reçoit que les fichiers approuvés nécessaires au projet.

## Assets externes et IA

Aucun asset téléchargé, acheté ou généré n'entre sans : source, auteur/fournisseur, date, licence, preuve conservée, transformations et restrictions. Pour l'IA, inscrire aussi l'outil, le modèle/version si connu, l'entrée sensible éventuelle et la décision d'usage (`prototype`, `commercial autorisé`, `à remplacer`).

Un plugin doit fournir les binaires nécessaires à l'éditeur Mac Apple Silicon et à la cible Windows x86_64. Une compatibilité uniquement Windows n'est pas suffisante, même si la sortie initiale reste Windows.

## Sauvegarde et récupération

- activer le versioning objet sur le remote ;
- conserver une deuxième copie sur un autre compte ou support ;
- tester une restauration complète au début de M1 puis chaque trimestre ;
- interdire la suppression permanente aux comptes courants ;
- journaliser qui possède l'accès et le révoquer au départ d'un membre.

Voir aussi [la politique de gestion des données](DATA_MANAGEMENT.md).
