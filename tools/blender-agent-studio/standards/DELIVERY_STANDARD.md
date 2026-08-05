# Standard de livraison

## Dépôt compact

Le dépôt Git contient règles, code, contrats, catalogues et preuves textuelles. Il ne contient aucun
`.blend`, rendu, texture, vidéo, audio, cache ou export 3D. Ces fichiers vivent dans `local_assets/`
ou `local_work/`, tous deux ignorés par Git.

## Manifeste

Chaque fichier livré possède chemin relatif, rôle, version, taille, SHA‑256, format, profil d’export,
source et statut de validation. Le manifeste distingue :

- source maître ;
- fichier de travail ;
- export candidat ;
- export réimporté et validé ;
- preview ou preuve visuelle ;
- cache régénérable.

## Rôles minimaux par type

Les noms ci-dessous sont ceux attendus par `validate_team_project.py` :

| Type | Rôles obligatoires |
|---|---|
| `asset` | `master_blend`, `preview`, `export`, `reimport_evidence` |
| `game-asset` | `master_blend`, `export`, `target_engine_import` |
| `rig` | `master_blend`, `rig_audit`, `deformation_preview` |
| `animation` | `master_blend`, `playblast`, `clip_manifest`, `reimport_evidence` |
| `environment` | `master_blend`, `performance_report`, `target_engine_import` |
| `cinematic` | `master_blend`, `preview`, `media_probe` |
| `still` | `master_blend`, `final_render`, `render_settings` |
| `procedural` | `master_blend`, `procedural_manifest`, `performance_report` |

Un rôle peut pointer vers un fichier binaire de `local_work/` ou une preuve textuelle versionnée.
Tous sont hashés ; le statut `validated` n’est posé qu’après le contrôle métier correspondant.

## Validation cible

Un export est ouvert dans un contexte indépendant. Pour un jeu, importer dans le moteur et relever
warnings, échelle, axes, matériaux, LOD, collisions, rig et clips. Pour une vidéo, utiliser un lecteur
et `ffprobe`. Pour un asset Blender, ouvrir avec auto-exécution désactivée et vérifier les dépendances.

## Publication

Vérifier droits, secrets, chemins personnels, taille et hashes. Exécuter
`tools/check_distribution_budget.py` et les tests. Publier les packs binaires séparément avec version
et manifeste ; ne jamais les pousser dans l’historique du dépôt compact.
