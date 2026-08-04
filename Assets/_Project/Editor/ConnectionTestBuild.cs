using System;
using System.IO;
using FishNet.Managing;
using FishNet.Managing.Object;
using FishNet.Transporting.Tugboat;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace NotThatWay.Game.Editor
{
    public static class ConnectionTestBuild
    {
        private const string GeneratedDirectory = "Assets/_GeneratedLocal";
        private const string ScenePath = GeneratedDirectory + "/FirstConnection.unity";
        private const string PrefabsPath = GeneratedDirectory + "/ConnectionTestPrefabs.asset";

        [MenuItem("GAME/Connection Test/Create Scene")]
        public static void CreateScene()
        {
            EnsureGeneratedDirectory();
            var prefabs = LoadOrCreatePrefabCollection();
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            var networkRoot = new GameObject("NetworkManager");
            networkRoot.AddComponent<Tugboat>();
            var networkManager = networkRoot.AddComponent<NetworkManager>();
            networkManager.SpawnablePrefabs = prefabs;
            networkRoot.AddComponent<ConnectionSmokeTest>();

            CreateEnvironment();
            EditorSceneManager.MarkSceneDirty(scene);
            if (!EditorSceneManager.SaveScene(scene, ScenePath))
                throw new InvalidOperationException($"Unable to save {ScenePath}.");

            AssetDatabase.SaveAssets();
            Debug.Log($"[GAME-CONNECTION] Generated {ScenePath}.");
        }

        [MenuItem("GAME/Connection Test/Build macOS")]
        public static void BuildMac()
        {
            Build(BuildTarget.StandaloneOSX, "Builds/ConnectionTest/macOS/GAME-Connection-Test.app", false);
        }

        [MenuItem("GAME/Connection Test/Build Windows")]
        public static void BuildWindows()
        {
            Build(BuildTarget.StandaloneWindows64, "Builds/ConnectionTest/Windows/GAME-Connection-Test.exe", true);
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
                    throw new BuildFailedException($"Connection test build failed: {report.summary.result}.");
            }
            finally
            {
                if (forceIl2Cpp && PlayerSettings.GetScriptingBackend(namedTarget) != previousBackend)
                    PlayerSettings.SetScriptingBackend(namedTarget, previousBackend);
            }

            Debug.Log($"[GAME-CONNECTION] Build ready: {Path.GetFullPath(outputPath)}");
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

        private static void CreateEnvironment()
        {
            var cameraObject = new GameObject("Main Camera", typeof(Camera), typeof(AudioListener));
            cameraObject.tag = "MainCamera";
            cameraObject.transform.position = new Vector3(0f, 7f, -10f);
            cameraObject.transform.rotation = Quaternion.LookRotation(new Vector3(0f, 1f, 0f) - cameraObject.transform.position);
            cameraObject.GetComponent<Camera>().backgroundColor = new Color(0.035f, 0.045f, 0.065f);

            var lightObject = new GameObject("Directional Light", typeof(Light));
            lightObject.transform.rotation = Quaternion.Euler(45f, -35f, 0f);
            var light = lightObject.GetComponent<Light>();
            light.type = LightType.Directional;
            light.intensity = 1.2f;

            var floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
            floor.name = "Connection Test Floor";
            floor.transform.localScale = new Vector3(2f, 1f, 2f);

            for (var index = 0; index < 3; index++)
            {
                var marker = GameObject.CreatePrimitive(PrimitiveType.Cube);
                marker.name = $"Team Marker {index + 1}";
                marker.transform.position = new Vector3((index - 1) * 2.5f, 0.75f, 0f);
                marker.transform.localScale = new Vector3(1.2f, 1.5f, 1.2f);
            }
        }
    }
}
