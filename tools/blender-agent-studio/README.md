# Blender Team Studio

Un dépôt Blender léger et clonable pour une équipe : règles de production, agents, scripts,
contrats, validations et connaissance issue de projets réels — sans transporter plusieurs gigaoctets
d’assets.

Il couvre :

- génération et modélisation d’assets ;
- props et personnages game-ready pour Unity, Unreal, Godot ou glTF ;
- rigging, articulation, clips, boucles et root motion ;
- environnements modulaires, scatter et Geometry Nodes ;
- matériaux, textures et lookdev ;
- animation, caméra, lumière, rendu, stills et cinématiques ;
- audit, optimisation, export, réimport et livraison.

## Clone léger

```bash
git clone https://github.com/NOT-THAT-WAY/blender-agent-studio.git blender-team-studio
cd blender-team-studio
python3 tools/bootstrap.py --configure
python3 workflows/tools/studio_readiness_check.py
```

En ouvrant le clone comme workspace Codex, `AGENTS.md` et le skill
`$blender-production-studio` sont découverts automatiquement depuis `.agents/skills/`. Aucune
installation globale du skill n'est nécessaire. Le bootstrap est une initialisation locale à lancer
une fois par machine : il détecte Blender et écrit uniquement des fichiers de configuration ignorés
par Git.

Git LFS et les sous-modules ne sont pas requis. Le budget du dépôt est plafonné à 50 Mio et les
extensions binaires sont refusées par `tools/check_distribution_budget.py`.

## Assets sans les envoyer

`catalog/assets.json` décrit 12 115 contenus uniques et 12 251 chemins par SHA‑256, taille, rôle,
métadonnées et provenance. Les 7,82 Go correspondants restent dans un coffre privé. Un membre qui
a accès au coffre peut récupérer uniquement ce dont il a besoin dans `local_assets/`, dossier ignoré
par Git.

Voir `catalog/README.md` et vérifier avec :

```bash
python3 tools/search_assets.py "chair side" --kind image
python3 tools/verify_asset_catalog.py
```

## Premier projet

```bash
python3 workflows/tools/create_team_project.py \
  --id hero-robot-v001 \
  --type game-asset \
  --objective "Robot jouable lisible en vue troisième personne" \
  --target "Unreal Engine, PC" \
  --profile game-unreal
```

Les contrats légers sont versionnés dans `projects/team/hero-robot-v001/`. Tous les binaires de
production restent dans `local_work/hero-robot-v001/`.

## Points d’entrée

| Emplacement | Rôle |
|---|---|
| `AGENTS.md` | règles non négociables |
| `SECURITY.md` | frontières BlenderMCP, auto-exécution et secrets |
| `standards/` | normes asset, jeu, animation, rendu, environnement et livraison |
| `catalog/capabilities.json` | capacités et maturité des automations |
| `catalog/assets.json` | inventaire content-addressed des assets non embarqués |
| `knowledge/` | apprentissages Blender et profils artistiques |
| `workflows/catalog/` | contrats machine des opérations Blender |
| `workflows/scripts/` | automations allowlistées |
| `workflows/tools/` | scaffolds, validateurs et utilitaires |
| `.agents/skills/blender-production-studio/` | skill Codex de dépôt, découvert automatiquement |
| `projects/team/` | contrats et preuves textuelles des projets d’équipe |
| `local_assets/`, `local_work/` | fichiers lourds locaux, jamais versionnés |

La direction Drumboiii reste disponible comme profil artistique. Le défaut est
`neutral-production`; fonction, performance et cible passent toujours avant le style.
