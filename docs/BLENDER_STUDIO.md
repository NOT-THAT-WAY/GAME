# Studio Blender intégré à GAME

Le dépôt `GAME` contient maintenant le studio compact sous
`tools/blender-agent-studio/`. Il ne faut pas cloner un second dépôt Blender à l'intérieur : le
contenu est déjà versionné dans ce dépôt, sans `.git` imbriqué et sans les assets binaires lourds.

## Initialisation d'une machine

Depuis la racine de `GAME`, Claude lance automatiquement cette initialisation au premier travail
Blender. Elle peut aussi être lancée manuellement :

```bash
python3 tools/blender-agent-studio/tools/bootstrap.py --configure
python3 tools/blender-agent-studio/workflows/tools/studio_readiness_check.py
```

Ces commandes détectent Blender, FFmpeg/ffprobe et écrivent uniquement la configuration ignorée du
studio. FFmpeg vient du setup machine : `./scripts/setup-macos.sh --install-tools` sur Mac,
`powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1 -InstallTools` sur Windows.
Le doctor le signale en avertissement tant qu'il manque. Blender lui-même reste installé à la main. Le coffre d'assets est optionnel. Pour réutiliser une source cataloguée, définir localement
`BLENDER_ASSET_VAULT` vers le coffre privé autorisé ; ne jamais ajouter les fichiers matérialisés à
Git.

## Utiliser Claude

Lancer Claude depuis la racine de `GAME` :

```text
Utilise $blender-production-studio pour créer un asset game-ready destiné à Unity.
```

Le skill est installé dans `.claude/skills/blender-production-studio/` et déclenché
automatiquement pour les tâches Blender, 3D, animation, rendu, lookdev et export Unity. Le skill
fait travailler l'agent dans `tools/blender-agent-studio/`, puis exige une validation avant de
copier un export dans `Assets/_Project/`.

Les fichiers de travail lourds restent dans `tools/blender-agent-studio/local_work/` et
`local_assets/`, ignorés par Git. Les masters éditables restent dans le coffre DVC/privé selon les
règles de GAME.

## Handoff vers Unity

Un export Blender ne devient pas automatiquement un asset gameplay. Après validation Blender :

1. exporter vers le dossier de travail local déclaré ;
2. réimporter et vérifier dans la version Unity de `config/toolchain.env` ;
3. enregistrer provenance, licence, budgets et cible ;
4. copier uniquement l'export runtime validé dans `Assets/_Project/<Feature>/` avec son `.meta` ;
5. exécuter le doctor et `scripts/validate-repository.sh` avant la PR.

Un `.blend`, un master PSD/DAW, un cache ou un rendu lourd ne doit jamais être committé dans le
repo GAME.
