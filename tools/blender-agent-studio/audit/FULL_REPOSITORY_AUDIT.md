# Audit du corpus source — provenance

Date : 4 août 2026. Ce document résume l’audit en lecture seule du corpus complet avant sa
compaction. Pour l’état distribuable actuel, lire `COMPACT_REPOSITORY_AUDIT.md`.

## Corpus observé

- environ 7,7 Go, 14 178 fichiers et 826 dossiers ;
- 45 `.blend` et 32 sauvegardes `.blend1` ;
- 9 423 PNG, 2 637 JPEG, 166 MP4, 656 Python, 524 JSON et 205 Markdown ;
- quatre dépôts Git imbriqués et aucun dépôt racine à l’origine ;
- environ 814 Mo de doublons détectés par contenu ;
- 18 contrats d’automation et de nombreux projets/cas d’étude.

Les 45 `.blend` ont été ouverts en batch avec Blender 5.1.1 et auto-exécution désactivée : 45/45
ouverts, aucune bibliothèque liée ou référence média manquante observée. Cela prouve l’ouverture,
pas la qualité physique ou artistique.

## Connaissance transférable retenue

- priorité à l’identité, la fonction réelle, les supports, contacts et collisions ;
- séparation package / physique / technique / visuel / goût humain ;
- blockout et gates avant lumière et polish ;
- comparaison A/B et correction d’une catégorie à la fois ;
- caméra/target/focus séparés, états de mouvement et validation de tout le clip ;
- lumière par couches et HDRI distinct du ciel visible ;
- tutoriel transformé en preuves, transcript, analyse et recette validable ;
- asset validé indépendamment de sa scène de présentation.

## Écarts corrigés dans la copie compacte

Le corpus mélangeait chemins machine, projets personnels, binaires massifs, opérations historiques
exposées comme génériques et niveaux de preuve parfois trop optimistes. La copie compacte :

- remplace les 7,82 Go logiques par un catalogue content-addressed vérifié ;
- interdit binaires, LFS, sous-modules et liens symboliques ;
- généralise les normes pour assets, jeux, rig, animation, environnements, procédural et rendu ;
- sépare contrats Git et production locale ;
- marque les automations historiques ou expérimentales ;
- fournit fixtures, tests, profils cibles et import moteur obligatoire.

## Limites

Le catalogue ne transfère aucun droit. Les validations historiques ne sont pas automatiquement
promues au schéma actuel. Une licence racine doit être choisie avant publication publique et les
droits restent à revoir dans `content-rights.json`.
