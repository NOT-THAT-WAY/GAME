# Revue finale — « Le réveil du bord » (fable)

Verdict : **reject**, score plafonné à **49/100** par un échec critique que je déclare
moi-même — le genou traverse la rampe de 4,4 cm pendant une dizaine de frames au moment du
step-up. Sans ce plafond, la note artistique serait 78,05. Le film raconte ce qu'il doit
raconter et le reste de la physique tient, mais le contrat du dépôt est clair : une
traversée de décor est éliminatoire quelle que soit la note esthétique, et je préfère la
signaler que de la maquiller.

## Ce que j'ai choisi

**Le tempérament.** Je l'ai joué *curieux mais pas pressé*. Il ne bondit pas : il bat le
tempo du pied pendant presque deux secondes avant de bouger, se lève en chargeant ses mains
sur le bord (le tronc plonge à 38° avant que le bassin décolle — c'est ce plongeon qui rend
le poids), et pendant la marche sa tête balaie lentement les murs, à une période plus longue
que sa cadence de pas. Il ne regarde pas où il met les pieds : il regarde autour.

**La contrainte que la mesure m'a imposée.** L'intérieur de cette boîte n'a pas de sol
horizontal : le « sol », c'est la rampe du Piano Roll, mesurée à **46,34°**. Et le bord sur
lequel il est assis (z = 0,76) est **12 cm plus bas** que l'arête de cette rampe (z = 0,88).
Je n'ai pas ajouté de plancher : j'ai fait de cette lèvre un vrai step-up, avec deux appuis
préparatoires — un sur le bord plat, puis celui qui franchit la marche. C'est devenu le
meilleur moment du film et sa principale difficulté technique.

**La caméra.** Un seul plan, 38 mm → 17 mm, de trois-quarts dos à 1,5 m jusqu'à 3,1 m en
plongée. Je recule *et* j'élargis en même temps : le champ passe de 0,8 m à 3,7 m de haut,
donc l'espace se déploie autour de lui au lieu de simplement s'éloigner. À la fin, le TARGET
quitte sa poitrine et monte vers le haut des écrans — la caméra suit son regard plutôt que
son corps.

**Mon idée personnelle : les notes du Piano Roll.** Chaque fois qu'un pied se pose, la
cellule de note sous lui s'allume en vert puis retombe — comme si marcher dans le séquenceur
déclenchait le son. Onze notes, exactement sur les onze poses de pied. La dernière reste
allumée sous lui, et pendant qu'il lève les yeux, une note tenue monte sur le mur arrière :
la pièce lui répond. C'est ce qui transforme « un personnage marche dans un décor » en « il
appartient à ce logiciel ».

## Ce que j'ai ajouté au rig

L'asset v002 n'avait **aucune armature** (son manifeste ne prévoit qu'un futur lattice). J'ai
ajouté, sans toucher au mesh : 16 os (bassin, colonne, poitrine, tête, clavicules/bras/
avant-bras, cuisses/tibias/pieds), placés sur des positions mesurées dans la géométrie
(entrejambe à 0,623, épaules à 1,268, coudes trouvés par abscisse curviligne le long du
bras). Le mesh est intact : 6348 vertices, aucune coordonnée modifiée, seulement des vertex
groups. La tête est parentée à son os.

**Le heat weighting de Blender a échoué** sur ce mesh — il attribuait 4579 vertices sur 6348
à `FOOT.R`, y compris la tête, ce qui étirait le corps entier en lame dès que le pied
bougeait. Je l'ai remplacé par un skinning déterministe : distance aux segments d'os,
puissance 3,6, trois os par vertex, avec une pénalité de côté pour éviter que les membres
gauches capturent les vertices droits. Le résultat est anatomiquement propre (`diagnostics/
weight-check.json`).

## Ce qui marche à l'œil

- Les quatre temps se lisent dans l'ordre, chacun tombe sur un downbeat mesuré.
- Le sit-to-stand a du poids : hauteur du sommet du crâne 0,66 m assis → 0,87 m debout.
- Le step-up est le moment le plus convaincant : il fléchit, monte la marche, se rétablit.
- Le plan final fait exactement ce que le brief demandait : petite silhouette blanche
  (22,7 % de la hauteur du cadre) au centre d'un espace qui la dépasse de partout.
- Les notes vertes sous ses pieds sont lisibles sans expliquer quoi que ce soit.

## Ce qui rate encore

1. **Il a l'air ramassé.** C'est mon principal regret. Les mesures disent qu'il est bien
   debout (0,87 m sur 0,88 m), mais à l'écran il paraît accroupi. Deux causes cumulées : ses
   jambes ne font que 26 % de sa taille (0,227 m sur 0,88 m — c'est l'asset), et la caméra
   plonge de plus en plus, ce qui les raccourcit encore. Un plan un peu moins haut à
   l'arrivée corrigerait la moitié du problème.
2. **Le genou traverse la rampe de 4,4 cm** pendant une dizaine de frames au moment du
   step-up (frames 136-146) — c'est l'échec critique. Franchir une marche de 13 cm avec des
   jambes de 22 cm oblige à une flexion extrême, et sur une pente à 46° tout ce qui avance
   entre dans le sol. J'ai réduit le défaut de 25 cm à 4,4 cm en deux passes (pole du genou
   porté par la normale du sol plutôt que la verticale monde, puis swing du step-up abaissé)
   sans parvenir à l'éliminer. La vraie correction n'est pas un réglage : il faut soit
   supprimer la marche du parcours, soit accepter qu'il la franchisse de côté, soit un
   personnage aux jambes plus longues.
3. **Les bras restent coudés en permanence.** Ils mesurent 0,4165 m pour une hauteur
   d'épaule de 0,44 m : bras tendus, les mains touchent le sol. J'ai dû garder le coude
   fléchi (60° minimum) et faire balancer vers l'aval, sinon les mains passaient sous la
   rampe. Ça donne une posture de grimpeur cohérente, mais moins de liberté de jeu.
4. **Le balayage de la tête est trop discret** pendant la marche (±16°) — l'intention
   « il regarde les murs » se lit surtout grâce à la caméra, pas assez grâce à lui.

## Ce que je referais avec une passe de plus

Baisser la caméra finale d'environ 40 cm et réduire la plongée, pour rendre ses jambes ; les
mesures montrent qu'il y a de la marge (clearance décor 0,57 m). Ajouter un temps d'arrêt
d'une demi-seconde en haut de la marche, sur le downbeat 154, pour faire respirer le
step-up. Et remonter le regard : une vraie amplitude de tête pendant la marche, quitte à
ralentir la cadence à un appui toutes les trois pulsations.

## Preuves

`scene/trial.blend` · `renders/preview.mp4` (H.264, 640×360, 30 fps, 360 frames, 12,000 s,
AAC, zéro frame noire au blackdetect) · `renders/frames/` (360 PNG) · `gates/contact-sheet.jpg`
(les quatre temps) · `gates/key1-assis.png`, `key2-lever.png`, `key3-marche.png`,
`key4-reveal.png` · `gates/lighting-gate/` (6 états cumulatifs) · `diagnostics/box-analysis.json`
(mesures du décor) · `diagnostics/rig-report.json` · `diagnostics/weight-check.json` ·
`diagnostics/physical-validation.json` (360 frames) · `shot-manifest.json` · `score.json`.

Template et asset sources vérifiés intacts par SHA-256 après coup. Aucun fichier d'un autre
participant n'a été ouvert.
