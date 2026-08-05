---
name: blender-production-studio
description: Use automatically for any Blender, 3D asset, modeling, rigging, animation, rendering, lookdev, procedural environment, game-asset, Unity export, or cinematic task in GAME. Build, audit, generate, optimize, export, and validate through the compact Blender Team Studio embedded at tools/blender-agent-studio, without committing heavy source assets.
---

# Blender Production Studio

Treat the repository as a production system. Preserve sources, declare the target and budgets, and
match every claim to evidence strong enough to support it.

## GAME integration

When Claude is launched from the Unity repository root, treat
`tools/blender-agent-studio/` as the Blender studio root. Before running a Blender studio command,
change into that directory; paths in the remaining instructions are relative to it. Do not clone a
second copy of the Blender repository and do not create a nested `.git` directory.

Keep Blender sources, renders, caches and exports in the studio's ignored `local_work/` or
`local_assets/` directories. Only validated runtime exports may enter `Assets/_Project/`, with their
Unity `.meta` files and the provenance/licence record required by GAME. Keep editable `.blend`, PSD,
raw media and other masters outside Git in the declared DVC/private vault workflow.

## First-use setup

When the user asks for Blender work, perform the local setup automatically after changing into
`tools/blender-agent-studio/`:

1. If `.studio.local.json` or `app/.env` is missing, run `python3 tools/bootstrap.py --configure`.
2. Run `python3 workflows/tools/studio_readiness_check.py` before creating or editing a scene.
3. If the readiness check reports a missing Blender, FFmpeg or other machine dependency, report the
   exact missing item and use the existing GAME `setup-game` workflow for an interactive install;
   never silently install system software or secrets.
4. Continue with the requested Blender task only after the relevant readiness gate is clear.

## Start every task

1. Run `scripts/locate_repo.py` after changing into `tools/blender-agent-studio/` when the repository root is not obvious.
2. Read root `AGENTS.md` completely and follow its mandatory reading order.
3. Identify one project type: `asset`, `game-asset`, `rig`, `animation`, `environment`,
   `procedural`, `cinematic`, or `still`.
4. Inspect the source, catalog references, target version and relevant workflow JSON before writing.
5. State the execution mode: read-only, MCP working copy, or isolated batch.

Read `references/task-routing.md` when the type or route is uncertain.

## Create an isolated contract

For new work, run `workflows/tools/create_team_project.py`. Keep versioned contracts and textual
evidence in `projects/team/<id>/`; keep `.blend`, textures, renders, caches and exports in ignored
`local_work/<id>/`.

Search `catalog/assets.json` by path, role or metadata. If an authorized private vault is available,
use `tools/materialize_assets.py` to fetch only selected content into `local_assets/` and verify its
SHA-256. Never assume an absent catalog entry is locally available, and never add binaries to Git.

Read the relevant domain reference:

- game assets: `references/game-assets.md`;
- rigs and animation: `references/animation-and-rig.md`;
- environments, procedural systems and rendering: `references/environments-and-rendering.md`.

## Execute safely

Use versioned scripts and honor `execution`, `mutates_scene`, `requires_confirmation`,
`enabled_in_app`, `maturity`, and `evidence_level` in `workflows/catalog/`. Run batch operations with
factory-startup isolation. Use MCP only on a deliberate working copy. Do not save unless the exact
destination was declared.

If ad hoc `bpy` is necessary, keep it inside the project workspace, explain why no catalog workflow
fits, prefix new data with the project prefix, and produce a manifest.

## Build in order

```text
observable brief → read-only audit → physical/technical contract → local work copy
→ blockout → scale/structure gates → domain construction → materials
→ rig/motion/camera when needed → lighting → complete preview
→ one-category correction → export → independent and target reimport → human review
```

Use `neutral-production` unless the user selects another style. A style may choose among solutions
that already satisfy identity, function, target, budgets and physical gates.

## Validate and stop

Use evaluated geometry, real supports, a declared coordinate frame and per-frame parent evaluation
for physical claims. Validate the whole clip, not only hero frames. A Blender or glTF reimport is not
a target-engine import.

Run `workflows/tools/validate_team_project.py` before a final verdict. Read
`references/evidence-and-stop-gates.md` for critical failures and the required handoff split. Use
`references/repository-map.md` to load only the relevant knowledge branch.
