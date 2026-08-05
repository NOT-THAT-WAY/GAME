# Analyse — Chains and Movements / Drumboiii

## Ce que sa méthode change

Une chaîne qui bouge, l'intuition dit « rig ». Drumboiii ne rigge rien. Il fabrique **un**
maillon, le répète avec un Array, le plie sur une courbe — puis il anime **les déformeurs**,
jamais la transform de l'objet. La chaîne ne se déplace pas : elle se tord sur place.

C'est ce dernier point qui vaut d'être retenu ici. Le mouvement d'ambiance qu'il obtient est
gratuit en simulation, exact en boucle, et il ne touche pas à la position du sujet. Un décor
peut donc respirer sans qu'aucune mesure de contact, d'appui ou de dérive ne bouge d'un
millimètre.

Il montre deux moteurs de mouvement, et le second n'est pas une variante du premier : ils
n'ont ni les mêmes garanties ni les mêmes pièges.

## Déroulé observé

| Timecode | Étape | Ce qui est réglé |
|---|---|---|
| 00:00–00:15 | intention | chaînes de décor, deux façons de les animer |
| 00:15–01:06 | maillon | Torus Minor Radius 0,35 ; Ctrl+B Segments 1 ; étirement en G X ; voisin à R X 90 |
| 01:06–01:25 | Array | Offset Method Relative, Offset X 1,000 → **0,768**, Count 3 → 24 |
| 01:25–02:12 | chemin | NurbsPath, dernier point de contrôle ramené sur l'origine |
| 02:12–02:45 | Curve | Curve Object NurbsPath, Deform Axis X ; Count réajusté 24 → 19 |
| 02:46–03:15 | forme | sculpture en vue de côté puis G Y pour sortir du plan |
| 03:15–03:52 | scène | 24 → **60 fps**, plage 1 → 500 |
| 03:52–04:52 | Twist n°1 | axe X, cles −10 / +10 / −10 aux frames 1 / 50 / 100, bloc recopié |
| 04:52–05:30 | Twist n°2 | axe Y, mêmes valeurs inversées — **et le résultat empire** |
| 05:30–06:08 | correction | décaler les clés du second de ~25 frames |
| 06:08–07:20 | méthode B | Empty Plain Axes, driver `#frame/60` sur Rotation Z, Origin du Simple Deform |
| 07:20–07:34 | clôture | |

## Le vrai enseignement : le déphasage

C'est le seul moment du tutoriel où il montre une erreur avant de la corriger, et c'est le
passage le plus utile.

Deux Twist sur des axes perpendiculaires, clés **alignées**, valeurs opposées : le résultat,
dit-il lui-même, est *« really static and ugly almost »*. La raison est mécanique — les deux
torsions atteignent leurs extrêmes sur la **même frame**. Les deux axes basculent ensemble,
et l'œil lit un unique aller-retour rigide, exactement ce qu'on voulait éviter en ajoutant un
second déformeur.

Décaler les clés du second d'un **quart de période** (25 frames sur 100) suffit : X est à son
extrême quand Y passe par zéro. La somme ne décrit plus une oscillation plate mais une
rotation lente et continue.

La règle transférable n'a rien à voir avec les chaînes :

> Deux déformeurs de faible amplitude sur des axes perpendiculaires, décalés d'un quart de
> période, produisent un mouvement d'ambiance. Les mêmes déformeurs en phase produisent une
> raideur.

Vérification : à t=333 s, `SimpleDeform` vaut +6,03° pendant que `SimpleDeform.001` vaut
−6,03°. L'opposition de signe est bien tenue sur toute la boucle.

## Le piège du driver, mesuré

Méthode B : `#frame/60` tapé dans le champ Rotation Z d'un Empty. Le champ passe en violet,
l'Empty tourne indéfiniment, et le Simple Deform suit parce que son `Origin` pointe dessus.
Zéro keyframe.

Ce que le tutoriel ne dit pas, et qui casse tout si on l'ignore : **le driver écrit la valeur
brute de la propriété, donc des radians**, même si le champ affiche des degrés.

Mesuré sur les frames plutôt que supposé — à la frame **9**, le champ affiche **8,59°**.
Or 9/60 = 0,15 rad = 8,594°. La correspondance est exacte.

Il en découle une formulation propre, que l'auteur n'énonce pas :

> `#frame/<fps>` donne exactement **1 radian par seconde**, soit un tour complet toutes les
> **6,28 s**, quelle que soit la cadence. Le diviseur **est** la cadence.

C'est pour ça que 60 marche chez lui. Copié tel quel dans une scène à 24 fps, le même
`#frame/60` tourne 2,5 fois trop lentement. Le portage correct est `#frame/24`.

Second piège, plus discret : un driver **n'apparaît pas dans le Dope Sheet**. Tout contrôle
de mouvement basé sur les F-Curves passera à côté. La seule trace visuelle est la couleur
violette du champ.

## Valeurs relevées

Le maillon : Torus, **Minor Radius 0,25 → 0,35 m**, Major Radius laissé à 1,0. Puis Ctrl+B
avec **Width 0,0406 m et Segments 1** — le biseau ne biseaute rien, il dédouble l'anneau
central pour créer la partie droite du maillon quand le côté droit est tiré en G X.

L'Array : **Relative Offset X 0,768**. Cette valeur ne veut rien dire hors contexte : elle
dépend entièrement de la distance d'étirement du maillon. Elle se réaccorde à l'œil, jusqu'à
l'emboîtement.

Le Count descend de 24 à 19 après mise à l'échelle du chemin. C'est une dépendance à retenir :
`longueur = Count × Offset × taille du maillon`, à réaccorder après **chaque** changement
d'échelle de la courbe.

L'ordre de la pile est contraint : **Array → Curve → SimpleDeform**. Inversé, la courbe
déformerait un maillon unique avant répétition.

L'Angle du Simple Deform arrive à **45° par défaut** ; il le descend à ~10° en le qualifiant
lui-même de *« really intense »*. Régler l'amplitude par le bas.

## Limites de cette analyse

La source est une **capture d'écran d'une page Patreon**, pas le fichier de l'auteur. Le
contenu utile ne fait que 992×558 : le dépôt ne garde qu'un proxy recadré sur la zone du
lecteur, et les petites valeurs d'interface ont été lues par recadrage et agrandissement.
Les derniers chiffres gardent une incertitude.

Frame End lu à **500** à t=321 s puis à **400** à partir de t=339 s. Le changement n'est ni
commenté ni capturé.

Un seul changement de plan détecté : le tutoriel est un screencast continu, la détection de
plans n'apporte rien et les frames régulières sont la seule couverture visuelle.

Les timings du transcript viennent de whisper large-v3-turbo. Ils ont été recoupés
visuellement en quatre points — Array à 69 s, Curve à 144 s, Simple Deform à 210 s, driver à
411 s — et concordent. Ailleurs ils ne sont pas garantis.

**Aucune étape n'a été reproduite dans Blender.** Tout ici est au niveau *observé*. Rien
n'est au niveau *validé*.

## Ce qui reste ouvert

L'auteur ne montre jamais comment il boucle **exactement** une séquence : le collage de clés
prolonge la boucle, mais la longueur totale n'est pas annoncée comme un multiple de la
période. L'interpolation des clés n'est pas ouverte dans le Graph Editor — Bézier par défaut
est probable, non vérifié. Le matériau chrome de ses rendus finaux n'est pas traité.

## Portage vers le dépôt

Le dépôt travaille à **24 fps**. Période 100 frames à 60 fps = 1,667 s = **40 frames** à
24 fps ; le décalage de 25 frames devient **10 frames** ; le diviseur du driver passe de 60
à **24**.

L'amplitude de 10° vaut pour ses scènes verticales. Sur un sujet de 16 cm cadré serré, elle
se rejuge au rendu.

Compatibilité contractuelle : cette technique anime des **déformeurs**, pas la transform du
sujet. Elle ne perturbe donc ni la pénétration, ni l'écart d'appui, ni la dérive de contact —
à condition de ne l'appliquer qu'à des objets de **décor**, jamais à un sujet dont le contrat
physique impose une géométrie rigide.

## Promotion

Non promue en workflow. `workflows/catalog/` exige entrées typées, script idempotent,
manifeste de sortie, mode opératoire dans l'app et gate reproductible : aucun n'existe encore
pour cette technique. Candidature enregistrée dans `analysis.json → promotion_candidate`.
