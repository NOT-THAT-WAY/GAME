# Pulsed — Prompts de génération v2 (post-mortem v1 intégré)

> Remplace la spec v1 (§0.7 du preflight). Cause racine de l'échec v1 : le BLOC IDENTITÉ commun décrivait
> **tous** les contrôles (dont la molette) dans **chaque** prompt, et la spec top-edge **inventait** un switch
> absent des refs → nano-banana a fusionné les deux en « roulette sur le dessus ».

## Doctrine anti-drift (non négociable)

1. **Un prompt ne décrit QUE ce qui est visible dans le cadre demandé.** Aucun inventaire global des contrôles. L'identité de l'objet est portée par les **images de référence attachées**, pas par le texte.
2. **Aucune feature non vérifiée dans les refs.** Zone inconnue = « continuer les formes de la coque, ne rien ajouter ». Jamais de proposition design dans un prompt.
3. **Négatif court et explicite par image** (« do not add any control/button/switch/dial/port on this edge »).
4. **Critères d'acceptation mesurables avant intégration** (listés par image ci-dessous).
5. Itérer 2-3 fois par plan, garder la plus conforme. Snapshots en `_gen-runs/`, rien ne rentre dans `assets_blender/` sans validation croisée carte (`pulsed-object-map.md`).

## Préambule commun (UNIQUE bloc partagé, volontairement minimal)

```
Photorealistic product photography of the exact handheld device shown in the attached
reference images — same shell, same proportions, same materials (glossy translucent
amethyst-purple plastic with the internal PCB visible through it), same parting seam.
Warm cream seamless background, soft drop shadow, consistent with the references.
Do not add, remove, move or restyle any element of the device. No text overlays, no props, no people.
```

---

## 🔴 P1 — `05_top_edge_canonical.png` (la bloquante — refaite sur plan réel)

- **Objectif** : vérité de la tranche haute. Décision verrouillée : tranche **nue**.
- **Refs à attacher** : `closeup-01_hero-front-3q.jpeg`, `closeup-02_hero-back-internals.jpeg`, `closeup-10_macro-bottom-port-usbc.jpeg` (pour le style de cadrage tranche).
- **Ratio** : 16:9, résolution max.

```
Straight-on view of the TOP edge of the device, camera at edge height, centered, the full
device width sharp in frame edge-to-edge with margin at both ends (deep focus, f/11, no
perspective distortion). Same framing style as the attached bottom-edge reference photo,
but showing the opposite (top) edge, which is PLAIN: only the horizontal parting seam
running along it, a gently convex crown profile, and two very low-profile light-grey shell
clips sitting flush on the seam at roughly one-third and two-thirds of the width, exactly
as visible on the top silhouette of the attached back reference. Corner screw bosses and
faint internal PCB connectors may show through the translucent purple plastic only.
This edge carries no controls: do not add any button, switch, wheel, dial, knob, port,
hole or marking on this edge.
```

- **Acceptation** : silhouette de tranche = crown lisse + 2 micro-clips (≤1,5 mm) à ~30 %/~70 % ; AUCUN élément mécanique ; seam continue ; coins arrondis cohérents avec `02_back`.

## 🔴 P2 — `00_front_uncropped.png` (NOUVEAU — vérité silhouette/ratio)

- **Objectif** : trancher le conflit de ratio W/H (1,43→1,74 selon refs). La `01_front` actuelle est croppée DANS la silhouette → vérité **layout** mais pas **silhouette**. Cette image devient la vérité silhouette ; `01_front` reste la vérité positions.
- **Refs à attacher** : `01_front_canonical.png`, `closeup-01_hero-front-3q.jpeg`.
- **Ratio** : 3:2 paysage, résolution max.

```
Perfectly frontal, head-on view of the device, camera axis exactly perpendicular to the
front face, centered, long telephoto lens look (no perspective distortion). The ENTIRE
device fits in frame with at least 12% empty background margin on all four sides, so the
complete outer silhouette and all four rounded corners are fully visible. Front face
layout, controls and markings exactly as in the attached front reference image. Device
floating, soft drop shadow below.
```

- **Acceptation** : marge visible sur les 4 côtés ; W/H mesuré attendu ≈ 1,51 ±0,06 (sinon itérer et garder la médiane des runs) ; layout face identique à `01_front` (positions table §3 de la carte, ±2 %).

## 🟠 P3 — `04_side_right_canonical.png` (itération de nettoyage sur iter3)

- **Objectif** : flanc droit nu. L'iter3 est bonne sauf un bossage parasite bas-gauche.
- **Méthode** : édition/inpaint de l'iter3 si l'outil le permet, sinon regen avec ce prompt.
- **Refs à attacher** : iter3 existante, `03_side_clean_canonical.png` (style), `closeup-01`.
- **Ratio** : 16:9 (ou identique à iter3).

```
Same image as the attached side-view generation, with one correction: remove the small
parasitic bump on the lower left of the silhouette. The right-side edge of the device is
plain — only the horizontal parting seam runs along it, with smooth continuous shell
surfaces above and below. No control, button, wheel, dial, port or hole anywhere on this
edge. Keep everything else identical: framing, lighting, background, proportions.
```

- **Acceptation** : silhouette lisse (profil = crown haut, dos bombé, fond arrondi) ; seam seule sur le flanc ; T/H ≈ 0,25.

## 🟡 P4 — `06_bottom_edge_canonical.png`

- **Objectif** : tranche basse pleine largeur (complète `closeup-10`, qui est légèrement croppée/floue aux extrémités).
- **Refs à attacher** : `closeup-10` (vérité ports), `closeup-02`.
- **Ratio** : 16:9.

```
Straight-on view of the BOTTOM edge of the device, camera at edge height, perfectly
perpendicular, full device width sharp in frame with margin at both ends (deep focus,
f/11). The ports exactly as in the attached bottom-edge close-up reference: the metal
USB-C port slightly left of center, and the trapezoid multi-pin expansion port to its
right, each recessed in its rounded cutout of the purple shell, with the parting seam
running along the edge. Nothing else on this edge.
```

- **Acceptation** : USB-C centré ≈47 % ±3, trapèze ≈58-64 % ; formes des découpes = closeup-10 ; aucun port/élément supplémentaire.

## ⚪ P5 — `material-neutral.png` (bonus, Phase 6)

- **Refs** : `closeup-01`, `closeup-09`. **Ratio** : 3:2.

```
Three-quarter front view of the device floating on a neutral light-grey seamless studio
background under soft neutral white light (5500K daylight softbox, no warm color cast, no
colored rim light). Faithful color of the translucent amethyst-purple shell, internal PCB
visible through the plastic, soft neutral shadow. Device strictly identical to the
attached references.
```

- **Acceptation** : zéro dominante chaude ; device inchangé.

## ⚪ P6 — `hero-back-top-34.png` (bonus, validation croisée)

- **Refs** : `closeup-02`, P1 validée, P3 validée. **Ratio** : 16:9.
- ⚠️ À générer **après** validation de P1/P3 (elles définissent ce que cette vue doit montrer).

```
Three-quarter hero shot of the device seen from above and behind, slightly to the right:
showing together the back shell with the PCB visible through the purple plastic, the plain
top edge with its parting seam and two small flush shell clips (as in the attached top-edge
reference), and the plain right side edge. Floating over the warm cream background, soft
drop shadow, same hero style as the attached references.
```

- **Acceptation** : cohérence stricte avec P1 (tranche nue) et P3 (flanc nu) ; pas d'élément nouveau.

---

## Ordre de tir conseillé

1. **P1** (débloque tout — la décision tranche haute est actée)
2. **P2** (verrouille le ratio avant la Phase 1 Blender)
3. P3 (simple nettoyage) → 4. P4 → 5. P5/P6 quand utiles.

Rappel : les **dimensions réelles** restent non générables — toujours preneur d'une cote (largeur en mm suffit, tout le reste est en ratios mesurés).
