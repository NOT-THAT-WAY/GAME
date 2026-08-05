# Architecture de Blender Team Studio

Le dépôt sépare volontairement la méthode partageable des fichiers de production lourds.

```text
Git compact
├── règles, standards, connaissances et prompts
├── catalogue JSON content-addressed
├── scripts Blender et contrats de workflows
└── contrats/proofs textuels de projets

Machine de chaque membre
├── coffre d’assets optionnel → local_assets/ (ignoré)
├── scènes, textures, caches, rendus → local_work/ (ignoré)
└── Blender natif
    ├── batch isolé
    └── MCP interactif optionnel sur localhost
```

## Frontières de confiance

- Le catalogue décrit un asset absent ; sa présence n’est jamais supposée.
- Une matérialisation vérifie le SHA-256 et exige une confirmation de droits.
- L’application n’accepte pas de Python libre et ne lance que les workflows MCP explicitement
  allowlistés.
- Un workflow batch ne s’exécute jamais dans la scène MCP active.
- Les API locales et BlenderMCP restent sur loopback ; elles ne sont pas exposées au LAN.
- Aucun workflow interactif ne sauvegarde silencieusement.
- Les binaires ne sont jamais suivis par Git, ni via LFS, ni via sous-module.

## Modes d’exécution

- **Lecture seule** : inventaire, diagnostic, dépendances, bounds et contrats.
- **MCP interactif** : opération courte et visible dans une copie de travail ouverte.
- **Batch isolé** : génération, conversion, rendu long et tests reproductibles avec
  `--factory-startup` et `--disable-autoexec` lorsque possible.
- **Hors Blender** : scaffolds, catalogues, manifests, hashes, probes et contrôle de distribution.

## Unité de travail

`workflows/tools/create_team_project.py` crée deux espaces liés par un identifiant :

- `projects/team/<id>/` : brief, contrat, gates, hashes et revue versionnés ;
- `local_work/<id>/` : sources, `.blend`, références, exports et rendus locaux.

Les profils de `standards/profiles/` déterminent les gates du type `asset`, `game-asset`, `rig`,
`animation`, `environment`, `procedural`, `cinematic` ou `still`.

## Ajouter une automation

1. Écrire un script borné dans `workflows/scripts/`.
2. Accepter des paramètres structurés et un dossier de sortie déclaré.
3. Ajouter son contrat JSON dans `workflows/catalog/` avec mutation, mode, confirmation, domaine,
   maturité et niveau de preuve.
4. Restaurer les états temporaires et ne jamais sauvegarder implicitement.
5. Produire un résultat JSON et les preuves nécessaires.
6. Tester sur une fixture synthétique, puis sur une copie réelle.
7. Pour un export, réimporter indépendamment et tester aussi dans la cible déclarée.
