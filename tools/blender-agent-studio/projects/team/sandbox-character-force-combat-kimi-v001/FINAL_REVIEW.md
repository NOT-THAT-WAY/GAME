# Revue finale — pôle forces, poussée, combat et états de vie

Sept Actions produites, validées et checkpointées séparément. `SB_Idle` a servi de référence et n'a
pas été régénéré. Aucune Action du lot locomotion/objets n'a été créée dans ce projet.

**Reprise de pôle.** Kimi a produit les premières versions de `SB_Punch`, `SB_HitReact` et six
passes sur `SB_Push` avant d'épuiser son budget. Ses checkpoints et ses preuves sont conservés dans
`local_work/.../checkpoints/master_ckpt*.blend` et `evidence/SB_*/`. Les sept clips livrés ici ont
été réauthorés avec un pipeline unique afin que toutes les preuves proviennent du même instrument :
comparer sept clips mesurés par deux chaînes différentes n'aurait pas donné un verdict cohérent.
Le diagnostic de Kimi sur `SB_Push` — « ouvrir le coude dégage l'épaule » — s'est révélé exact et a
été intégré comme second degré de liberté de la passe de dégagement.

## Verdict

**7 clips sur 7 : PASS sur les cinq portes du contrat.** Un contrôle supplémentaire de continuité,
ajouté par ce pôle et non exigé par le contrat, signale `SB_Knockout` ; l'attribution est prouvée
plus bas. Rien n'a été commité, poussé, ni écrit sous `Assets/_Project/`.

| Clip | Plage | Durée | Loop | Contrat | Physique | Réimport | Unity | Preuve | Verdict | Continuité |
|---|---:|---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `SB_Punch` | 1–20 | 0,63333 s | non | PASS | PASS | PASS | PASS | PASS | **PASS** | PASS |
| `SB_HitReact` | 1–18 | 0,56667 s | non | PASS | PASS | PASS | PASS | PASS | **PASS** | PASS |
| `SB_Push` | 1–30 | 0,96667 s | oui | PASS | PASS | PASS | PASS | PASS | **PASS** | PASS |
| `SB_WallPushed` | 1–24 | 0,76667 s | oui | PASS | PASS | PASS | PASS | PASS | **PASS** | PASS |
| `SB_KnockedOutLoop` | 1–60 | 1,96667 s | oui | PASS | PASS | PASS | PASS | PASS | **PASS** | PASS |
| `SB_Knockout` | 1–30 | 0,96667 s | non | PASS | PASS | PASS | PASS | PASS | **PASS** | **FAIL** |
| `SB_Recover` | 1–36 | 1,16667 s | non | PASS | PASS | PASS | PASS | PASS | **PASS** | PASS |

Chaque durée vaut exactement `(n − 1) / 30`. `loopTime = true` sur les trois boucles, `false` sur
les quatre one-shots, appliqué puis relu côté importeur Unity. Aucun avertissement Unity imputable
à un candidat.

## Les raccords KO sont exacts, pas approchés

Le brief exige trois poses identiques. Elles le sont au zéro machine, vérifiées **après** la passe
de dégagement qui édite les poses image par image :

| Comparaison | Écart de position | Écart de rotation |
|---|---:|---:|
| `SB_Knockout` f30 → `SB_KnockedOutLoop` f1 | **0,0000000 m** | **0,00000°** |
| `SB_Recover` f1 → `SB_KnockedOutLoop` f1 | **0,0000000 m** | **0,00000°** |

Tolérances déclarées : 0,001 m et 0,01°. Preuve : `evidence/interface-poses.json`.

## Mesures principales

Géométrie évaluée, `sample_frame_step = 1`, repère déclaré `world_blender`.

| Mesure | Seuil | Pire valeur sur les 7 clips |
|---|---:|---:|
| Pénétration sol | ≤ 0,002 m | **0,000000 m** |
| Drift d'un appui planté | ≤ 0,005 m | **0,000000 m** |
| Clearance d'un pied en swing | ≥ 0,010 m | 0,072 m |
| Translation du root | ≈ 0 | **0,000000 m** |
| Rotation du root | ≈ 0 | **0,000000°** |
| Aggravation d'un socket d'épaule | ≤ 0,020 m | +0,001405 m |
| Paires de dégagement en contact | 0 | **0** |
| Pompage des mains sur le mur (`SB_Push`) | ≤ 0,010 m | **0,008257 m** |

## Le plan de poussée est dérivé, jamais exporté

`SB_Push` demande des mains en appui contre un plan. Aucun objet plan n'existe : le plan est
**déduit** de la position réelle des poings évalués, `y = −1,029753`, et ne vit que dans
`evidence/push-proxy-plane.json`. Le contrôle utile n'est pas le plan mais l'écart des mains à ce
plan sur le cycle : **8,26 mm**, sous le budget de 10 mm.

Ce contrôle a d'abord échoué à 23,7 mm. Ma compensation de bras avait le **signe inversé** : `+rx`
penche le corps en avant mais fait reculer un bras, si bien que la correction s'ajoutait au
mouvement au lieu de l'annuler. Le signe corrigé n'a pas suffi — le corps pivote à `z = 0,30` et
l'épaule à `z = 0,92`, deux bras de levier différents dont la différence ne peut pas s'annuler
exactement. L'amplitude du cycle a donc été calibrée sur la mesure jusqu'à tenir le budget.

## Le KO est posé au sol, pas suspendu au-dessus

`SCENE_TRIAL_EVALUATION_RULES.md` interdit de confondre « aucune pénétration » et « contact ». La
première pose KO ne pénétrait rien — et flottait **2,69 cm au-dessus du sol**. Le seuil a été
descendu depuis la mesure, pas depuis l'estimation analytique : `−0,045` laissait 26,9 mm d'air,
`−0,0719` enfonçait 2,9 mm, le contact tient à `−0,0685`.

Le corps du personnage, pas ses pieds, est le support : c'est une sphère basculée de 50° sur son
arrière, pieds en l'air. `SB_KnockedOutLoop` touche dès l'image 1 avec `min_z = 0,00052 m`, et la
respiration ne peut que soulever — une oscillation symétrique aurait traversé le sol.

`SB_Knockout` exige un premier contact **avant l'image 22** : mesuré à **f19**. La première version
tombait à f24, et la descente a été avancée plutôt que l'exigence réinterprétée.

## Limite anatomique mesurée : pas de direct croisé

Les épaules sont à `x = ±0,52` pour un bras de 0,70 m. Un poing **ne peut pas** franchir la ligne
médiane sans traverser le corps : le solveur, avec sa pénalité de collision, s'arrête à
**0,257 m** de la cible centrale. `SB_Punch` frappe donc de son propre côté, poing droit en
extension, poing gauche en garde. Ce n'est pas un choix de style, c'est ce que le rig permet.

## SB_Knockout : le seul contrôle en échec, et sa cause prouvée

Le contrôle de continuité mesure le plus grand pas image-à-image d'un os, rapporté à la médiane du
clip. `SB_Knockout` pique à **9,54° à l'image 5** (médiane 1,42°), au-dessus du plancher de 8°.

Trois corrections ont été tentées : clé intermédiaire, réduction des amplitudes, échelonnement du
contrepoids. Résultats successifs 9,92° → 9,50° → 9,69° → 9,54° : **pas d'amélioration démontrée
sur trois essais**, ce qui déclenche l'arrêt prévu par le contrat.

Avant de qualifier, l'attribution a été prouvée. Le clip a été réauthoré avec la passe de
dégagement **désactivée** : le pic est **identique**, 9,54° à l'image 5. Il est donc entièrement
authoré — c'est l'accélération de la chute — et non un artefact de correction. 9,54°/image vaut
286°/s pour un avant-bras pendant une chute, ce qui est modeste ; le ratio est élevé seulement
parce que le dernier tiers du clip est presque immobile pendant que le corps se stabilise.

**Ce contrôle reste marqué FAIL. Il n'a pas été converti, et le seuil n'a pas été élargi.** La
décision d'accepter cet accent appartient à la revue humaine.

## Défauts trouvés et corrigés

### Instruments corrigés

| Défaut | Conséquence | Correction |
|---|---|---|
| Solveur de pose échantillonnant 1 vertex sur 8 | garde et poussée déclarées propres puis en collision de 8 à 22 mm | passe de raffinement finale à pleine résolution |
| Cible de garde à `y = −0,50` | la sphère est à `y = −0,470` à cette hauteur et le poing fait 0,146 de rayon : la pose était condamnée dès la cible | garde reciblée hors de la sphère |
| Passe de dégagement ne retenant que l'amplitude d'épaule | le repli réappliquait une autre ouverture de coude que celle qui avait dégagé l'image | le couple épaule/coude est mémorisé |
| Enveloppe lissée imposée même quand elle recrée un contact | images livrées en collision au nom de la douceur | repli sur le minimum connu, contact prioritaire |

### Animation corrigée

| Défaut | Mesure | Correction |
|---|---|---|
| Épaule seule pour dégager la poussée | 30 images sur 30 non résolues | ouverture du coude ajoutée comme second degré de liberté |
| Compensation de bras de signe inversé | pompage des mains 23,7 mm | signe corrigé puis amplitude calibrée à 8,26 mm |
| Corps KO flottant | 26,9 mm au-dessus du sol | assise dérivée de la mesure |
| Premier contact du KO trop tardif | f24 contre f22 exigé | descente avancée, mesuré f19 |
| Affaissement entre la pose d'assise et l'ancre | 2,9 mm sous le sol images 23–27 | clés d'encadrement à f23 et f27 |
| Garde sollicitée sous une inclinaison de corps inverse | avant-bras 18 mm dans le torse | garde allégée et écartée pendant le recul |
| Pieds dérivant dans la fenêtre d'appui déclarée | 11,7 mm et 12,1 mm | pieds fixés image par image sur toute la fenêtre |

## Sources et références intactes

| Fichier | SHA-256 | État |
|---|---|---|
| `Assets/_Project/Player/PersoBouleRigged.fbx` | `4503459d…1cce1` | inchangé, lecture seule |
| `…/sandbox_character_SB_Idle_master.blend` | `864807e9…0464` | inchangé |

Dans la copie de travail, `SB_Idle` (100 courbes) et le placeholder Punch 24 fps (109 courbes) sont
**identiques au bit près** à la référence, écart maximal `0.0` — `evidence/reference-integrity.json`.

Rig préservé : 10 os, hiérarchie et bind pose inchangées, pieds enfants directs de `BAS_PUNCH_root`,
9 pièces rigides, **5 664 triangles**, **1 influence par vertex**, aucun os ajouté, aucun genou
simulé.

## Mode d'exécution

Toutes les Actions ont été créées dans une **session Blender 5.1.1 interactive** ouverte sur le
master de ce pôle, via le serveur de l'addon BlenderMCP sur le port **9880** — la session lancée par
Kimi, restée vivante et vérifiée avant chaque mutation et chaque sauvegarde par une garde qui refuse
tout fichier appartenant à l'autre pôle. Les batchs `--factory-startup` n'ont servi qu'aux audits,
rendus, exports et réimports sur des checkpoints sauvegardés.

**Écart déclaré** : le serveur MCP `blender` de Claude Code est enregistré sous une autre portée de
projet, donc ses outils ne sont pas liés dans une session lancée depuis ce dépôt. Le client
`scripts/pipeline/mcp_client.py` parle directement le protocole de l'addon : même session, mêmes
commandes, même exécution sur le thread principal. Écart de **shim client**, jamais de mode.

## Limites restantes

1. **`SB_Knockout` ne passe pas le contrôle de continuité**, avec preuve que le pic est authoré.
   Décision humaine.
2. **Pas de direct croisé**, limite anatomique mesurée à 0,257 m.
3. **`WallPushed` est neutre en direction** pour cette passe : une seule réaction, sans variante
   gauche/droite, conformément au contrat.
4. **`WallPushed` et `WallPushSpeed` ne sont pas exposés par le code.** Ils sont réservés par le
   handoff ; aucun paramètre Animator n'a été ajouté.
5. **Les images d'impact sont visuelles.** `SB_Punch` f10, `SB_HitReact` f3 ne portent aucun
   AnimationEvent : ni dégâts, ni collision, ni dépense.
6. **Le plan de poussée n'existe pas en tant qu'objet** ; il est reconstruit par la mesure et ne
   pourra pas être réutilisé tel quel par l'intégration sans être redéclaré.
7. **Le jugement de goût n'est pas délégable.** Les portes prouvent le contrat, les contacts, les
   raccords et l'import. Elles ne prouvent pas qu'un KO est drôle ou qu'un coup fait mal.

## Intégration

Lot de **candidats pour revue humaine**, jamais un remplacement automatique du runtime. Les FBX
vivent dans `local_work/…/exports/` et l'import de contrôle dans
`Assets/_GeneratedLocal/SandboxAnimKimi/`, un espace jetable. Aucun Animator Controller, collider,
script réseau ou paramètre Animator n'a été touché.
