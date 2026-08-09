# Roadmap opérationnelle

Le séquençage complet, les dépendances, les estimations et les responsabilités sont maintenus dans
le [plan maître d’exécution](EXECUTION_PLAN.md). Les fiches directement transformables en issues se
trouvent dans le [backlog prêt à distribuer](READY_BACKLOG.md). Cette page reste la vue courte de la
position et des prochaines gates.

Les détails fichier par fichier sont dans les [workpacks par pôle](POLE_WORKPACKS.md) et la rotation
des preuves dans la [matrice de tests](TEST_OWNERSHIP_MATRIX.md).
Les choix encore humains sont préparés dans le
[dossier DEC-01 à DEC-04](DECISION_PACKET_M1_M2.md), avec recommandations et tests minimaux.
Le séquençage vérifié après HT-00, y compris les dépendances assouplies et la fermeture de chaque
dette de l’audit, est dans le [plan de fermeture de l’audit](AUDIT_CLOSURE_PLAN.md).

## Position actuelle

Le premier import Unity, un build Mac du labyrinthe et un test local hôte/client sont validés. Un
premier smoke humain sans crash a aussi validé caméra, déplacement, saut et combat ; l’interaction
labyrinthe reste à isoler avec la télémétrie désormais intégrée. Le profil distant Tailscale est
automatisé, mais il n'existe pas encore de preuve produite par les trois machines ; le projet reste
donc en **M0 — fondations**.

La map 16x16, le joueur et les 17 pivots forment un smoke test utile, pas encore l'architecture M1 : déplacement client-authoritative, murs interpolés par image et collisions issues du FBX. [L'audit du 5 août](audits/2026-08-05-document-maitre.md) et [l'ADR 0004](adr/0004-authoritative-topology-and-ticks.md) fixent la migration à effectuer avant d'étendre le gameplay réseau.

Trois FBX sous LFS existent : deux masters sont absents et le master du clone riggé reste seulement
dans un workspace local ignoré. Le fournisseur R2 est choisi, mais aucun lot DVC n'a encore été
poussé puis restauré. Cela ne bloque pas le clone ou le runtime, mais bloque toute nouvelle
modification ou transmission de ces masters. Wwise et Steam restent derrière leurs gates.

## Priorités immédiates

Faire ces lots dans l'ordre. Les noms désignent une affinité de départ ; le propriétaire réel du poste ou la disponibilité prime.

Déjà terminé : premier import Unity, lockfile et migrations déterministes via la PR #10 ; deux instances Mac se sont authentifiées avec un roster local à deux ; la map 16x16 et le pivot ont compilé et tourné comme smoke test Mac.

| Priorité | Lot | Affinité pilote | Binôme | Preuve attendue |
|---:|---|---|---|---|
| P0 | livrer la préparation locale et durcir la provenance build/log | Nils | Zak | SHA propre, bundle manifesté, logs liés au build réel |
| P0 | fermer visibilité/licence/protection/rôles GitHub | Nils | Zak | décision écrite, `main` protégé, droits réduits |
| P0 | ouverture propre sur le second Mac | Sean | Nils | doctor vert et aucun diff après ouverture/fermeture |
| P0 | validation Windows IL2CPP | propriétaire du PC / Zak | Nils | exécutable lancé, log archivé dans l'issue |
| P0 | connexion distante à trois via Tailscale + Tugboat | Zak | les deux autres | Zak, Sean, Nils visibles dans le roster depuis trois réseaux |
| P0 | pousser/restaurer le premier lot DVC et récupérer les sources absentes | Nils | Sean + Zak | hashes identiques après restauration Mac + Windows |
| P1 | schéma de topologie typé, IDs et checksum | Zak | Nils | parsing/tests EditMode ; mêmes données et collisions sur deux OS |
| P1 | scène grise déterministe à un pivot/deux joueurs | Sean | Zak | collision issue du schéma ; aucune dépendance au FBX 16x16 |
| P1 | murs autoritaires par tick et arrivée tardive | Zak | Sean | transition/révision/snapshot identiques à 30/60/120 FPS |
| P1 | Input Actions et joueur prédit/réconcilié | Zak | Nils | `Replicate`/`Reconcile` sous `80 ms / 2 % / 20 ms` |
| P2 | gate Wwise après la première preuve distante autoritaire | Nils | Sean | événement sonore dans deux builds |
| P2 | `ConnectionTarget`, puis transport Steam | Zak | Nils | même appel gameplay pour Tugboat et lobby ; connexion réelle entre deux comptes |

Le testeur externe du lot n'est ni son pilote ni son binôme. Les chapeaux tournent au lot suivant.

HT-00 reste enregistré `INCOMPLETE` sans bloquer M1. Son prochain passage est optionnel pour maintenir
la démo legacy ; le prochain test humain prioritaire porte sur la graybox autoritaire.

Le dépôt est actuellement public et `main` n'est pas protégé côté serveur. Le hook local, les
préfixes de branche, les PR et la CI restent utiles mais ne suffisent pas : la visibilité/licence,
le ruleset et la réduction des trois rôles Admin constituent désormais la gate G0.

## M0 — définition de terminé

- les trois diagnostics passent ;
- le projet s'ouvre sans resérialisation massive sur les trois machines ;
- un build Windows Development IL2CPP se lance ;
- les trois machines rejoignent la même session Tugboat depuis leurs réseaux respectifs.

Le coffre DVC s'ouvre désormais avant de modifier ou partager les masters des exports présents. Il ne retarde pas l'onboarding d'un développeur qui consomme seulement les FBX. Wwise s'ouvre après le premier gameplay autoritaire testable, avec Nils comme seul poste Authoring au départ. Steam attend que Tailscale ait prouvé la connexion.

## M1 — duel de pivot

### Gate technique

Les changements M1 suivent l'ordre de migration de l'ADR 0004 : topologie typée et collision simple, mur par tick avec snapshot, puis joueur prédit/réconcilié. Le profil gris à un pivot/deux joueurs est la preuve primaire ; la map 16x16 vient ensuite comme test d'intégration.

Avant d'implémenter un mur qui peut toucher un joueur, décider explicitement si la transition est refusée, provoque un KO ou applique une autre règle. Fixer dans la même gate le taux de tick, le gabarit canonique et le statut du saut.

### Sprint A : sensation locale

- déplacement FPS via Input Actions, clavier/souris et manette ;
- interaction tap/hold ;
- rotation du pivot par quarts de tour ;
- poussée, contre-poussée et snap ;
- énergie partagée entre sprint, coup et poussée ;
- retours visuel et sonore provisoires.

Sortie : deux joueurs sur une machine comprennent comment pousser et contrer dans la scène grise, sans dépendre des props ou du maillage 16x16.

### Sprint B : autorité réseau

- commandes par tick transmises à l'hôte et validées ;
- état de transition du pivot avec ID, source/cible, tick de départ, durée et révision ;
- prédiction/réconciliation du joueur et interpolation uniquement cosmétique ;
- snapshot d'arrivée tardive avec version de schéma et checksum ;
- profil `80 ms / 2 % / 20 ms` ;
- session de dix minutes sans divergence de tick, topologie, collision ou état joueur.

Sortie : le duel reste compréhensible et produit le même résultat autoritaire entre Mac et Windows dans des conditions imparfaites.

## M2 — décision de fun

Deux vagues de playtests externes, d'abord 1v1 puis 2v2. Mesurer compréhension, plaisir, usages tactiques du pivot et incidents réseau. La décision est `GO`, `ITERATE` pour un seul sprint correctif, ou `STOP/PIVOT` avant toute production lourde.

Les données de playtest sont minimisées, pseudonymisées et supprimées à l'échéance annoncée. Les voix, IP et identifiants de plateforme ne sont pas conservés par défaut.

## Après validation

1. variantes et génération de labyrinthes depuis le schéma validé ;
2. minimap et propagation sonore depuis la même topologie ;
3. trésor, knockout et extraction ;
4. contenu piloté par données et validé par schéma ;
5. charge jusqu'à 12 connexions ;
6. Addressables si le volume de contenu le justifie ;
7. vertical slice, CI de build et distribution Steam.

Ni le lore étendu, ni les assets finaux, ni le matchmaking ne passent devant la validation du pivot.
