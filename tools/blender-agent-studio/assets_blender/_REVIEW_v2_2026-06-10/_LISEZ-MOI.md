# Review set préflight v2 — 2026-06-10

Candidats nano-banana-pro/edit 4K (doctrine v2 `audits_blender/pulsed-asset-prompts-v2.md`).
**Copies de review uniquement** — les originaux immuables sont dans `_gen-runs/<id>/runs/…`.
Rien n'a été copié dans `assets_blender/` racine (règle 5 : pas d'intégration sans ta validation carte).

| Fichier | Plan | Verdict | Note |
|---|---|---|---|
| `P1_05_top_edge_canonical.png` | top-edge nue | ✅ | crown + 2 clips à ⅓/⅔, zéro contrôle. La correction du bug « roulette ». Clips un poil marqués vs « ≤1,5 mm ». |
| `P2_00_front_uncropped__seed720002.png` | front non croppée | ✅ visuel · ⚠️ ratio | layout fidèle, marges 4 côtés. Ratio : voir point 1 ci-dessous. |
| `P2_..._seed720012_alt.png` | front (2e seed) | — | pour comparer le ratio (les 2 donnent ~1,65 en mesure like-for-like). |
| `P3_04_side_right_canonical.png` | side-right nu | ✅ corrigé | **molette parasite retirée**. Régénéré sans aucune ref de profil (rien à copier), puis bump résiduel de 18px raboté au pixel. Contour certifié lisse : gauche ≤8px, droite ≤2px. Marques sombres = PCB interne par transparence, pas des boutons. (run seed720023) |
| `P4_06_bottom_edge_canonical.png` | bottom-edge | ✅ | USB-C ~46 %, trapèze ~62 %, conforme closeup-10. |
| `P5_material-neutral.png` | matière neutre | ✅ | fond gris, zéro dominante chaude, violet fidèle. |
| `P6_hero-back-top-34.png` | hero back+top | ✅ | cohérent P1 (tranche nue) + P3 (flanc nu). |
| `EXTRA_closeup-11_macro-wheel.jpeg` | molette macro (v1) | ✅ | toujours valide (molette bord gauche, puits, knurling). |

## 2 décisions qui t'appartiennent (non-générables)

1. **Ratio P2** — passe `P2_00_front_uncropped__seed720002.png` dans **ton script de seuillage** (apples-to-apples), ou donne la **cote mm réelle**. En mesure like-for-like, mon P2 (≈1,65) = tes refs dos (≈1,65-1,67) ; le « 1,51 » vient d'un seuil différent.
2. **Inflexion P3** — rim légitime vs résidu. Si résidu → inpaint manuel 10s.

Dis-moi : (a) lesquelles tu valides, (b) si je copie les gagnantes aux noms canoniques dans `assets_blender/`.
