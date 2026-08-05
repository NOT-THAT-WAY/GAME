# FL Studio Box — template semantic panels

Version principale construite à partir de la référence finale : chaque vraie fenêtre FL
Studio reste lisible et reçoit sa propre surface, tout en restant synchronisée au même
master vidéo.

## Répartition

- playlist seule sur le mur du fond;
- liste de kits seule sur la paroi gauche, sans waveform ni pixels du Piano Roll;
- mixer seul sur la paroi droite;
- piano roll seul sur le plancher incliné;
- channel rack seul sur le module avant.

Le preset est normalisé depuis la capture test 1920×1080 et s'adapte aux autres captures
16:9 qui conservent la même organisation des fenêtres.

## Lighting V4

Le grade sombre et très contrasté a été remplacé par:

- deux grandes Area Lights neutres et douces;
- un environnement plus clair;
- une exposition à +0,55;
- AgX Medium Low Contrast;
- un rebond vert fortement réduit;
- une coque gris chaud plus lisible.

## Browser et glow V5

Le Browser utilise un encodage all-intra et une grille UV bilinéaire 20 x 40. Cela évite
les artefacts lors du scrubbing et la cassure diagonale produite par un unique quad
trapézoïdal. Les barres de lecture vertes sont des objets 3D émissifs synchronisés à la
lecture; leur glow réagit légèrement à l'énergie audio. Le Fog Glow est ajouté après le
rendu clair et ne dépend donc pas d'un lighting général sombre.

La V6 conserve uniquement la barre 3D du mur arrière. Celle du plancher a été retirée car
elle doublait le curseur déjà présent dans la vidéo du Piano Roll. La palette associe une
coque nacrée prune, une lumière acid lime à gauche et une lumière hot magenta à droite,
soutenues par des sources neutres pour éviter un résultat sombre ou délavé.

Le workspace `USTUDIO Camera Lab` place le rendu direct à gauche, la vue objet/caméra au
centre et le Dope Sheet en dessous.

## Flottement et caméra

`USTUDIO_BOX_FLOAT_ROOT` place la boîte environ 1,2 m au-dessus de sa position initiale et
anime une boucle lente de bob, drift et rotations. La caméra utilise deux gestes construits
avec la règle Drumboiii : pose, anticipation opposée, mouvement principal, settling. Sa
target suit la boîte avec six frames de retard environ, ce qui évite une caméra parfaitement
robotique et accentue la sensation de masse suspendue.
