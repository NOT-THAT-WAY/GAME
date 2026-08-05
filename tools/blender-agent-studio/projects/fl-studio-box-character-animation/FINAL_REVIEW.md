# Revue finale — FL Studio Character Arc

Verdict : **SHIP — 88,85/100**, sans échec critique.

## Film livré

Le film dure 13,533 secondes à 30 fps et conserve les 406 images du média source. Il raconte une trajectoire complète : un petit mannequin blanc est révélé par l'interface, s'assoit pour l'observer, tente de fuir son rythme puis accepte de se synchroniser avec elle. Les quatre scènes ne sont donc pas quatre démonstrations indépendantes : chaque état répond au précédent et la même playhead reste la cause visuelle centrale.

## Adaptations physiques

Le Piano Roll original est incliné de 46,34 degrés et ne pouvait pas servir de sol humain crédible. Une passerelle translucide horizontale, avec quatre ancrages visibles et deux arêtes lumineuses, a été ajoutée. Le personnage y est supporté pendant l'Éveil, la Course et la Communion. Pendant la Pause, son bassin repose exactement sur le dessus du véritable cadre inférieur. L'audit évalue les 406 images : zéro erreur de support, zéro contact de siège invalide et zéro sortie des limites contractuelles.

La playhead arrière reste l'unique playhead 3D active. La playhead du sol demeure désactivée. Comme la géométrie arrière est trop haute pour toucher un personnage de 31 cm, l'impact utilise un sweep lumineux dérivé plutôt qu'une fausse traversée de mesh.

## Caméra et mouvement

Les quatre caméras utilisent des targets et focus distincts. La course a d'abord présenté jusqu'à 3,8 cm de drift, parce que le personnage et la caméra utilisaient des interpolations séparées. Cette version a été rejetée. La caméra finale est parentée structurellement au root du personnage : l'erreur maximale mesurée sur 96 images de course est `0,00000036 m`.

L'orbite finale n'est pas un cercle aveugle. Elle reste dans un corridor local mesuré X `[-1,104 ; 1,085]`, Y `[-1,090 ; 1,250]`, Z `[2,220 ; 4,600]`. Le mur arrière est à Y 1,36, ce qui conserve plus de 10 cm de marge au passage le plus proche.

## Lumière et design

Le système conserve les écrans comme sources narratives. Le rig ajouté suit la hiérarchie Drumboiii : Sun de reflet, backlight dominant, glimmer lime, glimmer magenta et retour de détail, avec rapports d'énergie adaptés à l'échelle miniature. Le sweep a été réduit deux fois après des gates trop blancs. Le personnage pearl reste mat pendant les trois premiers actes puis gagne une émission contenue au climax. La typographie FL Studio reste diégétique dans les vidéos d'interface ; aucun titre superposé ne vient concurrencer cette lecture.

## Limites assumées

Le personnage est un mannequin graphique composé d'éléments rigides hiérarchisés, pas un rig de déformation destiné à un gros plan organique. La course privilégie une lecture claire et comique sur deux mesures plutôt qu'un cycle biomécanique détaillé. L'orbite de Communion est volontairement rapide, car le film entier contient seulement huit mesures. Une version longue pourrait développer davantage la Pause et ralentir le 360 degrés, mais ce n'est plus nécessaire pour comprendre l'arc présent.

## Preuves

- `renders/preview.mp4` : film final H.264 avec audio AAC du master
- `gates/contact-sheet.jpg` : neuf poses musicales
- `gates/lighting-gate-manifest.json` : six états cumulatifs de lumière
- `diagnostics/physical-validation.json` : validation exhaustive des 406 images
- `diagnostics/scene-audit.json` : audit final Blender
- `shot-manifest.json` : noms, coupes et stratégie des quatre caméras

