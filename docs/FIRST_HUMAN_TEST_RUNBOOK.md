# HT-00 — lancement minimal

## macOS

Fermer les anciennes instances, puis lancer :

```bash
./scripts/human-test-macos.sh --build
```

Le script effectue le préflight, reconstruit le profil `maze`, lance `HT_HOST` avec `--human-test`,
hash le binaire et écrit la session sous `Logs/HumanTest/<session-id>/`.

## Windows

```powershell
.\scripts\human-test-windows.ps1 -Build
```

La validation réelle Windows reste à effectuer sur le PC de l’équipe.

## Test

Suivre seulement la checklist de [FIRST_HUMAN_TEST_DESIGN.md](FIRST_HUMAN_TEST_DESIGN.md), puis fermer
le jeu. Les commandes sont affichées ; aucune fiche d’étude n’est à remplir.

## HT-M1 — mur autoritaire minimal

HT-M1 est un **banc technique**, pas une tranche du jeu. Il montre une arène 2×2 générée depuis la
topologie graybox pour mesurer déplacement prédit, autorité serveur et un seul mur pivotant. Le
labyrinthe 16×16 reste le banc de rendu ; l'annoncer autrement fausse l'avis demandé. Le personnage
et l'éclairage sont ceux du projet uniquement pour que l'image soit lisible, pas pour juger la
direction artistique.

Avant d'envoyer un build à un humain, produire et regarder les captures :

```bash
./scripts/m1-preview-macos.sh           # scène, personnages, vue première personne
./scripts/m1-preview-macos.sh --player  # capture de l'exécutable macOS déjà compilé
```

Elles sont écrites dans `Logs/M1Playtest/`, et `m1-human-test-macos.sh --build` les régénère puis
les copie dans la session. Un banc qui compile, passe ses tests et écrit ses logs peut sortir
entièrement en magenta : URP ne fournit plus de matériau par défaut hors éditeur, donc tout objet
doit porter un matériau explicite. La génération de scène refuse désormais tout matériau hors URP,
mais la capture reste le seul contrôle qui voit réellement l'image.

La gate locale doit être verte avant de demander un avis humain :

```bash
./scripts/m1-network-tests-macos.sh all --build
```

Elle exécute en vrais processus l’occupation de l’arc, l’opposition égale, le pivot A→B et le
remplacement par un client tardif. Elle ne remplace ni Windows, ni un réseau dégradé.

Lancer ensuite les deux fenêtres visibles :

```bash
./scripts/m1-human-test-macos.sh
```

Pour le smoke réseau à trois connexions simultanées, lancer à la place :

```bash
./scripts/m1-human-test-macos.sh --players 3
```

La topologie reste un duel à deux spawns canoniques. Le build M1 réserve un troisième emplacement
gris distinct uniquement pour ce test réseau afin de ne pas superposer deux contrôleurs.

Faire uniquement ces quatre quêtes, sans indice en jeu ni questionnaire :

1. fenêtre par fenêtre, chacun rejoint le pad coloré opposé ; PASS si aucun blocage ou reset n’est
   nécessaire ;
2. côté pad rouge, près du pivot orange, maintenir `E` deux secondes ; PASS si le mur cyan devient
   horizontal sur les deux fenêtres ;
3. sans changer de position, maintenir encore `E` deux secondes ; PASS si le mur revient vertical
   sur les deux fenêtres ;
4. sans déplacer ce pousseur, placer l’autre joueur sur le pad vert puis répéter `E` deux secondes ;
   PASS si le mur reste vertical et personne n’est déplacé ou coincé.

Fermer les deux instances après ces quatre verdicts. Le late join et l’opposition exacte au même
tick sont déjà automatisés : inutile d’essayer de les reproduire entre deux fenêtres macOS.

## Résultat

Le log privé contient les marqueurs `[GAME-SMOKE]`. Après fermeture, le verdict est produit par :

```bash
python3 scripts/human-test-report.py
```

Sans option, l’analyseur prend la dernière session possédant un `host.log` non vide. Il contrôle
automatiquement lancement, inputs de base, punch, impact bot, manipulation du labyrinthe et erreurs
fatales. Le testeur signale uniquement, en une phrase libre, ce qui lui a semblé cassé ou gênant.

HT-00 reste un smoke test local. Il ne valide pas Windows, le réseau distant, la simulation
autoritaire, la performance finale ou le fun du jeu.
