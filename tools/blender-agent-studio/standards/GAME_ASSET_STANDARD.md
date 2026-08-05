# Standard d’assets jeu vidéo

Ce standard complète le standard d’asset. Le moteur et la plateforme cibles doivent être déclarés ;
les valeurs de budget viennent du projet, jamais d’une recette générique.

## Contrat moteur

Déclarer version du moteur, renderer, plateforme, convention d’axes, unité cible, format, échelle,
orientation avant, règle de pivot, nommage, compression texture et méthode d’import. L’import dans
Unity, Unreal, Godot ou l’outil cible constitue la preuve finale de conversion.

## Géométrie temps réel

- Fixer un budget de triangles par LOD et distance d’écran.
- Éliminer géométrie invisible uniquement si elle n’est jamais révélée par gameplay ou destruction.
- Garder silhouette et shading stables entre LOD ; mesurer le saut visuel.
- Fournir collision simple, complexe ou hybride selon le gameplay, jamais depuis la seule silhouette.
- Contrôler normales pondérées, tangentes, smoothing, winding, n-gons d’export et scale négative.
- Déclarer sockets, points d’attache, pivots, pièces destructibles et variantes.

## UV, matériaux et textures

- Déclarer nombre d’UV, texel density, padding, résolution maximale et conventions de packing.
- Réserver une UV lightmap sans overlap quand le pipeline l’exige.
- Fixer budgets de materials, texture sets, dimensions, mémoire et shader complexity.
- Tester normal maps dans le moteur cible ; ne pas supposer une convention tangent-space compatible.

## Rigs et animation jeu

Déclarer squelette, bone budget, influences maximales, root, sockets, clips, root motion, sampling et
compression. Tester un cycle complet, transitions principales, pose extrême et déformation aux
articulations. Aucun bone auxiliaire non supporté ne reste silencieusement dans l’export.

## Gate moteur

Le rapport d’import cible consigne : échelle mesurée, orientation, pivot, materials, textures,
triangles/LOD, colliders, skeleton, clips, warnings importeur et captures de comparaison. Un GLB ou
FBX qui se réimporte seulement dans Blender n’est qu’une prévalidation.
