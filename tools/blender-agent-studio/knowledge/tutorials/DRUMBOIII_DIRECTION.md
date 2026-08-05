# Direction prioritaire — Drumboiii

## Politique de réalisation

Pour les prochaines réalisations, les tutoriels Drumboiii sont la référence prioritaire pour
la **mise en scène, le mouvement caméra, le caractère Squishy, le monde HDRI, le ciel, la
lumière et le mouvement d’ambiance du décor**. Cette priorité ne remplace pas les contrats
physiques, les dimensions ou la mécanique réelle d’un objet.

Ordre de décision :

1. vérité physique et affordance de l’objet ;
2. intention narrative et continuité du film ;
3. grammaire Drumboiii pour mouvement, caméra, focus, monde, reflets et lumière ;
4. tutoriels spécialisés pour modélisation, rig, boucles ou effets ;
5. presets génériques seulement comme fallback.

Si une préférence stylistique contredit un axe de charnière, un support, une collision ou la
fonction humaine d’un objet, le contrat physique gagne. Si plusieurs looks sont physiquement
valides, la solution la plus proche de la grammaire Drumboiii gagne.

## Grammaire unifiée mouvement + caméra + monde + lumière

```text
objet juste et utilisable
→ animation primaire lisible : still / anticipation / action / recovery
→ caractère Squishy optionnel : scale overshoot + Lattice en overlap
→ décor vivant par déformeurs déphasés, jamais par transform du sujet
→ composition caméra K1 pose / K2 anticipation / K3 travel / K4 recovery
→ TARGET et focus animés par points d’attention
→ HDRI d'éclairage séparé du ciel caméra avec Is Camera Ray
→ ciel Noise + Gradient réglé selon la focale
→ monde/HDRI retenu à 0,5–0,7
→ Sun oblique qui dessine les reflets
→ backlight dominant qui sépare le volume
→ glimmers locaux faibles, chacun avec une fonction
→ gates mouvement par pose + fond/reflets séparés + lumière par couche
→ correction d’une seule famille de causes à la fois
```

## Règle Squishy

- Le root de l'objet conserve placement, rotation et scale global.
- Une Lattice séparée porte uniquement la déformation secondaire.
- Le pop principal utilise `0 → overshoot → cible → petit rebound`.
- La Lattice démarre légèrement avant ou chevauche l'action principale.
- Sur un objet multi-mesh, chaque mesh déformable reçoit la même Lattice.
- Subdivision et Strength sont augmentées progressivement, après contrôle de l'identité.
- Écrans, logos, trims et surfaces informatives sont gatés aux extrêmes.

## Règle mouvement d'ambiance

- Un élément de décor bouge par **déformeurs**, jamais par sa transform : l'appui, la
  pénétration et la dérive de contact restent alors exactement mesurables.
- Deux Simple Deform en mode Twist sur des **axes perpendiculaires**, mêmes valeurs de signe
  opposé, portent le mouvement.
- Leurs clés sont décalées d'un **quart de période**. En phase, les deux axes atteignent
  leurs extrêmes sur la même frame et le mouvement redevient une raideur.
- L'amplitude se règle **par le bas** : partir de 10°, jamais des 45° par défaut.
- La variante sans clé est un driver `#frame/<fps>` sur la rotation d'un Empty servant
  d'`Origin` au déformeur. Le driver écrit des **radians** : `#frame/<fps>` vaut exactement
  1 rad/s, soit un tour toutes les 6,28 s. **Le diviseur est la cadence** — à 24 fps on écrit
  `#frame/24`.
- Un driver n'apparaît pas dans le Dope Sheet. Tout gate de mouvement basé sur les F-Curves
  doit donc déclarer explicitement les propriétés pilotées.
- Cette règle ne s'applique qu'au décor. Un sujet dont le contrat physique impose une
  géométrie rigide n'est jamais déformé.

## Règle HDRI et ciel

- Le HDRI éclaire et produit les reflets ; un second Background est visible par la caméra.
- `Light Path → Is Camera Ray` pilote le Mix Shader entre ces deux fonctions.
- Les nuages viennent de `Noise Texture → ColorRamp` ; la profondeur vient de
  `Gradient Texture → ColorRamp` ; `Mix Color` combine les deux.
- L'échelle du Noise est recalibrée après tout changement important de focale ou de distance
  caméra.
- Le gate compare séparément ciel caméra, éclairage du sujet et reflets.

## Critères de goût traduits en gates

- la base doit sembler incomplète sans être illisible ;
- les reflets doivent expliquer les surfaces, pas les blanchir ;
- le backlight doit séparer le contour sans créer un halo gratuit ;
- un glimmer doit révéler un détail précis ;
- l’anticipation caméra doit se sentir sans devenir un wobble ;
- le recovery doit absorber l’énergie et s’arrêter ;
- le squash doit ajouter du caractère sans détruire l'identité ni plier les détails durs ;
- le target peut réagir avec quelques frames de retard, jamais dériver sans cause ;
- le focus doit être contrôlé aux poses hero ;
- le ciel visible peut changer sans recolorer les reflets du produit ;
- les nuages doivent rester proportionnés à la focale finale ;
- couleur et décor soutiennent le produit au lieu de compenser un éclairage plat ;
- le décor doit respirer sans attirer l'œil hors du sujet, et aucun extrême de ses deux
  déformeurs ne doit tomber sur la même frame.

## Sources internes

- caméra : `drumboii-camera-tutorial-2026-07-18/analysis.json` ;
- lumière : `drumboii-lighting-tutorial-2026-07-20/analysis.json` ;
- HDRI, ciel et Squishy : `drumboii-hdri-squishy-2026-07-21/analysis.json` ;
- mouvement d'ambiance et drivers : `drumboii-chains-movements-2026-07-31/analysis.json` ;
- physique et usage : `../PHYSICAL_WORLD_OBJECT_RULES.md`.
