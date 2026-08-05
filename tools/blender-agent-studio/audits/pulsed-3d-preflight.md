# Pulsed — Pre-flight 3D (Phase 0)

> Audit de couverture des references avant modélisation. Brief : `Pulsed — 3D Modeling Brief (Blender MCP)`.
> Date : 2026-06-10 · Blender 5.1.1 via MCP · Analyste : Claude (Opus 4.8)

---

## 0.1 — Connexion

| Check | Résultat |
|---|---|
| Serveur MCP Blender | ✅ répond (get_scene_info + execute_blender_code OK) |
| Version Blender | **5.1.1** |
| Fichier ouvert | `${LEGACY_WORKSPACE_ROOT}/Pulsed_3D_model.blend` ⚠️ |
| Unités | METRIC, scale_length 1.0 |
| Scène | Défaut : Cube / Light / Camera (à nettoyer en Phase 1) |

⚠️ **Conflit de fichier** : le .blend ouvert est dans `~/unrecorded/` (parent), mais un second `Pulsed_3D_model.blend` existe dans `~/unrecorded/Blender/` (le dossier projet). Deux fichiers distincts → risque de sauvegarder au mauvais endroit. **À trancher en Phase 1 : "Save As" dans le dossier projet recommandé.**

---

## 0.2 — Inventaire & interprétation des assets

Dossier : `assets/` (4 canoniques) + `assets/close-ups/` (10 macros + INDEX.md). Pas de `video.mp4`, pas de `dimensions.md`.

> **Nature des refs** : set photoréaliste **généré par IA** (higgsfield, 2026-06-03, cf. INDEX.md). Conséquence directe : cohérence inter-vues non garantie au niveau du détail (PCB, silkscreen, micro-features varient d'une image à l'autre). La règle de priorité ORTHO > CLOSEUP > VIDEO_FRAME > PERSPECTIVE du brief devient essentielle, zone par zone.

| Fichier | Rés. | Type | Ce qu'on y voit | Fiable pour modéliser |
|---|---|---|---|---|
| `01_front_canonical.png` | 960×576 ⚠️ basse rés. | ORTHO front | Face avant complète, plein cadre (device bord à bord). Layout : wordmark *Pulsed* haut-centre, logo *U.* haut-droit, molette crantée haut-gauche, écran centré-gauche en retrait, slider gain vertical à droite de l'écran, SYNC rond bas-gauche, slider horizontal bas-centre, D-pad bas-droit | Proportions front (ratio 1.667), positions de tous les contrôles, empreintes. **Source de vérité layout face avant** |
| `02_back_canonical.png` | 1920×1072 | ORTHO back (flottant, légère perspective possible) | Dos complet, PCB entier visible à travers coque, vis de coins, connecteurs tranche haute et basse visibles par transparence | Silhouette dos, rayons de coins, position vis, bombé du dos |
| `03_side_clean_canonical.png` | 1376×768 | ORTHO side (un seul côté — **gauche** d'après la molette qui dépasse) | Profil complet : épaisseur, galbe de la coque arrière, molette qui affleure/dépasse de la tranche, profil des contrôles en silhouette, ligne de joint | **Seule source de profondeur fiable.** Ratio hauteur:épaisseur ≈ 4.4:1 |
| `07_screen_best_single.png` | 1153×681 | ORTHO front, écran ON | Même layout que 01, écran allumé : UI waveform teal (« Default », « 10.2 Hz »), bezel lumineux | Ratio écran exact, zone émissive, matériau écran. Numérotation à trous (04/05/06 absents → un set canonique plus large existe probablement) |
| `closeup-01_hero-front-3q.jpeg` | 5504×3072 | PERSPECTIVE ¾ | Objet entier ¾ haut-gauche : rebord de coque surélevé, faceplate en retrait, tous contrôles, tranche basse avec 2 connecteurs, seam coque | **Ref d'identité primaire** (INDEX). Validation volume/profondeur, relations faceplate/rim |
| `closeup-02_hero-back-internals.jpeg` | 4800×3584 | ORTHO back (serré) | PCB haute rés., vis, connecteurs tranches haute/basse par transparence | Détail dos ; **ancre choisie pour le PCB** (texture/géo simplifiée) |
| `closeup-03_macro…screen-gain-dpad` | 5056×3392 | CLOSEUP | Coin haut-droit : encastrement écran (~2 mm), slot gain embossé, poignée blanche, logo U., LEDs rouges sous coque | Profondeurs écran + gain slider, finition faceplate |
| `closeup-04_macro-dpad` | 5056×3392 | CLOSEUP | D-pad : croix grise mate, 4 flèches triangulaires embossées, dôme central convexe, puits cruciforme à congés, jeu ~1 mm | **Vérité D-pad** (forme, chanfreins, creux) |
| `closeup-05_macro-sync-button` | 5056×3392 | CLOSEUP | Bouton SYNC : cylindre bas bombé, texte SYNC embossé, anneau-puits dans coque, silkscreen LOW BATT, départ du slider horizontal, coin de coque | **Vérité SYNC** + construction coin bas-gauche |
| `closeup-06_macro-gain-slider-scale` | 5056×3392 | CLOSEUP | Slider gain : slot capsule embossé, fente noire, poignée cylindrique blanche à sommet concave, **échelle graduée embossée à droite du slot**, connecteur blanc interne visible bord droit | **Vérité slider gain** (profondeurs, échelle) |
| `closeup-07_macro…screen-edge` | 5056×3392 | CLOSEUP (quasi frontal) | Même zone à plat : proportions slot/ticks, bord écran surélevé fin, silkscreen CACO/TC8US598U, bras haut D-pad | Cotes relatives zone écran/gain/D-pad |
| `closeup-08_macro-pcb-interior` | 5056×3392 | CLOSEUP MATERIAL | PCB en biais à travers coque : puces, condensateurs ; tranche basse avec 2 connecteurs métal ; molette visible en haut par transparence | Matériau translucide + densité PCB. Layout PCB ≠ 02 (incohérence IA, voir conflits) |
| `closeup-09_macro-corner-shell-screwboss` | 5056×3392 | CLOSEUP MATERIAL | Coin : **bossage de vis cylindrique transparent**, épaisseur de paroi (~2 mm), ligne de joint avec recouvrement, congés internes, câbles bruns routés, élément crème allongé (batterie ?) | **Vérité construction coque** : seam, épaisseur, bossages |
| `closeup-10_macro-bottom-port-usbc` | 5056×3392 | CLOSEUP I/O | Tranche basse frontale : **USB-C métal centré(-gauche)** en découpe arrondie + **port secondaire trapézoïdal multi-broches à sa droite** ; au fond la face avant (SYNC à gauche, D-pad à droite) confirme l'orientation | **Vérité I/O** + calibration d'échelle (USB-C ≈ 8.94 mm) |

---

## 0.3 — Rapport de couverture zone par zone

| Zone | Refs disponibles | Confiance | Ce qui manque | Criticité du gap |
|---|---|---|---|---|
| **Volume global / shell** | 01 (front), 02 (back), 03 (side G), hero-01 (¾), 09 (construction coin) | **Haute** | Ortho top & bottom dédiées ; second côté | **Mineur** (dérivable, voir 0.4) |
| **Écran** | 01, 07 (ON), macros 03/07 | **Haute** | Rien de bloquant ; ratio exact à mesurer en px | Mineur |
| **Molette (haut-gauche)** | hero-01 (face), 03_side (profil, dépasse de la tranche), 08 (transparence) | **Moyenne** | Macro dédiée nette : cran exact, largeur de fente dans la tranche, relation faceplate/tranche | **Dégrade** |
| **D-pad** | closeup-04 (parfait) + 03/07 | **Haute** | — | — |
| **Bouton SYNC** | closeup-05 (parfait) | **Haute** | — | — |
| **Slider gain vertical** | closeup-06 + 07 (parfaits) | **Haute** | — | — |
| **Slider horizontal** | hero-01, fond de 05 et 10, bord de 04 | **Moyenne-haute** | Macro dédiée (extrémité droite du rail jamais vue de près) | Mineur |
| **Ports / tranche basse** | closeup-10 (parfait), 02, 08 | **Haute** | — | — |
| **Tranche haute** | Par transparence dans 02/closeup-02 (connecteurs internes, 2 languettes blanches) + hero-01 (tabs) | **Faible** | Vue dédiée : ces features sont-elles des boutons/switch externes ou des éléments internes vus à travers ? | **Dégrade** |
| **Tranche droite** | hero-01 (perspective), bord de 03/06/07 | **Faible-moyenne** | Ortho côté droit (symétrie supposée, sans molette) | **Dégrade** (hypothèse de symétrie raisonnable) |
| **Échelle / dimensions** | Aucune cote fournie | — | L×H×P réelles en mm | **Dégrade** (calibrable via USB-C, voir 0.4) |
| **Matériaux / finition** | Excellents : translucidité (toutes), épaisseur (09), contrôles mats (04/05/06), écran (07) | **Haute** | Ref sous lumière neutre (set entier en lumière chaude/crème → teinte exacte du violet incertaine) | Mineur |
| **Dos / PCB interne** | 02, closeup-02, 08 | **Haute** (silhouette) | Layouts PCB incohérents entre vues (refs IA) → le PCB sera **simplifié + texturé**, pas modélisé puce à puce | Mineur (décision de scope à valider) |

### Conflits détectés (refs IA — à trancher par règle de priorité, pas en silence)

1. **Layout PCB** : composants/silkscreen diffèrent entre `02_back_canonical`, `closeup-02` et `closeup-08`. → Ancre proposée : `closeup-02` (la plus nette). Impact faible si PCB texturé.
2. **Ordre des ports tranche basse** : `closeup-10` (vue dédiée) : USB-C au centre(-gauche), port trapézoïdal à droite — cohérent avec `closeup-02` une fois miroité. `hero-01` est ambigu (connecteurs internes vus par transparence). → **closeup-10 fait foi.**
3. **Tranche haute** : languettes/tabs visibles dans 02 et hero-01, mais nature indéterminée (switch ? caches ? bossages de moule ?). → Hypothèse : 2 petits tabs en relief, pas de contrôle fonctionnel. **À confirmer.**
4. **Molette** : présente face (hero-01) + profil débordant (03_side) + transparence (08) — cohérent avec une molette type Game Boy affleurant par la tranche gauche, mais aucune macro. Forme exacte des crans = hypothèse.
5. **`01_front` plein cadre** : le device touche les bords de l'image (crop). Les coins extrêmes de la silhouette sont à vérifier contre `02_back` (qui, lui, a de l'air autour).

---

## 0.4 — Stratégies de comblement (avant toute demande)

| Gap | Stratégie de dérivation | Confiance résultante |
|---|---|---|
| Ortho top/bottom absentes | Profondeur + galbe pris sur `03_side` ; longueur sur `01/02` ; coins croisés avec hero-01. La tranche basse a déjà sa vérité (closeup-10) | Bonne |
| Second côté (droit) | Symétrie du profil gauche **sans** la molette ; vérif contre hero-01 (le seul à montrer le flanc droit) | Moyenne+ (hypothèse marquée) |
| Échelle absolue | **Calibration USB-C** : largeur normalisée 8.94 mm dans closeup-10 → cote de la tranche basse → propagation via ratios des orthos. Estimation préliminaire (gabarit GBA-like, ratios mesurés 1.667 et 4.4) : **≈ 160 × 96 × 22 mm**, soit 16 × 9.6 × 2.2 BU (1 BU = 1 cm). Modélisation à l'échelle estimée ; un scale uniforme final suffira si cotes réelles fournies (non destructif) | Moyenne — **estimation à confirmer** |
| Molette sans macro | Profil pris sur 03_side (diamètre/débord), position sur 01/hero-01, crans extrapolés des refs GB classiques | Moyenne (hypothèse marquée) |
| Tranche haute indéterminée | Modéliser 2 tabs discrets en relief d'après silhouettes 02/hero-01 ; rien de fonctionnel | Moyenne (hypothèse marquée) |
| Teinte violet (lumière chaude) | Caler la base albedo/transmission sur les zones les moins contaminées (09, fond crème neutre) ; affiner en Phase 6 | Bonne |
| Front basse rés. (960×576) | Suffisant pour le blocking (positions/ratios) ; les profondeurs et détails viennent des macros 5K | Bonne |

---

## 0.5 — Demandes à Sliz (priorisées)

**1. Indispensable** — *rien ne bloque le démarrage.* Une seule chose changerait la donne :
   - **Dimensions réelles** (L×H×P en mm) si elles existent quelque part (fiche produit, brief marketing). Débloque : échelle exacte sans calibration estimée. Sans elles, je modélise sur l'estimation USB-C (~160×96×22 mm) et tout reste rattrapable par un scale uniforme.

**2. Fortement recommandé**
   - **Les canoniques manquantes `04/05/06`** : la numérotation de `assets/` saute de 03 à 07 → si un set plus large existe (top ? bottom ? ¾ ? droite ?), le copier tel quel. Débloque : tranche haute + côté droit sans hypothèse. *(Zéro coût si les fichiers existent déjà.)*
   - **Une vue de la tranche haute** (même une frame ou un hero incliné) : tranche la nature des tabs (conflit n°3). Débloque : dos/tranche haute sans invention.
   - **Macro molette** : forme des crans, débord exact dans la tranche. Débloque : un contrôle signature actuellement à confiance moyenne.

**3. Bonus**
   - Ref matière sous **lumière neutre** (teinte violette exacte pour la Phase 6).
   - **Décision PCB** : texture photo plaquée sur une carte simplifiée (recommandé pour le web/glTF) vs modélisation 3D des composants principaux (plus lourd, plus beau en macro). Impacte le poids du .glb.

---

## 0.6 — Verdict : **GO** (avec hypothèses marquées)

Couverture suffisante pour modéliser l'objet entier proprement :
- **Confiance haute** : volume global, face avant complète (écran, D-pad, SYNC, slider gain, ports), construction de coque (seam, épaisseur, bossages), matériaux.
- **Hypothèses à acter** (signalées, non bloquantes) : échelle estimée via USB-C (~160×96×22 mm), symétrie du flanc droit, tabs de la tranche haute non fonctionnels, crans de molette extrapolés.
- Les demandes 0.5 améliorent la fidélité mais ne conditionnent pas le démarrage.

**Prochaine étape (après validation de ce rapport)** : Phase 1 — nettoyage scène, "Save As" du .blend dans le dossier projet (lever le conflit ⚠️ 0.1), import des orthos 01/02/03 en image planes calées à l'échelle estimée, bounding box 16×9.6×2.2 BU, gate screenshot front+side.

---

## 0.7 — Spec de génération des refs manquantes (nanobanana, conv API séparée)

Décision Sliz 2026-06-10 : les assets manquants seront **générés** (nanobanana) plutôt que retrouvés. 6 images spécifiées — 3 indispensables (`04_side_right`, `05_top_edge`, `closeup-11_macro-wheel`), 1 recommandée (`06_bottom_edge`), 2 bonus (`material-neutral`, `hero-back-top-34`). Prompts complets transmis en conversation (bloc identité EN + contraintes anti-drift + 6 prompts par plan, avec refs à attacher et ratios).

Points actés :
- **Ne pas régénérer la vue front** : `01_front_canonical` reste canon (une régénération créerait une vérité concurrente). Si besoin de résolution → upscale de l'existante.
- ⚠️ **DESIGN canonisé par la génération** (tranche haute) : slide switch power discret à gauche du centre + petite languette à droite, rien d'autre. La 05 devient la vérité de cette zone.
- Génération = même set vérité que higgsfield : à réception, **re-audit de cohérence** de chaque nouvelle image vs canon existant (silhouette, contrôles, seam, ports) avant intégration en Phase 1. Conflit → la ref EXISTANTE gagne, la générée est refaite.
- Dépôt : `assets/` pour les 04/05/06 (comble les trous de numérotation), `assets/close-ups/` pour closeup-11 ; mise à jour INDEX.md à l'intégration.
