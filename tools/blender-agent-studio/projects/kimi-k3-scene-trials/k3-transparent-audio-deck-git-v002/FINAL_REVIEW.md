# Revue finale — k3-transparent-audio-deck-git-v002

## Verdict

`revise` — **84,4/100**, sans échec critique physique.

Le test de bout en bout du clone Git permanent est réussi techniquement. La même image a été admise,
analysée et transformée en un nouveau starter `ObjectSculptSpec` par
`third_party/img2threejs/`. Le bridge a ensuite produit un `.blend`, un `.glb`, des vues de contrôle,
un gate lumière et une preview de huit secondes dans un projet isolé. Le résultat reste un prototype
de reconstruction visible-side, pas une reproduction produit exacte.

## Ce que le test prouve

- Le clone upstream complet au commit `8b53125081c3798cf95bd517b64be024515a1c8d`
  fonctionne depuis son emplacement permanent.
- L’image 1199×1592 passe le probe et le gate d’admission.
- Le starter a été généré à neuf depuis cette image. Upstream ne produisant pas encore de
  `blenderRecipe`, seul le recipe déjà revu de `v001` a été réutilisé comme fixture de régression;
  les anciens résultats, états et reviews n’ont pas été copiés.
- La spec normalisée passe `--strict-quality` sans erreur ni avertissement : 22 composants,
  13 matériaux et 6 systèmes de répétition.
- Blender 5.1.1 construit 86 objets avec `--background --factory-startup`. Le `.blend` se rouvre
  proprement avec 94 objets, 74 meshes, 14 matériaux, une caméra active, 192 frames et `dirty=false`.
- Le GLB réimporté contient 77 meshes, 6 empties et 15 matériaux, sans caméra ni lumière exportée.
- La géométrie évaluée touche le support : pénétration `0 m`, gap `0 m`. La clearance caméra
  minimale vaut `0,418083 m` sur 192 frames, sans frame hors seuil.
- La preview est un H.264 576×720, 24 fps, 192 frames et exactement 8,000 secondes.

## Défaut d’intégration trouvé et corrigé

Un starter fraîchement produit avait `lightingFromPhoto: []`; le validateur strict refusait donc le
lighting-pass. Le normaliseur versionné ajoute désormais, uniquement quand la liste est absente,
un contrat concret pour key/reflection, environment fill, rim/glimmers, exposition, tone mapping,
fond et contact shadow. Après cette correction, la validation stricte passe sans avertissement.

## Gate amont encore bloquant

Le `structural-pass` reste volontairement bloqué. Le Tier‑1 mesure un IoU de silhouette de `0,5901`
pour un seuil verrouillé à `0,85`, ainsi qu’un delta de ratio de `0,058` pour un maximum de `0,05`.
Ces valeurs reproduisent exactement le défaut du test précédent, ce qui confirme le caractère
déterministe du gate. Les seuils n’ont pas été élargis.

Le gate multi-angle passe : front, profil et arrière ne s’effondrent pas, donc l’asset est bien
volumétrique. Cela ne compense pas le défaut de correspondance structurelle. La transparence, la
grande ombre détachée, la pose flottante et le fond non uniforme rendent le masque de référence
imparfait, mais les proportions du speaker et du transport restent aussi à affiner.

## Limites visuelles

La face arrière est une continuité conservatrice et apparaît trop claire sous ce setup; elle n’est
pas présentée comme une observation. Les mécanismes internes sont des couches visuelles séparées,
pas un mécanisme fonctionnel prouvé. Le polycarbonate EEVEE est une approximation de transmission.
Le texte `AUDIO // 01` est générique, car la marque de la référence est illisible.

## Suite recommandée

Pour débloquer le structural-pass, fournir au minimum une face, un profil, un dos et une vue
supérieure sur fond uniforme, sans ombre confondue avec la silhouette. Recalibrer ensuite les
dimensions du speaker, de la roue et du rail, puis relancer le gate sans modifier ses seuils.
