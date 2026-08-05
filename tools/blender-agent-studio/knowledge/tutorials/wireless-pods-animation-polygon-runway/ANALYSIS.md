# Analyse — Wireless Pods Animation Polygon Runway

Le tutoriel montre une chorégraphie produit articulée. Son principe clé est mécanique : le couvercle doit posséder une origine située exactement sur l'axe de charnière, et la hiérarchie doit être finalisée avant les keyframes.

## Workflow retenu

1. Modéliser les volumes en subdivision en privilégiant la silhouette.
2. Séparer corps, couvercle, détails et objets contenus.
3. Placer l'origine du couvercle sur la charnière avec le curseur 3D.
4. Construire `ROOT → body/lid`, tout en gardant les écouteurs animables.
5. Bloquer cinq états : fermé, ouvert, contenu en haut, contenu revenu, refermé.
6. Respecter l'ordre causal : ouverture, envol, suspension, retour, fermeture.
7. Régler les F-Curves par fonction et contrôler toute collision.
8. Ajouter une rotation globale modérée seulement après le mouvement mécanique.
9. Finaliser avec backdrop, HDRI, rim light, matériaux et couleur animée.

## Ce qui devient un asset réutilisable

- un rig générique `ROOT/body/lid/contents`;
- une action `open-close` avec axe de charnière documenté;
- une action `content-rise` indépendante;
- un studio produit HDRI + rim;
- un gate mécanique à chaque état important.

La recette paramétrique et ses risques se trouvent dans `analysis.json`; la synthèse avec les trois autres tutoriels est dans `knowledge/tutorials/ANIMATION_WORKFLOW_PLAYBOOK.md`.
