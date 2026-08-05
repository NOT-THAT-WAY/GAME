# Bien démarrer en équipe

## Prérequis

Python 3.11+, Blender 4.3+ ou la version déclarée par le projet, Git et FFmpeg/ffprobe pour les
travaux animés. Blender 5.1.1 est la version de référence des smoke tests actuels.

Si Blender n’est pas dans le `PATH`, définir `BLENDER_BIN` vers son exécutable. Le cœur catalogue et
contrats fonctionne sans FFmpeg ; les tutoriels, playblasts et validations vidéo l’exigent.

```bash
python3 tools/bootstrap.py --configure
python3 workflows/tools/studio_readiness_check.py
python3 tools/verify_asset_catalog.py
python3 tools/check_distribution_budget.py
```

Le rapport distingue `ready_core`, `ready_for_blender_batch`, `ready_for_animation_media` et
`ready_for_interactive_mcp` afin qu’un composant optionnel ne soit pas confondu avec un dépôt cassé.

## Vérifier Blender sans asset privé

Sur macOS ou un shell zsh compatible :

```bash
app/tests/smoke_blender.sh
```

Le script crée sa propre fixture temporaire et ne sauvegarde rien dans le dépôt. Sur une autre
plateforme, reprendre les mêmes appels Blender batch ou exécuter les tests dans la CI de la station.

## MCP interactif optionnel

Installer `blender_mcp_addon.py` depuis les préférences Blender, démarrer son serveur local, puis
connecter le client MCP à `127.0.0.1:9876`. Lire `SECURITY.md` avant : ce canal peut exécuter du
Python et ne doit jamais être exposé au réseau. Les workflows batch restent lancés hors MCP.
La configuration Codex du dépôt épingle `blender-mcp==1.6.0` et Python 3.11 ; l’addon fourni porte
le même hash que le snapshot documenté dans `vendor/blender-mcp/VERSION.json`.

## Travailler avec un agent

```text
Utilise $blender-production-studio. Lis AGENTS.md et le standard du domaine.
Crée un projet d’équipe isolé, déclare la cible et les budgets, puis travaille uniquement
dans local_work. Ne mets aucun binaire dans Git.
```

## Types disponibles

`asset`, `game-asset`, `rig`, `animation`, `environment`, `cinematic`, `still` et `procedural`.
Les profils de `standards/profiles/` fixent les gates, jamais les budgets spécifiques du projet.

## Accès au coffre optionnel

Définir localement, sans committer :

```bash
export BLENDER_ASSET_VAULT=/chemin/vers/le/coffre
```

Le dépôt reste entièrement utilisable sans le coffre pour créer de nouveaux contenus. Le coffre
sert uniquement à réutiliser des sources existantes répertoriées dans le catalogue.

## Skill agent

`.agents/skills/blender-production-studio/` est un skill de dépôt validé. Codex le découvre
automatiquement lorsqu'il est lancé depuis le clone ou l'un de ses sous-dossiers : aucune copie
vers un dossier utilisateur et aucune installation globale ne sont nécessaires. Démarrer une
nouvelle session Codex si le workspace était déjà ouvert avant le clonage. `AGENTS.md` est également
chargé automatiquement ; le skill ajoute le routage et le chargement progressif des références.
