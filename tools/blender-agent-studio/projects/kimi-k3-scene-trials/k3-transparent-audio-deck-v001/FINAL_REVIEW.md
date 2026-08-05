# Revue finale — k3-transparent-audio-deck-v001

## Verdict

`revise` — **84,4/100**, sans échec critique physique.

Le MVP Blender est exploitable : il livre une reconstruction procédurale distincte, un `.blend`,
un `.glb`, une hiérarchie explodable, des matériaux Principled, des sockets, un collider, quatre
vues de contrôle et une preview de huit secondes. Il ne doit toutefois pas être présenté comme
une reproduction produit exacte. Une seule vue transparente ne permet pas de déterminer le dos,
la profondeur des cavités ni la connectivité mécanique interne.

## Ce qui est validé

- La génération s’exécute dans Blender 5.1.1 avec `--background --factory-startup`; aucun `.blend`
  source n’a été ouvert ni écrasé.
- Le spec `img2threejs` passe sa validation stricte sans erreur ni avertissement : 22 composants
  sémantiques, 13 matériaux et 6 systèmes de répétition.
- Le gate blockout a été accepté après comparaison du rendu clay; le test multi-angle ne détecte
  aucune vue dégénérée ou plane.
- La scène contient 72 meshes visuels Blender dans une hiérarchie préfixée. Le GLB réimporté
  contient 77 meshes, 6 empties et 15 matériaux, sans caméra ni lumière exportée.
- Le mesh évalué touche le support à `z=0` : pénétration `0 m`, gap `0 m`. L’objet reste statique;
  seule la caméra bouge. La clearance caméra minimale est `0,418083 m` à la frame 76, avec zéro
  frame hors seuil.
- La preview H.264 mesure exactement 8,000 s, 576×720, 24 fps et 192 frames.

## Gate amont encore bloquant

Le `structural-pass` d’`img2threejs` reste volontairement bloqué. Son diagnostic Tier‑1 mesure un
IoU de silhouette de `0,5901` pour un seuil verrouillé à `0,85`, ainsi qu’un delta de ratio de
`0,058` pour un maximum de `0,05`. Le seuil n’a pas été élargi après l’échec. La référence combine
une coque transparente, un fond non uniforme, une pose flottante et une grande ombre détachée;
son masque déterministe n’est donc pas une mesure pure de géométrie. Une caméra diagnostic a été
alignée, mais cela ne suffit pas à faire passer le gate. Il faut de nouvelles vues orthographiques
ou un masque de silhouette propre avant de déclarer le pipeline amont terminé.

## Direction, lumière et itérations

La production respecte la priorité physique : le prop est posé et l’arc caméra remplace la
lévitation de la référence. Le mouvement suit anticipation, travel, overshoot et recovery.
L’éclairage utilise le monde, un Sun de reflet, un backlight de forme, deux glimmers locaux et un
detail return. Trois corrections bornées de la catégorie lumière/transparence ont réduit la
saturation jusqu’à restaurer les diaphragmes noirs; la preuve A/B complète comporte six rendus.
La caméra de preuve multi-angle a été séparée de l’action animée, puis une caméra de comparaison
référence a été ajoutée sans servir de preuve physique.

## Défauts restants

Le dos est une continuité conservatrice, non une reconstruction observée. Les rainures moulées,
les fixations internes et la mécanique du transport sont simplifiées. Le polycarbonate EEVEE est
une approximation alpha/transmission et non une mesure optique. Le texte `AUDIO // 01` est un
marquage générique afin de ne pas inventer la marque illisible de la référence. La pose finale
diffère de l’image flottante pour conserver un support réel et vérifiable.

## Suite recommandée

Conserver ce fichier comme prototype de bridge et asset de look-dev. Pour passer à `ship`, fournir
au minimum une face, un profil, un dos et une vue supérieure sans ombre confondue avec la
silhouette; recalibrer ensuite la caméra, les épaisseurs de coque et les détails cachés, puis
relancer le `structural-pass` sans modifier ses seuils.
