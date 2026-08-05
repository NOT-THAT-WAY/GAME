# test-002 — Scène Nano-Banana pour le v2v Blender × Seedance

**Date** : 2026-07-13 · **Demande Sliz** : « le spot lumineux d'au dessus pas très beau,
on peut faire une scene dans laquelle on met le plugin — utilise nanobanana via crédits
Higgsfield pour voir ».

## Problème

Le run 3 de test-001 (recette C″ VIDEO-FIRST) est validable côté mouvement/identité, mais
Seedance a inventé un **cône de projecteur tombant du haut du cadre** — le prior « product
shot dans le noir » que rien dans nos pixels d'entrée ne contredisait (front nue sur fond
neutre + prompt near-black). Cf.
`prompt-library/failure-patterns/v2v-neutral-void-invents-overhead-spotlight.md`.

## Objectif

Explorer des **scènes designées** générées Nano-Banana (`nano_banana_pro`, MCP Higgsfield)
dans lesquelles le device est posé — la scène devient l'image ref du v2v et fixe
fond + lumière à la place du prior.

## Contraintes (héritées de C″ + DA)

1. Device EXACTEMENT comme la canonique front : paysage, ENTIER, layout 6 contrôles,
   wordmark — jamais redessiné.
2. DA studio 3D fictif : pas de scène réelle, pas de main, near-black + accents
   cyan/magenta (teal=onde, lavande=coque).
3. Éclairage designé latéral/bas — interdits explicites : NO overhead spotlight,
   NO light cone/beam from above, NO volumetric rays, NO dust.
4. **Compatibilité trajectoire squelette** : sb-003 passe SOUS l'objet (contre-plongée
   z −3,5) → pas de sol au niveau de l'objet ; lévitation / sol lointain / gradient pur.

## Success criteria

1. ✓/❌ Identité device intacte (layout, proportions, wordmark, labels SYNC).
2. ✓/❌ Paysage entier, marges généreuses, centré.
3. ✓/❌ Aucun spot/cône/beam venant du haut.
4. ✓/❌ DA respectée (near-black, cyan/magenta, fictif).
5. ✓/❌ Scène compatible avec les beats bas du squelette sb-003.

## Lane & coûts

MCP Higgsfield `nano_banana_pro` (routé `nano_banana_2`), 9:16, 1k, ref = canonical front
(media_id `4514c2bf-17a7-4061-b989-a4d8751c609a`, réutilisé de test-001).
2 crédits/image · run v1 = 3 concepts = 6 crédits · solde après : **731**.

## Suite (après gate Sliz)

Le concept retenu devient l'image ref du premier run Seedance de **sb-003-arc-crane-vertigo**
(recette C″ : scène + squelette, ~21 crédits) — génération toujours en attente de la
validation du mouvement Blender ET du choix de scène.
