# Rapports de preuve assets

Deux modèles empêchent les validations DVC et Blender→Unity de rester dans des notes libres
impossibles à comparer :

- [`dvc-restore-report.template.json`](templates/dvc-restore-report.template.json) pour `DVC-02/03` ;
- [`blender-unity-import-report.template.json`](templates/blender-unity-import-report.template.json)
  pour la gate moteur du profil Blender `game-unity`.

Ils ne décident ni les budgets, ni la direction artistique, ni la licence. Ils vérifient seulement
que la preuve annoncée correspond réellement au test exécuté.

## Validation

Copier le modèle vers un dossier de session ignoré, le remplir, puis lancer :

```bash
python3 scripts/validate-evidence-report.py Logs/AssetRestore/<session>/report.json
```

```powershell
py .\scripts\validate-evidence-report.py Logs\AssetRestore\<session>\report.json
```

Le validateur retourne un JSON et un code non nul si le rapport se contredit. Le modèle brut est
volontairement invalide : un placeholder `UNRESOLVED` n’est jamais une preuve.

## Restauration DVC

Exécuter le test dans un clone jetable ou avec un cache isolé réellement vide. Ne jamais supprimer
le cache de travail partagé uniquement pour fabriquer cette preuve. Le rapport consigne :

- commit propre, version DVC, alias de machine et OS ;
- preuve du cache vide, cible exacte et log de `dvc pull` ;
- hash attendu, hash restauré et taille de chaque artifact contrôlé ;
- pour `DVC-03`, confirmation séparée du versioning objet et de la seconde copie.

Un `PASS` est refusé si le cache n’est pas vide, si `dvc pull` échoue, si un hash diffère ou si les
deux protections de stockage de `DVC-03` ne sont pas prouvées. Les noms réels, endpoint R2, IP,
credentials et identifiants de compte restent hors du rapport ; utiliser un alias de machine et une
référence vers la preuve administrative privée.

La preuve Mac et la preuve Windows restent deux rapports distincts. Elles peuvent partager le même
`testId`, commit et lot, mais jamais le même `sessionId`.

## Blender vers Unity

Le rapport final vit avec les preuves textuelles du projet studio :

```text
tools/blender-agent-studio/projects/team/<project-id>/evidence/unity-import-report.json
```

Les `.blend`, exports de travail, captures et caches restent sous le `local_work/<project-id>/`
ignoré ou dans le lot DVC déclaré. Le parcours attendu est : audit de source immuable, export hashé,
réimport indépendant, puis import dans **Unity 6000.3.20f1 dans ce projet**.

Le rapport reprend automatiquement les gates du profil
`tools/blender-agent-studio/standards/profiles/game-unity.json` : échelle, orientation, pivot, LOD,
colliders, UV/lightmap, matériaux, squelette/clips éventuels et rapport d’import Unity. Une gate sans
objet peut être `NOT_APPLICABLE`, avec une raison ; aucun budget générique n’est imposé.

Un réimport Blender seul ne peut jamais produire `technicalResult: PASS`. Il faut un import Unity,
des mesures cible, un log importeur et une preuve pour chaque gate applicable. Si l’asset Unity est
une dérivation et non une copie octet pour octet de l’export, `artifactComparison.mode` devient
`derived` et cite la transformation au lieu de forcer deux hashes identiques.

Le résultat technique et la décision de livraison restent séparés :

- `SHIP` exige droits validés et revue humaine approuvée ;
- `PROTOTYPE_ONLY` exige que ce statut de droits soit déclaré et approuvé ;
- une importation techniquement verte peut rester `BLOCKED` pour la livraison ;
- une collision, dépendance manquante, conversion non vérifiée ou autre échec critique interdit le
  `PASS` technique.

Le validateur contrôle la cohérence du rapport, pas l’existence d’une preuve privée inaccessible au
dépôt. Le témoin et l’approbateur vérifient les fichiers cités avant de fermer le ticket.
