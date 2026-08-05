# Revue finale — k3-pulsed-bench-demo-v001

## Verdict

**`revise` · 76,3 / 100 · aucun échec critique.**

Mini démo de Pulsed posé sur un plan de travail, 6,000 s à 24 fps, 960×540, Cycles.

## Ce qui est prouvé

L'objet **repose réellement**. Sur les 144 frames, mesuré sur la géométrie évaluée
(modifiers et parenting compris), dans un repère unique en mètres, avec le plan
d'appui dérivé du mesh du banc et non codé en dur :

| Contrôle | Valeur | Seuil | Frames hors seuil |
|---|---|---|---|
| Pénétration décor | 0,000 mm | ≤ 2 mm | 0 |
| Écart d'appui | 0,000 mm | ≤ 5 mm | 0 |
| Drift du contact | 0,000 mm | ≤ 5 mm | 0 |
| Clearance caméra | 116 mm | ≥ 80 mm | 0 |

Recouvrement BVH coque/banc : **0 paire**. `swing_clearance` est déclaré non
applicable, motivé : aucun membre en vol, les commandes sont guidées dans leur
logement et leurs limites sont vérifiées par
`knowledge/physics/object-contracts/pulsed.json`.

## Un seuil a échoué, et c'est la caméra qui a bougé

La première passe de preuves a mesuré **74 mm** de clearance caméra contre 80 mm
exigés, sur 17 frames : la pose d'anticipation rasait le plateau. Le seuil n'a pas
été touché — la trajectoire caméra a été relevée de z 0,074 à z 0,116. C'est
consigné dans `threshold_change_log` du contrat de scène.

## Deux bugs corrigés en cours de route

- Reparenter les flèches du D-pad avec
  `matrix_parent_inverse = parent.matrix_world.inverted()` alors que le parent
  porte déjà le scale 0,01 annule la chaîne : les flèches partaient à −2,6 m.
  Il faut réappliquer `matrix_world` après le reparentage.
- Keyframer `hide_viewport` sort l'objet du depsgraph et rend sa matrice évaluée
  inutilisable — les segments de jauge polluaient la mesure à ±150 mm. Seul
  `hide_render` doit être animé.

## Ce qui plafonne la note

Trois défauts réels, nommés et non masqués :

1. **Ouverture trop rasante.** Aux frames 1 à 30 l'écran n'est pas lisible et on
   lit surtout la tranche. Une bande noire non expliquée traverse le haut du cadre
   vers la frame 30, la caméra voyant au-delà du plateau.
2. **Lavage spéculaire à droite.** `SIDE_GLIMMER_A` blanchit la coque au lieu
   d'en expliquer la surface — il contredit le critère Drumboiii « les reflets
   doivent expliquer les surfaces, pas les blanchir ».
3. **Wordmark « Pulsed » encore en police Blender par défaut.** Défaut d'identité
   visible. Le logo UNRECORDED, lui, est du vrai glyphe tracé depuis l'asset de
   marque.

## Limite déclarée

Les courses des commandes sont jouées **sans main visible**. C'est une convention
de démonstration produit, déclarée dans le brief et dans le contrat d'objet ;
l'affordance réelle reste « actionné au pouce ». Elle affaiblit la causalité du
premier geste, ce qui est pris en compte dans la note.

## Actions suivantes

1. Relever et rapprocher K1 pour rendre l'écran lisible dès la première seconde,
   et fermer le cadre pour supprimer la bande noire.
2. Réduire ou écarter `SIDE_GLIMMER_A`.
3. Remplacer le wordmark via `logo_trace.build` dès que le PNG de marque existe.
4. Allonger le settle final de 4 à 6 frames.
