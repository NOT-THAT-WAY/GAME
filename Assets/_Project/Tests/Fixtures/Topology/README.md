# Fixtures de topologie v1

Ces fichiers préparent `TOP-01` sans implémenter le parseur ni trancher une règle de game design.
Le manifest associe chaque mutation à un code d’erreur stable attendu.

Portée déjà fixée : JSON strict, version de schéma, IDs explicites, références et coordonnées dans
les bornes. Les valeurs métriques du cas valide reprennent le labyrinthe actuel, mais ne deviennent
pas un preset joueur ou simulation.

Hors portée jusqu’aux décisions/PR concernées : garantie de connectivité DEC-02, bytes canoniques et
checksum, tick/physique/gabarit DEC-01, énergie DEC-03 et condition de manche DEC-04.

`valid-minimal.json` décrit deux cellules, un mur pivotant, deux ouvertures et deux spawns. Les cas
invalides ne changent qu’une catégorie afin qu’un test rouge garde une cause unique. Le futur test C#
charge `manifest.json`, exige exactement les `expectedIssueCodes` et refuse tout parse partiel.
