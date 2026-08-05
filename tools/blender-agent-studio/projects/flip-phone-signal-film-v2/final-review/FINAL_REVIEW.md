# LAST SIGNAL V2 — évaluation finale

## Résultat

Score pondéré V2 : **78,4/100**, contre **49/100** pour V1.

| Catégorie | Poids | V1 | V2 | Évolution |
|---|---:|---:|---:|---:|
| Histoire et causalité | 15% | 50 | 82 | +32 |
| Lisibilité du produit | 12% | 63 | 76 | +13 |
| Mouvement objet | 12% | 34 | 85 | +51 |
| Caméra et raccords | 12% | 38 | 74 | +36 |
| Rythme et respiration | 12% | 36 | 78 | +42 |
| Décor et profondeur | 8% | 48 | 75 | +27 |
| Matériaux et redesign | 8% | 62 | 78 | +16 |
| Lumière et couleur | 8% | 61 | 72 | +11 |
| Typographie et graphisme | 5% | 42 | 74 | +32 |
| Finition technique | 8% | 65 | 86 | +21 |

## Comparaison mesurée

| Mesure | V1 | V2 | Résultat |
|---|---:|---:|---|
| Mouvement moyen inter-frame | 5,9903 | 2,2086 | −63,1% |
| Mouvement P95 | 14,6090 | 5,9388 | −59,3% |
| Pics temporels | 8 | 3 | −62,5% |
| Pixels clippés moyens | 0,2036% | 0,0052% | −97,4% |
| Runs noirs détectés | 0 | 0 | stable |
| Ratio noir moyen | 51,9963% | 67,9648% | scène V2 trop sombre |

Les trois pics V2 correspondent aux coupes de 6, 12 et 18 secondes. Ils restent visibles, mais aucune image parasite ne se trouve entre les plans. Le pic critique de 86,76 de V1 a disparu ; le maximum V2 est 33,43.

## Ce qui fonctionne

- Le récit est causal : scan → trajet → arrêt → ouverture → message → balises → élévation.
- La charnière est le seul parent mécanique animé ; ses descendants héritent sans double transform.
- Le transport possède une vitesse linéaire, une caméra fixe et un chariot visible solidaire du produit.
- Le chariot s'élève au-dessus du bord du socle, se pose dessus et reste présent : aucun objet ne traverse le tapis ou le socle.
- La charnière utilise une limite mesh-spécifique de 140° : coque extérieure visible et clavier couvert à la fermeture, écran et clavier du même côté à l'ouverture.
- Les caméras ne concurrencent plus l’action principale.
- La palette graphite/ivoire/cuivre/turquoise/orange donne une identité moins générique.
- Le décor reste derrière le corridor produit après deux rejets de gates pour occlusion.
- Le clipping lumineux a presque disparu.
- Les 24 dernières images sont pixel-identiques. Les hash de fichiers diffèrent seulement à cause des métadonnées PNG ; la différence RGB mesurée est exactement nulle.
- Le film final contient 720 images, 24 fps et 30 secondes avec audio.

## Limites honnêtes

- La scène reste trop noire : 68% de pixels proches du noir. Un prochain étalonnage devrait relever les midtones du décor sans blanchir le produit.
- Les holds de 0–1,29 s, 4,67–6 s et 15,63–17,04 s sont intentionnels mais pourraient être raccourcis de 8 à 12 frames pour une version publicitaire plus nerveuse.
- Les coupes restent des ruptures mesurables. Un match cut plus strict sur la taille écran réduirait encore les trois pics.
- Le message `HELLO` est surtout porté par la typographie d’interface ; le texte 3D attaché à l’écran est trop petit à 540p.
- Les balises orange deviennent dominantes sur certains plans. Leur émission pourrait être réduite de 10 à 15%.

## Verdict de production

La V2 passe les gates de cohérence, mécanique, drift, clipping et repos terminal. Elle est suffisamment propre pour démontrer le workflow complet et nettement supérieure à V1. Elle n’est pas notée au-dessus de 80 à cause de la densité de noirs, des trois raccords encore abrupts et de la lisibilité limitée du message sur l’écran physique.
