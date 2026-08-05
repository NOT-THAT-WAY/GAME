# Blender Team Studio app

Interface locale optionnelle pour parcourir projets, scènes, catalogue JSON, bibliothèques,
tutoriels, connaissances et workflows contrôlés. Les cartes cataloguées restent visibles sans leur
binaire et indiquent qu’une matérialisation locale est nécessaire.

```bash
python3 ../tools/bootstrap.py --configure
docker compose -f compose.yml up --build -d
curl http://127.0.0.1:8778/api/health
```

Le bootstrap écrit `app/.env`, ignoré par Git. Le service n’écoute que sur `127.0.0.1:8778` et
rejoint Blender natif via `host.docker.internal:9876`. Il n’accepte aucun Python libre, refuse les
workflows batch et désactivés, et exige une confirmation pour les mutations.

Le coffre indiqué par `BLENDER_ASSET_VAULT` n’est jamais monté ni copié automatiquement. Les assets
sont récupérés explicitement avec `tools/materialize_assets.py`.

Le wrapper macOS peut être construit avec `./build-macos-app.sh`. L’option `--install` remplace
explicitement l’application locale ; elle n’est donc pas lancée par défaut.
