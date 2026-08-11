# Blocage Windows IL2CPP — handshake de version FishNet

La cible joueur initiale déclarée dans `config/toolchain.env` est
`PLAYER_TARGET=Windows-x86_64-IL2CPP`. **Sur cette cible, aucun player ne se connecte, pas même à
lui-même.** Le serveur éjecte son propre client local environ une seconde après la connexion. Le
même commit compilé en Mono2x se connecte normalement.

Ce document consigne le constat et son contournement. Il ne pose pas de diagnostic : la cause exacte
n'est pas établie.

## Symptôme

Sur un player Windows IL2CPP lancé avec `--game-role host`, le serveur démarre, lie son port UDP,
spawne l'autorité de mur, puis casse la connexion du client local :

```text
[GAME-CONNECTION] Démarrage serveur sur le port 7770...
[GAME-CONNECTION] Connexion client à 127.0.0.1:7770...
Local client is started for Tugboat.
[GAME-M1] server_connections=1.
Size of -6 is invalid.
  FishNet.Serializing.Reader:IsPossibleAllocationAttack(Int32, Boolean)
  FishNet.Serializing.Reader:ReadStringAllocated()
  FishNet.Managing.Server.ServerManager:ParseReceived(ServerReceivedDataArgs)
Connection Id [0] Address [127.0.0.1] has been kicked for being on FishNet version . Server version is 4.7.2.
Local client disconnect reason: RemoteConnectionClose.
[GAME-M1] server_connections=0.
```

La version annoncée par le client est vide dans le message de kick, et le lecteur du serveur refuse
une longueur de chaîne négative. Aucun joueur n'est spawné : le heartbeat reste à
`server=True client=False players=0` indéfiniment. À l'écran, le testeur voit le décor sans
personnage et sans terrain jouable, sans aucun message d'erreur.

## Ce qui est établi

| Profil | Backend | Date | Résultat |
| --- | --- | --- | --- |
| `maze` | IL2CPP | 2026-08-06 | kick, `Logs/MazePlaytest/player-host-20260806-114004.log` |
| `maze` | IL2CPP | 2026-08-10 17:38 et 17:42 | kick |
| `maze` | Mono2x | 2026-08-10 17:45 | `Authenticated as Zak`, roster à 1 |
| `m1` | IL2CPP | 2026-08-10 17:51 | kick |
| `m1` | Mono2x | 2026-08-10 17:55 | `Authenticated as ZAK_HOST`, session à deux joueurs |

La seule variable qui change le résultat est le backend de scripting. Ce n'est ni un profil, ni un
commit, ni une régression du squelette M1 : le blocage précède de quatre jours l'arrivée de M1.

## Pourquoi personne ne l'avait vu

`M1PlaytestBuild.BuildMac` et `MazePlaytestBuild.BuildMac` ne forcent aucun backend, et
`ProjectSettings.asset` ne déclare pas de backend Standalone — Unity retombe donc sur Mono2x. **Toute
la base de preuves macOS, y compris les gates réseau automatisées, est du Mono.** Seul le chemin
Windows force IL2CPP. Le blocage était structurellement invisible tant que Windows n'était pas
réellement lancé.

## Contournement

```text
Menu Unity : GAME > M1 Playtest > Build Windows (Mono)
```

En ligne de commande :

```powershell
& "C:\Program Files\Unity\Hub\Editor\6000.3.20f1\Editor\Unity.exe" -batchmode -quit `
  -projectPath . -executeMethod NotThatWay.Game.Editor.M1PlaytestBuild.BuildWindowsMono `
  -logFile .\Logs\m1-build-windows-mono.log
```

La sortie va dans `Builds/M1PlaytestMono/Windows/` afin de ne pas écraser le build IL2CPP. L'entrée
force `Mono2x` explicitement puis restaure le backend précédent : elle ne dépend pas du réglage local
de la machine et ne le laisse pas modifié.

## Ce que le contournement ne remplace pas

- Il ne livre pas la cible joueur. `PLAYER_TARGET` reste `Windows-x86_64-IL2CPP` et rien n'est
  décidé ici.
- **Il n'exerce pas la raison d'être de `FixedTrigonometry`.** La trigonométrie entière CORDIC existe
  pour que côté, bras de levier et contact rendent le même verdict sous Mono et sous IL2CPP. Une
  session Mono ne prouve rien sur cette égalité.
- Il ne dit rien de macOS IL2CPP, jamais construit.

Toute mesure Windows produite avec ce build doit donc être annoncée comme une mesure Mono.

## Pistes non vérifiées

Le message vient du désérialiseur, sur la chaîne de version envoyée à l'authentification. Les
suspects habituels sur ce chemin, par ordre de coût :

1. le stripping managé — `ProjectSettings.asset` porte `stripEngineCode: 1` et un
   `managedStrippingLevel` vide, donc la valeur par défaut IL2CPP s'applique ; tester
   `Disabled` sur `Standalone` isole cette hypothèse en un build ;
2. la codegen FishNet sous IL2CPP : un sérialiseur généré absent ou stripé produirait exactement une
   longueur de chaîne incohérente à la lecture ;
3. un `link.xml` préservant les types de `FishNet.Serializing` si le point 1 confirme.

Aucune de ces pistes n'a été testée. Le point 1 est le moins cher et doit passer en premier.

## Ce que ça bloque

- le test humain Windows, `scripts/human-test-windows.ps1`, sur son chemin IL2CPP ;
- toute session `lan-test` ou `remote-test` incluant un poste Windows sur la cible officielle ;
- la preuve Windows/IL2CPP listée comme manquante dans [GRAYBOX_M1.md](GRAYBOX_M1.md), qui n'est plus
  seulement absente : elle est en échec.
