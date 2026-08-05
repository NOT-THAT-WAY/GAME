# Analyse — Creating Quick Animation in Blender 4.0

La vidéo montre un plan automobile construit très vite à partir d'assets existants. Le savoir fiable est l'ordre des opérations : terrain et route d'abord, véhicule et caméra très tôt, puis matières, végétation, bâtiment et atmosphère.

## Workflow visuel retenu

1. Bloquer le terrain et l'horizon en clay.
2. Réserver la route et son corridor de sécurité.
3. Importer et normaliser l'asset voiture.
4. Tester immédiatement trajectoire et caméra.
5. Poser les grandes zones de matière.
6. Distribuer la végétation en masses contrôlées, pas uniformément.
7. Ajouter un bâtiment seulement s'il renforce la profondeur ou la narration.
8. Ajouter poussière, suspension et micro-vibrations après validation du déplacement.
9. Gater séparément silhouette, collisions, densité du décor, vitesse et atmosphère.

## Important sur la preuve

L'audio ne contient pas de tutoriel parlé exploitable. La transcription automatique répétait un faux crédit et a été rejetée. Les étapes sont donc fondées sur les 138 frames régulières, 165 changements de scène et trois planches détaillées. L'ordre général est fiable; les valeurs exactes de nodes, modifiers, densité et simulation ne doivent pas être copiées comme si elles avaient été confirmées.

La recette paramétrique est dans `analysis.json` et dans `knowledge/tutorials/ANIMATION_WORKFLOW_PLAYBOOK.md`.
