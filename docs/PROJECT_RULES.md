# Contrat du projet et règles du dépôt

Ce document répond à trois questions : **quel jeu construit-on**, **qu'est-ce qui est autorisé maintenant** et **qu'est-ce qui protège réellement `main`**. Il s'applique à Zak, Sean, Nils et aux assistants lancés dans le dépôt.

## Produit visé

`GAME` est un jeu de labyrinthe PvP compétitif en vue subjective, prévu à terme pour **2 à 12 joueurs**. La première preuve de fun reste volontairement petite : un duel 1v1 autour d'un pivot de labyrinthe que les joueurs poussent, contrent et utilisent tactiquement.

Contrat technique actuel :

- cible joueur initiale : **Windows x86_64**, build IL2CPP produit sur Windows ;
- postes de développement : **macOS Apple Silicon** et **Windows x86_64** ;
- réseau : listen-server à hôte autoritaire avec FishNet/Tugboat ;
- Tailscale : réseau privé de test entre développeurs, jamais une dépendance du jeu livré ;
- rendu : URP, profil PC ;
- `main` doit toujours s'ouvrir et rester constructible avec la version exacte de Unity enregistrée.

Un build Mac sert au développement et aux tests internes. Une sortie macOS, Linux, mobile, console ou WebGL n'est pas promise à ce stade.

## Ce que l'équipe fait maintenant

| Niveau | Autorisé | Condition |
|---|---|---|
| quotidien | code gameplay, tests, documentation, blockout, petits prefabs et scènes additives | branche courte, PR, CI verte |
| coordonné | scène partagée, prefab racine, `ProjectSettings`, package, transport réseau, shader global | un éditeur déclaré et une PR dédiée |
| croisé | réseau, input, build, plugin natif, audio, chemins ou import d'asset | validation Mac **et** Windows avant de déclarer terminé |
| assets runtime | PNG/FBX/WAV et autres exports nécessaires au build | licence enregistrée, `.meta` présent, Git LFS, budget respecté |

L'issue indique un pilote, un binôme, un testeur et les scènes/prefabs/lots revendiqués. Les affinités de profil orientent le départ sans créer de territoire permanent.

## Ce qui attend une gate

- DVC et son stockage distant : au premier master Blender/PSD/DAW lourd ou irremplaçable ;
- Wwise : après le premier gameplay distant, avec Nils comme seul poste Authoring au départ ;
- Steamworks/FishySteamworks : après la preuve distante Tailscale/Tugboat ;
- Addressables : avant la production de contenu, uniquement si le volume le justifie ;
- serveur dédié, matchmaking, voix de proximité, anti-cheat et builds de release : après validation du duel.

Une gate différée ne doit pas être installée « pour préparer » sur une seule machine. Son ouverture prend une branche dédiée, un résultat minimal et une preuve sur les plateformes concernées.

## Interdictions permanentes

- ne pas pousser directement vers `main` et ne pas contourner les hooks avec `--no-verify` ;
- ne pas mettre à jour Unity ou un package isolément ;
- ne pas committer `Library`, caches, logs, builds, secrets, tokens, IP d'équipe ou données personnelles ;
- ne pas mettre de master éditable lourd dans Git, même sous LFS ;
- ne pas ouvrir le projet depuis iCloud, OneDrive, Dropbox, un partage réseau ou WSL ;
- ne pas désactiver le pare-feu ni exposer le port UDP `7770` sur Internet ;
- ne pas intégrer un asset externe ou IA sans provenance, licence et restrictions ;
- ne pas merger une PR dont le résultat n'est pas testable par une autre personne.

## Protection réelle de `main`

Le dépôt privé de l'organisation est actuellement sur GitHub Free. La protection de branche/ruleset serveur n'est donc pas disponible pour ce dépôt privé. Les protections actives sont :

1. le setup configure les hooks partagés ; le hook refuse un push local vers `main` et valide le contrat du dépôt ;
2. les branches et titres de PR suivent le même type : `feat`, `fix`, `art`, `audio`, `data`, `docs` ou `chore` ;
3. GitHub Actions vérifie la politique, le dépôt et la syntaxe PowerShell avec des droits en lecture seule ; seules les Actions appartenant à GitHub sont autorisées et GitHub exige leur SHA complète ;
4. GitHub n'autorise que le squash merge et supprime la branche après merge ;
5. la règle humaine est une PR verte dont Nils, intégrateur du dépôt, décide le squash merge ; une revue supplémentaire est facultative et ciblée selon le risque.

Un hook local reste techniquement contournable et les trois membres ont actuellement le rôle GitHub Admin. La discipline branche + PR + décision de Nils est donc une règle d'équipe, pas une frontière de sécurité absolue. Quand les rôles seront stabilisés, conserver un ou deux Owners maximum et donner aux autres le droit Write suffira pour le travail quotidien.

## Choisir le bon type de branche

| Préfixe | Résultat principal |
|---|---|
| `feat/` | comportement jouable, réseau ou outil visible |
| `fix/` | correction d'un comportement incorrect |
| `art/` | visuel, animation, UI ou export artistique |
| `audio/` | son, musique ou intégration Wwise |
| `data/` | DVC, schéma, catalogue ou migration |
| `docs/` | documentation uniquement |
| `chore/` | dépendance, réglage, CI ou maintenance |

Une PR ne mélange pas une mise à jour de dépendances, une resérialisation de scène et une feature gameplay. Si ces changements sont tous nécessaires, les livrer dans cet ordre par PR séparées.

## Définition de terminé

Une tâche est terminée lorsque le résultat attendu est démontré, le dépôt reste propre après Unity, les contrôles adaptés passent, un autre membre peut reproduire le test et la documentation/ADR change avec tout contrat partagé. Un avertissement sur une gate différée est acceptable ; une ligne `[FAIL]` du doctor ne l'est pas.
