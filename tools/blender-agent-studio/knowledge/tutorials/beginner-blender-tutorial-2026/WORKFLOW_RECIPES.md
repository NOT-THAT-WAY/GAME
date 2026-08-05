# Recettes reproductibles issues du tutoriel

## 1. Blockout mesuré

**Entrées** : références, dimensions cibles, caméra prévue.

1. Créer les primitives les plus proches des formes finales.
2. Saisir des dimensions réelles avant le détail.
3. Appliquer les transforms seulement si un modifier l’exige.
4. Vérifier silhouette, proportions et intersections depuis la caméra.
5. Sauvegarder une version `blockout`.

**Gate** : échelle cohérente, aucun objet dupliqué au même endroit, noms et collections
propres. **Rollback** : revenir à la version `blockout`.

## 2. Tasse réutilisable

**Entrées** : cylindre, référence face/profil, épaisseur et subdivision.

1. Modeler le corps avec `Solidify` et `Subdivision Surface` non appliqués.
2. Contrôler le pied et le bord avec des loop cuts.
3. Versionner, puis appliquer Solidify.
4. Extruder l’anse depuis une face centrale.
5. Ajouter les loops de support et recalculer les normales.

**Gate** : anse soudée visuellement, épaisseur crédible, pas de pincement. **Sortie** :
collection objet + manifest des modifiers appliqués.

## 3. Icing organique contrôlé

**Entrées** : mesh donut validé, épaisseur, amplitudes des drips.

1. Dupliquer le donut sans translation et renommer immédiatement.
2. Conserver la moitié supérieure.
3. Modeler les drips en édition proportionnelle.
4. Construire le stack `Shrinkwrap → Solidify → Subdivision`.
5. Versionner avant d’appliquer Subdivision.
6. Ajouter Inflate/Grab de façon locale.

**Gate** : absence de z-fighting, drips non répétitifs, bords gonflés, profil lisible.

## 4. Matériau PBR trois maps

**Entrées** : Base Color, Normal, Roughness et licence de chaque fichier.

1. Créer un matériau Principled.
2. Configurer Base Color en sRGB.
3. Configurer Normal/Roughness en Non-Color.
4. Faire passer Normal par un nœud `Normal Map`.
5. Régler échelle, roughness et normal strength sur un objet test.
6. Écrire les dépendances dans le manifest.

**Gate** : aucun fichier manquant, color spaces corrects, pas de metallic/alpha parasite.

## 5. UV unwrap contrôlé

**Entrées** : mesh final ou stable, zones visibles, densité cible.

1. Placer les seams dans les zones cachées.
2. Séparer les formes impossibles à aplatir proprement.
3. Exécuter `Angle Based Unwrap`.
4. Vérifier stretching et texel density.
5. Corriger rotation/scale des îlots avec la texture réelle.
6. Utiliser Mio3/Gridify uniquement si déclaré.

**Gate** : seams invisibles depuis les caméras, stretching acceptable, résolution uniforme.

## 6. Scatter d’objets sans destruction

**Entrées** : surface cible, collection de variantes, vertex group, densité, seed.

1. Créer des sources low-poly aux pivots cohérents.
2. Ajouter `Scatter on Surface` et choisir la collection.
3. Activer `Pick Instance` et réinitialiser les transforms.
4. Régler axe, rotation, scale et surface offset.
5. Peindre le masque dans un Vertex Group.
6. Brancher le groupe sur `Distribution Mask`.
7. Ajuster Poisson Disc, Minimum Distance et Seed.
8. Ne réaliser les instances que si une correction finale l’exige.

**Gate** : couverture, collisions, variété, coût en polygones et silhouette caméra.

## 7. Rig lumière trois rôles

**Entrées** : intention narrative, exposition cible, palette chaud/froid.

1. Ajouter un Sun chaud comme key.
2. Ajouter un Point froid à grand radius comme sky fill.
3. Ajouter un Point neutre comme bounce intérieur.
4. Mettre chaque lumière dans une collection et les tester isolément.
5. Ajouter des blockers hors champ si nécessaire.
6. Tester depuis la caméra, pas seulement en perspective libre.

**Gate** : rôle lisible de chaque lampe, noirs non bouchés, highlights non brûlés, palette
cohérente.

## 8. Gate final Eevee/Cycles

**Entrées** : scène validée, caméra, focus object, budget de rendu.

1. Activer la profondeur de champ avec une cible explicite.
2. Rendre un frame Eevee avec Steps/samples/probe contrôlés.
3. Configurer Cycles sur GPU et activer denoise.
4. Rendre le même frame avec la même résolution.
5. Comparer silhouette, ombres, reflets, bruit, temps et mémoire.
6. Choisir le moteur selon le livrable mesuré.

**Sorties** : deux frames, métriques, décision de moteur et paramètres versionnés.

