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
| DVC | `3.x`, gate à ouvrir | pointeurs Git vers les masters qui ont produit les deux FBX actuels |
| Git LFS | version installée par la plateforme | binaires de runtime nécessaires au build uniquement |

Toutes les versions sont exactes. Aucun membre ne clique sur « Update » isolément.

DVC est borné au major 3 dans `config/toolchain.env` et reste hors de l'onboarding générique. Deux exports FBX sont désormais versionnés alors que leurs masters ne le sont pas : choisir et tester le remote est donc une gate P0 avant de modifier ou transmettre ces sources. Le remote n'est pas une dépendance du runtime ; un développeur réseau peut toujours compiler sans hydrater les sources Blender ou DAW.

Tailscale n'est ni un package Unity ni un transport livré aux joueurs. Il fournit uniquement une interface réseau privée aux postes de développement afin que Tugboat fonctionne entre plusieurs lieux. Sa connexion utilise des comptes individuels, aucune clé d'authentification n'entre dans le dépôt, et le propriétaire confirme une offre compatible avec l'usage commercial visé avant le prochain playtest structuré.

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

Les valeurs `WWISE_ENABLED`, `STEAM_TRANSPORT_ENABLED` et `UNITY_CI_BUILDS_ENABLED` restent à `0` dans `config/toolchain.env`. Une PR de gate les change uniquement avec l'intégration et ses preuves, afin d'éviter un état « à moitié installé » différent sur chaque poste.

## Architecture réseau de départ

Le produit utilise un listen-server à hôte autoritaire selon [l'ADR 0004](adr/0004-authoritative-topology-and-ticks.md). Les clients transmettent des intentions ; l'hôte valide et simule joueurs, murs, énergie et collisions sur le tick FishNet. La topologie logique versionnée demeure la source de vérité, et les clients peuvent prédire/réconcilier ou interpoler sans modifier le résultat.

Le code actuel est encore un smoke test : `PlayerMotor` est client-authoritative, `PivotDirector` anime localement transform et collider par image, et `MazePlaytestBuild` dépend de `MeshCollider` issus du FBX. Ne pas étendre ces chemins. La migration commence par une scène grise à un pivot, un schéma avec IDs/checksum, les transitions `startTick`/`durationTicks`/`revision`, puis `Replicate`/`Reconcile` pour le joueur.

La connexion reçoit à terme un `ConnectionTarget` : adresse/port pour Tugboat aujourd'hui, lobby après la gate Steam. Le gameplay ne dépend pas du transport choisi.

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
