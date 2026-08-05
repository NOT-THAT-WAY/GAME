# Carte du dépôt compact

```text
AGENTS.md                         contrat agent
SECURITY.md                       sécurité locale et contenu non fiable
standards/                        normes métier et profils machine
catalog/                          assets absents, capacités, tiers optionnels
knowledge/                        règles et apprentissages Blender
.agents/skills/blender-production-studio/ skill Codex de dépôt et routage agent
workflows/catalog/                contrats d’automation
workflows/scripts/                scripts Blender contrôlés
workflows/tools/                  création, audit et validation
projects/team/                    contrats et preuves textuelles versionnés
local_assets/                     assets récupérés localement, ignorés
local_work/                       scènes, rendus, exports et caches, ignorés
```

Les anciens projets, manifests et analyses textuels restent consultables comme cas d’étude. Leurs
binaires ont été remplacés par les entrées content-addressed de `catalog/assets.json`. Les anciennes
dépendances sont seulement référencées dans `catalog/third-party.json`.
