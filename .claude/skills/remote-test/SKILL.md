---
name: remote-test
description: Prépare et lance le test multijoueur de GAME lorsque les participants sont sur des réseaux différents. Utiliser automatiquement pour jouer en ligne, à distance, chacun chez soi, via Tailscale ou hors du même Wi-Fi.
---

# Lancer le test distant GAME

Exécuter le workflow ; ne pas présenter une adresse LAN `192.168.x.x` comme joignable depuis Internet.

## Frontière de sécurité

1. Tailscale est un outil de développement et ne fait pas partie du build distribué.
2. Ne jamais demander, afficher, stocker ou committer une clé d'authentification Tailscale.
3. Chaque membre utilise son propre compte et accepte manuellement l'invitation au tailnet.
4. L'installation de l'extension VPN et la connexion initiale restent interactives.
5. Une IP Tailscale et les logs réseau restent dans les échanges privés de l'équipe.

## Préparer la machine

Si Tailscale manque ou est déconnecté, utiliser le skill `setup-game` avec le profil distant :

- macOS : `./scripts/setup-macos.sh --all --remote-play`, puis `./scripts/doctor-macos.sh --remote-play` ;
- Windows : `.\scripts\setup-windows.ps1 -All -RemotePlay`, puis `.\scripts\doctor-windows.ps1 -RemotePlay`.

Attendre que l'utilisateur ait terminé la connexion dans l'application avant de reprendre. Les trois machines doivent ensuite afficher le même `git rev-parse --short HEAD`.

## Héberger

Le Mac mini de Zak peut héberger si Zak joue aussi dessus :

`./scripts/remote-test-macos.sh host --name "Zak"`

Le wrapper vérifie Tailscale, affiche l'IPv4 `100.x.y.z`, construit le jeu et lance l'hôte. L'hôte partage cette adresse uniquement avec Nils et Sean.

## Rejoindre

Sur Mac :

`./scripts/remote-test-macos.sh client --address "IP_TAILSCALE_HOTE" --name "Nils"`

Sur Windows :

`.\scripts\remote-test-windows.ps1 Client -Address "IP_TAILSCALE_HOTE" -Name "Sean"`

Le wrapper vérifie d'abord que l'hôte répond au niveau Tailscale, puis lance le test FishNet/Tugboat sur UDP `7770`.

## Verdict

Le test réussit lorsque les trois fenêtres affichent `AUTHENTICATED` et les trois noms. En cas d'échec, lire `Logs/ConnectionTest/` et suivre `docs/REMOTE_CONNECTION_TEST.md`. Ne pas prétendre que le duel jouable ou le transport Steam est déjà terminé.
