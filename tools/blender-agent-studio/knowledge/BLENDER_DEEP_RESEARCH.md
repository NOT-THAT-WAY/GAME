# Recherche — Blender, assets, caméra, animation et MCP

État de la recherche: 19 juillet 2026. Priorité donnée aux manuels Blender, à l’API Blender,
à FFmpeg et aux dépôts sources des outils utilisés.

## Conclusions structurantes

### Assets et data-blocks

Blender définit un asset comme un data-block enrichi de sens et de métadonnées. Les images,
sons et vidéos utilisés comme références ne sont pas, à eux seuls, des assets Blender. Cette
distinction justifie deux écrans séparés dans Studio.

Sources:

- [Asset Libraries — Blender Manual](https://docs.blender.org/manual/en/5.0/files/asset_libraries/introduction.html)
- [Data-Blocks — Blender Manual](https://docs.blender.org/manual/en/5.0/files/data_blocks.html)
- [Asset Browser — Blender Manual](https://docs.blender.org/manual/en/3.4/editors/asset_browser.html)
- [Asset Catalogs — Blender Manual](https://docs.blender.org/manual/en/3.3/files/asset_libraries/catalogs.html)

Le mode d’import doit être une décision de production:

- Link: source centrale et lecture seule;
- Append: copie locale indépendante;
- Append (Reuse Data): instances réutilisant le plus possible les mêmes données;
- Library Override: édition locale ciblée d’une hiérarchie liée.

Sources:

- [Link & Append — Blender Manual](https://docs.blender.org/manual/fr/5.0/files/linked_libraries/link_append.html)
- [Library Overrides — Blender Manual](https://docs.blender.org/manual/en/dev/files/linked_libraries/library_overrides.html)

### Caméra et animation

Les trajectoires complexes gagnent à séparer translation, orientation et roll. Follow Path
peut déplacer une caméra sur une courbe; un tracking distinct stabilise le regard. Les poses
et interpolations restent vérifiables dans les F-Curves.

Sources:

- [Follow Path Constraint — Blender Manual](https://docs.blender.org/manual/en/5.0/animation/constraints/relationship/follow_path.html)
- [Keyframes and interpolation — Blender Manual](https://docs.blender.org/manual/en/dev/animation/keyframes/introduction.html)
- [F-Curves — Blender Manual](https://docs.blender.org/manual/en/5.0/editors/graph_editor/fcurves/index.html)
- [Keying Sets — Blender Manual](https://docs.blender.org/manual/en/5.0/animation/keyframes/keying_sets.html)

### Matériaux réutilisables

Les Node Groups sont l’équivalent de fonctions paramétrables et composables. Ils constituent
la bonne unité pour partager des comportements de matériau ou Geometry Nodes sans dupliquer
des graphes entiers.

Source:

- [Node Groups — Blender Manual](https://docs.blender.org/manual/en/5.0/interface/controls/nodes/groups.html)

### Analyse vidéo

`ffprobe` fournit un inventaire JSON reproductible des streams. FFmpeg permet d’extraire des
frames à cadence fixe, de repérer des changements visuels et de détecter les silences. Cette
préparation factuelle doit précéder l’analyse sémantique.

Sources:

- [ffprobe Documentation](https://ffmpeg.org/ffprobe.html)
- [FFmpeg Filters Documentation](https://ffmpeg.org/ffmpeg-filters.html)

Whisper peut transcrire un audio multilingue et produire des segments horodatés. Les
timestamps au mot restent une estimation et ne doivent pas servir seuls à valider une action
à la frame près.

Sources:

- [OpenAI Whisper](https://github.com/openai/whisper)
- [Whisper transcription implementation](https://github.com/openai/whisper/blob/main/whisper/transcribe.py)

### MCP et sécurité

Le Blender MCP utilisé par le projet connecte un client IA à Blender et propose notamment
l’exécution de code. Cette puissance implique une frontière de confiance stricte: socket
local, scripts allowlistés, paramètres typés, confirmation des écritures et gates avant
sauvegarde.

Sources:

- [ahujasid/blender-mcp](https://github.com/ahujasid/blender-mcp)
- [Rapport public sur le risque execute_code](https://github.com/ahujasid/blender-mcp/issues/201)

## Décisions appliquées dans Blender Studio

1. Exécution Blender sérialisée: un seul job modifie la scène à la fois.
2. Bornes serveur pour nombres entiers et décimaux.
3. Confirmation explicite des workflows d’écriture.
4. Tutoriels stockés comme sources + preuves + interprétation versionnée.
5. `.blend` réutilisables séparés des images de référence.
6. Camera rigs namespacés par job avec manifeste.
7. Audit JSON profond avant production.
8. Gate filtrable par préfixe de shot.
9. Boucle agent séparée en gate visuel et audit technique.
10. Corrections atomiques avec budget d'itération et condition d'arrêt.
11. Audit de topologie non destructif: bords non-manifold, éléments libres, faces dégénérées,
    déterminant négatif, UV et matériaux absents.

Le protocole exécutable issu de la recherche est documenté dans
[`BLENDER_AGENT_LOOP.md`](BLENDER_AGENT_LOOP.md).

La veille des implémentations GitHub et les patterns retenus sont documentés dans
[`BLENDER_GITHUB_WORKFLOWS.md`](BLENDER_GITHUB_WORKFLOWS.md).
