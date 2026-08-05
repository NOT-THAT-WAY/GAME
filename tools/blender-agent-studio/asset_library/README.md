# Bibliothèque d’assets Blender

Ce dossier est une Asset Library native. L’enregistrement par défaut utilise le nom
`Blender Agent Studio` :

```bash
"${BLENDER_BIN:-/Applications/Blender.app/Contents/MacOS/Blender}" \
  --background --factory-startup \
  --python workflows/tools/register_asset_library.py
```

Le script modifie les préférences Blender uniquement lorsque l’utilisateur le lance explicitement.
Le nom peut être remplacé par `BLENDER_ASSET_LIBRARY_NAME`.

Utiliser **Link** pour conserver une source centrale en lecture seule, **Append** pour une copie
locale indépendante et **Append (Reuse Data)** pour éviter les doublons. Un Library Override est
réservé aux rigs liés qui doivent être édités localement.

Les sous-dossiers contiennent des assets historiques et génériques. Lire chaque manifeste pour la
provenance, les limites et le statut de redistribution.
