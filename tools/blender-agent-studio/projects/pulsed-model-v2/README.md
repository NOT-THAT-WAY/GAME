# Pulsed v2 — reconstruction depuis vidéo

Refonte complète du modèle Pulsed à partir de **deux vidéos de référence**, en
remplacement du v1 (`Pulsed_3D_model.blend` à la racine) qui avait été construit
sur des images fixes générées par IA.

Le `.blend` source à la racine du dépôt **n'est jamais ouvert ni modifié** par ce
projet.

## Pourquoi une v2

Le v1 souffrait d'un défaut de source, pas d'exécution : ses références étaient
des images IA indépendantes, donc sans cohérence 3D entre elles. Certaines
décisions verrouillées à l'époque se révèlent fausses une fois l'objet vu sous
tous les angles dans une même prise — la principale étant « toutes les tranches
sont lisses, pas de ports ». Voir `audits/pulsed-v1-vs-v2.md`.

## Chaîne de production

```bash
cd projects/pulsed-model-v2
BL="/Applications/Blender.app/Contents/MacOS/Blender"

# 1. Intake d'une vidéo de référence -> frames + planche contact
./intake_video.sh source-videos/pulse_ref_B.mp4 refB

# 2. Mesures numériques (bbox par frame, ombre exclue)
/Applications/Blender.app/Contents/Resources/5.1/python/bin/python3.13 measure_frames.py

# 3. Construction du modèle (repart de zéro à chaque fois)
"$BL" -b --python build_v2.py

# 4. Gates de comparaison contre les refs
PV2_SAMPLES=110 "$BL" -b scene/pulsed_v2.blend --python render_gate.py -- <tag>

# 5. Animation puis rendu
"$BL" -b scene/pulsed_v2.blend --python animate.py
PV2_SAMPLES=72 "$BL" -b scene/pulsed_v2_anim.blend --python render_anim.py -- v1

# 6. Export
"$BL" -b scene/pulsed_v2.blend --python export_glb.py
```

Le build est **entièrement reproductible** : `build_v2.py` repart d'une scène
vide, donc toute correction se fait dans le script, jamais à la main dans le
`.blend`.

## Fichiers

| Fichier | Rôle |
|---|---|
| `audits/pulsed-object-map-v3.md` | **source de vérité** des cotes et positions |
| `audits/frame-measurements.json` | bbox mesurée sur chaque frame |
| `audits/pulsed-v1-vs-v2.md` | ce qui change et pourquoi |
| `pulsed_lib.py` | primitives : silhouette, loft, booléens, helpers |
| `materials.py` | améthyste translucide, PCB procédural, plastiques, écran |
| `controls.py` | molette, SYNC, D-pad, sliders, sérigraphie, tranches |
| `internals.py` | PCB + composants, module écran, UI émissive (Geometry Nodes) |
| `build_v2.py` | assemblage complet |
| `studio.py` | monde, lumières, caméras de gate |
| `animate.py` | chorégraphie de la démo fonctionnelle |
| `measure_frames.py`, `intake_video.sh` | outillage de référence |

## Pièges rencontrés (ne pas les refaire)

1. **Booléen avant Solidify = géométrie folle.** Les demi-coques sont des
   surfaces *ouvertes* ; un booléen sur du non-manifold produit n'importe quoi.
   Le `Solidify` doit être **premier** dans la pile — c'est lui qui ferme la coque.
2. **`use_even_offset` sur Solidify** crée des pointes énormes sur les arêtes
   issues des booléens. Désactivé.
3. **`hide_viewport = True` sur un cutter casse le booléen** (l'objet sort du
   depsgraph). Utiliser `hide_render` + `display_type = "WIRE"`.
4. **Absorption volumique sur une paroi mince : à éviter.** Cycles finit par
   traiter toute la cavité du boîtier comme le volume → brouillard violet qui
   noie le PCB. La teinte passe par la couleur de transmission.
5. **Échelle des textures procédurales** : les coordonnées Objet du PCB vont à
   ±6,9 BU. Une échelle de 26 donnait ~360 bandes en travers → aliasing en
   aplat gris uniforme.
6. **Un seuil simple sur une texture ≠ des pistes.** `max(saw1, saw2) > 0.66`
   laissait passer 56 % de cuivre. Il faut une bande *fine* (rampe à 3 arrêts).
7. **Fond crème + intérieur sombre** ne se règlent pas avec la même valeur.
   Le nœud Light Path (fort pour les rayons caméra, faible pour le reste) sépare
   les deux ; sinon soit le fond est gris, soit le boîtier est délavé.
8. **Blender 5.1 : `Action.fcurves` n'existe plus.** Passer par
   `action.layers[].strips[].channelbags[].fcurves`.
