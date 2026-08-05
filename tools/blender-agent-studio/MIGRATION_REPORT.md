# Rapport de migration — Visual AI Hub vers Blender

> Archive de provenance. Ce rapport décrit la migration historique du 18 juillet 2026 ; il ne
> configure pas Blender Team Studio et ses noms/chemins ne sont pas des defaults actifs. Les
> binaires décrits ci-dessous ne sont plus embarqués : `catalog/assets.json` les représente.

Date: 18 juillet 2026.

## Périmètre audité

- `_Visual_AI_Hub/assets/assets_blender`;
- `_Visual_AI_Hub/audits_blender`;
- `_Visual_AI_Hub/unrecorded-marketing/blender-choreography`;
- `_Visual_AI_Hub/unrecorded-marketing/reel-blender`;
- application `unrecorded-studio` (FastAPI, Docker, wrapper Swift);
- projet cible et trois fichiers `.blend`;
- addon et config Blender MCP;
- historique des gates, likes, notes, métadonnées, coûts et prompts.

## Données exportées

La migration est une fusion sans suppression:

- `assets_blender/`: canoniques, close-ups, review v2, runs de génération et itérations rejetées;
- `library/blender-choreography/`: 474 Mo, shots, scripts, boards, keyframes et previews;
- `library/reel-blender/`: 50 Mo, quatre runs Seedance et le test de scène Nano-Banana;
- `audits/`: préflight, prompts anti-drift, object map et plan de build existant.

Le dossier cible pesait environ 424 Mo avant fusion et environ 1,5 Go après export. Les fichiers
existants ont été conservés; aucun `.blend` ni export n’a été remplacé.

## Projet Blender reconstruit

`Pulsed_3D_model.blend` est valide sous Blender 5.1.1:

- scène active `FLROOM`;
- 24 objets;
- 9 matériaux;
- 3 caméras FLROOM;
- frames 1–240 à 24 fps;
- rendu 1280×720;
- collection produit `PULSED`, références `REFS` et animations existantes.

Le backup daté du 10 juin ne contient que la scène Blender par défaut; il ne doit pas être pris
pour le projet courant.

## MCP

La config `uvx blender-mcp` était fonctionnelle. L’addon local correspondait à une révision
antérieure. Il a été sauvegardé dans `backups/addons/` puis remplacé sur disque par le snapshot
officiel du commit `6641189231caf3752302ae20591bc87fda85fc4e` (package 1.6.0). Le snapshot et son
hash sont dans `vendor/blender-mcp/VERSION.json`. Le processus Blender déjà ouvert n’a pas été
rechargé de force; la mise à jour s’active au prochain lancement.

Projet officiel: https://github.com/ahujasid/blender-mcp

## Décisions produit

- port distinct `8778` pour ne pas entrer en conflit avec Unrecorded Studio sur `8777`;
- app native macOS, pas simple onglet de navigateur;
- Docker loopback-only;
- assets et runs indexés depuis le dossier Blender autonome;
- tous les runs visibles avec tri et filtres;
- workflows allowlistés, jamais de code Python envoyé depuis un textarea;
- Blender natif pour UI/Metal, Docker pour l’orchestration;
- sorties no-overwrite par job;
- documentation des échecs conservée comme connaissance exploitable.

## Asset Library native

`asset_library/products/pulsed-assets.blend` a été construit comme copie indépendante et
enregistré dans les préférences Blender sous `Unrecorded Blender`. Il expose 8 assets:
la collection `PULSED`, six matériaux `M_*` et le world `flroom_world`, rangés dans trois
catalogues. La source `Pulsed_3D_model.blend` n’a pas été modifiée pendant cette opération.
