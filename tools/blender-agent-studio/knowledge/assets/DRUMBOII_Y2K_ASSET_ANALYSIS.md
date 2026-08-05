# Assets DRUMBOII Y2K — audit et guide d’usage

## Résultat de l’ingestion

Les six FBX originaux ont été copiés sans modification dans:

```text
asset_sources/drumboii-y2k/fbx/
```

Ils ont été importés dans Blender 5.1.1 et regroupés en six collections marquées comme assets:

```text
asset_library/imported/drumboii-y2k-assets.blend
```

Le manifeste machine complet se trouve dans `asset_sources/drumboii-y2k/audit.json`.

## Inventaire

| Asset | Objets | Vertices | Polygones | Usage conseillé |
|---|---:|---:|---:|---|
| Blob Speaker | 1 | 12 230 | 12 224 | hero simple, dolly court |
| Blob Bike | 20 | 59 295 | 58 992 | hero dynamique, plan bas |
| Cone | 1 | 5 545 | 5 466 | prop, repère d’échelle |
| Flip Phone | 24 | 85 130 | 80 910 | macro clavier/charnière |
| Gameboii | 24 | 80 624 | 79 727 | hero rétro, transferts d’attention |
| Traffic Light | 24 | 46 388 | 43 395 | scène urbaine, target animé |

Total: **289 212 vertices** et **280 714 polygones**.

## Matériaux et couleurs

Le pack est autonome: aucun asset n’utilise de texture image externe. Les 43 matériaux sont
des Principled BSDF simples avec couleurs et couples metallic/roughness. Cela les rend faciles
à recolorer et sûrs à déplacer entre machines, mais les détails de surface reposent uniquement
sur la géométrie et les valeurs shader.

Palette dominante:

- bleus électriques et bleu cyan;
- rose/magenta;
- violet;
- accents vert, rouge et orange;
- métaux très brillants, souvent `metallic ≈ 0.97` et `roughness ≈ 0.08`;
- coques colorées souvent assez spéculaires et peu rugueuses.

Avant un rendu photoréaliste, vérifier l’énergie des matériaux: certaines coques ont un
metallic élevé qui relève davantage d’un look Y2K stylisé que d’un plastique physique.

## Structure et risques

- Blob Speaker et Blob Bike conservent des transforms FBX non unitaires.
- Les cinq modèles DRUMBOII complexes possèdent une racine parentant leurs pièces; préserver
  cette hiérarchie pour déplacer/instancier l’asset.
- Bike, Flip Phone et Gameboii dépassent environ 50k polygones: adaptés aux plans hero, mais à
  optimiser ou instancier pour une foule d’objets.
- Aucun modifier n’est conservé: la géométrie importée est déjà évaluée/bakée.
- Les écrans du Flip Phone et du Gameboii sont noirs et brillants, sans contenu image.
- Les pivots importés n’ont pas été réécrits afin de préserver l’intention et la hiérarchie FBX.

## Import dans une scène

Dans l’Asset Browser, catalogue `Props/DRUMBOII Y2K`:

- **Append (Reuse Data)** pour des shots locaux et plusieurs occurrences;
- **Link** pour centraliser les mises à jour;
- ne créer un Library Override que si une animation locale de la hiérarchie est nécessaire.

Après import:

1. déplacer la collection via son objet racine;
2. vérifier l’échelle par rapport au décor;
3. ne pas appliquer les transforms d’une hiérarchie complexe sans copie de sécurité;
4. assigner un rig caméra et un target Empty;
5. rendre un gate silhouette/matériaux avant le look final.

## Correspondance avec le tutoriel caméra

La méthode Drumboiii convient aux assets qui ont plusieurs zones d’intérêt. Le target Empty
peut être animé indépendamment de la caméra:

- Gameboii: écran, D-pad, boutons A/B;
- Flip Phone: écran, charnière, clavier;
- Traffic Light: feux avant puis module latéral;
- Bike: phare/carénage puis guidon et roue;
- Speaker: contrôles supérieurs puis silhouette complète.

Utiliser la règle des quatre clés pour le déplacement caméra, puis décaler légèrement le
target pour un suivi plus humain. Le Cone est volontairement plus simple et sert bien de
contrôle de timing, de couleur ou d’échelle.
