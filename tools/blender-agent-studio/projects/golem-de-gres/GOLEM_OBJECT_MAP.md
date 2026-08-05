# Golem de grès — cartographie de l'objet

Personnage reconstruit depuis `~/Downloads/golem-de-gres-turnaround.png`.
Unités : **1 BU = 1 m**. Hauteur cible **1,00 m**, semelles à `z = 0`.

| | |
|---|---|
| Scène | `projects/golem-de-gres/scene/golem.blend` |
| Calque (source des formes) | `projects/golem-de-gres/golem-trace.json` |
| Extracteur | `workflows/tools/trace_golem_reference.py` |
| Constructeur | `workflows/scripts/build_golem_de_gres.py` |
| Gate de conformité | `workflows/tools/gate_golem_silhouette.py` |
| Collection | `K3_GOLEMGRES_ASSET` |
| Blender | 5.1.1, via BlenderMCP sur `127.0.0.1:9876` |

## Chaîne de production

```text
planche 360°  →  trace_golem_reference.py  →  golem-trace.json
                                                   ↓
                        build_golem_de_gres.py  →  scène Blender
                                                   ↓
                     gate_golem_silhouette.py  →  écart mesuré vs planche
```

Aucune silhouette n'est saisie à la main dans le constructeur : il consomme le
calque. Relancer l'extracteur suffit à répercuter un changement de référence.

## Repère et orientation

- `+X` = droite du spectateur en vue de face ; le bras à `x > 0` est `ARM_R`.
- `−Y` = **avant** du personnage (il regarde vers `−Y`). Les orbites sont percées
  selon `+Y`, donc droit vers l'arrière.
- `+Z` = haut. Sol à `z = 0`, contact réel mesuré à `0,0000`.

## Hiérarchie

```text
K3_GOLEMGRES_ROOT            (Empty, 0,0,0 — pivot de scène)
├── K3_GOLEMGRES_BODY        corps + crâne + orbites + runes de poitrine
├── K3_GOLEMGRES_ARM_R       bras droit + pouce + runes
├── K3_GOLEMGRES_ARM_L       bras gauche + pouce + runes
├── K3_GOLEMGRES_LEG_R       moignon droit
└── K3_GOLEMGRES_LEG_L       moignon gauche

hors personnage (banc de contrôle) :
K3_GOLEMGRES_GROUND · K3_GOLEMGRES_KEY · K3_GOLEMGRES_RIM · K3_GOLEMGRES_CAM
```

Le parentage est posé par affectation directe (`obj.parent` + `matrix_parent_inverse`)
et non par `parent_set`, qui réinitialise l'échelle.

## Pièces

| Pièce | Origine / pivot | Dimensions X·Y·Z (m) | Polys | Matières |
|---|---|---|---|---|
| `BODY` | `(0, 0, 0.063)` bas du ventre | 0.782 · 0.645 · 0.990 | 501 | grès + noir d'orbite |
| `ARM_R` | `(0.239, 0, 0.750)` épaule | 0.467 · 0.225 · 0.647 | 271 | grès |
| `ARM_L` | `(−0.239, 0, 0.750)` épaule | 0.473 · 0.225 · 0.656 | 317 | grès |
| `LEG_R` | `(0.182, −0.012, 0.154)` hanche | 0.240 · 0.254 · 0.152 | 97 | grès |
| `LEG_L` | `(−0.182, −0.012, 0.154)` hanche | 0.239 · 0.250 · 0.150 | 85 | grès |

**Total 1 271 polygones.** Encombrement global **1,250 × 0,645 × 1,000 m**.

Chaque pivot est posé au joint utile pour un futur rig : épaules pour les bras,
hanches pour les jambes, base du ventre pour le corps.

## Traits d'identité

| Trait | Valeur | Provenance |
|---|---|---|
| Hauteur | 1,000 m | contrat |
| Envergure bras compris | 1,250 m | calque (bord externe constant à 0,623) |
| Profondeur | 0,645 m | panneau de profil |
| Demi-largeur max du corps | 0,399 m à `z = 0,325` | calque |
| Base du crâne | demi-largeur 0,314 m à `z = 0,750` | calque |
| Rayon d'œil | 0,0296 m | pixels quasi noirs de la planche |
| Écart des yeux | ±0,094 m | idem |
| Hauteur des yeux | `z = 0,789` | idem |
| Profondeur d'orbite | 2,1 rayons, percée droit vers `+Y` | choix de construction |
| Jambes | largeur 0,215 m, écart ±0,182 m | deux plages basses du calque |
| Gravures | 4 runes, sillons 16 mm × 10 mm | dessin, placement posé à la main |

Les yeux sont de **vrais trous** : un fût cylindrique à fond en calotte, dont les
parois portent une matière noire dédiée. Une bille posée aurait pris la lumière
et produit un œil brillant, là où la référence montre des cavités mates.

## Matières

| Nom | Rôle | Points clés |
|---|---|---|
| `MAT_SANDSTONE` | pierre | dégradé vertical ocre, marbrure et grain en bump, rugosité 0,62–0,86 modulée |
| `MAT_EYE` | parois d'orbite | quasi noir, rugosité 0,32 |
| `MAT_GROUND` | sol du banc | gris mat, hors personnage |

L'assombrissement des creux passe par un nœud **Ambient Occlusion**, pas par
`Pointiness` : ce dernier n'existe que sous Cycles et laissait les gravures
invisibles au contrôle viewport en EEVEE.

## Conformité mesurée (dernier gate)

Silhouette de face, 41 tranches comparées à la planche, normalisées en hauteur :

| Zone | Écart |
|---|---|
| `t` = 0,975 → 0,025 (le personnage) | **−3,7 % à +0,6 %** |
| `t` = 1,000 (apex) | +17,1 % — sur une demi-largeur de 5,6 mm, soit +1 mm |
| `t` = 0,000 (semelle) | −11,3 % — l'arête de semelle est arrondie par le bevel |

## Écarts assumés

- **Profondeur des bras** : non mesurable. De profil, le bras est dessiné à
  l'intérieur du contour du corps. Déduite de la largeur par un ratio 1,08.
- **Hauteur des jambes** : non mesurable de face, le ventre les couvre. Posée à
  0,155 m pour garantir la soudure au corps.
- **Placement des runes** : la planche montre leur style, pas des coordonnées
  exploitables. Les tracés et positions sont composés à la main.
- **Échelle des panneaux** : la planche dessine le profil ~8 % plus grand que la
  face. Chaque vue est normalisée par sa propre hauteur de personnage.
- **Fermeture du dessous** : le calque s'arrête où les jambes prennent le relais ;
  le ventre est refermé 55 mm plus bas, hors silhouette.

## Pièges rencontrés, à ne pas refaire

1. **Maillage ouvert + booléen EXACT = blocage.** Un tour dont les extrémités
   n'étaient pas capées a fait tourner Blender 17 minutes à 99 % CPU sans jamais
   rendre la main. `assert_closed()` refuse désormais d'entrer dans un booléen
   avec un bord ouvert.
2. **Outil booléen en chapelet de cubes.** Une gravure approchée par des centaines
   de boîtes qui se recouvrent rendait un maillage déchiré (307 bords ouverts).
   Remplacé par un prisme fermé par trait, un booléen par trait.
3. **`recalc_face_normals` ne suffit pas.** Sur un tube courbe il peut retenir
   l'orientation inverse ; la différence devient alors une intersection et le
   corps disparaît. L'orientation se décide au volume signé (`ensure_outward`).
4. **Un booléen par coque.** Deux orbites dans un même maillage d'outil piègent le
   test de volume signé, qui raisonne sur leur somme.
5. **Le Boolean laisse un slot de matière vide en index 0**, et toutes les faces
   pointent dessus : le corps rendait en blanc. `assign_material()` repart d'un
   slot unique.
6. **Relevé à l'œil sur une illustration : non fiable.** Mes lectures au pixel se
   sont trompées de +43 % sur la largeur du crâne et de 3,7 cm sur la hauteur des
   yeux. Le gate d'extraction a tranché ; c'est lui qui fait autorité.

## Reprendre le travail

```bash
open -na /Applications/Blender.app          # l'addon démarre le serveur MCP seul
```

Puis, dans Blender :

```python
exec(open('${BLENDER_AGENT_STUDIO_ROOT}/workflows/tools/trace_golem_reference.py').read())
exec(open('${BLENDER_AGENT_STUDIO_ROOT}/workflows/scripts/build_golem_de_gres.py').read())
exec(open('${BLENDER_AGENT_STUDIO_ROOT}/workflows/tools/gate_golem_silhouette.py').read())
```

Le constructeur est idempotent : il purge sa propre production (`K3_GOLEMGRES_*`)
avant de rebâtir, et ne touche à aucun objet non préfixé.
