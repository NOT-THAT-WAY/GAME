# WORKFLOW — test-001 mouvement caméra (Blender → Seedance v2v)

## La chaîne (6 étapes)

1. **Storyboard NB** — `blender-choreography/tools/gen_storyboard.py sb-001`
   → 4 panels ($0.60), concept « crane macro→hero ».
2. **Chorégraphie Blender** — chaque panel interprété en pose caméra exacte
   (azimut/dist/z/focale), keyframes Bezier + holds. Vérité :
   `blender-choreography/shots/sb-001-crane.md`. Le .blend reste modifiable (marqueurs P1→P4).
3. **Préviz render** — playblast EEVEE 720×1280 @24 fps → `refs/08_blender_motion_skeleton_6s.mp4`.
   C'est le SQUELETTE : seul son mouvement compte, sa matière est jetable.
4. **Package refs** — tout copié dans `refs/` (règle always-copy-canonical-refs) :
   `01` identité front (ancre, TOUJOURS 1ère) · `02` back · `03` side ·
   `04–07` panels storyboard (⚠️ ARCHIVE du concept, PAS des refs de génération) ·
   `08` squelette vidéo.
5. **Génération** — MCP Higgsfield `seedance_2_0`, `video_references` = 08,
   `image_references` = **canoniques 01→03 UNIQUEMENT** (01 en tête), 9:16, 6 s,
   fast 720p, `generate_audio:false`, `get_cost` preflight.
   Prompt : `prompts/seedance-v2v-9x16-v2.md`.
   **⛔ LEÇON run 1 : jamais les panels storyboard en image refs** — leur drift de
   composition (device portrait) écrase le squelette aux beats concernés. Les panels
   servent à fabriquer la chorégraphie Blender, point.
   (`failure-patterns/v2v-drifted-panel-refs-override-motion-skeleton.md`)
6. **Run snapshot** — output + params + job_id dans `runs/<date>_9x16_job-<id>/`
   (jamais d'overwrite). Évaluation ligne par ligne vs success criteria du brief.

## Adaptation du système de prompt (moteur ↔ cartouche, use-case v2v)

Nouveau cas par rapport au moteur (use-cases A/B/C/C′/D) : **C″ — vidéo pilotée par
squelette v2v**. Différences vs use-case C (cinéma) :

- La couche STRUCTURE ne décrit plus un mouvement à inventer : elle **délègue le mouvement
  à la video reference** (« follow the reference video's camera path exactly ») et les BEATS
  ne servent plus qu'à nommer ce que la caméra voit à chaque instant (aide sémantique).
- Nouvelle couche **MOTION SOURCE** (en tête, juste après SHOT SPEC) : déclare que la vidéo
  est une préviz 3D du MÊME device, que sa trajectoire/cadrage/timing sont la loi, et que
  sa matière préviz doit être REMPLACÉE par le look des images refs.
- Le reste ne bouge pas : SUBJECT = cartouche verbatim (sans brand names), CONSTRAINTS,
  ANTI-PRIORS, COUNTER-PROMPTS inchangés.

Si ce use-case se confirme (test validé), le promouvoir dans
`prompt-library/process/ENGINE/prompt-architecture.md` comme use-case officiel.

## Règles héritées

- Device **montré, pas opéré** — aucun contrôle animé (ni dans le squelette, ni demandé à l'IA).
- **No brand names** dans le collable (wordmark décrit, jamais nommé).
- Écran OFF — pas de waveform inventée.
- Chaque run dans son sous-dossier horodaté — jamais d'overwrite.
- `get_cost` preflight avant chaque génération MCP (crédits réels, pas de perk fast via API).
