# FL Studio Box — ancien template à cinq crops

> Ce template est conservé comme prototype. Pour les nouveaux contenus, utiliser
> `projects/fl-studio-box-projection-template/FL_Studio_Box_Projection_Template.blend`,
> qui projette une seule vidéo continue et produit de meilleurs raccords.

Scène maître prévue pour recevoir de nouvelles captures FL Studio sans reconstruire la
boîte, la caméra, les lumières ou les matériaux.

## Utilisation rapide

1. Ouvrir [FL_Studio_Box_Template.blend](FL_Studio_Box_Template.blend).
2. Copier une capture FL Studio 16:9 dans `incoming/`.
3. Dans Blender Studio, lancer **Adapter une vidéo — FL Studio Box**.
4. Indiquer son chemin relatif, son point de départ et la durée utile.
5. Lire la timeline et vérifier les cinq surfaces.
6. Lancer **Gate de keyframes** avec `USTUDIO_MEDIA_`.
7. Faire `Save As` sous un nouveau nom seulement après validation.

## Slots vidéo

| Slot | Surface dans la boîte | Matériau Blender |
|---|---|---|
| Playlist | mur du fond | `M_MOVIE_PLAYLIST` |
| Browser | paroi gauche | `M_MOVIE_BROWSER` |
| Mixer | paroi droite | `M_MOVIE_MIXER` |
| Piano roll | plancher incliné | `M_MOVIE_PIANO_ROLL` |
| Channel rack | module au premier plan | `M_MOVIE_CHANNEL_RACK` |

Le workflow génère cinq clips H.264 dans un nouveau dossier `renders/`, relie les Movie
Textures, adapte la timeline à la durée et ajoute cinq marqueurs de gate. Il ne sauvegarde
jamais silencieusement le fichier Blender.

La scène contient déjà un média de démonstration dans `media/current/`. Les détails
techniques des slots sont dans [slot-map.json](slot-map.json).

## Exigences pour les nouvelles vidéos

- capture FL Studio seule, sans cadre ou boîte déjà présente;
- cadrage 16:9 recommandé;
- interface lisible, stable et sans notifications macOS;
- idéalement playlist en haut, browser à gauche, piano roll au centre, mixer à droite et
  channel rack en bas;
- MP4, MOV ou M4V, entre 1 et 60 secondes par adaptation.
