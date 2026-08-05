# DRUMBOII GAMEBOII — Arcade Environment

Mise en scène du `DRUMBOII_GAMEBOII` existant dans un environnement arcade/Y2K.

Le projet applique les principes du tutoriel Blender 5.0 :

- collections séparées pour produit, environnement, lumière et caméra ;
- décor limité à ce que voit la caméra ;
- éclairage par rôles : sun key, sky fill, indoor bounce et portal rim ;
- focus caméra explicite sur l’écran ;
- color management AgX Medium High Contrast ;
- comparaison de gate Eevee/Cycles avant décision de moteur.

Ouvrir `Drumboii_Gameboii_Arcade_Scene.blend`, passer en vue caméra et afficher le mode
Rendered. Les deux images du dossier `gate/` montrent le même cadrage dans Eevee et Cycles.

Le projet est reproductible avec :

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --python workflows/tools/create_gameboii_arcade_scene.py
```
