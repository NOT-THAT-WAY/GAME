# Fondation gameplay du sandbox

État au 14 août 2026 : la branche `feat/sandbox-gameplay-foundation` transforme le banc M1 en
petit sandbox jouable, sans prétendre figer le game design final. Le mur rotatif 360° reste intact ;
la nouvelle couche ajoute les contrôles, les ressources, le combat, trois cases de transport, un
caillou physique et une première boucle de trophée.

## Contrat de contrôle

| Intention | Clavier/souris | Manette |
| --- | --- | --- |
| Se déplacer | `ZQSD` ou flèches | stick gauche |
| Regarder | souris | stick droit |
| Sprinter | `Maj` maintenu | clic stick gauche |
| Sauter | `Espace` | bouton Sud |
| Plonger en avant (en sprintant vers l'avant) | `Ctrl gauche` ou `C` | LB/L1 |
| Ramper / se relever (hors sprint ; `Espace` relève aussi) | `Ctrl gauche` ou `C` | LB/L1 |
| Interagir / ramasser | `E` | bouton Ouest |
| Pousser le mur | maintenir `E` au contact | maintenir bouton Ouest |
| Frapper / lancer l'objet actif | clic gauche ou `F` | gâchette droite |
| Lâcher l'objet actif | `A` | bouton Est |
| Choisir une case | `1`, `2`, `3` | — |
| Case suivante | `Tab` | épaule droite |
| Basculer 1re / 3e personne | `F1` | croix haut |
| Zoom 3e personne | molette | croix gauche/droite |
| Pause / libérer le curseur | `Échap` | Start |

`A` n'est volontairement pas une direction : le déplacement clavier canonique est AZERTY et le
test d'import interdit qu'un binding de mouvement récupère cette touche.

## Baseline à tester

Toutes les durées de gameplay sont calculées à 60 ticks/s. Elles sont regroupées dans
`SandboxGameplayConfig.Baseline60Hz`, afin qu'un futur réglage soit un changement visible et testé.

| Élément | Baseline |
| --- | --- |
| Marche / sprint | 4,2 m/s / 7 m/s |
| Saut | impulsion 5,5 m/s, gravité -22 m/s², coyote 7 ticks, buffer 9 ticks |
| Plongeon avant | 13 m/s vers l'avant + 4,2 m/s vers le haut (~5 m), relevé 24 ticks, attente 90 ticks ; seulement en sprint vers l'avant, au sol, contrôle coupé en vol |
| Ramper | 1,7 m/s, capsule abaissée à 0,85 m, sprint/saut/plongeon coupés ; caméra à 0,55 m (cosmétique) |
| Vie / énergie | 100 / 100 |
| Coup de poing | 25 dégâts, 25 énergie, cooldown 48 ticks |
| Caillou | 30 dégâts, lancer 18 énergie, vitesse 11 m/s + 2,4 m/s vers le haut |
| Trophée lancé | 10 dégâts, même coût et même vitesse de lancer |
| Sprint normal | -1 énergie tous les 5 ticks, soit 12/s |
| Poussée valide du mur | -1 énergie tous les 4 ticks, soit 15/s |
| Régénération énergie | délai 60 ticks, puis +1 tous les 4 ticks |
| Régénération vie | délai 300 ticks après dégâts, puis +1 tous les 10 ticks |
| KO | 240 ticks (4 s), retour à 40 PV, protection 60 ticks |
| Trophée porté | vitesse ×0,75 ; sprint autorisé ; coût du sprint ×5 |
| Avec trophée | coup et poussée interdits ; lancer et lâcher autorisés |
| Inventaire | 3 cases, une seule case active |
| Manche | 3 s de compte à rebours, 90 s de jeu, 3 s de résultat |

Quatre coups mettent donc KO un joueur plein. Un seul caillou enlève 30 % de la vie : les deux
actions ont un impact immédiatement lisible, mais les chiffres restent des hypothèses de playtest.

## Boucle jouable

1. Le serveur fait apparaître six cailloux et un trophée dans l'arène 6×6.
2. `E` ramasse l'objet disponible le plus proche à moins de 1,7 m, si une case est libre.
3. L'objet de la case active est visible en main ; les deux autres sont transportés mais masqués.
4. Clic gauche ou `F` lance l'objet actif. Le serveur fixe la trajectoire et la dépense d'énergie.
5. Un caillou ou trophée lancé rebondit, ne peut blesser qu'une fois par lancer, se stabilise, puis
   redevient ramassable.
6. Un joueur à zéro PV lâche tout, ne peut plus agir, puis se relève automatiquement.
7. Porter le trophée ralentit le joueur. Entrer vivant dans la zone orange avec le trophée termine
   la manche ; les ressources et objets sont remis à zéro pour la suivante.

Le reset de manche ne replace pas encore les joueurs à leur spawn. C'est intentionnellement laissé
comme limite visible du prototype, à décider après le premier test de boucle.

## Autorité et séparation des responsabilités

- Le client transmet des intentions de contrôle déjà intégrées aux commandes prédites.
- L'hôte décide de l'énergie, du ramassage, de la case active, des dégâts, du KO, des lancers, des
  impacts, du dépôt et du résultat de manche.
- Le `NetworkTransform` transporte uniquement la pose des objets physiques ; il n'est pas utilisé
  sur le joueur prédit.
- Les animations et le HUD présentent l'état. Aucun événement d'animation ne décide si un coup ou
  un projectile touche.
- Le ralentissement du trophée est injecté comme modificateur de la simulation de déplacement, et
  non comme correction visuelle après coup.

Les fichiers centraux sont `Runtime/Sandbox/`, `Runtime/Player/M1PlayerActions.cs`,
`Runtime/Player/PredictedPlayerMotor.cs` et `Editor/M1PlaytestBuild.cs`.

## Preuves automatisées disponibles

| Niveau | Ce qui est vérifié |
| --- | --- |
| EditMode | ressources, cadence, régénération, KO/relevé, multiplicateur trophée, inventaire, manche, mappings d'input, vitesse simulée |
| PlayMode | contrat historique du joueur, du mur et de l'arène |
| Génération M1 | saut actif, composants sandbox, prefabs réseau, zone de dépôt, paramètres Animator, root motion désactivé |
| Réseau mur | occupation, opposition et late join restent valides |
| Réseau trophée | apparition, ramassage, ralentissement/route, dépôt, vainqueur et reset |
| Réseau caillou | ramassage, lancer réel, collision physique, 30 dégâts sur l'autre processus |
| Réseau poing | quatre impacts autoritaires, vie 75/50/25/0 et KO |

Les profils `sandbox-trophy-run`, `sandbox-rock-target`, `sandbox-rock-thrower` et
`sandbox-puncher` de `M1AutomatedCommandSource` sont des sondes de build Development, pas des bots de
jeu destinés à la production.

## Test humain recommandé

Faire une session à deux joueurs et noter séparément :

1. lisibilité du changement de vue et du saut ;
2. durée agréable du sprint normal, puis avec trophée ;
3. conflit éventuel entre `E` pour ramasser et maintenir `E` pour pousser ;
4. portée de ramassage et choix automatique de la case ;
5. lisibilité du lancer, du rebond et du moment où le caillou redevient ramassable ;
6. impact du poing, du caillou, du knockback et des quatre secondes de KO ;
7. intérêt de pouvoir lancer le trophée contre le risque de le perdre ;
8. clarté de la zone orange et du verdict de manche ;
9. besoin ou non de replacer les joueurs à chaque nouvelle manche.

Le résultat attendu de cette passe est une liste courte de réglages, pas de nouvelles mécaniques.
Après ce verdict seulement viennent l'intégration des animations, le vrai HUD, les sons/VFX et les
règles d'inventaire plus riches.
