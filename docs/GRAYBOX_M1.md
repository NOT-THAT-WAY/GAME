# Graybox M1 — contrat exécutable

Le banc M1 n'est pas le labyrinthe 16×16. Il part de
`Assets/_Project/Maze/GrayboxTopology2x2.v1.json` et construit au runtime une arène 2×2 uniquement
avec des primitives Unity.

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

## Ce qui n'est pas encore revendiqué

- aucun taux de tick concret tant que DEC-01 n'est pas accepté ;
- aucune conséquence mur/joueur autre qu'un code de refus paramétrable ;
- aucun preset d'effort choisi ;
- aucun joueur prédit/réconcilié ni adaptateur FishNet ;
- aucune preuve Windows, IL2CPP, late join ou profil réseau ;
- aucun verdict humain sur la taille, la lisibilité ou le feel.

Ces absences séparent les décisions humaines encore ouvertes du code pur déjà testable. Les étapes
suivantes ajoutent le modèle de transition par tick, puis les commandes joueur et enfin FishNet.

## Gates locales

```bash
./scripts/unity-tests-macos.sh all
python3 tests/topology-fixtures/test-fixtures.py
./scripts/validate-repository.sh
```

La gate PlayMode exige exactement un sol et sept colliders de mur actifs, tous des `BoxCollider`.
