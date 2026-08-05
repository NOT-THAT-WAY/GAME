# Playbook animation Blender — synthèse du corpus priorisé

Ce document transforme les quatre nouvelles vidéos en méthode de production contrôlable dans Blender Studio. Il ne copie pas une scène précise : il sépare les principes réutilisables des choix propres aux lunettes, au convoyeur, à la voiture et aux écouteurs.

## Quelle recette choisir

| Besoin | Recette principale | Mouvement dominant | Risque principal |
|---|---|---|---|
| donner du caractère à un objet | Drumboiii Squishy | scale bounce + Lattice en overlap | identité et détails trop déformés |
| révéler un produit complexe | Hero product assembly reveal | pièces vers pose finale | collisions et origines incohérentes |
| montrer un objet articulé | Hinged case product choreography | charnière + contenu | axe faux et ordre causal illisible |
| créer une boucle mécanique | Seamless conveyor loop | vitesse constante + événements | glissement et jonction visible |
| placer un asset dans un monde | Cinematic asset-in-environment shot | trajet héros + caméra | décor trop dense et échelles incohérentes |

Pour une caméra hero plus organique, combiner ces recettes avec le corpus Drumboiii : anticipation, mouvement principal, recovery, cible `Track To` indépendante et focus gaté. Pour la lumière, sa méthode devient également prioritaire : base HDRI retenue, Sun orienté par le reflet, backlight de forme et glimmers locaux validés un par un.

## 1. Séparer les sources avant de construire

Une image de référence, un asset Blender et un résultat rendu n'ont pas le même statut.

- `REFERENCES`: images, vidéos et dimensions servant à juger l'identité; jamais exportées comme géométrie.
- `SOURCE_ASSET`: collection importée ou liée, conservée intacte et masquée au rendu.
- `WORK_ASSET`: duplication de travail normalisée, seule version autorisée à recevoir corrections et rig.
- `SHOT`: caméra, décor, lumières, contrôles et animation du plan.
- `OUTPUT`: gates, previews, renders et manifeste; dossier unique par job.

Ne jamais corriger silencieusement l'asset source pour satisfaire un plan. Une correction devient soit une version documentée de l'asset, soit un override local au shot.

## 2. Audit obligatoire d'un asset existant

Avant animation, produire un manifeste avec :

1. chemin et hash du `.blend`, `.fbx`, `.glb` ou `.obj`;
2. unités, dimensions monde et orientation avant/haut;
3. nombre d'objets, meshes, matériaux, textures et modifiers;
4. hiérarchie, parents, contraintes, armatures et actions;
5. origines, transforms non appliqués et échelle négative;
6. bounding box globale et centre visuel;
7. pièces potentiellement animables;
8. textures manquantes ou chemins externes;
9. géométrie cachée, doublons, non-manifold et normales suspectes;
10. licence/provenance si l'asset doit sortir du poste local.

Le résultat de l'audit décide de la stratégie : animation directe, duplication de travail, reconstruction d'une pièce, ou rejet temporaire.

## 3. Hiérarchie de contrôle commune

Une structure minimale évite de mélanger animation globale et locale :

```text
USTUDIO_SHOT
├── ASSET_SOURCE       (lecture seule, masqué au rendu)
├── WORK_ASSET
│   ├── PRODUCT_ROOT   (placement et échelle globale)
│   ├── BODY_CTRL      (mouvement secondaire du corps)
│   ├── PARTS          (pièces de reveal)
│   ├── LID_CTRL       (charnière si présente)
│   └── CONTENTS       (objets contenus autonomes)
├── CAMERA_RIG
│   ├── CAMERA_ROOT
│   ├── CAMERA
│   ├── TARGET
│   └── FOCUS
├── ENVIRONMENT
├── LIGHTS
└── FX
```

Règles :

- `PRODUCT_ROOT` ne remplace pas les contrôles locaux;
- un couvercle tourne autour d'une origine mécanique vérifiée;
- les contenus qui doivent voler ne sont pas enfants du couvercle;
- la caméra vise `TARGET`, pas forcément l'origine mathématique du produit;
- `FOCUS` peut rester indépendant de `TARGET`;
- le parenting est finalisé avant les keyframes.

## 4. Bloquer le shot en états, pas en gestes flous

Écrire d'abord les états clés :

- `S0 still`: image de départ lisible;
- `S1 anticipation`: préparation éventuelle;
- `S2 action`: événement principal;
- `S3 impact`: arrivée, ouverture maximale ou point de chute;
- `S4 settle`: recovery court;
- `S5 still`: pose finale stable.

Les keyframes détaillées viennent ensuite. Pour un boîtier : fermé → ouvert → contenu haut → contenu revenu → fermé. Pour un reveal : dispersé → convergence → assemblé. Pour un convoyeur : le système est cyclique; l'état final doit être mathématiquement équivalent au premier.

### Extension Drumboiii : pop Squishy

Pour un objet qui doit apparaître avec du caractère, construire d'abord un pop de Scale
`0 → overshoot → cible → petit rebound`. Ajouter ensuite une Lattice commune comme couche
secondaire : elle commence légèrement avant ou chevauche le pop, traverse le volume puis se
stabilise. Le root garde le mouvement global ; la Lattice ne porte que la déformation.

Sur un asset multi-pièces, affecter la même Lattice à chaque mesh déformable. Exclure contrôles,
lights, caméra et sol. Ajouter la topologie minimale nécessaire, puis Subdivision Surface à la
fin. Les strengths élevées du tutoriel sont recalibrées et les écrans, logos, trims et arêtes
sont gatés aux poses extrêmes.

## 5. Choisir l'interpolation selon la fonction

| Canal | Interpolation de départ | Contrôle attendu |
|---|---|---|
| tapis convoyeur | Linear | vitesse constante |
| produit transporté | Linear pendant contact | aucun glissement |
| chute ou bascule | Bézier réglée | poids et impact |
| couvercle | Bézier réglée | départ/arrivée sans dépassement mécanique |
| pièces de reveal | Bézier par groupes | cascade et absence de collision |
| caméra hero | Bézier | anticipation, travel, recovery |
| hold de validation | Constant ou clés identiques | image réellement stable |

Ne pas convertir toutes les courbes en Bézier par réflexe. L'interpolation exprime une fonction physique ou narrative.

## 6. Caméra : montrer l'action, pas la concurrencer

Quand l'objet effectue déjà un mouvement complexe, la caméra reste simple : push, pan court ou three-quarter stable. Quand l'objet est presque immobile, la caméra peut porter le geste avec un arc, un crane ou le motif Drumboiii en quatre clés.

Checklist caméra :

1. composition de départ et d'arrivée validées en clay;
2. silhouette lisible aux extrêmes;
3. aucun clipping sur décor, produit ou particules;
4. `TARGET` animé vers les zones d'intérêt;
5. focus vérifié à chaque pose hero;
6. motion blur testé sur le détail identitaire le plus petit;
7. vraie pause au début et à la fin si la sortie doit alimenter une IA vidéo.

## 7. Environnement construit pour le plan

Pour un asset dans un décor :

1. bloquer terrain, horizon et route en clay;
2. placer le héros et la caméra avant les détails;
3. réserver un corridor négatif autour de la trajectoire;
4. distribuer végétation et architecture en masses de profondeur;
5. limiter les variations d'espèce, saison et échelle;
6. vérifier que les assets de décor ne croisent ni trajectoire ni champ proche;
7. texturer selon une échelle monde cohérente;
8. ajouter poussière, feuilles ou atmosphère comme passes secondaires.

La densité se juge depuis la caméra finale. Une vue aérienne de travail ne doit pas dicter la quantité de végétation.

## 8. Lookdev, texture et couleur

Ordre recommandé :

1. clay et silhouette;
2. valeurs de gris et séparation sujet/fond;
3. roughness et qualité des reflets;
4. couleur principale;
5. accents matière;
6. FX et variation colorée animée;
7. compositing.

Pour un produit brillant, une grande source définit la forme du reflet, tandis qu'un rim plus dur sépare le contour. Un HDRI fournit un contexte de réflexion, mais ne remplace pas toujours une lumière de dessin. Toute couleur animée doit être testée sur la lisibilité des détails, et pas seulement sur la saturation globale.

### Ordre lumière Drumboiii désormais privilégié

1. séparer le ciel visible de l'environnement d'éclairage avec `Is Camera Ray` ;
2. construire si nécessaire le ciel caméra avec Noise/ColorRamp + Gradient/ColorRamp ;
3. régler l'échelle du Noise selon la focale et le cadrage finaux ;
4. retenir l'HDRI vers `0,5–0,7` pour garder du headroom ;
5. orienter un Sun oblique jusqu'à ce que ses reflets décrivent la géométrie ;
6. ajouter un Area arrière dominant qui redonne volume et contour ;
7. ajouter des Areas latéraux faibles uniquement pour des détails nommés ;
8. rendre un A/B cumulatif après chaque couche ;
9. refaire ce gate à chaque pose caméra hero.

Les watts `1400 / 440 / 170 / 220` observés dans la scène source sont convertis en rapports
et adaptés aux bounds de l'asset. Ils ne sont jamais traités comme valeurs universelles.

## 9. Gates professionnels

Chaque workflow doit produire un dossier unique avec manifeste et au minimum :

- `gate_00_source.png`: asset avant modification;
- `gate_01_blockout.png`: composition clay;
- `gate_02_action_start.png`;
- `gate_03_action_peak.png`;
- `gate_04_impact.png`;
- `gate_05_final.png`;
- `contact-sheet.jpg`;
- `manifest.json` avec scène, caméra, fps, frames, paramètres et chemins sources.

Tests par famille :

- reveal : trajectoires et collisions de chaque pièce;
- charnière : axe, contact et ordre ouverture/contenu/fermeture;
- boucle : comparaison pixel et transforms entre jonction fin/début;
- environnement : corridor, collisions, échelle des textures, densité et silhouette;
- caméra : cadrage, focus, vitesse angulaire et motion blur.

## 10. Workflows contrôlés à ajouter à Blender Studio

### `asset-audit`

Lecture seule. Produit inventaire, bounding box, transforms, dépendances, actions et images de diagnostic.

### `product-assembly-reveal`

Écriture non sauvegardée. Paramètres bornés : collection, groupes de pièces, durée, dispersion, ordre, seed, anticipation, settle. Le workflow refuse les pièces sans origine documentée et ne sauvegarde jamais le `.blend`.

### `hinged-product-choreo`

Écriture non sauvegardée. Paramètres : body, lid, contents, axe local, angle maximal, timings. Avant génération, il rend une gate mécanique de l'axe.

### `conveyor-loop`

Écriture non sauvegardée. Paramètres : curve, link, count, axis, duration, transported collection, cadence. Il calcule le pas depuis la géométrie au lieu d'accepter une distance libre.

### `asset-environment-shot`

Workflow composé : audit → duplication de travail → blockout → corridor → caméra → scatter contrôlé → gates. Les assets de décor sont sélectionnés dans l'Asset Library, jamais depuis un chemin arbitraire saisi dans l'interface.

### `shot-quality-gate`

Lecture/rendu. Produit les six gates, un contact sheet et des diagnostics : clipping, objets absents, textures manquantes, transforms extrêmes et état sauvegardé/non sauvegardé.

## 11. Usage sûr avec MCP et IA

L'IA ne doit pas recevoir « fais une animation pro » comme instruction unique. Elle doit recevoir :

```text
Inspecte la scène sans la modifier.
Utilise la collection <nom> comme WORK_ASSET.
Prépare la recette <nom> sur <durée> secondes à <fps>.
Ne sauvegarde pas le .blend.
Ne crée que des objets préfixés ustudio_.
Rends les gates <liste> dans un nouveau dossier de job.
Retourne les diagnostics et attends validation avant toute sauvegarde.
```

La réponse attendue n'est pas seulement une vidéo : elle contient paramètres, objets créés, actions, gates, avertissements et chemin de sortie.

## 12. Provenance des règles

- reveal et séparation des pièces : `ray-ban-product-animation/analysis.json`;
- boucle Array/Curve et vitesse linéaire : `factory-animation-polygon-runway/analysis.json`;
- environnement automobile : `quick-animation-blender-4/analysis.json` — preuve visuelle, valeurs exactes non confirmées;
- charnière, parenting et cascade : `wireless-pods-animation-polygon-runway/analysis.json`;
- caméra anticipation/recovery/target/focus : `drumboii-camera-tutorial-2026-07-18/analysis.json`;
- lumière par couches/reflets et gate A/B : `drumboii-lighting-tutorial-2026-07-20/analysis.json`;
- HDRI/ciel procédural et Squishy/Lattice : `drumboii-hdri-squishy-2026-07-21/analysis.json`;
- asset, matériaux, UV, scatter et lighting : `beginner-blender-tutorial-2026/analysis.json`.

Ce playbook est la base de conception des futurs catalogues JSON et scripts MCP. Chaque automatisation devra conserver ses hypothèses comme paramètres visibles plutôt que les cacher dans le code.
