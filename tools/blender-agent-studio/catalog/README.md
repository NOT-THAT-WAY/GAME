# Catalogue léger

Le dépôt n’embarque aucun asset binaire. `assets.json` décrit chaque contenu par SHA‑256, taille,
rôle, chemins historiques et métadonnées techniques. Les copies identiques partagent le même
`asset_id`. `asset-families.json` résume les ensembles ; `blender-scenes.json` reprend l’audit des
fichiers Blender ; `capabilities.json` décrit ce que le studio sait produire.

Vérifier le catalogue seul :

```bash
python3 tools/verify_asset_catalog.py
```

Chercher sans charger le JSON de 8 Mio dans un éditeur :

```bash
python3 tools/search_assets.py "robot side" --kind image --limit 20
python3 tools/search_assets.py --kind geometry --extension blend --json
```

Sur la machine qui possède le coffre complet :

```bash
python3 tools/verify_asset_catalog.py --source-vault /chemin/vers/le/coffre
```

Récupérer un seul asset dans le dossier Git-ignoré `local_assets/` :

```bash
python3 tools/materialize_assets.py \
  --source-vault /chemin/vers/le/coffre \
  --asset-id <préfixe-sha256-unique> \
  --confirm-rights
```

La présence dans le catalogue ne vaut pas autorisation de redistribution.
