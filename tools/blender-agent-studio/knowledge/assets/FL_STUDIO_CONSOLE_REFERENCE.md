# Référence — FL Studio transformé en console 3D

Projet d'application : `projects/fl-studio-console-2026-07-19/`.

## Ce que montre la référence

Le sujet n'est pas un ordinateur affichant FL Studio. L'interface du logiciel devient
l'architecture de l'objet : browser vertical à gauche, playlist en écran supérieur,
piano roll en plateau principal, mixer à droite et channel rack en module flottant.
Un châssis épais et arrondi relie ces écrans en une console de musique Y2K.

La couleur est organisée par rôle : graphite pour la cavité, coque gris chaud, lumière
verte pour l'activité et accents violets pour la silhouette. Le fond noir et la lumière
rasante conservent une lecture produit plutôt qu'une lecture de capture d'écran.

## Traduction Blender reproductible

1. séparer le contenu d'écran et la géométrie;
2. recadrer la source en panneaux fonctionnels;
3. placer chaque panneau sur une surface distincte avec un boîtier;
4. construire la silhouette avec des volumes simples fortement bevelés;
5. ajouter les informations temporelles en géométrie émissive (playhead, vu-mètres);
6. animer un seul mouvement caméra continu et laisser l'interface fournir le mouvement
   secondaire;
7. contrôler les frames de début, quart, milieu, trois-quarts et fin.

Cette méthode permet ensuite de remplacer les images par des Movie Textures, sans refaire
le modèle, la lumière ou la caméra.
