# Revue finale — k3-mecha-mascot-model-v001

## Verdict

`ship` — score pondéré `91,55 / 100` et aucun échec critique.

## Résultat

La référence `model 3D mecha.png` a été reconstruite comme une mascotte humanoïde organique
réutilisable. Le corps forme un volume fermé continu avec bras relevés, taille pincée, jambes
ouvertes et deux pieds arrondis. La tête est un mesh fermé indépendant, parenté à une racine
commune afin de préserver une option d'animation sans imposer immédiatement un rig.

## Physique et usage

Le repère canonique est `+Z` vers le haut et `-Y` vers l'avant. Les deux pieds touchent le
support à `z=0` avec une erreur numérique inférieure au micromètre. Le corps évalué compte
32 122 sommets et 32 120 faces avant export, sans bord ouvert, bord non-manifold ni face
dégénérée. Aucun joint n'est déclaré : les futures scènes peuvent choisir une armature ou une
Lattice partagée selon le geste demandé.

## Caméra et rythme

La preview de six secondes utilise un seul arc studio. Les poses suivent la grammaire
Drumboiii : K1 pose, K2 anticipation opposée, K3 travel, K4 recovery, puis hold. Le sujet reste
immobile. Camera, target et focus sont séparés ; la focale de 56 mm garde la silhouette entière
dans le cadre sans clipping.

## Lumière et design

La présentation utilise un environnement distinct du ciel caméra, un Sun de reflet, un
backlight de forme et trois glimmers fonctionnels. Les six étapes cumulatives sont conservées
dans le gate lumière. Le matériau ivoire chaud reste volontairement neutre, mat et sans détail
typographique pour laisser le modèle disponible aux futurs looks.

## Limites assumées

Le modèle n'est pas encore riggé et ne possède aucun visage : ce sont des choix de neutralité,
pas des oublis cachés. Le profil est volontairement plus mince que la face, conformément à la
lecture en volume de la référence. La tête reste séparée du corps pour faciliter une future
animation ; elle peut être fusionnée dans une version dédiée si un plan exige un squash continu.

## Validation et livrables

Le `.blend` publié ne contient que la racine et les deux meshes utiles. L'audit publié relève
trois objets, deux meshes, zéro image externe, zéro bibliothèque et zéro alerte géométrique. Le
GLB a été réimporté avec fusion des coutures et conserve deux meshes fermés ainsi que le matériau.
Les livrables comprennent scène de trial, asset Blender catalogué, GLB, preview, contact sheet,
gate lumière, audits, contrat physique et manifeste d'asset.
