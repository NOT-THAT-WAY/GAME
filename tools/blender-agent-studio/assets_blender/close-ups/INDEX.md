# canonical-refs/close-ups/ — Pulsed macro & hero reference set

Set photoréaliste de l'objet **Pulsed** (10 images, higgsfield, 2026-06-03). Sert de
**vérité d'identité haute-fidélité** pour la préservation v2v : matière, translucidité,
contrôles, PCB interne, marquages de surface, ports. À utiliser comme `reference-assets`
(`@Image1`…) quand la transformation doit **garder l'objet exact**.

## Identité visuelle commune (à préserver)

- **Coquille** : plastique translucide améthyste/violet (« atomic clear purple »), brillante, PCB visible à travers.
- **Contrôles** : blanc/gris mat — D-pad croix (flèches embossées + dôme central), bouton rond **SYNC**, slider **gain** vertical (avec échelle graduée), slider horizontal.
- **Écran** : rectangle teal-noir (éteint sur ces refs).
- **Marquages** : wordmark cursif **« Pulsed »** + logo **U-point** (U stylisé + point) embossés ; silkscreen PCB (`LOW BATT`, `CACO`, refs composants).
- **I/O** : USB-C + port secondaire (lien/expansion) sur la tranche basse ; vis dans bossages de coin.
- **Éclairage** : fond crème/os, rim light chaud, LEDs internes rouge/bleu/cyan ; ombre douce portée (shots hero flottants).

## Plan par image

| Fichier | Type | Contenu / usage ref |
|---|---|---|
| `closeup-01_hero-front-3q.jpeg` | **HERO 3/4 front** (large) | Objet complet, layout canonique (wheel, SYNC, sliders, D-pad, écran, wordmark+logo). **Ref d'identité primaire.** |
| `closeup-02_hero-back-internals.jpeg` | **HERO dos** (large) | Dos complet, PCB entier à travers la coquille, molette, ports, vis. Ref structure interne. |
| `closeup-03_macro-faceplate-screen-gain-dpad.jpeg` | Macro face | Coin haut-droit : écran + slider gain + D-pad + wordmark + logo + LEDs. |
| `closeup-04_macro-dpad.jpeg` | Macro contrôle | D-pad croix blanche (flèches embossées, dôme central) sur PCB. |
| `closeup-05_macro-sync-button.jpeg` | Macro contrôle | Bouton **SYNC** rond + silkscreen `LOW BATT`. |
| `closeup-06_macro-gain-slider-scale.jpeg` | Macro contrôle | Slider gain vertical + échelle graduée + USB-C à travers coquille. |
| `closeup-07_macro-gain-slider-screen-edge.jpeg` | Macro contrôle | Slider gain + bord écran + silkscreen `CACO`/`TC8US598U` + flèche D-pad. |
| `closeup-08_macro-pcb-interior.jpeg` | Macro matière | PCB interne (puces, pistes) vu à travers la coquille translucide. |
| `closeup-09_macro-corner-shell-screwboss.jpeg` | Macro matière | Coin/tranche : épaisseur coquille, bossage de vis, ligne de joint, bord PCB. |
| `closeup-10_macro-bottom-port-usbc.jpeg` | Macro I/O | Tranche basse : USB-C + port secondaire, angle bas. |

## Usage v2v

- **Insertion** → fournir `01` (hero front) + `02` (back) en `reference-assets` pour ancrer la silhouette globale.
- **Préservation fine** → ajouter les macros pertinentes (contrôle/matière concernés par le plan) pour bloquer le drift (wordmark, D-pad, SYNC, translucidité, ports).
- Coupler avec `prompt-library/failure-patterns/` (anti-substitution de marque, anti-drift de silhouette) en prompt minimaliste.
