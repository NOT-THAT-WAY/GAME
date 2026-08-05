# Brief d’analyse — Chains and Movements — Drumboiii

## Principe

Séparer strictement ce qui est observé de ce qui est inféré. Chaque conclusion doit citer
un timecode, une frame ou un passage du transcript. Ne jamais transformer une préférence
du formateur en règle universelle sans le signaler.

## Sources préparées

- Vidéo originale: `knowledge/tutorials/drumboii-chains-movements-2026-07-31/source-proxy.mp4`
- Probe technique: `knowledge/tutorials/drumboii-chains-movements-2026-07-31/probe.json`
- Frames régulières: `knowledge/tutorials/drumboii-chains-movements-2026-07-31/frames/regular`
- Changements de plan: `knowledge/tutorials/drumboii-chains-movements-2026-07-31/frames/scenes`
- Contact sheet: `knowledge/tutorials/drumboii-chains-movements-2026-07-31/contact-sheet.jpg`
- Audio: `knowledge/tutorials/drumboii-chains-movements-2026-07-31/audio.wav`
- Transcript normalisé: `knowledge/tutorials/drumboii-chains-movements-2026-07-31/transcript.json`

## Analyse attendue

1. Résumer l’objectif final et le niveau requis.
2. Découper le tutoriel en chapitres avec `start`, `end`, objectif et preuve.
3. Extraire les opérations Blender exactes: espace de travail, outil/opérateur, réglages,
   raccourcis, ordre, préconditions et résultat observable.
4. Identifier les techniques caméra: rig, contrainte, focale, distance, composition,
   timing, F-Curves, easing et risques de dérive.
5. Identifier géométrie, modifiers, Geometry Nodes, shading, textures, lumière, couleur,
   compositing, rendu et export.
6. Distinguer assets réutilisables, dépendances externes et éléments spécifiques au projet.
7. Produire une recette reproductible avec paramètres, gate visuel et rollback.
8. Noter les ambiguïtés, versions Blender, addons et affirmations à vérifier.

## Contrat de sortie `analysis.json`

```json
{
  "schema_version": 1,
  "model": "agent utilisé",
  "summary": "résumé",
  "confidence": 0.0,
  "chapters": [{"start": 0, "end": 0, "title": "", "evidence": []}],
  "techniques": [{"domain": "camera", "name": "", "steps": [], "evidence": []}],
  "reusable_assets": [],
  "workflow_recipe": {"inputs": [], "steps": [], "gates": [], "outputs": []},
  "risks": [],
  "open_questions": []
}
```

Transcript disponible: **oui**.
