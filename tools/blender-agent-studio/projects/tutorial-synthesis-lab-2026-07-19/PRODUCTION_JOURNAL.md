# Journal de production — Tutorial Synthesis Lab

Date : 19 juillet 2026  
Blender : 5.1.1  
Moteur de gate : Eevee  
Timeline finale : 1–240, 24 fps, 10 secondes

## Objectif

Tester la connaissance extraite des six tutoriels sur plusieurs assets existants, en gardant
des états Blender et des preuves visuelles après chaque ajout. La campagne ne cherche pas à
copier une vidéo : elle vérifie si ses principes survivent au changement d'objet et de scène.

Assets de travail :

- `BLOB_SPEAKER` pour mouvement produit, caméra et lookdev;
- `DRUMBOII_GAMEBOII` pour transport mécanique et événement vertical;
- `DRUMBOII_BLOB_BIKE` pour déplacement dans un environnement;
- `DRUMBOII_TRAFFIC_LIGHT` comme set dressing secondaire.

Les collections viennent de `asset_library/imported/drumboii-y2k-assets.blend`. Les objets
sont chargés comme copies locales de travail sous un root `USTUDIO_*`; la bibliothèque source
reste intacte.

## Étape 1 — silhouette et mouvement objet

Fichier : `stages/01-clay-object-motion/01-clay-object-motion.blend`

- matériau clay global;
- caméra fixe;
- hold frames 1–12;
- anticipation frame 24;
- mouvement principal frame 54;
- settle et repos frame 72.

Validation : le hold 1–12 est pixel-identique. Les écarts visuels augmentent pendant
l'anticipation et l'action. La silhouette du Blob Speaker reste lisible.

## Étape 2 — langage caméra Drumboiii

Fichier : `stages/02-camera-language/02-camera-language.blend`

- poses K1, K2 anticipation, K3 mouvement principal et K4 settle;
- target caméra décalée de quatre frames;
- focus séparé du target;
- interpolation Bézier Auto Clamped.

Premier défaut : K3 produisait un rapprochement jugé trop agressif dans la planche réduite.
La caméra a été reculée puis la frame originale 640 × 360 a été contrôlée. La version finale
garde un plan rapproché complet sans couper la silhouette.

## Étape 3 — matière, texture et couleur

Fichier : `stages/03-procedural-lookdev/03-procedural-lookdev.blend`

- Noise 3D avec coordonnées Generated;
- Color Ramp violet/bleu;
- micro-bump;
- métallique et roughness contrôlés;
- éclairage key/fill/rim;
- barres magenta et cyan;
- look AgX Medium High Contrast.

La texture est volontairement forte : cette étape sert à prouver que le shader procédural
est observable et copiable, pas à verrouiller une direction artistique définitive.

## Étape 4 — transport et chorégraphie mécanique

Fichier : `stages/04-mechanical-choreography/04-mechanical-choreography.blend`

- convoyeur composé de 28 liens au pas documenté de 0,32;
- transport X en interpolation linéaire;
- montée, inclinaison et impact en Bézier;
- caméra plus retenue pendant l'action complexe;
- GAMEBOII visible uniquement frames 73–144.

Défauts corrigés :

1. le GAMEBOII et le Speaker se superposaient au départ;
2. le piédestal Speaker restait visible dans le gros plan GAMEBOII;
3. la visibilité a donc été isolée par shot au lieu de repousser les objets arbitrairement.

Limite : le convoyeur valide ici le pas visuel, le transport linéaire et la chorégraphie. Il
n'est pas encore le workflow final `Array → Curve` avec test mathématique de jonction.

## Étape 5 — asset dans un environnement

Fichier : `stages/05-environment-shot/05-environment-shot.blend`

- route créée autour du trajet caméra;
- corridor négatif réservé au héros;
- arches comme masses de profondeur;
- bâtiments procéduraux avec seed fixe `1987`;
- Blob Bike en transport linéaire;
- caméra suiveuse et hold final.

Échec détecté : le premier scatter plaçait des bâtiments entre la caméra et la route. Aux
frames 228–240, un bloc masquait presque tout le véhicule. Toutes les grandes masses ont été
replacées derrière la route. Les arches peuvent encore occulter brièvement le véhicule, mais
elles ne détruisent plus sa lecture.

## Étape 6 — scène finale multi-shot

Fichier : `stages/06-final-multishot/06-final-multishot.blend`

Découpage :

- frames 1–72 : Speaker, reveal et caméra hero;
- frames 73–144 : GAMEBOII sur convoyeur;
- frames 145–240 : Blob Bike dans l'environnement.

Trois caméras sont liées à des marqueurs timeline. Chaque famille de géométrie possède des
clés de visibilité constantes afin de ne pas contaminer les autres shots.

Échecs corrigés :

1. l'ancienne API `scene.node_tree` n'existe plus dans Blender 5.1;
2. le compositor a été migré vers `scene.compositing_node_group` et ses sockets Blender 5.1;
3. l'environnement du shot Bike masquait initialement le Speaker;
4. les barres lookdev utilisaient une coordonnée Y absolue et passaient devant la caméra;
5. les décors ont été isolés par segment et les barres replacées relativement au produit.

## Contrôles finaux

- 6 tutoriels : sources, probe, audio, analyses et contact sheets présents;
- 6 stages Blender reconstruits;
- 36 snapshots de développement;
- 176 objets dans la scène finale;
- 74 matériaux;
- 3 caméras animées;
- 240 frames de preview rendues;
- aucun snapshot manquant, noir ou surexposé selon les seuils du validateur;
- hold initial réellement immobile;
- cuts mesurés aux frames 72→73 et 144→145;
- dernier settle 228→229, puis hold immobile 229–240.

Le détail des métriques se trouve dans `validation-report.json`.

## Ce qui est validé et ce qui ne l'est pas encore

Validé :

- séparation source/work asset;
- roots copiables;
- animation still/action/settle;
- caméra K1–K4 et target indépendant;
- shader procédural;
- interpolation différente selon la fonction;
- environnement camera-first;
- visibilité par shot;
- gates et reconstruction automatisée.

Encore expérimental :

- direction artistique finale;
- rendu haute définition/Cycles;
- collisions physiques exactes;
- conveyor Array/Curve véritablement bouclé;
- sound design;
- montage avec transitions ou titrage;
- transformation de cette campagne en workflows paramétriques accessibles dans l'UI.

## Commandes utiles

Reproduire une étape :

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background --factory-startup \
  --python workflows/tools/create_tutorial_synthesis_campaign.py \
  -- --stage 4
```

Revalider la campagne :

```bash
python3 workflows/tools/validate_tutorial_synthesis_campaign.py
```

Ouvrir la scène finale :

```bash
open projects/tutorial-synthesis-lab-2026-07-19/stages/06-final-multishot/06-final-multishot.blend
```
