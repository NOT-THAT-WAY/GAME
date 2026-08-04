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

            // Aucun collider automatique : le labyrinthe embarque de la végétation et
            // des props denses qu'il serait absurde de faire cuire en MeshCollider.
            // MazePlaytestBuild pose les colliders sur les seuls objets qui bloquent
            // réellement le joueur. Le personnage, lui, utilise un CharacterController.
            importer.addCollider = false;
        }
    }
}
