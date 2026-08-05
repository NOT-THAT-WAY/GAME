# Standard rig et animation

## Rig

- Déclarer hiérarchie, axes d’os, bind pose, root, contrôles, deform bones et conventions de nommage.
- Séparer rig de contrôle et squelette d’export quand le moteur cible l’exige.
- Valider poids normalisés, influences, déformations extrêmes, volumes et zones rigides.
- Documenter contraintes, drivers, spaces, dépendances et ordre d’évaluation.
- Tester articulation et collisions sur géométrie évaluée, pas sur les contrôleurs seuls.

## Mouvement

Tout mouvement possède une cause, un état initial, une anticipation éventuelle, une action, une
réaction et une récupération. Les contacts des pieds, roues, mains, charnières et supports sont
mesurés frame par frame. Motion blur et caméra ne masquent jamais foot sliding, pops ou traversées.

## Clips

Chaque clip déclare nom, plage, fps, durée, loop, root motion, additive/non-additive, pose de référence
et événements. Pour une boucle, mesurer continuité de position, rotation, vitesse et déformation entre
fin et début. Pour root motion, fournir une version in-place si le pipeline la demande.

## Animation cinématique

Construire d’abord les poses clés et arcs en clay. Vérifier silhouette, ligne d’action, spacing,
contacts et rythme avant secondary motion. Les courbes sont revues dans le Graph Editor ; les
overshoots sont intentionnels et les tangentes ne créent pas de drift hors plan.

## Livraison

Exporter uniquement les bones et clips déclarés. Baker contraintes et drivers lorsque la cible ne
les supporte pas. Réimporter, comparer les frames clés et mesurer les écarts de transforms et de
durée. Un playblast complet et une contact sheet de poses sont obligatoires.
