# Task routing

| Outcome | Project type | Profile | Required final evidence |
|---|---|---|---|
| explain or diagnose | none, read-only | none | evidence-backed report |
| reusable model/material | `asset` | `asset-general` | audit, identity views, export/reimport |
| Unity/Unreal/Godot/glTF content | `game-asset` | matching `game-*` | target-engine import report |
| skeleton or mechanism | `rig` | `rig-animation` | hierarchy, limits, weights, extremes |
| clip, loop or locomotion | `animation` | `rig-animation` | contacts, seam/root motion, playblast, reimport |
| level, modular kit or biome | `environment` | `environment` | navigation, collision, performance, target import |
| Geometry Nodes generator | `procedural` | `environment` | seeds, inputs, instance/bake and performance report |
| shot or film | `cinematic` | `cinematic` | physical gates, contact sheet, full preview, media probe |
| final image | `still` | `cinematic` | composition/material gates and final render settings |
| tutorial learning | isolated evidence folder | none | source/evidence/inference/validation separation |
| new automation | workflow script + JSON | none | safety contract, fixture test and manifest |

When a request combines asset creation and presentation, validate the asset first, then link or
append its released local version into a separate shot. When it combines gameplay and film needs,
the game profile owns geometry/export budgets; the cinematic project owns camera and render.
