# Analyse — Drumboiii HDRI Setup + Lattice for Squishy Movements

## Corpus

Deux vidéos locales ont été analysées le 21 juillet 2026, avec lecture visuelle régulière et
transcription anglaise horodatée :

| Source | Durée | Sujet |
|---|---:|---|
| `${ORIGINAL_MOVIES}/Blender_HDRI_Tutoriel_Drumboiii.mp4` | 06:34.967 | séparer HDRI, éclairage et ciel caméra |
| `${ORIGINAL_MOVIES}/Blender_Squishy_Tutoriel_Drumboiii.mp4` | 05:52.833 | combiner scale bounce et Lattice animée |

Les vidéos originales restent externes et n'ont pas été modifiées ni copiées dans le dépôt.

## Priorité extraite

Ces deux techniques complètent les tutoriels Drumboiii Camera et Lighting. Elles sont promues
au niveau **P1 haute direction artistique**, sous réserve des contrats physiques, de
l'identité de l'objet et des gates techniques.

## Workflow HDRI observé

### 00:00–02:19 — dissocier éclairage et fond visible

1. Partir de `Background → World Output`.
2. Activer Node Wrangler et utiliser `Ctrl+T` sur le Background pour créer
   `Environment Texture`, `Mapping` et `Texture Coordinate`.
3. Charger un HDRI : il fournit d'abord à la fois ciel visible, éclairage et reflets.
4. Dupliquer le Background et ajouter un `Mix Shader`.
5. Ajouter `Light Path` et connecter `Is Camera Ray` au facteur du Mix.
6. Réserver le shader HDRI aux rays d'illumination/réflexion et le second Background à la
   caméra.

Résultat observé : modifier la couleur du ciel caméra ne recolore plus les reflets du sujet.

### 02:19–05:07 — ciel procédural

1. `Noise Texture → ColorRamp` construit les masses de nuages.
2. Le tutoriel part d'une Scale proche de `7`, augmente Detail et rapproche les stops de la
   ColorRamp pour des formes plus définies.
3. `Gradient Texture → ColorRamp` ajoute une variation claire/foncée dans le ciel.
4. Le Mapping du gradient est tourné de `90°` pour l'orienter horizontalement dans le cadre.
5. `Mix Color` combine nuages et gradient ; Soft Light et son Factor sont proposés comme
   réglage artistique.

### 05:07–06:29 — relation entre focale et échelle du ciel

- Avec une caméra reculée et une focale longue, les nuages deviennent visuellement trop gros :
  augmenter la Scale du Noise, par exemple vers `30–50` dans la scène de démonstration.
- Avec une caméra très proche et une focale très courte, les nuages deviennent trop dispersés :
  réduire la Scale, proche de `2` dans la démonstration.

Ces nombres ne sont pas universels. La règle validable est la proportion apparente des nuages
dans le cadre final.

## Workflow Squishy observé

### 00:00–01:18 — animation primaire

1. Créer trois clés de Scale, approximativement frames `1`, `10` et `30` dans la scène source.
2. Mettre la première Scale à zéro.
3. Agrandir légèrement la clé centrale pour créer l'overshoot.
4. Revenir à la forme cible sur la troisième clé.

Le résultat est déjà un pop avec rebond avant toute déformation.

### 01:18–03:32 — préparation de la Lattice

1. Subdiviser le mesh suffisamment pour que la déformation soit propre, sans surcharger.
2. Ajouter une Lattice, l'agrandir pour englober le sujet et régler sa résolution autour de
   `4` sur l'axe utile.
3. En Edit Mode, sélectionner les points internes et les resserrer pour dessiner le squash.
4. Ajouter un modifier Lattice au sujet et choisir cette Lattice comme objet.
5. Tester sa translation à travers le mesh ; le tutoriel augmente Strength vers `2`, puis `3`
   pour accentuer l'effet.

### 03:32–05:46 — overlap et finition

1. Animer la position de la Lattice en combinaison avec le pop du sujet.
2. Commencer la Lattice légèrement avant l'animation principale, vers frame `-6` dans la
   démonstration.
3. Faire traverser la zone de déformation pendant le pop ; la fin est rapprochée de frame
   `39` à `28` pour rendre la réaction plus vive.
4. Ajouter une quatrième clé de Scale pour un second petit rebound.
5. Ajouter Subdivision Surface à la fin, niveau `3` dans la démo, afin de lisser le résultat.

## Transfert vers un objet multi-pièces

Le tutoriel utilise un seul cube. Pour un produit composé de plusieurs meshes :

- conserver un root séparé pour le placement et le mouvement global ;
- créer une Lattice commune englobant tout le produit ;
- ajouter un modifier pointant vers cette Lattice à chaque mesh déformable ;
- exclure sol, caméra, lights et contrôles non géométriques ;
- vérifier écrans, logos, trims et surfaces planes aux poses extrêmes ;
- commencer avec une Strength modérée avant d'approcher les valeurs de la démonstration ;
- ne pas appliquer les modifiers tant que silhouette et identité ne sont pas validées.

Pour la Fl Studio Box, le root attendu est `Fl Studio Box`. Il porte le mouvement global ; une
future `Fl Studio Box Lattice` porterait uniquement le squash/stretch.

## Niveau de preuve et limites

- **Observé** : nodes, ordre des opérations, valeurs citées, timing relatif et résultat rendu.
- **Inféré** : généralisation à un asset multi-pièces et séparation root/Lattice.
- **À valider** : intensités, topologie requise et comportement Eevee/Cycles sur chaque projet.
- La touche `Ctrl+T` et Node Wrangler accélèrent la construction mais ne constituent pas la
  logique du workflow.
- Les valeurs de frames doivent être converties selon le fps cible ; le timing en secondes et
  la relation anticipation/action/recovery priment.

