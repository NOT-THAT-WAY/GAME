# Prompt prêt à copier — Claude / Opus 5

```text
Tu es responsable de tout le pôle « locomotion, verticalité et interactions d'objet » du personnage
sandbox. Claude et Opus 5 désignent ici le même agent : il n'existe pas de troisième lot.

MISSION

Produis les 11 Actions suivantes dans une seule mission autonome :

SB_Walk, SB_Sprint, SB_JumpTakeoff, SB_Airborne, SB_Land, SB_Pickup, SB_CarryIdle,
SB_CarryWalk, SB_Throw, SB_Drop, SB_Deposit.

Ne t'arrête pas après le premier clip et ne demande pas d'autorisation entre les clips. Valide et
checkpoint chaque Action séparément, puis continue automatiquement jusqu'à la onzième. SB_Idle est
déjà validé : conserve-le comme référence commune sans le régénérer. Ne crée aucune Action du lot de
Kimi : SB_Push, SB_WallPushed, SB_Punch, SB_HitReact, SB_Knockout, SB_KnockedOutLoop, SB_Recover.

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
  propre fichier. Si elle montre le master de Kimi, SB_Idle original ou le FBX runtime, arrête la
  mutation immédiatement.

Crée ou reprends exclusivement ce projet, seulement si son owner et ses chemins correspondent :

python3 workflows/tools/create_team_project.py \
  --id sandbox-character-motion-object-claude-v001 \
  --type animation \
  --objective "Produire les 11 clips locomotion, verticalité et objets du personnage sandbox" \
  --target "Unity 6000.3.20f1, rig Generic, gameplay réseau in-place" \
  --profile rig-animation \
  --style-profile neutral-production \
  --owner Claude

Tes seuls espaces d'écriture sont :

- preuves, contrats et scripts texte :
  tools/blender-agent-studio/projects/team/sandbox-character-motion-object-claude-v001/ ;
- .blend, exports, caches et médias lourds :
  tools/blender-agent-studio/local_work/sandbox-character-motion-object-claude-v001/ ;
- import Unity temporaire : Assets/_GeneratedLocal/SandboxAnimClaude/ uniquement.

Ne modifie jamais Assets/_Project/, docs/SANDBOX_ANIMATION_HANDOFF.md, le projet de Kimi, le projet
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
tools/blender-agent-studio/local_work/sandbox-character-motion-object-claude-v001/work/
sandbox_character_claude_motion_object_master.blend

SB_Idle et ses courbes doivent rester inchangés dans cette copie. Garde une seule Action par clip,
avec Fake User, et un checkpoint versionné après chaque Action acceptée. Ne remplace jamais un
checkpoint antérieur. Tous les helpers non exportés portent le préfixe BAS_CLAUDE_.

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
  Le déplacement gameplay vient exclusivement du moteur.

ORDRE DE PRODUCTION ET CONTRAT DES 11 ACTIONS

Tu peux construire les ancres dans cet ordre pour préserver les transitions : Walk, Sprint,
Airborne, JumpTakeoff, Land, CarryIdle, CarryWalk, Pickup, Throw, Drop, Deposit. Les noms et plages
ci-dessous sont immuables.

1. SB_Walk — images 1–30 incluses, boucle, 30 échantillons, durée attendue 29/30 s.
   Contact gauche f1, passage f8, contact droit f16, passage f23. Marche compacte et volontaire.
   Déclare la vitesse nominale du cycle ; pendant chaque appui, mesure le drift du pied dans un
   monde reconstruit qui ajoute cette translation virtuelle. Le root reste in-place.

2. SB_Sprint — images 1–24, boucle, 24 échantillons, durée 23/30 s.
   Contact gauche f1, suspension/passage f7, contact droit f13, suspension f19. Inclinaison et
   amplitude clairement supérieures à Walk. Déclare aussi sa vitesse nominale et valide les appuis
   dans le monde reconstruit, sans root motion.

3. SB_Airborne — images 1–24, boucle, 24 échantillons, durée 23/30 s.
   Pose aérienne stable, faible balancier des bras et pieds, aucun pédalage répétitif. Elle doit
   supporter plusieurs répétitions sans pop et fournir la pose de référence pour la fin de Takeoff.

4. SB_JumpTakeoff — images 1–12, one-shot, 12 échantillons, durée 11/30 s.
   Pose prête f1, compression maximale f4, extension maximale f8–9, fin compatible Airborne f12.
   La compression vient du corps et des pieds disponibles, jamais d'un genou imaginaire ni d'une
   translation du root.

5. SB_Land — images 1–12, one-shot, 12 échantillons, durée 11/30 s.
   Le gameplay le déclenche après le contact : f1 est déjà au sol, compression maximale vers f5,
   f12 compatible Idle/Walk. Aucun faux rebond ou saut avant contact.

6. SB_CarryIdle — images 1–60, boucle, 60 échantillons, durée 59/30 s.
   Même calme que SB_Idle, mais bras et mains stabilisent la zone d'objet devant le torse. Les mains
   dérivent très peu. Les props de contrôle Blender sont des proxies non exportés.

7. SB_CarryWalk — images 1–30, boucle, 30 échantillons, durée 29/30 s.
   Reprend exactement les phases et la vitesse nominale de SB_Walk, avec corps plus stable et zone
   portée cohérente. Ce clip couvre aussi le sprint porté par vitesse de lecture pour cette passe ;
   ne crée pas SB_CarrySprint.

8. SB_Pickup — images 1–24, one-shot, 24 échantillons, durée 23/30 s.
   Départ compatible Idle ; regard/lecture du sol, flexion et portée basse vers f8, prise visuelle
   f12, remontée f13–20, f24 identique ou directement compatible avec le début de CarryIdle.

9. SB_Throw — images 1–24, one-shot, 24 échantillons, durée 23/30 s.
   Départ CarryIdle f1, armé f4–7, accélération f8–11, release seulement visuel f12, suivi f13–17,
   retour sans objet compatible Idle f24. N'exporte ni projectile ni événement gameplay.

10. SB_Drop — images 1–18, one-shot, 18 échantillons, durée 17/30 s.
    Départ CarryIdle f1, ouverture des mains vers f6, release visuel f8–9, retrait léger des bras,
    retour sans objet compatible Idle f18.

11. SB_Deposit — images 1–30, one-shot, 30 échantillons, durée 29/30 s.
    Départ en port du trophée, présentation f1–10, extension vers la zone, release visuel f15,
    retrait des mains et retour sans objet compatible Idle f30.

PROXIES D'OBJETS À UTILISER POUR LA PREUVE, JAMAIS POUR L'EXPORT

Le code maintient le centre de l'objet en coordonnées locales Unity à
(side, y=0,86 m, z=+0,62 m), avec side=-0,16/0/+0,16 m selon le slot. L'équivalent Blender est
(x=side, y=-0,62 m, z=0,86 m). Teste au minimum :

- enveloppe caillou : 0,66 × 0,55 × 0,62 m ;
- enveloppe trophée/collider : 0,78 × 1,00 × 0,78 m ;
- les trois offsets latéraux de slot.

Le même clip doit fonctionner pour les deux objets. Ne force pas un contact exact des mains avec
toutes les enveloppes : exige une présentation lisible, une zone de prise stable et aucune grosse
intersection. Consigne les limites plutôt que de modifier le code d'attache.

MÉTHODE PAR ACTION — À RÉPÉTER 11 FOIS SANS PAUSE HUMAINE

1. Active uniquement l'Action cible. Pose d'abord les clés de lecture, inspecte face/profil/3-4,
   puis affine spacing, arcs et tangentes dans le Graph Editor. La méthode est celle utilisée pour
   le coup de poing : poses lisibles, anticipation/action/récupération, contrôle mesurable, puis
   export ; ne génère pas seulement des courbes sans revue visuelle.
2. Évalue toutes les images, sample_frame_step=1, sur les meshes déformés/évalués dans un repère
   déclaré. Verrouille avant correction : pénétration sol/décor max 0,002 m, écart d'un appui planté
   max 0,005 m, drift planté max 0,005 m et clearance swing min 0,010 m. Pour les locomotions, le
   drift planté est mesuré dans le monde reconstruit à la vitesse nominale, pas dans le local pur.
3. Compare les auto-intersections aux baselines du projet SB_Idle. Les pénétrations structurelles
   des sockets d'épaule existant dans la bind pose suivent une règle de non-aggravation ; ne prétends
   pas qu'elles sont nulles.
4. Pour une boucle, contrôle pose, rotation, vitesse et géométrie entre la fin et le début. Ne
   duplique pas visiblement f1 en dernière image. Pour un one-shot, contrôle exactement les poses de
   départ et de sortie demandées.
5. Sauvegarde un checkpoint versionné, puis exporte uniquement armature + neuf meshes skinnés vers
   local_work/sandbox-character-motion-object-claude-v001/exports/<ACTION>_candidate.fbx. Un FBX
   contient exactement un take nommé comme l'Action ; Bake Animation à 30 fps, Simplify=0, aucune
   caméra, lumière, plain MeshRenderer, helper ou proxy.
6. Réimporte chaque FBX dans une scène Blender factory-startup vide et compare plage, Action,
   squelette, transforms et poses clés au master.
7. Teste ensuite chaque candidat dans Unity 6000.3.20f1, Generic, via
   Assets/_GeneratedLocal/SandboxAnimClaude/ seulement. Le loop flag est un réglage d'importeur
   Unity, pas une propriété transportée de façon fiable par le FBX : applique et vérifie loopTime
   uniquement aux cinq boucles Walk, Sprint, Airborne, CarryIdle et CarryWalk, et false aux six
   one-shots. Vérifie clip unique, nom exact, 30 fps, nombre d'échantillons,
   durée, root immobile, 10 os, 5 664 triangles, maximum 4 influences, aucune caméra/lumière et aucun
   warning imputable au candidat.
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
cassé, workspace non isolé, session MCP appartenant à Kimi, MCP indispensable indisponible, ou
export/réimport globalement non fonctionnel. Ne transforme jamais un FAIL ou PENDING en PASS.

LIVRAISON DU PÔLE

Construis un clip-manifest.json couvrant exactement les 11 Actions, un physical-validation.json par
clip ou un fichier structuré équivalent, les audits squelette/poids, les probes médias, les rapports
de réimport et une FINAL_REVIEW.md avec un tableau PASS/FAIL/PENDING. Enregistre le master et chaque
FBX dans le delivery manifest avec leurs SHA-256, sans --validated tant que toutes les gates du clip
concerné ne sont pas PASS. Exécute :

python3 workflows/tools/validate_team_project.py \
  projects/team/sandbox-character-motion-object-claude-v001 --stage final

Puis exécute python3 tools/check_distribution_budget.py selon le contrat Studio. Ton message final doit
indiquer : les 11 verdicts individuels, chemins exacts, hashes, gates Unity, limites restantes et le
fait explicite que rien n'a été intégré dans Assets/_Project/. Le résultat est un lot de candidats
pour revue humaine et intégration centrale, jamais un remplacement automatique du runtime.
```
