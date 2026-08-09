# HT-00 — smoke test humain minimum

## But

HT-00 vérifie seulement que le build de développement permet d’utiliser les briques déjà décidées :
déplacement, caméra, saut, manipulation d’un pivot ou d’un mur et punch du bot.

Ce n’est pas un test de découverte, une étude UX ou un verdict de fun. Les commandes sont données
directement : aucun chronomètre de compréhension, questionnaire ou piège de test n’est ajouté.

## Préparation automatisée

Le wrapper construit le profil `maze`, lance un hôte local, hash le binaire et conserve le log :

```bash
./scripts/human-test-macos.sh --build
```

Le panneau réseau est masqué pour libérer l’écran. Le HUD affiche directement les commandes utiles.
Le gameplay reste identique au smoke test historique.

## Parcours strictement nécessaire

Durée cible : **3 à 5 minutes**.

1. Bouger et regarder autour de soi.
2. Sauter une fois.
3. Faire tourner un pivot avec clic gauche + avancer, ou déplacer un mur en avançant/clic droit.
4. Donner un coup de poing au bot.
5. Utiliser `U` seulement si le personnage est coincé.
6. Fermer le jeu.

Inutile de tester toutes les entrées, tous les murs, plusieurs résolutions, le réseau distant ou
l’équilibrage pendant HT-00.

## Verdict minimal

`PASS` si :

- le joueur apparaît et répond à la caméra/déplacement ;
- au moins une manipulation de labyrinthe réussit ;
- le punch est déclenché et le bot peut être touché ;
- aucun crash ou blocage durable n’interrompt le parcours.

`FAIL` seulement pour une panne reproductible qui empêche ces actions. Un défaut visuel, une valeur de
gameplay discutable ou une impression personnelle devient une note courte pour le prochain lot, pas
une nouvelle gate.

## Gestion automatique

En mode HT-00, le jeu écrit des marqueurs `[GAME-SMOKE]` pour `ready`, `look`, `movement`, `jump`,
`punch`, `bot_hit`, `pivot_turned` et `wall_turned`. Après fermeture, Codex lit le log et rend le
verdict ; le testeur n’a pas à remplir de protocole détaillé.

## Première exécution — 9 août 2026

La session `ht00-20260809T172338Z-6b565f06-29081` est **INCOMPLETE**, sans crash : démarrage,
caméra, déplacement, saut, punch et impact bot sont prouvés ; aucun changement effectif de pivot ou
mur n’apparaît dans le log malgré l’action opérateur. Ce n’est pas converti artificiellement en
`PASS`. Le suivi ajoute des marqueurs d’intention/contact/requête/refus afin d’isoler la chaîne en
une prochaine exécution, sans modifier les règles ni imposer une nouvelle session immédiatement.
