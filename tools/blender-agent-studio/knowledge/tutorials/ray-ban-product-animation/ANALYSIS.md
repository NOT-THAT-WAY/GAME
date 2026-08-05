# Analyse — Blender Product Animation Ray-Ban

Ce tutoriel fournit surtout une méthode de **reveal produit démonté/recomposé**. Sa règle la plus réutilisable est de préparer le modèle pour l'animation dès la modélisation : chaque composant qui doit voler, pivoter ou converger reste un objet distinct, puis tout le produit est parenté à un contrôle global.

## Workflow retenu

1. Modéliser depuis des références en conservant la symétrie avec Mirror.
2. Séparer monture, verres, branches, logos et détails caméra.
3. Corriger origines, noms et échelle avant l'animation.
4. Créer un `PRODUCT_ROOT` et parenter avec Keep Transform.
5. Verrouiller l'état assemblé et poser les clés finales en premier.
6. Revenir au départ, disperser les pièces, puis décaler les arrivées.
7. Régler les courbes Bézier dans le Graph Editor et contrôler les collisions.
8. Garder une caméra sobre, puis ajouter studio, particules et motion blur.
9. Gater quatre états : départ, dispersion maximale, impact, pose hero.

## Ce qui est reproductible

- le rig `PRODUCT_ROOT`;
- la construction de l'animation à rebours depuis la pose finale;
- le décalage par groupes de pièces plutôt qu'un keyframe simultané;
- une scène distincte pour le break-apart;
- un accent particulaire court, uniquement après validation du mouvement principal.

## Limites

Les réglages exacts appartiennent à cette paire de lunettes. Sur un autre objet, la distance de dispersion, l'ordre des pièces, l'intensité du motion blur et le rôle des particules doivent être recalibrés selon l'échelle et la silhouette.

La recette généralisée et ses gates sont dans `analysis.json` et dans le playbook commun `knowledge/tutorials/ANIMATION_WORKFLOW_PLAYBOOK.md`.
