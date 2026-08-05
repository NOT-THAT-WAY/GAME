# Raccourcis et opérateurs observés

Les raccourcis Blender sont contextuels : le curseur doit être placé dans le bon éditeur et le
mode Object/Edit doit être vérifié avant exécution.

| Action | Raccourci | Contexte / vigilance |
|---|---|---|
| Orbit | bouton central + drag | Viewport |
| Pan | Shift + bouton central | Viewport |
| Zoom | molette | Viewport |
| Add | Shift+A | dépend du mode et de l’éditeur |
| Delete | X | demande le type de suppression en Edit Mode |
| Move / Rotate / Scale | G / R / S | ajouter X/Y/Z pour contraindre |
| Exclure un axe | Shift+X/Y/Z | ex. `G`, puis `Shift+Z` pour rester sur le plan XY |
| Ajustement fin | maintenir Shift | pendant le drag d’une valeur |
| Dernière opération | F9 | disparaît après une autre action |
| Object ↔ Edit | Tab | source fréquente d’erreur de sélection |
| Vertex / Edge / Face | 1 / 2 / 3 | Edit Mode, rangée supérieure |
| Extrude | E | vérifier les normales si la direction est incorrecte |
| Loop Cut | Ctrl+R | nécessite une boucle de quads exploitable |
| Inset | I | Edit Mode, face sélectionnée |
| Sélection de loop | Alt + clic | dépend du keymap et de la topologie |
| Recalcul normales | Shift+N | Edit Mode |
| Proportional Editing | O | régler le rayon avec la molette |
| Merge | M | Edit Mode; choisir By Distance pour les doublons |
| Déplacer vers collection | M | Object Mode; même touche, autre contexte |
| Mark Seam | Ctrl+E → Mark Seam | Edit Mode, edges sélectionnées |
| UV Unwrap | U → Angle Based | Edit Mode |
| Local View | `/` pavé numérique | isoler temporairement la sélection |
| Focus sélection | `.` pavé numérique | View Selected |
| Panneau latéral | N | Viewport, UV Editor ou Shader Editor |
| Renommer | F2 | objet actif |
| Batch Rename | Ctrl+F2 | plusieurs objets |
| Dupliquer | Shift+D | Escape conserve la copie sur place |
| Répéter dernière action | Shift+R | utile après duplication |
| Lier données | Ctrl+L | l’objet actif fournit notamment le matériau |
| Parent | Ctrl+P | préférer Keep Transform |
| Apply modifier sélectionné | Ctrl+A | comportement montré dans le contexte modifier de Blender 5.0 |
| Render Image | F12 | rendu depuis la caméra active |
| Comparer Render Slots | J | Image Editor / Render Result |
| Shader pie | Z | choisir Material Preview ou Rendered |

## Opérateurs/panneaux essentiels

- `Solidify` : épaisseur réversible ;
- `Subdivision Surface` : lissage et densification ;
- `Shrinkwrap` : projection de l’icing sur le donut ;
- `Lattice` : variation organique globale ;
- `Scatter on Surface` : dispersion procédurale Blender 5.0 ;
- `Weight Paint` + Vertex Group : masque spatial ;
- `Poisson Disc` : espacement approximatif des instances ;
- `Object Info / Random` + `Color Ramp` : palette aléatoire contrôlée ;
- `Depth of Field / Focus Object` : attention caméra ;
- `Light Probe Volume` : rebond indirect Eevee ;
- `Cycles Render Devices` : configuration GPU.

