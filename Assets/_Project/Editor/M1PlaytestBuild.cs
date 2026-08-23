using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using FishNet.Component.Transforming;
using FishNet.Component.Spawning;
using FishNet.Managing;
using FishNet.Managing.Object;
using FishNet.Managing.Predicting;
using FishNet.Managing.Timing;
using FishNet.Object;
using FishNet.Transporting.Tugboat;
using NotThatWay.Game.Input;
using NotThatWay.Game.Sandbox;
using NotThatWay.Game.Topology;
using UnityEditor;
using UnityEditor.Animations;
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
        public const string GeneratedBotPrefabPath = "Assets/_GeneratedLocal/M1TrainingBot.prefab";
        public const string GeneratedRockPrefabPath = "Assets/_GeneratedLocal/SandboxRock.prefab";
        public const string GeneratedTrophyPrefabPath = "Assets/_GeneratedLocal/SandboxTrophy.prefab";
        public const string GeneratedPrefabsPath = "Assets/_GeneratedLocal/M1PlaytestPrefabs.asset";

        private const string GeneratedDirectory = "Assets/_GeneratedLocal";
        private const string MaterialsDirectory = GeneratedDirectory + "/M1Materials";
        private const string TopologyPath = "Assets/_Project/Maze/GrayboxTopology2x2.v1.json";
        private const string GameControlsPath = "Assets/_Project/Input/GameControls.inputactions";
        private const string PlayerModelPath = "Assets/_Project/Player/PersoBouleRigged.fbx";
        private const string PreviewDirectory = "Logs/M1Playtest";
        private const string GeneratedAnimatorPath = GeneratedDirectory + "/M1PlayerAnimator.controller";

        // Image du clip Punch où les bras sont tendus : la pose de poussée y est
        // figée en attendant une animation dédiée.
        private const float PushPoseNormalizedTime = 0.45f;
        private const string PunchParameter = "Punch";
        private const string ThrowParameter = "Throw";
        private const string HitParameter = "Hit";
        private const string KnockoutParameter = "Knockout";
        private const string RecoverParameter = "Recover";
        private const string KnockedOutParameter = "KnockedOut";
        private const string CarryKindParameter = "CarryKind";
        private const string MoveSpeedParameter = "MoveSpeed";
        private const string GroundedParameter = "Grounded";
        private const string SprintingParameter = "Sprinting";
        private const string JumpParameter = "Jump";
        private const string LandParameter = "Land";
        private const string PickupParameter = "Pickup";
        private const string DropParameter = "Drop";
        private const string DepositParameter = "Deposit";
        private const string CarryingParameter = "Carrying";
        private const string PushParameter = "Push";
        private const string DiveParameter = "Dive";
        private const string DivingParameter = "Diving";
        private const string DiveRecoveringParameter = "DiveRecovering";

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
            var animatorController = CreatePlayerAnimatorController();
            var playerPrefab = CreatePlayerPrefab(controls, animatorController);
            var botPrefab = CreateBotPrefab(animatorController);
            var wallAuthorityPrefab = CreateWallAuthorityPrefab();
            var rockPrefab = CreateCarryablePrefab(
                SandboxCarryableKind.Rock,
                GeneratedRockPrefabPath,
                CreateLitMaterial("SandboxRock", new Color(0.34f, 0.31f, 0.29f), 0.08f, false));
            var trophyPrefab = CreateCarryablePrefab(
                SandboxCarryableKind.Trophy,
                GeneratedTrophyPrefabPath,
                CreateLitMaterial("SandboxTrophy", new Color(1f, 0.58f, 0.06f), 0.48f, true));
            var prefabCollection = LoadOrCreatePrefabCollection();
            prefabCollection.Clear();
            prefabCollection.AddObject(playerPrefab, true);
            prefabCollection.AddObject(botPrefab, true);
            prefabCollection.AddObject(wallAuthorityPrefab, true);
            prefabCollection.AddObject(rockPrefab, true);
            prefabCollection.AddObject(trophyPrefab, true);
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
            CreateDepositZone(map);
            ConfigureRenderSettings(palette, keyLight);

            var networkRoot = new GameObject("NetworkManager");
            networkRoot.AddComponent<Tugboat>();
            var timeManager = networkRoot.AddComponent<TimeManager>();
            ConfigureTimeManager(timeManager);
            var predictionManager = networkRoot.AddComponent<PredictionManager>();
            ConfigurePredictionManager(predictionManager);

            var networkManager = networkRoot.AddComponent<NetworkManager>();
            networkManager.SpawnablePrefabs = prefabCollection;
            FishNetBuildConfiguration.AddVersionHandshakeGuard(networkRoot);
            var connection = networkRoot.AddComponent<ConnectionSmokeTest>();
            connection.ConfigureDisplay(
                "GAME — banc M1 réseau",
                "Prêt lorsque tous les participants apparaissent dans la liste.",
                true);
            networkRoot.AddComponent<M1PlaytestDiagnostics>();
            networkRoot.AddComponent<M1ScreenshotProbe>();
            networkRoot.AddComponent<M1ControlsOverlay>();

            var spawner = networkRoot.AddComponent<PlayerSpawner>();
            spawner.Spawns = spawns;
            spawner.SetPlayerPrefab(playerPrefab);

            var botSpawner = networkRoot.AddComponent<SimpleBotSpawner>();
            ConfigureBotSpawner(botSpawner, map, botPrefab);

            var wallSpawner = networkRoot.AddComponent<M1WallAuthoritySpawner>();
            var serializedWallSpawner = new SerializedObject(wallSpawner);
            SetObject(serializedWallSpawner, "_authorityPrefab", wallAuthorityPrefab);
            serializedWallSpawner.ApplyModifiedPropertiesWithoutUndo();

            var sandboxSpawner = networkRoot.AddComponent<SandboxWorldSpawner>();
            ConfigureSandboxSpawner(sandboxSpawner, map, rockPrefab, trophyPrefab);

            ValidateSceneContract(
                map,
                arena,
                playerPrefab,
                botPrefab,
                wallAuthorityPrefab,
                rockPrefab,
                trophyPrefab,
                prefabCollection,
                networkManager,
                timeManager,
                predictionManager,
                spawner);
            ValidateSceneRendering(
                scene,
                playerPrefab.gameObject,
                rockPrefab.gameObject,
                trophyPrefab.gameObject);

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
                // L'enceinte est close et haute de 3 m : une vue rasante ne
                // montrerait que le dos d'un mur. Le contrôle se fait de haut.
                var aerial = new Vector3(span * 0.55f, span * 2.4f, -span * 0.85f);
                RenderFrom(
                    aerial,
                    Quaternion.LookRotation((Vector3.up * 0.6f - aerial).normalized, Vector3.up),
                    50f,
                    "apercu-aerien.png");

                // L'enceinte est close sur 3 m : toute vue oblique cache une
                // moitié de l'arène derrière un mur. Le plan zénithal montre les
                // deux pads, le pivot orange et la pose du mur mobile d'un coup.
                // Le pivot du battant est au nœud central de la grille (Étape 1,
                // arène 6x6) : un nœud figé à (1,1) pointait le centre de l'ancienne
                // grille 2x2, pas celui-ci.
                var plan = TopologyGeometry.NodeMm(map, 3, 3).Meters + Vector3.up * span * 1.9f;
                RenderFrom(
                    plan,
                    Quaternion.LookRotation(Vector3.down, Vector3.forward),
                    45f,
                    "apercu-duel.png");

                // En jeu, M1PlayerAppearance masque le corps de son porteur : la
                // capture première personne doit montrer la même chose, sinon elle
                // valide une image que personne ne verra.
                foreach (var renderer in previews[0].GetComponentsInChildren<Renderer>(true))
                {
                    if (M1PlayerAppearance.IsFirstPersonPart(renderer))
                        continue;
                    renderer.shadowCastingMode = ShadowCastingMode.ShadowsOnly;
                }
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
                null);
        }

        [MenuItem("GAME/M1 Playtest/Build Windows")]
        public static void BuildWindows()
        {
            Build(
                BuildTarget.StandaloneWindows64,
                "Builds/M1Playtest/Windows/GAME-M1-Playtest.exe",
                ScriptingImplementation.IL2CPP);
        }

        /// <summary>
        /// Repli de secours tant que le garde du handshake FishNet n'est pas
        /// validé sur Windows IL2CPP (docs/WINDOWS_IL2CPP_BLOCKER.md). Sortie
        /// séparée pour ne pas écraser le build de la cible officielle, et backend
        /// forcé ici plutôt que lu dans les réglages du projet : la machine qui
        /// construit ne doit ni fournir ni conserver le basculement.
        /// </summary>
        [MenuItem("GAME/M1 Playtest/Build Windows (Mono)")]
        public static void BuildWindowsMono()
        {
            Build(
                BuildTarget.StandaloneWindows64,
                "Builds/M1PlaytestMono/Windows/GAME-M1-Playtest.exe",
                ScriptingImplementation.Mono2x);
        }

        private static NetworkObject CreatePlayerPrefab(
            InputActionAsset controls,
            AnimatorController animatorController)
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
                var body = CreatePlayerVisual(animatorController);
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

                root.AddComponent<SandboxPlayerGameplay>();
                root.AddComponent<SandboxPlayerAnimationBridge>();
                root.AddComponent<M1PlayerActions>();
                var divePresentation = root.AddComponent<M1DivePresentation>();
                var serializedDive = new SerializedObject(divePresentation);
                SetObject(serializedDive, "_body", presentation.transform);
                serializedDive.ApplyModifiedPropertiesWithoutUndo();

                var appearance = root.AddComponent<M1PlayerAppearance>();
                var serializedAppearance = new SerializedObject(appearance);
                SetObject(serializedAppearance, "_body", presentation.transform);
                SetObject(serializedAppearance, "_camera", camera);
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

        /// <summary>
        /// Clone réseau serveur-autoritaire du personnage, sans caméra ni entrée.
        /// Il partage le contrôleur d'animation du joueur afin que la préversion
        /// Claude montre marche, frappe et poussée sur le même rig.
        /// </summary>
        private static NetworkObject CreateBotPrefab(AnimatorController animatorController)
        {
            var root = new GameObject("M1TrainingBot")
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
                var body = CreatePlayerVisual(animatorController);
                body.transform.SetParent(presentation.transform, false);

                var networkObject = root.AddComponent<NetworkObject>();
                var serializedNetworkObject = new SerializedObject(networkObject);
                SetBool(serializedNetworkObject, "_enablePrediction", false);
                SetBool(serializedNetworkObject, "_enableStateForwarding", false);
                SetObject(serializedNetworkObject, "_networkTransform", null);
                serializedNetworkObject.ApplyModifiedPropertiesWithoutUndo();

                var networkTransform = root.AddComponent<NetworkTransform>();
                var serializedTransform = new SerializedObject(networkTransform);
                SetEnum(
                    serializedTransform,
                    "_componentConfiguration",
                    (int)NetworkTransform.ComponentConfigurationType.CharacterController);
                SetBool(serializedTransform, "_clientAuthoritative", false);
                SetBool(serializedTransform, "_sendToOwner", true);
                SetInt(serializedTransform, "_interval", 1);
                SetBool(serializedTransform, "_synchronizePosition", true);
                SetBool(serializedTransform, "_synchronizeRotation", true);
                SetBool(serializedTransform, "_synchronizeScale", false);
                SetBool(serializedTransform, "_enableTeleport", true);
                SetFloat(serializedTransform, "_teleportThreshold", 2f);
                serializedTransform.ApplyModifiedPropertiesWithoutUndo();

                var bot = root.AddComponent<SimpleBot>();
                var serializedBot = new SerializedObject(bot);
                SetObject(serializedBot, "_visual", presentation.transform);
                serializedBot.ApplyModifiedPropertiesWithoutUndo();

                var saved = PrefabUtility.SaveAsPrefabAsset(root, GeneratedBotPrefabPath);
                if (saved == null)
                {
                    throw new InvalidOperationException(
                        $"Impossible d'enregistrer {GeneratedBotPrefabPath}.");
                }
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
                // Battant libre : la vitesse suit le bras de levier, sans seuil à
                // charger ni palier. À 60 Hz, 400 milli-degrés par tick font un
                // quart de tour en 3,75 s au bout du battant et en 9,4 s contre le
                // gond (plancher remonté à 400 pour mille pour garder le gond jouable
                // à cette vitesse réduite) — plus lourd qu'avant, toujours immédiat,
                // jamais bloqué dans une pose. Réglage du retour testeur du
                // 2026-08-10 : le battant partait trop vite (docs/M1_WALL_HANDOFF.md).
                SetInt(serializedDirector, "_maximumAngularSpeedMilliDegreesPerTick", 400);
                SetInt(serializedDirector, "_minimumLeveragePermille", 400);
                SetLong(serializedDirector, "_maximumExtrapolationTicks", 180L);
                SetInt(serializedDirector, "_reachFromCapsuleMm", 900);
                serializedDirector.ApplyModifiedPropertiesWithoutUndo();
                root.AddComponent<SandboxRoundDirector>();

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

        private static NetworkObject CreateCarryablePrefab(
            SandboxCarryableKind kind,
            string prefabPath,
            Material material)
        {
            var root = new GameObject($"Sandbox{kind}")
            {
                layer = GameplayLayers.Player
            };
            try
            {
                var networkObject = root.AddComponent<NetworkObject>();
                var serializedNetworkObject = new SerializedObject(networkObject);
                SetBool(serializedNetworkObject, "_enablePrediction", false);
                SetBool(serializedNetworkObject, "_enableStateForwarding", false);
                SetObject(serializedNetworkObject, "_networkTransform", null);
                serializedNetworkObject.ApplyModifiedPropertiesWithoutUndo();

                var body = root.AddComponent<Rigidbody>();
                body.mass = kind == SandboxCarryableKind.Trophy ? 2.5f : 1.3f;
                body.linearDamping = 0.25f;
                body.angularDamping = 0.18f;
                body.interpolation = RigidbodyInterpolation.Interpolate;
                body.collisionDetectionMode = CollisionDetectionMode.ContinuousDynamic;

                Collider collider;
                var visualRoot = new GameObject("Visual")
                {
                    layer = GameplayLayers.VisualOnly
                };
                visualRoot.transform.SetParent(root.transform, false);
                if (kind == SandboxCarryableKind.Rock)
                {
                    var sphere = root.AddComponent<SphereCollider>();
                    sphere.radius = 0.33f;
                    collider = sphere;
                    var visual = CreateCarryableVisualPrimitive(
                        PrimitiveType.Sphere,
                        "Rock",
                        visualRoot.transform,
                        material);
                    visual.transform.localScale = new Vector3(0.66f, 0.55f, 0.62f);
                    visual.transform.localRotation = Quaternion.Euler(13f, 28f, -9f);
                }
                else
                {
                    var box = root.AddComponent<BoxCollider>();
                    box.size = new Vector3(0.78f, 1f, 0.78f);
                    collider = box;
                    var basePart = CreateCarryableVisualPrimitive(
                        PrimitiveType.Cylinder,
                        "Base",
                        visualRoot.transform,
                        material);
                    basePart.transform.localPosition = new Vector3(0f, -0.36f, 0f);
                    basePart.transform.localScale = new Vector3(0.48f, 0.09f, 0.48f);
                    var stem = CreateCarryableVisualPrimitive(
                        PrimitiveType.Cylinder,
                        "Stem",
                        visualRoot.transform,
                        material);
                    stem.transform.localPosition = new Vector3(0f, -0.08f, 0f);
                    stem.transform.localScale = new Vector3(0.13f, 0.24f, 0.13f);
                    var cup = CreateCarryableVisualPrimitive(
                        PrimitiveType.Cylinder,
                        "Cup",
                        visualRoot.transform,
                        material);
                    cup.transform.localPosition = new Vector3(0f, 0.28f, 0f);
                    cup.transform.localScale = new Vector3(0.38f, 0.20f, 0.38f);
                    var crown = CreateCarryableVisualPrimitive(
                        PrimitiveType.Sphere,
                        "Crown",
                        visualRoot.transform,
                        material);
                    crown.transform.localPosition = new Vector3(0f, 0.46f, 0f);
                    crown.transform.localScale = new Vector3(0.58f, 0.20f, 0.58f);
                }
                collider.sharedMaterial = CreateCarryablePhysicsMaterial();

                var networkTransform = root.AddComponent<NetworkTransform>();
                var serializedTransform = new SerializedObject(networkTransform);
                SetEnum(serializedTransform, "_componentConfiguration", 2); // Rigidbody.
                SetBool(serializedTransform, "_synchronizeParent", false);
                SetInt(serializedTransform, "_interpolation", 2);
                SetInt(serializedTransform, "_extrapolation", 2);
                SetBool(serializedTransform, "_enableTeleport", true);
                SetFloat(serializedTransform, "_teleportThreshold", 2f);
                SetBool(serializedTransform, "_clientAuthoritative", false);
                SetBool(serializedTransform, "_sendToOwner", true);
                SetInt(serializedTransform, "_interval", 1);
                SetBool(serializedTransform, "_synchronizePosition", true);
                SetBool(serializedTransform, "_synchronizeRotation", true);
                SetBool(serializedTransform, "_synchronizeScale", false);
                serializedTransform.ApplyModifiedPropertiesWithoutUndo();

                var carryable = root.AddComponent<SandboxCarryable>();
                var serializedCarryable = new SerializedObject(carryable);
                SetEnum(serializedCarryable, "_kind", (int)kind);
                SetObject(serializedCarryable, "_visualRoot", visualRoot.transform);
                SetObject(serializedCarryable, "_gameplayCollider", collider);
                SetObject(serializedCarryable, "_body", body);
                serializedCarryable.ApplyModifiedPropertiesWithoutUndo();

                var saved = PrefabUtility.SaveAsPrefabAsset(root, prefabPath);
                if (saved == null)
                    throw new InvalidOperationException($"Impossible d'enregistrer {prefabPath}.");
                return FinalizeNetworkPrefab(saved.GetComponent<NetworkObject>());
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        private static GameObject CreateCarryableVisualPrimitive(
            PrimitiveType primitiveType,
            string name,
            Transform parent,
            Material material)
        {
            var value = GameObject.CreatePrimitive(primitiveType);
            value.name = name;
            value.layer = GameplayLayers.VisualOnly;
            value.transform.SetParent(parent, false);
            UnityEngine.Object.DestroyImmediate(value.GetComponent<Collider>());
            value.GetComponent<MeshRenderer>().sharedMaterial = material;
            return value;
        }

        private static PhysicsMaterial CreateCarryablePhysicsMaterial()
        {
            const string path = MaterialsDirectory + "/SandboxCarryableBounce.physicMaterial";
            var existing = AssetDatabase.LoadAssetAtPath<PhysicsMaterial>(path);
            if (existing != null)
                return existing;
            var created = new PhysicsMaterial("SandboxCarryableBounce")
            {
                bounciness = 0.42f,
                dynamicFriction = 0.48f,
                staticFriction = 0.55f,
                bounceCombine = PhysicsMaterialCombine.Maximum,
                frictionCombine = PhysicsMaterialCombine.Average
            };
            AssetDatabase.CreateAsset(created, path);
            return created;
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
            SetBool(serialized, "_jumpEnabled", true);
            SetFloat(serialized, "_jumpSpeed", 5.5f);
            SetLong(serialized, "_coyoteTicks", 7L);
            SetLong(serialized, "_jumpBufferTicks", 9L);
            SetFloat(serialized, "_knockbackDecay", 10f);
            SetInt(serialized, "_maximumPitchCentidegrees", 8500);
            // Plongeon avant (baseline de banc, DEC-01 ouvert), seulement depuis un
            // sprint : 13 m/s vers l'avant et 4,2 m/s vers le haut, soit ~5 m de
            // bond à gravité -22 (premier essai à 8,5/3,2 jugé trop court) ;
            // relevé 0,4 s, puis 1,5 s avant le suivant.
            SetBool(serialized, "_diveEnabled", true);
            SetFloat(serialized, "_diveForwardSpeed", 13f);
            SetFloat(serialized, "_diveUpwardSpeed", 4.2f);
            SetLong(serialized, "_diveRecoveryTicks", 24L);
            SetLong(serialized, "_diveCooldownTicks", 90L);
            serialized.ApplyModifiedPropertiesWithoutUndo();
        }

        private static void ConfigureSandboxSpawner(
            SandboxWorldSpawner spawner,
            TopologyRuntimeMap map,
            NetworkObject rockPrefab,
            NetworkObject trophyPrefab)
        {
            var rockCells = new[]
            {
                new TopologyGridCell(0, 3),
                new TopologyGridCell(5, 3),
                new TopologyGridCell(1, 4),
                new TopologyGridCell(4, 4),
                new TopologyGridCell(1, 1),
                new TopologyGridCell(4, 1)
            };
            var rockPositions = new Vector3[rockCells.Length];
            for (var index = 0; index < rockCells.Length; index++)
            {
                rockPositions[index] = TopologyGeometry.CellCenterMm(map, rockCells[index]).Meters +
                                       Vector3.up * 0.38f;
            }

            var serialized = new SerializedObject(spawner);
            SetObject(serialized, "_rockPrefab", rockPrefab);
            SetObject(serialized, "_trophyPrefab", trophyPrefab);
            SetVector3Array(serialized, "_rockSpawnPositions", rockPositions);
            SetVector3(
                serialized,
                "_trophySpawnPosition",
                TopologyGeometry.CellCenterMm(map, new TopologyGridCell(2, 5)).Meters +
                Vector3.up * 0.55f);
            serialized.ApplyModifiedPropertiesWithoutUndo();
        }

        private static void ConfigureBotSpawner(
            SimpleBotSpawner spawner,
            TopologyRuntimeMap map,
            NetworkObject botPrefab)
        {
            // Une cellule au nord du premier joueur : assez proche pour que la
            // poursuite soit visible immédiatement, sans superposer les capsules.
            var position = TopologyGeometry.CellCenterMm(
                               map,
                               new TopologyGridCell(2, 3)).Meters +
                           Vector3.up * SpawnHeight;
            var serialized = new SerializedObject(spawner);
            SetObject(serialized, "_botPrefab", botPrefab);
            SetVector3(serialized, "_spawnPosition", position);
            SetQuaternion(serialized, "_spawnRotation", Quaternion.Euler(0f, 180f, 0f));
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
            // Angle assez haut pour voir par-dessus l'enceinte close de 3 m : la
            // caméra d'attente doit montrer l'arène, pas le dos d'un mur.
            cameraObject.transform.position = new Vector3(0f, width * 1.7f, -width * 0.95f);
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
        private static GameObject CreatePlayerVisual(AnimatorController animatorController)
        {
            if (animatorController == null)
                throw new ArgumentNullException(nameof(animatorController));
            var model = RequireAsset<GameObject>(PlayerModelPath);
            var visual = (GameObject)PrefabUtility.InstantiatePrefab(model);
            if (visual == null)
                throw new InvalidOperationException($"Instanciation impossible: {PlayerModelPath}.");

            visual.name = "Body";
            SetLayerRecursively(visual, GameplayLayers.VisualOnly);
            foreach (var collider in visual.GetComponentsInChildren<Collider>(true))
                UnityEngine.Object.DestroyImmediate(collider, true);

            var animator = visual.GetComponentInChildren<Animator>(true) ??
                           visual.AddComponent<Animator>();
            animator.applyRootMotion = false;
            animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;
            animator.runtimeAnimatorController = animatorController;

            ValidatePlayerVisual(visual);
            return visual;
        }

        /// <summary>
        /// Contrôleur minimal du banc : repos vide, coup de poing déclenché par
        /// son trigger, et pose de poussée obtenue en figeant le même clip sur son
        /// image bras tendus. L'animation dédiée viendra de Blender ; d'ici là ce
        /// gel donne un retour visuel honnête sans inventer d'os.
        /// </summary>
        private static AnimatorController CreatePlayerAnimatorController()
        {
            var clip = LoadPunchClip();
            if (AssetDatabase.LoadAssetAtPath<AnimatorController>(GeneratedAnimatorPath) != null)
                AssetDatabase.DeleteAsset(GeneratedAnimatorPath);

            var controller = AnimatorController.CreateAnimatorControllerAtPath(GeneratedAnimatorPath);
            controller.AddParameter(PunchParameter, AnimatorControllerParameterType.Trigger);
            controller.AddParameter(ThrowParameter, AnimatorControllerParameterType.Trigger);
            controller.AddParameter(HitParameter, AnimatorControllerParameterType.Trigger);
            controller.AddParameter(KnockoutParameter, AnimatorControllerParameterType.Trigger);
            controller.AddParameter(RecoverParameter, AnimatorControllerParameterType.Trigger);
            controller.AddParameter(KnockedOutParameter, AnimatorControllerParameterType.Bool);
            controller.AddParameter(CarryKindParameter, AnimatorControllerParameterType.Int);
            controller.AddParameter(MoveSpeedParameter, AnimatorControllerParameterType.Float);
            controller.AddParameter(GroundedParameter, AnimatorControllerParameterType.Bool);
            controller.AddParameter(SprintingParameter, AnimatorControllerParameterType.Bool);
            controller.AddParameter(JumpParameter, AnimatorControllerParameterType.Trigger);
            controller.AddParameter(LandParameter, AnimatorControllerParameterType.Trigger);
            controller.AddParameter(PickupParameter, AnimatorControllerParameterType.Trigger);
            controller.AddParameter(DropParameter, AnimatorControllerParameterType.Trigger);
            controller.AddParameter(DepositParameter, AnimatorControllerParameterType.Trigger);
            controller.AddParameter(CarryingParameter, AnimatorControllerParameterType.Bool);
            controller.AddParameter(PushParameter, AnimatorControllerParameterType.Bool);
            controller.AddParameter(DiveParameter, AnimatorControllerParameterType.Trigger);
            controller.AddParameter(DivingParameter, AnimatorControllerParameterType.Bool);
            controller.AddParameter(DiveRecoveringParameter, AnimatorControllerParameterType.Bool);

            var stateMachine = controller.layers[0].stateMachine;
            var idle = stateMachine.AddState("Idle");
            var punch = stateMachine.AddState("Punch");
            punch.motion = clip;
            var push = stateMachine.AddState("Push");
            push.motion = clip;
            push.speed = 0f;
            push.cycleOffset = PushPoseNormalizedTime;
            stateMachine.defaultState = idle;

            var enterPunch = stateMachine.AddAnyStateTransition(punch);
            enterPunch.hasExitTime = false;
            enterPunch.duration = 0.03f;
            enterPunch.canTransitionToSelf = false;
            enterPunch.AddCondition(AnimatorConditionMode.If, 0f, PunchParameter);

            var leavePunch = punch.AddTransition(idle);
            leavePunch.hasExitTime = true;
            leavePunch.exitTime = 1f;
            leavePunch.duration = 0.06f;

            var enterPush = idle.AddTransition(push);
            enterPush.hasExitTime = false;
            enterPush.duration = 0.18f;
            enterPush.AddCondition(AnimatorConditionMode.If, 0f, PushParameter);

            var leavePush = push.AddTransition(idle);
            leavePush.hasExitTime = false;
            leavePush.duration = 0.18f;
            leavePush.AddCondition(AnimatorConditionMode.IfNot, 0f, PushParameter);

            EditorUtility.SetDirty(controller);
            return controller;
        }

        private static AnimationClip LoadPunchClip()
        {
            AnimationClip single = null;
            var count = 0;
            foreach (var asset in AssetDatabase.LoadAllAssetRepresentationsAtPath(PlayerModelPath))
            {
                if (asset is not AnimationClip clip ||
                    clip.name.StartsWith("__preview__", StringComparison.Ordinal))
                {
                    continue;
                }

                count++;
                if (clip.name == "Punch")
                    return clip;
                single = clip;
            }

            return count == 1 && single != null
                ? single
                : throw new InvalidOperationException(
                    $"Clip Punch introuvable dans {PlayerModelPath} ({count} clips importés).");
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

        private static void CreateDepositZone(TopologyRuntimeMap map)
        {
            var root = new GameObject("SandboxDepositZone")
            {
                layer = GameplayLayers.Player
            };
            root.transform.position =
                TopologyGeometry.CellCenterMm(map, new TopologyGridCell(3, 0)).Meters;
            var trigger = root.AddComponent<BoxCollider>();
            trigger.isTrigger = true;
            trigger.center = new Vector3(0f, 0.75f, 0f);
            trigger.size = new Vector3(2.1f, 1.5f, 2.1f);
            root.AddComponent<SandboxDepositZone>();

            var material = CreateLitMaterial(
                "SandboxDeposit",
                new Color(1f, 0.28f, 0.04f),
                0.34f,
                true);
            var marker = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            marker.name = "DepositMarker";
            marker.layer = GameplayLayers.VisualOnly;
            marker.transform.SetParent(root.transform, false);
            marker.transform.localPosition = Vector3.up * 0.04f;
            marker.transform.localScale = new Vector3(1.05f, 0.04f, 1.05f);
            UnityEngine.Object.DestroyImmediate(marker.GetComponent<Collider>());
            marker.GetComponent<MeshRenderer>().sharedMaterial = material;

            var beacon = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            beacon.name = "DepositBeacon";
            beacon.layer = GameplayLayers.VisualOnly;
            beacon.transform.SetParent(root.transform, false);
            beacon.transform.localPosition = new Vector3(0f, 0.55f, 0f);
            beacon.transform.localScale = new Vector3(0.10f, 0.5f, 0.10f);
            UnityEngine.Object.DestroyImmediate(beacon.GetComponent<Collider>());
            beacon.GetComponent<MeshRenderer>().sharedMaterial = material;
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
            NetworkObject botPrefab,
            NetworkObject wallAuthorityPrefab,
            NetworkObject rockPrefab,
            NetworkObject trophyPrefab,
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
            if (arena == null || playerPrefab == null || botPrefab == null ||
                wallAuthorityPrefab == null ||
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
            var playerMotor = playerObject.GetComponent<PredictedPlayerMotor>();
            if (playerObject.layer != GameplayLayers.Player ||
                playerObject.GetComponent<CharacterController>() == null ||
                playerObject.GetComponent<PlayerInputSource>() == null ||
                playerMotor == null ||
                playerObject.GetComponent<SandboxPlayerGameplay>() == null ||
                playerObject.GetComponent<SandboxPlayerAnimationBridge>() == null ||
                playerObject.GetComponent<M1PlayerActions>() == null ||
                playerObject.GetComponent<M1PlayerAppearance>() == null)
            {
                throw new InvalidOperationException("Contrat du prefab joueur M1 incomplet.");
            }
            var serializedMotor = new SerializedObject(playerMotor);
            if (!RequireProperty(serializedMotor, "_jumpEnabled").boolValue)
                throw new InvalidOperationException("Le saut doit rester actif dans le sandbox M1.");
            ValidateAnimatorContract(playerObject);
            if (playerObject.GetComponent<FishNet.Component.Transforming.NetworkTransform>() != null)
                throw new InvalidOperationException("Le joueur prédit M1 ne doit pas avoir de NetworkTransform.");

            var botObject = botPrefab.gameObject;
            if (botPrefab.EnablePrediction ||
                botObject.layer != GameplayLayers.Player ||
                botObject.GetComponent<CharacterController>() == null ||
                botObject.GetComponent<NetworkTransform>() == null ||
                botObject.GetComponent<SimpleBot>() == null)
            {
                throw new InvalidOperationException("Contrat du bot d'entraînement M1 incomplet.");
            }
            ValidateAnimatorContract(botObject);
            if (wallAuthorityPrefab.GetComponent<M1AuthoritativeWallDirector>() == null ||
                wallAuthorityPrefab.GetComponent<SandboxRoundDirector>() == null ||
                wallAuthorityPrefab.EnablePrediction)
            {
                throw new InvalidOperationException("Prefab d'autorité murale M1 invalide.");
            }
            foreach (var carryable in new[] { rockPrefab, trophyPrefab })
            {
                if (carryable == null || carryable.EnablePrediction ||
                    carryable.GetComponent<SandboxCarryable>() == null ||
                    carryable.GetComponent<Rigidbody>() == null ||
                    carryable.GetComponent<NetworkTransform>() == null)
                {
                    throw new InvalidOperationException("Prefab carryable du sandbox invalide.");
                }
            }
            if (UnityEngine.Object.FindFirstObjectByType<SimpleBotSpawner>() == null ||
                UnityEngine.Object.FindFirstObjectByType<SandboxWorldSpawner>() == null ||
                UnityEngine.Object.FindFirstObjectByType<SandboxDepositZone>() == null)
            {
                throw new InvalidOperationException("Boucle objets/trophée du sandbox incomplète.");
            }
        }

        private static void ValidateAnimatorContract(GameObject playerObject)
        {
            var animator = playerObject.GetComponentInChildren<Animator>(true);
            var controller = animator == null
                ? null
                : animator.runtimeAnimatorController as AnimatorController;
            if (animator == null || controller == null)
                throw new InvalidOperationException("Animator joueur M1 absent ou non éditable.");
            if (animator.applyRootMotion)
                throw new InvalidOperationException("Le root motion doit rester désactivé dans le sandbox M1.");

            var expected = new Dictionary<string, AnimatorControllerParameterType>
            {
                [PunchParameter] = AnimatorControllerParameterType.Trigger,
                [ThrowParameter] = AnimatorControllerParameterType.Trigger,
                [HitParameter] = AnimatorControllerParameterType.Trigger,
                [KnockoutParameter] = AnimatorControllerParameterType.Trigger,
                [RecoverParameter] = AnimatorControllerParameterType.Trigger,
                [KnockedOutParameter] = AnimatorControllerParameterType.Bool,
                [CarryKindParameter] = AnimatorControllerParameterType.Int,
                [MoveSpeedParameter] = AnimatorControllerParameterType.Float,
                [GroundedParameter] = AnimatorControllerParameterType.Bool,
                [SprintingParameter] = AnimatorControllerParameterType.Bool,
                [JumpParameter] = AnimatorControllerParameterType.Trigger,
                [LandParameter] = AnimatorControllerParameterType.Trigger,
                [PickupParameter] = AnimatorControllerParameterType.Trigger,
                [DropParameter] = AnimatorControllerParameterType.Trigger,
                [DepositParameter] = AnimatorControllerParameterType.Trigger,
                [CarryingParameter] = AnimatorControllerParameterType.Bool,
                [PushParameter] = AnimatorControllerParameterType.Bool,
                [DiveParameter] = AnimatorControllerParameterType.Trigger,
                [DivingParameter] = AnimatorControllerParameterType.Bool,
                [DiveRecoveringParameter] = AnimatorControllerParameterType.Bool
            };
            var actual = new Dictionary<string, AnimatorControllerParameterType>();
            foreach (var parameter in controller.parameters)
                actual[parameter.name] = parameter.type;
            foreach (var entry in expected)
            {
                if (!actual.TryGetValue(entry.Key, out var type) || type != entry.Value)
                {
                    throw new InvalidOperationException(
                        $"Paramètre Animator M1 invalide: {entry.Key} doit être {entry.Value}.");
                }
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

        private static void Build(
            BuildTarget target,
            string outputPath,
            ScriptingImplementation? forcedBackend)
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

            using (new ScriptingBackendScope(target, forcedBackend))
            {
                var report = BuildPipeline.BuildPlayer(options);
                if (report.summary.result != BuildResult.Succeeded)
                    throw new BuildFailedException($"Build M1 échoué: {report.summary.result}.");
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

        private static void SetVector3(SerializedObject serialized, string name, Vector3 value) =>
            RequireProperty(serialized, name).vector3Value = value;

        private static void SetQuaternion(
            SerializedObject serialized,
            string name,
            Quaternion value) =>
            RequireProperty(serialized, name).quaternionValue = value;

        private static void SetVector3Array(
            SerializedObject serialized,
            string name,
            IReadOnlyList<Vector3> values)
        {
            var property = RequireProperty(serialized, name);
            property.arraySize = values.Count;
            for (var index = 0; index < values.Count; index++)
                property.GetArrayElementAtIndex(index).vector3Value = values[index];
        }

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
