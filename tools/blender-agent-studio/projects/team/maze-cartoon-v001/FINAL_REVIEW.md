# Revue finale — maze-cartoon-v001

## Verdict

**Livré pour revue humaine, avec un blocage d'intégration ouvert.** Le labyrinthe
16x16 de GAME est refait en style cartoon, contrat de grille conservé, et
remplace l'export désert précédent (`ART-MAZE-001`). La géométrie et la
topologie sont validées ; **le style ne passe pas encore dans Unity**, faute d'un
shader lisant les couleurs de sommet.

La direction artistique complète est documentée dans
[`docs/MAZE_ART_DIRECTION.md`](../../../../../docs/MAZE_ART_DIRECTION.md).

## Résultat par rapport au brief

Les invariants d'identité demandés sont tenus, et supprimés à la source plutôt
que masqués :

- **aucun objet au sol dans un couloir** — il n'y a plus de groupe `Props` ;
- **la végétation ne descend jamais dans un couloir** — dessus de murs, lierre
  plaqué au nu du mur, ou hors emprise ;
- **rien ne dépasse sous 1,40 m**, la taille du joueur : tout le relief de pierre
  est en creux, donc la boîte de collision coïncide avec la silhouette. Au-dessus
  de cette ligne le décor peut déborder sans qu'on puisse s'y cogner.

Le point structurant du paquet : **la topologie et la géométrie sortent du même
script**. L'ancienne map ne le permettait pas — la grille venait d'un dépôt de
préproduction, le FBX d'un autre outil, et le `tools/maze-3d/build_maze.py` cité
par le registre n'existait dans aucun dépôt joignable. Un mur déclaré par le JSON
pouvait donc manquer du FBX sans que rien ne le signale. Ici la grille est tirée
d'abord et la géométrie en découle ; Unity le vérifie en découpant 155 murs pour
155 arêtes statiques intérieures, sans avertissement.

## Preuves techniques, physiques et visuelles

Géométrie et échelle, mesurées à l'import et non déclarées :

- pas de grille 2,75 m, couloir 2,50 m, mur 0,25 x 3,00 m ;
- `Murs_Statiques` à 44,43 x 3,00 x 44,43 m — les 0,43 m au-delà de l'emprise de
  44 m sont le débord de chaperon, pas une dérive d'échelle ;
- `Pivot_01_15_I` en `(19.25, 0, -19.25)`, exactement son nœud de grille ;
- racine et 22 enfants importés **à l'identité et à l'échelle 1** ;
- 4 apparitions validées : sol présent, aucun collider, dégagement 2,75 m ;
- 256 cellules sur 256 atteignables, trésor à 31 pas.

Export FBX `axis_forward=-Z`, `axis_up=Y`, `bake_space_transform=True`,
`apply_unit_scale=True`, échelle globale 1. C'est un changement de fond : les
exports précédents portaient la conversion d'axes de Blender sur chaque nœud,
`-90°` en x et échelle 100. Cette convention avait une conséquence réelle, elle a
couché les 17 bras de pivot au démarrage jusqu'au correctif `d55a1cd`. Les deux
FBX du personnage sont encore dans l'ancienne convention.

Visuel : aucune texture. Le style tient dans deux mécanismes — **peinture par
couleur de sommet** (chaque pierre, chaque feuille sa teinte, un seul matériau
par famille de surface) et **ombrage cuit dans la couleur** (orientation de face
et occlusion de hauteur). S'y ajoutent un appareil de pierre irrégulier à biseaux
de 5 cm, des accessoires au-dessus de la ligne de 1,40 m, et des repères hors
emprise : crénelage, quatre tours, forêt.

Budgets : 310 674 triangles, **4 matériaux**, 0 texture. L'export pèse 5,2 Mio
contre 37,5 Mo à l'origine.

## Limites et décision humaine

Ce qui n'est **pas** prouvé, et qu'il ne faut pas déduire de ce verdict :

1. **Le style ne passe pas encore dans Unity.** URP Lit ne lit pas les couleurs
   de sommet. Il faut un shader qui multiplie la couleur de base par `COLOR`, et
   `MazePlaytestBuild` doit assigner ce matériau au lieu de consommer ceux du
   FBX. Sans ça, la map arrive grise dans le jeu. **C'est le blocage principal.**
2. **L'export du dépôt est en retard sur le générateur.** Celui d'
   `Assets/_Project/Maze/` date de la passe « matériau par teinte »
   (`b1e9859d…`, 1 972 924 o) ; l'export courant du studio est `0ab1dc2e…`
   (5 491 516 o). À resynchroniser avec le point 1.
3. **macOS uniquement.** Windows x86_64 IL2CPP n'a été ni construit ni lancé.
4. **Un seul joueur.** Rien de vérifié à plusieurs ni en arrivée tardive.
5. **Performance non mesurée en contexte.** `Murs_Statiques` est redécoupé en
   ~233 objets ; l'ordre de grandeur est le millier d'appels de rendu avant
   batching. Budget triangles tenu, performance réelle inconnue.
6. **Nouveau tracé.** Les repères appris sur l'ancienne map ne valent plus.
7. **Le master `.blend` n'est sur aucun coffre.** Il ne vit que sur la machine de
   Sean. La gate DVC reste P0.

Décision qui revient à l'équipe : valider ce tracé et cette palette avant que du
level design, de l'audio ou du réglage réseau ne s'y accroche.

## Historique des passes

Deux versions ont été refusées avant celle-ci. La trace explique le style actuel.

1. **Aplats nus** — 29 826 triangles, murs sans relief. Refusée : « bas de
   gamme ». La collision honnête avait été confondue avec l'absence de décor.
2. **Appareil de pierre à matériau par teinte** — 248 878 triangles, 22
   matériaux. Refusée : encore plat. Une couleur unique par matériau plafonne
   l'aspect quoi qu'on ajoute en géométrie.
3. **Peinture par couleur de sommet et ombrage cuit** — l'état actuel.

Leçon transférable : **la variation de teinte se règle avant la densité de
polygones.**
