# Registre des assets, dépendances et licences

Ajouter une ligne avant l'import dans Unity. Stocker la preuve de licence dans l'emplacement privé convenu par l'équipe ; ne pas committer de facture ou donnée personnelle.

| ID | Asset / plugin | Source | Version/date | Licence | Lot DVC / sortie | Plateformes vérifiées | Preuve | Responsable | Statut |
|---|---|---|---|---|---|---|---|---|---|
| DEP-001 | FishNet | GitHub FirstGearGames | 4.7.2 | MIT | package Unity | Mac/Windows à tester | dépôt/release | équipe | intégré |
| DEP-002 | Unity URP | Unity Registry | 17.3.0 | Unity Companion | package Unity | Mac/Windows à tester | manifest | équipe | intégré |
| DEP-003 | Wwise | Audiokinetic | 2025.1.4 | à enregistrer selon budget/projet | `WwiseProject/` | gate Mac/Windows requise | portail projet | à attribuer | différé |
| TOOL-001 | DVC | Iterative | 3.x | Apache-2.0 | remote privé à choisir | Mac/Windows à tester | documentation officielle | Nils + Zak | préparé |

Préfixes conseillés : `ART`, `AUD`, `NAR`, `UI`, `DEP`, `TOOL`. Le lot DVC d'un master suit `ExternalAssets/<Discipline>/<ID>/` ; la colonne indique aussi les exports Unity/Wwise.

Statuts : `proposé`, `claim`, `prototype seulement`, `validé`, `à remplacer`, `retiré`. Pendant un `claim`, l'issue liée précise le pilote et une échéance ; un claim expiré peut être repris après contact.
