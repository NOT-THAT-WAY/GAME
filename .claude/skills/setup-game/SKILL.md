---
name: setup-game
description: Initialise et vérifie une machine macOS ou Windows pour le projet GAME. Utiliser automatiquement lorsque l'utilisateur demande d'initialiser, setup, configurer, préparer ou intégrer cette machine au projet.
---

# Initialiser une machine GAME

Exécuter le workflow ; ne pas se limiter à le réciter.

## Garde-fous

1. Se placer à la racine retournée par `git rev-parse --show-toplevel`.
2. Afficher la branche et `git status --short`. Ne jamais effacer des changements existants.
3. Ne jamais changer les versions de `config/toolchain.env` pendant un setup.
4. Ne pas installer Wwise Authoring, intégrer Wwise ou ajouter Steam. Wwise Authoring est réservé à Nils. Tailscale est autorisé comme outil de test distant, jamais comme dépendance du build.
5. Ne configurer DVC que si l'utilisateur fournit déjà une URL non secrète. Ne jamais demander ni placer un token dans une commande, Git ou le chat.
6. Ne pas committer ni pousser pendant le setup, sauf demande explicite distincte. Ne jamais pousser directement sur `main`.

## Détecter la plateforme

- macOS : `uname -s` retourne `Darwin`.
- Windows natif ou Git Bash : utiliser les scripts PowerShell du dépôt.
- WSL : arrêter avant installation et demander de cloner le projet sur un disque Windows local hors OneDrive, puis de relancer Claude depuis PowerShell. Unity Hub Windows ne doit pas travailler dans un clone `\\wsl$`.
- Toute autre plateforme : expliquer qu'elle n'est pas prise en charge par le setup équipe.

## macOS

1. Si Homebrew manque, donner le lien `https://brew.sh` et attendre son installation interactive.
2. Pour cette équipe distribuée, exécuter `./scripts/setup-macos.sh --all --remote-play`.
3. Si Unity Hub s'ouvre, demander uniquement de terminer Unity Apple Silicon dans la version de `config/toolchain.env`. Wwise et Steam ne font pas partie de cette étape.
4. Si Tailscale s'ouvre, attendre que l'utilisateur accepte l'extension VPN, utilise son propre compte et rejoigne l'invitation de l'équipe. Ne jamais utiliser de clé d'authentification dans le terminal.
5. Après les installations interactives, exécuter `./scripts/setup-macos.sh --remote-play`, puis `./scripts/doctor-macos.sh --remote-play`.

## Windows

1. Depuis PowerShell, vérifier `winget`, Git et GitHub CLI. Si le dépôt est déjà cloné, exécuter :

   `powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1 -All -RemotePlay`

2. Si Unity Hub s'ouvre, demander de terminer la version exacte avec Windows Build Support IL2CPP.
3. Attendre que l'utilisateur se connecte à Tailscale avec son propre compte et accepte l'invitation, sans clé partagée.
4. Relancer :

   `powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1 -RemotePlay`

5. Exécuter :

   `powershell -ExecutionPolicy Bypass -File .\scripts\doctor-windows.ps1 -RemotePlay`

## Verdict

1. Vérifier si `Packages/packages-lock.json` existe.
   - S'il manque sur le Mac pilote, indiquer que le premier import doit encore être fait sur une branche dédiée.
   - S'il manque sur la machine d'un autre membre, ne pas ouvrir Unity : le pilote doit d'abord merger le lockfile.
2. Vérifier de nouveau `git status --short`.
3. Résumer les erreurs réelles et les avertissements attendus. DVC, Wwise et Steam peuvent rester en avertissement avant leurs jalons.
4. Ne déclarer la machine intégrée que si le doctor affiche zéro erreur. Après le lockfile, une ouverture/fermeture de Unity doit aussi laisser Git propre.
5. Quand la machine est intégrée, utiliser `remote-test` si les membres sont dans des lieux différents et `lan-test` uniquement sur le même réseau ; ne pas prétendre que le gameplay du duel existe déjà.
