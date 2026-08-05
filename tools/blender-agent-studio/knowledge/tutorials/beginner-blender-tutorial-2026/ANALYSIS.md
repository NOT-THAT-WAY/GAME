# Analyse profonde — Beginner Blender Tutorial 2026

## Ce que ce tutoriel ajoute au studio

Cette vidéo constitue une formation de production complète pour **Blender 5.0**. Elle ne
sert pas seulement à reproduire un donut : elle explique une chaîne de décisions allant de
la primitive au rendu final, avec les principales erreurs qui bloquent un débutant.

Le résultat final contient un donut, un icing, des sprinkles procéduraux, une assiette, une
tasse, une mousse de café, une table, une caméra et un éclairage de type café au lever du
soleil.

Corpus analysé :

- durée : 4 h 19 min 10 s ;
- transcription : 4 686 segments, environ 50 800 mots ;
- 480 frames régulières et 300 changements de scène ;
- dix planches chronologiques et dix-sept keyframes ciblées ;
- confiance globale : 0,96.

## Structure du cours

| Temps | Bloc | Compétences principales |
|---|---|---|
| 00:00–00:28 | Fondations | navigation, G/R/S, modes, torus, tasse, Solidify, Subdivision |
| 00:28–00:59 | Tasse | références, silhouette, loop cuts, anse, normales, modifier Apply |
| 00:59–01:30 | Icing | duplication, drips, proportional editing, Shrinkwrap, sculpt |
| 01:30–02:03 | Plate et rendu | extrusion, inset, Merge by Distance, Lattice, caméra, Principled, SSS |
| 02:03–02:35 | PBR | maps Base/Normal/Roughness, nodes, UV plate et donut |
| 02:35–03:09 | UV tasse | seams, Live Unwrap, îlots, Mio3 UV, texel density, atlas café |
| 03:09–03:46 | Sprinkles | Scatter on Surface, Weight Paint, Poisson, random materials |
| 03:46–04:19 | Final | parenting, sun/sky/bounce, DOF, Eevee, Cycles GPU, denoise |

## Doctrine de production extraite

### Rester non destructif jusqu’à ce qu’une opération exige de la vraie géométrie

Le tutoriel utilise Solidify et Subdivision comme paramètres réversibles. Solidify est
appliqué seulement lorsque l’anse doit réellement être extrudée depuis les faces internes de
la tasse. Subdivision est appliqué lorsque la sculpture nécessite davantage de vertices.

Pour Blender Studio, cela devient une règle de workflow :

1. travailler avec des modifiers ;
2. valider silhouette et proportions ;
3. créer une version avant `Apply` ;
4. appliquer uniquement le modifier nécessaire ;
5. auditer la topologie obtenue.

### L’ordre des modifiers est une partie du modèle

L’icing fournit l’exemple le plus important :

```text
Shrinkwrap → Solidify → Subdivision Surface
```

Projeter l’épaisseur entière après Solidify produit du z-fighting. Projeter d’abord la
surface, ajouter ensuite l’épaisseur et lisser à la fin conserve un icing propre et collé au
donut.

### Modéliser ce que la caméra doit réellement voir

La table finale est un simple plane, puisque la caméra ne voit jamais son épaisseur. Ce
principe doit être appliqué aux scènes produit : la complexité est justifiée par le cadre, les
ombres, les reflets et les mouvements prévus — pas par l’idée abstraite de compléter chaque
objet hors champ.

### Travailler depuis des références, puis exagérer avec intention

La référence contrôle les proportions et la plausibilité. L’artiste choisit ensuite les
caractéristiques lisibles à accentuer : drips plus nombreux, irrégularités, palette dominante,
contraste et direction de lumière. L’exagération reste un choix de design, pas une erreur de
mesure.

## Modélisation réutilisable

### Tasse hard-surface organique

- cylindre à résolution raisonnable ;
- suppression du couvercle ;
- Solidify pour l’épaisseur ;
- Subdivision pour la courbure ;
- loop cuts pour contrôler le pied et le bord ;
- application de Solidify avant l’anse ;
- extrusion par segments depuis une face centrale ;
- `Shift+N` si les normales produisent une extrusion inversée ;
- loops de support aux jonctions.

Gate : silhouette face/profil, épaisseur du bord, raccords de l’anse, absence de pincement et
normales cohérentes.

### Icing organique

- dupliquer le donut sans déplacement ;
- supprimer la moitié inférieure ;
- créer les drips avec Proportional Editing ;
- utiliser Shrinkwrap vers le donut ;
- placer Shrinkwrap avant Solidify et Subdivision ;
- appliquer Subdivision avant Inflate/Grab seulement si le sculpt est validé.

Gate : aucun z-fighting, épaisseur homogène, drips variés, silhouette intéressante depuis la
caméra et pas uniquement depuis le viewport libre.

### Assiette et variation organique

L’assiette illustre extrusion, scale, inset, Merge by Distance et Subdivision. Le Lattice sert
ensuite à produire une irrégularité globale sans déplacer chaque vertex du donut.

Gate : base plate, bord continu, absence de doubles vertices, subdiv propre, déformation
organique modérée.

## Matériaux, textures et UV

Le matériau PBR minimal fiable utilise :

```text
Base Color (sRGB) ───────────────→ Principled / Base Color
Normal (Non-Color) → Normal Map ─→ Principled / Normal
Roughness (Non-Color) ───────────→ Principled / Roughness
```

Metallic, alpha, AO et displacement ne doivent pas être connectés automatiquement. Ils sont
ajoutés uniquement si la matière et le moteur de rendu en ont besoin.

La stratégie UV est fondée sur quatre règles :

1. imaginer le mesh en papier ;
2. placer les seams dans les zones cachées ;
3. séparer les zones qui ne peuvent pas s’aplatir sans stretching ;
4. vérifier l’unwrap avec la texture réelle, pas seulement avec la forme des îlots.

Le tutoriel utilise **Mio3 UV / Gridify** pour redresser un îlot de tasse. Cette extension est
optionnelle et doit rester déclarée comme dépendance. La mousse de café utilise un atlas : un
îlot UV est placé sur une variation particulière du fichier au lieu de remplir toute l’image.

Les textures et l’addon Poliigon sont présentés par le propriétaire de Poliigon. Leur utilité
technique est réelle, mais leur source commerciale et leur licence doivent être enregistrées
séparément. Aucun fichier de texture externe n’a été copié par cette ingestion.

## Scatter on Surface et sprinkles

Le cours utilise le nouveau modifier Blender 5.0, construit sur Geometry Nodes :

1. créer plusieurs sprinkles low-poly ;
2. les placer dans une collection source ;
3. ajouter `Scatter on Surface` sur l’icing ;
4. sélectionner la collection ;
5. activer `Pick Instance` et `Reset Transform` ;
6. régler l’axe d’alignement et `Surface Offset` ;
7. peindre un Vertex Group en Weight Paint ;
8. utiliser ce groupe dans `Distribution Mask`, pas dans `Density` ;
9. utiliser Poisson Disc et Minimum Distance avec retenue ;
10. explorer le Seed et une légère inclinaison aléatoire.

Poisson Disc ne détecte pas la forme exacte des instances. Un espacement trop élevé produit
un arrangement artificiellement régulier ; un espacement trop faible laisse des collisions.
Le bon gate vérifie la vue caméra, puis change le Seed avant toute correction manuelle.

La palette est indépendante de la forme grâce à un matériau partagé :

```text
Object Info / Random → Color Ramp (Constant) → Principled / Base Color
```

La position des stops de la Color Ramp contrôle la proportion des couleurs. Une couleur
dominante et quelques accents sont plus lisibles qu’une répartition parfaitement égale.

## Éclairage, caméra et rendu

Le rig final sépare trois rôles :

- `SUN_KEY` : Sun chaud, direction du lever de soleil ;
- `SKY_FILL` : Point froid, large radius, ombres douces ;
- `INDOOR_BOUNCE` : Point neutre pour relever la zone sombre ;
- `BLOCKERS` : géométrie hors champ qui dessine les ombres.

Chaque lampe est évaluée seule. La taille de la source contrôle la douceur des ombres ; la
distance d’une Point light modifie fortement l’intensité à cause de l’inverse-square law. La
position d’un Sun ne change pas l’éclairage, seule sa rotation importe.

La caméra utilise `Lock Camera to View` seulement pendant le cadrage, puis le désactive. La
profondeur de champ cible explicitement l’icing afin de diminuer le bruit visuel du fond et de
guider l’attention.

### Gate Eevee

- ray tracing activé si disponible ;
- Steps augmenté vers 16 ;
- samples viewport/render contrôlés ;
- Light Probe Volume baké si les rebonds screen-space sont instables ;
- Jitter activé sur les lumières douces pour le rendu ;
- vérifier les changements d’éclairage pendant un mouvement caméra.

### Gate Cycles

- backend GPU : OptiX/CUDA, HIP, oneAPI ou Metal ;
- `GPU Compute` plutôt que CPU ;
- viewport réduit pendant le lookdev ;
- denoise viewport et rendu test ;
- comparaison objective du temps et de la qualité avec Eevee.

Le tutoriel mesure moins d’une seconde pour Eevee contre 23 secondes pour Cycles sur sa
machine. Ces chiffres ne sont pas transférables ; la méthode correcte consiste à mesurer un
frame représentatif sur la machine locale.

## Application à Blender Studio

Les éléments à transformer en assets ou workflows contrôlés sont :

1. collection de sources pour scatter ;
2. preset Scatter on Surface avec masque typé ;
3. matériau PBR trois maps ;
4. rig `Sun + Sky + Bounce + Blockers` ;
5. caméra produit avec focus object ;
6. gate comparatif Eevee/Cycles ;
7. audit de modifier order, doubles vertices, UV stretching et dépendances textures.

Le tutoriel de caméra DRUMBOII reste la source pour l’animation K1–K4 et le target lag. Ce
cours apporte la construction de la scène, les surfaces, l’éclairage et le rendu statique. Les
deux corpus sont complémentaires.

## Limites et vigilance

- `Scatter on Surface` requiert Blender 5.0+ ;
- Mio3 UV et Poliigon sont des dépendances tierces facultatives ;
- appliquer un modifier exige une version préalable ;
- `Medium High Contrast` est un choix esthétique, pas une règle absolue ;
- les valeurs de lumière, texture, SSS et samples doivent être recalibrées ;
- le tutoriel ne traite pas une véritable animation caméra ;
- les licences des textures doivent être vérifiées avant toute copie dans le repo.

