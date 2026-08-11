# Blocage Windows IL2CPP — handshake de version FishNet

La cible joueur initiale déclarée dans `config/toolchain.env` est
`PLAYER_TARGET=Windows-x86_64-IL2CPP`. **Sur les builds testés avant le garde correctif, aucun player
ne se connecte, pas même à lui-même.** Le serveur éjecte son propre client local environ une seconde
après la connexion. Le même commit compilé en Mono2x se connecte normalement.

Ce document consigne le constat, le correctif de compatibilité en attente de preuve Windows et le
contournement Mono. La cause exacte dans la chaîne IL2CPP reste à attribuer tant que le paquet brut
n'a pas été observé sur le PC.

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

Au moment du constat, `M1PlaytestBuild.BuildMac` et `MazePlaytestBuild.BuildMac` ne forçaient aucun
backend et `ProjectSettings.asset` n'en déclarait aucun pour Standalone : Unity retombait sur
Mono2x. **Toute la base de preuves macOS, y compris les gates réseau automatisées, était donc du
Mono.** Le réglage Standalone Mono est désormais explicite pour que les scopes de build puissent
forcer IL2CPP puis restaurer exactement le fichier ; les entrées Windows continuent de forcer
IL2CPP. Le blocage était structurellement invisible tant que Windows n'était pas réellement lancé.

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

## Correctif IL2CPP à vérifier

FishNet encode les longueurs signées en zig-zag. Pour la version ASCII `4.7.2`, longue de cinq
octets, le marqueur attendu est `0x0A`. La valeur lue par le serveur, `-6`, correspond exactement au
marqueur `0x0B` : le bit de signe est passé à un entre l'écriture et la lecture.

`FishNetVersionHandshakeGuard` est maintenant branché comme couche intermédiaire sur les trois
profils générés (`connection`, `maze` et `m1`). Il ne désactive pas le contrôle de version : il ne
corrige `0x0B` vers `0x0A` que si le paquet a la taille exacte attendue, l'identifiant FishNet
`Version` et le payload exact compilé `4.7.2`. Une autre version ou un autre paquet reste inchangé.

Le même garde inspecte les deux frontières et écrit un marqueur sans donnée personnelle :

```text
[GAME-FISHNET-HANDSHAKE] ... backend=il2cpp stage=client-outgoing ...
[GAME-FISHNET-HANDSHAKE] ... backend=il2cpp stage=server-incoming ...
```

Sur le PC Windows, depuis une branche propre :

```powershell
.\scripts\verify-il2cpp-handshake-windows.ps1
```

Le script reconstruit le player M1 IL2CPP, vérifie que `ProjectSettings.asset` est identique avant
et après, lance un host headless, attend l'authentification et écrit le hash du binaire ainsi que les
marqueurs dans `Logs/WindowsIl2CppHandshake/<session-id>/summary.json`. Il ne rend `PASS` que si les
frontières `client-outgoing` et `server-incoming` ont toutes deux été observées en IL2CPP.

Interprétation :

- `repaired ... stage=client-outgoing` : l'encodage IL2CPP a produit `0x0B` ; le garde l'a corrigé
  avant Tugboat ;
- sortie valide puis `repaired ... stage=server-incoming` : la mutation arrive dans le transport ;
- `valid` aux deux frontières mais kick `-6` : les octets sont bons et le lecteur IL2CPP est fautif ;
- `PASS` avec authentification et roster à un : le blocage immédiat est levé, mais les scénarios M1
  complets restent à exécuter avant de valider l'égalité Mono/IL2CPP.

## Diagnostic écarté ou restant

Quand le backend Standalone passe à IL2CPP, Unity `6000.3.20f1` résout le niveau de stripping vide à
`Minimal`. À ce niveau, l'appel du handshake est direct (`ClientManager` appelle
`Writer.WriteString`) et ne dépend pas d'un sérialiseur FishNet généré. Le stripping ou un `link.xml`
ne sont donc plus la première hypothèse ; les ajouter avant la capture brute masquerait le signal.

Si le garde confirme des octets valides aux deux frontières sans authentification, le prochain essai
isolera le lecteur. S'il corrige bien le paquet mais qu'une sérialisation ultérieure casse, il faudra
traiter l'encodeur zig-zag IL2CPP en amont plutôt que multiplier les exceptions protocole.

## Ce que ça bloque

- tant que la commande de preuve ci-dessus n'a pas rendu `PASS`, le test humain Windows,
  `scripts/human-test-windows.ps1`, sur son chemin IL2CPP ;
- toute session `lan-test` ou `remote-test` incluant un poste Windows sur la cible officielle ;
- la preuve Windows/IL2CPP listée comme manquante dans [GRAYBOX_M1.md](GRAYBOX_M1.md) : le dernier
  essai est en échec et le correctif reste non validé sur cette plateforme.
