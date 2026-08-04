using UnityEditor;

namespace NotThatWay.Game.Editor
{
    /// <summary>
    /// Réglages d'import des modèles du test de labyrinthe. Les FBX viennent de
    /// Blender avec la convention Unity (axis_forward=-Z, axis_up=Y, échelle 1 m),
    /// donc aucune correction d'axe ni d'échelle n'est appliquée ici.
    /// </summary>
    public sealed class PlaytestModelPostprocessor : AssetPostprocessor
    {
        private const string MazeModelPath = "Assets/_Project/Maze/Maze16x16.fbx";
        private const string PlayerModelPath = "Assets/_Project/Player/PersoBoule.fbx";

        private void OnPreprocessModel()
        {
            if (assetPath != MazeModelPath && assetPath != PlayerModelPath)
                return;

            var importer = (ModelImporter)assetImporter;

            // Le FBX du labyrinthe embarque les caméras et lumières de rendu Blender ;
            // l'éclairage de la scène Unity est monté par MazePlaytestBuild.
            importer.importCameras = false;
            importer.importLights = false;
            importer.importAnimation = false;
            importer.importBlendShapes = false;
            importer.animationType = ModelImporterAnimationType.None;
            importer.importConstraints = false;

            // Le décor est statique : un MeshCollider par maillage suffit et évite
            // de dessiner les collisions à la main. Le joueur, lui, utilise un
            // CharacterController et ne doit porter aucun collider de maillage.
            importer.addCollider = assetPath == MazeModelPath;
        }
    }
}
