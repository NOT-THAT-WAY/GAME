# Standard cinématique et rendu

## Plan et caméra

Chaque plan possède intention, sujet, action, durée, focale, mouvement, target, focus et marge de
sécurité. Travailler en anticipation → travel → recovery pour un mouvement motivé. Vérifier clipping,
corridor caméra, vitesse angulaire, parallax et continuité entre plans.

## Lumière et monde

Construire par couches attribuables : monde/HDRI, key, fill ou bounce, rim/backlight et accents.
Séparer éclairage environnemental et ciel visible lorsque nécessaire. Tester chaque couche en A/B ;
ne pas compenser une composition faible par plus de contraste ou de bloom.

## Matériaux et couleur

Déclarer color management, exposition, espaces colorimétriques des textures et cible de livraison.
Vérifier noirs, highlights, peau ou matériaux critiques sur plusieurs vues. Le grain, glare, DOF et
motion blur sont du polish, jamais des correctifs structurels.

## Gates

1. Clay : silhouette, échelle, supports et composition.
2. Poses : début, anticipation, action, impact, récupération, fin.
3. Lumière : couches isolées puis combinaison.
4. Preview : mouvement complet sans frame manquante.
5. Final : résolution, samples, denoise, color management et encodage déclarés.

Contrôler avec `ffprobe` durée, fps, résolution, codec et audio. Générer une contact sheet. Examiner
première/dernière frame, cuts, flashes, macroblocking, flicker, focus et continuité. Une image fixe ne
valide pas un film.
