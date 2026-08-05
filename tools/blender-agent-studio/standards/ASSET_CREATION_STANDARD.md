# Standard de création d’assets

## Références et génération

- Enregistrer provenance, modèle/générateur, prompt, seed, date et droits de chaque référence.
- Distinguer vue observée, détail inféré et zone inconnue.
- Ne pas fusionner des orthos incohérentes sans décision documentée.
- Verrouiller silhouette, proportions et détails canoniques avant micro-détails.
- Une image générée guide la forme ; elle ne prouve ni l’arrière, ni l’intérieur, ni la mécanique.

## Construction

1. Définir fonction, dimensions, pièces, hiérarchie, pivots et zones de contact.
2. Faire un blockout aux dimensions cibles et le tester dans un contexte neutre.
3. Construire une topologie adaptée à la déformation, au bake ou au rendu prévu.
4. Contrôler normales, doubles, faces dégénérées, non-manifold et intersections interdites.
5. Définir UV, texel density, UDIM éventuels et matériau avant la livraison.
6. Créer les niveaux de détail et collisions seulement après validation du modèle maître.

## Qualité et preuve

Le gate d’asset montre au minimum face, profil, dos, trois-quarts et macro des détails identitaires,
avec une caméra et un éclairage neutres. L’audit consigne dimensions évaluées, nombres de vertices,
edges, faces et triangles, modifiers, matériaux, UV, pivots, transforms et dépendances.

Un asset articulé exige en plus limites de joint, clearance, collisions, positions fermée/ouverte,
zones de préhension et comportement sous parent animé.

## Livraison

Conserver le `.blend` maître dans `local_work/`, jamais dans le dépôt compact. Décrire chaque export
dans `delivery-manifest.json`, avec SHA‑256, taille, profil d’export et preuve de réimport. Séparer
l’asset de ses scènes de présentation.
