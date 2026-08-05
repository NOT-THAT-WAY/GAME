# Étude validée — éclairage Drumboiii par couches

Cette étude applique le nouveau preset à la collection `PULSED` sans enregistrer le `.blend`.
Elle ne cherche pas un look final : elle vérifie que chaque couche produit une différence
lisible et localisée depuis la caméra active.

Ordre du contact sheet, de gauche à droite puis de haut en bas :

1. monde seul à `0,7` ;
2. Sun de reflet ;
3. backlight de forme ;
4. premier glimmer latéral ;
5. second glimmer ;
6. retour de détail final.

Résultat observé : le Sun sépare légèrement le bord, le backlight révèle la profondeur du
cadre, puis les trois petites couches rendent progressivement visibles les reliefs intérieurs
et l'objet central. Le dernier retour a ici un effet fort : dans une vraie réalisation, sa
puissance devra être réduite après le gate si l'identité centrale devient surexposée.

Preuves :

- `gates/contact-sheet.jpg` ;
- `gates/lighting-gate-manifest.json` ;
- six PNG individuels conservant l'ordre cumulatif.
