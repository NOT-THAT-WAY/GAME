# Prompt — environnement ou génération procédurale

Utilise `$blender-production-studio`, lis `AGENTS.md` et
`standards/ENVIRONMENT_PROCEDURAL_STANDARD.md`.

Type : `<environment|procedural>` ; usage/cible : `<JEU_FILM_STILL_ET_VERSION>`

Échelle/grille/navigation : `<CONTRAT_SPATIAL>` ; budgets par zone : `<BUDGETS>`

Kit, biomes, seeds et règles de scatter : `<SYSTEME>`

Crée le projet avec le profil `environment`. Valide d’abord grille, modularité, parcours, supports et
collisions. Versionne les node groups, expose leurs inputs, fige les seeds et déclare quand les
instances sont réalisées ou bakées. Les exclusions gameplay/caméra sont des gates.

Contrôle z-fighting, LOD/HLOD, culling, lumières, materials, draw calls, mémoire et navigation dans
la cible. Livre audit environnement, rapport de performance et preuve d’import ; les caches lourds
restent locaux et sont référencés par hash.
