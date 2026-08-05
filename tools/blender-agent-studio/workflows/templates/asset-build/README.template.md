# Construction d’asset — __ASSET_ID__

Objectif : __OBJECTIVE__

Le fichier de travail autorisé est `source/asset.blend`. Compléter le brief et le contrat avant de
modéliser, puis lancer :

```bash
python3 workflows/tools/validate_asset_build.py \
  projects/asset-builds/__ASSET_ID__ --stage scaffold
```

Tout export autre que `.blend` doit être réimporté et enregistré dans
`diagnostics/export-validation.json`.
