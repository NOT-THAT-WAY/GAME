# Standard de production Blender

Ce document est obligatoire pour toute création. Il définit le niveau minimal commun aux assets,
jeux vidéo, rigs, animations, environnements, images fixes et films.

## Priorités

1. Préserver les sources, les droits, l’identité et la fonction réelle.
2. Déclarer unités, repère, échelle, cible, contraintes et preuves avant de produire.
3. Valider géométrie et mouvement avant caméra, lumière et polish.
4. Séparer qualité du package, validité technique, validité physique et qualité visuelle.
5. Ne publier ou sauvegarder que vers une destination explicitement autorisée.

Un rendu séduisant ne compense jamais une topologie inutilisable, une collision, un pivot faux, une
animation qui glisse ou un export non testé.

## Contrat avant production

Tout projet déclare au minimum : résultat attendu, usage, distance d’observation, plateforme ou
moteur cible, unités, axes, dimensions, invariants visuels, interactions, budgets, formats,
profil artistique et critères d’acceptation. Une valeur inconnue reste `unresolved`; elle n’est pas
inventée silencieusement.

## Ordre obligatoire

```text
brief observable → audit lecture seule → contrat technique et physique → copie locale
→ blockout → gates structure/échelle → construction → gates métier
→ matériaux → animation/caméra → lumière → previews comparables
→ correction bornée → export → réimport cible → verdict
```

Une correction automatique ne change qu’une catégorie à la fois et s’arrête après trois essais
sans amélioration démontrée.

## Repère, unités et transformations

- Travailler en unités métriques sauf contrat contraire.
- Déclarer l’échelle Blender et l’échelle cible ; ne jamais utiliser un facteur d’export caché.
- Appliquer ou conserver les transformations selon le besoin du rig et du pipeline, puis le prouver.
- Déclarer origine, pivot fonctionnel, axes locaux et orientation avant animation ou export.
- Vérifier les bounds sur géométrie évaluée, pas seulement sur les objets de contrôle.

## Gates universels

- **Source** : fichier original immuable, provenance et droits connus.
- **Structure** : noms stables, collections propres, dépendances résolues, aucun datablock orphelin
  critique.
- **Fonction** : pièces, supports, clearances, colliders, joints et affordances cohérents.
- **Géométrie** : silhouette, normales, manifold selon usage, épaisseur, modifiers et densité adaptés.
- **Visuel** : composition, hiérarchie, focus, matériaux, exposition et lisibilité à la distance cible.
- **Performance** : budgets déclarés puis mesurés ; aucun budget universel inventé.
- **Livraison** : manifeste, hashes, versions, export et réimport indépendant.

## Preuves recevables

Une affirmation finale cite un fichier ou une mesure reproductible. Pour la physique et le mouvement,
mesurer les meshes évalués dans un repère déclaré à chaque frame utile. AABB, Empty, os ou rendu seul
sont des indices préliminaires. Pour l’image, comparer caméra, frame, résolution, color management et
samples identiques.

## Critères d’échec critique

Écrasement de source, identité cassée, traversée de décor, support absent, articulation impossible,
drift non motivé, normales visiblement invalides, frame corrompue, média manquant, dépassement de
budget non déclaré ou export non ouvrable entraînent un rejet, même si le rendu paraît beau.
