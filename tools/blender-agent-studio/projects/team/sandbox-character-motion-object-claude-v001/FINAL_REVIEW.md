# Revue finale — pôle locomotion, verticalité et interactions d'objet

Onze Actions produites en une passe autonome, chacune validée et checkpointée séparément.
`SB_Idle` a servi de référence et n'a pas été régénéré. Aucune Action du lot forces/combat n'a été
créée dans ce projet.

## Verdict

**11 clips sur 11 : PASS sur les cinq portes.** Rien n'a été commité, poussé, ni écrit sous
`Assets/_Project/`.

| Clip | Plage | Durée | Loop | Contrat | Physique | Continuité | Réimport | Unity | Verdict |
|---|---:|---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `SB_Walk` | 1–30 | 0,96667 s | oui | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `SB_Sprint` | 1–24 | 0,76667 s | oui | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `SB_Airborne` | 1–24 | 0,76667 s | oui | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `SB_JumpTakeoff` | 1–12 | 0,36667 s | non | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `SB_Land` | 1–12 | 0,36667 s | non | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `SB_CarryIdle` | 1–60 | 1,96667 s | oui | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `SB_CarryWalk` | 1–30 | 0,96667 s | oui | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `SB_Pickup` | 1–24 | 0,76667 s | non | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `SB_Throw` | 1–24 | 0,76667 s | non | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `SB_Drop` | 1–18 | 0,56667 s | non | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `SB_Deposit` | 1–30 | 0,96667 s | non | PASS | PASS | PASS | PASS | PASS | **PASS** |

Chaque durée vaut exactement `(n − 1) / 30`. Les cinq boucles portent `loopTime = true`, les six
one-shots `false`, appliqué et relu côté importeur Unity.

## Mesures principales

Géométrie évaluée, `sample_frame_step = 1`, repère déclaré `world_blender` (matrice d'armature =
identité).

| Mesure | Seuil | Pire valeur sur les 11 clips |
|---|---:|---:|
| Pénétration sol | ≤ 0,002 m | **7,45 × 10⁻⁹ m** |
| Drift d'un appui planté | ≤ 0,005 m | **0,000000 m** |
| Écart d'un appui planté | ≤ 0,005 m | 0,000000 m |
| Clearance d'un pied en swing | ≥ 0,010 m | 0,095 m |
| Translation du root | ≈ 0 | **0,000000 m** |
| Rotation du root | ≈ 0 | **0,000000°** |
| Aggravation d'un socket d'épaule | ≤ 0,020 m | +0,00031 m |
| Paires de dégagement en contact | 0 | **0** |

Le drift nul n'est pas une chance : pendant l'appui le pied suit exactement `y = −A + v·t`, et le
balancier est un Hermite cubique dont **les tangentes d'extrémité valent la vitesse d'appui**. Le
pied est donc déjà en train de reculer à la bonne vitesse au moment du contact.

## Vitesse nominale : une décision à trancher

Le gameplay marche à **4,2 m/s** et sprinte à **7,0 m/s**
(`PredictedPlayerMotor._walkSpeed` / `._sprintSpeed`). Une foulée couvrant 4,2 m en une seconde
authorée demanderait 2,1 m par pas à un personnage de 1,34 m : c'est un bond, pas une marche.

Les cycles sont donc authorés à **exactement la moitié** de la vitesse gameplay, ce qui donne un
multiplicateur unique et propre :

| Clip | Vitesse nominale | Vitesse gameplay | Multiplicateur |
|---|---:|---:|---:|
| `SB_Walk` | 2,10 m/s | 4,2 m/s | **×2,0** |
| `SB_CarryWalk` | 2,10 m/s | 4,2 m/s | **×2,0** |
| `SB_Sprint` | 3,50 m/s | 7,0 m/s | **×2,0** |

**Décision qui appartient à l'intégrateur** : accepter la lecture ×2,0, ou retimer les clips. Le
choix n'a pas été fait ici.

## Ce que la géométrie du personnage impose

Trois contraintes mesurées, pas supposées, ont dicté la forme des clips :

1. **Aucun dégagement vertical.** Au repos le sommet d'un pied (`z = 0,220`) est exactement tangent
   au bas de la sphère du corps (`z = 0,220`). Une première marche à 0,20 m de levée a enfoncé le
   pied de **0,098 m dans le ventre**. Les pieds passent donc *à côté* du corps : levée 0,095 m,
   écartement 0,22 m, ce qui satisfait `(0,11 + écart)² ≥ 1,12·levée − levée²` avec marge. La
   démarche chaloupée qui en résulte est une conséquence du rig, pas un parti pris.
2. **Corridor latéral de 12,4 cm** entre le bord externe d'un pied (`x = 0,45`) et le bord interne
   du poing (`x = 0,5738`), alors que dégager le corps en demande environ 23. À bras fixes les deux
   contraintes n'ont **aucune solution commune** : les bras s'écartent donc en phase avec le pied du
   même côté et ouvrent le corridor.
3. **Accroupissement plafonné à 53 mm.** Le dégagement minimal entre le dessous de la sphère et les
   dômes des pieds vaut `0,0534 m` à sa tranche la plus serrée (`x = 0,204`). Les compressions de
   `SB_JumpTakeoff` et `SB_Land` sont portées par l'inclinaison et les bras, pas par une descente du
   corps. Une première version à −0,16 m enterrait les pieds de 0,108 m.

## La zone de port est atteignable — mesuré, pas supposé

Le code tient l'objet à `(side, y = 0,86, z = +0,62)` en local Unity, soit `(side, −0,62, 0,86)` en
Blender. Une estimation à la main concluait que les bras ne pouvaient pas l'atteindre ; elle ne
considérait qu'un balancier plan. Le solveur, qui travaille sur les **poings évalués**, atteint la
cible à **1,8 mm**.

Distances signées du poing à l'enveloppe (négatif = à l'intérieur) :

| Objet | Slot −0,16 | Slot 0,00 | Slot +0,16 |
|---|---:|---:|---:|
| Caillou (0,66 × 0,55 × 0,62) | +0,191 / −0,129 | **+0,031 / +0,031** | −0,129 / +0,191 |
| Trophée (0,78 × 1,00 × 0,78) | +0,131 / −0,189 | **−0,029 / −0,029** | −0,189 / +0,131 |

Le slot central est bon pour les deux objets : les poings encadrent le caillou à 3 cm et entrent de
3 cm dans le trophée, ce qui est une prise, pas une traversée. **Limite déclarée** : sur les slots
latéraux, la main opposée reste à 13–19 cm de l'enveloppe. Le code d'attache n'a pas été modifié.

## Défauts trouvés et corrigés

Une catégorie à la fois. Les corrections d'instrument sont distinguées des corrections d'animation.

### Instruments corrigés (mesure fausse, pas animation fausse)

| Défaut | Conséquence | Correction |
|---|---|---|
| Comptage de triangles BVH utilisé comme verdict de socket | `Forearm/UpperArm` passait de 366 à 1661 triangles pour un enfoncement réel de **+0,31 mm** | verdict sur la profondeur nearest-surface, triangles conservés en diagnostic |
| `Body ↔ Foot` classé « socket » | recouvrement au repos = 0, ces paires ne doivent jamais se toucher | reclassé en dégagement, règle **plus stricte** |
| Fenêtre de balancier non bouclée | l'apex du pied droit de `SB_Sprint` (f7) tombait hors mesure | fenêtres bouclées, fin une image avant le contact |
| `rotation_difference().angle` lu brut | pics fantômes de 359,8° sur une main immobile | repli sur `360 − angle` |
| Ratio de continuité sans plancher absolu | un os immobile a une médiane nulle et produisait un ratio infini | seuil double : ratio > 4 **et** pic > 8° |
| `worst` élu par ratio seul | un os à ratio 999 et 4° masquait un os réellement saccadé | classement par qualification d'abord |

### Animation corrigée

| Défaut | Mesure | Correction |
|---|---|---|
| Roulé talon-pointe pendant l'appui | pénétration 5,3 mm **et** drift 56 mm | appui strictement plat : ce rig n'a pas de cheville |
| Levée verticale du pied | 98 mm dans le corps | balancier vers l'extérieur dimensionné sur la sphère |
| Pied écarté contre le poing | 39 mm | écartement des bras synchronisé sur le pied du même côté |
| Solveur de pose sans terme de collision | bras 135 mm dans le ventre sur **six** clips | pénalité de collision dans le coût ; poses re-résolues |
| Corrections image par image | sauts de 52,8° et 58,1° en une image sur Throw et Deposit | enveloppe à pente bornée (3°/image) au lieu d'une moyenne glissante |
| Catmull-Rom à paramétrisation uniforme | avec des clés à 1, 6, 11, 12, 17, 24, le segment d'une image recevait la tangente d'un segment de cinq → pic de 59° | paramétrisation non uniforme réelle |
| Pose résolue appliquée sous une autre inclinaison de corps | `reach` résolu à 20,95° appliqué à 9° remettait le poing dans le ventre | la pose du corps et les angles de bras voyagent ensemble |
| Bras s'ouvrant trop vite à la réception | 17,2° en une image contre une médiane de 1,1° | les bras suivent l'absorption au lieu de la mener → 5,7° |

## Sources et références intactes

| Fichier | SHA-256 | État |
|---|---|---|
| `Assets/_Project/Player/PersoBouleRigged.fbx` | `4503459d…1cce1` | inchangé, ouvert en lecture seule |
| `…/sandbox_character_SB_Idle_master.blend` | `864807e9…0464` | inchangé |

Dans la copie de travail, `SB_Idle` (100 courbes) et le placeholder
`BAS_PUNCH_Rig|BAS_PUNCH_Rig|BAS_PUNCH_punch` (109 courbes) sont **identiques au bit près** à la
référence, écart de valeur maximal `0.0` — preuve dans `evidence/reference-integrity.json`.

Rig préservé : 10 os, hiérarchie et bind pose inchangées, pieds toujours enfants directs de
`BAS_PUNCH_root`, 9 meshes rigides, **5 664 triangles**, **1 influence par vertex**, aucun os de
déformation ajouté.

## Mode d'exécution et écart déclaré

Toutes les créations et éditions d'Actions ont été faites dans une **session Blender 5.1.1
interactive** ouverte sur la copie de travail du pôle, via le serveur de l'addon BlenderMCP
(`127.0.0.1:9876`), avec une garde vérifiant avant chaque mutation et chaque sauvegarde que la
session pointe bien sur ce fichier. Les batchs `--factory-startup` n'ont servi qu'aux audits,
rendus, exports et réimports, sur des checkpoints sauvegardés.

**Écart déclaré** : le serveur MCP `blender` de Claude Code est enregistré sous une autre portée de
projet, donc ses outils ne sont pas liés dans une session lancée depuis `JEU/GAME`. Le client
`scripts/mcp_client.py` parle directement le protocole de l'addon — même session, même jeu de
commandes, même exécution sur le thread principal. C'est un écart de **shim client**, jamais de
mode : à aucun moment une génération batch n'a remplacé MCP.

## Limites restantes

1. **Le multiplicateur de lecture ×2,0 est une décision non prise.** Voir plus haut.
2. **Slots latéraux de port** : la main opposée reste à 13–19 cm de l'enveloppe. Consigné plutôt que
   corrigé, le code d'attache étant hors de ce pôle.
3. **La démarche est chaloupée par nécessité géométrique.** Si la revue humaine juge la lecture trop
   large, la seule autre issue est une modification du personnage, donc un nouveau projet
   `game-asset`, pas un réglage d'animation.
4. **Les frames de release sont visuelles.** `SB_Throw` f12, `SB_Drop` f9, `SB_Deposit` f15 ne
   portent aucun AnimationEvent ; aucun projectile ni règle n'est exporté.
5. **`SB_Punch` reste au lot forces/combat** et n'a pas été réexporté ici.
6. **Le jugement de goût n'est pas délégable.** Les portes prouvent le contrat, les contacts, la
   continuité et l'import. Elles ne prouvent pas que la marche a du caractère : cette lecture
   appartient à la revue humaine devant les playblasts.

## Intégration

Ce lot est un ensemble de **candidats pour revue humaine**, jamais un remplacement automatique du
runtime. Les FBX vivent dans `local_work/…/exports/` et l'import de contrôle dans
`Assets/_GeneratedLocal/SandboxAnimClaude/`, un espace jetable. Aucun Animator Controller, collider,
script réseau ou paramètre Animator n'a été touché.
