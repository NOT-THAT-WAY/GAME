# Registre des assets, dépendances et licences

Ajouter une ligne avant l'import dans Unity. Stocker la preuve de licence dans l'emplacement privé convenu par l'équipe ; ne pas committer de facture ou donnée personnelle.

| ID | Asset / plugin | Source | Version/date | Licence | Lot DVC / sortie | Plateformes vérifiées | Preuve | Responsable | Statut |
|---|---|---|---|---|---|---|---|---|---|
| DEP-001 | FishNet | GitHub FirstGearGames | 4.7.2 | MIT | package Unity | Mac/Windows à tester | dépôt/release | équipe | intégré |
| DEP-002 | Unity URP | Unity Registry | 17.3.0 | Unity Companion | package Unity | Mac/Windows à tester | manifest | équipe | intégré |
| DEP-003 | Wwise | Audiokinetic | 2025.1.4 | à enregistrer selon budget/projet | `WwiseProject/` | gate Mac/Windows requise | portail projet | à attribuer | différé |
| TOOL-001 | DVC | Iterative | 3.x | Apache-2.0 | remote privé à choisir | Mac/Windows à tester | documentation officielle | Nils + Zak | préparé |
| ART-MAZE-001 | Labyrinthe 16x16 de test | création interne, `tools/maze-3d/build_maze.py` sous Blender 5.1 | grille seed 1704, 2026-08-04 | propriété de l'équipe | master `.blend` hors dépôt en attente du coffre DVC ; export `Assets/_Project/Maze/Maze16x16.fbx` (37 Mo, LFS) + `MazeGrid16x16.json` | macOS vérifié, Windows à vérifier | rendus de contrôle `Logs/MazePlaytest/` | Sean | prototype seulement |
| ART-PERSO-001 | Personnage espèce « boule » | création interne, `build_character.py` sous Blender 5.1 | 2026-08-04 | propriété de l'équipe | master `.blend` hors dépôt en attente du coffre DVC ; export `Assets/_Project/Player/PersoBoule.fbx` | macOS vérifié, Windows à vérifier | planche turnaround du dépôt de préproduction | Sean | prototype seulement |

Préfixes conseillés : `ART`, `AUD`, `NAR`, `UI`, `DEP`, `TOOL`. Le lot DVC d'un master suit `ExternalAssets/<Discipline>/<ID>/` ; la colonne indique aussi les exports Unity/Wwise.

Statuts : `proposé`, `claim`, `prototype seulement`, `validé`, `à remplacer`, `retiré`. Pendant un `claim`, l'issue liée précise le pilote et une échéance ; un claim expiré peut être repris après contact.
