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
