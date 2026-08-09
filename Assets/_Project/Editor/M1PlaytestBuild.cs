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
using UnityEngine.SceneManagement;

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
        private const string MaterialsDirectory = GeneratedDirectory + "/M1Materials";
        private const string TopologyPath = "Assets/_Project/Maze/GrayboxTopology2x2.v1.json";
        private const string GameControlsPath = "Assets/_Project/Input/GameControls.inputactions";
        private const string PlayerModelPath = "Assets/_Project/Player/PersoBouleRigged.fbx";
        private const string PreviewDirectory = "Logs/M1Playtest";

        // URP 17 n'expose plus de matériau par défaut hors éditeur. Chaque objet
        // rendu du banc doit donc porter un matériau explicite construit ici.
        private const string LitShaderName = "Universal Render Pipeline/Lit";
        private const string SkyboxShaderName = "Skybox/Procedural";

        // Profil de mesure M1, pas encore une décision de game feel finale.
        private const ushort TickRate = 60;
        private const float PlayerHeight = 1.4f;
        private const float PlayerRadius = 0.4f;
        private const float EyeHeight = 1.05f;
        private const float SpawnHeight = 0.05f;
        private const int GameplaySpawnCount = 2;
        private const int NetworkTestSpawnCount = 3;

        // Gabarit du personnage produit par build_character.py, identique au banc
        // labyrinthe : 1,40 m, origine aux pieds.
        private const int PlayerTriangleBudget = 6000;
        private const int PlayerBoneBudget = 16;

        private static readonly Color SkyColor = new(0.08f, 0.10f, 0.14f);
        private static readonly Color HorizonColor = new(0.16f, 0.19f, 0.26f);

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

            var palette = CreatePalette();
            var playerPrefab = CreatePlayerPrefab(controls);
            var wallAuthorityPrefab = CreateWallAuthorityPrefab();
            var prefabCollection = LoadOrCreatePrefabCollection();
            prefabCollection.Clear();
            prefabCollection.AddObject(playerPrefab, true);
            prefabCollection.AddObject(wallAuthorityPrefab, true);
            EditorUtility.SetDirty(prefabCollection);

            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            var arenaObject = new GameObject("M1TopologyArena");
            var arena = arenaObject.AddComponent<TopologyArena>();
            arena.Configure(topologyAsset, true);
            arena.ConfigureMaterials(palette.Surface, palette.Accent);

            var spawns = CreateSpawnPoints(map);
            CreateSpectatorCamera(map);
            var keyLight = CreateLighting();
            CreateDecor(map, palette);
            ConfigureRenderSettings(palette, keyLight);

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
                "Prêt lorsque tous les participants apparaissent dans la liste.",
                true);
            networkRoot.AddComponent<M1PlaytestDiagnostics>();
            networkRoot.AddComponent<M1ScreenshotProbe>();

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
            ValidateSceneRendering(scene, playerPrefab.gameObject);

            EditorSceneManager.MarkSceneDirty(scene);
            if (!EditorSceneManager.SaveScene(scene, GeneratedScenePath))
                throw new InvalidOperationException($"Impossible d'enregistrer {GeneratedScenePath}.");

            AssetDatabase.SaveAssets();
            Debug.Log(
                $"[GAME-M1] Generated {GeneratedScenePath}; topology={map.TopologyId}; " +
                $"checksum={map.Checksum}; gameplaySpawns={map.Spawns.Count}; " +
                $"networkTestSpawns={spawns.Length}; tickRate={TickRate}.");
        }

        [MenuItem("GAME/M1 Playtest/Validate Generated Scene")]
        public static void ValidateGeneratedScene()
        {
            CreateScene();
            Debug.Log("[GAME-M1] Generated scene contract valid.");
        }

        /// <summary>
        /// Contrôle visuel réel : construit la scène, l'arène et deux personnages,
        /// puis écrit des captures. Un banc validé uniquement par ses logs peut
        /// être entièrement magenta sans qu'aucune gate ne s'en aperçoive.
        /// </summary>
        [MenuItem("GAME/M1 Playtest/Render Preview")]
        public static void RenderPreview()
        {
            using var physicsModeScope = new PhysicsSimulationModeScope();
            CreateScene();

            var arena = UnityEngine.Object.FindFirstObjectByType<TopologyArena>(FindObjectsInactive.Include);
            if (arena == null)
                throw new InvalidOperationException("Arène M1 absente de la scène générée.");
            arena.BuildFromConfiguredAsset();

            var map = arena.Map;
            var span = (float)((double)map.Dimensions.WidthCells *
                               map.Dimensions.CellPitchMm / 1000d);
            var previews = InstantiatePreviewPlayers();
            Directory.CreateDirectory(Path.GetFullPath(PreviewDirectory));

            try
            {
                var aerial = new Vector3(span * 0.75f, span * 1.35f, -span * 1.15f);
                RenderFrom(
                    aerial,
                    Quaternion.LookRotation((Vector3.up * 0.6f - aerial).normalized, Vector3.up),
                    55f,
                    "apercu-aerien.png");

                // Vue de contrôle du duel : les deux personnages, le pivot orange
                // et le mur mobile cyan dans le même cadre.
                var duel = new Vector3(-span * 0.85f, 2.6f, -span * 1.05f);
                var target = TopologyGeometry.NodeMm(map, 1, 1).Meters + Vector3.up * 0.8f;
                RenderFrom(
                    duel,
                    Quaternion.LookRotation((target - duel).normalized, Vector3.up),
                    60f,
                    "apercu-duel.png");

                // En jeu, M1PlayerAppearance masque le corps de son porteur : la
                // capture première personne doit montrer la même chose, sinon elle
                // valide une image que personne ne verra.
                foreach (var renderer in previews[0].GetComponentsInChildren<Renderer>(true))
                    renderer.shadowCastingMode = ShadowCastingMode.ShadowsOnly;
                var eye = previews[0].transform.position + Vector3.up * EyeHeight;
                RenderFrom(eye, previews[0].transform.rotation, 70f, "apercu-premiere-personne.png");
            }
            finally
            {
                foreach (var preview in previews)
                    UnityEngine.Object.DestroyImmediate(preview);
                if (arena.GeneratedRoot != null)
                    UnityEngine.Object.DestroyImmediate(arena.GeneratedRoot.gameObject);
            }

            Debug.Log($"[GAME-M1] Preview images written to {Path.GetFullPath(PreviewDirectory)}.");
        }

        private static GameObject[] InstantiatePreviewPlayers()
        {
            var prefab = RequireAsset<GameObject>(GeneratedPlayerPrefabPath);
            var spawnRoot = GameObject.Find("M1SpawnPoints");
            if (spawnRoot == null || spawnRoot.transform.childCount < GameplaySpawnCount)
                throw new InvalidOperationException("Points d'apparition M1 absents de la scène générée.");

            var previews = new GameObject[GameplaySpawnCount];
            for (var index = 0; index < previews.Length; index++)
            {
                var spawn = spawnRoot.transform.GetChild(index);
                var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                instance.name = $"PreviewPlayer_{index}";
                instance.transform.SetPositionAndRotation(spawn.position, spawn.rotation);
                foreach (var renderer in instance.GetComponentsInChildren<Renderer>(true))
                {
                    var properties = new MaterialPropertyBlock();
                    renderer.GetPropertyBlock(properties);
                    var color = M1PlayerAppearance.ColorForIndex(index);
                    properties.SetColor("_BaseColor", color);
                    properties.SetColor("_Color", color);
                    renderer.SetPropertyBlock(properties);
                }

                previews[index] = instance;
            }

            return previews;
        }

        private static void RenderFrom(
            Vector3 position,
            Quaternion rotation,
            float fieldOfView,
            string fileName)
        {
            var cameraObject = new GameObject("M1PreviewCamera", typeof(Camera));
            var texture = new RenderTexture(1600, 900, 24);
            var screenshot = new Texture2D(1600, 900, TextureFormat.RGB24, false);
            var previousActive = RenderTexture.active;

            try
            {
                cameraObject.transform.SetPositionAndRotation(position, rotation);
                var camera = cameraObject.GetComponent<Camera>();
                camera.fieldOfView = fieldOfView;
                camera.nearClipPlane = 0.05f;
                camera.farClipPlane = 400f;
                camera.clearFlags = CameraClearFlags.Skybox;
                camera.backgroundColor = SkyColor;
                camera.targetTexture = texture;
                camera.Render();

                RenderTexture.active = texture;
                screenshot.ReadPixels(new Rect(0f, 0f, 1600f, 900f), 0, 0);
                screenshot.Apply();
                File.WriteAllBytes(
                    Path.Combine(PreviewDirectory, fileName),
                    screenshot.EncodeToPNG());
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

                // Le personnage du projet, pas une primitive : le banc réseau doit
                // se regarder comme le jeu. Il reste strictement visuel, sur le
                // layer VisualOnly et sans collider ; le CharacterController est la
                // seule forme physique du joueur.
                var body = CreatePlayerVisual();
                body.transform.SetParent(presentation.transform, false);

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
                camera.farClipPlane = 400f;
                camera.fieldOfView = 70f;
                camera.clearFlags = CameraClearFlags.Skybox;
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

                var appearance = root.AddComponent<M1PlayerAppearance>();
                var serializedAppearance = new SerializedObject(appearance);
                SetObject(serializedAppearance, "_body", presentation.transform);
                serializedAppearance.ApplyModifiedPropertiesWithoutUndo();

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
            if (map.Spawns.Count != GameplaySpawnCount)
            {
                throw new InvalidOperationException(
                    $"Le banc M1 exige exactement {GameplaySpawnCount} spawns de gameplay, " +
                    $"trouvé {map.Spawns.Count}.");
            }

            var root = new GameObject("M1SpawnPoints").transform;
            var result = new Transform[NetworkTestSpawnCount];
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

            // M1 reste un duel à deux spawns canoniques. Ce troisième emplacement
            // n'entre pas dans la topologie ni son checksum : il sert uniquement à
            // exercer trois connexions simultanées sans superposer deux contrôleurs.
            var testCell = FindUnusedNetworkTestCell(map);
            var testPoint = new GameObject("Spawn_NetworkTest_3").transform;
            testPoint.SetParent(root, false);
            testPoint.localPosition = TopologyGeometry.CellCenterMm(map, testCell).Meters +
                                      Vector3.up * SpawnHeight;
            testPoint.localRotation = Quaternion.Euler(0f, 180f, 0f);
            result[GameplaySpawnCount] = testPoint;

            return result;
        }

        private static TopologyGridCell FindUnusedNetworkTestCell(TopologyRuntimeMap map)
        {
            for (var y = map.Dimensions.HeightCells - 1; y >= 0; y--)
            {
                for (var x = map.Dimensions.WidthCells - 1; x >= 0; x--)
                {
                    var candidate = new TopologyGridCell(x, y);
                    var used = false;
                    for (var index = 0; index < map.Spawns.Count; index++)
                    {
                        if (!map.Spawns[index].Cell.Equals(candidate))
                            continue;

                        used = true;
                        break;
                    }

                    if (!used)
                        return candidate;
                }
            }

            throw new InvalidOperationException(
                "Le banc M1 ne possède aucune cellule libre pour le troisième client réseau.");
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
            camera.farClipPlane = 400f;
            camera.clearFlags = CameraClearFlags.Skybox;
            camera.backgroundColor = SkyColor;
        }

        private static Light CreateLighting()
        {
            var lightObject = new GameObject("M1KeyLight", typeof(Light));
            lightObject.transform.rotation = Quaternion.Euler(48f, -32f, 0f);
            var key = lightObject.GetComponent<Light>();
            key.type = LightType.Directional;
            key.color = new Color(1f, 0.92f, 0.82f);
            key.intensity = 1.15f;
            key.shadows = LightShadows.Soft;
            key.shadowStrength = 0.75f;

            // Lumière d'appoint froide sans ombre : les faces opposées au soleil
            // gardent leur volume, ce qui rend les murs et le personnage lisibles.
            var fillObject = new GameObject("M1FillLight", typeof(Light));
            fillObject.transform.rotation = Quaternion.Euler(22f, 155f, 0f);
            var fill = fillObject.GetComponent<Light>();
            fill.type = LightType.Directional;
            fill.color = new Color(0.62f, 0.72f, 0.95f);
            fill.intensity = 0.35f;
            fill.shadows = LightShadows.None;

            return key;
        }

        private static void ConfigureRenderSettings(Palette palette, Light sun)
        {
            // Trilight explicite plutôt qu'ambiance issue du ciel : le banc est
            // généré sans bake, donc l'éclairage doit être identique en éditeur,
            // en player macOS et en player Windows IL2CPP.
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(0.34f, 0.39f, 0.48f);
            RenderSettings.ambientEquatorColor = new Color(0.26f, 0.28f, 0.33f);
            RenderSettings.ambientGroundColor = new Color(0.12f, 0.13f, 0.16f);
            RenderSettings.skybox = palette.Sky;
            RenderSettings.sun = sun;
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.ExponentialSquared;
            RenderSettings.fogColor = HorizonColor;
            RenderSettings.fogDensity = 0.012f;
        }

        /// <summary>
        /// Personnage du projet monté en visuel pur : layer VisualOnly, aucun
        /// collider, aucun MeshCollider. Sa hauteur et son budget sont vérifiés
        /// pour que le rendu reste aligné sur la capsule simulée de 1,40 m.
        /// </summary>
        private static GameObject CreatePlayerVisual()
        {
            var model = RequireAsset<GameObject>(PlayerModelPath);
            var visual = (GameObject)PrefabUtility.InstantiatePrefab(model);
            if (visual == null)
                throw new InvalidOperationException($"Instanciation impossible: {PlayerModelPath}.");

            visual.name = "Body";
            SetLayerRecursively(visual, GameplayLayers.VisualOnly);
            foreach (var collider in visual.GetComponentsInChildren<Collider>(true))
                UnityEngine.Object.DestroyImmediate(collider, true);

            var animator = visual.GetComponentInChildren<Animator>(true);
            if (animator != null)
            {
                animator.applyRootMotion = false;
                animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;
            }

            ValidatePlayerVisual(visual);
            return visual;
        }

        private static void ValidatePlayerVisual(GameObject visual)
        {
            var renderers = visual.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            if (renderers.Length == 0)
                throw new InvalidOperationException($"{PlayerModelPath} ne contient aucun SkinnedMeshRenderer.");

            var bounds = renderers[0].bounds;
            var bones = new System.Collections.Generic.HashSet<Transform>();
            ulong triangles = 0;
            foreach (var renderer in renderers)
            {
                bounds.Encapsulate(renderer.bounds);
                foreach (var bone in renderer.bones)
                {
                    if (bone != null)
                        bones.Add(bone);
                }

                var mesh = renderer.sharedMesh;
                if (mesh == null)
                    continue;
                for (var subMesh = 0; subMesh < mesh.subMeshCount; subMesh++)
                    triangles += mesh.GetIndexCount(subMesh) / 3;
            }

            if (bounds.size.y < 1.3f || bounds.size.y > 1.45f)
            {
                throw new InvalidOperationException(
                    $"Hauteur Unity du joueur: {bounds.size.y:F3} m, hors contrat [1,30 ; 1,45] m " +
                    $"pour une capsule simulée de {PlayerHeight:F2} m.");
            }
            if (triangles > PlayerTriangleBudget)
                throw new InvalidOperationException(
                    $"Budget joueur dépassé: {triangles} triangles > {PlayerTriangleBudget}.");
            if (bones.Count == 0 || bones.Count > PlayerBoneBudget)
                throw new InvalidOperationException(
                    $"Budget squelette invalide: {bones.Count} bones, attendu 1..{PlayerBoneBudget}.");
            if (visual.GetComponentsInChildren<Collider>(true).Length != 0)
                throw new InvalidOperationException("Le visuel joueur M1 ne doit porter aucun collider.");
        }

        private static void SetLayerRecursively(GameObject value, int layer)
        {
            value.layer = layer;
            for (var index = 0; index < value.transform.childCount; index++)
                SetLayerRecursively(value.transform.GetChild(index).gameObject, layer);
        }

        /// <summary>
        /// Décor lointain strictement visuel : aucun collider, aucun layer
        /// gameplay. Il donne une échelle et un horizon au banc sans ajouter la
        /// moindre surface sur laquelle un joueur pourrait s'appuyer.
        /// </summary>
        private static void CreateDecor(TopologyRuntimeMap map, Palette palette)
        {
            var root = new GameObject("M1Decor").transform;
            var width = (float)((double)map.Dimensions.WidthCells *
                                map.Dimensions.CellPitchMm / 1000d);
            var depth = (float)((double)map.Dimensions.HeightCells *
                                map.Dimensions.CellPitchMm / 1000d);
            var span = Mathf.Max(width, depth);

            var ground = CreateDecorBlock(root, "Ground", palette.DecorGround);
            ground.transform.localPosition = new Vector3(0f, -0.52f, 0f);
            ground.transform.localScale = new Vector3(320f, 1f, 320f);

            var plinth = CreateDecorBlock(root, "Plinth", palette.DecorPlinth);
            plinth.transform.localPosition = new Vector3(0f, -0.35f, 0f);
            plinth.transform.localScale = new Vector3(span + 2.4f, 0.5f, span + 2.4f);

            // Silhouettes semées : le tirage est déterministe, donc les captures de
            // contrôle et les trois fenêtres du test montrent le même horizon.
            var random = new System.Random(20260810);
            const int pillarCount = 18;
            for (var index = 0; index < pillarCount; index++)
            {
                var angle = (float)(index * 2d * Math.PI / pillarCount + random.NextDouble() * 0.2d);
                var radius = span * 4.2f + (float)random.NextDouble() * 38f;
                var height = 5f + (float)random.NextDouble() * 17f;
                var footprint = 2.2f + (float)random.NextDouble() * 4.5f;
                var pillar = CreateDecorBlock(
                    root,
                    $"Pillar_{index:D2}",
                    index % 3 == 0 ? palette.DecorPillarWarm : palette.DecorPillarCool);
                pillar.transform.localPosition = new Vector3(
                    Mathf.Cos(angle) * radius,
                    height * 0.5f - 0.4f,
                    Mathf.Sin(angle) * radius);
                pillar.transform.localScale = new Vector3(footprint, height, footprint);
                pillar.transform.localRotation = Quaternion.Euler(
                    0f,
                    (float)random.NextDouble() * 90f,
                    0f);
            }
        }

        private static GameObject CreateDecorBlock(Transform root, string name, Material material)
        {
            var block = GameObject.CreatePrimitive(PrimitiveType.Cube);
            block.name = name;
            block.layer = GameplayLayers.VisualOnly;
            block.transform.SetParent(root, false);
            UnityEngine.Object.DestroyImmediate(block.GetComponent<Collider>());
            block.GetComponent<MeshRenderer>().sharedMaterial = material;
            return block;
        }

        private static Palette CreatePalette()
        {
            EnsureMaterialsDirectory();
            return new Palette(
                // Blanc : la teinte réelle arrive par bloc de propriétés au runtime,
                // et un défaut blanc reste lisible si un objet en manque.
                CreateLitMaterial("M1Surface", Color.white, 0.16f, false),
                CreateLitMaterial("M1Accent", Color.white, 0.42f, true),
                CreateSkyMaterial(),
                CreateLitMaterial("M1DecorGround", new Color(0.10f, 0.11f, 0.14f), 0.08f, false),
                CreateLitMaterial("M1DecorPlinth", new Color(0.14f, 0.15f, 0.18f), 0.12f, false),
                CreateLitMaterial("M1DecorPillarCool", new Color(0.17f, 0.19f, 0.24f), 0.10f, false),
                CreateLitMaterial("M1DecorPillarWarm", new Color(0.24f, 0.21f, 0.20f), 0.10f, false));
        }

        private static Material CreateLitMaterial(
            string assetName,
            Color color,
            float smoothness,
            bool emissive)
        {
            var shader = Shader.Find(LitShaderName) ??
                         throw new InvalidOperationException(
                             $"Shader « {LitShaderName} » introuvable : le banc M1 exige URP.");
            var material = LoadOrCreateMaterial($"{MaterialsDirectory}/{assetName}.mat", assetName, shader);
            material.SetColor("_BaseColor", color);
            material.SetFloat("_Smoothness", smoothness);
            material.SetFloat("_Metallic", 0f);
            material.SetColor("_EmissionColor", emissive ? color : Color.black);
            if (emissive)
                material.EnableKeyword("_EMISSION");
            else
                material.DisableKeyword("_EMISSION");
            material.globalIlluminationFlags = emissive
                ? MaterialGlobalIlluminationFlags.RealtimeEmissive
                : MaterialGlobalIlluminationFlags.EmissiveIsBlack;
            EditorUtility.SetDirty(material);
            return material;
        }

        private static Material CreateSkyMaterial()
        {
            var shader = Shader.Find(SkyboxShaderName) ??
                         throw new InvalidOperationException(
                             $"Shader « {SkyboxShaderName} » introuvable.");
            var material = LoadOrCreateMaterial($"{MaterialsDirectory}/M1Sky.mat", "M1Sky", shader);
            material.SetColor("_SkyTint", new Color(0.29f, 0.38f, 0.55f));
            material.SetColor("_GroundColor", HorizonColor);
            material.SetFloat("_AtmosphereThickness", 0.85f);
            material.SetFloat("_Exposure", 1.05f);
            material.SetFloat("_SunSize", 0.035f);
            EditorUtility.SetDirty(material);
            return material;
        }

        private static Material LoadOrCreateMaterial(string path, string assetName, Shader shader)
        {
            var existing = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (existing != null)
            {
                existing.shader = shader;
                return existing;
            }

            var created = new Material(shader) { name = assetName };
            AssetDatabase.CreateAsset(created, path);
            return created;
        }

        private static void EnsureMaterialsDirectory()
        {
            EnsureGeneratedDirectory();
            if (!AssetDatabase.IsValidFolder(MaterialsDirectory))
                AssetDatabase.CreateFolder(GeneratedDirectory, "M1Materials");
        }

        /// <summary>
        /// Contrôle de rendu exécuté à chaque génération. Un matériau hors URP
        /// passe la compilation, les tests et les logs, puis sort en magenta dans
        /// le player : seule cette vérification l'attrape avant un humain.
        /// </summary>
        private static void ValidateSceneRendering(Scene scene, params GameObject[] additionalRoots)
        {
            foreach (var root in scene.GetRootGameObjects())
                ValidateRenderers(root);
            foreach (var root in additionalRoots)
                ValidateRenderers(root);

            if (RenderSettings.skybox == null || !IsPipelineShader(RenderSettings.skybox.shader))
                throw new InvalidOperationException("Ciel M1 sans matériau compatible URP.");

            var arena = UnityEngine.Object.FindFirstObjectByType<TopologyArena>(FindObjectsInactive.Include);
            if (arena == null)
                throw new InvalidOperationException("Arène M1 absente de la scène générée.");
            var serializedArena = new SerializedObject(arena);
            foreach (var field in new[] { "_surfaceMaterial", "_accentMaterial" })
            {
                var material = RequireProperty(serializedArena, field).objectReferenceValue as Material;
                if (material == null || !IsPipelineShader(material.shader))
                {
                    throw new InvalidOperationException(
                        $"TopologyArena.{field} doit référencer un matériau URP explicite : " +
                        "sans lui, URP 17 rend toutes les primitives runtime en magenta.");
                }
            }
        }

        private static void ValidateRenderers(GameObject root)
        {
            foreach (var renderer in root.GetComponentsInChildren<Renderer>(true))
            {
                var materials = renderer.sharedMaterials;
                if (materials.Length == 0)
                    throw new InvalidOperationException($"Renderer sans matériau: {HierarchyPath(renderer.transform)}.");
                foreach (var material in materials)
                {
                    if (material == null || material.shader == null || !IsPipelineShader(material.shader))
                    {
                        throw new InvalidOperationException(
                            $"Matériau hors URP sur {HierarchyPath(renderer.transform)}: " +
                            $"« {(material == null ? "aucun" : material.shader == null ? "sans shader" : material.shader.name)} ». " +
                            "Un player URP le rendrait en magenta.");
                    }
                }
            }
        }

        private static bool IsPipelineShader(Shader shader)
        {
            if (shader == null)
                return false;
            return shader.name.StartsWith("Universal Render Pipeline/", StringComparison.Ordinal) ||
                   shader.name.StartsWith("Shader Graphs/", StringComparison.Ordinal) ||
                   shader.name.StartsWith("Skybox/", StringComparison.Ordinal) ||
                   shader.name.StartsWith("TextMeshPro/", StringComparison.Ordinal);
        }

        private static string HierarchyPath(Transform value)
        {
            var path = value.name;
            var current = value.parent;
            while (current != null)
            {
                path = $"{current.name}/{path}";
                current = current.parent;
            }

            return path;
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
            if (map.Spawns.Count != GameplaySpawnCount || !HasMobileWall(map))
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
            if (networkManager.SpawnablePrefabs != prefabCollection ||
                spawner.Spawns.Length != NetworkTestSpawnCount)
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

        /// <summary>Matériaux URP explicites du banc, créés une fois par génération.</summary>
        private readonly struct Palette
        {
            public Palette(
                Material surface,
                Material accent,
                Material sky,
                Material decorGround,
                Material decorPlinth,
                Material decorPillarCool,
                Material decorPillarWarm)
            {
                Surface = surface;
                Accent = accent;
                Sky = sky;
                DecorGround = decorGround;
                DecorPlinth = decorPlinth;
                DecorPillarCool = decorPillarCool;
                DecorPillarWarm = decorPillarWarm;
            }

            public Material Surface { get; }
            public Material Accent { get; }
            public Material Sky { get; }
            public Material DecorGround { get; }
            public Material DecorPlinth { get; }
            public Material DecorPillarCool { get; }
            public Material DecorPillarWarm { get; }
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
