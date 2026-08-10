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

Ce chemin construit en IL2CPP, donc il ne se connecte pas aujourd’hui : le serveur éjecte son propre
client local sur le handshake de version FishNet. Le constat, ses preuves et le build Mono de secours
sont dans [WINDOWS_IL2CPP_BLOCKER.md](WINDOWS_IL2CPP_BLOCKER.md). Toute mesure Windows obtenue par ce
repli doit être annoncée comme une mesure Mono.

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

Elle exécute en vrais processus l’écartement d’un joueur resté dans l’arc, l’opposition égale, le
pivot A→B et le remplacement par un client tardif. Elle ne remplace ni Windows, ni un réseau dégradé.

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

### Commandes

Le player affiche en permanence un rappel repliable des commandes en bas à gauche. Aucun objectif
n'y est injecté : le banc mesure les actions prévues, pas la découverte d'un tutoriel.

| Action | Clavier / souris | Manette |
| --- | --- | --- |
| Se déplacer | `ZQSD` (`WASD`) | stick gauche |
| Regarder | souris | stick droit |
| Courir | `Maj` | L3 |
| **Pousser le mur cyan** | **maintenir `E`** ou clic gauche | gâchette droite |
| Frapper | `F` ou clic droit | R1 |
| Vue 1re / 3e personne | `F1` | croix haut |
| Libérer le curseur | `Échap` | Start |

Le battant s'éloigne toujours de celui qui pousse et il tourne librement sur 360°. Il n'y a ni
seuil à charger ni palier : il part au premier tick d'appui et s'arrête au tick où l'on relâche.
La puissance dépend de l'endroit où l'on pousse — **30 % contre le gond, 100 % au bout du
battant**, au prorata — et l'indicateur central affiche ce levier en pour-cent. Comme une vraie
porte, il faut **marcher avec elle** : un pousseur immobile perd le contact au bout de quelques
dizaines de degrés. Se placer sur l'autre face inverse le sens. Deux joueurs face à face
s'annulent : le battant se fige, et celui qui s'éloigne du gond l'emporte. Les coups de poing
versent le même couple pendant une fraction de seconde. Le saut n'est pas branché sur ce banc.

Faire uniquement ces cinq quêtes, sans indice en jeu ni questionnaire :

1. fenêtre par fenêtre, chacun rejoint le pad coloré opposé ; PASS si aucun blocage ou reset n’est
   nécessaire ;
2. au contact du mur cyan, maintenir `E` et marcher avec lui ; PASS si le battant part au premier
   appui sans temps mort et tourne tant que la main reste dessus, sur les deux fenêtres ;
3. repasser sur l’autre face du battant et maintenir `E` ; PASS s’il repart dans l’autre sens,
   depuis n’importe quel angle du tour ;
4. de part et d’autre du battant, chacun maintient `E` ; PASS si le mur se fige quand les leviers
   se valent et repart du côté de celui qui s’éloigne du gond, l’indicateur affichant les deux
   pourcentages ;
5. laisser un joueur immobile dans la trajectoire pendant que l’autre pousse ; PASS si le battant
   l’écarte sans le traverser ni le coincer.

Fermer les deux instances après ces cinq verdicts. Le late join et l’opposition exacte au même
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
