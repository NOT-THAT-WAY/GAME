# Lire les cas d’étude historiques

Les dossiers historiques conservent des scripts, manifests, analyses et décisions qui ont servi à
construire la méthode. Leurs binaires ne sont pas inclus ; ils sont décrits dans `catalog/assets.json`.

Pour un nouveau travail, partir de `AGENTS.md`, `standards/`, `knowledge/`, `workflows/` et
`projects/team/`. Les autres projets sont des exemples, jamais des defaults.

Les préfixes, noms de marques, chemins tokenisés et styles propres à une ancienne campagne sont de
la provenance. Un script historique peut donc être non exécutable sans adaptation. Ne pas remplacer
ses jetons automatiquement : inspecter, copier la technique utile dans un workflow générique et
tester sur une scène isolée.

Un ancien score ou `package_valid: true` ne prouve que son schéma d’époque. Toute réutilisation doit
repasser les gates actuels, les droits et la validation de cible.
