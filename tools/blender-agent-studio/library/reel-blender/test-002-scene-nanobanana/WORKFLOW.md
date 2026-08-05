# WORKFLOW — scène Nano-Banana → image ref du v2v

La chaîne complète Blender × Seedance avec la couche scène :

```
1. Chorégraphie Blender (blender-choreography/, sb-xxx)        → squelette .mp4
2. Scène Nano-Banana (CE dossier)                              → image ref designée
   nano_banana_pro MCP Higgsfield · ref = canonical front · 9:16 · ~2 crédits
3. Gate Sliz sur les DEUX (mouvement + scène)
4. Seedance v2v (recette C″ VIDEO-FIRST) :
   image_references = LA scène retenue (remplace la front nue)
   video_references = le squelette
   prompt = MOTION SOURCE + LIGHTING aligné sur la scène
5. Éval vs success criteria brief → notes.md du run
```

## Règles de la scène (résumé — détail dans brief.md)

- Device = clone exact de la canonique, paysage ENTIER, jamais redessiné.
- Interdits : overhead spotlight / light cone / beam / rays / dust (le prior qu'on tue).
- Scène compatible trajectoire : la caméra du squelette passe sous l'objet → lévitation,
  sol lointain ou gradient pur. Jamais de sol au niveau de l'objet.
- Vérifier labels (SYNC ↔ « EVNC ») et wordmark sur CHAQUE image avant usage en ref.
- Prompt v2v : la section LIGHTING doit DÉCRIRE la scène retenue (cohérence pixels/texte).

## Itération

Chaque batch de concepts dans `runs/<date>_scene-concepts-vN/` (jamais d'écrasement).
Raffiner un concept = edit-chaining : relancer `nano_banana_pro` avec le PNG du concept
en ref + la correction en prompt.
