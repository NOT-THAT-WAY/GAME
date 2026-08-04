# Instructions Claude Code — GAME

## Références du projet

- Lire `README.md`, `CONTRIBUTING.md`, `docs/PROJECT_RULES.md` et le document ciblé dans `docs/` avant de modifier le projet.
- `config/toolchain.env` est la source de vérité des versions partagées.
- Ne jamais mettre à jour Unity, un package, FishNet, Wwise ou Steam sur une seule machine.
- Ne jamais supprimer ou écraser des changements existants sans demande explicite.

## Initialisation d'une machine

Quand un utilisateur demande « initialise », « setup », « prépare la machine » ou une formulation équivalente, utiliser immédiatement le skill projet `setup-game` et exécuter ses vérifications. L'équipe travaillant depuis plusieurs lieux, le profil standard inclut Tailscale pour les tests distants. Ne pas répondre seulement avec une liste théorique.

Le setup standard n'installe ni DVC, ni Wwise Authoring, ni SDK Steam et ne configure aucun secret. Ces étapes ont leurs propres jalons. Wwise Authoring est réservé à Nils ; les autres postes consomment l'intégration et les SoundBanks versionnées dans le dépôt. La connexion initiale Tailscale reste interactive et propre à chaque membre.

## Git et collaboration

- Inspecter la branche et `git status --short` avant toute modification.
- Ne jamais travailler directement sur `main` : utiliser le skill `git-task` et créer une branche courte (`feat/`, `fix/`, `art/`, `audio/`, `data/`, `docs/` ou `chore/`).
- Le nom suit `TYPE/nom-court-en-minuscules` et le titre de PR reprend le même type (`feat: ...`, `fix: ...`, etc.).
- Ne jamais contourner le hook avec `--no-verify`, modifier le hook local ou pousser `main` depuis une autre interface.
- Livrer par pull request et attendre les contrôles `workflow-policy`, `validate` et `powershell-syntax`.
- Nils est l'intégrateur : ne pas demander automatiquement une revue à Zak ou Sean et ne jamais merger à leur place. Ils publient leur branche testée ; Nils décide du merge.
- Une scène, un prefab racine, un Work Unit Wwise ou un lot DVC ne possède qu'un éditeur déclaré à la fois.
- La cible joueur initiale est Windows x86_64 IL2CPP ; macOS Apple Silicon est une plateforme de développement. Ne pas ajouter une autre cible sans ADR et validation dédiée.

## Données et assets

- Code, scènes, configuration et documentation : Git.
- Binaires runtime approuvés, intégration Wwise et SoundBanks : Git LFS.
- Masters Blender/PSD/DAW, prises brutes et sources lourdes : DVC dans `ExternalAssets/`.
- Caches, `Library`, builds, secrets et préférences locales : jamais dans Git.
- Déplacer ou renommer un asset Unity depuis Unity afin de préserver son `.meta`.

## Validation

- macOS : `./scripts/doctor-macos.sh`.
- Windows : `powershell -ExecutionPolicy Bypass -File .\scripts\doctor-windows.ps1`.
- Contrat du dépôt : `./scripts/validate-repository.sh`.
- Une machine est prête quand son doctor affiche zéro erreur et que le dépôt reste propre après ouverture/fermeture de Unity.
- Pour lancer la connexion à trois, utiliser le skill `lan-test`.
- Si les membres sont sur des réseaux différents, utiliser `remote-test` au lieu de `lan-test`.
