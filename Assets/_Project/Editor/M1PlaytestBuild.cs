using System;
using System.IO;
using System.Reflection;
using FishNet.Component.Spawning;
using FishNet.Managing;
using FishNet.Managing.Object;
using FishNet.Managing.Predicting;
using FishNet.Managing.Timing;
using FishNet.Object;
using FishNet.Transporting.Tugboat;
using NotThatWay.Game.Input;
using NotThatWay.Game.Topology;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.Rendering;

namespace NotThatWay.Game.Editor
{
    /// <summary>
    /// Génère le banc M1 minimal sans modifier la scène historique du labyrinthe.
    /// Tous les paramètres qui influencent le test sont écrits ici explicitement.
    /// </summary>
    public static class M1PlaytestBuild
    {
        public const string GeneratedScenePath = "Assets/_GeneratedLocal/M1Playtest.unity";
        public const string GeneratedPlayerPrefabPath = "Assets/_GeneratedLocal/M1PredictedPlayer.prefab";
        public const string GeneratedWallAuthorityPrefabPath =
            "Assets/_GeneratedLocal/M1WallAuthority.prefab";
        public const string GeneratedPrefabsPath = "Assets/_GeneratedLocal/M1PlaytestPrefabs.asset";

        private const string GeneratedDirectory = "Assets/_GeneratedLocal";
        private const string TopologyPath = "Assets/_Project/Maze/GrayboxTopology2x2.v1.json";
        private const string GameControlsPath = "Assets/_Project/Input/GameControls.inputactions";

        // Profil de mesure M1, pas encore une décision de game feel finale.
        private const ushort TickRate = 60;
        private const float PlayerHeight = 1.4f;
        private const float PlayerRadius = 0.4f;
        private const float EyeHeight = 1.05f;
        private const float SpawnHeight = 0.05f;

        private static readonly Color SkyColor = new(0.08f, 0.10f, 0.14f);

        [MenuItem("GAME/M1 Playtest/Create Scene")]
        public static void CreateScene()
        {
            using var physicsModeScope = new PhysicsSimulationModeScope();
            EnsureGeneratedDirectory();
            var topologyAsset = RequireAsset<TextAsset>(TopologyPath);
            var map = ReadVerifiedMap(topologyAsset);
            var controls = RequireAsset<InputActionAsset>(GameControlsPath);
            if (!GameControlsContract.TryValidate(controls, out var controlsError))
                throw new InvalidOperationException($"Contrôles M1 invalides: {controlsError}.");

            var playerPrefab = CreatePlayerPrefab(controls);
            var wallAuthorityPrefab = CreateWallAuthorityPrefab();
            var prefabCollection = LoadOrCreatePrefabCollection();
            prefabCollection.Clear();
            prefabCollection.AddObject(playerPrefab, true);
            prefabCollection.AddObject(wallAuthorityPrefab, true);
            EditorUtility.SetDirty(prefabCollection);

            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            ConfigureRenderSettings();

            var arenaObject = new GameObject("M1TopologyArena");
            var arena = arenaObject.AddComponent<TopologyArena>();
            arena.Configure(topologyAsset, true);

            var spawns = CreateSpawnPoints(map);
            CreateSpectatorCamera(map);
            CreateLighting();

            var networkRoot = new GameObject("NetworkManager");
            networkRoot.AddComponent<Tugboat>();
            var timeManager = networkRoot.AddComponent<TimeManager>();
            ConfigureTimeManager(timeManager);
            var predictionManager = networkRoot.AddComponent<PredictionManager>();
            ConfigurePredictionManager(predictionManager);

            var networkManager = networkRoot.AddComponent<NetworkManager>();
            networkManager.SpawnablePrefabs = prefabCollection;
            var connection = networkRoot.AddComponent<ConnectionSmokeTest>();
            connection.ConfigureDisplay(
                "GAME — banc M1 réseau",
                "Prêt lorsque les deux participants apparaissent dans la liste.",
                true);
            networkRoot.AddComponent<M1PlaytestDiagnostics>();

            var spawner = networkRoot.AddComponent<PlayerSpawner>();
            spawner.Spawns = spawns;
            spawner.SetPlayerPrefab(playerPrefab);

            var wallSpawner = networkRoot.AddComponent<M1WallAuthoritySpawner>();
            var serializedWallSpawner = new SerializedObject(wallSpawner);
            SetObject(serializedWallSpawner, "_authorityPrefab", wallAuthorityPrefab);
            serializedWallSpawner.ApplyModifiedPropertiesWithoutUndo();

            ValidateSceneContract(
                map,
                arena,
                playerPrefab,
                wallAuthorityPrefab,
                prefabCollection,
                networkManager,
                timeManager,
                predictionManager,
                spawner);

            EditorSceneManager.MarkSceneDirty(scene);
            if (!EditorSceneManager.SaveScene(scene, GeneratedScenePath))
                throw new InvalidOperationException($"Impossible d'enregistrer {GeneratedScenePath}.");

            AssetDatabase.SaveAssets();
            Debug.Log(
                $"[GAME-M1] Generated {GeneratedScenePath}; topology={map.TopologyId}; " +
                $"checksum={map.Checksum}; spawns={spawns.Length}; tickRate={TickRate}.");
        }

        [MenuItem("GAME/M1 Playtest/Validate Generated Scene")]
        public static void ValidateGeneratedScene()
        {
            CreateScene();
            Debug.Log("[GAME-M1] Generated scene contract valid.");
        }

        [MenuItem("GAME/M1 Playtest/Build macOS")]
        public static void BuildMac()
        {
            Build(
                BuildTarget.StandaloneOSX,
                "Builds/M1Playtest/macOS/GAME-M1-Playtest.app",
                false);
        }

        [MenuItem("GAME/M1 Playtest/Build Windows")]
        public static void BuildWindows()
        {
            Build(
                BuildTarget.StandaloneWindows64,
                "Builds/M1Playtest/Windows/GAME-M1-Playtest.exe",
                true);
        }

        private static NetworkObject CreatePlayerPrefab(InputActionAsset controls)
        {
            var root = new GameObject("M1PredictedPlayer")
            {
                layer = GameplayLayers.Player
            };

            try
            {
                var controller = root.AddComponent<CharacterController>();
                controller.height = PlayerHeight;
                controller.radius = PlayerRadius;
                controller.center = new Vector3(0f, PlayerHeight * 0.5f, 0f);
                controller.slopeLimit = 45f;
                controller.stepOffset = 0.3f;
                controller.skinWidth = 0.03f;
                controller.minMoveDistance = 0f;
                controller.detectCollisions = true;
                controller.enableOverlapRecovery = true;

                var presentation = new GameObject("Presentation")
                {
                    layer = GameplayLayers.VisualOnly
                };
                presentation.transform.SetParent(root.transform, false);

                var body = GameObject.CreatePrimitive(PrimitiveType.Capsule);
                body.name = "Body";
                body.layer = GameplayLayers.VisualOnly;
                body.transform.SetParent(presentation.transform, false);
                body.transform.localPosition = new Vector3(0f, PlayerHeight * 0.5f, 0f);
                body.transform.localScale = new Vector3(
                    PlayerRadius * 2f,
                    PlayerHeight * 0.5f,
                    PlayerRadius * 2f);
                UnityEngine.Object.DestroyImmediate(body.GetComponent<Collider>());

                var cameraPivot = new GameObject("CameraPivot")
                {
                    layer = GameplayLayers.VisualOnly
                };
                cameraPivot.transform.SetParent(presentation.transform, false);
                cameraPivot.transform.localPosition = new Vector3(0f, EyeHeight, 0f);

                var cameraObject = new GameObject(
                    "PlayerCamera",
                    typeof(Camera),
                    typeof(AudioListener))
                {
                    layer = GameplayLayers.VisualOnly
                };
                cameraObject.transform.SetParent(cameraPivot.transform, false);
                var camera = cameraObject.GetComponent<Camera>();
                camera.nearClipPlane = 0.05f;
                camera.farClipPlane = 100f;
                camera.fieldOfView = 70f;
                camera.clearFlags = CameraClearFlags.SolidColor;
                camera.backgroundColor = SkyColor;
                cameraObject.SetActive(false);

                var networkObject = root.AddComponent<NetworkObject>();
                ConfigureNetworkPrediction(networkObject, presentation.transform);

                var inputSource = root.AddComponent<PlayerInputSource>();
                inputSource.enabled = false;
                inputSource.Configure(controls);
                var serializedInput = new SerializedObject(inputSource);
                SetFloat(serializedInput, "_pointerDegreesPerPixel", 0.12f);
                SetFloat(serializedInput, "_stickDegreesPerSecond", 180f);
                serializedInput.ApplyModifiedPropertiesWithoutUndo();

                var motor = root.AddComponent<PredictedPlayerMotor>();
                ConfigureMotor(motor, cameraPivot.transform, camera);

                var saved = PrefabUtility.SaveAsPrefabAsset(root, GeneratedPlayerPrefabPath);
                if (saved == null)
                    throw new InvalidOperationException(
                        $"Impossible d'enregistrer {GeneratedPlayerPrefabPath}.");

                return FinalizeNetworkPrefab(saved.GetComponent<NetworkObject>());
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        private static NetworkObject CreateWallAuthorityPrefab()
        {
            var root = new GameObject("M1WallAuthority");
            try
            {
                var networkObject = root.AddComponent<NetworkObject>();
                var serializedNetworkObject = new SerializedObject(networkObject);
                SetBool(serializedNetworkObject, "_enablePrediction", false);
                SetBool(serializedNetworkObject, "_enableStateForwarding", false);
                SetObject(serializedNetworkObject, "_networkTransform", null);
                serializedNetworkObject.ApplyModifiedPropertiesWithoutUndo();

                var director = root.AddComponent<M1AuthoritativeWallDirector>();
                var serializedDirector = new SerializedObject(director);
                SetInt(serializedDirector, "_tickCallbacks", 1); // PreTick.
                SetInt(serializedDirector, "_wallId", 10);
                SetInt(serializedDirector, "_effortThreshold", 120);
                SetInt(serializedDirector, "_maximumEffortPerSourcePerTick", 4);
                SetInt(serializedDirector, "_effortDecayPerTick", 2);
                SetInt(serializedDirector, "_rejectedEffortRetention", 0);
                SetLong(serializedDirector, "_transitionDurationTicks", 30L);
                SetInt(serializedDirector, "_effortPerHeldTick", 4);
                SetInt(serializedDirector, "_reachFromCapsuleMm", 900);
                serializedDirector.ApplyModifiedPropertiesWithoutUndo();

                var saved = PrefabUtility.SaveAsPrefabAsset(
                    root,
                    GeneratedWallAuthorityPrefabPath);
                if (saved == null)
                {
                    throw new InvalidOperationException(
                        $"Impossible d'enregistrer {GeneratedWallAuthorityPrefabPath}.");
                }
                return FinalizeNetworkPrefab(saved.GetComponent<NetworkObject>());
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        private static void ConfigureNetworkPrediction(
            NetworkObject networkObject,
            Transform presentation)
        {
            var serialized = new SerializedObject(networkObject);
            SetBool(serialized, "_enablePrediction", true);
            SetEnum(serialized, "_predictionType", 0); // Other / CharacterController.
            SetObject(serialized, "_graphicalObject", presentation);
            SetBool(serialized, "_detachGraphicalObject", true);
            SetBool(serialized, "_enableStateForwarding", true);
            SetObject(serialized, "_networkTransform", null);
            SetInt(serialized, "_ownerInterpolation", 1);
            SetInt(serialized, "_ownerSmoothedProperties", 3); // Position + rotation.
            SetEnum(serialized, "_adaptiveInterpolation", 0); // Profil exact, non adaptatif.
            SetInt(serialized, "_spectatorSmoothedProperties", 3);
            SetInt(serialized, "_spectatorInterpolation", 2);
            SetBool(serialized, "_enableTeleport", true);
            SetFloat(serialized, "_teleportThreshold", 2f);
            serialized.ApplyModifiedPropertiesWithoutUndo();
        }

        private static void ConfigureMotor(
            PredictedPlayerMotor motor,
            Transform cameraPivot,
            Camera camera)
        {
            var serialized = new SerializedObject(motor);
            SetObject(serialized, "_cameraPivot", cameraPivot);
            SetObject(serialized, "_camera", camera);
            SetFloat(serialized, "_walkSpeed", 4.2f);
            SetFloat(serialized, "_sprintSpeed", 7f);
            SetFloat(serialized, "_groundAcceleration", 35f);
            SetFloat(serialized, "_airAcceleration", 12f);
            SetFloat(serialized, "_groundDeceleration", 45f);
            SetFloat(serialized, "_airDeceleration", 8f);
            SetFloat(serialized, "_gravity", -22f);
            SetFloat(serialized, "_groundedVelocity", -3f);
            SetBool(serialized, "_jumpEnabled", false);
            SetFloat(serialized, "_jumpSpeed", 5.5f);
            SetLong(serialized, "_coyoteTicks", 7L);
            SetLong(serialized, "_jumpBufferTicks", 9L);
            SetFloat(serialized, "_knockbackDecay", 10f);
            SetInt(serialized, "_maximumPitchCentidegrees", 8500);
            serialized.ApplyModifiedPropertiesWithoutUndo();
        }

        private static Transform[] CreateSpawnPoints(TopologyRuntimeMap map)
        {
            if (map.Spawns.Count != 2)
            {
                throw new InvalidOperationException(
                    $"Le banc M1 exige exactement deux spawns, trouvé {map.Spawns.Count}.");
            }

            var root = new GameObject("M1SpawnPoints").transform;
            var result = new Transform[map.Spawns.Count];
            for (var index = 0; index < map.Spawns.Count; index++)
            {
                var source = map.Spawns[index];
                var point = new GameObject($"Spawn_{source.SpawnId}").transform;
                point.SetParent(root, false);
                point.localPosition = TopologyGeometry.CellCenterMm(map, source.Cell).Meters +
                                      Vector3.up * SpawnHeight;
                point.localRotation = Quaternion.Euler(
                    0f,
                    source.YawQuarterTurns * 90f,
                    0f);
                result[index] = point;
            }

            return result;
        }

        private static void CreateSpectatorCamera(TopologyRuntimeMap map)
        {
            var width = (float)((double)map.Dimensions.WidthCells *
                                map.Dimensions.CellPitchMm / 1000d);
            var cameraObject = new GameObject(
                "M1SpectatorCamera",
                typeof(Camera),
                typeof(AudioListener),
                typeof(SpectatorCamera));
            cameraObject.transform.position = new Vector3(0f, width * 1.2f, -width * 1.1f);
            cameraObject.transform.rotation = Quaternion.LookRotation(
                (Vector3.up * 0.8f - cameraObject.transform.position).normalized,
                Vector3.up);
            var camera = cameraObject.GetComponent<Camera>();
            camera.fieldOfView = 55f;
            camera.nearClipPlane = 0.05f;
            camera.farClipPlane = 100f;
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = SkyColor;
        }

        private static void CreateLighting()
        {
            var lightObject = new GameObject("M1DirectionalLight", typeof(Light));
            lightObject.transform.rotation = Quaternion.Euler(48f, -32f, 0f);
            var light = lightObject.GetComponent<Light>();
            light.type = LightType.Directional;
            light.color = new Color(1f, 0.92f, 0.82f);
            light.intensity = 1.15f;
            light.shadows = LightShadows.Soft;
        }

        private static void ConfigureRenderSettings()
        {
            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(0.30f, 0.34f, 0.42f);
            RenderSettings.fog = false;
        }

        private static void ConfigureTimeManager(TimeManager manager)
        {
            var serialized = new SerializedObject(manager);
            SetEnum(serialized, "_updateOrder", 0); // BeforeTick.
            SetEnum(serialized, "_timingType", 0); // Tick.
            SetBool(serialized, "_allowTickDropping", false);
            SetInt(serialized, "_maximumFrameTicks", 4);
            SetInt(serialized, "_tickRate", TickRate);
            SetInt(serialized, "_pingInterval", 1);
            serialized.ApplyModifiedPropertiesWithoutUndo();

            // SerializedObject déclenche TimeManager.OnValidate, lequel modifie les
            // ProjectSettings physiques globaux. Le banc doit sérialiser son mode
            // sans changer le comportement de toutes les autres scènes du dépôt.
            SetPrivateField(manager, "_physicsMode", PhysicsMode.TimeManager);
            EditorUtility.SetDirty(manager);
        }

        private static void ConfigurePredictionManager(PredictionManager manager)
        {
            var serialized = new SerializedObject(manager);
            SetBool(serialized, "_reduceReconcilesWithFramerate", false);
            SetInt(serialized, "_minimumClientReconcileFramerate", 50);
            SetBool(serialized, "_createLocalStates", true);
            SetInt(serialized, "_stateInterpolation", 2);
            SetEnum(serialized, "_stateOrder", (int)ReplicateStateOrder.Appended);
            SetBool(serialized, "_dropExcessiveReplicates", true);
            SetInt(serialized, "_maximumServerReplicates", 15);
            serialized.ApplyModifiedPropertiesWithoutUndo();
        }

        private static void ValidateSceneContract(
            TopologyRuntimeMap map,
            TopologyArena arena,
            NetworkObject playerPrefab,
            NetworkObject wallAuthorityPrefab,
            DefaultPrefabObjects prefabCollection,
            NetworkManager networkManager,
            TimeManager timeManager,
            PredictionManager predictionManager,
            PlayerSpawner spawner)
        {
            if (map.Spawns.Count != 2 || !HasMobileWall(map))
            {
                throw new InvalidOperationException(
                    "Le banc M1 doit contenir deux spawns et au moins un mur mobile.");
            }
            if (arena == null || playerPrefab == null || wallAuthorityPrefab == null ||
                networkManager == null ||
                timeManager == null || predictionManager == null || spawner == null)
            {
                throw new InvalidOperationException("Composant structurel M1 manquant.");
            }
            if (timeManager.TickRate != TickRate || timeManager.PhysicsMode != PhysicsMode.TimeManager)
                throw new InvalidOperationException("Profil temporel M1 mal sérialisé.");
            if (predictionManager.StateInterpolation != 2 ||
                predictionManager.StateOrder != ReplicateStateOrder.Appended ||
                predictionManager.GetMaximumServerReplicates() != 15)
            {
                throw new InvalidOperationException("Profil de prédiction M1 mal sérialisé.");
            }
            if (networkManager.SpawnablePrefabs != prefabCollection || spawner.Spawns.Length != 2)
                throw new InvalidOperationException("Spawning FishNet M1 incomplet.");
            if (!playerPrefab.EnablePrediction || !playerPrefab.EnableStateForwarding ||
                playerPrefab.GetGraphicalObject() == null)
            {
                throw new InvalidOperationException("Prediction du prefab joueur M1 incomplète.");
            }
            var playerObject = playerPrefab.gameObject;
            if (playerObject.layer != GameplayLayers.Player ||
                playerObject.GetComponent<CharacterController>() == null ||
                playerObject.GetComponent<PlayerInputSource>() == null ||
                playerObject.GetComponent<PredictedPlayerMotor>() == null)
            {
                throw new InvalidOperationException("Contrat du prefab joueur M1 incomplet.");
            }
            if (playerObject.GetComponent<FishNet.Component.Transforming.NetworkTransform>() != null)
                throw new InvalidOperationException("Le joueur prédit M1 ne doit pas avoir de NetworkTransform.");
            if (wallAuthorityPrefab.GetComponent<M1AuthoritativeWallDirector>() == null ||
                wallAuthorityPrefab.EnablePrediction)
            {
                throw new InvalidOperationException("Prefab d'autorité murale M1 invalide.");
            }
        }

        private static bool HasMobileWall(TopologyRuntimeMap map)
        {
            for (var index = 0; index < map.Walls.Count; index++)
            {
                if (map.Walls[index].IsMobile)
                    return true;
            }

            return false;
        }

        private static TopologyRuntimeMap ReadVerifiedMap(TextAsset topologyAsset)
        {
            if (!TopologyRuntimeMap.TryCreateVerified(topologyAsset.text, out var map, out var issues))
            {
                var detail = issues.Count == 0
                    ? "aucun détail"
                    : $"{issues[0].Code}@{issues[0].Path}";
                throw new InvalidOperationException($"Topologie M1 invalide: {detail}.");
            }

            return map;
        }

        private static void Build(BuildTarget target, string outputPath, bool forceIl2Cpp)
        {
            using var physicsModeScope = new PhysicsSimulationModeScope();
            CreateScene();
            var platform = target == BuildTarget.StandaloneOSX ? "macos" : "windows";
            BuildIdentityWriter.WriteForBuild("m1", platform);
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(outputPath)) ?? "Builds");

            var options = new BuildPlayerOptions
            {
                scenes = new[] { GeneratedScenePath },
                locationPathName = outputPath,
                target = target,
                options = BuildOptions.Development
            };

            var namedTarget = NamedBuildTarget.FromBuildTargetGroup(
                BuildPipeline.GetBuildTargetGroup(target));
            var previousBackend = PlayerSettings.GetScriptingBackend(namedTarget);
            try
            {
                if (forceIl2Cpp)
                    PlayerSettings.SetScriptingBackend(namedTarget, ScriptingImplementation.IL2CPP);

                var report = BuildPipeline.BuildPlayer(options);
                if (report.summary.result != BuildResult.Succeeded)
                    throw new BuildFailedException($"Build M1 échoué: {report.summary.result}.");
            }
            finally
            {
                if (forceIl2Cpp && PlayerSettings.GetScriptingBackend(namedTarget) != previousBackend)
                    PlayerSettings.SetScriptingBackend(namedTarget, previousBackend);
            }

            Debug.Log($"[GAME-M1] Build ready: {Path.GetFullPath(outputPath)}");
        }

        private static DefaultPrefabObjects LoadOrCreatePrefabCollection()
        {
            var existing = AssetDatabase.LoadAssetAtPath<DefaultPrefabObjects>(GeneratedPrefabsPath);
            if (existing != null)
                return existing;

            var created = ScriptableObject.CreateInstance<DefaultPrefabObjects>();
            AssetDatabase.CreateAsset(created, GeneratedPrefabsPath);
            return created;
        }

        private static NetworkObject FinalizeNetworkPrefab(NetworkObject networkObject)
        {
            if (networkObject == null)
                throw new InvalidOperationException("Prefab réseau M1 sans NetworkObject.");

            var pathAndName =
                $"{AssetDatabase.GetAssetPath(networkObject.gameObject)}{networkObject.gameObject.name}"
                    .Trim()
                    .ToLowerInvariant();
            var normalized = string.Empty;
            foreach (var character in pathAndName)
            {
                if ((character >= 'a' && character <= 'z') ||
                    (character >= '0' && character <= '9'))
                {
                    normalized += character;
                }
            }

            var hash = StableHashU64(normalized);
            if (hash == 0)
                throw new InvalidOperationException($"Hash FishNet nul pour {pathAndName}.");
            networkObject.SetAssetPathHash(hash);
            EditorUtility.SetDirty(networkObject);
            return networkObject;
        }

        private static ulong StableHashU64(string value)
        {
            const ulong offsetBasis = 14695981039346656037;
            const ulong prime = 1099511628211;
            unchecked
            {
                var hash = offsetBasis;
                foreach (var character in value)
                {
                    hash *= prime;
                    hash ^= character;
                }
                return hash;
            }
        }

        private static T RequireAsset<T>(string path) where T : UnityEngine.Object
        {
            var asset = AssetDatabase.LoadAssetAtPath<T>(path);
            return asset != null
                ? asset
                : throw new InvalidOperationException($"Asset M1 introuvable: {path}.");
        }

        private static void EnsureGeneratedDirectory()
        {
            if (!AssetDatabase.IsValidFolder(GeneratedDirectory))
                AssetDatabase.CreateFolder("Assets", "_GeneratedLocal");
        }

        private static SerializedProperty RequireProperty(SerializedObject serialized, string name)
        {
            return serialized.FindProperty(name) ??
                   throw new InvalidOperationException(
                       $"Champ sérialisé {serialized.targetObject.GetType().Name}.{name} introuvable.");
        }

        private static void SetBool(SerializedObject serialized, string name, bool value) =>
            RequireProperty(serialized, name).boolValue = value;

        private static void SetInt(SerializedObject serialized, string name, int value) =>
            RequireProperty(serialized, name).intValue = value;

        private static void SetLong(SerializedObject serialized, string name, long value) =>
            RequireProperty(serialized, name).longValue = value;

        private static void SetFloat(SerializedObject serialized, string name, float value) =>
            RequireProperty(serialized, name).floatValue = value;

        private static void SetEnum(SerializedObject serialized, string name, int value) =>
            RequireProperty(serialized, name).enumValueIndex = value;

        private static void SetObject(
            SerializedObject serialized,
            string name,
            UnityEngine.Object value) =>
            RequireProperty(serialized, name).objectReferenceValue = value;

        private static void SetPrivateField<T>(UnityEngine.Object target, string name, T value)
        {
            var field = target.GetType().GetField(
                name,
                BindingFlags.Instance | BindingFlags.NonPublic);
            if (field == null || field.FieldType != typeof(T))
            {
                throw new InvalidOperationException(
                    $"Champ privé {target.GetType().Name}.{name} introuvable ou incompatible.");
            }

            field.SetValue(target, value);
        }

        private sealed class PhysicsSimulationModeScope : IDisposable
        {
            private readonly SimulationMode _physics3D;
            private readonly SimulationMode2D _physics2D;

            public PhysicsSimulationModeScope()
            {
                _physics3D = Physics.simulationMode;
                _physics2D = Physics2D.simulationMode;
            }

            public void Dispose()
            {
                Physics.simulationMode = _physics3D;
                Physics2D.simulationMode = _physics2D;
            }
        }
    }
}
