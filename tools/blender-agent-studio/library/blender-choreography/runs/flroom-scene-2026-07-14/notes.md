# notes — scène FLROOM (2026-07-14) — boîte-room clay + Pulsed au centre

Demande Sliz : « copier le plug-in dans une nouvelle scène et construire une sorte de
boîte qui ressemble à ce qu'on a fait [fond-flroom-001] — pas la texture, pas de props
(précisés par la vidéo) — comme ça on a l'espace ET l'objet au milieu de l'espace ».

**Évolution du squelette C″** : jusqu'ici le squelette = device seul dans le void
(l'espace était laissé à l'invention de Seedance → priors). Ici le squelette contient
**la géométrie de l'espace en dur** : la relation caméra/room/device devient déterministe,
la vidéo/scène ref ne fournit plus que la matière.

## Ce qui est construit (scène Blender `FLROOM`, script `tools/build_flroom_box.py`)

| Élément | Valeur | Source |
|---|---|---|
| Intérieur W×H×D | 48 × 25 × 30 BU (W:H = 1.92) | mesuré sur `refs/04_plate_start_frame_room.png` (700×375 px) |
| Coque | épaisseur 3.5, bevel 2.2 (monocoque arrondie), front ouvert (boolean) | même lecture que la boîte du plateau |
| Device | copie liée des 12 meshes PULSED, pivot `flroom_device_pivot`, scale 1.5 (24 BU ≈ 50 % de W), lévitation à z=10.5, face à l'ouverture | canonique, landscape |
| Lumières | softbox frontales (`fl_key`, `fl_fill`), bounce interne bas, softbox device à travers l'ouverture — **aucun spot du haut** | failure-pattern `v2v-neutral-void-invents-overhead-spotlight` |
| Sol | plan void near-black (la boîte pose dessus, comme le plateau) | plate fond-flroom |
| Caméras | `flroom_cam_front` (cadrage plate, boîte ~66 % du cadre) · `flroom_cam_34` · `flroom_cam_inside` | — |

Previews : `preview_front.png` / `preview_34.png` / `preview_inside.png` (EEVEE 1280×720).
.blend sauvegardé (`~/unrecorded/Blender/Pulsed_3D_model.blend`, scène FLROOM ajoutée,
scène squelette « Scene » intacte).

## v2 — recentrage (gate Sliz : « trop haut, touche le plafond ; au milieu, élément
## central, proche de sortir de la boîte, pas au fond »)

Deux causes réelles derrière le « trop haut », corrigées dans l'ordre :

1. **Caméra plongeante** : `flroom_cam_front` à z=14 au-dessus du device → beaucoup de
   sol visible, l'objet se plaque contre le plafond perçu. Fix : caméra au NIVEAU du
   device (z=11, target z=10.5) — composition frontale comme le plateau.
2. **Origine du mesh Pulsed au BAS du device, pas au centre** : bbox monde mesurée =
   centre réel 6.3 BU au-dessus du pivot (scale 1.3). Un `pivot.z = 10.5` mettait donc
   le centre réel à ~16.8. Fix : base z = 10.5 − 6.3 = 4.2 dans PARAMS.

Placement v2 final : device scale 1.3 (~43 % de W), centre réel à z=10.5 (air égal
au-dessus/en-dessous), y=−10 → face avant à ~2.5 BU du plan de sortie (nettement
détaché du fond, « proche de sortir »). Séquence `hover_frames_v2/` → `hover_10s_v2.mp4`
(v1 conservée).

## Leçon script

Cubes = dimensions **cuites dans le mesh** (bmesh scale sur vertices), jamais `ob.scale` :
le width du bevel travaille en espace local → sur un cube unitaire scalé il mange toute
la coque (1er render = boîte pleine).

## Rig hover (feedback Sliz, même jour)

« Pas collé au fond : le plug EN AVANT, qui flotte au milieu de la boîte et qui bouge
en temps réel, en fonction des paramètres ajustés. »

→ `tools/rig_flroom_hover.py` : device avancé (base y=-3) + lévitation paramétrique
240 frames / 10 s / boucle parfaite (cycles entiers). Tout se règle dans `PARAMS` :

| Axe | Amplitude | Cycles / 10 s |
|---|---|---|
| bob vertical | ±0.9 BU | 2 |
| dérive latérale X | ±0.5 BU | 1 |
| dérive profondeur Y | ±0.35 BU | 2 |
| yaw (lacet) | ±7° | 1 |
| pitch (tangage) | ±3.5° | 2 |
| roll (roulis) | ±2° | 1 |

Contrôles NON animés (règle : device montré, pas opéré) — c'est l'objet entier qui vit.
Phases décalées entre axes → mouvement organique, jamais mécanique.

Caméra du playblast = `flroom_cam_front` (cadrage plate, PLAN FIXE) → le squelette est
directement compatible avec le fond FL room plan fixe.

Sortie : séquence PNG `hover_frames/` (ce build Blender n'a pas de sortie FFMPEG)
assemblée en `hover_10s.mp4` (h264 24 fps). Render headless (`Blender -b -S FLROOM -a`)
pour ne pas bloquer l'UI de Sliz ni le socket bl.py (timeout 60 s).

## Prochaines étapes (après gate Sliz)

1. Gate du hover (amplitudes/vitesses = 1 ligne à changer dans PARAMS, re-render).
2. Playblast squelette → v2v Seedance : video_ref = squelette room+device+hover,
   image refs = plate/room fond-flroom (matière) + canonique front (identité).
   → une seule génération sort le fond FL room AVEC Pulsed vivant dedans
   (plus de compositing manuel).
