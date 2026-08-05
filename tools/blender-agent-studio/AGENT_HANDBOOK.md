# Manuel du studio Blender d’équipe

## Démarrer

1. Exécuter `python3 tools/bootstrap.py --configure`.
2. Exécuter `python3 workflows/tools/studio_readiness_check.py`.
3. Lire `AGENTS.md` et le standard du domaine.
4. Chercher les références dans `catalog/assets.json`, jamais dans des chemins supposés.
5. Créer un contrat de projet avant d’ouvrir ou modifier Blender.

Exemple :

```bash
python3 workflows/tools/create_team_project.py \
  --id forest-props-v001 \
  --type game-asset \
  --objective "Kit de props forestiers modulaire et performant" \
  --target "Godot, desktop" \
  --profile game-godot
```

Les contrats sont suivis dans `projects/team/forest-props-v001/`. Les `.blend`, textures, previews
et exports vont dans `local_work/forest-props-v001/` et ne quittent pas la machine par Git.

## Choisir le mode d’exécution

- **Lecture seule** : audit, inventaire, diagnostic, bounds, dépendances.
- **MCP interactif** : petite modification visible dans une copie de travail ouverte.
- **Batch isolé** : génération, conversion, validation longue ou départ depuis une scène vide.
- **Application locale** : lancement de workflows MCP allowlistés, jamais de Python libre.

Le JSON du workflow décide du mode, de la confirmation, de la mutation et du niveau de preuve.

## Utiliser un asset du coffre

Rechercher par chemin, rôle ou métadonnées dans `catalog/assets.json`. Puis matérialiser un contenu
unique :

```bash
python3 tools/search_assets.py "wood roughness" --kind image --limit 20

python3 tools/materialize_assets.py \
  --source-vault "$BLENDER_ASSET_VAULT" \
  --asset-id <préfixe-sha256> \
  --confirm-rights
```

Le fichier arrive sous `local_assets/` avec un manifeste de vérification. Linker ou copier ensuite
explicitement vers le workspace du projet. Ne jamais committer le fichier.

## Parcours asset et jeu

Définir fonction, échelle, silhouette, pièces, pivots et interactions. Valider le blockout, puis
topologie, normales, UV, matériaux et collisions. Pour le temps réel, déclarer budgets LOD,
textures, materials, bones et colliders. Importer l’export dans le moteur cible et consigner les
warnings et mesures ; une réouverture dans Blender ne suffit pas.

## Parcours rig et animation

Auditer le squelette et la bind pose. Tester poids, axes, limites et poses extrêmes. Définir chaque
clip, fps, root motion, boucle, événements et sampling. Mesurer contacts et continuité frame par
frame. Livrer playblast, contact sheet et réimport des clips bakés.

## Parcours environnement et procédural

Définir grille, navigation, kit modulaire, collisions et budgets par zone. Figer seeds et versions
de node groups. Tester exclusions de scatter, LOD/culling, éclairage et performance dans la cible.
Les caches et bakes restent locaux, référencés par hash.

## Parcours cinématique et rendu

Écrire l’intention causale du plan. Bloquer géométrie et poses en clay, puis caméra, focus, monde,
lumière par couches et matériaux. Vérifier tout le mouvement, pas seulement des hero frames.
Contrôler la sortie avec contact sheet et `ffprobe`.

## Enregistrer une livraison

Ajouter les fichiers locaux au manifeste sans les mettre dans Git :

```bash
python3 workflows/tools/build_delivery_manifest.py \
  projects/team/forest-props-v001 \
  --file master_blend=local_work/forest-props-v001/work/asset.blend \
  --file export=local_work/forest-props-v001/exports/forest-props.glb \
  --validated
```

N’utiliser `--validated` qu’après le contrôle du rôle. Compléter les gates, la validation cible,
les droits, passer `project.json` à `reviewed` ou `released` et terminer `FINAL_REVIEW.md`, puis :

```bash
python3 workflows/tools/validate_team_project.py \
  projects/team/forest-props-v001 --stage final
```

## Ce qu’un verdict doit dire

Rapporter séparément : package, validité technique, validité physique/fonctionnelle, qualité
visuelle, performance cible, statut d’import et décision humaine. Citer les preuves et limites.
