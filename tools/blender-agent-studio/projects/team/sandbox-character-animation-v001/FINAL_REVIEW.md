# Revue finale — sandbox-character-animation-v001

Passe 1 : `SB_Idle` uniquement. `SB_Walk` n'est pas commencé et attend une autorisation explicite.

## Verdict

`SB_Idle` est **candidat accepté sous revue humaine**. Les cinq gates de réception du handoff sont
PASS. Aucun échec critique. La décision d'intégration reste humaine : rien n'a été écrit dans
`Assets/_Project/`, rien n'a été commité, rien n'a été poussé.

| # | Gate | Verdict |
|---|---|---|
| 1 | Contrat | PASS |
| 2 | Physique visuelle | PASS |
| 3 | Réimport Blender | PASS |
| 4 | Import Unity | PASS |
| 5 | Preuves | PASS |

## Résultat par rapport au brief

Boucle in-place de respiration et de transfert de poids, images 1–60 incluses à 30 fps, Action et
take FBX nommés exactement `SB_Idle`. Root strictement immobile, pieds strictement plantés, volume
sphérique et silhouette préservés, poings et avant-bras hors du corps, couture continue sans pose
finale dupliquée.

Le mouvement est construit comme une somme d'harmoniques de période exactement 60 images, évaluées à
`theta = 2*pi*(f-1)/60`. La boucle n'est donc pas rattrapée après coup : `pose(f+60) == pose(f)` par
construction, ce qui donne une continuité C-infinie en position **et** en vitesse à la couture.
Amplitudes : corps ±1,0 cm vertical (fondamentale) + 0,28 cm (2e harmonique), ±0,8 cm latéral,
roulis 1,5°, tangage 0,7°, lacet 0,9° ; bras 2,5° avec traînée progressive (5 / 8 / 10 images).

## Preuves techniques, physiques et visuelles

Mesures sur **géométrie évaluée** (armature + modifiers appliqués), repère monde Blender Z-up en
mètres, **toutes les images** (`sample_frame_step = 1`), plus l'analyse cyclique de la couture.

- Root : translation **0,000000 m**, rotation **0,000000°** ; objet armature à l'identité.
- Pieds plantés : drift XY **0,000000 m**, pire vertex **0,000000 m**, pénétration sol
  **0,000000 m**, semelle à Z = 0. Les os de pied ne reçoivent aucun mouvement, la valeur nulle est
  donc structurelle, pas une tolérance.
- 36 paires de volumes mesurées (BVH triangle/triangle + distance au plus proche), pas seulement les
  paires évidentes. Paire non adjacente la plus serrée : `Body/Foot_L` à **0,0370 m**.
  `Fist_L/Foot_L` à **0,2019 m** — le contact apparent en vue de profil est une superposition de
  projection, pas un contact.
- Sockets articulaires (épaule, coude, poignet) : ils existent **dans la bind pose de la source**
  (épaule : 102 vertices à l'intérieur, 0,148885 m). Critère appliqué : non-aggravation.
  Aggravation maximale mesurée par l'animation : **0,000030 m**.
- Couture : pas à la couture **0,004375 m**, à l'intérieur de l'intervalle intérieur
  [0,002808 ; 0,004438]. Accélération 0,000449 contre 0,000549 au maximum intérieur. Image 60
  distincte de l'image 1 de **0,004375 m**.
- Réimport Blender en scène vide : écart maximal **3,4e-07 m** en translation, **0,0°** en rotation,
  **4,2e-07 m** sur les bounds évalués, à l'offset de numérotation +1.
- Import Unity 6000.3.20f1 : Generic, clip `SB_Idle`, 1,9666667 s, 30 fps, 60 échantillons,
  `loopTime = true`, `hasRootCurves = false`, `hasMotionCurves = false`, `averageSpeed = (0,0,0)`,
  10 os attendus, 5 664 triangles, 1 influence/vertex, 0 caméra, 0 lumière, 0 MeshRenderer parasite,
  aucun warning imputable au FBX.

Preuves visuelles : contact sheet orthographique 6 poses × 3 vues (face, profil, trois-quarts),
bande de couture 57-58-59-60 | 1-2-3-4, playblast 3 vues × 4 répétitions (1620×540, 30 fps, 8,0 s).

## Limites et décision humaine

1. **MCP indisponible.** `ready_for_interactive_mcp: false` (port fermé). Le travail a été fait en
   batch isolé sur une copie de travail explicitement déclarée, jamais sur la source. La consigne
   demandait une copie MCP déclarée ; le mode réellement utilisé est le batch isolé.
2. **Le loop flag n'est pas dans le FBX.** C'est un réglage d'importeur Unity (`.meta`). Il a été
   posé et vérifié pendant le test, mais il devra être reposé lors de l'intégration définitive.
3. **Blender renumérote le clip en 2–61 au réimport.** La durée (59 intervalles, 60 échantillons) et
   les poses sont identiques ; Unity lit bien 1,9666667 s / 60 images. C'est une convention de
   l'importeur Blender, pas une dérive.
4. **Écart avec `docs/SANDBOX_ANIMATION_HANDOFF.md`** : les os portent le préfixe réel `BAS_PUNCH_`
   et le FBX source ne contient **ni Cube, ni Camera, ni Light**. Le document n'a pas été modifié.
5. **Jugement esthétique non délégable.** Les gates prouvent la correction physique et technique.
   Le caractère « très subtil » de la respiration, sa lisibilité en première personne et le rythme
   restent une décision humaine devant le playblast.
6. `SB_Walk` et les 16 clips restants ne sont pas commencés, comme demandé.
