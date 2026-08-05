# FL Studio Box — arc personnage (4 scènes)

Copie de travail : `FL_Studio_Box_Character_Anim.blend`
Source intacte : `projects/fl-studio-box-semantic-template/FL_Studio_Box_Semantic_Template.blend`
(template jamais ouvert en écriture ; la copie initiale était byte-identique, MD5 vérifié)

## Ce qui a été mesuré (ÉTAPE 0, audit lecture seule)

- Timeline 30 fps, frames 1–406, EEVEE 640×360, AgX Medium Low Contrast.
- Markers média : IN=1, QUARTER=102, MIDDLE=203, THREE_QUARTERS=305, OUT=406
  → 4 intervalles de ~101 frames, utilisés comme grille de découpage des scènes.
- Volume intérieur : x ±3,8 m ; sol = piano roll incliné (z 2,0 avant → 3,9 fond) ;
  plafond z ≈ 6,24. Hauteur libre ≈ 4,2 m à l'avant.
- Cadre avant (`USTUDIO_FRONT_BOTTOM_RIM`) : assise à z ≈ 2,0, y ≈ −0,7.
- Playhead back : balayage x −2,78 → +2,78 sur les frames 1→397, soit **0,014 m/frame
  (0,42 m/s)**. Elle croise x=−1,8 à la frame ~70 et atteint x=+1,49 à la frame 305.
- `USTUDIO_BOX_FLOAT_ROOT` : bob z ±0,1 et rotations ±1° calés sur les markers ;
  tout l'intérieur lui est parenté → le personnage et les caméras intérieures
  lui sont parentés pour rester solidaires du flottement.

## Choix retenus

- **Échelle personnage : 0,35 m** (~1/12 de la hauteur libre avant).
- **Découpage** : S1 = 1→102, S2 = 102→203, S3 = 203→305, S4 = 305→406.
  L'impact de la course tombe pile sur `USTUDIO_MEDIA_THREE_QUARTERS` (305) ;
  l'affaissement qui suit devient l'ouverture de S4.
- S2 en push-in frontal symétrique lent (la version reveal ne tenait pas en 3,4 s).
- Rig **FK** (pas d'IK) : plus robuste pour ce format ; le contact main/sol est posé à la main.

## Objets créés (nomenclature USTUDIO_*, collection dédiée)

Collection `USTUDIO_CHARACTER` :
- `USTUDIO_CHAR_RIG` (armature FK : root, hips, spine, chest, neck, head,
  upper_arm/forearm/hand L-R, thigh/shin/foot L-R), parentée à `USTUDIO_BOX_FLOAT_ROOT`
- 21 parties sphériques parentées aux os : `USTUDIO_CHAR_HEAD`, `USTUDIO_CHAR_TORSO`,
  `USTUDIO_CHAR_PELVIS`, épaules/bras/avant-bras/mains/cuisses/genoux/tibias/pieds L-R
- Matériau `M_CHAR_WHITE` (blanc mat, roughness 0,55 — capte la lumière des écrans)

Caméras (collection `CAMERA_RIG`, activées par markers liés) :
- `USTUDIO_CAM_SCENE1_AWAKENING` (18 mm, worm's eye intérieur, push-in + tilt-up, DOF 2,8)
- `USTUDIO_CAM_SCENE2_PAUSE` (55 mm, plan large frontal monde, push-in imperceptible, DOF 11)
- `USTUDIO_CAM_SCENE3_RUN` (35 mm, tracking frontal parenté FLOAT_ROOT, shake croissant,
  rapprochement brutal à l'impact, DOF 4)
- `USTUDIO_CAM_SCENE4_COMMUNION` (32→85 mm, orbite 360° spirale resserrée parentée
  à `USTUDIO_CAM_S4_ORBIT`, DOF 1,4 sur la poitrine)
- Cibles : `USTUDIO_CAM_S1/S2/S3/S4_TARGET`, `USTUDIO_CAM_S4_ORBIT`
- Markers : `USTUDIO_SCENE1_AWAKENING` (1), `USTUDIO_SCENE2_PAUSE` (102),
  `USTUDIO_SCENE3_RUN` (203), `USTUDIO_SCENE4_COMMUNION` (305)

Lumières (collection `LIGHTING`) :
- `USTUDIO_S1_RIM_SWEEP` (spot vert, balaye la silhouette quand la playhead passe, f50→88)
- `USTUDIO_S3_FLASH` (point, pic 700 W pile sur la frame 305)
- `USTUDIO_S4_CLIMAX` (point chaud, montée 330→406 : le perso devient le point le plus lumineux)

## Animation

- S1 : debout à (−1,8 ; 0,45), tête levée f1→35, pivot lent −150° sur 101 frames ;
  la playhead le croise à f~70, synchronisée avec le rim sweep.
- S2 : assis sur le cadre avant, jambes pendantes, appui arrière ; pied droit qui bat
  le tempo (~138 BPM, une demi-pulsation toutes les 6,5 frames).
- S3 : course de x 0,35 → 1,45 synchronisée sur la vitesse réelle de la playhead,
  cycle 10 frames, regards par-dessus l'épaule à 225/255/285, impact + flash à 305.
- S4 : affaissé (305–318) → accroupi main au sol (318–332) → redressement progressif
  (332–392) → pose hero (392–406), fin d'orbite sur le climax à 406.

## Corrections menées (3 itérations)

1. **Raycast auto-référent** : le sol était mesuré en incluant le personnage → dérive
   en dents de scie (+1,8 m). Fix : meshes `USTUDIO_CHAR_*` masqués pendant le raycast.
2. **Frame noire à f360** : l'orbite S4 circulaire sortait du volume intérieur (caméra
   dans le mur du fond). Fix : spirale reclampée dans le volume (y_local ≤ 0,8).
3. **Cible S4 sur les tibias** : `USTUDIO_CAM_S4_TARGET` à z 3,15 au lieu de 3,32
   (poitrine) → le plan final cadré sur les jambes. Fix : cible recalée.

## Livrables

- `FL_Studio_Box_Character_Anim.blend` (scène complète, template source intact)
- `renders/preview-character-arc.mp4` (406 frames, 30 fps, 640×360 EEVEE)
- `renders/preview-frames/frame_0001..0406.png`
- `gates/contact-scene1..4.png` (4 frames par scène)
- `analysis/template-structure.json`, `analysis/template-keyframes-bounds.json` (audit ÉTAPE 0)
- `scripts/build_character.py`, `scripts/build_scenes.py`, `scripts/fix_s4_orbit.py`
  (reproductibles : recopier le template puis relancer les scripts dans l'ordre)

## Limites connues

- Preview 640×360 : le personnage de S2 est petit à l'écran (choix du plan poster) ;
  lisible en rendu 1080p.
- La course de S3 est stylisée (la playhead avance à 0,42 m/s — la comédie vient
  du contraste panique/vitesse réelle), pas une foule biomécanique.
- Fin d'orbite S4 : le fond est surtout le piano roll en bokeh ; les écrans du mur
  arrière restent hors champ bas à cette hauteur de caméra.
