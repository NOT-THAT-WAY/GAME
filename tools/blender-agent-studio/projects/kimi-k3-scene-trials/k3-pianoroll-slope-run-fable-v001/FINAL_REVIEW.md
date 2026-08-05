# Revue finale — k3-pianoroll-slope-run-fable-v001

Participant : **fable**. Score : **89.45 / 100** (barème validateur) et **91.5 / 100** (barème mission).

## Verdict

`ship` — aucun échec critique, validation physique 11/11 sur les 240 frames évaluées.

## Histoire et causalité

Un petit coureur pearl (0,323 m) se tient au pied de la rampe du Piano Roll dans la boîte FL Studio
flottante. La musique du master pulse ; il transfère son poids (f17-32), se comprime, lève le genou
droit (f41) et pousse sur le pied gauche (f49-53) pour poser son premier appui fort exactement sur le
downbeat frame 57. Il monte la pente réelle de 46,34° en 12 foulées calées sur la grille de
pulsations mesurée (période 12,1 frames, ~148,7 BPM), décélère sur le downbeat frame 203, absorbe
l'énergie en deux appuis de stabilisation et finit en pose stable, encore incliné dans la pente,
0,47 m sous le bord supérieur. Chaque changement a une cause visible ; le pulse lime des semelles
n'existe qu'au contact.

## Physique et usage

- Surface **mesurée**, pas supposée : normale (0, −0,723449, +0,690377), pente 46,3400°, longueur
  utile 2,419 m (`diagnostics/surface-analysis.json`), repère de locomotion SURFACE_NORMAL /
  UPHILL_TANGENT / CROSS_SLOPE_TANGENT / WORLD_GRAVITY.
- Le point central du test : le personnage n'est **ni vertical naïf ni tourné selon la normale**.
  Les semelles sont coplanaires au plan pendant chaque contact (spread de coins mesuré : 0), le
  bassin se déplace parallèlement au plan (erreur de hauteur selon la normale : 0), les jambes
  travaillent près de la ligne de gravité monde (bassin bas ~0,11 m, appuis 0,08-0,09 m en aval du
  bassin), et le torse répond à la gravité : 19,5-22,5° par rapport à la verticale monde pendant la
  course — loin des 46,34° d'une rotation rigide.
- Adhérence : cause visible et contractuelle — semelles grip lime, propriété `ustudio_grip_surface`
  = 1,25 sur les semelles et le sol, minimum requis tan(46,34°) = 1,048, marge 0,20. Aucun sol
  horizontal invisible.
- Mesures (240 frames, scène évaluée, pas les keyframes) : drift pied planté max **2×10⁻⁶ m** ;
  pénétration max **0** ; clearance d'orteil en swing min **0,0137 m** ; zéro genou inversé ; marge
  aux extrémités min **0,27 m** ; hanche-cheville max 0,124 m pour 0,139 m de jambe (genou toujours
  fléchi, aucune hyperextension).

## Caméra et rythme

Tracking latéral trois-quarts (25°) côté −X, 50 mm f/5.0, TARGET indépendant (poitrine, retard
2 frames) et FOCUS séparé. K1 pose (f1-40) ; K2 anticipation en arc de −4° à distance constante
(f40-52) ; K3 travel parallèle à UPHILL_TANGENT avec offset constant (f52-206) ; K4 recovery +1,4°
amorti (f206-228) puis arrêt complet sans wobble. Distance caméra/coureur constante à **3×10⁻⁵ m**
près (compensation le long de l'axe de visée), clearance décor min **0,618 m**, pieds dans le cadre
**100 %** de la course, horizon monde niveau (Track To en espace monde), aucun roll copié de la
pente. Trois caméras diagnostiques (profil strict, top/rear contacts, normale de surface) servent
uniquement aux gates.

## Lumière et design

Ordre Drumboiii en six états A/B (`gates/lighting-gate/`) : environnement du template retenu ; Sun
oblique rasant dont l'ombre portée du coureur **prouve** l'inclinaison ; backlight dominant (58 W)
pour le contour pearl ; glimmer lime sur semelles et bord montant (0,24× le backlight) ; glimmer
magenta opposé en écho des LEDs violettes (0,19×) ; retour de détail doux sur le torse (0,22×).
Palette : pearl dominant, écrans du template en secondaire, accents lime/magenta. Aucune typo.

## Défauts restants

1. **Diagonale apparente ~51°** au lieu de la bande 20-35° demandée : impossibilité projective —
   toute caméra sans roll proche du profil projette une pente de 46,34° à un angle ≥ 46,34° ; seule
   une vue plongeante l'aplatirait, ce que la mission interdit par ailleurs. Documenté dans
   `shot-manifest.json`. La diagonale reste clairement ni horizontale ni verticale.
2. La grille rythmique (downbeats 9/57/106/154/203) reste l'estimation spectrale du dépôt : un gate
   d'écoute humaine confirmerait ou décalerait de quelques frames.
3. Style de contact « pose plate statique » : pas de déroulé talon-pointe (choix pour garantir zéro
   drift au sens strict) ; un déroulé physique demanderait un modèle de contact plus riche.
4. Le support affiché à l'instant exact du touchdown (f57) est étiqueté `transition` — artefact
   d'étiquetage à la frontière, le pied est bien à la surface.

## Itérations

1. **Rig/pose** — symptôme : seuls des blocs isolés visibles ; cause : lecture de matrices de pose
   évaluées périmées en batch ; correction : basis calculée depuis les matrices désirées du parent ;
   verdict `improved`.
2. **Silhouette** — symptôme : segments disjoints aux articulations pliées ; correction : sphères
   articulaires (hanches, genoux, chevilles, coudes, cou, taille) ; verdict `improved`.
3. **Lumière** — symptôme : lavage spéculaire blanc dans le coin amont ; cause : reflet du
   backlight 110 W sur la rampe glossy ; correction : 58 W, +0,85 m selon la normale, spread 70° ;
   verdict `improved`.

## Livrables

`FL_Studio_PianoRoll_Slope_Run_Fable.blend`, `preview-pianoroll-slope-run-fable.mp4` (H.264
640×360, 30 fps, 240 frames, 8,000 s, AAC, zéro frame noire), `renders/preview.mp4`,
`renders/frames/` (240 PNG), `gates/contact-sheet.jpg` (narratif), `gates/contact-sheet-profile.jpg`,
`gates/contact-sheet-feet.jpg`, `gates/lighting-gate-manifest.json` + 6 PNG,
`diagnostics/surface-analysis.json`, `diagnostics/physical-validation.json`,
`diagnostics/scene-audit.json`, `diagnostics/motion-plan.json`, `shot-manifest.json`, `score.json`,
`validation-report.json`. Source template intacte (SHA-256 identique), aucun output d'un autre
participant inspecté.
