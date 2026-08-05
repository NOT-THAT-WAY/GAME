# Pulsed — Index des assets de référence (2026-06-10, après tri des générations)

> Règle : chaque asset a un domaine de validité. Ne jamais utiliser un asset hors de son
> domaine (les refs sont générées par IA → variance inter-vues). Positions exactes :
> `audits/pulsed-object-map.md` (v2). Tranches : **toutes lisses** (décision Sliz) —
> ignorer tout élément type bouton/clip sur un bord, quelle que soit l'image.

| Fichier | Sert à | Ignorer / ne PAS utiliser pour |
|---|---|---|
| `00_front_uncropped.png` | **Silhouette + ratio (1,653) + layout face** — vérité principale, c'est sur elle que la carte v2 est mesurée | la couleur exacte (légère dominante chaude) |
| `01_front_canonical.png` | Layout face (vérité historique, concorde avec 00), design des contrôles en plus net | silhouette/ratio (croppée DANS le device) |
| `02_back_canonical.png` | Volume dos, silhouette secondaire (1,666) | layout PCB (canon = closeup-02), clips visibles sur son contour haut |
| `03_side_clean_canonical.png` | Galbes/roundovers seulement | toute cote ou position (device incliné, T/H apparent faussé) |
| `04_side_right_canonical.png` | **Profil canon** : T/H total 0,278, crown, **renflement DORSAL ergonomique à y≈15 %** (la bosse = le dos qui se prend en main, PAS la molette — corrigé 2026-06-10) | lecture en miroir (côté plat = face −Y, côté bosse = dos +Y) ; positions y de la face |
| `05_top_edge_canonical.png` | Crown convexe + seam de la tranche haute | **les 2 clips argentés (à ignorer — tranche lisse)** |
| `06_bottom_edge_canonical.png` | Tranche basse : USB-C ≈46 %, trapèze ≈62 % (concorde closeup-10) | — |
| `07_screen_best_single.png` | Contenu écran allumé (waveform teal) pour le matériau émissif | géométrie/positions |
| `08_material_neutral.png` | **Couleur/matériau de référence** (lumière neutre, violet améthyste fidèle, PCB par transparence) | — |
| `09_hero_back_top_34.png` | Validation volume 3/4 dos | **clips argentés tranche haute (à ignorer)**, layout PCB |
| `close-ups/` (01→10) | Détails par zone, voir `close-ups/INDEX.md` | — |

Rejetée et **supprimée** (2026-06-10) : `MACRO_molette_closeup-11.jpeg` — roue traversant le
bord gauche + pin blanc sur la tranche = contredisait `01_front`/`00_front` (molette = disque
cranté axe horizontal, entièrement sur la face, bords intacts). Remplacement : macro M1
spécifiée dans `audits/pulsed-asset-prompts-v2.md` §v2.1, pas encore générée.
