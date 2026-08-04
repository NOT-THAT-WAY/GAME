# Roadmap opérationnelle

## Position actuelle

Le premier import Unity et un test local hôte/client sur Mac sont validés. Le profil distant Tailscale est automatisé, mais il n'existe pas encore de preuve produite par les trois machines ; le projet reste donc en **M0 — fondations**. DVC, Wwise et Steam ne bloquent pas ce jalon.

## Priorités immédiates

Faire ces lots dans l'ordre. Les noms désignent une affinité de départ ; le propriétaire réel du poste ou la disponibilité prime.

Déjà terminé : premier import Unity, lockfile et migrations déterministes via la PR #10 ; deux instances Mac se sont authentifiées avec un roster local à deux.

| Priorité | Lot | Affinité pilote | Binôme | Preuve attendue |
|---:|---|---|---|---|
| P0 | ouverture propre sur le second Mac | Sean | Nils | doctor vert et aucun diff après ouverture/fermeture |
| P0 | validation Windows IL2CPP | propriétaire du PC / Zak | Nils | exécutable lancé, log archivé dans l'issue |
| P0 | connexion distante à trois via Tailscale + Tugboat | Zak | les deux autres | Zak, Sean, Nils visibles dans le roster depuis trois réseaux |
| P1 | blockout du pivot en T et échelle joueur | Sean | Zak | scène grise comprise sans explication |
| P1 | registre licences/données du premier lot | Zak | Sean | provenance et restrictions complètes |
| P2 | choisir le remote DVC privé au premier master lourd | Nils | Zak | pull/push/restauration Mac + Windows avant de partager ce master |
| P2 | gate Wwise Mac/Windows après le premier gameplay | Nils | Sean | événement sonore dans deux builds |
| P2 | transport Steam | Zak | Nils | connexion réelle entre deux comptes |

Le testeur externe du lot n'est ni son pilote ni son binôme. Les chapeaux tournent au lot suivant.

Le dépôt privé gratuit utilise le contrat local partagé : pas de push direct vers `main`, préfixe de branche contrôlé, PR et CI. Une protection serveur absolue pourra être ajoutée plus tard, mais elle n'est pas nécessaire pour démarrer à trois.

## M0 — définition de terminé

- les trois diagnostics passent ;
- le projet s'ouvre sans resérialisation massive sur les trois machines ;
- un build Windows Development IL2CPP se lance ;
- les trois machines rejoignent la même session Tugboat depuis leurs réseaux respectifs.

Le coffre DVC s'ouvre avant de partager le premier master lourd ou irremplaçable. Wwise s'ouvre après le premier gameplay testable, avec Nils comme seul poste Authoring au départ. Steam attend que Tailscale ait prouvé la connexion. Ces trois chantiers restent prévus, mais ne retardent pas l'onboarding.

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
