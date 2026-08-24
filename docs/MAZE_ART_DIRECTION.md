# Direction artistique du labyrinthe

Style cartoon lisible pour la map 16x16. Ce document couvre le parti pris, la
façon dont il est produit et ce qui reste à faire. Le protocole de test jouable
est dans [MAZE_PLAYTEST.md](MAZE_PLAYTEST.md) ; les règles d'autorité réseau dans
[l'ADR 0004](adr/0004-authoritative-topology-and-ticks.md).

## Où vivent les choses

| Élément | Chemin | Versionné |
|---|---|---|
| Générateur | `tools/maze-3d/build_maze_cartoon.py` | Git |
| Export runtime | `Assets/_Project/Maze/Maze16x16.fbx` | Git LFS |
| Topologie typée | `Assets/_Project/Maze/MazeGrid16x16.json` | Git |
| Master Blender | `tools/blender-agent-studio/local_work/maze-cartoon-v001/maze_cartoon.blend` | **non** — coffre DVC en attente |
| Rendus de contrôle | `local_work/maze-cartoon-v001/renders/` | **non** |
| Contrat studio | `tools/blender-agent-studio/projects/team/maze-cartoon-v001/` | Git |

**Un seul script produit la grille et la géométrie.** C'est le point structurant.
Tant que les deux sortaient d'outils séparés — et que le générateur cité par le
registre n'existait dans aucun dépôt joignable — un mur déclaré par le JSON
pouvait manquer du FBX sans que rien ne le signale. La grille est tirée d'abord,
la géométrie en découle, et Unity le vérifie en découpant autant de murs mobiles
que le JSON déclare d'arêtes statiques intérieures.

## La règle qui tient tout

**Ce qu'on voit est ce qui arrête.** Elle se décline en deux lignes concrètes :

1. **Sous 1,40 m — la taille du joueur — rien ne dépasse jamais du nu du mur.**
   Tout le relief de pierre est en creux : les blocs affleurent l'épaisseur
   nominale de 0,25 m et ce sont les joints qui rentrent. La boîte de collision
   posée par Unity coïncide donc exactement avec la silhouette.
2. **Au-dessus de 1,40 m, on peut déborder.** Le joueur ne peut pas s'y cogner,
   donc torches, chaînages de bois, corniches débordantes, crénelage et
   végétation vivent là. C'est ce qui donne quelque chose à regarder sans mentir
   sur un passage.

Trois conséquences assumées, héritées de la map précédente :

- **il n'y a pas de groupe `Props`** — aucun objet au sol dans un couloir, qui
  est libre sur ses 2,50 m ;
- **la végétation ne descend jamais dans un passage** — dessus de murs, lierre
  plaqué au nu, ou hors du labyrinthe ;
- **plus rien ne gêne dans un couloir**, donc un blocage inexpliqué est un vrai
  défaut, pas un gravat.

## Comment le style est produit

Aucune texture. Tout tient dans la géométrie et la couleur.

### Peinture par couleur de sommet

Chaque pierre, chaque feuille et chaque face porte sa propre teinte, écrite dans
un attribut de couleur `Col`. Un seul matériau par famille de surface — pierre,
feuillage, sol, ferronnerie — en porte des centaines.

C'est le point qui décide de l'aspect. **Une couleur plate par matériau donne une
surface en plastique quelle que soit la finesse du maillage** ; aucune quantité
de polygones ne rachète ça. Et comme la variation ne passe plus par des
matériaux séparés, elle ne multiplie pas les sous-maillages : plus de richesse
pour moins d'appels de rendu, au lieu de l'inverse.

### Ombrage cuit dans la couleur

Deux termes sont multipliés dans la teinte de chaque face à la génération :

- **orientation** — un dessus reçoit le ciel et s'éclaircit, un dessous ne reçoit
  rien et s'éteint ;
- **occlusion de hauteur** — le bas d'un mur est assombri par le sol, sur les
  1,3 premiers mètres.

Une seule lumière directionnelle laisse un aplat sur une face verticale. Peindre
ces deux faits donne le volume que le rendu ne fournit pas.

### Appareillage irrégulier

Cinq assises par mur, à hauteurs et découpes tirées au sort, joints croisés d'une
assise à l'autre. Les blocs n'ont pas la même largeur, quelques-uns rentrent d'un
centimètre, il en manque parfois un — un mur bâti puis vécu, pas un mur imprimé.
Blocs de rive en teinte de chaîne d'angle, verdissement progressif en pied.

**Chaque bloc a un biseau de 5 cm.** C'est ce liseré qui fait vivre une face
verticale ; à 2 cm il ne se voyait pas et le mur restait un aplat.

### Masses, pas cônes

Feuillages, buissons, rochers et flammes sont des sphères basse résolution dont
chaque sommet est déplacé au hasard. Un cône empilé se reconnaît immédiatement
comme un asset générique.

## Palette

| Famille | Teintes | Rôle |
|---|---|---|
| Pierre | 6 tons sable chauds, écart de valeur, teinte resserrée | corps des murs |
| Chaîne d'angle | sable soutenu | blocs de rive |
| Noyau | brun très sombre | fond des joints et des niches |
| Corniches | cuivre patiné, ardoise, terre cuite, olive | **une par quadrant** |
| Pivot | orangés, totem bleu nuit, couronnement doré | ce qui bouge |
| Bannière | rouge, bleu, ocre | niches et fanions d'entrée |
| Sol | 3 pavés, 3 herbes | dallage à joints creusés |
| Feuillage | 4 verts | lierre, buissons, arbres |

Les **quatre couleurs de corniche par quadrant** ne sont pas décoratives : elles
disent au joueur dans quel coin du labyrinthe il se trouve, d'un coup d'œil vers
le haut. C'est le seul repère d'orientation que la map offre au sol.

Les teintes sont écrites plus saturées que le rendu final : l'ombrage cuit
multiplie tout vers le bas, et une palette réglée « à l'œil juste » sort en
pastel poussiéreux.

## Repères et points de fuite

- **Crénelage** sur tout le pourtour, à plus de 3 m ;
- **quatre tours** hors emprise, toit rouge, visibles par-dessus les murs ;
- **portails d'entrée** à montants, poutre et fanion ;
- **socle du trésor** à deux degrés surmonté d'une balise ;
- **forêt et rochers** au-delà du pourtour.

Tout cela est hors du labyrinthe fermé, donc inatteignable et sans collider.

## Cotes, invariants et contrat FBX

Le générateur ne peut pas s'en écarter sans casser le code réseau.

- pas de grille **2,75 m** = couloir 2,50 m + mur 0,25 m ;
- mur **3,00 m** de haut, emprise **44 x 44 m** centrée sur l'origine ;
- **4 entrées** sur la rangée `y = 0`, côté +Z Unity ; trésor côté -Z ;
- **17 pivots**, chacun un objet distinct dont l'origine est sur son nœud ;
- murs statiques dans un **unique maillage fusionné** `Murs_Statiques` ;
- objets à collider : `Pivot_*`, `Sol_Dalles`, `Sol_Sable`, `Reperes_Gameplay` ;
- `Vegetation` et `Decor_Lointain` sans collider.

Export `axis_forward=-Z`, `axis_up=Y`, `bake_space_transform=True`,
`apply_unit_scale=True`, échelle 1. **Racine et enfants arrivent à l'identité et
à l'échelle 1**, mesuré à l'import — contrairement aux exports précédents, qui
portaient `-90°` en x et une échelle 100 sur chaque nœud et avaient fini par
coucher les bras de pivot au démarrage (correctif `d55a1cd`). Les deux FBX du
personnage sont encore dans l'ancienne convention.

## Régénérer

```bash
W=tools/blender-agent-studio/local_work/maze-cartoon-v001
/Applications/Blender.app/Contents/MacOS/Blender --factory-startup --background \
  --python tools/maze-3d/build_maze_cartoon.py -- \
  --seed 20260805 \
  --out-json "$W/MazeGrid16x16.json" --out-fbx "$W/Maze16x16.fbx" \
  --out-blend "$W/maze_cartoon.blend" --render-dir "$W/renders"
```

La topologie seule, sans Blender, pour un test rapide :

```bash
python3 tools/maze-3d/build_maze_cartoon.py --topology-only --seed 20260805 --out-json /tmp/grid.json
```

Le `.blend` est **régénéré à chaque exécution**. Ne pas l'éditer à la main : les
réglages sont en tête du script — palette, hauteur de chaperon, densité de
végétation, probabilité des torches, seed du tracé.

Quatre rendus de contrôle sortent dans `--render-dir` : aérien, entrée, pivot et
couloir cadré sur une torche.

## État au 6 août 2026

Tracé courant, seed `20260805` : **155 murs mobiles**, 46 arêtes de bras,
106 arêtes interdites, 17 pivots (12 T, 2 L, 3 I), 256 cellules sur 256
atteignables, trésor à 31 pas.

| | Valeur |
|---|---|
| Triangles | 310 674 |
| Matériaux | 4 |
| Textures | 0 |
| FBX studio courant | 5 491 516 o — `0ab1dc2e…` |
| FBX dans le dépôt | 1 972 924 o — `b1e9859d…` |

### Ce qui reste à faire

1. **Unity n'affiche pas encore les couleurs de sommet.** URP Lit ne les lit pas.
   Il faut un shader qui multiplie la couleur de base par `COLOR`, et
   `MazePlaytestBuild` doit assigner ce matériau au lieu de consommer ceux du
   FBX. **Sans ça la map arrive grise dans le jeu** : c'est le blocage principal.
2. **L'export du dépôt est en retard sur le générateur** — il date de la passe
   « matériau par teinte », avant la peinture par sommet. Les deux empreintes
   ci-dessus le montrent. À resynchroniser en même temps que le point 1.
3. **Performance non mesurée en contexte.** `Murs_Statiques` est redécoupé en
   ~233 objets ; l'ordre de grandeur est le millier d'appels de rendu avant
   batching. Budget triangles tenu, performance réelle inconnue.
4. **macOS seulement, un seul joueur.** Windows IL2CPP et une session à
   plusieurs restent à faire.
5. **Le master `.blend` n'est sur aucun coffre.** Gate DVC toujours P0.

## Historique des passes

Trois versions ont été produites et deux refusées. La trace est utile : elle dit
pourquoi le style est ce qu'il est.

1. **Aplats nus** — 29 826 triangles, murs sans relief. Refusée : « bas de
   gamme ». La collision honnête avait été confondue avec l'absence de décor,
   alors que du relief en creux ne ment sur rien.
2. **Appareil de pierre à matériau par teinte** — 248 878 triangles, 22
   matériaux. Refusée : encore plat. La géométrie était là, mais une couleur
   unique par matériau plafonne l'aspect quoi qu'on ajoute.
3. **Peinture par couleur de sommet + ombrage cuit** — l'état actuel.

La leçon, si une autre map est produite : **la variation de teinte se règle avant
la densité de polygones**.
