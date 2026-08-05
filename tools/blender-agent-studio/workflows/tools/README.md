# Outils de production

## Points d’entrée génériques

- `studio_readiness_check.py` : diagnostic de machine et de dépôt, sans mutation ;
- `create_team_project.py` / `validate_team_project.py` : pipeline principal pour les huit types ;
- `build_delivery_manifest.py` : hashes et rôles des livrables locaux ;
- `create_scene_trial.py` / `validate_scene_trial.py` : compatibilité pour une scène/film isolé ;
- `create_asset_build.py` / `validate_asset_build.py` : compatibilité pour un asset isolé ;
- `register_asset_library.py` : enregistrement explicite d’une bibliothèque matérialisée localement.

Ces outils sont les choix par défaut d’un nouveau projet. Les opérations interactives allowlistées
se trouvent dans `workflows/scripts/` et leur contrat machine dans `workflows/catalog/`.

## Constructeurs historiques ou spécialisés

Les fichiers portant `kimi`, `pulsed`, `fl_studio`, `golem`, `gameboii`, `mecha`, `drumboii` ou le
nom d’une campagne reproduisent une production déterminée. Ils restent versionnés pour leurs
techniques, tests et décisions, mais peuvent supposer des collections, médias ou contrats propres
à ce cas. Inspecter leur source et leurs entrées avant exécution ; ne pas les traiter comme API
générique.

`create_kimi_scene_trial.py`, `validate_kimi_scene_trial.py` et `kimi_readiness_check.py` sont des
wrappers de compatibilité. Les nouveaux travaux utilisent `create_team_project.py` et le préfixe
`BAS_`. Un script historique qui pointe vers un binaire absent doit être étudié, pas lancé pour
tester le clone compact.
