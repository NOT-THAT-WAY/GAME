# Revue finale — k3-pianoroll-slope-run-codex-v001

## Verdict

`ship` — 88,55/100, sans échec critique. Ce verdict concerne un benchmark stylisé de
compréhension physique et caméra, pas une animation humanoïde de niveau mocap.

## Histoire et causalité

Une petite figurine blanche se prépare au bas du Piano Roll, active ses semelles lime, transfère
son poids vers l’amont puis gravit la vraie pente de l’interface. Les pas courts alternent entre
appui fixe et swing. Au sommet, la cadence tombe, le torse revient de 19–22° vers 8° et les deux
semelles se reposent sans glissement. Le changement est donc concret : immobile en bas, stable
en haut, avec une cause visible — l’adhérence — plutôt qu’un déplacement arbitraire du root.

## Physique et usage

La surface `USTUDIO_PIANO_ROLL_FLOOR` mesure 46,340008°. Le coefficient de friction minimal
calculé est 1,047904 et le grip fictionnel est contracté à 1,25. La validation échantillonne les
240 frames : pénétration maximale 0,0000006 m, drift tangent maximal d’un pied planté 0 m,
clearance de swing évaluée 0,01224563 m, hauteur du pelvis stable à 0,148 m. Le torse est calculé
depuis la verticale du monde, entre 8° et 22°, et non collé à la normale du plan.

## Caméra et rythme

La caméra principale reste à +X, légèrement en amont, avec un horizon monde stable. K1 pose le
rapport d’échelle, K2 prépare le mouvement, K3 suit l’ascension à offset presque constant et K4
absorbe l’arrivée. TARGET et FOCUS sont séparés; le TARGET retarde de deux frames pendant le
travel. La distance caméra varie de 1,27885261 à 1,2819766 m et le corridor passe avec 0,3067 m
minimum au-dessus du plan. Les pieds restent lisibles et l’inclinaison n’est jamais aplatie.

## Lumière et design

Le rig suit le gate Drumboiii : monde volontairement incomplet, Sun pour les réflexions,
Back Shape pour détacher la figurine, Glimmer A lime pour le grip, Glimmer B magenta comme
contrepoint FL Studio, puis Detail Return. Le personnage est perle mate, les chaussures sont
sombres et les semelles n’émettent fortement que pendant l’appui. La typographie de l’interface
existante reste un décor secondaire et ne concurrence pas la lecture du geste.

## Défauts restants

La silhouette à volumes articulés assume un langage de mannequin graphique : les articulations
sont plus « bead figure » que peau continue, et la course n’a pas la torsion fine d’un bassin ou
la déformation musculaire d’un rig organique. Le glimmer magenta produit un wash volontairement
fort au milieu du plan. Ces limites réduisent le score motion/lumière, mais ne créent ni collision,
ni drift, ni inversion d’articulation, ni frame corrompue.

## Itérations

1. Segments : une contrainte Stretch To initialisée avant la pose étirait les membres sur plusieurs
   mètres. Elle a été remplacée par position, quaternion et longueur recalculés à chaque frame.
2. Contact : le pied gauche sautait de 20 mm tout en restant déclaré planté à la frame 49. Sa pose
   initiale correspond désormais exactement au premier contact; drift mesuré après correction : 0 m.
3. Caméra : l’offset initial de -0,52 m en aval cachait les premières images derrière la lèvre basse.
   Le suivi est devenu latéral puis avancé de +0,25 m sur la pente; les 240 frames sont visibles et
   le corridor est validé.

## Livrables

La scène se trouve dans `scene/trial.blend`, le film dans `renders/preview.mp4`, les gates dans
`gates/`, les audits et mesures dans `diagnostics/`, et l’évaluation pondérée dans `score.json`.
Le template source conserve son SHA-256 `c0b9c1a32722e8ec3fe49037011c81e529379235c67aa2b64e59bbe1a20fee36`.
