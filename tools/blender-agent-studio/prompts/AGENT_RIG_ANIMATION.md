# Prompt — rig, articulation ou animation

Utilise `$blender-production-studio`, lis `AGENTS.md` et `standards/RIG_ANIMATION_STANDARD.md`.

Type : `<rig|animation>` ; fonction/action : `<OBJECTIF>`

Squelette ou pièces : `<STRUCTURE>` ; cible/version : `<CIBLE>`

FPS, clips, root motion, boucles et événements : `<CONTRAT_ANIMATION>`

Crée le projet et inspecte hiérarchie, bind pose, axes, pivots et topologie avant toute clé. Déclare
limites mécaniques, influences, sampling et politique de bake. Teste les poids et déformations aux
extrêmes. Pour une interaction, mesure les contacts sur meshes évalués à chaque frame pertinente.

Livre audits squelette/poids, clip manifest, playblast, contrôle de seam/root motion et réimport des
clips bakés. Foot sliding, interpenetration ou articulation impossible est un échec critique.
