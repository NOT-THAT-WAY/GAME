# Veille GitHub — workflows Blender pilotés par agent

État: 19 juillet 2026. Cette veille compare les dépôts à l'architecture locale de Blender
Studio. Un dépôt découvert n'est jamais installé directement dans le poste de production:
les patterns utiles sont adaptés derrière les workflows allowlistés et testés sur une copie.

## Résultat principal

Le dépôt le plus proche de la cible n'est pas le Blender MCP officiel mais
[`PatrykIti/blender-ai-mcp`](https://github.com/PatrykIti/blender-ai-mcp) (Apache-2.0). Il combine:

- objectif persistant et routing guidé;
- références attachées au goal;
- comparaison et itération par checkpoint;
- analyse de silhouette et hints d'action typés;
- diagnostic caméra en espace image: couverture, centrage, visibilité et hors-cadre;
- graphes de scope et de relations entre objets;
- macros bornées pour proportions, symétrie, contact et intersections;
- escalade automatique vers inspection/validation lorsqu'une correction se répète;
- gates proposés par le modèle mais validés par des preuves Blender déterministes.

Ce dernier point est la règle la plus importante à reprendre: la vision propose un diagnostic;
la scène, les mesures, le mesh et les assertions restent l'autorité pour réussir un gate.

## Comparaison

| Dépôt | Forces | Limites / risque | Décision locale |
|---|---|---|---|
| [`ahujasid/blender-mcp`](https://github.com/ahujasid/blender-mcp) | Bridge simple, screenshot, `bpy`, Poly Haven, Sketchfab | `execute_code` arbitraire; peu de workflow métier | Conserver comme transport vendored |
| [`PatrykIti/blender-ai-mcp`](https://github.com/PatrykIti/blender-ai-mcp) | Boucle guidée et vérification la plus complète | Architecture beaucoup plus large; providers vision externes; intégration invasive | Adapter ses contrats et diagnostics, ne pas remplacer le bridge immédiatement |
| [`sandraschi/blender-mcp`](https://github.com/sandraschi/blender-mcp) | 40+ outils, mode headless, dashboard, matériaux, lighting, render, export, repository | Surface très large, seulement 22 stars au contrôle, maturité à confirmer par tests ciblés | Étudier ses presets lighting/material et fallback headless |
| [`elasticdotventures/blender-agent-tools`](https://github.com/elasticdotventures/blender-agent-tools) | Docker, dashboard, vision/LangChain exploratoires | Se déclare WIP et instable | Inspiration seulement |
| [`lastmile-ai/mcp-agent`](https://github.com/lastmile-ai/mcp-agent) | Patterns d'agents MCP composables | Pas spécifique à Blender | Candidat futur pour orchestration externe |

## Patterns à adapter dans Blender Studio

### Priorité 1 — diagnostic caméra déterministe

Ajouter un workflow read-only calculant, pour chaque caméra et objet cible:

- bounding box projetée dans l'image;
- pourcentage de couverture;
- offset du centre;
- verdict `visible`, `partial`, `occluded` ou `off-frame`;
- clipping near/far;
- frame et focale utilisées.

Ce diagnostic doit précéder toute correction de cadrage par vision. Il évite de demander au
modèle d'estimer en pixels une information que Blender peut calculer exactement.

### Priorité 2 — état d'itération structuré

Créer un manifeste par boucle:

```json
{
  "goal": "...",
  "immutable": ["proportions", "logo", "ports"],
  "active_category": "composition",
  "attempt": 1,
  "max_attempts": 3,
  "evidence": [],
  "disposition": "continue_build"
}
```

Après trois actions sans amélioration: `inspect_validate`. Si la prochaine action dépend du
goût ou menace un invariant: `human_review`.

### Priorité 3 — graphe spatial minimal

Produire un JSON read-only avec parenté, collections, bounds, distances, contacts approximatifs,
symétries déclarées et rôles `core/accessory/control/reference`. L'agent doit consulter ce graphe
après toute modification géométrique importante au lieu de déduire la structure depuis les noms.

### Priorité 4 — presets contrôlés

Étudier dans `sandraschi/blender-mcp` les presets de matériaux, lighting rigs, turntables et
fallback headless. Ne reprendre que des recettes paramétrées, compatibles Blender 5.1 et couvertes
par les smoke tests locaux.

## Ce qui ne doit pas être repris tel quel

- installation automatique d'un fork MCP au-dessus du bridge vendored;
- providers vision ou clés externes activés par défaut;
- textarea ou endpoint Python libre;
- validation visuelle considérée comme preuve de dimensions/topologie;
- centaines d'outils visibles simultanément sans routing ni allowlist;
- sauvegarde silencieuse de la scène principale.

## État d'implémentation local

1. `scene-view-diagnostics` read-only — implémenté et testé Blender 5.1;
2. manifeste d'itération et dispositions d'arrêt — implémenté et testé;
3. graphe spatial read-only — implémenté et testé;
4. presets studio lighting — implémentés et testés;
5. presets matériaux — à étudier sans altérer les matériaux canoniques;
6. boucle preview automatique — seulement après validation en production des quatre premières couches.

Cette progression apporte l'essentiel des dépôts avancés tout en conservant le transport,
l'interface, les gates et les règles de sécurité déjà validés localement.
