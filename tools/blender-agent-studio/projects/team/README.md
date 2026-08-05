# Projets d’équipe

Les dossiers créés ici ne contiennent que des contrats et preuves textuelles. Générer un projet :

```bash
python3 workflows/tools/create_team_project.py \
  --id example-prop-v001 \
  --type game-asset \
  --objective "Prop interactif" \
  --target "Godot 4.x, desktop" \
  --profile game-godot
```

Compléter tous les `UNRESOLVED`, budgets et gates. Les binaires restent dans le dossier ignoré
`local_work/<id>/`. Ajouter leurs hashes avec `build_delivery_manifest.py`; utiliser `--validated`
seulement après les contrôles correspondant à chaque rôle.

Pour la livraison finale, passer le projet à `reviewed` ou `released`, fournir un fichier de preuve
pour chaque gate et pour l’import cible, compléter la revue des droits et `FINAL_REVIEW.md`, puis :

```bash
python3 workflows/tools/validate_team_project.py projects/team/<id> --stage final
```
