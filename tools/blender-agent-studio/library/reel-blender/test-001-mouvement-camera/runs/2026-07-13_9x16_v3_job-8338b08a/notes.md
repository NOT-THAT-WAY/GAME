# notes — run 3 v3 (job 8338b08a, 21 crédits) — VIDEO-FIRST, squelette sb-002

## Évaluation vs success criteria (ligne par ligne)

| # | Critère | Verdict | Observation factuelle |
|---|---|---|---|
| 1 | Trajectoire = préviz | ✓ | Suit sb-002 beat par beat : t0.4 macro basse frontale partielle (cadrage partiel REPRODUIT, pas recomposé) ; t1.8-2.6 turn 3/4 GAUCHE en remontée ✓ ; t4.6 objet ENTIER dans le cadre en descente vers le repos ✓ ; t5.9 rest frontal centré marges larges ✓. Aucune coupe, aucun beat inventé. |
| 2 | Identité device | ✓ | Layout canonique tenu sur TOUTES les frames (molette gauche écran, fader droite, SYNC bas-gauche, slider bas-centre, D-pad bas-droite, wordmark + U.). Paysage constant ✓. |
| 3 | Écran OFF | 🟡 | OFF partout ; léger reflet fumé/haze sur l'écran à t0.4 (pas une waveform ni UI — lisible comme reflet du void). |
| 4 | Non opéré / bords nus | 🟡 | Contrôles non animés ✓ ; plus de ports francs ✓ ; 2 micro-nubs subsistent sur le bord haut au plan large (bien plus discrets qu'au run 2). |
| 5 | Matière upgradée | ✓ | Void near-black + key haut + rim, améthyste translucide PCB, satin. |

**Verdict : meilleur run des trois — VALIDABLE sous gate Sliz** (2 réserves mineures : reflet
écran t0.4, micro-nubs bord haut).

## Feedback Sliz (2026-07-13, post-run)

Mouvement validé (« vraiment pas mal ») MAIS « le spot lumineux d'au dessus pas très
beau » — le cône de projecteur du haut du cadre est un PRIOR Seedance (« produit dans le
noir »), pas un choix : rien dans nos pixels d'entrée (front nue, fond neutre) ne disait
à quoi ressemble le fond. Antidote = scène designée Nano-Banana en image ref →
`../../../test-002-scene-nanobanana/` +
`failure-patterns/v2v-neutral-void-invents-overhead-spotlight.md`.

## Ce que la v3 prouve (la « super méthode »)

1. **VIDEO-FIRST fonctionne** : 1 seule image ref (front) + squelette = le mouvement Blender
   est suivi shot-for-shot, y compris le cadrage PARTIEL voulu de l'ouverture.
2. Le fix « objet entier dans le cadre » (sb-002, dist 58→66 BU) élimine la recomposition.
3. Retirer side (colonne verticale) + back (fond crème) n'a PAS affaibli l'identité — le
   front + SUBJECT verbatim suffisent.

## Boucle itérative validée

Modifier le mouvement = éditer les keyframes dans le .blend (marqueurs B1→B4) ou
`tools/rig_sb002.py` → re-playblast → re-upload → relancer. Zéro re-prompt nécessaire.
