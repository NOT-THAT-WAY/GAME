# Prompt — vérifier un clone

Utilise `$blender-production-studio`. Reste en lecture seule et n’ouvre aucun fichier externe avec
auto-exécution.

1. Exécute `python3 tools/bootstrap.py`.
2. Exécute `python3 workflows/tools/studio_readiness_check.py`.
3. Vérifie les JSON, le catalogue, les profils, les scripts, les chemins personnels, les liens
   symboliques, l’absence de sous-module/LFS/binaire et le budget de 50 Mio.
4. Si Blender est disponible, lance `app/tests/smoke_blender.sh` sur sa fixture synthétique.
5. Rapporte séparément le cœur, Blender batch, animation/vidéo, MCP et coffre optionnel.

N’installe, ne publie, ne matérialise et ne modifie rien sans demande explicite.
