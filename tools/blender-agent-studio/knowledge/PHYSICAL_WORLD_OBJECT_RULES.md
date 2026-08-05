# Règles du monde physique et affordances d'objets

## Pourquoi ce système existe

Une animation peut être géométriquement valide et humainement absurde. Une charnière peut tourner
sans erreur Python dans le mauvais sens; un produit peut suivre une courbe tout en traversant un
support; un objet peut rester dans le cadre tout en présentant sa face arrière à l'utilisateur.

Chaque asset articulé doit donc posséder un **contrat d'objet** avant animation. Le contrat est une
source locale, explicite et testable. Un modèle de langage ne peut pas remplacer ce contrat par une
supposition.

## Les cinq couches de vérité

1. **Repère canonique** : haut, avant utilisateur, droite et position debout.
2. **Sémantique des pièces** : base fixe, pièce mobile, surface manipulée, surfaces regardées.
3. **Cinématique** : pivot, axe, degré de liberté, signe d'ouverture et limites angulaires.
4. **Contact** : support, gravité, dégagement minimal et volumes interdits.
5. **Affordance humaine** : ce que l'objet permet et la configuration dans laquelle cette action a du sens.

## Règles obligatoires

- Un objet articulé ne peut être animé avant d'avoir rendu les deux signes candidats du joint.
- `open` et `closed` sont des relations sémantiques, pas seulement deux angles.
- Une surface d'interaction doit rester accessible dans l'état d'usage.
- Une surface d'information doit faire face à l'utilisateur dans l'état d'usage.
- Une pièce ne possède que les degrés de liberté déclarés dans le contrat.
- Le pivot doit rester invariant dans le repère de la base.
- Les angles doivent rester dans les limites déclarées.
- Toute trajectoire doit produire des clearances positives contre le décor.
- Un déplacement au contact d'un support doit partager sa vitesse, ou montrer un support solidaire.
- Une lévitation exige une cause visible et ne peut commencer avant cette cause.
- Les états début, anticipation, action, impact et repos sont validés séparément.
- Les gates doivent montrer le contact et l'espace libre, pas seulement le produit.

## Représentation locale

Les contrats sont stockés dans `knowledge/physics/object-contracts/`. Ils reprennent les idées utiles
des URDF : liens, joint revolute/prismatic, axe, limites et relation parent/enfant. Ils ajoutent les
éléments absents d'une simple simulation : côté utilisateur, surface informative et description de
l'affordance.

Le validateur Blender est `workflows/scripts/validate_articulated_object.py`. Il refuse un contrat
incomplet, vérifie les angles aux états clés, la monotonie du mouvement principal et les dégagements
verticaux déclarés.

## Sources de recherche intégrées

- **Articulate-Anything** : génération et critique de joints articulés, pivot, axe, partie fixe,
  partie mobile et limites; copie de recherche dans `third_party/physical-world/articulate-anything`.
- **PhysBench** : catégories de compréhension du monde physique; copie Apache-2.0 dans
  `third_party/physical-world/physbench`.
- **RoboCSKBench** : affordances et commonsense incarné. Aucune licence claire n'a été trouvée dans
  la copie téléchargée; elle reste une référence locale non redistribuable.
- **PartNet / PartNet-Mobility et SAPIEN** : objets articulés décrits par parties, joints et URDF.
- **BEHAVIOR-1K / OmniGibson** : états d'objets et actions humaines de haut niveau.
- **Blender Rigid Body Constraints** : hinge à un degré de liberté, pivot, axe et limites.

## Limite importante

Une loi physique ne suffit pas à décider si un téléphone s'ouvre vers l'utilisateur. La gravité et
les collisions acceptent les deux signes. Le sens correct vient de la combinaison suivante :

```text
joint valide + écran face utilisateur + clavier accessible + état fermé cohérent
```

C'est une règle d'affordance, confirmée par des gates opposant les deux candidats. Pour le
`DRUMBOII_FLIP_PHONE`, un balayage statique a montré que la limite fermée propre est `+140°` :
`+90°` reste horizontal et `+155°..+180°` traverse le clavier. La limite théorique d'une classe
d'objet ne doit donc jamais remplacer la limite mesurée de son mesh particulier.
