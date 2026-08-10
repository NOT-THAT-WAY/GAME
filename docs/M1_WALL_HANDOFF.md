# Reprise M1 — battant rotatif : état, mesures, plan

Document de passage de relais. Il décrit ce qui est en place sur la branche
`feat/m1-minimal-skeleton`, ce que la session humaine du 2026-08-10 a réellement mesuré, le retour du
testeur, et le plan de la passe suivante. Quiconque reprend la branche — humain ou agent — devrait
pouvoir travailler à partir d'ici sans relire l'historique.

## 1. Où en est la branche

Dernier commit : `74baeac feat: faire tourner le mur librement sur 360 degrés`.

Le banc M1 est une arène graybox 2×2 construite au runtime depuis
`Assets/_Project/Maze/GrayboxTopology2x2.v1.json`. Ce n'est pas le labyrinthe 16×16 et ce n'est pas
« le jeu » : c'est un instrument de mesure réseau.

Le mur mobile `wallId=10` a été refait en **battant libre** (ADR 0005) :

- état partagé = `angle (milli-degrés), vitesse angulaire (mdeg/tick), tick d'ancrage, révision` ;
- le couple net du tick donne directement la vitesse : pas de seuil à charger, pas d'inertie ;
- le sens vient du demi-plan occupé par le pousseur à l'angle courant → valable sur 360°, dans les
  deux sens, sans état de destination ;
- bras de levier au prorata : 300 pour mille au gond, 1000 au bout du battant ;
- les couples signés s'additionnent → la contre-poussée est gratuite, sans règle supplémentaire ;
- le couple net est quantifié à 50 pour mille pour ne pas ouvrir un segment réseau par tick ;
- trigonométrie entière CORDIC (`FixedTrigonometry`) pour que côté, levier et contact rendent le
  même verdict sous Mono et sous IL2CPP.

### Fichiers qui portent la mécanique

| Fichier | Rôle |
| --- | --- |
| `Runtime/Maze/Simulation/WallRotationMachine.cs` | intégrateur pur, un tick = une vitesse |
| `Runtime/Maze/Simulation/WallState.cs` | réglages, intention de couple, état/segment, quantification |
| `Runtime/Maze/Simulation/WallPose.cs` | pose logique échantillonnée d'un tick |
| `Runtime/Maze/Simulation/WallSnapshot.cs` | codec binaire v2 (21 octets, sans flottant) |
| `Runtime/Maze/Simulation/FixedTrigonometry.cs` | CORDIC entier micro-degrés → Q16 |
| `Runtime/Maze/Simulation/M1WallInteractionRules.cs` | portée, côté, abscisse, bras de levier |
| `Runtime/Maze/Topology/TopologyGeometry.cs` | `TopologyBladeSpec.Probe` : mesure entière du contact |
| `Runtime/Maze/M1AuthoritativeWallDirector.cs` | adaptateur FishNet : intentions, tick, snapshots, poussée des balayés |
| `Runtime/Maze/TopologyWallView.cs` | pose du transform et du BoxCollider depuis l'angle |
| `Runtime/Player/M1PlayerActions.cs` | coup de poing serveur, pose de poussée, indicateur de levier |
| `Runtime/Player/M1PlayerAppearance.cs` | teinte, bras en vue subjective, bascule 1re/3e personne |
| `Editor/M1PlaytestBuild.cs` | génération de la scène, du prefab et des réglages sérialisés |

### Réglages actuels (sérialisés dans `M1PlaytestBuild.CreateWallAuthorityPrefab`)

| Réglage | Valeur | Effet à 60 Hz |
| --- | --- | --- |
| `_maximumAngularSpeedMilliDegreesPerTick` | 900 | 54 °/s à pleine puissance |
| `_minimumLeveragePermille` | 300 | 16 °/s au contact du gond |
| `_maximumExtrapolationTicks` | 180 | 3 s d'avance libre maximum côté client |
| `_reachFromCapsuleMm` | 900 | portée de contact depuis la capsule |
| `LeverageQuantumPermille` | 50 | 15 paliers de vitesse entre gond et bout |
| `M1PunchTuning.WallImpulseTicks` | 40 | un coup verse 40 ticks de couple |
| `M1PunchTuning.CooldownTicks` | 48 | cadence maximale du bras |
| `MaximumPushSpeedMetersPerSecond` | 3,5 | plafond de la poussée subie |

### Gates, toutes vertes au commit

```bash
./scripts/unity-tests-macos.sh all          # 105 EditMode + 7 PlayMode
python3 tests/topology-fixtures/test-fixtures.py
bash tests/m1-network/test-wrapper-contract.sh
./scripts/validate-repository.sh
./scripts/m1-network-tests-macos.sh all --build
./scripts/m1-preview-macos.sh --player      # captures dans Logs/M1Playtest/
./scripts/m1-human-test-macos.sh            # banc à deux fenêtres
```

## 2. Ce que la session humaine a mesuré

Session `Logs/HumanTest/M1-20260810T115724Z-41451`, deux fenêtres macOS, hôte + client local.

### Le réseau est propre

- `snapshot_rejected` = 0, `history_miss` = 0, aucune exception, aucun crash ;
- l'hôte et le client finissent sur le **même angle et la même révision** : `20070 mdeg`, `rev 124` ;
- 963 snapshots reçus côté client pour 124 segments : le battement d'une seconde domine, la
  quantification tient sa promesse.

Rien à corriger de ce côté. Les points ci-dessous sont du **feel**, pas de l'infra.

### Le battant tourne — beaucoup trop

- **24 segments de poussée**, **8 quarts de tour franchis**, soit **720° cumulés** en une session ;
- de nombreux segments à `vel=900`, c'est-à-dire la vitesse maximale, saturée ;
- `swept_player_pushed` = 56, avec des vitesses de 3,2 à 3,4 m/s, donc collées au plafond de 3,5.

### Deux règles n'ont jamais été exercées

- **`direction_reversed` = 0, et les 24 segments sont tous `direction=1`.** Le battant n'a jamais
  tourné dans l'autre sens. La quête 3 n'a pas de verdict : soit elle n'a pas été tentée, soit
  repasser sur l'autre face est trop pénible dans une arène de 5,5 m où le battant balaie tout.
- **`torque_opposed` = 0.** La contre-poussée à deux n'a jamais eu lieu. La quête 4 n'a pas de
  verdict non plus.

Ces deux mécaniques sont prouvées par les tests EditMode et par le scénario réseau `opposition`,
mais **aucun humain ne les a validées**. C'est la première chose à obtenir à la prochaine passe.

### Le coup de poing

`wall_impulse` = 5, `GAME-M1-PUNCH] hit` = 0 — cinq coups sur le mur, aucun sur l'autre joueur. Un
coup verse 40 ticks de couple au levier du contact : jusqu'à `40 × 900 = 36 000 mdeg`, soit **36° de
rotation pour un seul coup**. C'est ce que le testeur décrit comme « le coup de poing balance trop ».

## 3. Retour du testeur, tel qu'il l'a donné

> « ok ça va mais il y a des collisions et bras passe à travers (pas si grave […] tant qu'il y a une
> cohérence sur comment la physique de pousser le joueur marche quand même). […] le coup de poing
> balance trop, le mur aussi avance trop vite, […] il faut que le mur soit un peu plus lourd. Aussi,
> on peut agrandir l'espace, mettre une salle plus grande […] doubler les mesures et tripler le
> terrain de jeu autour, pour avoir plus de place et que ce soit plus clair. Faire en sorte d'avoir
> aussi une vue troisième personne qui soit plus proche du personnage et qui ne soit jamais vue à
> travers un mur. […] qu'il puisse voir son personnage logiquement et que ce soit jamais à travers
> un mur. »

Traduction en éléments actionnables, par priorité décroissante :

1. agrandir l'arène ;
2. alourdir le battant (vitesse continue) ;
3. réduire l'effet d'un coup de poing sur le battant ;
4. caméra troisième personne proche, jamais dans un mur, orbite autour du personnage ;
5. traversées visuelles bras/mur : **tolérées**, à ne traiter qu'après le reste.

## 4. Plan de la prochaine passe

L'ordre compte : la taille de l'arène change la longueur du battant, donc la vitesse ressentie. Ne
pas régler la vitesse avant d'avoir figé la géométrie.

### Étape 1 — Agrandir l'arène

**Décision à prendre en premier, elle conditionne le reste.** Deux lectures de la demande :

- **A — grille plus grande, battant inchangé** : passer de 2×2 à 6×6 cellules en gardant
  `cellPitchMm = 2750`. Arène de 16,5 m × 16,5 m au lieu de 5,5 m. Le battant garde 2,75 m, donc
  **tous les réglages de levier et de vitesse restent valides**, et le pousseur a la place de
  contourner le battant pour le prendre à revers. C'est l'option recommandée : elle répond à
  « plus de place, plus clair » sans invalider le travail de réglage.
- **B — tout doubler** : `cellPitchMm = 5500`, battant de 5,5 m. Le bout du battant se déplace deux
  fois plus vite à vitesse angulaire égale, donc la vitesse doit être divisée par deux rien que pour
  retrouver le ressenti actuel. Plus proche du mot « doubler », mais rejoue tout le réglage.

Recommandation : **A**, éventuellement avec un `cellPitchMm` porté à 3500–4000 pour élargir un peu
les couloirs sans doubler le battant.

Marche à suivre, quelle que soit l'option :

1. éditer `Assets/_Project/Maze/GrayboxTopology2x2.v1.json` : dimensions, liste des murs de
   périmètre, deux spawns éloignés, pivot au centre. **Le périmètre doit rester entièrement fermé** :
   c'est ce qui empêche un joueur de tomber hors du sol.
2. recalculer le checksum. Il est produit par la forme canonique de `TopologyCanonicalizer` ; le plus
   simple est de lancer `python3 tests/topology-fixtures/test-fixtures.py` et de reprendre la valeur
   attendue, ou d'ajouter un checksum volontairement faux et de lire celui que la validation réclame.
3. mettre à jour les constantes de checksum et de comptage de murs dans
   `Tests/EditMode/TopologyGeometryTests.cs` et `Tests/PlayMode/TopologyArenaPlayModeTests.cs`
   (`arena.WallCount`, nombre de colliders actifs = murs + 1 sol).
4. **repositionner les bots automatisés.** `M1AutomatedCommandSource` contient les profils
   `push-left` / `push-right`, dont le sens de marche est lié à la disposition actuelle des spawns.
   Si les spawns changent de côté, ces profils poussent dans le vide et les trois scénarios réseau
   tombent. Vérifier avec `./scripts/m1-network-tests-macos.sh all --build`.
5. penser au décor : `M1PlaytestBuild.CreateDecor` et la caméra spectateur sont dimensionnés sur
   l'arène actuelle.

Critère de PASS : les trois scénarios réseau repassent, la capture aérienne montre une enceinte
close, et un joueur peut faire le tour complet du battant sans être balayé.

### Étape 2 — Alourdir le battant

Un seul fichier : `Assets/_Project/Editor/M1PlaytestBuild.cs`, méthode `CreateWallAuthorityPrefab`.

- `_maximumAngularSpeedMilliDegreesPerTick` : **900 → 400** (24 °/s ; quart de tour en 3,75 s à
  pleine puissance au lieu de 1,7 s). Point de départ, à ajuster en jeu.
- `_minimumLeveragePermille` : **300 → 400**. À 400 mdeg/tick, 30 % au gond donnerait 7 °/s, soit
  13 s pour un quart de tour — injouable. Remonter le plancher garde le contraste du levier
  (400 → 1000, soit ×2,5) sans rendre le gond inutile.
- `MaximumPushSpeedMetersPerSecond` dans `M1AuthoritativeWallDirector` : 3,5 est saturé en
  permanence dans les logs. Une fois le battant ralenti, la vitesse de surface baissera d'elle-même ;
  vérifier que la poussée reste **supérieure** à la vitesse du battant, sinon un joueur balayé est
  rattrapé et poussé en continu au lieu d'être dégagé.

Ces trois valeurs entrent dans l'empreinte de simulation (`ComputeSimulationFingerprint`) : hôte et
clients doivent tourner **le même build**, sinon les snapshots sont refusés — c'est voulu.

Critère de PASS : un humain décrit le battant comme lourd mais réactif, et un tour complet demande
un effort visible.

### Étape 3 — Calmer le coup de poing

`Assets/_Project/Runtime/Player/M1PlayerActions.cs`, bloc `M1PunchTuning`, et
`M1AuthoritativeWallDirector.TryRegisterPunchImpulse`.

Deux leviers, à combiner :

- réduire `WallImpulseTicks` de 40 à ~15 ;
- ajouter un facteur d'atténuation propre au coup, par exemple
  `PunchTorqueScalePermille = 500`, appliqué au levier au moment de créer l'impulsion :
  `decision.LeveragePermille * PunchTorqueScalePermille / 1000`.

Avec l'étape 2 et ces deux réglages, un coup vaut ≈ 15 × 400 × 0,5 = 3 000 mdeg, soit **3°** au lieu
de 36°. Un coup devient un à-coup lisible, pas une bourrasque.

Ajouter un test EditMode dans `M1WallNetworkModelTests` qui fige la rotation produite par un coup :
c'est un nombre de game design, il doit être verrouillé par un test pour qu'on voie quand il change.

### Étape 4 — Caméra troisième personne

État actuel : `M1PlayerAppearance` place simplement la caméra à un décalage fixe
`ThirdPersonCameraOffset = (0, 0.55, -3.4)`, sans aucun test de collision. Elle traverse donc les
murs, ce que le testeur a vu.

Ce qu'il faut construire, **entièrement cosmétique et local** — donc `Update`, `Time.deltaTime` et
les requêtes physiques sont autorisés ici, contrairement à toute règle partagée :

1. **Bras à ressort.** Depuis un point d'ancrage à hauteur d'épaule sur le personnage, faire un
   `Physics.SphereCast` vers la position de caméra souhaitée, contre le seul layer
   `GameplayLayers.World` (8), rayon ~0,25 m. Si le rayon touche, ramener la caméra au point de
   contact moins une marge. Distance minimale ~1,2 m pour que le personnage reste visible et que la
   caméra ne finisse jamais à l'intérieur de son propre corps.
2. **Lissage asymétrique.** Rentrer instantanément (sinon la caméra traverse pendant une frame),
   ressortir progressivement (sinon la caméra saute dès qu'un mur passe). Un lissage exponentiel sur
   la seule longueur du bras suffit.
3. **Orbite.** Le testeur demande de pouvoir tourner autour du personnage. Aujourd'hui le lacet fait
   pivoter le personnage lui-même. Deux options : soit la caméra orbite librement et le personnage
   ne s'oriente que quand il se déplace, soit l'orbite est une entrée séparée. **C'est une décision
   produit, pas une évidence technique** : la demander avant de coder, parce qu'elle change le
   contrat d'input, donc `GameControls.inputactions` et `PlayerInputSource`.
4. **Anti-occultation rapprochée.** Quand le bras est très court, basculer les renderers du corps du
   porteur en `ShadowCastingMode.ShadowsOnly` — le mécanisme existe déjà dans
   `M1PlayerAppearance.ApplyAppearance` pour la vue subjective, il suffit de le réutiliser.
5. Le mur mobile est sur le layer `World` : la caméra doit donc aussi être repoussée par **le
   battant en mouvement**, ce qui est le cas gratuitement avec le SphereCast.

Preuve attendue : un test PlayMode qui place un joueur dos à un mur et vérifie que la caméra reste
du bon côté de la surface, plus une capture `m1-preview-macos.sh --player` en troisième personne
collé à un mur.

### Étape 5 — Traversées visuelles, basse priorité

Cause connue : la collision est un unique `CharacterController` de 0,4 m de rayon, alors que le
visuel FBX est plus large et anime des bras au-delà de ce rayon. Le testeur les accepte
explicitement. Ne pas ajouter de collider au visuel — le FBX reste sur `VisualOnly` sans collider,
c'est une règle du projet. Si on y revient un jour, la voie propre est de réduire l'amplitude de
l'animation ou d'élargir légèrement la capsule, pas d'ajouter de la collision au maillage.

## 5. Ce qu'il ne faut pas casser

- **Le client envoie une intention, l'hôte décide.** Aucun `wallId`, aucun côté, aucun levier ne
  vient d'un client. Tout est recalculé serveur dans `M1AuthoritativeWallDirector`.
- **La pose du mur est une fonction du tick**, jamais un transform diffusé par image. Un segment
  n'est émis que si la vitesse change, plus un battement d'une seconde. Si un changement fait
  remonter le nombre de segments, c'est une régression : le compteur est visible dans le verdict
  (`revision=`) et dans `snapshots=` côté client.
- **`Time.deltaTime` et `Time.time` restent cosmétiques.** Caméra, UI, animation : oui. Collision,
  cooldown, couple, angle : jamais.
- **Pas de lecture directe `Keyboard.current` / `Mouse.current`** dans le contrat joueur —
  `validate-repository.sh` le refuse.
- **La topologie signée produit les colliders**, jamais un nom d'objet ou un triangle de FBX.
- **Ne jamais travailler directement sur `main`**, ne jamais contourner le hook, livrer par PR et
  laisser Nils décider du merge.

## 6. Décisions produit encore ouvertes

À trancher avec l'équipe, pas à inventer :

- taille finale de l'arène (option A ou B ci-dessus) ;
- vitesse nominale, levier minimal et pas de quantification comme valeurs produit ;
- orbite caméra : libre, ou liée à l'orientation du personnage ;
- conséquence d'un joueur coincé entre le battant et l'enceinte — rien n'arrête la rotation
  aujourd'hui ;
- énergie, coût du coup de poing, cooldown ;
- réintégration de ce socle dans le labyrinthe 16×16.

## 7. Première chose à faire en reprenant

Relancer le banc et **obtenir les deux verdicts manquants** avant de changer quoi que ce soit :
pousser le battant dans le sens négatif depuis l'autre face, et se mettre à deux de part et d'autre
pour vérifier que le mur se fige. Sans ces deux mesures, on règlerait la vitesse d'une mécanique
dont la moitié n'a jamais été observée par un humain.

```bash
./scripts/m1-human-test-macos.sh
# puis, après fermeture des fenêtres :
grep -cE "direction_reversed|torque_opposed" Logs/HumanTest/M1-*/host.log
```
