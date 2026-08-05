# Analyse — Blender Lighting Tutorial / Drumboiii

## Ce que sa vision change

Drumboiii ne traite pas l’éclairage comme un preset trois-points posé avant de regarder le
rendu. Il part du résultat caméra, construit une base volontairement insuffisante, puis ajoute
une fonction visuelle à la fois : reflet, contour, glimmer local. La question n’est donc pas
« combien de lampes ? », mais « quelle différence exacte cette lampe apporte-t-elle ? ».

Cette méthode devient prioritaire dans Blender Studio pour la direction lumière et complète
son tutoriel caméra : la caméra exprime la masse avec anticipation/travel/recovery, tandis que
la lumière décrit la forme par reflets et séparation de silhouette.

## Déroulé observé

| Timecode | Couche | Fonction |
|---|---|---|
| 00:00–00:45 | Cycles, lumières coupées | baseline noire et organisation de scène |
| 00:45–02:19 | monde + HDRI à 0,7 | base contrôlée, ciel visible séparé de l’éclairage |
| 02:19–03:19 | Sun à 1,0 | sculpter les reflets par un angle oblique |
| 03:19–04:18 | Area arrière 1400 W | redonner volume, bords supérieurs et inférieurs |
| 04:18–05:10 | Area.001 440 W | glimmer local, notamment sur la chaîne |
| 05:10–06:10 | Area.002 170 W | détail latéral encore plus discret |
| 06:10–06:48 | Area.003 20 → 220 W | retour opposé renforcé parce que 20 W ne lisait pas |
| 06:48–07:26 | récapitulatif | conserver du headroom et éviter la surexposition |

Les quatre Area Lights visibles sont blanches, carrées, normalisées et mesurent 1 m dans
cette scène. Les puissances donnent surtout un rapport utile : `1 / 0,314 / 0,121 / 0,157`
par rapport au backlight dominant. Elles ne doivent pas être recopiées comme vérité absolue.

## Architecture du monde

Le tutoriel sépare deux fonctions avec `Light Path → Is Camera Ray → Mix Shader` :

```text
HDRI Background (illumination/reflets, strength 0.5–0.7) ─┐
                                                          ├─ Mix → World Output
Sky Background (visible par la caméra) ───────────────────┘
                        Is Camera Ray ─────────────────────┘
```

Le montage exact du ciel est montré mais n’est pas enseigné ici ; Drumboiii renvoie à un
autre tutoriel. Le nouveau workflow reproduit donc l’architecture validée et utilise un ciel
Nishita comme fallback explicite, sans prétendre copier son ciel personnalisé.

## Méthode promue

1. verrouiller la composition caméra et la silhouette ;
2. poser l’environnement à 0,5–0,7 pour garder du headroom ;
3. orienter le Sun jusqu’à obtenir des reflets qui expliquent la forme ;
4. poser un backlight fort derrière le sujet, dirigé vers la caméra ;
5. ajouter seulement des glimmers faibles avec un rôle local nommé ;
6. rendre base → sun → back → side A → side B → retour ;
7. déplacer, renforcer ou supprimer une lampe dont l’A/B ne montre rien d’utile ;
8. répéter le gate aux poses caméra majeures.

## Implémentation

- `studio-lighting` possède maintenant le preset `drumboiii-layered`, orienté relativement à
  la caméra et mis à l’échelle depuis les bounds du sujet ;
- `drumboiii-lighting-gate` rend six états cumulatifs et un manifeste ;
- le moteur source est Cycles, mais le gate peut employer Eevee pour une preview rapide ;
- aucune exécution ne sauvegarde silencieusement le `.blend`.

Voir `analysis.json` pour les preuves, valeurs observées, limites et contrat complet.
