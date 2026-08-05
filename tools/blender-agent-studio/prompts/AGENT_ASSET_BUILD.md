# Prompt — asset Blender réutilisable

Utilise `$blender-production-studio`, lis `AGENTS.md` et applique le profil `asset-general`.

Objectif/fonction : `<OBJECTIF>`

Usage et distance d’observation : `<USAGE>`

Dimensions et unités : `<DIMENSIONS>` ; cible/formats : `<CIBLE_ET_FORMATS>`

Références catalogue : `<ASSET_IDS_OU_AUCUNE>` ; invariants : `<IDENTITE_ET_FONCTION>`

Crée un projet `asset` avec `create_team_project.py`. Audite les références avant de construire.
Déclare pièces, matériaux, supports, interactions, pivots, axes, topologie, UV et budgets. Travaille
seulement dans `local_work/`, de façon non destructive et avec le préfixe du projet.

Valide en clay puis sur mesh évalué : silhouette, dimensions, identité, fonction, normales,
topologie, UV, matériaux, pivot et dépendances. Produis les vues d’identité, exporte, réimporte dans
un processus indépendant, hash les livrables et complète la revue humaine. Aucun beau rendu ne
remplace l’audit de l’asset.
