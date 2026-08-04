---
name: lan-test
description: Construit et lance le premier test multijoueur LAN de GAME sur Mac ou Windows. Utiliser lorsque l'utilisateur veut jouer ensemble, héberger, rejoindre ou tester la connexion réseau.
---

# Lancer le test LAN GAME

## Préconditions

1. Se placer à la racine du dépôt et refuser le test si `Packages/packages-lock.json` manque.
2. Vérifier que les participants utilisent le même commit avec `git rev-parse --short HEAD`.
3. Exécuter le doctor de la plateforme et arrêter sur toute erreur.
4. Vérifier que Unity est fermé.
5. Le coffre DVC, Wwise et Steam ne sont pas requis.

## Informations nécessaires

Déterminer le rôle (`host` ou `client`) et le nom du joueur. Pour un client, obtenir l'adresse IPv4 privée affichée par l'hôte. Ne jamais inventer cette adresse ni la publier dans une issue publique.

## Commandes

Sur le Mac hôte :

`./scripts/first-test-macos.sh host --name "NOM"`

Sur un client Mac :

`./scripts/first-test-macos.sh client --address "IP_HOTE" --name "NOM"`

Sur un client Windows :

`.\scripts\first-test-windows.ps1 Client -Address "IP_HOTE" -Name "NOM"`

Le port commun est UDP `7770`. Au premier lancement Windows, demander à l'utilisateur d'autoriser GAME uniquement sur les réseaux privés. Ne jamais désactiver globalement un pare-feu.

Le test réussit lorsque les trois fenêtres affichent `AUTHENTICATED` et les trois noms. En cas d'échec, lire `Logs/ConnectionTest/` et suivre `docs/FIRST_CONNECTION_TEST.md`.
