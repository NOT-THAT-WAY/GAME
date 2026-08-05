# Règles d'évaluation des essais de scènes Blender

## But

Ce document définit ce qui **va**, ce qui **ne va pas** et ce qui constitue une preuve valable
pour tous les essais de scènes du dépôt. Il s'applique au film, au `.blend`, aux diagnostics et au
score. Un validateur de package ne remplace jamais cette revue.

## Les trois verdicts à ne pas confondre

1. **Package valide** : les fichiers attendus existent, les JSON sont cohérents et la vidéo a le
   bon format. Cela ne prouve ni la physique ni la qualité du film.
2. **Preuves valides** : les mesures portent sur la géométrie réellement rendue, dans le bon repère,
   sur toute la plage temporelle. Cela ne prouve pas encore que le film est intéressant.
3. **Film validé** : les preuves P0 passent et la mise en scène atteint le seuil artistique.

`package_valid: true` signifie uniquement le premier niveau. Il est interdit de le présenter comme
un verdict artistique ou physique.

## Ordre du jugement

Évaluer dans cet ordre, sans permettre à une couche inférieure de compenser une couche supérieure :

1. source intacte et identité canonique ;
2. physique, support, contacts, collisions et affordances ;
3. causalité et continuité du récit ;
4. mouvement du sujet et rythme ;
5. composition, caméra et lisibilité ;
6. lumière, matières, couleur et typographie ;
7. polish et intégrité de la vidéo.

Une belle lumière ne répare pas un pied sous le sol. Une caméra spectaculaire ne transforme pas une
pose accroupie en assise. Une pénétration invisible depuis la caméra hero reste une pénétration.

## Standard minimal des preuves physiques

### Géométrie mesurée

- Mesurer les **meshes évalués** après armature, constraints, modifiers, parenting et transforms.
- Ne pas valider un corps avec seulement la tête ou la queue d'un os, un Empty ou le root du rig.
- Mesurer le sujet visible, ses semelles ou zones de contact, et la géométrie réelle du support.
- Un plan mathématique codé en dur n'est recevable que s'il est dérivé du mesh et recroisé avec lui.
- Déclarer les paires sémantiques : pied/sol, bassin/rim, main/support, corps/décor, caméra/décor.

### Repères

- Employer un seul repère déclaré pour chaque calcul.
- Si un parent tel que `FLOAT_ROOT` bouge, recalculer sa matrice inverse à **chaque frame**.
- Ne jamais mesurer en coordonnées monde puis réutiliser ces valeurs comme coordonnées locales.
- Conserver dans le diagnostic le nom du repère, sa source et la méthode de transformation.

### Échantillonnage

- Évaluer toutes les frames (`sample_frame_step = 1`) pour un verdict final autonome.
- Les poses hero servent à la lecture visuelle, pas à remplacer l'audit frame par frame.
- Rapporter la pire valeur, la frame correspondante et le nombre de frames hors seuil.
- Utiliser au minimum distance signée ou nearest-surface **et** recouvrement BVH/triangles pour les
  solides qui peuvent se traverser.

### Contact et support

- `pénétration = 0` ne prouve pas un contact : un personnage à 9 cm du sol ne collisionne pas, mais
  il lévite.
- Un contact planté doit prouver simultanément : faible distance au support, absence de pénétration
  excessive et faible drift tangentiel.
- Une assise doit montrer et mesurer le support du bassin ou des cuisses ; une silhouette proche du
  bord ne suffit pas.
- Une lévitation n'est valide que si sa cause est visible et établie avant la perte de support.
- Distinguer un contact voulu d'une collision : les mains peuvent toucher un bord, le genou ne peut
  pas le traverser.

## Seuils autonomes par défaut

Les seuils sont verrouillés dans `scene-contract.json` **avant** l'animation :

| Mesure | Seuil par défaut |
|---|---:|
| pénétration maximale dans le décor | `0,002 m` |
| écart maximal d'un appui déclaré planté | `0,005 m` |
| drift maximal d'un appui planté | `0,005 m` |
| clearance minimale d'un membre en swing | `0,010 m` |
| clearance minimale caméra/décor | `0,080 m` |
| échantillonnage final | chaque frame |

Un seuil plus strict est permis. Un seuil plus permissif exige une justification d'échelle dans le
contrat et une approbation humaine antérieure à l'animation ; sans cette approbation, l'essai ne peut
pas recevoir `ship`. Il est interdit d'élargir un seuil après avoir découvert une collision.

## Échecs critiques

Les cas suivants imposent `reject` et plafonnent la note finale à 49 :

- collision ou traversée involontaire du décor ;
- support absent, lévitation ou assise sans contact alors que l'histoire exige un appui ;
- articulation impossible ou affordance humaine incorrecte ;
- drift ou glissement sans cause pendant un contact planté ;
- identité canonique ou proportions contractuelles cassées ;
- caméra ou géométrie qui clippe ;
- frame noire, corrompue, manquante ou glitchée.

Le score artistique brut peut être conservé pour comparer les idées, mais le score officiel reste
plafonné. Exemple : `75 brut → 49 officiel, reject`.

## Ce qui va

- Une histoire lisible comme une chaîne : état → cause → action → conséquence → repos.
- Une pose dont la fonction est immédiatement compréhensible en silhouette.
- Un mouvement qui respecte les dimensions et les capacités réelles du personnage ou de l'objet.
- Une idée visuelle causale : un pas allume une note, une playhead provoque une réaction, une lumière
  révèle réellement le sujet.
- Un reveal progressif qui conserve le sujet lisible et réserve une respiration finale mesurée.
- Une caméra avec anticipation, travel et recovery, sans drift décoratif permanent.
- Une lumière par fonctions nommées : séparation, volume, accent, information.
- Un rapport qui déclare lui-même un défaut critique au lieu de le cacher.

## Ce qui ne va pas

- Déclarer `ship` parce que Blender, Python ou le validateur de package n'a pas renvoyé d'erreur.
- Mesurer des os de contrôle à la place du mesh déformé.
- Mélanger espace monde et espace local ou figer la matrice d'un parent animé.
- Coder un plan approximatif sans le recroiser contre le support réel.
- Augmenter une tolérance pour faire passer après coup une pénétration observée.
- Présenter l'absence d'intersection comme preuve de support.
- Utiliser une plongée, le motion blur, le noir ou un cadre serré pour cacher un mauvais contact.
- Résoudre le plan large trop tôt puis conserver plusieurs secondes sans nouvelle information.
- Laisser lumière et caméra porter seules l'intention quand la pose du personnage ne la raconte pas.
- Écrire « zéro défaut » sans limites, pires frames et vues de contrôle.

## Leçons du comparatif « Réveil du Bord »

| Cas observé | Ce qui était bon | Ce qui invalide le résultat | Règle retenue |
|---|---|---|---|
| métriques propres, personnage visuellement flottant | package complet, idée de playhead | corps à environ 9 cm du sol et assise à environ 17,5 cm du bord ; mauvais repère de mesure | mesurer mesh évalué + support réel + matrice animée par frame |
| meilleur éclairage, mouvement apparemment propre | composition et palette fortes | pénétration d'environ 7 mm et tolérance élargie à 25 mm après coup | seuil contractuel immuable ; le polish ne compense pas P0 |
| meilleure histoire, rapport honnête | assise lisible, notes déclenchées par les pas, reveal progressif | genou/corps dans la pente d'environ 30 mm | conserver l'idée, rejeter la version et redessiner le trajet |

## Classement comparatif

Pour comparer plusieurs agents, publier les deux notes :

- **brute** : valeur narrative et visuelle avant plafond ;
- **officielle** : note après application des échecs critiques.

Puis nommer séparément : meilleure histoire, meilleure image, meilleure rigueur de preuve. Cette
séparation empêche un rendu séduisant de gagner grâce à une physique fausse et valorise un agent qui
déclare honnêtement son propre échec.

## Contenu obligatoire de `physical-validation.json` v2

- méthode de mesure et géométrie évaluée ;
- repère et gestion des parents animés ;
- frame de début, frame de fin et pas d'échantillonnage ;
- seuils verrouillés ;
- checks applicables avec valeur, seuil, pire frame et nombre de frames hors seuil ;
- paires de collision/contact et classification sémantique ;
- vues de preuve ;
- limites connues ;
- `passed` cohérent avec les checks et liste des échecs critiques.

Le template est `workflows/templates/kimi-scene-trial/physical-validation.template.json`.
