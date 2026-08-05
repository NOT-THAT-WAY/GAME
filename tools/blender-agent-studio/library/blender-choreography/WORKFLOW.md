# Blender Choreography — mouvement déterministe pour les reels Pulsed

> Lane où **Blender EST l'outil de mouvement** : les patterns de la
> `prompt-library/motion-language/` sont transposés en axes caméra réels
> (arc/dolly/roll/focale) + automation objet — déterministe, seedable, itérable au degré
> près. Claude pilote tout via le socket MCP addon (port 9876, client `tools/bl.py`),
> Sliz dirige en langage naturel + images-guides Nano-Banana.
> Le stylage IA (Seedance v2v) est une étape OPTIONNELLE en aval, pas la finalité.

## La boucle

1. **Brief du shot** — Sliz décrit le mouvement (catalogue `shots/` ou langage libre),
   et/ou fournit des **images-guides** (Nano-Banana, refs, screenshots) déposées dans `refs/`.
   Chaque image-guide = un **beat** de la chorégraphie (un angle/framing à un instant T).
2. **Interprétation** — Claude lit chaque image-guide, en déduit la pose caméra
   (azimut/élévation/distance/focale/cible) par comparaison avec le modèle 3D, et pose
   les keyframes correspondantes. Interpolation lissée entre les beats.
3. **Gate keyframes** — Claude rend les frames clés (stills EEVEE) dans
   `runs/<shot>-<date>/keyframes/`. Sliz corrige en langage naturel
   (« plus près », « angle plus bas », « plus lent entre beat 2 et 3 »)
   → ajustements chiffrés, re-render, jusqu'à OK.
4. **Render du clip** — 720p (ou natif Seedance), 24 fps, EEVEE (Cycles si la
   transmission doit être fidèle). Sortie `runs/<shot>-<date>/clip.mp4`.
5. **Stylage IA (optionnel)** — si le rendu Blender ne suffit pas seul, le clip peut
   partir en Seedance v2v (`video_input` / video_references, UI illimitée jusqu'au 18/07)
   avec les refs canoniques pour matière/lumière. Sinon : render final **Cycles**
   (transmission fidèle), EEVEE réservé aux préviz/gates.
   Écran : émissif Blender ou off → composite footage réel (Route B reel-005).
   **Couche scène (2026-07-13)** : avec une front nue en ref, Seedance invente un spot
   générique tombant du haut → générer d'abord une **scène designée Nano-Banana** (device
   dans le fond/lumière voulus, compatible trajectoire — lévitation si la caméra passe
   dessous) et l'utiliser comme image ref. Cf. `reel-blender/test-002-scene-nanobanana/`
   + `failure-patterns/v2v-neutral-void-invents-overhead-spotlight.md`.
6. **Post** — mmaudio (son) + Topaz (4K), chaîne existante.

## Règles

- **Jamais d'écrasement de run** : chaque render dans son sous-dossier
  `runs/<shot>-<date>[-vN]/` (règle iterations-no-overwrite).
- **Device montré, pas opéré** : on anime caméra + lumière, pas les contrôles
  (règle seedance-smooth-motion — vaut aussi en 3D tant que non re-décidé).
- Avant tout render : **masquer** `ref_front/side/top/bottom` + `_calage_bbox`
  (render visibility off).
- Le `.blend` reste la propriété de `~/unrecorded/Blender/` — cette lane ne stocke
  que scripts, briefs, keyframes et clips. Sauvegarder le .blend après chaque
  session de rig validée (jamais silencieusement).
- Images-guides : le modèle 3D reste la vérité géométrique. Une image-guide donne
  l'ANGLE et l'INTENTION, jamais une modification de l'objet.

## Scène (état au 2026-07-12)

- `Pulsed_3D_model.blend` — collection PULSED (11 meshes), lumières key/fill/rim,
  caméras statiques `cam_front/back/34/side/back34`, Cycles, 24 fps.
- Les rigs de chorégraphie créés par Claude sont préfixés `choreo_`
  (ex. `choreo_pivot`, `choreo_cam_orbit`) pour ne jamais toucher l'existant.

## Catalogue de shots (`shots/`)

Un fichier par mouvement type, réutilisable et paramétrable
(durée, distance, élévation, cible). Grandit à chaque nouveau besoin.

## Grammaire caméra (vocabulaire + règles de fluidité)

`prompt-library/motion-language/camera-grammar-object-staging.md` — hiérarchie officielle
des mouvements (pan/tilt/roll · dolly/truck/pedestal · arc/crane/tracking · zoom/rack
focus/dolly-zoom), plans types produit (hero, reveal/pullback, orbit, macro sweep,
rise reveal, top-down) et règles de fluidité (still→move→still, un geste continu,
pas de hold intermédiaire — leçon test-001 run 2 saccadé vs run 3 fluide).
Composer chaque nouveau shot sb-xxx à partir de ce vocabulaire.
