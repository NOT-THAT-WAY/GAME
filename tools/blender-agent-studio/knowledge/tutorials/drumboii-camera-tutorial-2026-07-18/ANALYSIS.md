# Analyse — Blender Camera Tutorial / Drumboiii

## Idée centrale

La caméra n’est pas traitée comme un déplacement linéaire entre deux poses. Chaque geste est
construit comme un mouvement avec masse:

```text
pose → anticipation opposée → mouvement principal → recul/settling
 K1            K2                    K3                  K4
```

Le mouvement important se produit entre K2 et K3. K1–K2 crée l’élan; K3–K4 absorbe le
mouvement. L’auteur répète ce motif localement tout au long du plan.

## Chapitres

| Timecode | Sujet |
|---|---|
| 00:00–01:32 | lecture des canaux caméra dans le Dope Sheet |
| 01:32–02:00 | animation en 60 fps et conversion des frames |
| 02:00–03:18 | anticipation, déplacement principal et rebound |
| 03:18–05:35 | micro-flottement au milieu d’un hold |
| 05:35–09:35 | répétition du motif et règle des quatre clés |
| 09:35–12:15 | focus distance et f-stop synchronisés |
| 12:15–13:55 | Track To vers un Empty |
| 13:55–15:25 | déplacement du centre d’attention |
| 15:25–17:57 | rebond du target et retard de réaction volontaire |

## Techniques reproductibles

### Règle des quatre clés

1. K1: pose de départ.
2. K2: petit déplacement opposé à la direction souhaitée.
3. K3: déplacement principal, nettement plus rapide.
4. K4: petit retour depuis l’extrême pour absorber l’énergie.

Cette règle décrit un motif de timing, pas des distances fixes. Les amplitudes doivent être
proportionnelles à la taille du sujet et contrôlées dans le Graph Editor.

### Floating hold

Entre deux poses presque identiques, ajouter une clé centrale légèrement décalée en Z crée un
flottement. Cette technique est optionnelle: pour une frame d’identité, un compositing précis
ou un conditioning vidéo, conserver un vrai still peut être préférable.

### Focus

L’auteur vérifie le focus à chaque pose caméra majeure, ajuste `Focus Distance`, puis insère
une clé avec `I`. `F-Stop` est également visible dans les canaux animés. Cette méthode permet
un focus pull expressif mais demande un nouveau contrôle après toute modification de caméra.

### Track To et cible animée

La caméra regarde un Empty invisible au rendu. L’Empty devient le contrôle de composition:
il passe de la machine à laver au bloc audio, puis suit un objet qui surgit. Un décalage de
quelques frames derrière le mouvement du sujet simule la réaction imparfaite d’un opérateur.

## Conversion vers Blender Studio

Le projet montré est en 60 fps, tandis que le pipeline Pulsed utilise 24 fps. Convertir les
durées en secondes ou appliquer `frames_cible = frames_source × 24 / 60`. Ne jamais recopier
les numéros de frames tels quels.

Le rig interne recommandé reste:

```text
ROOT → PIVOT → CAMERA
ROOT → TARGET
CAMERA --Track To--> TARGET
```

Les nouveaux assets DRUMBOII se prêtent particulièrement aux transferts d’attention:

- Gameboii: écran → D-pad → boutons;
- Flip Phone: écran → charnière → clavier;
- Traffic Light: bloc supérieur → bloc latéral;
- Blob Bike: carénage avant → guidon → roues;
- Blob Speaker: contrôles supérieurs → coque → pieds.

## Limites observées

- les handles et interpolations exacts ne sont pas expliqués;
- les amplitudes sont jugées visuellement, sans valeurs normalisées;
- la phrase Whisper sur le retard contient une erreur: l’image indique quelques frames de
  retard, pas plusieurs secondes;
- un excès d’anticipation/rebound donne un wobble décoratif au lieu d’une caméra crédible.

Voir `analysis.json` pour le contrat complet, les preuves et le blueprint de workflow.
