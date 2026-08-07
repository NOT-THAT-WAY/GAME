# Gestion des données

Cette politique évite que GitHub, le coffre d'assets, les postes locaux et les services de test deviennent quatre versions contradictoires du projet.

## Carte des données

| Donnée | Source de vérité | Partage | Conservation |
|---|---|---|---|
| code, réglages, scènes, prefabs, documentation | GitHub privé | branches + PR | historique Git |
| binaires nécessaires à Unity/Wwise | Git LFS, avec budget surveillé | clone/pull Git | tant que référencés par une release supportée |
| masters art/audio/IA et références lourdes | remote DVC privé — bucket Cloudflare R2 `ntw-assets`, préfixe `game/` | `dvc pull/push` | versioning objet + sauvegarde séparée |
| SoundBanks runtime approuvées | Git LFS sous `Assets/StreamingAssets/Audio/GeneratedSoundBanks/` | clone/pull Git | tant que la version du jeu les référence |
| `Library`, caches, builds locaux, SoundBanks intermédiaires | poste local | jamais | supprimables/reconstructibles |
| builds de test et logs partagés | artefacts de release/CI dédiés plus tard | lien à durée limitée | 30 à 90 jours selon utilité |
| secrets, tokens, clés Steam/cloud/Tailscale | gestionnaire de secrets ou variables locales | accès nominatif | rotation et révocation |
| licences, factures, contrats, preuves nominatives | espace administratif privé | accès restreint | selon obligations ; Git ne garde qu'une référence |
| retours et télémétrie de playtest | espace de recherche restreint | données minimisées/pseudonymisées | durée définie avant collecte |

## Principes obligatoires

1. **Une source de vérité.** Une donnée n'est pas maintenue manuellement à deux endroits. Les exports Unity sont reconstruits depuis un master identifié.
2. **Identifiant stable.** Chaque asset reçoit un ID (`ART-PIVOT-001`, `AUD-FOOTSTEP-001`) conservé lors des renommages visuels.
3. **Provenance avant usage.** Source, auteur, licence, preuve et restrictions sont enregistrés avant l'import.
4. **Accès individuel.** MFA, aucun compte ou mot de passe partagé, droits minimaux et révocation documentée.
5. **Pas de secret dans Git.** Même un dépôt privé n'est pas un coffre à secrets. En cas de fuite : révoquer/rotater d'abord, nettoyer ensuite.
6. **Versionner n'est pas sauvegarder.** Le remote DVC possède une deuxième copie et un test de restauration.
7. **Collecter le minimum.** Aucun nom réel, voix brute, IP ou identifiant de plateforme n'est conservé sans objectif, information des testeurs et durée de suppression définie.

## Cycle de vie

```text
proposé → provenance validée → master DVC → export runtime → revue → utilisé
                                      ↘ remplacé/archivé avec raison
```

Une migration de format ou de schéma se fait dans une PR dédiée, avec une note de migration et une preuve d'ouverture Mac/Windows. Une suppression d'asset doit d'abord confirmer qu'aucun prefab, scène, événement Wwise ou build supporté ne le référence.

## Données du jeu

| Type | Contrat de départ |
|---|---|
| valeurs de design partagées | `ScriptableObject` ou JSON validé, versionné sous `Assets/_Project/<Feature>/Data/` |
| état réseau vivant | mémoire uniquement, serveur autoritaire, messages explicitement versionnés si le protocole change |
| préférences locales | `Application.persistentDataPath`, jamais dans le dépôt |
| sauvegarde joueur future | format portant un `schemaVersion`, migrations testées et écriture atomique |
| télémétrie future | événements nommés, schéma documenté, identifiant pseudonyme et consentement adapté |

Éviter les valeurs de gameplay copiées dans plusieurs prefabs. Une valeur partagée possède un propriétaire et un emplacement canonique ; le code consomme cette donnée sans la dupliquer. Les IDs fonctionnels restent stables même si le nom affiché ou le fichier change.

La première version ne construit ni backend de compte ni base de données : aucune donnée persistante n'est nécessaire au test LAN. Ces frontières permettent d'en ajouter plus tard sans mélanger sauvegardes, configuration et état réseau.

## Coffre d'assets

Le remote DVC s'appelle `assets` sur toutes les machines ; `doctor-macos.sh` et `doctor-windows.ps1` refusent tout autre nom dès qu'un pointeur existe. Sa définition — URL, endpoint, région, profil — vit dans `.dvc/config.local`, jamais dans Git : `GAME` est un dépôt public, et un endpoint publié désigne la cible du coffre de façon irréversible. Les clés passent par un profil local, pas par la ligne de commande.

Les secrets d'organisation `R2_ACCESS_KEY_ID` et `R2_SECRET_ACCESS_KEY`, avec les variables `R2_ENDPOINT` et `R2_BUCKET`, servent uniquement aux workflows GitHub Actions. Ils ne configurent aucun poste et ne déplacent aucun asset.

L'ordre est contraint : `dvc add`, puis `dvc push`, puis `git commit` du pointeur, puis `git push`. Publier un pointeur avant que le contenu soit dans le coffre produit une référence que personne ne peut résoudre. `scripts/assets-*.sh` le rappelle après chaque `push`.

L'état de couverture du coffre — quels masters sont réellement sécurisés et lesquels ne le sont pas — est tenu dans [ASSETS.md](ASSETS.md).

## Travail local

- cloner le dépôt sur un disque local, hors iCloud/OneDrive/Dropbox ;
- ne jamais partager `Library` entre machines ou branches ;
- faire `git pull --ff-only` avant `dvc pull` ;
- vérifier `git status` et `dvc status` avant de commencer et avant de livrer ;
- ne pas synchroniser tous les masters si la tâche n'en a pas besoin ;
- les noms de fichiers restent ASCII, sans espace, avec casse stable sur Mac et Windows.

## Contrôle mensuel léger

- taille Git/LFS et croissance du remote ;
- assets sans propriétaire, licence ou export utilisé ;
- comptes et clés encore nécessaires ;
- capacité à restaurer un lot DVC sur une machine propre ;
- logs/playtests arrivés à leur date de suppression ;
- versions de formats et dépendances toujours compatibles Mac/Windows.

Cette base peut ensuite évoluer vers un catalogue automatisé ou un DAM sans changer les frontières de stockage.
