# FL Studio Box — test de projection continue

> Cette variante est conservée comme comparaison technique. La version principale est
> `projects/fl-studio-box-semantic-template/FL_Studio_Box_Semantic_Template.blend`, car ses
> cinq crops sémantiques rendent les fenêtres FL Studio plus lisibles.

Ce template colle une seule capture FL Studio sur l'intérieur de la boîte avec une caméra
projecteur. Les pixels du logiciel restent alignés lorsqu'ils passent du mur du fond aux
parois latérales et au plancher incliné.

Cette méthode remplace le premier système de cinq crops indépendants, qui pouvait produire
des répétitions et des raccords incohérents.

## Utilisation

1. Ouvrir `FL_Studio_Box_Projection_Template.blend`.
2. Copier la nouvelle capture 16:9 dans `incoming/`.
3. Dans Blender Studio, lancer **Projeter une vidéo — FL Studio Box**.
4. Indiquer le chemin relatif, le début, la durée et les FPS.
5. Lire la timeline : la capture complète doit rester continue sur la boîte.
6. Lancer un gate avec le préfixe `USTUDIO_MEDIA_`.
7. Sauvegarder sous un nouveau nom après validation.

## Architecture

- `M_FL_STUDIO_MASTER_PROJECTION` : matériau vidéo maître;
- `USTUDIO_FL_PROJECTOR` : caméra fixe qui calcule les UV continus;
- quatre surfaces intérieures reçoivent exactement le même flux vidéo;
- le channel rack détaché reçoit un seul crop provenant du même master;
- les anciens playheads Blender sont désactivés, car la vidéo possède déjà son playhead.

Le média de démonstration est le test `fond fl test 1-1.mp4`, 1920×1080, 30 fps,
13,53 secondes.

## Workspace caméra

Le `.blend` s'ouvre dans `USTUDIO Camera Lab`, inspiré du tutoriel Drumboiii :

- rendu caméra direct à gauche;
- vue objet, boîte et rig caméra au centre;
- Dope Sheet avec les keyframes en dessous;
- Outliner et Properties à droite.

Le layout peut être reconstruit avec
`workflows/tools/setup_camera_lab_workspace.py` depuis une fenêtre Blender visible.
