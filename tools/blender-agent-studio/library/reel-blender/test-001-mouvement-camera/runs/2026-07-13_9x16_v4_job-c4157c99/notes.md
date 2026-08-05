# notes — run 4 v4 (job c4157c99, 21 crédits) — sb-003 + scène A

## Évaluation vs success criteria (ligne par ligne)

| # | Critère | Verdict | Observation factuelle |
|---|---|---|---|
| 1 | Trajectoire = préviz sb-003 | ✓ | t0.4 macro basse partielle (cadrage partiel reproduit) ; t3.0 wrap-around 3/4 gauche monumental en hauteur ✓ ; t4.6→5.9 pullback reveal objet ENTIER puis rest frontal centré. Un seul geste continu, pas de coupe. (Vertigo final à juger à l'œil sur le .mp4 — subtil par design.) |
| 2 | Identité device | 🟡 | Layout 6 contrôles tenu à tous les angles ✓, paysage constant ✓ — MAIS label SYNC corrompu aux angles (« ƎTNC »/« STNC » à t3.0/t5.9) et wordmark légèrement instable à t0.4. |
| 3 | Écran OFF | ✓ | OFF sur toutes les frames, aucun UI inventé. |
| 4 | Non opéré / bords nus | ❌ | Contrôles non animés ✓ — mais **2 caps blancs sur le bord HAUT** (t3.0, t5.9) + **2 tabs blancs sur la tranche GAUCHE** (t3.0). Le prior « shoulder buttons » se réveille dès que la caméra monte au-dessus de l'objet (déjà vu run 2, plus fort ici car sb-003 plonge davantage). |
| 5 | Matière upgradée + **SCÈNE A** | ✓ | **LE SPOT DU HAUT EST MORT** — zéro cône/beam. Horizon teal, sol miroir avec reflet, rim cyan gauche + magenta droite : la scène A est transférée fidèlement et tenue sous tous les angles. Améthyste translucide PCB ✓. |

**Verdict : la couche scène FONCTIONNE (objectif du run atteint) — non validable en l'état
à cause des caps bord haut/tranche (#4) + labels (#2).**

## Leçons

1. **Scène ref > prompt seul** : 3 runs de prompts « near-black void » n'avaient jamais
   fixé le fond ; UNE image de scène l'a fait en un run. Les pixels gagnent sur le texte
   (cohérent avec le failure-pattern refs-override-skeleton — ici utilisé POUR nous).
2. Le prior « caps bord haut » est corrélé à l'ALTITUDE caméra (plongées de sb-003).
   Counter-prompt « TOP edge bare smooth plastic » présent mais insuffisant seul.
   → pistes v5 : (a) scène ref B0 supplémentaire vue de dessus bords nus,
   (b) squelette clay pass avec bords lisses plus lisibles (vs viewport flat),
   (c) atténuer la plongée (crane z +6 → +4).
3. Labels : corruption aux angles rasants — la scène A avait SYNC correct de face ;
   prévoir ref macro du bouton si on veut le verrouiller (ou accepter, illisible en motion).
4. Fusion scène/squelette : Seedance a posé l'objet SUR la ligne d'horizon au rest
   (vs lévitation haute de la scène A) — compromis élégant, pas un défaut.

## Boucle suivante (proposée)

v5 = mêmes médias + BEATS inchangés, ANTI-PRIORS renforcés bord haut (« nothing on the
top edge ever — no caps, no tabs, no buttons — even seen from above ») ou squelette clay.
