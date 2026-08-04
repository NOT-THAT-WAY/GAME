# ADR 0003 — Sources, exports, données et caches

**Statut : accepté — 2026-08-04**

## Décision

Le dépôt GitHub contient le code, les réglages, les scènes, les métadonnées Unity, la documentation et les exports nécessaires au build. Les binaires de livraison autorisés passent par Git LFS.

Les masters éditables et lourds vivent sous `ExternalAssets/` dans les espaces de travail locaux. DVC enregistre dans Git un pointeur par lot d'asset et stocke le contenu dans un remote privé indépendant de GitHub. Les lots sont petits et orientés feature, par exemple `ExternalAssets/Art/PivotDoor` ou `ExternalAssets/Audio/PivotEffort`, afin que chacun ne synchronise que ce dont il a besoin et que deux disciplines ne modifient pas le même pointeur.

Les caches, builds, logs et données temporaires sont reconstruits localement et ne sont jamais partagés. Les secrets, factures, contrats nominatifs et données de playtest identifiantes vivent dans des outils dédiés ; le dépôt ne conserve qu'un identifiant ou un lien non sensible.

## Conséquences

- cloner Git ne télécharge pas les masters lourds ; `dvc pull` les hydrate à la demande ;
- une PR d'asset contient le pointeur `.dvc`, le registre de provenance et les exports Unity, mais pas le master ;
- le remote DVC doit activer le versioning objet et posséder une sauvegarde séparée ; DVC n'est pas une sauvegarde à lui seul ;
- chaque membre utilise son propre compte et ses propres credentials, stockés localement ;
- le même lot d'asset n'a qu'un éditeur déclaré à la fois.

## Options écartées maintenant

- tous les masters dans Git LFS : quotas GitHub, clones lourds et verrouillage peu adapté à la croissance ;
- dossier Dropbox/Drive synchronisé comme projet Unity : risques de conflits silencieux et de corruption des fichiers générés ;
- un unique gros dossier DVC : chaque modification ferait entrer les trois disciplines en conflit sur le même pointeur.
