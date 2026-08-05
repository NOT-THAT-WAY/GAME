# Revue finale — k3-mecha-mascot-model-v002

## Verdict

`ship` — score pondéré `92,25 / 100`, sans échec critique.

## Correction morphologique

La nouvelle planche montre que la V1 interprétait une pose en étoile comme une proportion
canonique. Ses jambes étaient trop courtes, trop épaisses à la hanche et beaucoup trop écartées
pour servir de base aux poses assise, agenouillée, couchée ou debout visibles dans la référence.
La V2 conserve la tête, le matériau et le langage organique, mais remonte le bassin, affine les
cuisses, allonge les jambes et rapproche les pieds presque sous les hanches.

## Physique et topologie

Le corps évalué compte 27 586 sommets et 27 584 faces dans Blender. Il ne présente aucun bord
ouvert, bord non-manifold ou face dégénérée. Les deux pieds touchent le plan `z=0` avec seulement
une erreur numérique infinitésimale et aucune géométrie ne passe sous le support. La tête reste
un mesh fermé distinct, parenté à `K3_MECHA_MASCOT_ROOT`.

## Comparaison et cadrage

La comparaison V1/V2 emploie le même cadrage et le même éclairage. La V2 forme désormais deux
colonnes de jambes longues avec une fourche plus haute, conformément aux personnages debout de
la planche. La largeur extrême des bras est conservée car elle vient de la première référence ;
seule la famille de causes « proportions des jambes » a été modifiée pendant cette passe.

## Animation future

L'asset reste volontairement non riggé pour ne pas imposer des poids avant de choisir les poses
à produire. Sa géométrie fermée et ses jambes distinctes conviennent maintenant mieux à une
armature simple. Pour le caractère Drumboiii, la racine servira au mouvement global et une
Lattice ou une armature pourra porter le squash secondaire sans déformer le placement général.

## Livrables

La V1 est conservée. La V2 est publiée séparément dans le catalogue `Characters/Mascots` en
`.blend` et `.glb`. Le fichier de bibliothèque contient trois objets, deux meshes et aucune
dépendance externe. Le GLB a été réimporté avec deux meshes fermés, leurs noms et leur matériau.
La scène d'essai contient aussi la preview de six secondes, le contact sheet, la comparaison
directe V1/V2, le gate lumière et les diagnostics complets.
