# Audit de Blender Team Studio — distribution compacte

Date : 4 août 2026.

## Verdict

La copie compacte est prête pour un clone privé d’équipe. Elle fournit une méthode commune, huit
types de projets, des profils de validation, un skill agent, une application locale, 18 workflows
contrôlés et le catalogue vérifié du corpus — sans transporter les binaires.

Une publication publique reste conditionnée au choix d’une licence racine et à la revue des droits
des sources cataloguées. Le catalogue n’accorde aucun droit de redistribution.

## Périmètre compris

L’audit source a couvert environ 7,7 Go, 14 178 fichiers, 45 `.blend`, 32 `.blend1`, des milliers de
références visuelles, des tutoriels, scripts, projets et quatre dépôts imbriqués. Les 45 scènes
principales ont été ouvertes avec Blender 5.1.1 et auto-exécution désactivée. Les enseignements
transférables ont été séparés des réglages propres à Kimi, Pulsed, FL Studio ou une campagne.

## Résultat de la compaction

| Mesure | Résultat |
|---|---:|
| chemins binaires catalogués et vérifiés | 12 251 |
| contenus uniques SHA-256 | 12 115 |
| images / vidéos / audio / géométrie | 12 045 / 105 / 10 / 91 |
| scènes Blender et backups décrits | 77 |
| volume logique non embarqué | 7 820 498 266 octets |
| volume unique non embarqué | 7 009 145 417 octets |
| doublons non répétés | 811 352 849 octets |
| binaires inclus dans Git | 0 |
| liens symboliques inclus | 0 |
| sous-modules / règles LFS | 0 / 0 |
| taille du noyau avant métadonnées Git | moins de 20 Mio |

Le catalogue a été régénéré après détection de cinq captures modifiées dans le coffre pendant
l’audit, puis les 12 251 chemins ont été relus : taille et SHA-256 correspondent tous. Le rapport
est `asset-vault-verification.json` et n’expose pas le chemin du coffre.

## Architecture retenue

- Git suit code, connaissances, standards, prompts, catalogues, contrats, hashes et verdicts.
- `local_assets/` reçoit uniquement les contenus matérialisés et vérifiés depuis un coffre autorisé.
- `local_work/<project-id>/` contient `.blend`, textures, caches, rendus et exports.
- `projects/team/<project-id>/` contient le brief, le contrat, les gates et la revue partageables.
- Le budget de distribution refuse 43 familles d’extensions lourdes, les symlinks, LFS, sous-modules,
  chemins personnels et fichiers hors budget.
- L’application affiche les assets et scènes catalogués même lorsqu’ils sont absents et ne propose
  jamais de bouton d’ouverture sur un fichier virtuel.

## Couverture fonctionnelle et maturité

| Domaine | État honnête | Gate final |
|---|---|---|
| audit de scène | stable | diagnostic sourcé |
| modélisation d’asset | contrat stable | mesh évalué, identité, export/réimport |
| image/référence vers 3D | automation expérimentale | revue humaine + validation asset |
| Unity, Unreal, Godot, glTF | contrat stable | rapport d’import dans la cible déclarée |
| rig et articulation | automation préliminaire | limites, poids, collisions et déformations |
| clips et boucles | contrat stable | contacts, seam/root motion, playblast, réimport |
| environnement/procédural | contrat stable | navigation, collision, exclusions, performance |
| still/cinématique | stable | physique, contact sheet, preview complète, probe |
| GLB | automation stable | réimport indépendant ; moteur cible si applicable |
| FBX/USD et autres cibles | contractualisé | import réel obligatoire |

Les budgets ne sont jamais universels : ils sont remplis par projet selon moteur, plateforme,
distance, caméra et usage. Le style neutre est le défaut ; Drumboiii reste un profil optionnel qui ne
peut pas contredire fonction, physique, cible ou performance.

## Défauts corrigés

- Les workflows batch ne sont plus injectables via MCP.
- Le workflow FL Studio spécifique est marqué historique et désactivé dans l’application.
- Les opérations génériques acceptent `STUDIO_PARAMS`; l’ancien nom reste un fallback.
- Les sorties de travail ne peuvent pas écraser une source ni entrer dans Git.
- Les profils jeux exigent une preuve Unity, Unreal, Godot ou glTF adaptée, pas un simple preset
  d’axes.
- Le validateur final contrôle gates, fichiers de preuve, hashes, statuts, rôles, import cible,
  droits et revue humaine.
- Le smoke Blender ne dépend plus d’un produit ou d’un `.blend` privé.
- Les chemins personnels ont été tokenisés dans les cas d’étude et éliminés du noyau actif.

## Contrôles exécutés

- parsing de tous les JSON de profils, catalogues, schémas et workflows ;
- parsing Python et validation JavaScript ;
- tests des huit scaffolds et d’une livraison finale complète ;
- pipeline tutoriel FFmpeg ;
- validateur officiel du skill ;
- application HTTP : UI et 12 endpoints principaux répondent sans asset binaire ;
- schéma Docker Compose valide ;
- Blender 5.1.1 : trois mouvements caméra, hover causal, shot, audit profond, visibilité, graphe
  spatial, correction bornée, deux rigs lumière, six gates A/B, trois rendus, export GLB et réimport
  indépendant de deux meshes avec parent hors collection ;
- budget compact, absence de binaire, symlink, LFS, sous-module et chemin machine.

## Limites et suite

Ce dépôt ne remplace pas les SDK et importeurs des moteurs. Les gates Unity, Unreal et Godot doivent
être exécutés dans le projet cible réel. Les automations de rig et de génération 3D sont marquées à
leur niveau de maturité actuel. Les packs binaires doivent être distribués séparément avec version,
hashes et droits. Toute nouvelle connaissance est ajoutée progressivement sans relever un ancien
verdict sans nouvelle preuve.
