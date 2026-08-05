# DRUMBOII Blob Speaker — Camera Study

Projet autonome créé à partir de l’asset `BLOB_SPEAKER` et du knowledge extrait du tutoriel
DRUMBOII Camera Tutorial.

## Mouvement

- frame 1 — `K1_POSE`: composition trois-quarts;
- frame 24 — `K2_ANTICIPATION`: recul opposé au mouvement principal;
- frame 96 — `K3_MAIN_MOVE`: reveal rapproché vers les contrôles supérieurs;
- frame 132 — `K4_SETTLE`: léger retour après le point extrême;
- frame 144 — `REST`: repos final.

La caméra utilise `USTUDIO_TRACK_TO_DELAYED_TARGET`. La cible reçoit ses poses quatre frames
après la caméra pour reproduire la réaction opérateur décrite dans le tutoriel. Le focus repose
sur `USTUDIO_FOCUS_TARGET`; le `f-stop` est également animé aux poses majeures.

## Utilisation

Ouvrir `Drumboii_Blob_Speaker_Camera_Study.blend`, passer en vue caméra et lire les frames
1 à 144 à 24 fps. Les collections `CAMERA_RIG_TUTORIAL_K1_K4`, `LIGHTING_STUDIO`,
`ENVIRONMENT` et `PRODUCT_BLOB_SPEAKER` sont séparées pour permettre leur copie.

Le dossier `gate/` contient les cinq compositions de contrôle. `camera-study-preview.mp4`
permet de vérifier le mouvement sans ouvrir Blender.
