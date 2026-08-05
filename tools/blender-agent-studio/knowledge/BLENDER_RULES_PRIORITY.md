# Priorité des règles Blender

Ce fichier tranche les conflits entre apprentissages. Les détails restent dans les standards,
playbooks, tutoriels et contrats d’objet liés.

## P0 — sécurité, identité et réalité

- Respecter la demande, les droits et les invariants déclarés.
- Inspecter scène, échelle, parents, axes, unités, caméra et dépendances avant toute écriture.
- Ne jamais écraser une source ni sauvegarder silencieusement.
- Préserver identité, fonction, supports, contacts, clearances, collisions et affordances.
- Mesurer les meshes évalués dans un repère déclaré ; recalculer les parents animés par frame.
- Refuser une preuve fondée seulement sur un rendu, une origine, un bone, un Empty ou un succès
  Python.

Sources : `PHYSICAL_WORLD_OBJECT_RULES.md`, `SCENE_TRIAL_EVALUATION_RULES.md` et les contrats sous
`physics/object-contracts/`.

## P1 — cible et livraison

- Le profil technique, la version de Blender ou du moteur, les unités, axes, formats et budgets
  déclarés gouvernent la production.
- Les budgets sont spécifiques au projet ; aucun nombre universel de triangles, textures, bones,
  samples ou lumières n’est inventé.
- Tout export est réimporté. Un asset de jeu est aussi testé dans Unity, Unreal, Godot ou la cible
  explicitement déclarée.
- Une dépendance, une conversion d’axes ou un dépassement de budget non vérifié bloque la livraison.

Sources : `standards/`, `standards/profiles/` et `standards/DELIVERY_STANDARD.md`.

## P2 — méthode reproductible

- Séparer références, source, travail, shot et sorties.
- Préférer modifiers et procédures non destructives ; versionner avant Apply ou bake.
- Suivre l’ordre blockout → structure/physique → métier → matériaux → mouvement/caméra → lumière.
- Corriger une catégorie à la fois, trois essais maximum, avec preuves comparables.
- Base Color est sRGB ; roughness, normal, masks et données sont Non-Color sauf preuve contraire.
- Les caches, seeds, node groups, réglages d’export et paramètres de rendu sont déclarés.

Sources : `BLENDER_AGENT_LOOP.md`, `BLENDER_PRODUCTION_PLAYBOOK.md` et les playbooks de tutoriels.

## P3 — domaine et direction artistique

Le standard métier et le profil artistique explicitement choisis s’appliquent uniquement après P0
à P2. Sans choix, utiliser `style-profiles/neutral-production.md`.

Drumboiii reste un profil disponible : anticipation/travel/recovery, caméra/target/focus séparés,
overlap Squishy contrôlé, HDRI séparé du ciel visible, fond procédural adapté à la focale et lumière
par couches prouvée en A/B. Ses valeurs sont toujours recalibrées sur l’asset, le fps, les bounds et
le moteur. Il ne peut déformer un objet rigide, casser une interaction ou masquer une collision.

Les recettes reveal, charnière, boucle, scatter, environnement et lookdev ne s’appliquent que quand
leur besoin existe.

## P4 — finition

FX, bloom, particules, poussière, motion blur, compositing, micro-détails et presets génériques
arrivent après les gates structurels. Ils ne masquent jamais un défaut.

## Séquence obligatoire

```text
brief observable → audit lecture seule → contrat physique/technique → workspace local
→ blockout → gates P0/P1 → construction métier → matériaux
→ mouvement/caméra/lumière si requis → preview complète → correction bornée
→ export → réimport cible → revue humaine → verdict séparé
```

En conflit : P0 gagne, puis P1, puis P2. P3 départage les solutions déjà valides ; P4 finit.
