# Entrées et commande joueur — contrat INP-01

Le chemin M1 ne lit jamais directement `Keyboard.current`, `Mouse.current` ou `Gamepad.current`.
`GameControls.inputactions` décrit les périphériques ; `PlayerInputSource` est l'unique frontière Unity
et `PlayerCommand` est l'intention compacte destinée à un tick.

## Contrat de l'asset

- Map `Player` : `Move`, `LookPointer`, `LookStick`, `Sprint`, `Interact`, `Punch`, `Jump`, `Dive`,
  `Pause`.
- Map `UI` : `Navigate`, `Submit`, `Cancel`, `Point`, `Click`, `Scroll`.
- Schemes `KeyboardMouse` et `Gamepad` validés au chargement et en EditMode.
- Le pointeur produit un delta par frame ; le stick produit un taux intégré une seule fois avec la
  durée explicite du tick. Les deux unités ne sont donc jamais additionnées comme si elles étaient
  équivalentes.
- La deadzone native du layout `Gamepad` s'applique une seule fois ; l'asset n'empile aucun processor
  `stickDeadzone` supplémentaire sur l'action ou le binding.
- Chaque joueur clone l'asset. Il peut limiter sa copie à une liste de devices sans contaminer une
  seconde source locale.

## Commande réseau pure

- Mouvement : deux `sbyte` dans `[-127, 127]`, diagonale normalisée, `-128` jamais produit.
- Regard : deux `short` en centièmes de degré, arrondi explicite et saturation sans wrap.
- Continus : `SprintHeld`, `InteractHeld`.
- Fronts mémorisés jusqu'au tick : `JumpPressed`, `DivePressed`, `InteractPressed`, `PunchPressed`.
- `Dive` : `Ctrl gauche` ou `C` au clavier, `LB/L1` à la manette — bindings de banc, pas un feel
  validé.
- `Pause` reste une action locale et n'entre pas dans `PlayerCommand`.

Un appui puis relâchement entre deux ticks est conservé. Après `Consume`, les fronts et deltas de
regard sont vidés exactement une fois ; mouvement et boutons tenus persistent. Perte/reprise de
focus, désactivation, restriction de devices et changement d'asset remettent tout le buffer à zéro.

## Décisions encore ouvertes

Les sensibilités par défaut sont des valeurs de banc sérialisées, pas une décision de feel. Le saut
reste capturé pour rendre le binding testable, mais PLY-01 doit pouvoir le désactiver par configuration
tant que DEC-01 ne l'a pas retenu. L'adaptateur FishNet utilisera un DTO mutable propre à FishNet : il
ne donnera pas directement ce `readonly struct` à son codegen.
