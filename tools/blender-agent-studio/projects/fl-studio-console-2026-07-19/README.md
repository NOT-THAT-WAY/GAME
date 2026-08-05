# FL Studio Console — étude 3D

Reconstruction modulaire de la référence `output.mp4` / `output-2.mp4` sous la forme
d'une console Y2K contenant une interface FL Studio.

## Lecture de la référence

- `output.mp4` montre la transition conceptuelle : capture FL Studio plane, apparition du
  châssis, séparation des panneaux, puis stabilisation en objet 3D;
- `output-2.mp4` montre le plan final : console immobile, lecture FL Studio signalée par
  le playhead et les vu-mètres;
- les images `t0.3s.png`, `t2.5s.png` et `t5.0s.png` servent respectivement de vérité pour
  l'interface, la transformation intermédiaire et la composition finale.

Le principe retenu est de construire une vraie scène 3D et de garder l'interface comme
contenu remplaçable. La vidéo finale n'est donc pas reprojetée sur une simple boîte.

## Résultat corrigé — V2

- [Scène Blender principale](FL_Studio_Box_V2.blend)
- [Preview 10 secondes](fl-studio-box-v2-preview.mp4)
- [Contact sheet de la preview](box-v2-contact-sheet.jpg)
- [Manifest V2](box-v2-manifest.json)
- [Analyse temporelle complète](reference-analysis/)
- [Clips vidéo découpés par paroi](source-panel-clips/)
- [Références originales](source-reference/)
- [Gates V2](gate-v2-box/)
- [Trois texture runs et comparatif](texture-runs/README.md)

La V2 représente une boîte profonde unique. FL Studio en constitue l'intérieur : playlist
sur le mur du fond, browser sur le mur gauche, mixer sur le mur droit, piano roll sur le
plancher incliné et channel rack flottant à l'avant.

Animation actuelle : 240 frames à 24 fps, caméra presque verrouillée, cinq clips FL Studio
cycliques et deux playheads qui traversent ensemble le mur du fond et le plancher.

`FL_Studio_Console_Study.blend` reste conservé comme test V1 rejeté : il assemblait les
panneaux sur une façade et ne respectait pas la profondeur de la référence.

## Reproduction

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --python workflows/tools/create_fl_studio_box_v2.py
```

Le builder recrée la scène et cinq frames de gate. Les cinq clips de
`source-panel-clips/` doivent rester présents avec le `.blend`.

## Limites du prototype

- le texte FL Studio reste rasterisé dans les textures;
- les fenêtres ne sont pas encore des widgets 3D individuels;
- la transformation plate vers console visible dans `output.mp4` n'est pas encore animée;
- l'animation simule la lecture avec géométrie et lumière, elle n'est pas synchronisée à
  un véritable projet `.flp` ou à son audio.

La prochaine version peut remplacer chaque PNG par un crop vidéo propre d'un screen
recording FL Studio, puis ajouter l'ouverture mécanique du châssis et une caméra plus
cinématographique.
