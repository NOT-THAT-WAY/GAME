# Matrice de tests et responsabilités

> Baseline : `main` à `6b565f0`, 9 août 2026. Cette matrice complète le
> [plan maître](EXECUTION_PLAN.md) et le [backlog prêt à distribuer](READY_BACKLOG.md).

Les preuves de gate sont produites depuis un clone ou worktree propre au SHA gelé. Le workspace de
préparation courant contient des changements documentaires et ne constitue pas un environnement de
preuve.

## Principe

Un test possède quatre rôles. Une même personne peut préparer et opérer un test local, mais elle ne
peut pas être à la fois producteur du changement et approbateur indépendant.

| Rôle | Responsabilité |
|---|---|
| préparateur | écrit la procédure, les fixtures, l’instrumentation et le format de preuve |
| opérateur | exécute sur la machine, le compte ou le réseau demandé |
| témoin | reproduit ou observe sans corriger silencieusement pendant le test |
| approbateur | compare au critère fixé et prononce `PASS`, `FAIL` ou `BLOCKED` |

Codex peut préparer, automatiser, analyser et corriger. Il n’occupe jamais seul la case témoin ou
approbateur d’un changement qu’il a produit. Une sortie Python, une CI verte ou un beau rendu est une
preuve technique ciblée, pas une acceptation produit.

## HT-00 — smoke avant les gates

HT-00 n’est pas une gate et n’exige pas les rotations formelles ci-dessous. Un membre disponible suit
les commandes affichées pendant 3–5 minutes ; le log porte l’essentiel de la preuve.

| ID | Observation | Préparateur | Opérateur | Sortie |
|---|---|---|---|---|
| HT-00-A | build/UI/récupération praticables | Codex | membre disponible | `READY`, warning ou blocker |
| HT-00-B | actions jouables minimales | Codex | membre disponible | marqueurs `[GAME-SMOKE]` |
| HT-00-C | absence de panne bloquante | Codex | membre disponible | rapport `PASS / INCOMPLETE / FAIL` |

La [checklist](FIRST_HUMAN_TEST_DESIGN.md) fixe les seules actions manuelles et le
[runbook](FIRST_HUMAN_TEST_RUNBOOK.md) prépare les artifacts locaux.

## Rotations humaines

Les rotations évitent de faire de Nils l’unique approbateur ou de Sean le testeur permanent du
réseau.

| Rotation | Opérateur | Témoin | Approbateur | Usage naturel |
|---|---|---|---|---|
| R-A | Zak | Sean | Nils | topologie, réseau, joueur, Windows |
| R-B | Sean | Nils | Zak | graybox, art, UI, lisibilité |
| R-C | Nils | Zak | Sean | dépôt, DVC, CI, audio, données |

Pour un test à trois machines, les trois deviennent opérateurs. L’approbation revient au membre qui
n’a pas écrit le composant principalement testé ; si tous ont contribué, une seconde exécution ou un
testeur externe est obligatoire.

### Rotation des hôtes réseau

| Passage | Hôte | Client Mac | Client Windows | But |
|---|---|---|---|---|
| M0-A | Zak sur Mac | Nils | Sean ou propriétaire réel du PC | preuve distante initiale |
| M1-B | propriétaire du PC Windows | Zak | autre poste disponible | détecter dépendance au rôle/OS |
| M1-C | Nils sur Mac | Zak | propriétaire du PC | arrivée tardive et reconnexion |

Si l’affectation matérielle réelle diffère, conserver les trois principes : un hôte Mac, un hôte
Windows avant G3, et un opérateur qui n’a pas produit la dernière correction réseau.

### Prévol obligatoire d’une session de preuve

Sur chaque Mac, depuis le clone propre :

```bash
git rev-parse HEAD
git status --porcelain=v1
git lfs fsck
./scripts/doctor-macos.sh
./scripts/validate-repository.sh
```

Sur Windows, depuis PowerShell puis Git Bash pour le validateur :

```powershell
git rev-parse HEAD
git status --porcelain=v1
git lfs fsck
powershell -ExecutionPolicy Bypass -File .\scripts\doctor-windows.ps1
bash ./scripts/validate-repository.sh
```

Le SHA doit être identique sur tous les postes, `git status --porcelain=v1` doit être vide et chaque
doctor doit être sans `[FAIL]`. Un build distribué reçoit un SHA-256 avant transfert ; le receveur
vérifie ce hash au lieu de reconstruire silencieusement un autre binaire.

## Niveaux de preuve

| Niveau | Exemple | Suffit pour |
|---|---|---|
| L0 — statique | parse, schéma, contrat, diff, secret scan | autoriser la revue |
| L1 — automatisé Unity | compilation, EditMode, PlayMode | valider le modèle et les fixtures |
| L2 — local cible | build Mac/Windows lancé, import Unity exact | valider une plateforme |
| L3 — distribué | plusieurs machines, late join, réseau dégradé | valider un état partagé |
| L4 — humain métier | lisibilité, déformation, audio, UX | accepter un contenu ou une interaction |
| L5 — produit externe | playtest sans coaching de l’auteur | décider du fun |

Une gate exige tous les niveaux qui la concernent. L3 ne remplace pas L1 ; L5 ne doit pas servir à
découvrir un défaut de build déjà testable en L2.

## Matrice commune par PR

| ID | Test | Préparateur | Opérateur | Témoin/approbateur | Fréquence | Preuve |
|---|---|---|---|---|---|---|
| REP-01 | `validate-repository.sh` | Codex/Nils | auteur de la PR | CI puis intégrateur | chaque PR | log vert, commit |
| REP-02 | politique branche/titre/corps PR | Codex | auteur | Nils ou suppléant | chaque PR | check GitHub, corps rempli |
| REP-03 | diff propre Unity/DVC/LFS | Codex | auteur | binôme | chaque PR | `git status`, `dvc status`, LFS si touché |
| SEC-01 | secret et chemin sensible | Codex/Zak | auteur | Zak ou Nils hors PR | chaque PR sensible | rapport sans valeur secrète |
| DOC-01 | liens et contrat documentaire | Codex | auteur | binôme | docs/ADR | validateur de liens et lecture |
| UNI-01 | compilation assemblies | Codex | auteur puis CI | binôme | chaque PR C# | log Unity sans erreur |
| UNI-02 | EditMode | Codex | auteur puis CI | binôme | modèle/données | XML + code de sortie |
| UNI-03 | PlayMode | Codex | auteur puis CI | testeur | scène/prefab/runtime | XML, scénario et capture utile |

Règle : une CI rouge bloque. Un opérateur ne relance pas jusqu’au vert sans conserver la première
cause ; la correction reste sur la même branche.

## G0 — dépôt, droits et workflow

| ID | Cible | Opérateur | Témoin | Approbateur | Protocole | Critère de passage |
|---|---|---|---|---|---|---|
| G0-01 | visibilité/licence | Nils | Zak | Sean | API GitHub + document de décision | état public/privé et droit de diffusion cohérents |
| G0-02 | protection `main` | Nils | Sean | Zak | tentative depuis rôle Write | push direct refusé, check requis |
| G0-03 | rôles GitHub | Nils | Zak | Sean | API collaborateurs | un/deux Admin max, droits quotidiens suffisants |
| G0-04 | PR humaine | Sean | Zak | Nils | branche fixture valide/invalide | bon cas vert, mauvais cas rouge, corps non vierge |
| G0-05 | Dependabot | Nils | Codex analyse | Zak | PR bot ou fixture équivalente | politique satisfaite sans bypass large |
| G0-06 | droits du contenu | Sean + Zak | Nils | propriétaire/ayant droit | registre + preuves privées | aucune redistribution `unknown` |
| G0-07 | secret factice | Zak | Nils | Sean | fixture temporaire non poussée | détecté sans imprimer la valeur |

Les réglages GitHub et décisions de licence sont humains. Codex peut générer les appels ou les
documents après autorisation, mais ne choisit pas la politique.

## G1 — machines, build, réseau et DVC

| ID | Cible | Opérateur | Témoin | Approbateur | Commande/protocole | Preuve |
|---|---|---|---|---|---|---|
| PROV-01 | identité du build | Codex puis auteur du build | Nils | Zak | marqueur runtime + manifest complet | même `buildId`, commit propre et bundle hashé dans tous les logs |
| ENV-01 | second Mac propre | Sean | Nils | Zak | doctor, deux ouvertures, build | aucun `[FAIL]`, aucun diff Unity |
| ENV-02 | Windows IL2CPP | propriétaire PC avec Zak | Nils | Sean | `first-test-windows.ps1 Manual -BuildOnly -TestProfile Connection` | exe lancé, log, commit/Unity |
| NET-01 | roster distant à trois | trois membres | rotation M0-A | Nils | `remote-test-*`, profil connection | trois noms sur trois écrans, sans IP publiée |
| NET-02 | reconnexion simple | client non-auteur | hôte | troisième membre | fermer/rejoindre sans rebuild | roster nettoyé puis restauré |
| DVC-01 | push premier lot | Nils | Sean | Zak | track → push → Git | pointeur seulement, hash enregistré |
| DVC-02 | restore cache vide Mac | Nils | Sean | Zak | pull ciblé | contenu/hash identiques |
| DVC-03 | restore cache vide Windows | Zak/PC | Nils | Sean | pull ciblé | contenu/hash identiques |
| DVC-04 | contenu métier restauré | Sean | Nils | Zak | ouvrir copie/restauration lecture seule | source exploitable, dépendances présentes |
| DVC-05 | seconde copie/versioning | Nils | Zak | Sean | restauration d’une version antérieure | version récupérable, procédure écrite |

Les logs bruts restent sous `Logs/` ou dans un artifact privé à rétention courte. L’issue publique ne
reçoit que commit, OS, rôle, résultat, durée et la sortie de `scripts/network-log-report.py`.

## G2 — topologie, collision et scène grise

| ID | Test | Producteur | Opérateur indépendant | Approbateur | Critère |
|---|---|---|---|---|---|
| TOP-01 | JSON valide/invalides | Codex + Zak | Nils | Sean | erreurs déterministes, aucun parse partiel |
| TOP-02 | canonicalisation/checksum | Codex + Zak | Mac Nils + Windows propriétaire/Zak | Sean | bytes/checksum identiques |
| TOP-03 | IDs stables | Zak | Sean | Nils | ordre/noms visuels sans effet sur IDs |
| TOP-04 | connectivité/spawns | Codex | Sean | Zak | cas coupés/dupliqués/hors bornes refusés |
| COL-01 | colliders depuis schéma | Codex + Zak | Sean | Nils | aucun collider gameplay issu du FBX |
| COL-02 | arc balayé du mur | Zak | Nils | Sean | collision traversée détectée avant acceptation |
| GRY-01 | génération/scene propre | Codex + Sean | Nils depuis clone propre | Zak | résultat déterministe et aucun diff parasite |
| GRY-02 | deux joueurs sans déblocage | Zak + Sean | Nils | Sean | déplacement/interaction sans téléport de secours |
| GRY-03 | lisibilité pivot | Sean | testeur briefé sur commandes/objectif | Nils | côté, état et action compris sans indice ajouté au jeu |

TOP-01 à COL-02 sont des tests de vérité logique. Une belle représentation du pivot ne peut pas
faire passer un checksum, une collision ou une connectivité en échec.

## G3 — murs, joueur et autorité réseau

| ID | Test | Opérateur principal | Témoin | Approbateur | Critère |
|---|---|---|---|---|---|
| WALL-01 | état du mur 30/60/120 FPS | Nils | Zak | Sean | même tick/pose logique/révision |
| WALL-02 | arrivée tardive en mouvement | rotation M1-C | autre client | Sean | état correct dès snapshot |
| WALL-03 | révision ancienne | test automatisé | Zak | Nils | aucune régression d’état |
| WALL-04 | portée/LOS/côté/couple | Sean black-box | Zak | Nils | intentions invalides refusées |
| WALL-05 | joueur dans l’arc | Zak | Sean | Nils | politique ADR appliquée identiquement |
| INP-01 | clavier/souris | Sean | Nils | Zak | aucune lecture directe hors adaptateur |
| INP-02 | manette/focus multi-instance | Sean | Zak | Nils | bindings et focus reproductibles |
| PLY-01 | simulation par tick | tests EditMode | Zak | Sean | séquences déterministes |
| PLY-02 | prediction/reconcile | hôte Mac puis Windows | troisième machine | Sean | corrections bornées, serveur faisant foi |
| INT-01 | spam/hors portée/énergie | Sean black-box | Zak | Nils | aucun gain par fréquence RPC |
| NET-03 | `80 ms / 2 % / 20 ms` | Nils | Zak | Sean | aucune divergence critique |
| NET-04 | session 20 minutes | trois membres | logs comparés par Codex | membre non-auteur | deux manches/rejoins sans relance |
| MAP-01 | intégration 16x16 | Sean | Zak | Nils | checksum/collisions identiques, FBX visuel seul |

La preuve réseau compare tick, checksum, révisions et états. “Les écrans ont l’air synchronisés” ne
suffit pas.

## Assets Blender/Unity

| ID | Test | Producteur | Opérateur/témoin | Approbateur | Preuve requise |
|---|---|---|---|---|---|
| ART-01 | source immuable et droits | Sean | Nils | Zak | ID, hash, provenance, lot DVC |
| ART-02 | package studio | Codex/Sean | Nils | Zak | contrat/projet textuel valide |
| ART-03 | échelle/axes/pivot | Codex | Sean | Zak | mesures Blender + Unity exact |
| ART-04 | géométrie/normales/UV/tangentes | Sean | Codex mesure | Nils | rapport, warnings et limites |
| ART-05 | rig/poids/poses extrêmes | Sean | Codex audit frame/pose | Nils | mesh évalué, influences, déformations |
| ART-06 | clip complet/réimport | Sean | Nils Unity | Zak | fps/durée/events, playblast, Unity |
| ART-07 | budget runtime | Sean + Nils | Zak sur cible | Nils | tris/LOD/materials/mémoire mesurés |
| ART-08 | lisibilité gameplay | Sean | testeur non briefé | Nils | silhouette/affordance à distance cible |

Ordre obligatoire : audit source → contrat → blockout → structure/physique → matériau/rig → export →
réimport indépendant → Unity exact → revue humaine. Un FBX réouvert dans Blender n’est pas une preuve
Unity. Aucun master `.blend`, texture source, rendu ou cache n’entre dans Git ; seuls export runtime,
`.meta`, registre et preuves textuelles approuvées y entrent.

## G4 — performance, audio, UX et playtests

| ID | Test | Opérateur | Témoin | Approbateur | Critère |
|---|---|---|---|---|---|
| PERF-01 | CPU/physique/rendu/mémoire | Zak sur Windows | Nils | Sean | budgets déclarés, pires frames citées |
| PERF-02 | scène grise vs 16x16 | Zak | Sean | Nils | coût du contenu séparé du gameplay |
| UI-01 | clavier/manette/résolutions | Sean | Zak Windows | Nils | navigation et lecture sans blocage |
| UI-02 | FOV/sensibilité/inversion/volume | Sean | Nils | Zak | réglages appliqués et persistants selon contrat |
| AUD-01 | événement Wwise Mac | Nils | Sean | Zak | événement correct dans build |
| AUD-02 | événement Wwise Windows | Zak | Nils | Sean | même banque/version, aucun warning bloquant |
| TEL-01 | événement de session factice | Codex/Nils | Zak | Sean | données minimales et agrégables |
| TEL-02 | suppression/anonymisation | Nils | Zak | Sean | aucune IP/voix/ID plateforme conservé |
| PLAY-01 | vague 1v1 | joueurs externes | Sean modère, Nils observe | Zak sépare incidents réseau | protocole identique, aucun coaching de l’auteur |
| PLAY-02 | correction unique | auteur du correctif | testeurs vague suivante | troisième membre | hypothèse avant/après mesurable |
| PLAY-03 | vague 2v2 | joueurs externes | rôles équipe tournants | décision commune | rapport `GO/ITERATE/STOP` |

Le modérateur ne doit pas expliquer le pivot avant de mesurer sa compréhension. Les problèmes de
réseau, de lisibilité et de plaisir sont codés séparément.

## Calendrier des sessions communes

| Session | Durée cible | Participants | Déclencheur | Sortie |
|---|---:|---|---|---|
| S0 — gouvernance | 45 min | Nils, Zak, Sean | documents/options prêts | décisions G0 et propriétaires |
| S1 — M0 machines | 90 min | trois postes | doctors/builds prêts | ENV/NET/DVC pass/fail |
| S2 — topologie/graybox | 60 min | trois membres | TOP/COL automatisés verts | gate G2 |
| S3 — autorité réseau | 120 min | trois postes | murs+joueur intégrés | late join, dégradé, 20 min |
| S4 — playtest interne à blanc | 60 min | équipe, rôles externes simulés | G3 vert | protocole M2 corrigé, pas le gameplay |
| S5 — vague 1 | selon GAME-01 | joueurs externes | build gelé | données/observations |
| S6 — vague 2 | selon GAME-01 | joueurs externes | correctif gelé | verdict M2 |

Les sessions sont réservées dès que la dépendance précédente devient verte. Une session annulée pour
build rouge redevient une tâche technique ; elle n’est pas transformée en réunion de debug à trois.

## Ordre détaillé de la session QA-01

1. Geler le SHA et produire les manifests de build Mac/Windows depuis ce même SHA.
2. Exécuter un smoke de cinq minutes sur chaque type d’hôte, sans changer le build ; répéter
   seulement si un défaut intermittent est observé.
3. Jouer 20 minutes avec hôte Windows et deux clients Mac.
4. Jouer 20 minutes avec hôte Mac et client Windows, puis répéter sous réseau dégradé.
5. Tester séparément `30`, `60`, puis `120 FPS` avant d’ajouter la dégradation réseau.
6. À `60 FPS` fixe, appliquer `80 ms RTT / 2 % perte / 20 ms jitter`.
7. Inclure une arrivée tardive à chaque rotation et deux reconnexions volontaires.
8. Comparer tick, checksum, révision, états joueur/mur et nombre de reconciliations.

Changer à la fois framerate et réseau invalide le diagnostic : les deux axes sont éprouvés
séquentiellement avant leur combinaison finale.

## Tests bloqués aujourd’hui

| Test visé | Pourquoi il n’est pas encore exécutable | Débloqué par |
|---|---|---|
| Unity CI multi-OS | tests/wrappers locaux présents ; runner/licence et preuve Windows absents | `TST-01`, `CI-01` |
| tick/checksum multi-build | manifest du player build présent ; tick/checksum runtime absents | `TOP-01`, `WALL-01` |
| réseau dégradé et comparaison automatique | harness non implémenté | `QA-01` après `INT-01` et `INTG-01` |
| Windows et trois machines | machines et opérateurs externes à cette session | `ENV-01`, `ENV-02`, `NET-00` |
| restore DVC vide Mac/Windows | modèle/validateur prêts ; remote et premier lot non prouvés | `DVC-01` à `DVC-03` |
| preuve finale Blender vers Unity | modèle/validateur prêts ; masters et validation cible incomplets | `DVC-02`, `DVC-04`, `ART-02` |
| budget performance | cible et budgets non décidés | décision humaine avant `PERF-01` |
| playtest de fun | duel, contrat de manche et recrutement incomplets | G3, `GAME-01`, `PLAY-01` |

Ces cellules sont `BLOCKED`, pas `PASS` ni “non applicable”. Leur propriétaire ferme le prérequis et
réserve ensuite la session correspondante.

## Conflits de planification des tests

- `TST-01`, `INP-01`, `CI-01` et `AUD-01` prennent successivement le verrou `Packages` ou
  `ProjectSettings` ; aucune exécution parallèle sur ces fichiers.
- Unity batch ne tourne jamais dans un clone déjà ouvert par l’éditeur ; utiliser un clone de test
  séparé.
- `ENV-*` et `NET-*` utilisent un SHA gelé : aucune correction en direct pendant la session.
- Les claims DVC sont exclusifs ; un seul éditeur manipule un lot jusqu’au `dvc push` vérifié.
- QA-01 démarre après `INT-01` et `INTG-01`, CI-01 après la preuve manuelle, playtest après QA et
  baseline performance.
- `AUD-01` ne bloque pas M2 si l’audio temporaire prévu par le plan suffit au protocole.

## Format de preuve

Chaque verdict consigne :

```text
testId, buildId, commit, gitClean, bundleManifestSha256, dateUTC,
opérateur, témoin, approbateur, machineAlias, plateforme,
Unity/Blender/versionOutil, rôleRéseau, transport, profil,
schemaVersion, checksum, tickRate, attendu, observé,
résultat PASS|FAIL|BLOCKED, artifactPrivé,
limites, ticketCorrectif éventuel
```

Le manifest n’enregistre ni nom de machine nominatif, ni IP, ni identifiant de plateforme. Un alias
éphémère de poste suffit.

Emplacements :

- résultats automatisés : XML/logs sous `Logs/` local puis artifacts CI courts ;
- build : manifest texte avec commit, Unity, plateforme, schéma et checksum ;
- Blender : preuves textuelles sous `tools/blender-agent-studio/projects/team/<id>/`, binaires dans
  `local_work/` puis master DVC ;
- DVC : pointeur/hash/registre dans Git, credentials et contenu dans le coffre ;
- réseau : extrait anonymisé dans l’issue, logs bruts privés puis supprimés ;
- playtest : matière brute privée avec échéance, synthèse pseudonymisée seulement dans Git.

## Règles d’échec et de reprise

- `FAIL` bloque la gate ; aucun approbateur ne le transforme en avertissement.
- `BLOCKED` nomme le prérequis exact, le propriétaire et la prochaine date de contrôle.
- Une cellule sans artifact requis est “non exécutée”, jamais `PASS`.
- Un résultat intermittent est `FAIL`; un seul retry d’infrastructure est permis si la première
  cause et les deux sorties sont conservées.
- Un SHA différent, un worktree sale ou un build sans hash invalide la preuve distribuée.
- Un warning lié au critère reste bloquant tant qu’il n’est pas trié et attribué.
- Une correction automatique change une catégorie à la fois, trois tentatives maximum.
- Toute divergence de tick, checksum, révision ou collision autoritaire bloque G3.
- Tout master introuvable, droit inconnu, export non réimporté ou conversion Unity non vérifiée bloque
  la livraison de l’asset.
- Toute donnée personnelle publiée impose retrait, rotation des secrets si nécessaire et revue avant
  reprise.
- Le testeur rejoue le scénario complet après correction ; un test ciblé seul ne clôt pas une
  régression intégrée.
