# Standard matériaux et textures

## Source

Consigner origine, licence, résolution, espace colorimétrique et transformations de chaque texture.
Ne jamais traiter une image téléchargée ou générée comme libre par défaut.

## PBR

- Base color et données couleur utilisent l’espace déclaré par le pipeline.
- Roughness, metallic, normal, height, AO et masques sont traités comme données non couleur lorsque
  requis.
- Déclarer convention de normal map et la tester dans la cible.
- Éviter valeurs physiquement impossibles sauf direction artistique explicite.
- Vérifier tiling, seams, mipmaps, anisotropie et compression à distance réelle.

## Budget

Déclarer nombre de texture sets, résolutions, bits, canaux packés, UDIM, texel density et mémoire
estimée. Un matériau héro et un prop de fond n’ont pas le même budget. Pour le temps réel, mesurer
shader complexity, transparence, overdraw et variantes.

## Gate

Présenter lumière neutre, lumière rasante et contexte cible. Vérifier cohérence d’échelle des détails,
réponse des highlights, noirs, alpha, displacement et correspondance bake high/low. Les textures et
leurs paramètres d’import figurent dans le manifeste de livraison.
