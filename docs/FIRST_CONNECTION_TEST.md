# Premier test de connexion à trois

Objectif : afficher les trois noms dans la même liste, sans Steam, Wwise ni gameplay. Cela valide les installations, le build, FishNet/Tugboat, l'adressage LAN et les pare-feux avant tout système plus complexe.

## Préconditions

- les trois machines sont sur le même réseau local, sans VPN ;
- le premier import Unity et le `packages-lock.json` ont été mergés ;
- chaque machine a fait `git pull --ff-only`, puis son script `setup` et son `doctor` ;
- Unity est fermé avant le build en ligne de commande ;
- le port UDP `7770` est libre.

Le coffre d'assets externe n'est pas nécessaire pour ce test : il ne contient encore aucun master requis.

## 1. Choisir l'hôte

Commencer avec un Mac pour éviter la règle de pare-feu Windows lors du tout premier essai :

```bash
./scripts/first-test-macos.sh host --name Nils
```

Le script vérifie le dépôt, génère la scène locale ignorée par Git, construit l'application et affiche l'IP probable de l'hôte. Relever cette IP, par exemple `192.168.1.42`.

## 2. Connecter le second Mac

```bash
./scripts/first-test-macos.sh client --address 192.168.1.42 --name Sean
```

## 3. Connecter Windows

Dans PowerShell :

```powershell
.\scripts\first-test-windows.ps1 Client -Address 192.168.1.42 -Name Zak
```

Le premier build Windows est IL2CPP et peut être long. Les suivants peuvent réutiliser le binaire :

```powershell
.\scripts\first-test-windows.ps1 Client -Address 192.168.1.42 -Name Zak -SkipBuild
```

## Succès

Les trois fenêtres affichent `AUTHENTICATED` et les trois noms. Noter dans l'issue de test : commit, OS, rôle, IP privée, durée et résultat. Ne jamais publier l'IP dans une issue publique.

## Si la connexion échoue

1. Vérifier que les trois ports sont `7770` et que l'adresse n'est ni `127.0.0.1` ni une adresse VPN.
2. Confirmer que le ping entre machines fonctionne si le routeur l'autorise.
3. Sur Windows, autoriser l'exécutable sur les **réseaux privés** au premier lancement.
4. Désactiver temporairement le VPN ; ne pas désactiver globalement le pare-feu.
5. Lire `Logs/ConnectionTest/` sur la machine concernée.
6. Inverser l'hôte :

   ```powershell
   .\scripts\first-test-windows.ps1 Host -Name Zak
   ```

7. Tester d'abord hôte + client sur une même machine avec `127.0.0.1`, puis revenir au LAN.

Une fois ce test vert dans les deux sens Mac ↔ Windows, la scène réseau peut évoluer vers le déplacement et le pivot. Steam reste une gate ultérieure.
