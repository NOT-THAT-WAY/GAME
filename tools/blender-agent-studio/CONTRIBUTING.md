# Contribuer

Une contribution doit être légère, reproductible et réutilisable par une autre équipe.

1. Créer un contrat sous `projects/team/` et garder les binaires sous `local_work/`.
2. Déclarer cible, version, unités, axes, budgets, invariants et critères d’acceptation.
3. Ajouter toute opération réutilisable à `workflows/catalog/` et la tester sur une fixture.
4. Classer une nouvelle connaissance comme observée, inférée ou validée localement.
5. Documenter provenance et droits ; ne jamais embarquer une ressource seulement parce qu’elle est
   disponible localement.
6. Pour les jeux, fournir un rapport d’import du moteur cible ; pour l’animation, contrôler tout le
   clip ; pour le rendu, fournir contact sheet et probe.
7. Exécuter les tests, le validateur de catalogue et le budget de distribution.

```bash
python3 -m unittest discover -s app/tests -p 'test_*.py'
python3 tools/verify_asset_catalog.py
python3 tools/check_distribution_budget.py
```

Ne pas committer de secret, chemin machine, lien symbolique, cache, `.blend`, image, audio, vidéo
ou format 3D. Une mise à jour du catalogue est générée depuis un coffre autorisé et vérifiée avant
commit.
