# Test à trois depuis des réseaux différents

Ce profil permet à Zak, Sean et Nils de tester FishNet/Tugboat depuis trois lieux différents. Tailscale crée un réseau privé virtuel entre les machines ; aucun port de box, serveur cloud ou changement du code réseau n'est nécessaire pour ce test de développement.

Ce n'est pas le réseau final du jeu. Tailscale reste un outil d'équipe externe au build ; Steam/FishySteamworks viendra après validation de la connexion et du premier gameplay.

## Tailnet utilisé maintenant

La fenêtre Tailscale du Mac pilote affiche un tailnet GitHub personnel. L'appartenance à l'organisation GitHub `NOT-THAT-WAY` ne donne donc pas automatiquement accès à ce réseau.

Pour démarrer vite, Nils conserve ce tailnet et crée [deux invitations à usage unique](https://tailscale.com/docs/features/sharing/how-to/invite-any-user) : console Tailscale → **Users** → **Invite external users** → **Copy invite link** → rôle **Member**. Envoyer un lien différent à Zak et Sean par canal privé. Ne pas publier ces liens dans GitHub, Claude ou un salon partagé.

Le [plan Personal](https://tailscale.com/pricing) accepte actuellement jusqu'à six utilisateurs, mais il est annoncé pour un usage non commercial. Si le développement devient commercial, passer au plan Standard — actuellement 8 USD par utilisateur et par mois — ou abandonner Tailscale au profit du profil Steam. Un [tailnet GitHub d'organisation](https://tailscale.com/docs/integrations/identity/github) serait un réseau séparé ; il n'est pas nécessaire pour le premier test.

## Ce qui reste manuel une seule fois

L'administrateur invite les deux autres comptes. Chaque membre :

1. utilise son propre compte ;
2. ouvre son lien à usage unique et choisit **Sign up with GitHub** ;
3. autorise l'extension VPN de macOS ou Windows ;
4. termine la connexion dans l'application Tailscale.

Ne jamais partager un compte ni placer une clé d'authentification Tailscale dans Git, Claude, Discord ou une commande. Le plan Tailscale choisi doit correspondre à l'usage réel de l'équipe.

## Installation assistée

Après avoir cloné le repo, lancer Claude à sa racine :

```text
claude
> initialise l'environnement pour jouer à distance
```

Claude installe ou vérifie Tailscale avec les autres outils, ouvre l'application si nécessaire, puis attend la connexion interactive. Commandes directes équivalentes :

```bash
# macOS
./scripts/setup-macos.sh --all --remote-play
./scripts/doctor-macos.sh --remote-play
```

```powershell
# Windows
.\scripts\setup-windows.ps1 -All -RemotePlay
.\scripts\doctor-windows.ps1 -RemotePlay
```

La machine est prête quand le doctor affiche `0 erreur` et une IPv4 Tailscale `100.x.y.z`.

## Avant chaque session

Les trois membres exécutent :

```bash
git switch main
git pull --ff-only
git rev-parse --short HEAD
```

Les trois valeurs doivent être identiques. Fermer Unity avant le build en ligne de commande et vérifier que Tailscale indique `Connected`.

## Option simple : Zak héberge sur le Mac mini

Le Mac mini n'est pas un serveur dédié : Zak héberge **et joue** dans la même application. Il doit rester allumé, connecté à Tailscale et garder le jeu ouvert pendant la session.

Sur le Mac mini :

```bash
./scripts/remote-test-macos.sh host --name "Zak"
```

Le script affiche une adresse `100.x.y.z`. Zak la transmet uniquement à Nils et Sean.

Sur le Mac de Nils ou Sean :

```bash
./scripts/remote-test-macos.sh client --address "100.x.y.z" --name "Nils"
```

Sur Windows :

```powershell
.\scripts\remote-test-windows.ps1 Client -Address "100.x.y.z" -Name "Sean"
```

Le premier lancement Windows peut demander d'autoriser GAME sur les réseaux privés. Ne pas désactiver le pare-feu globalement.

## Succès

Les wrappers valident deux niveaux :

1. le client atteint l'hôte via `tailscale ping` ;
2. FishNet/Tugboat authentifie les trois joueurs sur UDP `7770`.

Les trois fenêtres doivent afficher `AUTHENTICATED` et le roster Zak/Sean/Nils. Noter le commit, les OS, les rôles et le résultat dans l'issue privée sans copier les IP ni les logs bruts.

## Dépannage

1. Relancer le doctor avec le profil `--remote-play` ou `-RemotePlay`.
2. Vérifier que les trois comptes voient leurs machines dans le même tailnet.
3. Confirmer que le wrapper client réussit son `tailscale ping`.
4. Autoriser GAME uniquement sur les réseaux privés du pare-feu Windows.
5. Vérifier que l'hôte a gardé son application ouverte et utilise aussi le port `7770`.
6. Lire `Logs/ConnectionTest/` localement.
7. Inverser temporairement l'hôte pour distinguer un problème de machine d'un problème de transport.

Si Tailscale fonctionne mais Tugboat échoue, conserver les logs localement et ouvrir une issue `fix/` avec le commit, l'OS et le rôle, sans identifiant réseau personnel.
