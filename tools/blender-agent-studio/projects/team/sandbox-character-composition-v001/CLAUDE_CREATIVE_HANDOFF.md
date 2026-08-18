# Handoff créatif Claude — personnage sandbox

## Point de départ

Ouvrir la copie de présentation suivante, jamais le master d'animation :

`local_work/sandbox-character-composition-v001/work/sandbox_character_composition_v001_c.blend`

La scène `BAS_SANDBOX_CHARACTER_COMPOSITION_V001_REVIEW` est une baseline technique neutre. Elle
est prête pour une passe de direction artistique, mais ce n'est pas une proposition de style final.
Le master source `sandbox_character_SB_Idle_master.blend` reste immuable, hash
`864807e970705bf44a1c3dcbcfaac85102458917a5c8ccec90f5f36728590464`.

Avant de modifier, enregistrer une nouvelle copie explicite, par exemple
`sandbox_character_composition_claude_v001.blend`. Ne pas écraser le fichier `_c.blend`.

## Carte de la scène

| Collection | Statut | Usage |
|---|---|---|
| `..._CHARACTER_LOCKED` | verrouillée P0-P2 | 10 objets originaux, rig et Actions ; ne pas modifier en place |
| `..._STAGE_EDITABLE` | libre | cyclorama neutre et matériau du décor |
| `..._LIGHTING_EDITABLE` | libre | key, fill et rim séparées par rôle |
| `..._CAMERAS_EDITABLE` | hero libre, contrôles à conserver | caméra hero 64 mm plus face/profil orthographiques |
| `..._GUIDES` | conserver | target personnage et focus visage séparés |

La scène contient aussi un Text datablock `BAS_SANDBOX_CHARACTER_COMPOSITION_V001_CLAUDE_HANDOFF`.

## Ce qui est verrouillé

- noms, hiérarchie, transforms, géométrie, poids et Actions du personnage ;
- `SB_Idle`, images 1-60 inclusives à 30 fps, root immobile et pieds plantés ;
- orientation faciale `-Y`, hauteur `1,34 m`, support réel à `Z=0` ;
- sources Unity et master d'animation ; aucun export runtime dans cette passe ;
- caméras face/profil comme vues de contrôle, même si le plan hero est redessiné.

Pour explorer un look personnage, ne pas modifier les matériaux partagés dans
`CHARACTER_LOCKED`. Créer une variante de matériau ou une scène/collection lookdev séparée avec le
préfixe du projet. Un changement de silhouette ou de proportions appartient à un nouveau projet
`game-asset`, pas à cette composition.

## Libertés créatives

Claude peut proposer et itérer sur :

- intention visuelle et storytelling du décor ;
- palette, fond, matériau du cyclorama et accessoires de présentation ;
- positions, tailles, températures et ratios key/fill/rim ;
- position et focale de la caméra hero, espace négatif et frame hero de la boucle ;
- profondeur de champ, seulement après validation du nouveau cadrage ;
- variantes de lookdev non destructives du personnage.

Bloom, grain, motion blur, glare et FX restent une finition. Ils ne doivent pas masquer les pieds,
une silhouette coupée, un clipping ou une mauvaise séparation des bras.

## Baseline mesurée à préserver ou améliorer

- 60/60 images dans le safe frame ;
- couverture verticale `0,765974–0,778627` ;
- couverture horizontale maximale `0,500332` ;
- offset centre absolu maximal `(0,006828 ; 0,018834)` ;
- marges minimales : gauche `0,244961`, droite `0,251730`, bas `0,098179`, haut `0,123194` ;
- caméra/personnage : clearance minimale `5,110044 m`, aucun clipping ;
- semelles à `Z=0` et root à l'identité.

Les seuils de réception restent dans `technical-contract.json`. Une composition créative peut être
asymétrique, mais elle doit garder tout le personnage et le contact au sol lisibles sur la boucle,
ou déclarer explicitement un nouveau contrat avant l'itération.

## Références à regarder avant de créer

- baseline : `local_work/.../renders/final/final/neutral-design-baseline.png` ;
- évolution A → C : `local_work/.../renders/final/comparison-attempt-a-vs-final-c.png` ;
- six poses hero : `local_work/.../renders/final/contact-sheet-hero-poses.png` ;
- face/profil : `local_work/.../renders/final/contact-sheet-controls.png` ;
- lumière key → key+fill → complète : `local_work/.../renders/final/contact-sheet-lighting.png` ;
- boucle x4 : `local_work/.../renders/final/sb-idle-neutral-loop-x4.mp4`.

## Boucle de travail recommandée

1. Lire `brief.json`, `technical-contract.json` et ce handoff.
2. Dupliquer `_c.blend` vers une copie Claude déclarée.
3. Écrire une intention créative observable en une phrase.
4. Changer une seule catégorie : décor, caméra, lumière ou lookdev.
5. Comparer le même frame et la même résolution ; trois essais maximum par catégorie.
6. Rejouer la boucle entière et contrôler face/profil avant tout polish.
7. Lancer la validation de cadrage :

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background --factory-startup <copie-claude.blend> \
  --python projects/team/sandbox-character-composition-v001/scripts/validate_composition_scene.py \
  -- projects/team/sandbox-character-composition-v001/evidence/composition-validation-claude.json
```

8. Régénérer les gates avec `render_composition_evidence.py` seulement après PASS.

## Décisions créatives encore ouvertes

- monde diégétique ou studio abstrait ;
- chaleur/froideur de la palette et degré de contraste ;
- style matière du personnage sans changement destructif du runtime ;
- image hero exacte dans la phase de respiration ;
- cadrage centré mascotte ou composition narrative asymétrique ;
- éventuelle cible finale : revue interne, key art ou future présentation Unity.

Le handoff s'arrête volontairement ici : les contraintes techniques et physiques sont réglées ; le
choix de goût, de récit et de style appartient maintenant à Claude puis à la revue humaine.
