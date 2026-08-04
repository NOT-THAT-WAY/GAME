# Roadmap opérationnelle

## Position actuelle

Le socle est préparé, mais il n'existe pas encore de preuve produite par les trois machines. Le projet est donc toujours en **M0 — fondations**.

## Priorités immédiates

Faire ces lots dans l'ordre. Les noms désignent une affinité de départ ; le propriétaire réel du poste ou la disponibilité prime.

| Priorité | Lot | Affinité pilote | Binôme | Preuve attendue |
|---:|---|---|---|---|
| P0 | choisir le remote DVC privé, créer trois accès et restaurer un lot test | Nils | Zak | pull/push/restauration Mac + Windows |
| P0 | premier import Unity et lockfile | Nils | Sean | PR propre avec `packages-lock.json` |
| P0 | validation Windows IL2CPP | propriétaire du PC / Zak | Nils | exécutable lancé, log archivé dans l'issue |
| P0 | connexion LAN à trois via Tugboat | Zak | les deux autres | Zak, Sean, Nils visibles dans le roster |
| P1 | blockout du pivot en T et échelle joueur | Sean | Zak | scène grise comprise sans explication |
| P1 | gate Wwise Mac/Windows | Nils | Sean | événement sonore dans deux builds |
| P1 | registre licences/données du premier lot | Zak | Sean | provenance et restrictions complètes |
| P2 | transport Steam | Zak | Nils | connexion réelle entre deux comptes |

Le testeur externe du lot n'est ni son pilote ni son binôme. Les chapeaux tournent au lot suivant.

Le plan GitHub actuel ne permet pas encore la protection serveur d'une branche privée. Le hook local bloque les pushes directs vers `main`, mais l'activation de la règle serveur « PR + une approbation + CI » reste une action d'administration à faire lors du passage au plan adapté.

## M0 — définition de terminé

- les trois diagnostics passent ;
- le remote DVC utilise des comptes individuels, le versioning objet et une sauvegarde restaurable ;
- le projet s'ouvre sans resérialisation massive sur les trois machines ;
- un build Windows Development IL2CPP se lance ;
- les trois machines rejoignent la même session Tugboat ;
- la scène contient une échelle joueur cohérente et un pivot en T lisible ;
- Wwise compile et joue un événement minimal sur Mac/Windows, ou une décision écrite le reporte ;
- licences et provenance du premier lot d'assets sont enregistrées.

## M1 — duel de pivot

### Sprint A : sensation locale

- déplacement FPS avec `CharacterController` ;
- interaction tap/hold ;
- rotation du pivot par quarts de tour ;
- poussée, contre-poussée et snap ;
- énergie partagée entre sprint, coup et poussée ;
- retours visuel et sonore provisoires.

Sortie : deux joueurs sur une machine comprennent comment pousser et contrer.

### Sprint B : autorité réseau

- inputs transmis à l'hôte ;
- état discret du pivot validé côté serveur ;
- interpolation/prédiction minimale ;
- profil `80 ms / 2 % / 20 ms` ;
- session de dix minutes sans désynchronisation critique.

Sortie : le duel reste compréhensible entre Mac et Windows dans des conditions imparfaites.

## M2 — décision de fun

Deux vagues de playtests externes, d'abord 1v1 puis 2v2. Mesurer compréhension, plaisir, usages tactiques du pivot et incidents réseau. La décision est `GO`, `ITERATE` pour un seul sprint correctif, ou `STOP/PIVOT` avant toute production lourde.

Les données de playtest sont minimisées, pseudonymisées et supprimées à l'échéance annoncée. Les voix, IP et identifiants de plateforme ne sont pas conservés par défaut.

## Après validation

1. grille et génération du labyrinthe ;
2. minimap et propagation sonore depuis la même topologie ;
3. trésor, knockout et extraction ;
4. contenu piloté par données et validé par schéma ;
5. charge jusqu'à 12 connexions ;
6. Addressables si le volume de contenu le justifie ;
7. vertical slice, CI de build et distribution Steam.

Ni le lore étendu, ni les assets finaux, ni le matchmaking ne passent devant la validation du pivot.
