# Stack technique et politique de versions

## Socle actif

| Élément | Version | Pourquoi maintenant |
|---|---:|---|
| Unity | `6000.3.20f1` | LTS actuelle, support prolongé et même éditeur sur Mac/Windows |
| URP | `17.3.0` | rendu compatible Metal/Windows ; renderer PC configuré en Forward+ |
| Input System | `1.20.0` | inputs explicites et tests multi-instance |
| Cinemachine | `3.1.7` | caméra du prototype sans framework maison |
| FishNet | `4.7.2` | hôte autoritaire, prédiction/réconciliation disponibles |
| Tugboat | inclus avec FishNet | sessions locales et LAN sans Steam |
| Multiplayer Play Mode | `2.0.2` | plusieurs joueurs dans l'éditeur |
| Multiplayer Tools | `2.2.10` | profils de latence/perte et métriques |
| Tailscale | client stable auto-mis à jour | relie les postes distants pendant le développement, hors du build |
| DVC | `3.x` | pointeurs Git vers les masters stockés hors GitHub |
| Git LFS | version installée par la plateforme | binaires de runtime nécessaires au build uniquement |

Toutes les versions sont exactes. Aucun membre ne clique sur « Update » isolément.

DVC est borné au major 3 dans `config/toolchain.env`. Son remote n'est pas une dépendance du runtime : un développeur réseau peut compiler sans télécharger les sources Blender ou DAW qui ne sont pas utilisées par le build.

Tailscale n'est ni un package Unity ni un transport livré aux joueurs. Il fournit uniquement une interface réseau privée aux postes de développement afin que Tugboat fonctionne entre plusieurs lieux. Sa connexion utilise des comptes individuels et aucune clé d'authentification n'entre dans le dépôt.

## Éléments volontairement différés

### Wwise `2025.1.4`

Wwise est bien la direction audio, mais son intégration modifie fortement le projet Unity et contient des binaires par plateforme. La documentation de l'intégration `2025.1.3` annonçait un maximum supporté de Unity 6.2 ; la version `2025.1.4` existe, mais sa combinaison avec Unity 6.3 doit être vérifiée sur un Mac et Windows avant diffusion aux trois postes.

Décision : une branche de compatibilité, un son minimal, un build sur chaque OS, puis déploiement général. L'audio Unity intégré peut servir quelques heures pour ne pas bloquer le prototype.

### Steamworks.NET `2025.164.1` + FishySteamworks `4.1.1`

L'ancien document citait FishyFacepunch. Ce dépôt est aujourd'hui archivé ; il ne fait donc pas partie de la stack. FishySteamworks est le transport Steam maintenu dans l'écosystème FishNet et s'appuie sur Steamworks.NET.

Décision :

- Tugboat pour le développement quotidien et la première session entre machines ;
- Tailscale autour de Tugboat lorsque les développeurs ne partagent pas le même réseau ;
- FishySteamworks pour le profil Steam après cette gate ;
- Multipass seulement si l'équipe a besoin d'exposer les deux transports simultanément dans la même build.

### Addressables

Addressables n'est pas nécessaire pour la salle grise et le pivot unique. L'ajouter maintenant multiplie les chemins de build, surtout avec Wwise. Il sera décidé avant la production de contenu, pas avant la validation du duel.

### Voix de proximité

La piste Steam Voice vers Wwise Audio Input reste un spike, pas un contrat confirmé. Il faut mesurer latence, coupure réseau, spatialisation et comportement hors Steam avant de figer l'architecture.

## Cibles de plateforme

- **Cible de sortie initiale : Windows x86_64**, build IL2CPP produit et validé sur Windows.
- **Développement : macOS Apple Silicon + Windows**.
- **Build Mac joueur : décision ultérieure**. Les plugins doivent néanmoins fonctionner dans l'éditeur macOS.
- Pas de Windows ARM natif à ce stade.

## Architecture réseau de départ

Le prototype utilise un listen-server à hôte autoritaire. L'hôte valide l'orientation discrète du pivot, les inputs, l'énergie, les collisions et plus tard le trésor. Les clients peuvent interpoler ou prédire les transitions, mais la grille logique demeure la source de vérité.

Profil réseau cible du premier playtest : environ `80 ms` RTT, `2 %` de perte et `20 ms` de jitter.

## Changer une version

Une mise à jour doit tenir dans une seule PR et modifier ensemble :

1. `config/toolchain.env` ;
2. `ProjectSettings/ProjectVersion.txt` si Unity change ;
3. `Packages/manifest.json` ;
4. `Packages/packages-lock.json` généré par Unity ;
5. le résultat des tests Mac + Windows ;
6. cette page si le contrat change.

## Références officielles

- [Unity 6000.3.20f1](https://unity.com/releases/editor/whats-new/6000.3.20f1)
- [Support des versions Unity 6](https://unity.com/releases/unity-6/support)
- [Unity CLI et installation des éditeurs](https://docs.unity.com/en-us/hub/use-unity-cli)
- [FishNet 4.7.2](https://github.com/FirstGearGames/FishNet/releases/tag/4.7.2)
- [Tugboat](https://fish-networking.gitbook.io/docs/fishnet-building-blocks/transports/tugboat)
- [Installation Tailscale](https://tailscale.com/docs/install)
- [FishySteamworks](https://fish-networking.gitbook.io/docs/fishnet-building-blocks/transports/fishysteamworks)
- [Steamworks.NET 2025.164.1](https://github.com/rlabrecque/Steamworks.NET/releases/tag/2025.164.1)
- [Wwise Unity Integration 2025.1.4](https://www.audiokinetic.com/en/public-library/2025.1.4_9062/?id=index.html&source=Unity)
- [Installation DVC sur macOS](https://dvc.org/doc/install/macos)
- [Installation DVC sur Windows](https://dvc.org/doc/install/windows)
- [Stockages distants DVC](https://dvc.org/doc/user-guide/data-management/remote-storage)
