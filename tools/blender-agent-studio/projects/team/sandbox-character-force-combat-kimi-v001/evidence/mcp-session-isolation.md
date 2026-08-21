# Session MCP et isolation — sandbox-character-force-combat-kimi-v001

## État de readiness

- `studio_readiness_check.py` (2026-08-15, avant toute mutation) :
  `ready_core=true`, `ready_for_animation_media=true`, `ready_for_interactive_mcp=false`
  (`mcp_port_open=false` à ce moment). Blender 5.1.1, FFmpeg/ffprobe présents.
- Le port MCP 9876 était fermé au départ : démarrage normal de Blender 5.1.1 GUI avec l'addon
  BlenderMCP déjà installé (`~/Library/Application Support/Blender/5.1/scripts/addons/blender_mcp_addon.py`,
  auto-start à l'enregistrement).

## Conflit de port constaté et résolu SANS toucher à la session de Claude

- L'agent Claude travaille en parallèle : son instance Blender GUI (PID 62697, lancée 23:31,
  master `sandbox-character-motion-object-claude-v001/work/sandbox_character_claude_motion_object_master.blend`)
  a lié le port 9876 en premier (vérifié par `lsof -iTCP:9876`).
- Ma première sonde a répondu avec le filepath du master de Claude : mutation immédiatement
  interdite, aucune scène touchée.
- Résolution : ma propre instance (que j'avais lancée, PID 63243) a été arrêtée — c'était MON
  processus, sans travail non sauvegardé, fichier disque intact (SHA-256 revérifié après coup) —
  puis relancée avec `--python` fixant `scene.blendermcp_port=9880` et redémarrant le serveur de
  l'addon sur le port 9880. Aucun processus de Claude n'a été tué ni modifié.
- Client : `scripts/mcp_client.py`, `BAS_KIMI_MCP_PORT=9880` par défaut.

## Vérifications d'appartenance de session

- Avant chaque mutation et chaque sauvegarde, `bpy.data.filepath` est relu par MCP et comparé à
  `local_work/sandbox-character-force-combat-kimi-v001/work/sandbox_character_kimi_force_combat_master.blend`.
  Toute autre valeur (master de Claude, SB_Idle original, FBX runtime) arrête la mutation.
- Vérifié au démarrage : filepath = master de travail Kimi, Actions présentes =
  `BAS_PUNCH_Rig|BAS_PUNCH_Rig|BAS_PUNCH_punch` (placeholder 24 fps, conservé) et `SB_Idle`
  (référence, conservée), 10 os `BAS_PUNCH_*`, Blender 5.1.1.

## Règle d'exécution

- Mutations de scène : uniquement via MCP (session GUI ouverte sur la copie de travail).
- Batch (`blender -b --factory-startup`) : uniquement ensuite, sur des checkpoints sauvegardés,
  pour audits, mesures, renders, exports et réimports isolés. Aucun batch ne sauvegarde le master
  ouvert dans la session MCP.
