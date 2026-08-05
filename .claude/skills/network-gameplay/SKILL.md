---
name: network-gameplay
description: Encadre toute modification du déplacement joueur, des murs ou pivots, des collisions, de la topologie du labyrinthe, des interactions ou de la connexion FishNet. Utiliser automatiquement dès qu'une tâche touche un état gameplay partagé, l'autorité réseau, la prédiction/réconciliation ou un test réseau dégradé.
---

# Modifier le gameplay réseau de GAME

Ce skill protège le contrat décrit dans `docs/adr/0004-authoritative-topology-and-ticks.md`. L'exécuter avant d'éditer du code, une scène ou une donnée qui peut modifier le mouvement d'un joueur, un mur, une collision ou l'état partagé du labyrinthe.

## Avant de modifier

1. Lire `docs/adr/0004-authoritative-topology-and-ticks.md`, `docs/PROJECT_RULES.md`, `docs/ROADMAP.md` et le protocole de playtest concerné.
2. Inspecter le code réellement appelé et classer chaque changement :
   - **cosmétique/local** : caméra, UI, audio, animation visuelle sans effet sur une règle ;
   - **autoritaire/partagé** : position, collision, mur, énergie, cooldown, interaction, KO, inventaire ou résultat de partie.
3. Si une décision produit est encore ouverte dans l'ADR, ne pas l'inventer. Documenter le choix demandé ou limiter la PR à ce qui reste valide quelle que soit l'option.
4. Traiter `PlayerMotor`, `PivotDirector` et les `MeshCollider` ajoutés par `MazePlaytestBuild` comme un smoke test historique. Ne pas étendre leur architecture client-authoritative ou pilotée par image.

## Invariants obligatoires

- Le client envoie une **intention** ; l'hôte décide. Il valide identité/état du joueur, identifiant de cible, portée, ligne de vue ou contact, direction, durée d'effort, énergie, cooldown, conflit et collision.
- Toute règle partagée avance sur le tick FishNet du serveur. `Time.time`, `Time.deltaTime`, `Update` et l'heure de réception locale sont réservés au visuel, à la caméra, à l'UI et aux autres effets sans autorité.
- Un mur mobile possède un identifiant entier stable et un état de transition au minimum équivalent à `wallId`, `fromState`, `toState`, `startTick`, `durationTicks` et `revision`. Sa pose logique est une fonction du tick, pas de la fréquence d'image.
- Les collisions autoritaires et les apparitions proviennent d'une topologie typée, versionnée et validée avec au minimum `schemaVersion`, IDs stables, `cellPitchMm`, `wallThicknessMm`, `wallHeightMm` et checksum. Les noms, pivots, transforms et triangles d'un FBX ne définissent jamais une règle réseau.
- Le déplacement réseau final consomme des commandes d'input par tick et utilise la prédiction/réconciliation FishNet (`Replicate`/`Reconcile`). Un `NetworkTransform` client-authoritative ne constitue pas une preuve M1.
- Les contrôles de jeu passent par des Input Actions partagées et doivent couvrir clavier/souris et manette. La lecture directe de `Keyboard.current` ou `Mouse.current` peut rester dans un outil local, pas devenir le contrat joueur.
- Le chargement ou la reconnexion restitue un snapshot cohérent : version de schéma, checksum de map, tick serveur, joueurs et transitions de murs avec leur révision.
- L'adresse Tugboat et, plus tard, un lobby Steam sont deux résolutions d'une même abstraction `ConnectionTarget`. Le gameplay ne connaît ni IP brute ni transport concret.
- Le code déterministe reste en C# testable sans scène ; les `NetworkBehaviour` adaptent transport, ownership et sérialisation aux frontières.

## Ordre de simulation à préserver

Pour chaque tick autoritaire : consommer les intentions valides, démarrer les transitions de murs, échantillonner la topologie et les collisions du tick, appliquer la politique explicite des chevauchements, simuler les joueurs, produire l'état autoritaire, puis réconcilier. L'interpolation cosmétique vient après et ne réécrit jamais cet état.

La conséquence d'un mur qui se referme sur un joueur reste une décision produit ouverte. Toute implémentation concernée doit d'abord obtenir et enregistrer la règle : rejet du mouvement, KO ou autre résultat explicite.

## Preuves minimales

Une PR réseau/gameplay fournit les tests proportionnés au risque :

1. tests EditMode du modèle pur : IDs, transitions aux bornes de ticks, révisions, validation d'intentions et checksum ;
2. test PlayMode dans un profil gris minimal à un pivot et deux joueurs ;
3. arrivée tardive pendant une rotation et reconnexion sur snapshot ;
4. comparaison à 30, 60 et 120 FPS ;
5. profil `80 ms RTT / 2 % perte / 20 ms jitter` pour tout comportement partagé ;
6. Mac et Windows IL2CPP au même commit avant de déclarer une modification réseau terminée ;
7. preuve que client et serveur partagent checksum, tick logique et résultat de collision.

La map 16x16 reste un test d'intégration et de rendu. Elle ne remplace pas le profil gris déterministe.

## Refuser ces raccourcis

- synchroniser un transform de mur chaque image ;
- faire tourner le collider avec `Time.deltaTime` ou à partir de l'arrivée d'un message ;
- accepter une position ou une durée d'effort décidée par le client ;
- ajouter un `MeshCollider` au décor FBX pour régler une collision gameplay ;
- dériver un identifiant réseau d'un nom de GameObject, d'un ordre de hiérarchie ou d'un index trouvé dans la scène ;
- coder Tugboat, Steam ou une adresse directement dans le gameplay ;
- déclarer « autoritaire » parce que le RPC s'exécute sur l'hôte sans valider l'intention ;
- étendre Wwise, Steam, voix, matchmaking ou contenu final pour contourner une preuve de duel manquante.

## Verdict avant publication

Résumer dans la PR : état partagé touché, autorité, tick, IDs/schéma, décision de collision, snapshot/reconnexion, tests réalisés et limites restantes. Si une ligne obligatoire n'a pas de preuve, ne pas déclarer le comportement réseau terminé.
