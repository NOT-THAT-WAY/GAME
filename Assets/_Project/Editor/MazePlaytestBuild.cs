using System;
using System.Collections.Generic;
using System.IO;
using FishNet.Component.Spawning;
using FishNet.Component.Transforming;
using FishNet.Managing;
using FishNet.Managing.Object;
using FishNet.Object;
using FishNet.Transporting.Tugboat;
using NotThatWay.Game.Input;
using NotThatWay.Game.Topology;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.InputSystem;
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
        private const string PivotDirectorPrefabPath = GeneratedDirectory + "/PivotDirector.prefab";
        private const string WallMeshesPath = GeneratedDirectory + "/MazeWallMeshes.asset";
        private const string BotPrefabPath = GeneratedDirectory + "/MazeBot.prefab";
        private const string PunchAnimatorPath = GeneratedDirectory + "/MazePunchAnimator.controller";
        private const string MazeModelPath = "Assets/_Project/Maze/Maze16x16.fbx";
        private const string MazeGridPath = "Assets/_Project/Maze/MazeTopology16x16.v1.json";
        private const string PlayerModelPath = "Assets/_Project/Player/PersoBouleRigged.fbx";
        private const string GameControlsPath = "Assets/_Project/Input/GameControls.inputactions";
        private const string PreviewDirectory = "Logs/MazePlaytest";

        // Gabarit du personnage produit par build_character.py : 1,40 m, origine
        // aux pieds, yeux à 1,03 m.
        private const float PlayerHeight = 1.4f;
        private const float PlayerRadius = 0.45f;
        private const float EyeHeight = 1.05f;
        private const float SpawnHeight = 0.2f;
        private const int PlayerTriangleBudget = 6000;
        private const int PlayerBoneBudget = 16;

        // Cotes du design, reprises de tools/maze-3d/build_maze.py : couloir 2,50 m
        // et murs de 0,25 m d'épaisseur, donc un pas de grille de 2,75 m. La grille
        // JSON ne les transporte pas ; les changer, c'est changer le design.
        private const float GridPitch = 2.75f;

        // Objets du FBX qui arrêtent réellement le joueur. `Props` en fait partie :
        // ce sont des colonnes brisées et des jarres, les traverser se verrait tout
        // de suite. Seule `Vegetation` (mousses, lierres, buissons) reste sans
        // collider, parce qu'elle est dense et qu'on doit pouvoir la longer.
        // `Murs_Statiques` n'y figure pas : ce bloc est découpé par SplitStaticWalls
        // et chaque mur reçoit une boîte aux cotes de la grille, pas un collider de
        // maillage sculpté.
        private static readonly string[] CollidingObjectPrefixes =
        {
            "Pivot_", "Sol_Dalles", "Sol_Sable", "Reperes_Gameplay", "Props"
        };

        // Préfixe des pièces mobiles : chaque pivot est un objet à part, origine sur
        // son nœud, totem et bras réunis. Un export qui les fusionnerait rendrait la
        // rotation impossible, d'où le contrôle de CreateEnvironment.
        private const string PivotPrefix = "Pivot_";
        private const string MergedArmsObject = "Bras_Pivots";

        // Tous les murs statiques sortent du FBX dans un seul maillage fusionné :
        // aucun d'eux ne pourrait bouger seul. SplitStaticWalls le redécoupe en un
        // objet par arête de la grille JSON, ce qui rend chaque mur frappable.
        private const string StaticWallsObject = "Murs_Statiques";

        // Épaisseur d'un mur, du design repris par GridPitch. La hauteur de collision
        // vient désormais de la topologie signée, jamais des bosses du mesh sculpté.
        private const float WallThickness = 0.25f;

        // Adaptateur temporaire des etats typés de MazeTopology16x16.v1.json vers
        // les trois valeurs encore consommees par le generateur historique.
        private const int EmptyWallState = 0;
        private const int StaticWallState = 1;
        private const int PivotWallState = 2;

        private static readonly Color SkyColor = new(0.96f, 0.85f, 0.72f);

        [MenuItem("GAME/Maze Playtest/Create Scene")]
        public static void CreateScene()
        {
            EnsureGeneratedDirectory();

            var layout = ReadLayout();
            var playerPrefab = CreatePlayerPrefab();
            var pivotDirectorPrefab = CreatePivotDirectorPrefab(layout);
            var botPrefab = CreateBotPrefab();
            var prefabCollection = LoadOrCreatePrefabCollection();
            prefabCollection.Clear();
            prefabCollection.AddObject(playerPrefab, true);
            prefabCollection.AddObject(pivotDirectorPrefab, true);
            prefabCollection.AddObject(botPrefab, true);
            EditorUtility.SetDirty(prefabCollection);

            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            CreateEnvironment(layout);
            var spawns = CreateSpawnPoints(layout);
            VerifySpawns(spawns);

            var networkRoot = new GameObject("NetworkManager");
            networkRoot.AddComponent<Tugboat>();
            var networkManager = networkRoot.AddComponent<NetworkManager>();
            networkManager.SpawnablePrefabs = prefabCollection;
            FishNetBuildConfiguration.AddVersionHandshakeGuard(networkRoot);
            networkRoot.AddComponent<ConnectionSmokeTest>();

            var directorSpawner = networkRoot.AddComponent<PivotDirectorSpawner>();
            var serializedDirector = new SerializedObject(directorSpawner);
            serializedDirector.FindProperty("_directorPrefab").objectReferenceValue = pivotDirectorPrefab;
            serializedDirector.ApplyModifiedPropertiesWithoutUndo();

            var spawner = networkRoot.AddComponent<PlayerSpawner>();
            spawner.Spawns = spawns;
            var serializedSpawner = new SerializedObject(spawner);
            serializedSpawner.FindProperty("_playerPrefab").objectReferenceValue = playerPrefab;
            serializedSpawner.ApplyModifiedPropertiesWithoutUndo();

            // Cible immédiatement testable : deux mètres devant la première
            // apparition, dans le passage que VerifySpawns vient de déclarer libre.
            // FindFreeSpot garde une marge de capsule si un prop frôle l'axe.
            var botDirection = spawns[0].forward;
            var botSpot = FindFreeSpot(
                spawns[0].position + botDirection * 2f,
                botDirection, layout.Entrances[0]);
            var botSpawner = networkRoot.AddComponent<SimpleBotSpawner>();
            var serializedBotSpawner = new SerializedObject(botSpawner);
            serializedBotSpawner.FindProperty("_botPrefab").objectReferenceValue = botPrefab;
            serializedBotSpawner.FindProperty("_spawnPosition").vector3Value = botSpot;
            serializedBotSpawner.FindProperty("_spawnRotation").quaternionValue =
                Quaternion.LookRotation(botDirection, Vector3.up);
            serializedBotSpawner.ApplyModifiedPropertiesWithoutUndo();

            EditorSceneManager.MarkSceneDirty(scene);
            if (!EditorSceneManager.SaveScene(scene, ScenePath))
                throw new InvalidOperationException($"Unable to save {ScenePath}.");

            AssetDatabase.SaveAssets();
            Debug.Log($"[GAME-MAZE] Generated {ScenePath} with {spawns.Length} spawn point(s).");
        }

        [MenuItem("GAME/Maze Playtest/Build macOS")]
        public static void BuildMac()
        {
            Build(BuildTarget.StandaloneOSX, "Builds/MazePlaytest/macOS/GAME-Maze-Playtest.app", null);
        }

        [MenuItem("GAME/Maze Playtest/Build Windows")]
        public static void BuildWindows()
        {
            Build(
                BuildTarget.StandaloneWindows64,
                "Builds/MazePlaytest/Windows/GAME-Maze-Playtest.exe",
                ScriptingImplementation.IL2CPP);
        }

        /// <summary>
        /// Rend deux images de contrôle depuis la scène générée : une vue aérienne et
        /// une vue à hauteur d'yeux devant une entrée. Sert de preuve d'échelle et
        /// d'orientation avant de lancer un test à plusieurs.
        /// </summary>
        [MenuItem("GAME/Maze Playtest/Render Preview")]
        public static void RenderPreview()
        {
            // Toujours régénérer : une scène laissée par une exécution précédente
            // ferait mentir l'aperçu sur l'état réel des assets et du script.
            CreateScene();
            EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            Directory.CreateDirectory(PreviewDirectory);

            var layout = ReadLayout();
            var span = layout.Width * GridPitch;

            var aerial = new Vector3(0f, span * 0.95f, span * 0.75f);
            RenderFrom(aerial, Quaternion.LookRotation((Vector3.zero - aerial).normalized, Vector3.up),
                60f, "apercu-aerien.png");

            // Exactement ce que voit un joueur à son apparition : on relit le point
            // d'apparition posé dans la scène plutôt que de le recalculer, sinon
            // l'aperçu pourrait valider une vue que personne n'aura jamais.
            var spawnRoot = GameObject.Find("SpawnPoints");
            if (spawnRoot == null || spawnRoot.transform.childCount == 0)
                throw new InvalidOperationException("Aucun point d'apparition dans la scène générée.");

            var spawn = spawnRoot.transform.GetChild(0);
            RenderFrom(spawn.position + Vector3.up * EyeHeight, spawn.rotation, 70f, "apercu-entree.png");

            Debug.Log($"[GAME-MAZE] Preview images written to {Path.GetFullPath(PreviewDirectory)}.");
        }

        /// <summary>
        /// Gate d'intégration d'un nouvel export joueur : force Unity à repasser le
        /// ModelImporter, puis reconstruit et rend la scène avec le résultat réel.
        /// </summary>
        [MenuItem("GAME/Maze Playtest/Reimport Player + Render Preview")]
        public static void ReimportPlayerAndRenderPreview()
        {
            AssetDatabase.ImportAsset(
                PlayerModelPath,
                ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
            RenderPreview();
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

        private static void Build(
            BuildTarget target,
            string outputPath,
            ScriptingImplementation? forcedBackend)
        {
            CreateScene();
            var platform = target == BuildTarget.StandaloneOSX ? "macos" : "windows";
            BuildIdentityWriter.WriteForBuild("maze", platform);
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(outputPath)) ?? "Builds");

            var options = new BuildPlayerOptions
            {
                scenes = new[] { ScenePath },
                locationPathName = outputPath,
                target = target,
                options = BuildOptions.Development
            };

            using (new ScriptingBackendScope(target, forcedBackend))
            {
                var report = BuildPipeline.BuildPlayer(options);
                if (report.summary.result != BuildResult.Succeeded)
                    throw new BuildFailedException($"Maze playtest build failed: {report.summary.result}.");
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

                var animator = visual.GetComponentInChildren<Animator>(true);
                if (animator == null)
                    animator = visual.AddComponent<Animator>();

                ValidateRiggedPlayerVisual(visual);
                animator.runtimeAnimatorController = CreatePunchAnimatorController(visual);
                animator.applyRootMotion = false;
                animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;

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

                var controls = AssetDatabase.LoadAssetAtPath<InputActionAsset>(GameControlsPath);
                if (!GameControlsContract.TryValidate(controls, out var controlsError))
                {
                    throw new InvalidOperationException(
                        $"Invalid player controls at {GameControlsPath}: {controlsError}.");
                }
                var inputSource = root.AddComponent<PlayerInputSource>();
                inputSource.enabled = false;
                inputSource.Configure(controls);

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

                root.AddComponent<PlayerPunch>();

                var saved = PrefabUtility.SaveAsPrefabAsset(root, PlayerPrefabPath);
                if (saved == null)
                    throw new InvalidOperationException($"Unable to save {PlayerPrefabPath}.");

                return FinalizeNetworkPrefab(saved.GetComponent<NetworkObject>());
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        /// <summary>
        /// Contrôleur minimal : pose de repos vide, clip Punch déclenché par le
        /// paramètre homonyme, puis retour automatique au repos. Le fichier vit
        /// avec les autres sorties locales régénérables de la scène.
        /// </summary>
        private static AnimatorController CreatePunchAnimatorController(GameObject visual)
        {
            var clips = new List<AnimationClip>();
            foreach (var asset in AssetDatabase.LoadAllAssetRepresentationsAtPath(PlayerModelPath))
            {
                if (asset is AnimationClip clip && !clip.name.StartsWith("__preview__", StringComparison.Ordinal))
                    clips.Add(clip);
            }

            AnimationClip punchClip = null;
            foreach (var clip in clips)
            {
                if (clip.name == "Punch")
                {
                    punchClip = clip;
                    break;
                }
            }

            if (punchClip == null && clips.Count == 1)
                punchClip = clips[0];

            if (punchClip == null)
            {
                var names = new List<string>(clips.Count);
                foreach (var clip in clips)
                    names.Add(clip.name);

                throw new InvalidOperationException(
                    $"Clip Punch introuvable dans {PlayerModelPath}. Clips importés: {string.Join(", ", names)}.");
            }

            if (punchClip.length < 0.7f || punchClip.length > 0.9f)
            {
                throw new InvalidOperationException(
                    $"Durée Punch inattendue: {punchClip.length:F3} s (attendu 20 images à 24 fps, environ 0,8 s).");
            }

            var bindings = AnimationUtility.GetCurveBindings(punchClip);
            if (bindings.Length == 0)
                throw new InvalidOperationException($"Le clip {punchClip.name} ne contient aucune courbe Unity.");

            foreach (var binding in bindings)
            {
                if (binding.type != typeof(Transform) || string.IsNullOrEmpty(binding.path))
                    continue;
                if (visual.transform.Find(binding.path) == null)
                    throw new InvalidOperationException(
                        $"Binding Punch introuvable dans le prefab importé: {binding.path} ({binding.propertyName}).");
            }

            if (AssetDatabase.LoadAssetAtPath<AnimatorController>(PunchAnimatorPath) != null)
                AssetDatabase.DeleteAsset(PunchAnimatorPath);

            var controller = AnimatorController.CreateAnimatorControllerAtPath(PunchAnimatorPath);
            controller.AddParameter("Punch", AnimatorControllerParameterType.Trigger);

            var stateMachine = controller.layers[0].stateMachine;
            var idle = stateMachine.AddState("Idle");
            var punch = stateMachine.AddState("Punch");
            punch.motion = punchClip;
            stateMachine.defaultState = idle;

            var enterPunch = stateMachine.AddAnyStateTransition(punch);
            enterPunch.hasExitTime = false;
            enterPunch.duration = 0.03f;
            enterPunch.canTransitionToSelf = false;
            enterPunch.AddCondition(AnimatorConditionMode.If, 0f, "Punch");

            var leavePunch = punch.AddTransition(idle);
            leavePunch.hasExitTime = true;
            leavePunch.exitTime = 1f;
            leavePunch.duration = 0.06f;

            EditorUtility.SetDirty(controller);
            Debug.Log(
                $"[GAME-PUNCH] Clip Unity « {punchClip.name} » importé: {punchClip.length:F3} s, " +
                $"{punchClip.frameRate:F0} fps, {bindings.Length} courbes résolues, loop={punchClip.isLooping}.");
            return controller;
        }

        private static void ValidateRiggedPlayerVisual(GameObject visual)
        {
            var renderers = visual.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            if (renderers.Length == 0)
                throw new InvalidOperationException($"{PlayerModelPath} ne contient aucun SkinnedMeshRenderer.");

            var bounds = renderers[0].bounds;
            var bones = new HashSet<Transform>();
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
                throw new InvalidOperationException(
                    $"Hauteur Unity du joueur: {bounds.size.y:F3} m, hors contrat [1,30 ; 1,45] m.");
            if (triangles > PlayerTriangleBudget)
                throw new InvalidOperationException(
                    $"Budget joueur dépassé: {triangles} triangles > {PlayerTriangleBudget}.");
            if (bones.Count == 0 || bones.Count > PlayerBoneBudget)
                throw new InvalidOperationException(
                    $"Budget squelette invalide: {bones.Count} bones, attendu 1..{PlayerBoneBudget}.");

            Debug.Log(
                $"[GAME-PUNCH] Import Unity validé: {renderers.Length} meshes skinnés, " +
                $"{triangles} triangles, {bones.Count} bones, hauteur {bounds.size.y:F3} m.");
        }

        /// <summary>
        /// Clone réseau simple du personnage : l'hôte le déplace avec
        /// <see cref="SimpleBot"/> et NetworkTransform réplique sa pose racine.
        /// </summary>
        private static NetworkObject CreateBotPrefab()
        {
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(PlayerModelPath);
            if (model == null)
                throw new InvalidOperationException($"Modèle de personnage introuvable: {PlayerModelPath}.");

            var root = new GameObject("MazeBot");
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

                var animator = visual.GetComponentInChildren<Animator>(true);
                if (animator != null)
                {
                    animator.runtimeAnimatorController = null;
                    animator.applyRootMotion = false;
                }

                root.AddComponent<NetworkObject>();

                var networkTransform = root.AddComponent<NetworkTransform>();
                var serializedTransform = new SerializedObject(networkTransform);
                serializedTransform.FindProperty("_componentConfiguration").enumValueIndex =
                    (int)NetworkTransform.ComponentConfigurationType.CharacterController;
                serializedTransform.FindProperty("_clientAuthoritative").boolValue = false;
                serializedTransform.ApplyModifiedPropertiesWithoutUndo();

                var bot = root.AddComponent<SimpleBot>();
                var serializedBot = new SerializedObject(bot);
                serializedBot.FindProperty("_visual").objectReferenceValue = visual.transform;
                serializedBot.ApplyModifiedPropertiesWithoutUndo();

                var saved = PrefabUtility.SaveAsPrefabAsset(root, BotPrefabPath);
                if (saved == null)
                    throw new InvalidOperationException($"Unable to save {BotPrefabPath}.");

                return FinalizeNetworkPrefab(saved.GetComponent<NetworkObject>());
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        private static void CreateEnvironment(MazeLayout layout)
        {
            var mazeModel = AssetDatabase.LoadAssetAtPath<GameObject>(MazeModelPath);
            if (mazeModel == null)
                throw new InvalidOperationException($"Modèle de labyrinthe introuvable: {MazeModelPath}.");

            var maze = (GameObject)PrefabUtility.InstantiatePrefab(mazeModel);
            maze.name = "Maze16x16";
            maze.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);

            var colliders = 0;
            var pivots = new List<Transform>();
            var staticWalls = (Transform)null;
            foreach (var child in maze.GetComponentsInChildren<Transform>(true))
            {
                // Le bloc des murs statiques est traité à part : il est découpé en
                // murs individuels, qui reçoivent un collider de boîte issu de la
                // grille plutôt qu'un MeshCollider sur le décor sculpté.
                if (child.name.StartsWith(StaticWallsObject, StringComparison.Ordinal))
                {
                    staticWalls = child;
                    continue;
                }

                if (child.name.StartsWith(MergedArmsObject, StringComparison.Ordinal))
                {
                    throw new InvalidOperationException(
                        $"{MazeModelPath} contient encore « {MergedArmsObject} » : les bras de tous les pivots y sont fusionnés et aucun ne peut tourner seul. " +
                        "Ré-exporter la map avec tools/maze-3d/build_maze.py, qui sort un objet par pivot.");
                }

                var isPivot = child.name.StartsWith(PivotPrefix, StringComparison.Ordinal);
                if (isPivot)
                {
                    pivots.Add(child);
                    foreach (var legacyCollider in child.GetComponentsInChildren<Collider>(true))
                        UnityEngine.Object.DestroyImmediate(legacyCollider);
                }
                else
                    // Un objet statique ne peut pas bouger : les pivots en sont exclus,
                    // sinon le batching fige leur maillage à l'orientation de départ.
                    GameObjectUtility.SetStaticEditorFlags(child.gameObject, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic);

                if (isPivot || !BlocksThePlayer(child.name) ||
                    !child.TryGetComponent<MeshFilter>(out var meshFilter) || meshFilter.sharedMesh == null)
                    continue;

                child.gameObject.AddComponent<MeshCollider>();
                colliders++;
            }

            if (staticWalls == null)
                throw new InvalidOperationException($"Aucun objet « {StaticWallsObject} » dans {MazeModelPath} : les noms d'objets du FBX ont changé.");

            var movableWalls = SplitStaticWalls(staticWalls, layout);

            if (colliders == 0)
                throw new InvalidOperationException($"Aucun collider posé sur {MazeModelPath} : les noms d'objets du FBX ont changé, revoir CollidingObjectPrefixes.");
            if (pivots.Count == 0)
                throw new InvalidOperationException($"Aucun objet « {PivotPrefix}… » dans {MazeModelPath} : la map ne contient pas de mur pivotant.");

            if (pivots.Count != layout.Topology.Pivots.Count)
            {
                throw new InvalidOperationException(
                    $"Le FBX contient {pivots.Count} pivots, la topologie signee en declare {layout.Topology.Pivots.Count}.");
            }

            var unmatchedPivots = new List<TopologyPivot>(layout.Topology.Pivots);
            var topologyByVisual = new Dictionary<Transform, TopologyPivot>();
            foreach (var visual in pivots)
            {
                TopologyPivot nearest = null;
                var nearestDistance = float.PositiveInfinity;
                foreach (var candidate in unmatchedPivots)
                {
                    var distance = Vector3.Distance(visual.position, NodeToUnity(candidate.Node, layout));
                    if (distance >= nearestDistance)
                        continue;
                    nearest = candidate;
                    nearestDistance = distance;
                }
                if (nearest == null || nearestDistance > 0.1f)
                {
                    throw new InvalidOperationException(
                        $"Le pivot visuel {visual.name} n'a aucun pivot topologique a moins de 0,10 m.");
                }
                topologyByVisual.Add(visual, nearest);
                unmatchedPivots.Remove(nearest);
            }

            // L'index legacy est au moins dérivé de l'ID canonique, plus d'un nom FBX.
            pivots.Sort((left, right) =>
                topologyByVisual[left].PivotId.CompareTo(topologyByVisual[right].PivotId));
            var pivotBoxColliders = 0;
            for (var index = 0; index < pivots.Count; index++)
            {
                var topologyPivot = topologyByVisual[pivots[index]];
                pivotBoxColliders += AddCanonicalPivotColliders(pivots[index], topologyPivot, layout);
                var wall = pivots[index].gameObject.AddComponent<PivotWall>();
                var serializedWall = new SerializedObject(wall);
                serializedWall.FindProperty("_index").intValue = index;
                serializedWall.FindProperty("_pivotId").intValue = topologyPivot.PivotId;
                serializedWall.ApplyModifiedPropertiesWithoutUndo();
            }

            Debug.Log(
                $"[GAME-MAZE] {colliders} MeshCollider(s) decoratifs, {pivotBoxColliders} BoxCollider(s) " +
                $"canoniques sur {pivots.Count} pivot(s), {movableWalls} mur(s) legacy decoupe(s).");

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
            var spectatorPosition = new Vector3(0f, 40f, 32f);
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
            // Le sable s'arrête à 48 m du centre (emprise 44 m + 26 m de débord) :
            // le brouillard fond son bord sans toucher aux couloirs.
            RenderSettings.fogStartDistance = 45f;
            RenderSettings.fogEndDistance = 150f;
            RenderSettings.sun = light;
        }

        /// <summary>
        /// Vérifie chaque apparition contre la géométrie réelle : du sol dessous, pas
        /// de mur autour, et de quoi avancer d'un pas. Un décalage d'axe entre la
        /// grille et le FBX produit des points d'apparition parfaitement plausibles
        /// mais posés dans un mur : seule une mesure sur la scène le détecte.
        /// </summary>
        private static void VerifySpawns(Transform[] spawns)
        {
            Physics.SyncTransforms();

            var failures = new List<string>();
            foreach (var spawn in spawns)
            {
                var feet = spawn.position;
                var chest = feet + Vector3.up * (PlayerHeight / 2f);

                if (!Physics.Raycast(feet + Vector3.up * 3f, Vector3.down, out var ground, 8f))
                    failures.Add($"{spawn.name}: aucun sol sous le point d'apparition.");
                else if (Mathf.Abs(ground.point.y - feet.y) > 1.5f)
                    failures.Add($"{spawn.name}: sol à {ground.point.y:F2} m alors que le joueur est posé à {feet.y:F2} m.");

                var overlaps = Physics.OverlapSphere(chest, PlayerRadius);
                if (overlaps.Length > 0)
                {
                    var names = new List<string>(overlaps.Length);
                    foreach (var overlap in overlaps)
                        names.Add($"{overlap.name} (le plus proche à {Vector3.Distance(chest, overlap.ClosestPoint(chest)):F2} m)");
                    failures.Add($"{spawn.name}: le joueur apparaît dans {string.Join(", ", names)}.");
                }

                if (Physics.Raycast(chest, spawn.forward, out var ahead, GridPitch))
                    failures.Add($"{spawn.name}: obstacle à {ahead.distance:F2} m droit devant ({ahead.collider.name}).");
            }

            if (failures.Count > 0)
                throw new InvalidOperationException("Points d'apparition invalides :\n  " + string.Join("\n  ", failures));

            Debug.Log($"[GAME-MAZE] {spawns.Length} apparition(s) vérifiée(s) : sol présent, pas de collider, passage libre sur {GridPitch:F2} m.");
        }

        /// <summary>
        /// Prefab de l'objet réseau qui détient l'orientation des pivots. Il retrouve
        /// les pivots dans la scène à l'exécution, par leur index, donc rien n'est
        /// sérialisé ici.
        /// </summary>
        private static NetworkObject CreatePivotDirectorPrefab(MazeLayout layout)
        {
            var root = new GameObject("PivotDirector");
            try
            {
                root.AddComponent<NetworkObject>();
                root.AddComponent<PivotDirector>();

                // La grille voyage dans le prefab, donc à l'identique sur les trois
                // machines : les cases interdites aux murs mobiles ne se
                // redécouvrent pas dans la scène et ne dépendent d'aucun nom d'objet.
                var wallDirector = root.AddComponent<MovableWallDirector>();
                var serializedWalls = new SerializedObject(wallDirector);
                serializedWalls.FindProperty("_width").intValue = layout.Width;
                serializedWalls.FindProperty("_height").intValue = layout.Height;

                var blocked = CollectBlockedSlots(layout);
                var blockedProperty = serializedWalls.FindProperty("_blockedSlots");
                blockedProperty.arraySize = blocked.Length;
                for (var index = 0; index < blocked.Length; index++)
                    blockedProperty.GetArrayElementAtIndex(index).intValue = blocked[index];

                serializedWalls.ApplyModifiedPropertiesWithoutUndo();

                var saved = PrefabUtility.SaveAsPrefabAsset(root, PivotDirectorPrefabPath);
                if (saved == null)
                    throw new InvalidOperationException($"Unable to save {PivotDirectorPrefabPath}.");

                return FinalizeNetworkPrefab(saved.GetComponent<NetworkObject>());
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        /// <summary>
        /// Découpe le bloc fusionné des murs statiques en un objet par arête de la
        /// grille, pour que chaque mur puisse coulisser seul.
        ///
        /// Le FBX sort tous les murs statiques dans un seul maillage : aucun d'eux
        /// ne peut bouger. La découpe se fait sur la topologie typée du JSON et non
        /// sur la géométrie — chaque triangle rejoint l'arête dont son barycentre
        /// est le plus proche — donc les identifiants et les colliders viennent de
        /// la grille, pas des triangles (ADR 0004). Le collider est une boîte aux
        /// cotes du design ; le maillage sculpté n'est plus qu'un habillage.
        /// </summary>
        /// <returns>Nombre de murs mobiles créés.</returns>
        private static int SplitStaticWalls(Transform source, MazeLayout layout)
        {
            if (!source.TryGetComponent<MeshFilter>(out var meshFilter) || meshFilter.sharedMesh == null)
                throw new InvalidOperationException($"« {StaticWallsObject} » n'a pas de maillage dans {MazeModelPath}.");

            var mesh = meshFilter.sharedMesh;
            var submeshes = mesh.subMeshCount;
            var sourceRenderer = source.GetComponent<MeshRenderer>();
            var materials = sourceRenderer != null ? sourceRenderer.sharedMaterials : Array.Empty<Material>();
            var parent = source.parent;

            // Les sommets passent une fois en coordonnées monde : les objets créés
            // ensuite sont posés à l'identité sur la case que la grille leur donne,
            // sans hériter de la rotation d'export du FBX.
            var localVertices = mesh.vertices;
            var localNormals = mesh.normals;
            var uv = mesh.uv;
            var vertices = new Vector3[localVertices.Length];
            for (var index = 0; index < vertices.Length; index++)
                vertices[index] = source.TransformPoint(localVertices[index]);

            var normals = new Vector3[localNormals.Length];
            for (var index = 0; index < normals.Length; index++)
                normals[index] = source.TransformDirection(localNormals[index]);

            var buckets = new Dictionary<int, WallBucket>();
            var loose = new List<int>[submeshes];

            for (var submesh = 0; submesh < submeshes; submesh++)
            {
                var indices = mesh.GetTriangles(submesh);
                for (var triangle = 0; triangle < indices.Length; triangle += 3)
                {
                    var centroid = (vertices[indices[triangle]]
                        + vertices[indices[triangle + 1]]
                        + vertices[indices[triangle + 2]]) / 3f;

                    List<int> target;
                    if (TryFindWallSlot(centroid, layout, out var family, out var x, out var y))
                    {
                        var key = MovableWallDirector.SlotKey(family, x, y);
                        if (!buckets.TryGetValue(key, out var bucket))
                        {
                            bucket = new WallBucket(family, x, y, submeshes);
                            buckets.Add(key, bucket);
                        }

                        target = bucket.Triangles[submesh] ??= new List<int>();
                    }
                    else
                    {
                        target = loose[submesh] ??= new List<int>();
                    }

                    target.Add(indices[triangle]);
                    target.Add(indices[triangle + 1]);
                    target.Add(indices[triangle + 2]);
                }
            }

            var keys = new List<int>(buckets.Keys);
            keys.Sort();

            var wallMeshes = new List<Mesh>(keys.Count + 1);
            var movableWalls = 0;

            foreach (var key in keys)
            {
                var bucket = buckets[key];
                var slot = SlotCenterToUnity(bucket.Family, bucket.X, bucket.Y, layout);
                var name = $"Mur_{(bucket.Family == 0 ? "V" : "H")}_{bucket.X}_{bucket.Y}";

                var wallMesh = BuildSubMesh(bucket.Triangles, vertices, normals, uv, slot, name);
                wallMeshes.Add(wallMesh);

                var wallObject = new GameObject(name);
                wallObject.transform.SetParent(parent, false);
                wallObject.transform.SetPositionAndRotation(slot, Quaternion.identity);
                wallObject.AddComponent<MeshFilter>().sharedMesh = wallMesh;
                wallObject.AddComponent<MeshRenderer>().sharedMaterials = materials;

                // Cotes du contrat de topologie : le mesh sculpté reste un habillage
                // et ne décide d'aucune limite physique.
                var box = wallObject.AddComponent<BoxCollider>();
                box.center = new Vector3(0f, layout.WallHeight * 0.5f, 0f);
                box.size = bucket.Family == 0
                    ? new Vector3(WallThickness, layout.WallHeight, GridPitch)
                    : new Vector3(GridPitch, layout.WallHeight, WallThickness);

                if (IsPerimeterSlot(bucket.Family, bucket.X, bucket.Y, layout))
                {
                    // Le pourtour ne pivote pas : il ferme le labyrinthe, et le laisser
                    // statique garde son batching.
                    GameObjectUtility.SetStaticEditorFlags(wallObject,
                        StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic);
                    continue;
                }

                var movable = wallObject.AddComponent<MovableWall>();
                var serialized = new SerializedObject(movable);
                serialized.FindProperty("_id").intValue = movableWalls++;
                serialized.FindProperty("_homeFamily").intValue = bucket.Family;
                serialized.FindProperty("_homeSlotX").intValue = bucket.X;
                serialized.FindProperty("_homeSlotY").intValue = bucket.Y;
                serialized.ApplyModifiedPropertiesWithoutUndo();
            }

            var looseMesh = BuildSubMesh(loose, vertices, normals, uv, Vector3.zero, $"{StaticWallsObject}_Divers");
            if (looseMesh.vertexCount > 0)
            {
                // Restes qui ne tombent sur aucune arête pleine : décor, jamais une
                // règle. Ils gardent le comportement d'avant, collider de maillage
                // compris, et ne bougent pas.
                wallMeshes.Add(looseMesh);
                var looseObject = new GameObject(looseMesh.name);
                looseObject.transform.SetParent(parent, false);
                looseObject.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
                looseObject.AddComponent<MeshFilter>().sharedMesh = looseMesh;
                looseObject.AddComponent<MeshRenderer>().sharedMaterials = materials;
                looseObject.AddComponent<MeshCollider>();
                GameObjectUtility.SetStaticEditorFlags(looseObject,
                    StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic);
            }

            UnityEngine.Object.DestroyImmediate(source.gameObject);
            SaveWallMeshes(wallMeshes);

            var expected = CountMovableSlots(layout);
            if (movableWalls < expected)
            {
                Debug.LogWarning(
                    $"[GAME-MUR] {expected - movableWalls} arête(s) pleine(s) de la grille n'ont reçu aucun triangle : " +
                    "un mur declare par MazeTopology16x16.v1.json est absent du FBX, il ne sera ni visible ni frappable.");
            }

            return movableWalls;
        }

        /// <summary>Triangles d'un mur, regroupés par sous-maillage donc par matériau.</summary>
        private sealed class WallBucket
        {
            public WallBucket(int family, int x, int y, int submeshes)
            {
                Family = family;
                X = x;
                Y = y;
                Triangles = new List<int>[submeshes];
            }

            public int Family { get; }
            public int X { get; }
            public int Y { get; }
            public List<int>[] Triangles { get; }
        }

        /// <summary>
        /// Reconstruit un maillage à partir des triangles retenus, réindexé et
        /// recentré sur <paramref name="origin"/> pour que l'objet créé porte sa
        /// propre position.
        /// </summary>
        private static Mesh BuildSubMesh(
            List<int>[] triangles, Vector3[] vertices, Vector3[] normals, Vector2[] uv, Vector3 origin, string name)
        {
            var map = new Dictionary<int, int>();
            var newVertices = new List<Vector3>();
            var newNormals = normals.Length == vertices.Length ? new List<Vector3>() : null;
            var newUv = uv.Length == vertices.Length ? new List<Vector2>() : null;
            var newTriangles = new List<int>[triangles.Length];

            for (var submesh = 0; submesh < triangles.Length; submesh++)
            {
                var source = triangles[submesh];
                var target = new List<int>(source?.Count ?? 0);
                newTriangles[submesh] = target;
                if (source == null)
                    continue;

                foreach (var index in source)
                {
                    if (!map.TryGetValue(index, out var mapped))
                    {
                        mapped = newVertices.Count;
                        map.Add(index, mapped);
                        newVertices.Add(vertices[index] - origin);
                        newNormals?.Add(normals[index]);
                        newUv?.Add(uv[index]);
                    }

                    target.Add(mapped);
                }
            }

            var mesh = new Mesh { name = name, indexFormat = IndexFormat.UInt32 };
            mesh.SetVertices(newVertices);
            if (newNormals != null)
                mesh.SetNormals(newNormals);
            if (newUv != null)
                mesh.SetUVs(0, newUv);

            mesh.subMeshCount = triangles.Length;
            for (var submesh = 0; submesh < triangles.Length; submesh++)
                mesh.SetTriangles(newTriangles[submesh], submesh);

            mesh.RecalculateBounds();
            return mesh;
        }

        /// <summary>
        /// Les maillages découpés sont enregistrés dans un seul asset. Sans ça, ils
        /// seraient sérialisés dans la scène générée et la feraient enfler à chaque
        /// reconstruction.
        /// </summary>
        private static void SaveWallMeshes(List<Mesh> meshes)
        {
            AssetDatabase.DeleteAsset(WallMeshesPath);

            var created = false;
            foreach (var mesh in meshes)
            {
                if (!created)
                {
                    AssetDatabase.CreateAsset(mesh, WallMeshesPath);
                    created = true;
                }
                else
                {
                    AssetDatabase.AddObjectToAsset(mesh, WallMeshesPath);
                }
            }

            if (created)
                AssetDatabase.SaveAssets();
        }

        /// <summary>
        /// Arête pleine la plus proche d'un point. Inverse de
        /// <see cref="CellCenterToUnity"/> : une arête verticale tient un nœud en x
        /// et court sur une cellule en y, une horizontale fait l'inverse. On garde
        /// la famille dont le point s'écarte le moins de la ligne, et on bascule sur
        /// l'autre si cette arête-là est vide.
        /// </summary>
        private static bool TryFindWallSlot(Vector3 point, MazeLayout layout, out int family, out int x, out int y)
        {
            var nodeX = -point.x / GridPitch + layout.Width / 2f;
            var nodeY = -point.z / GridPitch + layout.Height / 2f;

            var verticalX = Mathf.Clamp(Mathf.RoundToInt(nodeX), 0, layout.Width);
            var verticalY = Mathf.Clamp(Mathf.FloorToInt(nodeY), 0, layout.Height - 1);
            var horizontalX = Mathf.Clamp(Mathf.FloorToInt(nodeX), 0, layout.Width - 1);
            var horizontalY = Mathf.Clamp(Mathf.RoundToInt(nodeY), 0, layout.Height);

            var verticalFirst = Mathf.Abs(nodeX - verticalX) <= Mathf.Abs(nodeY - horizontalY);
            for (var attempt = 0; attempt < 2; attempt++)
            {
                var vertical = verticalFirst == (attempt == 0);
                family = vertical ? 0 : 1;
                x = vertical ? verticalX : horizontalX;
                y = vertical ? verticalY : horizontalY;

                var states = vertical ? layout.VerticalWalls : layout.HorizontalWalls;
                if (states[x, y] == StaticWallState)
                    return true;
            }

            family = 0;
            x = 0;
            y = 0;
            return false;
        }

        /// <summary>
        /// Centre monde d'une arête de la grille. La formule appartient au runtime :
        /// c'est <see cref="MovableWallDirector"/> qui repose les murs à l'exécution,
        /// et deux copies de ce calcul finiraient par diverger.
        /// </summary>
        private static Vector3 SlotCenterToUnity(int family, int x, int y, MazeLayout layout)
        {
            return MovableWallDirector.SlotCenter(family, x, y, layout.Width, layout.Height);
        }

        private static Vector3 NodeToUnity(TopologyPoint node, MazeLayout layout)
        {
            return new Vector3(
                -(node.X - layout.Width / 2f) * GridPitch,
                0f,
                -(node.Y - layout.Height / 2f) * GridPitch);
        }

        private static int AddCanonicalPivotColliders(
            Transform visual,
            TopologyPivot pivot,
            MazeLayout layout)
        {
            var count = 0;
            foreach (var wallId in pivot.WallIds)
            {
                var wall = layout.Topology.Walls.Find(candidate => candidate.WallId == wallId);
                if (wall == null)
                    throw new InvalidOperationException($"Mur canonique {wallId} introuvable pour le pivot {pivot.PivotId}.");
                var initial = wall.States.Find(state => state.StateId == wall.InitialStateId);
                var family = initial.Edge.Axis == TopologyEdge.VerticalAxis ? 0 : 1;
                var center = SlotCenterToUnity(family, initial.Edge.X, initial.Edge.Y, layout);

                var collision = new GameObject($"Collision_Wall_{wall.WallId}");
                collision.transform.SetPositionAndRotation(
                    center + Vector3.up * (layout.WallHeight * 0.5f),
                    Quaternion.identity);
                collision.transform.SetParent(visual, true);
                var box = collision.AddComponent<BoxCollider>();
                box.size = family == 0
                    ? new Vector3(WallThickness, layout.WallHeight, GridPitch)
                    : new Vector3(GridPitch, layout.WallHeight, WallThickness);
                count++;
            }
            return count;
        }

        /// <summary>Arête du pourtour de la map, qui ferme le labyrinthe et ne pivote pas.</summary>
        private static bool IsPerimeterSlot(int family, int x, int y, MazeLayout layout)
        {
            return family == 0
                ? x == 0 || x == layout.Width
                : y == 0 || y == layout.Height;
        }

        /// <summary>Nombre d'arêtes pleines qui devraient donner un mur mobile.</summary>
        private static int CountMovableSlots(MazeLayout layout)
        {
            var count = 0;
            for (var family = 0; family < 2; family++)
            {
                var states = family == 0 ? layout.VerticalWalls : layout.HorizontalWalls;
                for (var x = 0; x < states.GetLength(0); x++)
                {
                    for (var y = 0; y < states.GetLength(1); y++)
                    {
                        if (states[x, y] == StaticWallState && !IsPerimeterSlot(family, x, y, layout))
                            count++;
                    }
                }
            }

            return count;
        }

        /// <summary>
        /// Cases d'arête qu'aucun mur mobile ne peut occuper : les bras de
        /// pivot, qui tournent sur place, et le pourtour de la map, qui doit rester
        /// fermé.
        /// </summary>
        private static int[] CollectBlockedSlots(MazeLayout layout)
        {
            var slots = new List<int>();
            for (var family = 0; family < 2; family++)
            {
                var states = family == 0 ? layout.VerticalWalls : layout.HorizontalWalls;
                for (var x = 0; x < states.GetLength(0); x++)
                {
                    for (var y = 0; y < states.GetLength(1); y++)
                    {
                        if (states[x, y] == EmptyWallState)
                            continue;

                        if (states[x, y] == PivotWallState || IsPerimeterSlot(family, x, y, layout))
                            slots.Add(MovableWallDirector.SlotKey(family, x, y));
                    }
                }
            }

            return slots.ToArray();
        }

        private static bool BlocksThePlayer(string objectName)
        {
            foreach (var prefix in CollidingObjectPrefixes)
            {
                if (objectName.StartsWith(prefix, StringComparison.Ordinal))
                    return true;
            }

            return false;
        }

        /// <summary>
        /// Les prefabs de cette scène utilisent une collection FishNet locale, pas
        /// la collection globale régénérée par le package. On reproduit donc ici
        /// son hash FNV-1 stable basé sur chemin + nom avant le build.
        /// </summary>
        private static NetworkObject FinalizeNetworkPrefab(NetworkObject networkObject)
        {
            if (networkObject == null)
                throw new InvalidOperationException("Prefab réseau généré sans NetworkObject.");

            var pathAndName =
                $"{AssetDatabase.GetAssetPath(networkObject.gameObject)}{networkObject.gameObject.name}"
                    .Trim()
                    .ToLowerInvariant();
            var normalized = string.Empty;
            foreach (var character in pathAndName)
            {
                if ((character >= 'a' && character <= 'z') || (character >= '0' && character <= '9'))
                    normalized += character;
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

        private static Transform[] CreateSpawnPoints(MazeLayout layout)
        {
            var root = new GameObject("SpawnPoints").transform;
            var spawns = new List<Transform>(layout.Entrances.Count);

            // Les colliders du décor existent déjà : on peut interroger la géométrie.
            Physics.SyncTransforms();

            for (var index = 0; index < layout.Entrances.Count; index++)
            {
                var entrance = layout.Entrances[index];
                // Dans la cellule du seuil, et non dehors : le sable extérieur est
                // parsemé de props et le joueur y apparaîtrait le nez sur une colonne.
                var declaredForward = SpawnDirection(layout.SpawnYawQuarterTurns[index]);
                var position = FindFreeSpot(
                    CellCenterToUnity(entrance, layout) + Vector3.up * SpawnHeight,
                    declaredForward,
                    entrance);
                var point = new GameObject(
                    $"Spawn_{layout.SpawnIds[index]}_Cell_{entrance.x}_{entrance.y}").transform;
                point.SetParent(root, false);
                point.SetPositionAndRotation(position, Quaternion.LookRotation(declaredForward, Vector3.up));
                spawns.Add(point);
            }

            return spawns.ToArray();
        }

        /// <summary>
        /// Cherche un emplacement libre dans la cellule d'entrée. Le générateur sème des
        /// colonnes brisées et des jarres jusque dans les couloirs : le centre exact
        /// d'une cellule n'est pas garanti libre, et ça change à chaque graine de map.
        /// </summary>
        private static Vector3 FindFreeSpot(Vector3 center, Vector3 inward, Vector2Int cell)
        {
            var sideways = Vector3.Cross(Vector3.up, inward);
            // Le couloir fait 2,50 m : au-delà de 0,9 m d'écart on sortirait du passage.
            var offsets = new[] { 0f, 0.55f, -0.55f, 0.9f, -0.9f };

            foreach (var along in offsets)
            {
                foreach (var across in offsets)
                {
                    var candidate = center + inward * along + sideways * across;
                    if (Physics.OverlapSphere(candidate + Vector3.up * (PlayerHeight / 2f), PlayerRadius).Length == 0)
                        return candidate;
                }
            }

            throw new InvalidOperationException(
                $"Aucun emplacement libre dans la cellule {cell.x},{cell.y} : le décor l'obstrue entièrement.");
        }

        /// <summary>
        /// Choisit la direction de regard la plus dégagée parmi l'entrée du couloir et
        /// ses deux perpendiculaires. Toutes les cellules d'entrée ne sont pas ouvertes
        /// vers l'intérieur : certaines donnent sur un couloir latéral, et un joueur qui
        /// apparaît le nez contre un mur croit à une map cassée. Faire demi-tour vers la
        /// sortie n'est jamais proposé.
        /// </summary>
        private static Vector3 ClearestDirection(Vector3 spawnPosition, Vector3 inward)
        {
            var chest = spawnPosition + Vector3.up * (PlayerHeight / 2f);
            var maxDistance = GridPitch * 3f;
            var sideways = Vector3.Cross(Vector3.up, inward);

            var best = inward;
            var bestClearance = -1f;
            foreach (var candidate in new[] { inward, sideways, -sideways })
            {
                var clearance = Physics.Raycast(chest, candidate, out var hit, maxDistance) ? hit.distance : maxDistance;

                // À égalité, `inward` est testée en premier et gagne : entrer tout droit
                // reste la lecture naturelle quand le couloir le permet.
                if (clearance <= bestClearance)
                    continue;

                best = candidate;
                bestClearance = clearance;
            }

            return best;
        }

        /// <summary>
        /// Direction d'entrée dans le labyrinthe depuis une cellule de bord. Viser le
        /// trésor serait faux : il est en diagonale pour la plupart des entrées, et le
        /// joueur apparaîtrait face au mur voisin de sa porte.
        /// </summary>
        private static Vector3 InwardDirection(Vector2Int entrance, MazeLayout layout)
        {
            // Les deux axes du plan sont inversés à l'export : un bord « bas » de la
            // grille se retrouve côté +Z dans Unity, un bord « gauche » côté +X.
            if (entrance.y == 0)
                return Vector3.back;
            if (entrance.y == layout.Height - 1)
                return Vector3.forward;
            if (entrance.x == 0)
                return Vector3.left;
            if (entrance.x == layout.Width - 1)
                return Vector3.right;

            throw new InvalidOperationException(
                $"L'entrée {entrance.x},{entrance.y} n'est sur aucun bord de la grille {layout.Width}x{layout.Height}.");
        }

        private static Vector3 SpawnDirection(int yawQuarterTurns)
        {
            return Quaternion.Euler(0f, yawQuarterTurns * 90f, 0f) * Vector3.back;
        }

        /// <summary>
        /// Centre d'une cellule, avec la même formule que le générateur Blender :
        /// un nœud vaut `(i - largeur / 2) * pas`, un centre de cellule ajoute un
        /// demi-pas.
        ///
        /// L'export FBX en `axis_forward=-Z, axis_up=Y` fait pivoter la scène d'un
        /// demi-tour autour de la verticale : Unity reçoit `(-x, z, -y)`, et non
        /// `(x, z, -y)`. Les deux X et Z sont inversés, pas seulement Z. Un seul
        /// signe oublié décale les apparitions d'un bout à l'autre de la map en
        /// gardant l'air correct, d'où le contrôle de VerifySpawns.
        /// </summary>
        private static Vector3 CellCenterToUnity(Vector2Int cell, MazeLayout layout)
        {
            var blenderX = (cell.x - layout.Width / 2f + 0.5f) * GridPitch;
            var blenderY = (cell.y - layout.Height / 2f + 0.5f) * GridPitch;
            return new Vector3(-blenderX, 0f, -blenderY);
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
            public MazeLayout(
                TopologyDocument topology, int width, int height, float wallHeight, List<Vector2Int> entrances,
                List<int> spawnIds, List<int> spawnYawQuarterTurns,
                int[,] verticalWalls, int[,] horizontalWalls)
            {
                Topology = topology;
                Width = width;
                Height = height;
                WallHeight = wallHeight;
                Entrances = entrances;
                SpawnIds = spawnIds;
                SpawnYawQuarterTurns = spawnYawQuarterTurns;
                VerticalWalls = verticalWalls;
                HorizontalWalls = horizontalWalls;
            }

            public TopologyDocument Topology { get; }
            public int Width { get; }
            public int Height { get; }
            public float WallHeight { get; }
            public List<Vector2Int> Entrances { get; }
            public List<int> SpawnIds { get; }
            public List<int> SpawnYawQuarterTurns { get; }

            /// <summary>Arêtes portées par un nœud en x, longues d'une cellule en y : `[largeur + 1, hauteur]`.</summary>
            public int[,] VerticalWalls { get; }

            /// <summary>Arêtes portées par un nœud en y, longues d'une cellule en x : `[largeur, hauteur + 1]`.</summary>
            public int[,] HorizontalWalls { get; }
        }

        /// <summary>
        /// Adapte la topologie runtime stricte vers les deux tables d'aretes encore
        /// consommees par le generateur visuel historique. Le parseur regex precedent
        /// n'est plus une autorite : IDs, dimensions, references et checksum passent
        /// tous par <see cref="TopologyParser"/> avant de toucher la scene.
        /// </summary>
        private static MazeLayout ReadLayout()
        {
            if (!File.Exists(MazeGridPath))
                throw new InvalidOperationException($"Grille du labyrinthe introuvable: {MazeGridPath}.");

            var parsed = TopologyParser.ParseVerified(File.ReadAllText(MazeGridPath));
            if (!parsed.IsValid)
            {
                var first = parsed.Issues[0];
                throw new InvalidOperationException(
                    $"Topologie invalide dans {MazeGridPath}: {first.Code} a {first.Path}.");
            }

            var topology = parsed.Document;
            if (topology.Dimensions.CellPitchMm != Mathf.RoundToInt(GridPitch * 1000f) ||
                topology.Dimensions.WallThicknessMm != Mathf.RoundToInt(WallThickness * 1000f))
            {
                throw new InvalidOperationException(
                    $"Les dimensions de {MazeGridPath} divergent encore des cotes du generateur historique.");
            }

            var width = topology.Dimensions.WidthCells;
            var height = topology.Dimensions.HeightCells;
            var verticalWalls = new int[width + 1, height];
            var horizontalWalls = new int[width, height + 1];
            foreach (var wall in topology.Walls)
            {
                var initial = wall.States.Find(state => state.StateId == wall.InitialStateId);
                var grid = initial.Edge.Axis == TopologyEdge.VerticalAxis ? verticalWalls : horizontalWalls;
                if (grid[initial.Edge.X, initial.Edge.Y] != EmptyWallState)
                {
                    throw new InvalidOperationException(
                        $"Deux murs initiaux occupent l'arete {initial.Edge.Axis}:{initial.Edge.X},{initial.Edge.Y}.");
                }
                grid[initial.Edge.X, initial.Edge.Y] = wall.PivotId.HasValue ? PivotWallState : StaticWallState;
            }

            var orderedSpawns = new List<TopologySpawn>(topology.Spawns);
            orderedSpawns.Sort((left, right) => left.SpawnId.CompareTo(right.SpawnId));
            var entrances = new List<Vector2Int>(orderedSpawns.Count);
            var spawnIds = new List<int>(orderedSpawns.Count);
            var spawnYawQuarterTurns = new List<int>(orderedSpawns.Count);
            foreach (var spawn in orderedSpawns)
            {
                entrances.Add(new Vector2Int(spawn.Cell.X, spawn.Cell.Y));
                spawnIds.Add(spawn.SpawnId);
                spawnYawQuarterTurns.Add(spawn.YawQuarterTurns);
            }
            if (entrances.Count == 0)
                throw new InvalidOperationException($"Aucun spawn declare dans {MazeGridPath}.");

            return new MazeLayout(
                topology,
                width,
                height,
                topology.Dimensions.WallHeightMm / 1000f,
                entrances,
                spawnIds,
                spawnYawQuarterTurns,
                verticalWalls,
                horizontalWalls);
        }
    }
}
