---
name: git-task
description: Démarre, reprend ou publie une tâche Git du projet GAME avec une branche normalisée et une pull request. Utiliser automatiquement quand l'utilisateur demande de commencer une tâche, créer une branche, publier, pousser ou ouvrir une PR.
---

# Gérer une tâche Git GAME

Exécuter le workflow au lieu de seulement donner les commandes.

## Avant toute action

1. Lire `git status --short --branch` et les règles de `docs/WORKFLOW.md`.
2. Ne jamais effacer, stasher ou déplacer des changements existants sans accord explicite.
3. Ne jamais travailler ni pousser directement sur `main`.
4. Ne jamais utiliser `--no-verify`, modifier le hook local ou pousser `main` depuis une autre interface.

## Commencer

Choisir le type qui décrit le contenu principal :

- `feat` : capacité jouable, réseau ou outil utilisateur ;
- `fix` : correction d'un comportement incorrect ;
- `art` : visuel, animation, UI artistique ou export ;
- `audio` : Wwise, son, musique ou intégration audio ;
- `data` : DVC, schéma, catalogue ou migration de données ;
- `docs` : documentation uniquement ;
- `chore` : dépendances, configuration, CI ou maintenance.

Créer un nom court en minuscules avec tirets, puis utiliser le script de la plateforme :

- macOS : `./scripts/start-task.sh TYPE nom-court`
- Windows : `.\scripts\start-task.ps1 TYPE nom-court`

Si une branche valide contient déjà le travail demandé, la conserver au lieu d'en créer une autre.

## Publier

1. Examiner le diff et exécuter les tests proportionnés au changement.
2. Faire un commit dont le préfixe correspond à la branche.
3. Vérifier que le dépôt est propre.
4. Publier avec un titre de PR correspondant :
   - macOS : `./scripts/publish-task.sh "TYPE: résultat testable"`
   - Windows : `.\scripts\publish-task.ps1 "TYPE: résultat testable"`
5. Rendre le lien de la PR et l'état des contrôles. Ne merger que sur demande explicite ou si la demande initiale incluait clairement la livraison complète.
