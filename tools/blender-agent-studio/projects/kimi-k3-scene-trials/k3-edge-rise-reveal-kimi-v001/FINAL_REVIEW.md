# FINAL_REVIEW — k3-edge-rise-reveal-kimi-v001 « Le Réveil du Bord »

**Participant : kimi — verdict : ship, 88.3/100**

## Ce que raconte le plan

Assis sur le bord inférieur de la boîte, genoux remontés, un pied bat le tempo
(contact pile sur chaque beat). À la deuxième mesure il bascule en arrière puis
en avant, pousse sur ses genoux et se lève. Il gravit le Piano Roll réel
(47,1° mesurés) en huit pas calés sur les mesures de la grille 148,9 BPM, la
tête balayant les murs-écrans. À f203 la playhead le traverse : temps d'arrêt,
il la regarde passer dans un halo lime, puis repart. Au centre du sol-écran il
s'immobilise, se redresse, et lève lentement le regard — posé sur le downbeat
f348 — pendant que l'intensité des écrans monte et qu'une hero light fait de sa
silhouette le point le plus lumineux. Un seul plan continu : proche/bas 50 mm
au début, recul + élévation jusqu'au plan large 35 mm final où il tient 13,7 %
de la hauteur du cadre.

## Tempérament choisi

Curieux-posé, pas fatigué. Le pied qui bat dit qu'il *vit* ici ; la bascule en
arrière avant de se lever dit la résolution, pas l'effort ; la tête qui panote
pendant la marche dit la découverte tranquille ; l'ouverture des bras à f330
dit la réception.

## Idée personnelle (hors brief)

La playhead ne pouvait pas balayer le climax (son sweep unique f1→397 la place
à x≈+2,6 à f348), alors j'ai utilisé son passage réel au centre (x≈0 à la
mesure 203) : le personnage marque un temps d'arrêt exactement sur la barre de
mesure, la ligne lime le traverse, et un point light lime
(`K3_EDGE_PLAYHEAD_SWEEP`, 0→35 W) synchronisé sur le x réel de la playhead
vend le balayage de son corps — EEVEE ne fait pas de GI, l'émissif seul ne
l'aurait pas éclairé. C'est le seul effet ajouté qui n'était pas dans le brief.

## Ajouts au rig (mesh de l'asset NON modifié)

L'asset v002 n'a aucun rig (2 meshes, 0 vertex group). Ajouté, documenté ici :
armature `K3_EDGE_RIG` à 13 os (Pelvis, Spine, Chest, Neck, Head, UpperArm/
Forearm L/R, Thigh/Shin L/R) placés sur les centre-lines mesurés du mesh,
skinning par poids automatiques, modifier Armature avant le Subsurf. Totaux
vertex inchangés : 6348 + 1986. L'avant nominal de l'asset est −Y ; le mesh
étant quasi symétrique, je l'oriente face +Y (vers les écrans) — invisible sur
cette silhouette sans visage.

## Choix physiques imposés par les mesures

- Le Piano Roll (47,1°) **surplombe** le bord : des jambes pendantes passeraient
  à travers l'écran. D'où l'assise genoux remontés sur le rim horizontal, et un
  lever par bascule (mains sur genoux — les bras de 0,64 m ne peuvent pas
  atteindre le rim depuis l'épaule, mesuré).
- Adhérence contractuelle `ustudio_grip_surface = 1.25` (pente > 45°), reprise
  de la convention du repo.
- Validation frame par frame (360) : drift pied planté 0,00005 m, pénétration
  0 m, clearance swing 0,026 m, torse 0,5–18,3° de la verticale monde, jamais
  de genou hyper-étendu (span jambe max 0,46/0,613).

## Ce qui marche

L'arc se lit en 12 s sans contexte : petit être → bord → immensité. Le crossing
f203 est le meilleur moment du film. Le plan final tient la silhouette lisible
avec la boîte entière. La montée en lumière des écrans porte le climax.

## Ce qui rate encore (honnêtement)

- De face, l'assise reste peu « posée » : le rim est vu par la tranche, le
  contact fesses/siège se devine plus qu'il ne se voit (f1–57).
- Les bras font légèrement « ailes de poulet » pendant le lever (coudes dehors,
  mains courtes — limite anatomique de l'asset).
- Le personnage est un peu terne dans les plans moyens (f106–250) ; la hero
  light n'arrive que tard.
- Cisaillement du blob au niveau des hanches quand les genoux sont au maximum
  remontés (poids automatiques sur mesh fusionné).
- La grille 148,9 BPM vient de l'autocorrélation spectrale, pas confirmée à
  l'écoute — les appuis suivent les mesures estimées.

## Avec une passe de plus

Re-cadrer f1–57 un demi-plan plus latéral pour montrer le plan du rim sous
l'assise ; adoucir les poids hanche/bassin à la main ; éclairer le buste dès
f150 avec un dimmer progressif ; confirmer la grille à l'échelle et recaler le
premier pas si besoin.

## Preuves

`renders/preview.mp4` (H.264 640×360, 30 fps, 360 frames, AAC, 12,000 s,
blackdetect propre), `diagnostics/physical-validation.json` (passed: true),
`gates/contact-sheet.jpg`, `gates/key-0*.png`, `gates/lighting-gate-manifest.json`,
`diagnostics/scene-audit.json`, scripts reproductibles dans `scene/`
(build_scene.py, bake_anim.py, validate_physical.py).
