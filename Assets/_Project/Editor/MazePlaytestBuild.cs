using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text.RegularExpressions;
using FishNet.Component.Spawning;
using FishNet.Component.Transforming;
using FishNet.Managing;
using FishNet.Managing.Object;
using FishNet.Object;
using FishNet.Transporting.Tugboat;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace NotThatWay.Game.Editor
{
    /// <summary>
    /// Génère la scène jouable du labyrinthe 16x16 et ses builds. Comme le test de
    /// connexion, la scène n'est pas versionnée : elle est reconstruite depuis les
    /// assets et ce script, ce qui évite les conflits de fusion sur un `.unity`.
    /// </summary>
    public static class MazePlaytestBuild
    {
        private const string GeneratedDirectory = "Assets/_GeneratedLocal";
        private const string ScenePath = GeneratedDirectory + "/MazePlaytest.unity";
        private const string PrefabsPath = GeneratedDirectory + "/MazePlaytestPrefabs.asset";
        private const string PlayerPrefabPath = GeneratedDirectory + "/MazePlayer.prefab";
        private const string MazeModelPath = "Assets/_Project/Maze/Maze16x16.fbx";
        private const string MazeGridPath = "Assets/_Project/Maze/MazeGrid16x16.json";
        private const string PlayerModelPath = "Assets/_Project/Player/PersoBoule.fbx";
        private const string PreviewDirectory = "Logs/MazePlaytest";

        // Gabarit du personnage produit par build_character.py : 1,40 m, origine
        // aux pieds, yeux à 1,03 m.
        private const float PlayerHeight = 1.4f;
        private const float PlayerRadius = 0.45f;
        private const float EyeHeight = 1.05f;
        private const float SpawnHeight = 0.2f;

        private static readonly Color SkyColor = new(0.96f, 0.85f, 0.72f);

        [MenuItem("GAME/Maze Playtest/Create Scene")]
        public static void CreateScene()
        {
            EnsureGeneratedDirectory();

            var layout = ReadLayout();
            var playerPrefab = CreatePlayerPrefab();
            var prefabCollection = LoadOrCreatePrefabCollection();
            prefabCollection.Clear();
            prefabCollection.AddObject(playerPrefab, true);
            EditorUtility.SetDirty(prefabCollection);

            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            CreateEnvironment();
            var spawns = CreateSpawnPoints(layout);

            var networkRoot = new GameObject("NetworkManager");
            networkRoot.AddComponent<Tugboat>();
            var networkManager = networkRoot.AddComponent<NetworkManager>();
            networkManager.SpawnablePrefabs = prefabCollection;
            networkRoot.AddComponent<ConnectionSmokeTest>();

            var spawner = networkRoot.AddComponent<PlayerSpawner>();
            spawner.Spawns = spawns;
            var serializedSpawner = new SerializedObject(spawner);
            serializedSpawner.FindProperty("_playerPrefab").objectReferenceValue = playerPrefab;
            serializedSpawner.ApplyModifiedPropertiesWithoutUndo();

            EditorSceneManager.MarkSceneDirty(scene);
            if (!EditorSceneManager.SaveScene(scene, ScenePath))
                throw new InvalidOperationException($"Unable to save {ScenePath}.");

            AssetDatabase.SaveAssets();
            Debug.Log($"[GAME-MAZE] Generated {ScenePath} with {spawns.Length} spawn point(s).");
        }

        [MenuItem("GAME/Maze Playtest/Build macOS")]
        public static void BuildMac()
        {
            Build(BuildTarget.StandaloneOSX, "Builds/MazePlaytest/macOS/GAME-Maze-Playtest.app", false);
        }

        [MenuItem("GAME/Maze Playtest/Build Windows")]
        public static void BuildWindows()
        {
            Build(BuildTarget.StandaloneWindows64, "Builds/MazePlaytest/Windows/GAME-Maze-Playtest.exe", true);
        }

        /// <summary>
        /// Rend deux images de contrôle depuis la scène générée : une vue aérienne et
        /// une vue à hauteur d'yeux devant une entrée. Sert de preuve d'échelle et
        /// d'orientation avant de lancer un test à plusieurs.
        /// </summary>
        [MenuItem("GAME/Maze Playtest/Render Preview")]
        public static void RenderPreview()
        {
            if (!File.Exists(ScenePath))
                CreateScene();

            EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            Directory.CreateDirectory(PreviewDirectory);

            var layout = ReadLayout();
            var span = layout.Width * layout.CellSize;
            var entrance = CellCenterToUnity(layout.Entrances[0], layout);
            var treasure = CellCenterToUnity(layout.Treasure, layout);

            var aerial = new Vector3(0f, span * 0.95f, span * 0.75f);
            RenderFrom(aerial, Quaternion.LookRotation((Vector3.zero - aerial).normalized, Vector3.up),
                60f, "apercu-aerien.png");

            var eye = entrance + new Vector3(0f, EyeHeight, 6f);
            var toTreasure = treasure - eye;
            toTreasure.y = 0f;
            RenderFrom(eye, Quaternion.LookRotation(toTreasure.normalized, Vector3.up), 70f, "apercu-entree.png");

            Debug.Log($"[GAME-MAZE] Preview images written to {Path.GetFullPath(PreviewDirectory)}.");
        }

        private static void RenderFrom(Vector3 position, Quaternion rotation, float fieldOfView, string fileName)
        {
            var cameraObject = new GameObject("PreviewCamera", typeof(Camera));
            var texture = new RenderTexture(1280, 720, 24);
            var screenshot = new Texture2D(1280, 720, TextureFormat.RGB24, false);
            var previousActive = RenderTexture.active;

            try
            {
                cameraObject.transform.SetPositionAndRotation(position, rotation);
                var camera = cameraObject.GetComponent<Camera>();
                camera.fieldOfView = fieldOfView;
                camera.nearClipPlane = 0.05f;
                camera.farClipPlane = 600f;
                camera.clearFlags = CameraClearFlags.SolidColor;
                camera.backgroundColor = SkyColor;
                camera.targetTexture = texture;
                camera.Render();

                RenderTexture.active = texture;
                screenshot.ReadPixels(new Rect(0f, 0f, 1280f, 720f), 0, 0);
                screenshot.Apply();
                File.WriteAllBytes(Path.Combine(PreviewDirectory, fileName), screenshot.EncodeToPNG());
            }
            finally
            {
                RenderTexture.active = previousActive;
                UnityEngine.Object.DestroyImmediate(screenshot);
                UnityEngine.Object.DestroyImmediate(cameraObject);
                texture.Release();
                UnityEngine.Object.DestroyImmediate(texture);
            }
        }

        private static void Build(BuildTarget target, string outputPath, bool forceIl2Cpp)
        {
            CreateScene();
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(outputPath)) ?? "Builds");

            var options = new BuildPlayerOptions
            {
                scenes = new[] { ScenePath },
                locationPathName = outputPath,
                target = target,
                options = BuildOptions.Development
            };

            var namedTarget = NamedBuildTarget.FromBuildTargetGroup(BuildPipeline.GetBuildTargetGroup(target));
            var previousBackend = PlayerSettings.GetScriptingBackend(namedTarget);

            try
            {
                if (forceIl2Cpp)
                    PlayerSettings.SetScriptingBackend(namedTarget, ScriptingImplementation.IL2CPP);

                var report = BuildPipeline.BuildPlayer(options);
                if (report.summary.result != BuildResult.Succeeded)
                    throw new BuildFailedException($"Maze playtest build failed: {report.summary.result}.");
            }
            finally
            {
                if (forceIl2Cpp && PlayerSettings.GetScriptingBackend(namedTarget) != previousBackend)
                    PlayerSettings.SetScriptingBackend(namedTarget, previousBackend);
            }

            Debug.Log($"[GAME-MAZE] Build ready: {Path.GetFullPath(outputPath)}");
        }

        private static NetworkObject CreatePlayerPrefab()
        {
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(PlayerModelPath);
            if (model == null)
                throw new InvalidOperationException($"Modèle de personnage introuvable: {PlayerModelPath}.");

            var root = new GameObject("MazePlayer");
            try
            {
                var controller = root.AddComponent<CharacterController>();
                controller.height = PlayerHeight;
                controller.radius = PlayerRadius;
                controller.center = new Vector3(0f, PlayerHeight / 2f, 0f);
                controller.slopeLimit = 45f;
                controller.stepOffset = 0.3f;
                controller.skinWidth = 0.03f;

                var visual = (GameObject)PrefabUtility.InstantiatePrefab(model);
                visual.name = "Visual";
                visual.transform.SetParent(root.transform, false);

                var pivot = new GameObject("CameraPivot");
                pivot.transform.SetParent(root.transform, false);
                pivot.transform.localPosition = new Vector3(0f, EyeHeight, 0f);

                var cameraObject = new GameObject("PlayerCamera", typeof(Camera), typeof(AudioListener));
                cameraObject.transform.SetParent(pivot.transform, false);
                var camera = cameraObject.GetComponent<Camera>();
                camera.nearClipPlane = 0.05f;
                camera.farClipPlane = 400f;
                camera.clearFlags = CameraClearFlags.SolidColor;
                camera.backgroundColor = SkyColor;
                // Activée uniquement pour le propriétaire, dans PlayerMotor.OnStartClient.
                cameraObject.SetActive(false);

                root.AddComponent<NetworkObject>();

                // Déclarer le CharacterController au NetworkTransform : FishNet ne le
                // laisse actif que sur la copie contrôlée, les copies distantes sont
                // pilotées uniquement par la réplication.
                var networkTransform = root.AddComponent<NetworkTransform>();
                var serializedTransform = new SerializedObject(networkTransform);
                serializedTransform.FindProperty("_componentConfiguration").enumValueIndex =
                    (int)NetworkTransform.ComponentConfigurationType.CharacterController;
                serializedTransform.ApplyModifiedPropertiesWithoutUndo();

                var motor = root.AddComponent<PlayerMotor>();
                var serializedMotor = new SerializedObject(motor);
                serializedMotor.FindProperty("_cameraPivot").objectReferenceValue = pivot.transform;
                serializedMotor.FindProperty("_camera").objectReferenceValue = camera;
                serializedMotor.FindProperty("_visual").objectReferenceValue = visual.transform;
                serializedMotor.ApplyModifiedPropertiesWithoutUndo();

                var saved = PrefabUtility.SaveAsPrefabAsset(root, PlayerPrefabPath);
                if (saved == null)
                    throw new InvalidOperationException($"Unable to save {PlayerPrefabPath}.");

                return saved.GetComponent<NetworkObject>();
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        private static void CreateEnvironment()
        {
            var mazeModel = AssetDatabase.LoadAssetAtPath<GameObject>(MazeModelPath);
            if (mazeModel == null)
                throw new InvalidOperationException($"Modèle de labyrinthe introuvable: {MazeModelPath}.");

            var maze = (GameObject)PrefabUtility.InstantiatePrefab(mazeModel);
            maze.name = "Maze16x16";
            maze.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
            foreach (var child in maze.GetComponentsInChildren<Transform>(true))
                GameObjectUtility.SetStaticEditorFlags(child.gameObject, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic);

            // Soleil venant du sud (côté des entrées) pour que la face abordée par les
            // joueurs soit éclairée et non à contre-jour.
            var lightObject = new GameObject("Directional Light", typeof(Light));
            lightObject.transform.rotation = Quaternion.Euler(50f, 155f, 0f);
            var light = lightObject.GetComponent<Light>();
            light.type = LightType.Directional;
            light.color = new Color(1f, 0.95f, 0.86f);
            light.intensity = 1.4f;
            light.shadows = LightShadows.Soft;

            var cameraObject = new GameObject("SpectatorCamera", typeof(Camera), typeof(AudioListener), typeof(SpectatorCamera));
            cameraObject.tag = "MainCamera";
            var spectatorPosition = new Vector3(0f, 58f, 46f);
            cameraObject.transform.SetPositionAndRotation(
                spectatorPosition,
                Quaternion.LookRotation((Vector3.zero - spectatorPosition).normalized, Vector3.up));
            var spectatorCamera = cameraObject.GetComponent<Camera>();
            spectatorCamera.clearFlags = CameraClearFlags.SolidColor;
            spectatorCamera.backgroundColor = SkyColor;
            spectatorCamera.farClipPlane = 600f;

            // Direction artistique : ciel crème chaud, pas de bleu. Le brouillard masque
            // le bord du plan de sable sans cacher les murs du labyrinthe.
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(0.72f, 0.66f, 0.58f);
            RenderSettings.ambientEquatorColor = new Color(0.56f, 0.48f, 0.41f);
            RenderSettings.ambientGroundColor = new Color(0.38f, 0.31f, 0.26f);
            RenderSettings.skybox = null;
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.Linear;
            RenderSettings.fogColor = SkyColor;
            RenderSettings.fogStartDistance = 90f;
            RenderSettings.fogEndDistance = 280f;
            RenderSettings.sun = light;
        }

        private static Transform[] CreateSpawnPoints(MazeLayout layout)
        {
            var root = new GameObject("SpawnPoints").transform;
            var treasure = CellCenterToUnity(layout.Treasure, layout);
            var spawns = new List<Transform>(layout.Entrances.Count);

            foreach (var entrance in layout.Entrances)
            {
                var position = CellCenterToUnity(entrance, layout) + Vector3.up * SpawnHeight;
                var point = new GameObject($"Spawn_Cell_{entrance.x}_{entrance.y}").transform;
                point.SetParent(root, false);

                var toTreasure = treasure - position;
                toTreasure.y = 0f;
                point.SetPositionAndRotation(position, Quaternion.LookRotation(toTreasure.normalized, Vector3.up));
                spawns.Add(point);
            }

            return spawns.ToArray();
        }

        /// <summary>
        /// La grille Blender est centrée sur l'origine et l'export FBX applique la
        /// conversion Blender (x, y, z) vers Unity (x, z, -y). Les entrées sont donc
        /// du côté +Z dans Unity et le trésor du côté -Z.
        /// </summary>
        private static Vector3 CellCenterToUnity(Vector2Int cell, MazeLayout layout)
        {
            var blenderX = -layout.Width * layout.CellSize / 2f + (cell.x + 0.5f) * layout.CellSize;
            var blenderY = -layout.Height * layout.CellSize / 2f + (cell.y + 0.5f) * layout.CellSize;
            return new Vector3(blenderX, 0f, -blenderY);
        }

        private static DefaultPrefabObjects LoadOrCreatePrefabCollection()
        {
            var existing = AssetDatabase.LoadAssetAtPath<DefaultPrefabObjects>(PrefabsPath);
            if (existing != null)
                return existing;

            var created = ScriptableObject.CreateInstance<DefaultPrefabObjects>();
            AssetDatabase.CreateAsset(created, PrefabsPath);
            return created;
        }

        private static void EnsureGeneratedDirectory()
        {
            if (!AssetDatabase.IsValidFolder(GeneratedDirectory))
                AssetDatabase.CreateFolder("Assets", "_GeneratedLocal");
        }

        private readonly struct MazeLayout
        {
            public MazeLayout(int width, int height, float cellSize, List<Vector2Int> entrances, Vector2Int treasure)
            {
                Width = width;
                Height = height;
                CellSize = cellSize;
                Entrances = entrances;
                Treasure = treasure;
            }

            public int Width { get; }
            public int Height { get; }
            public float CellSize { get; }
            public List<Vector2Int> Entrances { get; }
            public Vector2Int Treasure { get; }
        }

        /// <summary>
        /// Lecture minimale de `MazeGrid16x16.json` : seules les entrées, le trésor et
        /// les dimensions sont nécessaires pour poser les points d'apparition. Le vrai
        /// importeur de grille (murs et pivots) viendra avec le sprint pivot.
        /// </summary>
        private static MazeLayout ReadLayout()
        {
            if (!File.Exists(MazeGridPath))
                throw new InvalidOperationException($"Grille du labyrinthe introuvable: {MazeGridPath}.");

            var json = File.ReadAllText(MazeGridPath);
            var entrances = ReadCells(ExtractBracketBlock(json, "entrances"));
            var treasureCells = ReadCells(ExtractBracketBlock(json, "treasure"));

            if (entrances.Count == 0)
                throw new InvalidOperationException($"Aucune entrée déclarée dans {MazeGridPath}.");
            if (treasureCells.Count != 1)
                throw new InvalidOperationException($"Cellule de trésor illisible dans {MazeGridPath}.");

            return new MazeLayout(
                ReadInt(json, "width"),
                ReadInt(json, "height"),
                ReadFloat(json, "cell_size_m"),
                entrances,
                treasureCells[0]);
        }

        private static string ExtractBracketBlock(string json, string key)
        {
            var keyIndex = json.IndexOf($"\"{key}\"", StringComparison.Ordinal);
            if (keyIndex < 0)
                throw new InvalidOperationException($"Clé \"{key}\" absente de {MazeGridPath}.");

            var start = json.IndexOf('[', keyIndex);
            if (start < 0)
                throw new InvalidOperationException($"Clé \"{key}\" sans tableau dans {MazeGridPath}.");

            var depth = 0;
            for (var index = start; index < json.Length; index++)
            {
                if (json[index] == '[')
                    depth++;
                else if (json[index] == ']' && --depth == 0)
                    return json.Substring(start, index - start + 1);
            }

            throw new InvalidOperationException($"Tableau \"{key}\" non terminé dans {MazeGridPath}.");
        }

        private static List<Vector2Int> ReadCells(string block)
        {
            var cells = new List<Vector2Int>();
            foreach (Match match in Regex.Matches(block, @"\[\s*(-?\d+)\s*,\s*(-?\d+)\s*\]"))
            {
                cells.Add(new Vector2Int(
                    int.Parse(match.Groups[1].Value, CultureInfo.InvariantCulture),
                    int.Parse(match.Groups[2].Value, CultureInfo.InvariantCulture)));
            }

            return cells;
        }

        private static int ReadInt(string json, string key) =>
            (int)Math.Round(ReadFloat(json, key));

        private static float ReadFloat(string json, string key)
        {
            var match = Regex.Match(json, $"\"{Regex.Escape(key)}\"\\s*:\\s*(-?[0-9]+(?:\\.[0-9]+)?)");
            if (!match.Success)
                throw new InvalidOperationException($"Clé \"{key}\" absente ou non numérique dans {MazeGridPath}.");

            return float.Parse(match.Groups[1].Value, CultureInfo.InvariantCulture);
        }
    }
}
