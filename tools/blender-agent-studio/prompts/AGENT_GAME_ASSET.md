# Prompt — asset temps réel

Utilise `$blender-production-studio`, lis `AGENTS.md` et `standards/GAME_ASSET_STANDARD.md`.

Asset et gameplay : `<FONCTION>` ; moteur/version/plateforme : `<CIBLE>`

Échelle/axes/pivot : `<CONTRAT>` ; formats : `<FORMATS>`

Budgets LOD, materials, textures, bones et colliders : `<BUDGETS>`

Crée un projet `game-asset` avec le profil `<game-gltf|game-unity|game-unreal|game-godot>`.
Déclare silhouette par distance, UV/lightmap, tangentes, collision, LOD/Nanite, squelette et clips
applicables. Ne déduis aucun budget du style visuel.

Après l’audit Blender et le round-trip, importe dans la version exacte du moteur. Mesure échelle,
orientation, pivot, materials, collisions, animations, warnings et coût. Le rapport d’import cible
est obligatoire pour valider.
