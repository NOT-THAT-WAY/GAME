# Méthode Blender Team Studio

## Principe

Séparer les responsabilités rend la génération éditable :

1. **Identité** — références canoniques, dimensions, détails et affordances.
2. **Asset** — géométrie, hiérarchie, matériaux, rig et provenance.
3. **Mouvement** — poses, pivots, caméra et timing déterministes.
4. **Scène** — supports, décor, lumière, reflets et corridor caméra.
5. **Stylage** — profil artistique explicite, rendu ou génération vidéo aval.

Un modèle vidéo ou un preset ne doit pas réinventer simultanément ces cinq couches.

## Boucle commune

### 1. Brief atomique

Un sujet, une fonction ou action principale, une durée/échelle, des états de départ et d’arrivée,
des invariants et des critères observables.

### 2. Contrat réel

Déclarer unités, repère, supports, colliders, contacts, joints, clearances et usages. Les seuils sont
fixés avant l’animation et ne sont pas élargis après un échec.

### 3. Blockout

Valider silhouette, proportions, états mécaniques et poses hero en clay. Pour un asset, tester la
distance caméra prévue. Pour un film, poser `still → anticipation → action → impact → settle`.

### 4. Caméra et lumière

Calibrer les valeurs sur les bounds évalués. Séparer caméra, target et focus. Construire la lumière
par fonctions visibles et comparer les mêmes frames. Le profil par défaut est neutral-production ;
Drumboiii est sélectionné explicitement.

### 5. Gates

1. identité et proportions ;
2. supports, contacts, articulations et collisions ;
3. mouvement, cadrage, focus et continuité ;
4. matériaux, labels et détails ;
5. dépendances, rendu et frames ;
6. export et réimport ;
7. verdict humain lorsque le goût ou le risque le demande.

## Génération vidéo aval

Une vidéo Blender déterministe peut servir de squelette de mouvement tandis qu’une image de scène
fixe la direction visuelle. Les références concurrentes sont limitées et leur domaine de vérité est
déclaré : front pour layout, side pour profondeur, close-up pour détail local. Les résultats rejetés
restent archivés mais ne reviennent jamais comme références silencieuses.

## Génération d’asset

Construire et valider l’asset hors de sa scène de présentation. La scène hero peut masquer un défaut
de topologie ou d’échelle ; l’audit de l’asset et le round-trip d’export sont donc séparés.

## Temps réel et environnements

Un export Blender ou glTF valide n’est qu’une preuve intermédiaire. Déclarer le moteur et sa
version, importer dans la cible, vérifier échelle, axes, pivots, matériaux, collisions, LOD,
navigation, clips et performance. Les Geometry Nodes, seeds, caches et instances doivent rester
reproductibles et respecter les exclusions de gameplay.
