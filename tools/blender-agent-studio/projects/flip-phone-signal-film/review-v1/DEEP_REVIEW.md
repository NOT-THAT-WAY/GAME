# LAST SIGNAL V1 — revue profonde et plan de reconstruction

## Verdict

La V1 est une démonstration techniquement fonctionnelle, mais pas encore un film produit. Elle montre plusieurs recettes apprises sans leur donner une priorité dramatique. Le téléphone reste identifiable et la palette possède une signature, mais l’assemblage, les déplacements, les coupes et la lumière ne construisent pas une causalité continue.

Score pondéré V1 : **49/100**.

## Grille de classement

| Catégorie | Poids | V1 | Contribution | Critère de réussite |
|---|---:|---:|---:|---|
| Histoire et causalité | 15% | 50% | 7.50 | Chaque action produit visiblement la suivante |
| Lisibilité du produit | 12% | 63% | 7.56 | Silhouette, détails et états mécaniques compréhensibles |
| Mouvement objet | 12% | 34% | 4.08 | Axes crédibles, absence de glissement et de double transform |
| Caméra et raccords | 12% | 38% | 4.56 | Motivations, continuité spatiale, vitesse et cadrage maîtrisés |
| Rythme et respiration | 12% | 36% | 4.32 | Beats hiérarchisés, impacts courts, holds réels |
| Décor et profondeur | 8% | 48% | 3.84 | Monde utile à l’histoire, corridor libre, échelle cohérente |
| Matériaux et redesign | 8% | 62% | 4.96 | Matières différenciées et détails non écrasés |
| Lumière et couleur | 8% | 61% | 4.88 | Séparation de silhouette, exposition et progression narrative |
| Typographie et graphisme | 5% | 42% | 2.10 | Hiérarchie, placement, durée et lien avec le récit |
| Finition technique | 8% | 65% | 5.20 | Aucun glitch, image noire, clipping critique ou dépendance manquante |
| **Total** | **100%** |  | **49.00** |  |

Les notes visuelles sont limitées par des gates mesurables. Une note supérieure à 80 exige qu’aucun défaut critique de visibilité, mécanique ou continuité ne subsiste.

## Mesures temporelles V1

- 720 images, 24 fps, 30 secondes.
- Différence moyenne entre images : 5,99 niveaux de luminance.
- 95e percentile du mouvement : 14,61.
- Huit pics au-dessus du seuil 99e percentile.
- Pics majeurs aux coupes : frame 145 / 6 s = 35,33 ; frame 289 / 12 s = 86,76 ; frame 433 / 18 s = 56,35 ; frame 601 / 25 s = 47,00.
- Freeze détecté de 0,83 à 1,33 s et hold terminal à partir de 29,21 s. Le hold terminal est souhaitable ; le premier ralentit une ouverture déjà peu informative.
- 52% des pixels sont noirs en moyenne. Le contraste est volontaire, mais le décor perd souvent ses volumes et ne permet plus de lire le trajet.

## Problèmes trouvés dans le script

### Double transformation hiérarchique

Le reveal anime `Buttons`, `Hinge`, `Screen.001`, `Screws2` et `Screws3`. Or `Screen.001` est enfant de `Hinge`, et les textes des touches sont enfants de `Buttons`. Le déplacement du parent se cumule avec celui du descendant. Des pièces traversent donc le cadre sans trajectoire mécanique crédible.

### Transport sans preuve de contact

`PRODUCT_ROOT` se déplace linéairement, mais les lattes du convoyeur restent immobiles. La caméra translate elle aussi durant le même beat. Sans vitesse relative stable ni tapis animé, l’œil interprète un drift du produit.

### Courbes génériques

Les caméras reçoivent toutes du Bézier Auto Clamped, quelle que soit leur fonction. La règle des quatre clés est appliquée à des durées complètes de six secondes plutôt qu’à des gestes courts. Elle devient une oscillation constante, pas une anticipation suivie d’un recovery.

### Raccords arbitraires

Les caméras changent exactement à 6, 12, 18 et 25 secondes. Le sujet ne conserve ni taille écran, ni axe, ni direction dominante. À 12 secondes, une surface floue et sombre remplit l’image : c’est une occultation accidentelle, pas un wipe motivé.

### Concurrence entre actions

Le root, la charnière, la cible caméra, le focus, la focale, la position caméra, les anneaux et les particules se déplacent parfois ensemble. Aucun canal ne devient le geste principal. Le spectateur voit de l’activité, mais ne sait pas quelle information retenir.

### Lumière non dramatique

Les quatre sources suivent la cible produit pendant tout le film. Le monde ne possède donc pas vraiment un état éteint puis allumé. L’histoire affirme une restauration du signal, mais la lumière produit est déjà complète avant l’activation.

### Typographie plaquée

Le titre d’ouverture masque les premières transformations, et le carton final décrit littéralement les actions déjà vues. La typographie commente la démonstration au lieu de porter un enjeu ou un message.

## Reconstruction V2

Nouvelle histoire : un téléphone oublié dans un observatoire silencieux reçoit un dernier message. Un scanner le reconnaît, il traverse une voie unique, s’arrête, écoute, s’ouvre, puis son écran rallume successivement trois balises. Le produit se soulève seulement après que le monde a répondu.

Règles de réalisation :

1. Une cause et un mouvement dominant par beat.
2. Aucune animation simultanée d’un parent et de son descendant.
3. Caméra fixe pendant le transport linéaire.
4. Coupe seulement sur un hold, avec sujet conservé dans la même zone de cadre.
5. Charnière seule animée ; écran et détails héritent naturellement.
6. Lumière du décor activée après le message, jamais avant.
7. Palette graphite, ivoire chaud, cuivre oxydé, turquoise et orange signal.
8. Typographie courte : titre, message, résolution. Aucun texte pendant une action mécanique.
9. Dernière seconde réellement immobile.
10. Gates à chaque état narratif, puis analyse temporelle du MP4 final.

