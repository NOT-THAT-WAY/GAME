# FL Studio Box Character Animation — Étape 0

Statut : analyse terminée, animation non commencée. Le template source est resté intact. La copie de travail est encore identique octet pour octet au source au moment de ce rapport.

## Fichiers et intégrité

- Source propre : `projects/fl-studio-box-semantic-template/FL_Studio_Box_Semantic_Template.blend`
- Copie de travail : `projects/fl-studio-box-character-animation/FL_Studio_Box_Character_Anim.blend`
- SHA-256 commun à l'étape 0 : `c0b9c1a32722e8ec3fe49037011c81e529379235c67aa2b64e59bbe1a20fee36`
- Blender : 5.1.1
- Scène : `FL_STUDIO_BOX_SEMANTIC_TEMPLATE`
- Timeline : images 1–406, 30 fps, 13,533 s
- Rendu : Eevee, 640 × 360, AgX Medium Low Contrast, exposition +0,48

## Structure observée

La scène contient 41 objets, tous préfixés `USTUDIO_` : 28 meshes, 7 lumières, 5 empties et 1 caméra. Elle utilise 12 matériaux, 5 vidéos synchronisées et 6 actions. Aucun armature, rigid body, lien de bibliothèque externe ou média manquant n'a été trouvé.

Collections principales :

- `BOX_SHELL` : 20 objets
- `FL_STUDIO_INTERIOR` : 6 objets
- `PLAYBACK_MOTION` : 3 objets
- `CAMERA_RIG` : 2 objets
- `LIGHTING` : 4 objets

`USTUDIO_BOX_FLOAT_ROOT` porte la coque, les panneaux d'interface, le Channel Rack et les deux playheads. Le sol extérieur, les lumières, la caméra source et ses targets restent en espace monde. Le futur personnage devra donc avoir son propre root/armature sous `USTUDIO_BOX_FLOAT_ROOT` pour rester solidaire de la boîte.

## Mesures réelles

- Coque hors sol extérieur, dans l'espace local du float root : `9,72 × 3,01 × 6,00 m`
- Union des panneaux intérieurs : `8,16 × 2,44 × 4,32 m`
- Ouverture frontale approximative : `8,28 × 4,62 m`
- Centre du Piano Roll : `(0 ; 0,415 ; 1,755) m`
- Hauteur libre au centre jusqu'au dessous du plafond : `3,365 m`
- Taille demandée à 1/10–1/15 de cette hauteur : `0,224–0,337 m`
- Taille de départ recommandée : `0,30 m`, à valider en clay render
- Dessus du cadre inférieur : `z ≈ 0,76 m`, utilisable pour la pose assise de la scène 2

Point physique critique : `USTUDIO_PIANO_ROLL_FLOOR` n'est pas horizontal. C'est une rampe de `46,34°`, avec une friction statique minimale théorique d'environ `1,048` pour ne pas glisser. Faire marcher, courir ou s'accroupir un personnage comme sur un sol normal serait incohérent sans une règle visible ou explicitement posée.

Solutions possibles avant rig :

1. Ajouter dans la copie une petite passerelle/scène transparente réellement horizontale, ancrée à la boîte.
2. Déclarer une règle diégétique d'adhérence ou de gravité locale de l'interface, visible dans la mise en scène.

Une surface de collision horizontale invisible qui contredit l'image est exclue.

## Rig caméra et flottement existants

- Caméra : `USTUDIO_BOX_CAMERA`, focale animée 43,5–47 mm, DOF active à f/4,5.
- Contrainte Track To vers `USTUDIO_BOX_TARGET`, axes `-Z / Y`.
- Le float root est animé aux images `1 / 102 / 203 / 305 / 406`, avec flottement lent : Z 1,18–1,38 m, translation X/Y faible et rotations proches de ±1°.
- La caméra et la target sont en espace monde. Les futures caméras intérieures devront suivre le float root ; la caméra extérieure de la scène 2 peut rester en espace monde.
- L'action caméra existante est partagée entre l'objet caméra et son datablock. Chaque nouvelle caméra devra avoir son propre datablock et ses propres actions pour éviter les contaminations entre scènes.

Caméras prévues, non créées à cette étape :

- `USTUDIO_CAM_SCENE1_AWAKENING`
- `USTUDIO_CAM_SCENE2_PAUSE`
- `USTUDIO_CAM_SCENE3_RUN`
- `USTUDIO_CAM_SCENE4_COMMUNION`

## Playhead et synchronisation

La playhead 3D active est `USTUDIO_PLAYHEAD_BACK`, enfant du float root. Elle balaie le mur arrière de X = -2,78 m à +2,78 m, puis reboucle à l'image 398. `USTUDIO_PLAYHEAD_FLOOR` est volontairement masquée car la vidéo du Piano Roll contient déjà sa propre playhead : elle ne doit pas être réactivée ni dupliquée.

Deux limites changent le brief :

- La playhead arrière occupe approximativement Z = 3,03–4,79 m. Un personnage de 0,30 m sur le Piano Roll atteint environ Z = 2,05 m : la géométrie existante ne peut donc pas réellement le traverser.
- Elle ne traverse le centre de la boîte qu'autour des images 199–203, pas pendant le créneau naturel de la scène 1.

La solution recommandée est un balayage lumineux non solide, dérivé de la position et de l'émission de `USTUDIO_PLAYHEAD_BACK`. On réutilise ainsi le système et sa causalité sans déplacer la playhead ni inventer une collision impossible.

Autre point : l'interpolation X de la playhead est Bézier, pas linéaire. La course devra lire sa position réellement évaluée, pas supposer une vitesse constante.

## Grille temporelle

Les markers existants sont des quarts de média :

- `USTUDIO_MEDIA_IN` : 1
- `USTUDIO_MEDIA_QUARTER` : 102
- `USTUDIO_MEDIA_MIDDLE` : 203
- `USTUDIO_MEDIA_THREE_QUARTERS` : 305
- `USTUDIO_MEDIA_OUT` : 406

Ce ne sont pas des mesures ou des downbeats. Le master contient bien une piste AAC, mais aucune bande audio n'est montée dans le VSE de Blender.

Une analyse de flux spectral reproductible estime `148,7–149,0 BPM`, probablement huit mesures 4/4, avec des départs de mesure aux images `9 / 57 / 106 / 154 / 203 / 251 / 299 / 348 / 396`. Cette grille reste heuristique jusqu'à validation à l'écoute dans la copie.

Montage compact proposé si la durée source est conservée :

- 1–8 : respiration
- 9–105 : scène 1, Éveil, deux mesures
- 106–202 : scène 2, Pause, deux mesures
- 203–298 : scène 3, Course, deux mesures ; impact probable image 251
- 299–396 : scène 4, Communion, deux mesures
- 397–406 : tenue finale et rebouclage média

Le brief demande un push-in de huit mesures dans la scène 2, mais le film entier ne contient qu'environ huit mesures. Dans la durée actuelle, il faut donc choisir l'alternative déjà prévue dans le brief : macro sur le pied, crane up et pull back. Sinon, il faut allonger le film.

## Faisabilité par scène

### 1 — L'Éveil

Le 16–20 mm est faisable avec un clip start de 0,005–0,01 m. La caméra et son target devront suivre le float root. Le reveal exige le sweep lumineux dérivé, car la playhead géométrique est trop haute et trop tardive.

### 2 — La Pause

Le cadre inférieur fournit un siège physique crédible. Une caméra extérieure en espace monde peut révéler le flottement de la boîte. La version macro pied → crane/pull back tient dans deux mesures ; huit mesures exigent une extension.

### 3 — La Course

Une course le long de X est possible. La caméra frontale devra être liée au root du personnage avec un offset contrôlé. Le rattrapage doit lire la playhead évaluée ; le shake reste additif, borné et ne doit jamais produire de drift. L'impact image 251 est une hypothèse musicale à confirmer.

### 4 — La Communion

Un 360° entre 299 et 396 durerait 3,23 s, soit environ 111°/s : c'est énergique, pas contemplatif. La faible profondeur de la boîte interdit une orbite circulaire plane ; il faut une trajectoire 3D contrôlée, testée au minimum tous les 45°, ou davantage de durée. La fin à 85 mm exige une distance d'environ 0,9–1,1 m pour un personnage de 0,30 m.

## Lumière et matériaux existants

Les écrans utilisent cinq vidéos de 406 images, auto-refresh et loop, branchées en Base Color et émission. La playhead possède un matériau à émission audio-réactive animé sur 136 clés. La scène utilise déjà sept lumières, mais pas encore le rig Drumboiii en couches ; aucune lumière n'a été modifiée à l'étape 0.

Pour la suite, les couches seront ajoutées une par une dans la copie et jugées A/B : environnement incomplet, Sun oblique, backlight principal, puis glimmers uniquement pour des détails nommés.

## Décisions requises avant l'animation

1. Physique du sol : passerelle transparente horizontale, ou adhérence/gravité locale explicitement diégétique ?
2. Durée : conserver 406 images avec le montage compact, ou étendre la timeline pour rendre la Pause réellement contemplative et ralentir l'orbite finale ?
3. Reveal/impact : autoriser un sweep lumineux dérivé de la playhead existante, sans dupliquer ni retimer sa géométrie ?

## Preuves produites

- `analysis/step0-scene-structure.json` : inventaire exhaustif, hiérarchie, actions, keyframes, matériaux, médias et états aux markers
- `analysis/audio-grid-estimate.json` : méthode et estimation musicale
- `diagnostics/deep-audit/scene-audit.json` : audit structurel
- `diagnostics/spatial/scene-spatial-graph.json` : relations spatiales
- `diagnostics/view/scene-view-diagnostics.json` : visibilité depuis la caméra à l'image 203
- `gates/step0-source-marker-gate/contact-sheet.jpg` : rendu du source aux cinq markers média
- `copy-manifest.json` : preuve d'intégrité source/copie

