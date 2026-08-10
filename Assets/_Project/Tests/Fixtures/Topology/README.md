# Fixtures de topologie v1

Ces fichiers verrouillent `TOP-01` sans trancher une règle de game design. Le manifest associe chaque
mutation à un code d’erreur stable attendu et les tests C# refusent tout document partiel.

Portée déjà fixée : JSON strict, version de schéma, IDs explicites, références bijectives,
coordonnées, limites de cardinalité, géométrie des quarts de tour et absence de chevauchement entre
arêtes initiales/ouvertures. Les valeurs métriques du cas valide reprennent le labyrinthe actuel,
mais ne deviennent pas un preset joueur ou simulation.

Hors portée jusqu’aux décisions/PR concernées : garantie de connectivité DEC-02,
tick/physique/gabarit DEC-01, énergie DEC-03 et condition de manche DEC-04. Les bytes canoniques et
le checksum SHA-256 sont maintenant implémentés ; le cas minimal fixe un vecteur de hash commun.
Le chargement runtime utilise `ParseVerified` : checksum absent ou vide et espace d'états mobile
incomplet sont refusés, même si `Parse` reste disponible pour une fixture d'auteur non signée.

`valid-minimal.json` décrit deux cellules, un mur pivotant, deux ouvertures et deux spawns. Les cas
invalides ne changent qu’une catégorie afin qu’un test rouge garde une cause unique. Le test C# exige
exactement le code attendu et refuse tout parse partiel.
