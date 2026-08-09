# Backlog prêt à distribuer

> Baseline : `main` à `6b565f0`, 9 août 2026. Ce backlog détaille G0 à M2. Les horizons suivants
> restent dans [EXECUTION_PLAN.md](EXECUTION_PLAN.md) jusqu’au verdict de fun.

Pour démarrer chaque ticket sans refaire l’audit, utiliser les
[workpacks par pôle](POLE_WORKPACKS.md). Les propriétaires et preuves de test sont fixés dans la
[matrice QA](TEST_OWNERSHIP_MATRIX.md).

## Mode d’emploi

Chaque fiche peut devenir une issue GitHub. Conserver l’identifiant dans le corps de l’issue, puis
utiliser la branche proposée. Les estimations sont des jours concentrés, revue et preuve locale
incluses.

Statuts :

- `READY-CODEX` : Codex peut produire une branche complète dès que le ticket est autorisé ;
- `READY-HUMAN` : l’action dépend principalement d’un compte, d’une machine ou d’une décision ;
- `BLOCKED` : une dépendance listée doit être fermée ;
- `CONDITIONAL` : ne pas ouvrir avant la gate indiquée.

Une issue n’est pas “assignée à Codex” sans propriétaire humain. Le pilote accepte la solution, le
binôme comprend le changement et le testeur reproduit la preuve.

## HT-00 — smoke test humain minimum

### HT-00 — Vérifier le chemin jouable du prototype actuel

- **Statut** : premier passage exécuté, `INCOMPLETE` ciblé ; instrumentation prête pour le prochain passage utile
- **Branche** : `feat/first-human-test-mode`
- **Pilote / opérateur** : Sean / membre disponible
- **Codex** : mode UI `--human-test`, tests Unity, wrappers, manifest et rapport automatique.
- **Estimation** : 0,5–1 j de préparation, puis 3–5 min d’exécution
- **Dépendances** : aucune gate M1 ; seulement build local, contrôles fonctionnels et récupération
- **Claims** : présentation smoke, scripts HT-00, documents et artifacts locaux ignorés.

Vérifier déplacement/caméra, saut, une manipulation de labyrinthe, punch et impact bot. Ne pas
conclure sur réseau, autorité, équilibre ou fun de production. Un arbre sale devient un warning
déclaré, pas un blocage de ce smoke local ; le hash identifie le binaire réellement joué.

Preuve : marqueurs `[GAME-SMOKE]`, rapport `PASS / INCOMPLETE / FAIL` et une note humaine libre
uniquement si quelque chose paraît cassé ou gênant.

État local du 9 août 2026 : aucun crash ; caméra, déplacement, saut, punch et impact bot sont prouvés.
La manipulation du labyrinthe n’a pas produit d’état serveur visible. Des marqueurs uniques couvrent
maintenant entrée, contact, requête et refus pivot/mur ; aucun nouveau test humain n’est demandé avant
qu’une prochaine modification ou décision rende ce passage informatif.

## Rebasage des issues GitHub existantes

| Issue actuelle | Action préparée | Motif |
|---|---|---|
| `#1 Choisir et restaurer le coffre DVC` | garder ouverte, renommer “Pousser et restaurer les masters via R2”, lier DVC-01 à DVC-03 | le fournisseur est choisi mais aucun lot n’est restaurable |
| `#2 Premier import Unity` | fermer comme terminé par la PR #10 | lockfile et migrations sont mergés |
| `#3 Second Mac et Windows` | scinder en ENV-01 et ENV-02 | propriétaires et preuves distincts |
| `#4 Connecter sur le LAN` | renommer “Session distante à trois via Tailscale/Tugboat” | le LAN local n’est plus la preuve attendue |
| `#5 Blockout du pivot` | déplacer en M1 et remplacer par GRY-01 puis ART-01 | le blockout doit suivre la topologie/collision déterministe |
| `#6 Gate Wwise` | déplacer après G3, statut `CONDITIONAL` | l’audio ne doit pas précéder le duel autoritaire |

Pilote de cette opération : Nils. Codex peut fournir les nouveaux textes ; la modification et la
fermeture des issues sont des mutations GitHub explicites.

---

## G0 — gouvernance et outils fiables

### GOV-01 — Décider visibilité, licence et protection de `main`

- **Statut** : `READY-HUMAN`
- **Branche** : `docs/repository-governance-decision`
- **Pilote / binôme / testeur** : Nils / Zak / Sean
- **Codex** : préparer les options, l’ADR et appliquer les réglages après autorisation.
- **Estimation** : 0,5–1 j
- **Dépendance** : aucune
- **Claims** : `README.md`, `docs/PROJECT_RULES.md`, nouvel ADR ; réglages GitHub hors Git.

Travail :

- choisir explicitement public ou privé ;
- choisir licence open source ou notice propriétaire, avec validation de Zak ;
- activer un ruleset/protection de `main` avec le check du dépôt ;
- conserver un ou deux Admin/Owner maximum et passer les autres en Write/Maintain ;
- définir qui peut bypass, qui merge et le remplaçant de Nils ;
- aligner tous les documents sur la réalité GitHub.

Preuve de terminé : API GitHub montrant visibilité, licence, protection active, check requis et rôles
attendus ; clone non-admin incapable de pousser directement sur `main`.

### GOV-02 — Réparer publication des PR et Dependabot

- **Statut** : implémentation locale terminée ; `READY-HUMAN` pour revue et preuve sur PR réelle
- **Branche** : `fix/pr-automation`
- **Pilote / binôme / testeur** : Nils / Zak / Sean
- **Estimation** : 1–1,5 j
- **Dépendance** : aucune
- **Claims** : `scripts/publish-task.sh`, `scripts/publish-task.ps1`, validateurs, template PR,
  `.github/dependabot.yml`, tests de scripts.

Travail Codex :

- empêcher `publish-task` de publier le template vierge comme corps réel ;
- accepter un fichier de résultat rempli ou ouvrir l’éditeur avant création ;
- empêcher les placeholders non remplis d’entrer dans l’historique de squash ;
- rendre la politique branche/titre compatible avec Dependabot ou désactiver ce bot explicitement ;
- ajouter des fixtures de test communes Bash/PowerShell pour les cas autorisés/refusés.

Preuve : une PR de fixture possède un résultat, des tests et aucun placeholder ; une branche humaine
incorrecte échoue ; le chemin Dependabot choisi passe sans exception générale.

État local du 9 août 2026 : validation de corps renseigné, mode interactif/non interactif,
compatibilité `dependabot[bot]` bornée à GitHub Actions et fixtures communes passent. Il reste à
observer une PR humaine et une PR Dependabot réelles après publication de ces changements.

### GOV-03 — Installer une baseline de détection des secrets

- **Statut** : `READY-CODEX` avec activation GitHub humaine
- **Branche** : `chore/security-baseline`
- **Pilote / binôme / testeur** : Zak / Nils / Sean
- **Estimation** : 1–2 j
- **Dépendance** : GOV-01
- **Claims** : workflow de sécurité, validateur local, `docs/DATA_MANAGEMENT.md`.

Travail :

- choisir un scanner reproductible, épinglé et compatible avec la politique d’Actions ;
- scanner l’arbre suivi et l’historique sans imprimer les valeurs détectées ;
- activer les fonctions GitHub disponibles ;
- vérifier qu’aucun endpoint sensible, token, IP d’équipe ou preuve nominative n’est suivi ;
- documenter la réponse en cas de fuite et la rotation des clés.

Preuve : scan propre au commit courant, secret factice détecté dans une fixture puis supprimé, droits
de workflow minimaux.

### RIGHTS-01 — Fermer les droits du contenu déjà public

- **Statut** : `READY-HUMAN`, inventaire et dossier de preuve `READY-CODEX`
- **Branche** : `docs/content-rights-review`
- **Pilote / binôme / testeur** : Zak / Nils / Sean
- **Estimation** : 0,5–1,5 j
- **Dépendance** : GOV-01 pour la politique de distribution
- **Claims** : `docs/assets/ASSET_REGISTER.md`, audit de droits du studio, notices de dépendances et
  emplacement privé des preuves.

Travail : recroiser auteur, source, date, licence, droit de redistribution et restrictions de chaque
FBX, package, référence externe ou contenu généré. Codex peut inventorier et signaler les trous ;
seuls les propriétaires/ayants droit peuvent confirmer une propriété ou autoriser une publication.

Preuve : aucune ligne runtime suivie n’a un droit `unknown` silencieux ; les preuves nominatives
restent privées ; tout contenu non autorisé est retiré de la diffusion ou remplacé.

### GOV-04 — Rebaser les issues et la documentation d’état

- **Statut** : `READY-HUMAN`
- **Branche** : `docs/rebase-project-status`
- **Pilote / binôme / testeur** : Nils / Sean / Zak
- **Codex** : textes, liens PR et matrice de fermeture déjà préparés ci-dessus.
- **Estimation** : 0,5 j
- **Dépendance** : GOV-01 pour les formulations de visibilité/licence
- **Claims** : issues `#1` à `#6`, `README.md`, `docs/ROADMAP.md`, `docs/ASSETS.md`.

Preuve : aucune checklist racine ne dit que R2 reste à choisir ; aucune issue ouverte n’est déjà
terminée ; chaque issue active possède pilote, binôme, testeur, dépendance et preuve.

---

## G1 — fermer M0 sur les vraies machines

### ENV-01 — Ouverture propre sur le second Mac

- **Statut** : `READY-HUMAN`
- **Branche** : aucune si tout est vert ; `fix/macos-second-machine` seulement en cas d’écart.
- **Pilote / binôme / testeur** : Sean / Nils / Zak
- **Codex** : guider la procédure, diagnostiquer logs/diffs et corriger un script si nécessaire.
- **Estimation** : 0,5–1 j
- **Dépendance** : GOV-04 recommandé, non bloquant
- **Claims** : aucun fichier partagé avant qu’un écart soit identifié.

Preuve : doctor sans `[FAIL]`, Unity ouvre/ferme deux fois au même commit, build Development Mac
fonctionnel et aucun diff généré par l’ouverture/fermeture.

### ENV-02 — Build Windows x86_64 IL2CPP de référence

- **Statut** : `READY-HUMAN`
- **Branche** : aucune si vert ; `fix/windows-il2cpp-build` si correction nécessaire.
- **Pilote / binôme / testeur** : propriétaire du PC avec Zak / Nils / Sean
- **Codex** : analyser `Editor.log`, erreurs IL2CPP, packages et scripts.
- **Estimation** : 0,5–1,5 j
- **Dépendance** : setup Windows et Unity exacts
- **Claims** : aucun fichier avant diagnostic ; correction isolée si nécessaire.

Preuve : build Development Windows lancé, connexion locale possible, commit/Unity version archivés,
aucune resérialisation persistante après fermeture.

### NET-00 — Session distante à trois via Tailscale et Tugboat

- **Statut** : `READY-HUMAN`
- **Branche** : aucune si vert ; `fix/remote-three-player-test` si défaut reproductible.
- **Pilote / binôme / testeur** : Zak / Sean / Nils, avec rôles hôte/client tournants
- **Codex** : préparer commandes, anonymiser les logs et diagnostiquer transport/pare-feu.
- **Estimation** : 0,5–1 j
- **Dépendances** : ENV-01, ENV-02, plan Tailscale compatible confirmé
- **Claims** : scripts réseau uniquement si un défaut est prouvé.

Preuve : Zak, Sean et Nils apparaissent sur les trois écrans depuis trois réseaux ; log avec commit,
OS, rôle et transport, sans IP publiée ; une reconnexion simple fonctionne.

Préparation locale du 9 août 2026 : `network-log-report.py` collecte les trois logs après fermeture,
retire noms/IP/machines/chemins et refuse `PASS` sans authentification par log, roster hôte complet ou
reconnexion demandée. La session à trois reste humaine ; la synthèse n’est plus manuelle.

### DVC-01 — Sécuriser le premier master existant

- **Statut** : `READY-HUMAN`, avec préparation Codex/Blender studio
- **Branche** : `data/secure-rigged-character-master`
- **Pilote / binôme / testeur** : Nils / Sean / Zak
- **Estimation** : 0,5–1 j
- **Dépendances** : accès R2 individuel, versioning/sauvegarde du bucket décidés
- **Claims** : lot `ExternalAssets/Art/ART-PERSO-PUNCH-001`, pointeur DVC, registre, preuves
  textuelles studio ; master binaire hors Git.

Travail : créer le lot depuis une copie immuable du workspace local, calculer les hashes, compléter
provenance/droits, `dvc push` avant Git, puis vérifier que l’export Unity actuel correspond au master.

Preuve : pointeur suivi, objet présent dans R2, clone propre capable de restaurer le lot, hash et
rapport de contenu enregistrés sans committer `.blend` ou texture.

### DVC-02 — Récupérer ou requalifier les deux masters absents

- **Statut** : `READY-HUMAN`
- **Branche** : `data/recover-missing-art-masters`
- **Pilote / binôme / testeur** : Sean / Nils / Zak
- **Codex** : inventaire, hash, package DVC, manifeste et contrôle de provenance.
- **Estimation** : 0,5–2 j selon disponibilité des sources
- **Dépendance** : transmission par Sean ou décision formelle de régénération
- **Claims** : `ART-MAZE-001`, `ART-PERSO-001`, éventuels scripts source, registre et lots DVC.

Preuve : chaque export FBX possède soit un master restaurable, soit un générateur versionné et une
requalification approuvée. “Le fichier existe peut-être sur une machine” n’est pas une preuve.

### DVC-03 — Prouver restauration Mac/Windows et seconde copie

- **Statut** : `BLOCKED`
- **Branche** : `data/validate-asset-vault-restore`
- **Pilote / binôme / testeur** : Nils / Zak / Sean
- **Codex** : script de contrôle non destructif et rapport de hashes.
- **Estimation** : 0,5–1 j
- **Dépendances** : DVC-01 et, si récupérables, DVC-02
- **Claims** : scripts assets, `docs/ASSETS.md`, `docs/DATA_MANAGEMENT.md`.

Preuve : pull depuis un cache vide sur Mac et Windows, hashes identiques, versioning objet confirmé,
seconde copie désignée et procédure trimestrielle écrite.

Préparation locale du 9 août 2026 : modèle `dvc-restore-report` et validateur prêts. Ils exigent un
cache vide prouvé, les hashes restaurés et, pour DVC-03, les deux contrôles de stockage. Le ticket
reste bloqué par l’absence de premier lot réellement poussé, pas par le format de rapport.

---

## G2 — topologie, tests et scène minimale

### TST-01 — Créer la fondation EditMode/PlayMode

- **Statut** : implémentation Mac terminée ; `READY-HUMAN` pour preuve Windows et revue
- **Branche** : `chore/unity-test-foundation`
- **Pilote / binôme / testeur** : Zak / Nils / Sean
- **Estimation** : 1–1,5 j
- **Dépendance** : ENV-02 souhaitable pour la preuve croisée, non requise pour écrire les tests
- **Claims** : `Assets/_Project/Tests/`, asmdefs, scripts de lancement Unity, documentation CI.

Travail Codex :

- ajouter assemblies EditMode et PlayMode séparés ;
- ajouter une fixture triviale prouvant leur exécution ;
- fournir des commandes Mac/Windows qui exportent XML et code de sortie ;
- conserver le test de domaine indépendant d’une scène lorsque possible ;
- ajouter les résultats de tests aux manifests de build locaux.

Preuve : même suite verte en batch sur Mac et Windows, puis test volontairement cassé observé rouge.

État local du 9 août 2026 : compilation Mac verte, `26/26` EditMode (dont `5/5` fondation) et
`1/1` PlayMode, wrappers,
`test-run.json`, manifests de player build Mac/Windows et documentation présents. Un rouge volontaire
`4/5` a aussi été observé localement. Restent la reproduction depuis un SHA propre, la revue des
artifacts et la preuve Windows ; elles ne sont pas remplacées par le résultat Mac sale.

### PROV-01 — Lier chaque preuve au build réellement exécuté

- **Statut** : `IMPLEMENTED-LOCAL`; EditMode et contrats Mac verts, parse/build Windows encore à prouver
- **Branche** : `chore/runtime-build-provenance`
- **Pilote / binôme / testeur** : Nils / Zak / Sean
- **Estimation** : 0,5–1,5 j
- **Dépendance** : intégrer d’abord la préparation locale actuelle sur une branche propre
- **Claims** : identité de build runtime, manifests Mac/Windows, rapport réseau et tests de contrat.

Travail : générer avant build un `buildId` portant commit, état propre/sale, profil et version ; écrire
ce marqueur dans chaque log au démarrage ; produire après build un inventaire canonique hashé du
bundle `.app` ou du dossier Windows complet ; obliger le rapport réseau à vérifier que chaque log et
chaque manifest désignent le même build. Un SHA passé en argument ne peut plus réétiqueter un ancien
log. Les smokes développeur peuvent déclarer un arbre sale ; une preuve de gate le refuse.

Preuve : un ancien log ou deux builds différents donnent `INCOMPLETE`, trois logs du même build propre
sont acceptés, et aucune donnée machine/réseau n’entre dans la sortie expurgée.

État local du 9 août 2026 : identité runtime et writer de build présents, manifests schéma 2 et
empreinte récursive du bundle implémentés sur Mac/Windows, rapport lié aux manifests. Tests locaux :
`8/8` EditMode, `11/11` rapport réseau et `3/3` fingerprint. Restent le parseur CI PowerShell puis un
vrai build Windows IL2CPP au même commit qu’un build Mac propre.

### DEC-01 — Fermer les décisions M1 de l’ADR 0004

- **Statut** : `READY-HUMAN`
- **Branche** : `docs/close-m1-simulation-decisions`
- **Pilote / binôme / testeur** : Nils / Zak / Sean
- **Codex** : note d’options, impacts réseau/feel, patch ADR après choix.
- **Estimation** : 0,5–1 j
- **Dépendances** : ENV-01 et ENV-02 pour toute mesure matérielle invoquée
- **Claims** : ADR 0004, configuration de simulation, contrat joueur/pivot.

Décider : taux de tick, gabarit/hauteur, saut, politique d’un mur contre un joueur, ordre exact avec
la physique et statut du listen-server pour M1. Ne pas régler ces valeurs dans une PR de code cachée.

Preuve : ADR amendé, valeurs canoniques dans une seule source, scénario jouable ou mesure citée.

Préparation locale du 9 août 2026 : options, impacts, baseline recommandée et tests de mesure sont
regroupés dans `DECISION_PACKET_M1_M2.md`. La décision reste humaine ; aucun réglage recommandé n’est
encore appliqué au runtime.

### DEC-02 — Fixer la garantie de connectivité

- **Statut** : `READY-HUMAN`
- **Branche** : `docs/decide-maze-connectivity-contract`
- **Pilote / binôme / testeur** : Sean / Zak / Nils
- **Codex** : quatre options bornées, fixtures topologiques et patch de contrat après choix.
- **Estimation** : 0,25–0,5 j
- **Dépendance** : aucune pour la décision ; `TOP-01` fournit ensuite le support de validation
- **Claims** : règle de connectivité, erreurs du validateur, politique explicite de reset/softlock.

Choisir si chaque mouvement doit préserver tous les spawns, un chemin vers une zone/objective, la
seule zone de duel, ou aucune garantie globale avec politique de reset explicite. Le validateur ne
déduit pas une règle de game design depuis la géométrie.

Preuve : une phrase normative, une fixture acceptée et une fixture refusée sans ambiguïté.

Préparation locale : le dossier DEC recommande la portée « zone de duel » pour M1 puis un chemin
spawn→objectif après choix de manche. Les fixtures restent à créer sous TOP-01.

### DEC-03 — Fixer énergie, contestation et tie-break

- **Statut** : `READY-HUMAN`
- **Branche** : `docs/decide-pivot-effort-rules`
- **Pilote / binôme / testeur** : Sean + Nils / Zak / membre non auteur
- **Codex** : table d’options, séquences de ticks et patch du modèle après choix.
- **Estimation** : 0,25–0,5 j
- **Dépendance** : `WALL-01` souhaitable pour mesurer, non requise pour préparer la règle
- **Claims** : énergie max/régénération/coûts, effort, priorité push/punch, contestation et tie-break.

Preuve : tous les cas simultanés ont un verdict déterministe au même tick et une seule source
canonique alimente serveur, tests et UI.

Préparation locale : le dossier DEC sépare effort réseau sans énergie, énergie partagée et ressources
séparées, puis propose une agrégation signée sans priorité liée au `ClientId` ou à l’ordre des RPC.

### TOP-01 — Introduire le schéma de topologie v1

- **Statut** : `IMPLEMENTED-LOCAL`; preuve Windows du checksum encore attendue.
- **Branche** : `feat/m1-minimal-skeleton`
- **Pilote / binôme / testeur** : Zak / Nils / Sean
- **Estimation** : 2–3 j
- **Claims** : nouveaux types purs sous `Assets/_Project/Runtime/Maze/Topology/`, schéma/données,
  migration du JSON actuel, tests EditMode.

Contrat minimal : `schemaVersion`, IDs entiers stables, dimensions en millimètres, murs, pivots,
ouvertures, spawns, checksum canonique et règles d’erreur. Valider doublons, bornes, références,
dimensions et spawns. La politique de connectivité reste dans TOP-02 après DEC-02. Le parser regex
de l’éditeur ne devient pas la nouvelle source.

Preuve : mêmes bytes canoniques et checksum sur Mac/Windows ; fixtures valides/invalides ; migration
de `MazeGrid16x16.json` sans dépendre des noms ou de l’ordre du FBX.

État local du 9 août 2026 : types runtime, parseur strict sans parse partiel, checksum obligatoire
au runtime, références bijectives, états/occupations cohérents, limites de ressources et migration
reproductible du 16×16 implémentés. Le générateur legacy lit la topologie v1 signée et a régénéré
sa scène avec quatre spawns orientés par les arêtes libres. Preuve Mac : `26/26` EditMode,
checksum fixture `b78a…e580`, checksum 16×16 `36a8…528a`. Connectivité reste dans TOP-02.

### TOP-02 — Générer collisions et connectivité depuis le schéma

- **Statut** : `IMPLEMENTED-LOCAL` pour primitives, occupation, graphe, sweep et fixture M1 ;
  intégration de la politique de refus attend le modèle de transition
- **Branche** : `feat/topology-colliders`
- **Pilote / binôme / testeur** : Zak / Sean / Nils
- **Estimation** : 1,5–2,5 j
- **Claims** : générateur de colliders, couches physique, validations topologiques, tests.

Travail : générer primitives simples, distinguer pose logique et rendu, vérifier arc balayé des murs,
occupation des arêtes et chemins minimum. Les requêtes utilisent des layers explicites. Aucun
`MeshCollider` du décor ne décide d’un état partagé.

Preuve : test de correspondance schéma/colliders, zéro collider gameplay issu du FBX dans la scène
de référence, cas de fermeture impossible refusé de façon déterministe.

État local du 9 août 2026 : `TopologyRuntimeMap` copie le document signé vers un modèle immuable ;
géométrie millimétrique, occupation d'arêtes, BFS, périmètre et quart de disque balayé sont testés.
La fixture 2×2 garde ses deux spawns reliés en `3` puis `1` arête. La gate atomique refuse destination
occupée, rupture de connectivité et joueur dans l'arc sans muter l'état. Le PlayMode génère un sol et
sept `BoxCollider`, aucun `MeshCollider`, change l'état du mur 10, répète trois resets exacts et
compare deux hiérarchies générées indépendamment.

### GRY-01 — Livrer la scène grise à un pivot et deux joueurs

- **Statut** : collision/topologie primitive `IMPLEMENTED-LOCAL`; joueurs, HUD et réseau à brancher
- **Branche** : `feat/pivot-graybox`
- **Pilote / binôme / testeur** : Sean / Zak / Nils
- **Estimation** : 1–2 j
- **Claims** : petite scène/prefabs ou générateur déterministe, donnée de fixture, HUD debug, tests
  PlayMode. Aucun FBX final.

Travail : un pivot, deux spawns, reset instantané, repères d’orientation/IDs/tick/checksum visibles,
volumes simples et distance d’interaction mesurable. Si la scène est générée, deux générations
propres produisent la même hiérarchie et aucun diff parasite.

Preuve : clone propre capable de lancer la fixture ; deux joueurs se déplacent sans bouton de
déblocage ; collision et état proviennent uniquement du schéma.

### ART-01 — Contrat de lisibilité du pivot gris

- **Statut** : `BLOCKED` par GRY-01, puis travail parallèle autorisé
- **Branche** : `art/pivot-readability-blockout`
- **Pilote / binôme / testeur** : Sean / Nils / Zak
- **Codex** : contrat studio, previews comparables, validation échelle/pivot/import Unity.
- **Estimation** : 1–2 j
- **Claims** : projet textuel sous le studio, master DVC/local, exports runtime approuvés, registre.

Définir côté manipulable, axe, sens, état disponible/bloqué/contesté et lecture à distance gameplay.
Le mesh visuel ne porte ni ID ni collision autoritaire. Budgets, unités, axes, UV, matériaux et
colliders sont déclarés avant détail.

Preuve : source immuable, vues d’identité, quatre orientations, import Unity exact, lisibilité
humaine validée et master restaurable. Aucun asset lourd du studio n’entre directement dans Git.

---

## G3 — simulation autoritaire et preuve M1

### TICK-01 — Modèle pur du mur par tick

- **Statut** : `IMPLEMENTED-LOCAL` pour le modèle paramétré, le codec snapshot, le wrap et les tests ;
  taux concret, ordre PhysX et politique mur/joueur restent bloqués par DEC-01
- **Branche** : `feat/m1-minimal-skeleton`
- **Pilote / binôme / testeur** : Zak / Sean / Nils
- **Codex** : implémentation et tests déterministes.
- **Estimation** : 1,5–2,5 j
- **Claims** : types `WallState`, `WallTransition`, simulation pure et tests.

État minimal : ID, source, cible, `startTick`, `durationTicks`, `revision`, effort/énergie/cooldown
en ticks si applicables. La pose logique est calculée depuis état + tick, jamais accumulée avec
`deltaTime`.

Preuve : même suite d’états à 30/60/120 FPS de rendu ; révision ancienne refusée ; sérialisation et
snapshot round-trip identiques.

État local du 9 août 2026 : machine à deux poses avec IDs non denses, effort signé borné par source,
agrégation indépendante de l'ordre, gate atomique, progression Q16, codec v1 et restauration late
join implémentés. Les gates Mac comptent `86/86` EditMode après PLY-01 ; l'adaptateur FishNet reste WALL-01.

### WALL-01 — Adaptateur FishNet, validation et arrivée tardive

- **Statut** : `BLOCKED` par TICK-01 et GRY-01
- **Branche** : `feat/pivot-authoritative-network`
- **Pilote / binôme / testeur** : Zak / Sean / Nils
- **Codex** : refactor réseau, tests PlayMode, instrumentation.
- **Estimation** : 3–4,5 j
- **Claims** : `PivotDirector`, `MovableWallDirector` ou remplaçant unique, spawner, snapshot, tests.

Travail : une intention compacte, validation hôte de portée/LOS/côté/couple/énergie/cooldown/espace,
transition datée, révision monotone, snapshot complet et reconnexion. Consolider les deux systèmes de
pivots/murs actuels au lieu de prolonger les deux.

Preuve : client tardif entrant au milieu d’une rotation voit immédiatement le bon état ; 10 minutes
sans divergence ; requêtes abusives de fixture refusées et journalisées sans spam.

### INP-01 — Passer aux Input Actions

- **Statut** : `IMPLEMENTED-LOCAL` pour asset, schemes, source frame→tick, commande compacte et
  pont du smoke legacy ; statut durable du saut et sémantique finale tap/hold restent sous DEC-01
- **Branche** : `feat/m1-minimal-skeleton`
- **Pilote / binôme / testeur** : Sean / Zak / Nils
- **Codex** : asset d’actions, adaptateur de commande, tests de bindings.
- **Estimation** : 0,5–1 j
- **Claims** : action map joueur/UI, capture de commande, documentation contrôles.

Actions minimales : mouvement, regard, sprint, interaction tap/hold, punch, saut si retenu, pause.
Clavier/souris et manette ; aucune logique réseau ne lit directement `Keyboard.current` ou
`Mouse.current`.

Preuve : bindings fonctionnels dans deux instances, focus souris maîtrisé, commande compacte testée.

État local du 9 août 2026 : asset Player/UI validé, clavier/souris et manette virtuels, sources
restreintes à des devices distincts, fronts conservés une seule fois et souris/stick séparés par
unités. `PlayerMotor` et `PlayerPunch` ne lisent plus directement les devices ; le générateur de
scène sérialise la source désactivée, activée ensuite uniquement pour le propriétaire. Une gate
statique interdit le retour des lectures directes. Reste à prouver une manette physique et deux
processus lors du test humain ; `Pause` est local et absent du payload réseau.

### PLY-01 — Extraire la simulation pure du joueur

- **Statut** : `IMPLEMENTED-LOCAL` pour le modèle pur paramétré ; valeurs canoniques, preuve Windows
  et adaptateur physique restent à fermer
- **Branche** : `feat/m1-minimal-skeleton`
- **Pilote / binôme / testeur** : Zak / Nils / Sean
- **Codex** : état/commande/simulation et tests.
- **Estimation** : 1–2 j
- **Claims** : `PlayerCommand`, `PlayerState`, simulation, gabarit canonique et tests.

Travail : mouvement, rotation utile au gameplay, gravité/saut retenu, sprint et knockback sous un
ordre de tick explicite. Séparer caméra/interpolation de la décision de collision.

Preuve : séquences déterministes, bords de collision et reset testés, aucune dépendance au framerate.

État local du 9 août 2026 : état entièrement réconciliable, configuration sans preset caché,
mouvement/yaw/sprint, gravité, saut désactivable, fenêtres coyote/buffer, knockback, collision injectée
une fois par tick, restauration et wrap sont couverts. Payloads forgés, ticks non contigus, réentrance
et exceptions de collision sont refusés atomiquement. La gate Mac compte `86/86` EditMode ; voir
`docs/PLAYER_SIMULATION_MODEL.md`. PLY-02 doit encore fournir `CharacterController`, DTO FishNet,
prédiction, replay et réconciliation.

### PLY-02 — Brancher prédiction et réconciliation FishNet

- **Statut** : `READY-CODEX` pour l’adaptateur local après PLY-01, INP-01 et GRY-01 ; preuve distribuée
  encore bloquée par les décisions PhysX/tick et les machines de QA
- **Branche** : `feat/predicted-player-motor`
- **Pilote / binôme / testeur** : Zak / Nils / Sean
- **Codex** : `Replicate`/`Reconcile`, instrumentation et tests.
- **Estimation** : 3–5 j
- **Claims** : remplacement de `PlayerMotor`, prefab/générateur joueur, tests réseau.

Travail : commandes par tick, simulation serveur, replay client, état de reconcile et rendu lissé.
Retirer le `NetworkTransform` client-authoritative et le téléport de déblocage comme mécanismes de
gameplay. Conserver un outil debug serveur explicitement hors build release si nécessaire.

Preuve : profil `80 ms / 2 % / 20 ms`, corrections bornées et visibles dans les métriques, aucune
position acceptée sur simple affirmation cliente.

### INT-01 — Unifier push, punch, énergie et contestation

- **Statut** : `BLOCKED` par DEC-03, WALL-01 et PLY-02
- **Branche** : `feat/authoritative-pivot-interactions`
- **Pilote / binôme / testeur** : Sean / Zak / Nils
- **Codex** : modèle de règles, serveur, UI debug et tests.
- **Estimation** : 2–3 j
- **Claims** : interaction joueur/mur, punch, énergie, paramètres canoniques, tests.

Une source unique reçoit les intentions de push/punch, calcule effort/énergie/contestation et applique
la politique de collision décidée. Le serveur recalcule pose, portée et direction ; la victime ne
s’applique pas elle-même un knockback faisant foi.

Preuve : spam, cible hors portée, traversée, effort concurrent et énergie insuffisante testés ; deux
joueurs obtiennent le même verdict au même tick.

### CON-01 — Introduire `ConnectionTarget`

- **Statut** : valeur, parseur CLI et tests purs `READY-CODEX` ; branchement runtime après NET-00
- **Branche** : `feat/connection-target`
- **Pilote / binôme / testeur** : Zak / Nils / Sean
- **Estimation** : 0,5–1 j
- **Dépendance** : NET-00 uniquement pour remplacer le bootstrap Tugboat actuel
- **Claims** : bootstrap connexion, cible/adaptateur Tugboat, tests.

Preuve : le gameplay ne connaît ni adresse Tugboat ni Steam ; host/client/reconnexion utilisent la
même API ; aucune dépendance Steam ajoutée.

### INTG-01 — Rebrancher la map 16x16 comme test d’intégration

- **Statut** : `BLOCKED` par TOP-02, WALL-01 et PLY-02
- **Branche** : `feat/maze16-topology-integration`
- **Pilote / binôme / testeur** : Sean / Zak / Nils
- **Codex** : migration du builder, validateurs et tests.
- **Estimation** : 1,5–2,5 j
- **Claims** : `MazePlaytestBuild`, donnée migrée, colliders, import visuel, tests.

Travail : supprimer le parser regex et les IDs issus de l’ordre FBX, générer collisions depuis le
schéma, conserver le FBX uniquement pour le rendu, détecter pièces visuelles absentes et interdire
un build silencieusement incomplet. Supprimer le collider géant ou le cantonner au non-gameplay.

Preuve : checksum et suite d’états identiques Mac/Windows ; zéro collision gameplay dépendante des
triangles FBX ; connectivité et spawns validés avant build.

### QA-01 — Exécuter la matrice de sortie M1

- **Statut** : `BLOCKED` par INT-01 et INTG-01
- **Branche** : `chore/m1-network-proof-harness` pour l’outillage ; preuves dans l’issue.
- **Pilote / binôme / testeur** : Nils / Zak / Sean
- **Codex** : harness, comparaison de logs et rapport automatique.
- **Estimation** : 1–2 j plus disponibilité des machines
- **Claims** : outils de test, format de logs, rapport de preuve ; pas d’IP ou identifiant personnel.

Matrice : Mac/Windows, hôte/client tournants, arrivée tardive, reconnexion, 30/60/120 FPS, puis
`80 ms RTT / 2 % perte / 20 ms jitter`. Comparer tick, checksum, révisions, états joueurs/murs et
nombre de reconciliations, pas seulement l’image.

Ordre : gel du SHA et manifests → trois smokes de cinq minutes par type d’hôte → 20 minutes hôte
Windows → 20 minutes hôte Mac → 30/60/120 FPS → profil dégradé à 60 FPS → late join et deux
reconnexions. Ne varier qu’un axe à la fois avant la combinaison finale.

Preuve : session de 20 minutes, deux joueurs relancent volontairement, aucune divergence critique,
même résultat logique au même commit.

### CI-01 — Activer compilation et tests Unity en CI

- **Statut** : `BLOCKED` par ENV-02, TST-01 et preuve manuelle G3
- **Branche** : `chore/unity-build-ci`
- **Pilote / binôme / testeur** : Nils / Zak / Sean
- **Codex** : scripts/workflows, cache, artifacts et permissions.
- **Estimation** : 2–3 j
- **Claims** : `.github/workflows/`, scripts batch Unity, politique de secrets, manifests.

Décider runner/licence, épingler toute Action externe, commencer par compilation + EditMode +
PlayMode. N’ajouter le build Windows artifact qu’après preuve locale, avec rétention courte. Signature
et Steam restent dans un workflow release séparé.

Preuve : PR volontairement cassée rouge ; PR correcte verte ; aucun secret dans logs/artifacts ;
manifest contenant commit, Unity, plateforme, schéma et checksum.

---

## G4 — décision de fun M2

### GAME-01 — Écrire le contrat de la manche M2

- **Statut** : `BLOCKED` par G3
- **Branche** : `docs/m2-round-contract`
- **Pilote / binôme / testeur** : Nils / Sean / Zak
- **Codex** : options, statechart et critères mesurables.
- **Estimation** : 0,5–1 j
- **Claims** : document de design court, paramètres canoniques, protocole de playtest.

Décider départ, objectif, score/victoire, KO éventuel, durée/fin, respawn/reset et ce que la vague doit
apprendre. Ne pas ajouter trésor/extraction par défaut si le duel de pivot suffit au test.

Preuve : un nouveau testeur comprend en une page ce qu’il doit faire et comment la manche se termine.

### GAME-02 — Implémenter état de manche, reset et résultat

- **Statut** : `BLOCKED` par GAME-01
- **Branche** : `feat/duel-round-loop`
- **Pilote / binôme / testeur** : Nils / Zak / Sean
- **Codex** : modèle pur, adaptateur réseau, tests et HUD debug.
- **Estimation** : 2–3 j
- **Claims** : état de session/manche, règles, spawns/reset, tests.

Preuve : deux manches consécutives sans relancer le processus ; late join/reconnexion explicitement
acceptés ou refusés ; même résultat autoritaire chez tous les joueurs.

### UI-01 — Fournir HUD et réglages nécessaires au playtest

- **Statut** : `BLOCKED` par INP-01 et GAME-01
- **Branche** : `feat/playtest-ui-settings`
- **Pilote / binôme / testeur** : Sean / Nils / Zak
- **Codex** : structure UI, données, navigation et tests fonctionnels.
- **Estimation** : 1,5–2,5 j
- **Claims** : HUD, menu pause/réglages, Input Actions, styles provisoires.

Minimum : objectif, état du pivot/énergie, feedback d’interaction, sensibilité, FOV, inversion, volume,
bindings visibles et états connexion/reconnexion. Les couleurs seules ne portent pas une information.

Preuve : clavier/souris et manette, résolutions cibles, test de compréhension sans explication orale.

### TEL-01 — Préparer télémétrie minimale et protocole de playtest

- **Statut** : `BLOCKED` par GAME-01
- **Branche** : `feat/playtest-measurement`
- **Pilote / binôme / testeur** : Nils / Zak / Sean
- **Codex** : événements, format local, agrégation, questionnaire et rapport.
- **Estimation** : 1–2 j
- **Claims** : schéma d’événements, export local, notice de données, questionnaire.

Mesurer : temps avant première action intentionnelle, tentatives/réussites/contestations, durée de
manche, resets, déconnexions, divergences/reconciliations et réponse qualitative. Pseudonymiser,
annoncer la finalité et la suppression ; ne pas conserver IP, voix ou identifiants de plateforme.

Preuve : session factice exportée puis agrégée ; suppression vérifiée ; aucune donnée inutile.

### PERF-00 — Établir la baseline de performance du build de playtest

- **Statut** : `BLOCKED` par INTG-01, GAME-02 et UI-01
- **Branche** : `chore/playtest-performance-baseline`
- **Pilote / binôme / testeur** : Zak / Nils / Sean
- **Codex** : instrumentation, scénario reproductible et synthèse des captures.
- **Estimation** : 1–2 j
- **Claims** : marqueurs de profilage, scénario, budgets décidés, rapport textuel ; captures lourdes
  conservées comme artifacts, pas dans Git.

Déclarer le PC cible minimal et un objectif mesurable avant le test. Capturer CPU main thread,
physique, rendu, mémoire, allocations et pics lors des rotations/connexions. Comparer scène grise et
map 16x16 ; éliminer au minimum les erreurs critiques comme le collider géant, sans lancer une passe
d’optimisation artistique prématurée.

Preuve : même scénario sur build Windows IL2CPP et build Mac interne, pires frames documentées,
aucun dépassement caché susceptible de fausser le ressenti du playtest.

### PLAY-01 — Vague externe 1v1

- **Statut** : `BLOCKED` par GAME-02, UI-01, TEL-01, PERF-00 et QA-01
- **Branche** : aucune pour les données personnelles ; synthèse anonymisée `docs/playtest-m2-wave1`.
- **Pilote / binôme / testeur** : Sean / Nils / Zak
- **Codex** : guide modérateur, analyse et synthèse.
- **Estimation** : 1 j plus recrutement

Preuve : nombre de duos fixé dans GAME-01, même build pour tous, observations séparées des
interprétations, incidents techniques isolés des problèmes de fun.

### FIX-01 — Sprint correctif M2 unique

- **Statut** : `CONDITIONAL`, uniquement si PLAY-01 produit une hypothèse prioritaire testable
- **Branche** : type selon la correction, une seule catégorie principale
- **Pilote / binôme / testeur** : attribués selon la cause ; le testeur n’est pas l’auteur
- **Codex** : implémentation et comparaison avant/après.
- **Estimation** : 2–4 j, plafond strict

Preuve : une hypothèse, une métrique cible, aucune extension de contenu ; si trois tentatives dans la
même catégorie n’améliorent pas la preuve, arrêter et préparer `STOP/PIVOT`.

### AUD-01 — Gate Wwise minimale

- **Statut** : `CONDITIONAL` après G3, parallèle à la préparation PLAY-01 uniquement si elle ne
  retarde pas le test
- **Branche** : `audio/wwise-minimal-gate`
- **Pilote / binôme / testeur** : Nils / Sean / Zak
- **Codex** : intégration contrôlée, événement minimal, validateurs et documentation.
- **Estimation** : 2–4 j
- **Claims** : packages/ProjectSettings dans une PR dédiée, projet Wwise privé/DVC, SoundBanks
  runtime Git LFS, registre de licence.

Preuve : un événement pivot audible dans builds Mac et Windows au même commit, banques reproductibles,
aucun Work Unit concurrent. Sinon, conserver l’audio Unity temporaire et ne pas bloquer M2.

### PLAY-02 — Vague 2v2 et décision

- **Statut** : `BLOCKED` par PLAY-01 et FIX-01 si ouvert
- **Branche** : `docs/m2-go-iterate-stop`
- **Pilote / binôme / testeur** : Nils / Sean / Zak, avec joueurs externes
- **Codex** : analyse croisée, rapport et traçabilité des limites.
- **Estimation** : 1–2 j plus recrutement

Preuve finale séparée : qualité technique, compréhension, tactiques observées, plaisir/envie de
rejouer, incidents et limites. Verdict obligatoire :

- `GO` : ouvrir la planification détaillée M3 ;
- `ITERATE` : une seule hypothèse et un seul sprint supplémentaire explicitement autorisés ;
- `STOP/PIVOT` : geler la production lourde et archiver les apprentissages.

---

## File de travail immédiate

Sans attendre les décisions de game design, le prochain lot peut être distribué ainsi :

| Voie | Pilote | Travail immédiat | Codex |
|---|---|---|---|
| A — dépôt | Nils | GOV-01 et rebasage issues | GOV-02 puis textes GOV-04 |
| B — machines | Zak | ENV-02 puis NET-00 | diagnostic logs/scripts |
| C — art/data | Sean + Nils | ENV-01, DVC-01, recherche DVC-02 | manifests, hashes, registre |
| D — qualité | Zak | relire TST-01 et la provenance des preuves | durcir build/log puis implémenter TOP-01A |

La première nouvelle règle de gameplay n’est ouverte qu’après la décision qu’elle concerne.
`PROV-01`, `TOP-01A/B`, le modèle de transition paramétré et les Input Actions de base sont du
travail d’infrastructure réversible ; ils peuvent précéder DEC-01. `TOP-02` et `GRY-01` suivent,
sans prolonger les deux systèmes legacy du prototype.

## Définition de terminé commune

Chaque ticket livré respecte au minimum :

- résultat reproductible depuis un clone ou une mise à jour propre ;
- tests proportionnés au risque et commande exacte consignée ;
- second humain ayant reproduit la preuve ;
- autre OS pour réseau, input, packages, chemins, plugins ou build ;
- aucun secret, cache, build, donnée personnelle ou master brut dans Git ;
- `dvc push` avant `git push` si un pointeur change ;
- schéma/ADR/documentation mis à jour avec tout contrat partagé ;
- limites et avertissements déclarés, sans transformer une prévalidation en preuve finale.
