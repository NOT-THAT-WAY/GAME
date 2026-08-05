# FL Studio Box — texture runs

Trois traitements de matière appliqués à la même boîte, au même éclairage, à la même
caméra et à la même animation FL Studio.

## Comparaison

- [Comparatif vidéo des trois runs](texture-comparison.mp4)
- [Comparatif fixe — frame 120](texture-comparison.jpg)

Ordre de gauche à droite : Graphite ABS, Pearl Polycarbonate, Machined Gunmetal.

| Run | Intention | Blender | Preview |
|---|---|---|---|
| Graphite ABS | soft-touch sombre, fidèle à la référence | [blend](graphite-abs/FL_Studio_Box_graphite-abs.blend) | [mp4](graphite-abs/preview.mp4) |
| Pearl Polycarbonate | coque claire nacrée, reflets bleu/rose | [blend](pearl-polycarbonate/FL_Studio_Box_pearl-polycarbonate.blend) | [mp4](pearl-polycarbonate/preview.mp4) |
| Machined Gunmetal | métal sombre, contraste et reflets plus durs | [blend](machined-gunmetal/FL_Studio_Box_machined-gunmetal.blend) | [mp4](machined-gunmetal/preview.mp4) |

Chaque dossier contient aussi cinq gates, les 240 frames PNG et un `manifest.json` avec
les paramètres de matière. Les textures sont procédurales : elles restent éditables dans
le Shader Editor et ne dépendent pas d'une image de texture externe.

## Reproduction

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background projects/fl-studio-console-2026-07-19/FL_Studio_Box_V2.blend \
  --python workflows/tools/create_fl_studio_box_texture_variant.py \
  -- --variant graphite-abs
```

Variantes acceptées : `graphite-abs`, `pearl-polycarbonate`, `machined-gunmetal`.
