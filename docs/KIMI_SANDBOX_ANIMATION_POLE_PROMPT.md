# Prompt prêt à copier — Kimi

```text
Tu es responsable de tout le pôle « forces, poussée, combat et états de vie » du personnage sandbox.

MISSION

Produis les 7 Actions suivantes dans une seule mission autonome :

SB_Push, SB_WallPushed, SB_Punch, SB_HitReact, SB_Knockout, SB_KnockedOutLoop, SB_Recover.

Ne t'arrête pas après le premier clip et ne demande pas d'autorisation entre les clips. Valide et
checkpoint chaque Action séparément, puis continue automatiquement jusqu'à la septième. SB_Idle est
déjà validé : conserve-le comme référence commune sans le régénérer. Ne crée aucune Action du lot de
Claude : SB_Walk, SB_Sprint, SB_JumpTakeoff, SB_Airborne, SB_Land, SB_Pickup, SB_CarryIdle,
SB_CarryWalk, SB_Throw, SB_Drop, SB_Deposit.

AUTORITÉ ET LECTURES OBLIGATOIRES

1. Travaille depuis /Users/unrecorded/unrecorded/JEU/GAME.
   Tous les chemins ci-dessous sont relatifs à cette racine, sauf les commandes explicitement
   exécutées depuis tools/blender-agent-studio.
2. Utilise obligatoirement $blender-production-studio.
3. Dans tools/blender-agent-studio, lis intégralement AGENTS.md et sa chaîne obligatoire, en
   particulier standards/CORE_PRODUCTION_STANDARD.md, AGENT_HANDBOOK.md,
   knowledge/BLENDER_RULES_PRIORITY.md, knowledge/PHYSICAL_WORLD_OBJECT_RULES.md,
   knowledge/SCENE_TRIAL_EVALUATION_RULES.md, standards/RIG_ANIMATION_STANDARD.md,
   standards/profiles/rig-animation.json et knowledge/style-profiles/neutral-production.md.
4. Lis intégralement
   /Users/unrecorded/unrecorded/JEU/GAME/docs/SANDBOX_ANIMATION_HANDOFF.md et les preuves du candidat
   SB_Idle dans tools/blender-agent-studio/projects/team/sandbox-character-animation-v001/.
5. Si les fichiers references/animation-and-rig.md ou references/evidence-and-stop-gates.md cités
   par le skill sont absents de ce checkout, consigne cette limite documentaire et applique les
   standards présents ci-dessus ; n'invente pas leur contenu et ne bloque pas pour ce seul motif.

MODE D'EXÉCUTION MCP ET ISOLATION

La création et l'édition des animations doivent se faire par Blender MCP sur une copie de travail
délibérée. Les scripts batch ne sont permis qu'ensuite, sur une copie sauvegardée, pour les audits,
renders, exports et réimports isolés ; n'injecte jamais un workflow batch dans la scène MCP ouverte.

Depuis tools/blender-agent-studio :

- exécute python3 workflows/tools/studio_readiness_check.py ;
- exige ready_core=true, ready_for_animation_media=true et ready_for_interactive_mcp=true avant
  toute mutation de scène ;
- si mcp_port_open=false, tente seulement le démarrage normal de Blender 5.1.1 et de l'addon
  BlenderMCP déjà installé. Ne remplace pas silencieusement MCP par une génération batch. Si le port
  reste fermé, rends un blocage précis et ne touche à aucune scène ;
- avant chaque mutation et chaque sauvegarde, vérifie que la session MCP ouverte pointe vers ton
  propre fichier. Si elle montre le master de Claude, SB_Idle original ou le FBX runtime, arrête la
  mutation immédiatement.

Crée ou reprends exclusivement ce projet, seulement si son owner et ses chemins correspondent :

python3 workflows/tools/create_team_project.py \
  --id sandbox-character-force-combat-kimi-v001 \
  --type animation \
  --objective "Produire les 7 clips poussée, combat et états de vie du personnage sandbox" \
  --target "Unity 6000.3.20f1, rig Generic, gameplay réseau in-place" \
  --profile rig-animation \
  --style-profile neutral-production \
  --owner Kimi

Tes seuls espaces d'écriture sont :

- preuves, contrats et scripts texte :
  tools/blender-agent-studio/projects/team/sandbox-character-force-combat-kimi-v001/ ;
- .blend, exports, caches et médias lourds :
  tools/blender-agent-studio/local_work/sandbox-character-force-combat-kimi-v001/ ;
- import Unity temporaire : Assets/_GeneratedLocal/SandboxAnimKimi/ uniquement.

Ne modifie jamais Assets/_Project/, docs/SANDBOX_ANIMATION_HANDOFF.md, le projet de Claude, le projet
SB_Idle existant, un Animator Controller, un collider, une règle de gameplay, un script réseau ou un
paramètre Animator. Ne committe et ne pousse rien.

SOURCES IMMUABLES ET COPIE DE TRAVAIL

Source runtime à auditer sans écriture :
Assets/_Project/Player/PersoBouleRigged.fbx
SHA-256 attendu : 4503459d16ccc2af8ebc11b621850de3d1dae213d8d3f43420ae97f84231cce1

Référence SB_Idle validée à dupliquer, jamais à modifier en place :
tools/blender-agent-studio/local_work/sandbox-character-animation-v001/work/
sandbox_character_SB_Idle_master.blend
SHA-256 attendu : 864807e970705bf44a1c3dcbcfaac85102458917a5c8ccec90f5f36728590464

Sauvegarde immédiatement une copie sous le chemin exact :
tools/blender-agent-studio/local_work/sandbox-character-force-combat-kimi-v001/work/
sandbox_character_kimi_force_combat_master.blend

SB_Idle et ses courbes doivent rester inchangés dans cette copie. Garde une seule Action par clip,
avec Fake User, et un checkpoint versionné après chaque Action acceptée. Ne remplace jamais un
checkpoint antérieur. Tous les helpers non exportés portent le préfixe BAS_KIMI_.

RIG RÉEL À RESPECTER

- Blender 5.1.1 ; Unity 6000.3.20f1 ; 30 fps ; mètres ; Blender Z-up ; personnage face à -Y dans
  Blender et +Z dans Unity ; rig Unity Generic.
- 10 os réels, tous préfixés BAS_PUNCH_. Conserve exactement noms, hiérarchie, bind pose et axes.
- Le personnage n'a ni jambes ni genoux. Les deux pieds sont directement enfants de
  BAS_PUNCH_root. N'invente aucune articulation.
- Les neuf meshes sont des pièces rigides, avec une seule influence par vertex. Aucun squash,
  stretch ou skin lisse inventé.
- 5 664 triangles, plafond 6 000 ; 10 os, plafond 16 ; maximum 4 influences par vertex ; aucun
  nouvel os de déformation.
- BAS_PUNCH_root et l'objet armature restent strictement constants en position, rotation et scale.
  Le déplacement gameplay, le knockback et la poussée du mur viennent exclusivement de la simulation.

ORDRE DE PRODUCTION ET CONTRAT DES 7 ACTIONS

Construis d'abord les ancres de continuité dans cet ordre conseillé : Punch, HitReact, Push,
WallPushed, KnockedOutLoop, Knockout, Recover. Les noms et plages ci-dessous sont immuables.

1. SB_Punch — images 1–20 incluses, one-shot, 20 échantillons, durée attendue 19/30 s.
   Garde f1, anticipation f3–5, extension/impact visuel f10, suivi f11–13, récupération compatible
   Idle f20. Les poings ne traversent ni le corps ni l'autre bras. L'Action 24 fps existante
   BAS_PUNCH_Rig|BAS_PUNCH_Rig|BAS_PUNCH_punch est une référence de lisibilité seulement :
   ré-auteur et retime réellement à 30 fps ; ne te contente pas de changer le fps de scène.

2. SB_HitReact — images 1–18, one-shot, 18 échantillons, durée 17/30 s.
   Départ compatible Idle, impact perceptible f2–3, recul du volume du haut du corps et protection du
   visage jusqu'à f8, récupération compatible Idle f18. Pas de chute, pas de translation root.

3. SB_Push — images 1–30, boucle, 30 échantillons, durée 29/30 s.
   Le joueur agit : pieds écartés et stables, corps basculé vers l'avant autour de son vrai pivot,
   mains posées contre un plan proxy dérivé de la géométrie évaluée. Le léger effort cyclique ne fait
   ni pomper les mains ni glisser les appuis. Le plan proxy est une preuve et n'est jamais exporté.

4. SB_WallPushed — images 1–24, boucle, 24 échantillons, durée 23/30 s.
   Le joueur subit : volume du corps légèrement en retard sur la translation externe, bascule
   amortie, bras en contrepoids et petits pas alternés avec les pieds détachés. Le rig n'a pas de
   genoux : ne simule aucun pli de jambe. Le root reste in-place ; la simulation seule translate le
   personnage. La boucle doit rester crédible lorsque WallPushSpeed varie de 1 à 3,5 m/s, sans
   rejouer un impact à chaque couture et sans forte direction gauche/droite dans cette première passe.

5. SB_KnockedOutLoop — images 1–60, boucle, 60 échantillons, durée 59/30 s.
   Construis cette ancre avant les deux transitions. Corps clairement KO au sol, supports réels
   stables, respiration à peine visible, aucune dérive, couture continue. La lecture doit être KO,
   pas « Idle couché ». Conserve la pose f1 comme référence exacte des transitions.

6. SB_Knockout — images 1–30, one-shot, 30 échantillons, durée 29/30 s.
   Départ compatible Idle, rupture d'équilibre f1–8, descente contrôlée, premier contact au sol avant
   f22, stabilisation. F30 doit être mathématiquement identique à f1 de SB_KnockedOutLoop pour chaque
   os animé. Pas de téléportation root, pas de traversée du sol ni de pièce du corps.

7. SB_Recover — images 1–36, one-shot, 36 échantillons, durée 35/30 s.
   F1 doit être mathématiquement identique à f1 de SB_KnockedOutLoop. Appui des mains, redressement,
   reprise des pieds sous le corps avec les articulations réellement disponibles ; f36 doit être
   mathématiquement compatible avec la pose de référence SB_Idle. Aucun genou ou os fictif.

PARAMÈTRES DE PRÉSENTATION, PAS DE GAMEPLAY

SB_Push correspond au bool Push du joueur qui pousse. SB_WallPushed correspond au bool réservé
WallPushed de la victime, et WallPushSpeed est un float réservé de 0 à 3,5 m/s qui pourra moduler
l'intensité ou la vitesse de lecture. Ces deux paramètres ne sont pas encore exposés dans le code :
ne les ajoute pas. Punch, Hit, Knockout et Recover restent des triggers/états décidés par le serveur.
N'ajoute aucun AnimationEvent de dégâts, collision, dépense ou mouvement. Les frames d'impact ne sont
que des repères visuels pour l'intégration future.

MÉTHODE PAR ACTION — À RÉPÉTER 7 FOIS SANS PAUSE HUMAINE

1. Active uniquement l'Action cible. Pose d'abord les clés de lecture, inspecte face/profil/3-4,
   puis affine spacing, arcs et tangentes dans le Graph Editor. Reprends la méthode du coup de poing :
   anticipation/action/récupération lisibles, contrôle mesurable, puis export ; ne génère pas
   seulement des courbes sans revue visuelle.
2. Évalue toutes les images, sample_frame_step=1, sur les meshes déformés/évalués dans un repère
   déclaré. Verrouille avant correction : pénétration sol/décor max 0,002 m, écart d'un appui planté
   max 0,005 m, drift planté max 0,005 m et clearance swing min 0,010 m. Pour Push, mesure pieds/sol
   et mains/plan proxy ; pour KO/Recover, mesure chaque contact voulu et chaque collision corps/sol.
3. Compare les auto-intersections aux baselines du projet SB_Idle. Les pénétrations structurelles
   des sockets d'épaule existant dans la bind pose suivent une règle de non-aggravation ; ne prétends
   pas qu'elles sont nulles.
4. Pour une boucle, contrôle pose, rotation, vitesse et géométrie entre la fin et le début. Ne
   duplique pas visiblement f1 en dernière image. Pour Knockout/KO loop/Recover, ajoute une comparaison
   numérique os par os des poses d'interface demandées.
5. Sauvegarde un checkpoint versionné, puis exporte uniquement armature + neuf meshes skinnés vers
   local_work/sandbox-character-force-combat-kimi-v001/exports/<ACTION>_candidate.fbx. Un FBX
   contient exactement un take nommé comme l'Action ; Bake Animation à 30 fps, Simplify=0, aucune
   caméra, lumière, plain MeshRenderer, helper, plan proxy ou collider.
6. Réimporte chaque FBX dans une scène Blender factory-startup vide et compare plage, Action,
   squelette, transforms et poses clés au master.
7. Teste ensuite chaque candidat dans Unity 6000.3.20f1, Generic, via
   Assets/_GeneratedLocal/SandboxAnimKimi/ seulement. Le loop flag est un réglage d'importeur Unity,
   pas une propriété transportée de façon fiable par le FBX : applique et vérifie loopTime=true aux
   trois boucles Push, WallPushed et KnockedOutLoop, et false aux quatre one-shots. Vérifie clip
   unique, nom exact, 30 fps, nombre d'échantillons, durée, root immobile, 10 os, 5 664 triangles,
   maximum 4 influences, aucune caméra/lumière et aucun warning imputable au candidat.
8. Si Unity est verrouillé par l'autre agent, ne force pas, ne tue aucun processus et ne touche pas
   son dossier temporaire. Termine les validations Blender des autres clips, marque la gate Unity
   PENDING puis retente une fois le projet disponible. Aucun clip PENDING ne peut recevoir PASS final.
9. Produit pour chaque Action : playblast complet à 30 fps, boucles montrées au moins quatre fois,
   contact sheet des poses clés en face/profil/3-4, bande de couture pour les loops, JSON de mesures,
   réimport Blender, import Unity et verdict séparé.

CORRECTIONS ET ARRÊT

Corrige une seule catégorie à la fois et au maximum trois fois par clip. Après trois tentatives sans
amélioration démontrée, marque ce clip FAIL avec sa pire frame et continue les autres Actions. Arrête
tout le pôle uniquement pour une cause systémique : SHA source/référence différent, rig ou identité
cassé, workspace non isolé, session MCP appartenant à Claude, MCP indispensable indisponible, ou
export/réimport globalement non fonctionnel. Ne transforme jamais un FAIL ou PENDING en PASS.

LIVRAISON DU PÔLE

Construis un clip-manifest.json couvrant exactement les 7 Actions, un physical-validation.json par
clip ou un fichier structuré équivalent, les audits squelette/poids, les probes médias, les rapports
de réimport et une FINAL_REVIEW.md avec un tableau PASS/FAIL/PENDING. Enregistre le master et chaque
FBX dans le delivery manifest avec leurs SHA-256, sans --validated tant que toutes les gates du clip
concerné ne sont pas PASS. Exécute :

python3 workflows/tools/validate_team_project.py \
  projects/team/sandbox-character-force-combat-kimi-v001 --stage final

Puis exécute python3 tools/check_distribution_budget.py selon le contrat Studio. Ton message final doit
indiquer : les 7 verdicts individuels, chemins exacts, hashes, gates Unity, limites restantes et le
fait explicite que rien n'a été intégré dans Assets/_Project/. Le résultat est un lot de candidats
pour revue humaine et intégration centrale, jamais un remplacement automatique du runtime.
```
