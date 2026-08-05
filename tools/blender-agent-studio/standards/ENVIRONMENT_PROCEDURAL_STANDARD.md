# Standard environnements et procédural

## Environnement

- Déclarer métrique de grille, échelle humaine, zones jouables, caméra et navigation.
- Construire un kit modulaire avec pivots, dimensions et règles de connexion documentés.
- Vérifier coutures, z-fighting, collisions, épaisseur, accès, hauteurs et pentes.
- Définir budgets par zone : triangles, instances, materials, lights, overdraw et mémoire textures.
- Prévoir LOD/HLOD, culling, occlusion, lightmaps ou éclairage dynamique selon la cible.

## Scatter et Geometry Nodes

Tout système procédural déclare seed, surface, densité, masque, orientation, échelle, exclusions,
distance de sécurité et version des node groups. Utiliser des instances tant que possible. Mesurer
le nombre final d’instances, la mémoire et le coût après réalisation éventuelle.

Les règles de scatter respectent gameplay, chemins, contacts et visibilité. Un sol visuellement
rempli mais impraticable est invalide.

## Reproductibilité

Figer les seeds pour un gate. Versionner les paramètres et node groups, pas les caches lourds.
Déclarer comment rebaker simulations, végétation, lightmaps et navigation. Les caches locaux restent
dans `local_work/` et sont référencés par hash dans le manifeste.
