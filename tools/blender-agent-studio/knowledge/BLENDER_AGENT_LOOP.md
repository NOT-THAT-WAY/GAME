# Boucle agent visuelle Blender — protocole de production

État: 19 juillet 2026. Ce protocole est indépendant du modèle: Codex, Claude ou tout autre
agent MCP avec vision peut l'appliquer.

## Principe

Une commande réussie ne prouve pas qu'une image est réussie. Une belle image ne prouve pas
que la scène est livrable. Chaque itération doit donc passer deux boucles séparées:

```text
brief mesurable → modification bornée → rendu preview → diagnostic visuel → correction
                                      ↓
                         audit technique → gate humain → sauvegarde/export
```

La boucle visuelle traite les pixels. L'audit technique traite la scène, les dépendances et
la géométrie. Aucun des deux ne remplace l'autre.

## Contrat du brief

Avant toute écriture, convertir la demande en critères observables:

- sujet et collection cible;
- caméra: angle, focale ou plage, marges et format;
- lumière: direction, contraste, zones à préserver et clipping interdit;
- matière: couleur, roughness, transmission, IOR et reflets interdits;
- fond et séparation de silhouette;
- éléments immuables: proportions, logo, ports, écran et détails canoniques;
- résolution preview et résolution finale;
- budget maximal de trois itérations automatiques par catégorie.

Les adjectifs seuls (`premium`, `cinématique`, `propre`) ne sont pas des critères. Ils doivent
être traduits en propriétés vérifiables, puis confirmés par le gate humain.

## Ordre des corrections

Corriger une seule famille de causes par passe afin de garder une attribution claire:

1. visibilité: caméra active, sujet dans le cadre, clipping et occlusion;
2. composition: focale, distance, hauteur, marges et horizon;
3. exposition: énergie, taille et position des lights, exposition et highlights;
4. silhouette: séparation sujet/fond et rims;
5. matière: assignation, roughness, transmission, IOR et normales;
6. détails: labels, ports, écran et microgéométrie;
7. mouvement: poses clés, continuité, overshoot et holds.

Une correction de matériau ne doit pas déplacer la caméra. Une correction de cadrage ne doit
pas reconstruire le produit. Si une passe touche plusieurs familles, elle doit être divisée.

## Preuve de chaque itération

Chaque dossier d'itération conserve:

- brief normalisé et références retenues;
- capture avant et capture après;
- paramètres modifiés avec anciennes et nouvelles valeurs;
- diagnostic: symptôme visible, cause supposée, action, résultat;
- scène, caméra, frame, moteur, résolution, samples et color management;
- verdict `improved`, `unchanged`, `regressed` ou `human-review`.

Ne jamais comparer deux rendus dont la caméra, la frame ou le transform de vue ont changé sans
le déclarer. Pour les matières produit, comparer AgX et Khronos PBR Neutral seulement comme
deux looks explicitement nommés; ne pas les mélanger silencieusement.

## Conditions d'arrêt

L'agent s'arrête quand l'une de ces conditions est vraie:

- tous les critères mesurables passent;
- trois corrections de la même catégorie n'améliorent pas le verdict;
- la correction exige un choix de goût non contenu dans le brief;
- identité, dimensions ou topologie risquent d'être altérées;
- une dépendance manque ou Blender/MCP devient instable;
- le prochain changement demande une sauvegarde, un export final ou un accès externe.

L'arrêt n'est pas un échec: il transfère une décision de goût ou de risque à l'humain.

## Gates minimaux

### Gate visuel

- sujet entièrement lisible aux frames prévues;
- aucune collision ou géométrie inventée visible;
- highlights non clippés sur les zones critiques;
- silhouette séparée du fond;
- focale et perspective cohérentes entre itérations;
- détails canoniques conservés.

### Gate technique

- unités explicites;
- chemins externes résolus ou fichiers packés;
- transforms intentionnels;
- aucune géométrie dégénérée;
- non-manifold et bords ouverts documentés selon le type d'asset;
- UV et matériaux présents quand le livrable les exige;
- caméra, color management et réglages de rendu consignés;
- export testé par réimport ou lecteur indépendant.

## Application dans Blender Studio

1. **Audit profond scène & assets** avec contrôle de topologie.
2. Workflow de création ciblé, sans sauvegarde automatique.
3. **Gate de keyframes** en preview EEVEE basse résolution.
4. Diagnostic structuré et correction d'une seule catégorie.
5. Au maximum trois passages automatiques, chacun dans un nouveau dossier.
6. Gate humain.
7. Audit final, sauvegarde décidée par l'humain, puis export versionné.

## Sources primaires

- [Blender Color Management](https://docs.blender.org/manual/en/latest/render/color_management.html)
- [Blender BMesh API](https://docs.blender.org/api/current/bmesh.html)
- [Blender Mesh API](https://docs.blender.org/api/5.0/bpy.types.Mesh.html)
- [Blender command-line rendering](https://docs.blender.org/manual/en/latest/advanced/command_line/render.html)
- [Blender MCP](https://github.com/ahujasid/blender-mcp)
- [Risque d'exécution Python de Blender MCP](https://github.com/ahujasid/blender-mcp/issues/201)
- [Draft and Refine with Visual Experts, CVPR 2026](https://openaccess.thecvf.com/content/CVPR2026/html/Jeong_Draft_and_Refine_with_Visual_Experts_CVPR_2026_paper.html)
