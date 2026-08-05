# reel-blender / test-001 — mouvement caméra (squelette Blender → Seedance v2v)

> **Pôle** : `reel-blender/` — reels dont le MOUVEMENT est fabriqué en 3D (Blender, déterministe)
> puis stylisé par IA. Premier test de la chaîne complète, demandé par Sliz le 2026-07-13.

## Objectif

Prouver la chaîne : **storyboard Nano-Banana → chorégraphie Blender (keyframes exacts) →
préviz render → Seedance 2.0 `video_references` (MCP Higgsfield, crédits)** — l'IA garde
EXACTEMENT le mouvement caméra du squelette Blender et remplace la matière/lumière préviz
par le photoréel canonique.

- **Source motion** : `blender-choreography/runs/sb-001-crane-2026-07-13/preview_sb001_6s.mp4`
  (chorégraphie sb-001-crane, 4 poses interprétées du board NB — cf.
  `blender-choreography/shots/sb-001-crane.md`).
- **Différence vs pôles existants** : dans `pulsed-reels/` le mouvement est décrit en mots
  (Seedance interprète) ; ici le mouvement est **donné en vidéo** (Seedance obéit).

## Chorégraphie (ce que le squelette contient — 6 s, 24 fps, 9:16)

| Beat | Timing | Pose |
|---|---|---|
| P1 macro-low | 0,0–0,8 s | contre-plongée rasante grand-angle, slider + D-pad au premier plan |
| P1→P2 crane | 0,8–2,3 s | montée crane + resserrage focale 28→70 mm |
| P2 hero-3q | 2,3–3,0 s | hero 3/4 gauche monumental (hold) |
| P3 overhead | 4,2–4,7 s | plongée ~50° au-dessus de la face (hold) |
| P4 rest | 6,0 s | frontal à niveau, device centré, marges larges |

## Success criteria (à vérifier ligne par ligne sur l'output)

1. **Trajectoire caméra = préviz** : les 4 poses aux mêmes timings, aucune coupe, aucun beat inventé.
2. **Identité device** : layout 6 contrôles exact (molette haut-gauche face, SYNC bas-gauche,
   slider horizontal bas-centre, fader vertical droite, D-pad bas-droite), coque améthyste
   translucide **satin matte**, PCB violet visible.
3. **Écran OFF** (sombre/réflectif) — aucune waveform ni UI inventée.
4. **Contrôles non animés** (montré, pas opéré) ; aucun port inventé (pas d'USB-C).
5. **Matière upgradée** : le rendu préviz (EEVEE laiteux) devient photoréel premium —
   void near-black, rim light froide, haze volumétrique (cohérent panels storyboard).

## Lane & coûts

MCP Higgsfield `seedance_2_0` (fast 720p pour le test) — crédits explicitement autorisés
par Sliz (le perk fast illimité UI ne s'applique pas via MCP, ~21 crédits/clip 6 s 720p).
`get_cost` preflight obligatoire avant chaque run. Solde au départ : 800 crédits.
