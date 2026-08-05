# Analyse — Factory Animation Polygon Runway

Le noyau du tutoriel est une boucle mécanique reproductible : un maillon est répété avec `Array`, l'ensemble suit un chemin fermé avec `Curve`, puis le tapis est translaté exactement de la longueur d'un maillon entre la première et la dernière clé.

## Recette retenue

1. Fixer fps et durée avant d'animer.
2. Construire un chemin fermé propre.
3. Créer un seul maillon aux transforms appliqués.
4. Empiler `Array` puis `Curve` sur l'axe correct.
5. Mesurer le pas exact du maillon.
6. Déplacer le tapis d'un pas sur une période en interpolation `Linear`.
7. Déplacer les boîtes à vitesse constante sur le tapis.
8. Réserver les courbes accentuées aux bascules, rotations et chutes.
9. Dupliquer les produits avec un offset temporel constant.
10. Vérifier explicitement la jonction dernier frame → premier frame.

## Savoir de production

Le transport continu et les événements expressifs ne doivent pas partager la même logique de courbe. Le tapis et la boîte ont besoin d'une vitesse constante; la chute et la rotation peuvent utiliser Bézier, anticipation et overshoot. Cette séparation empêche le glissement visuel.

Le décor stylisé est construit après le mécanisme. La caméra three-quarter/isométrique est choisie tôt pour éviter de détailler des faces jamais visibles.

Les réglages généralisés et les gates sont dans `analysis.json` et `knowledge/tutorials/ANIMATION_WORKFLOW_PLAYBOOK.md`.
