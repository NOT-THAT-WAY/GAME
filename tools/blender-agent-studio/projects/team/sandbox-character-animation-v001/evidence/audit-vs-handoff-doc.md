# Audit réel du FBX source vs audit déclaré dans docs/SANDBOX_ANIMATION_HANDOFF.md

Source auditée (immuable, jamais écrite) :
`Assets/_Project/Player/PersoBouleRigged.fbx`
SHA-256 `4503459d16ccc2af8ebc11b621850de3d1dae213d8d3f43420ae97f84231cce1`

Méthode : import lecture seule dans Blender 5.1.1 `--background --factory-startup`, scène vidée par
`read_factory_settings(use_empty=True)` puis purge des datablocks orphelins. Mesures sur géométrie
**évaluée** (après armature + modifiers), repère monde Blender Z-up, mètres.
Scripts : `scripts/audit_source_fbx.py`, `scripts/audit_source_fbx_part2.py`.
Sorties : `evidence/skeleton-audit.json`, `evidence/source-audit-pass2.json`.

## Conforme à la doc

| Point de la doc | Mesure réelle | Statut |
|---|---|---|
| rig Generic, échelle d'armature `(1,1,1)`, origine `(0,0,0)` | objet armature `BAS_PUNCH_Rig` : loc `(0,0,0)`, rot `(0,0,0)`, scale `(1,1,1)` | conforme |
| 10 os, `root`, `body`, deux chaînes `upperarm/forearm/hand`, deux pieds sur `root` | 10 os, topologie identique (voir écart n°1 sur les noms) | conforme |
| 9 meshes skinnés, 2 870 vertices, 5 664 triangles | 9 meshes skinnés, **2 870** vertices, **5 664** triangles | conforme |
| une Action `BAS_PUNCH_Rig\|BAS_PUNCH_Rig\|BAS_PUNCH_punch`, images 1–20 à 24 fps | identique ; 109 fcurves ; scène à 24 fps | conforme |
| personnage haut de 1,30 à 1,45 m | **1,34 m** (bounds évalués au repos, axe Z) | conforme |
| max 4 influences par vertex | max réel **1** influence/vertex, 0 vertex non pesé, somme des poids exacte | conforme, très en dessous |
| budget 6 000 triangles / 16 os | 5 664 triangles / 10 os | conforme |

## Écarts à signaler

### 1. Les noms d'os portent le préfixe `BAS_PUNCH_` (impact élevé)

La doc écrit `root`, `body`, `upperarm/forearm/hand`. Les noms réels sont :

```
BAS_PUNCH_root
└─ BAS_PUNCH_body
   ├─ BAS_PUNCH_upperarm.L → BAS_PUNCH_forearm.L → BAS_PUNCH_hand.L
   └─ BAS_PUNCH_upperarm.R → BAS_PUNCH_forearm.R → BAS_PUNCH_hand.R
├─ BAS_PUNCH_foot.L
└─ BAS_PUNCH_foot.R
```

La doc emploie donc une forme abrégée, pas les identifiants littéraux. La consigne « conserver la
hiérarchie et les noms des os » est appliquée aux noms **réels** : aucun os n'est renommé.

### 2. Aucun Cube, Camera ou Light dans le FBX source (impact moyen)

La doc affirme : « le FBX contient aussi un Cube non skinné de 12 triangles ainsi que Camera/Light ».
Mesure : `PersoBouleRigged.fbx` ne contient que 9 objets MESH skinnés + 1 objet ARMATURE.
`bpy.data.cameras`, `bpy.data.lights` et les meshes non skinnés sont **vides** après import en scène
réellement vide. Le fichier voisin `PersoBoule.fbx` ne contient lui aussi aucun parasite (un seul
mesh `Perso_Boule`, non riggé, 2 234 v / 4 440 t).

Piège de mesure écarté : un premier passage lancé en `--factory-startup` avec simple suppression des
objets laissait les datablocks orphelins `Cube` / `Camera` / `Light` de la scène de démarrage Blender
et les faisait apparaître comme des parasites du FBX. Ils venaient de Blender, pas du fichier.

Conséquence : la consigne « ne pas exporter Cube, Camera, Light » est déjà satisfaite par la source ;
il n'y a rien à retirer. Le contrôle est néanmoins rejoué sur le FBX candidat exporté.

## Faits mesurés absents de la doc et structurants pour l'animation

1. **Personnage à pièces rigides, pas de skin lisse.** Chaque mesh est pesé à 100 % sur un seul os
   (max 1 influence/vertex). Il n'y a aucune déformation continue : les volumes sont transformés en
   corps rigides. Aucun squash/stretch par poids n'est possible.
2. **Aucune jambe.** Les pieds sont deux volumes détachés parentés directement à `BAS_PUNCH_root`.
   Les bras sont eux aussi des volumes détachés. Le transfert de poids ne peut donc pas passer par
   des genoux : il doit être porté par le corps et l'inclinaison.
3. **Orientation faciale mesurée.** Le patch de matériau `BAS_PUNCH_Mat_Eye` (172 vertices du mesh
   corps) est centré à `Y = -0,44`. Le personnage regarde donc **-Y en Blender**, ce qui correspond à
   **+Z Unity** (avant) avec l'export `-Z forward / Y up`.
4. **Pivot du corps sous le centre du volume.** `BAS_PUNCH_body` a sa tête à `Z = 0,30` alors que la
   sphère est centrée à `Z = 0,78` (rayon ≈ 0,56 m). Une rotation du corps produit donc une bascule
   autour du « bassin », pas autour du centre de la sphère.
5. **Budget vertical de respiration.** Distance libre mesurée entre le bas de la sphère et le dessus
   des pieds au repos : ≈ **0,071 m**. Au-delà, la sphère entre dans les pieds.
6. **La Punch existante n'a pas de root motion.** Ses canaux objet `location/rotation_euler/scale`
   sont keyés mais constants `(0,0,0)` / `(0,0,0)` / `(1,1,1)`, et `BAS_PUNCH_root` est keyé sans
   delta. Le placeholder est déjà in-place.
7. **La pose importée n'est pas la bind pose.** À l'image 1 avec l'Action Punch assignée, l'écart
   maximal de `matrix_basis` est **0,980** (`BAS_PUNCH_forearm.L`). La bind pose réelle est retrouvée
   en désassignant l'Action ; elle sert de base à `SB_Idle`.

## Décision

Aucun écart ne bloque la production de `SB_Idle`. Les écarts 1 et 2 sont consignés ici et repris dans
le rapport final. La doc `docs/SANDBOX_ANIMATION_HANDOFF.md` n'est pas modifiée pendant cette passe.
