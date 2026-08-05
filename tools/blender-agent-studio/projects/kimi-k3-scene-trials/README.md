# Essais autonomes Kimi K3

Chaque sous-dossier est un essai isolé, versionné et validable. Ne jamais déposer ici un
fichier source unique sans conserver son origine dans `trial-manifest.json`.

Créer un essai :

```bash
python3 workflows/tools/create_kimi_scene_trial.py \
  --id k3-objet-intention-v001 \
  --objective "Sujet + cause + action + résultat" \
  --source-blend Pulsed_3D_model.blend \
  --duration 8 --fps 24
```

Avant Blender :

```bash
python3 workflows/tools/validate_kimi_scene_trial.py \
  projects/kimi-k3-scene-trials/k3-objet-intention-v001 --stage scaffold
```

Avant livraison, employer `--stage final`. Le validateur contrôle le package, la durée vidéo,
les sept catégories de score, les preuves et les échecs critiques.
