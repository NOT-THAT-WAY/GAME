# Graybox M1 — contrat exécutable

Le banc M1 n'est pas le labyrinthe 16×16. Il part de
`Assets/_Project/Maze/GrayboxTopology2x2.v1.json` et construit au runtime une arène 2×2 uniquement
avec des primitives Unity. C'est un instrument de mesure réseau : le présenter comme « le jeu »
fausse l'avis de la personne qui le lance.

## Ce qui est déjà verrouillé

- checksum runtime obligatoire : `031f7d…d03aa` ;
- copie runtime immuable des dimensions, IDs, états, pivots, ouvertures et spawns ;
- sept murs à `BoxCollider`, dont `wallId=10` mobile autour de `pivotId=100` ;
- aucun FBX et aucun `MeshCollider` ;
- deux poses à 90°, calculées depuis les millimètres de la topologie ;
- état A : trajet entre spawns en trois arêtes ; état B : trajet direct en une arête ;
- spawns reliés et périmètre fermé hors des deux ouvertures dans les deux états ;
- volume balayé conservateur en arithmétique entière pour produire le même verdict sous Mono et
  Windows IL2CPP, y compris aux tangences ;
- transition atomique : destination occupée, rupture de connectivité, périmètre ouvert ou joueur
  dans l'arc produisent un code stable sans modifier l'état ni le collider ;
- reset exact vers les états initiaux ;
- collisions sol/murs isolées sur `GameplayWorld` (layer 8), joueurs sur `Player` (layer 9) ;
  seuls monde↔joueur et joueur↔joueur produisent des contacts parmi ces layers, tandis que
  `InteractionQuery` et `VisualOnly` n'en produisent aucun ;
- position et rotation de l'arène supportées, échelle monde différente de 1 refusée explicitement ;
- preuve PlayMode sur deux hiérarchies identiques, les colliders/layers, les deux sens de rotation,
  un rebuild sur la même instance et trois resets complets.

La convention du graybox est directe : grille `+X,+Y` vers monde Unity `+X,+Z`. La conversion
historique retournée du FBX 16×16 ne s'applique pas à cette scène.

## Rendu du banc

Le rendu ne change aucune règle, mais un banc illisible ne produit pas d'avis exploitable.

- Chaque objet rendu porte un matériau URP explicite, généré dans
  `Assets/_GeneratedLocal/M1Materials/` et sérialisé dans la scène. URP 17 n'expose plus de matériau
  par défaut hors éditeur : une primitive laissée au défaut du pipeline sort **magenta** dans un
  player alors que compilation, tests et logs restent verts.
- `M1PlaytestBuild` refuse à la génération tout renderer sans matériau ou dont le shader n'est pas
  celui du pipeline, y compris sur le prefab joueur et le ciel.
- Le joueur est `Assets/_Project/Player/PersoBouleRigged.fbx`, strictement visuel : layer
  `VisualOnly`, aucun collider, hauteur vérifiée dans `[1,30 ; 1,45] m` face à la capsule simulée de
  1,40 m. La collision reste le seul `CharacterController`.
- `M1PlayerAppearance` teinte chaque personnage d'après l'identifiant de connexion partagé par le
  serveur, donc identique sur toutes les fenêtres, et masque le corps de son porteur en vue
  première personne en gardant son ombre.
- Le décor lointain, le sol d'horizon et le socle sont sur `VisualOnly` sans collider. Ils ne créent
  aucune surface jouable : franchir les deux ouvertures sud fait toujours quitter le sol de l'arène,
  comportement inchangé et toujours à trancher.
- Contrôle visuel obligatoire avant tout build montré à un humain :
  `./scripts/m1-preview-macos.sh --player`, captures dans `Logs/M1Playtest/`. Cette option capture
  aussi l'écran du build macOS via
  `M1ScreenshotProbe`, refusé hors Development : l'éditeur résout des matériaux que le player ne
  résout pas, donc seule cette capture prouve l'image livrée.

## Ce qui n'est pas encore revendiqué

- le profil à 60 Hz reste une valeur de mesure M1, pas un réglage produit accepté ;
- aucune conséquence mur/joueur autre qu'un code de refus paramétrable ;
- aucun preset produit d'effort, d'énergie ou de cooldown choisi ;
- aucune preuve visuelle Windows/IL2CPP ni essai réseau distant, dégradé ou de longue durée ;
- aucune réintégration de ce socle dans le labyrinthe 16×16 ;
- aucun verdict humain sur la taille, la lisibilité ou le feel.

Le joueur prédit/réconcilié, le mur autoritaire FishNet et le late join local sont implémentés et
testés. Les absences ci-dessus séparent les décisions humaines encore ouvertes des invariants déjà
automatisés.

## Gates locales

```bash
./scripts/unity-tests-macos.sh all
python3 tests/topology-fixtures/test-fixtures.py
./scripts/validate-repository.sh
```

La gate PlayMode exige exactement un sol et sept colliders de mur actifs, tous des `BoxCollider`.
