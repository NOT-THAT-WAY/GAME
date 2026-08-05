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
using UnityEditor.Animations;
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
        private const string PivotDirectorPrefabPath = GeneratedDirectory + "/PivotDirector.prefab";
        private const string BotPrefabPath = GeneratedDirectory + "/MazeBot.prefab";
        private const string PunchAnimatorPath = GeneratedDirectory + "/MazePunchAnimator.controller";
        private const string MazeModelPath = "Assets/_Project/Maze/Maze16x16.fbx";
        private const string MazeGridPath = "Assets/_Project/Maze/MazeGrid16x16.json";
        private const string PlayerModelPath = "Assets/_Project/Player/PersoBouleRigged.fbx";
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
        private static readonly string[] CollidingObjectPrefixes =
        {
            "Murs_Statiques", "Pivot_", "Sol_Dalles", "Sol_Sable", "Reperes_Gameplay", "Props"
        };

        // Préfixe des pièces mobiles : chaque pivot est un objet à part, origine sur
        // son nœud, totem et bras réunis. Un export qui les fusionnerait rendrait la
        // rotation impossible, d'où le contrôle de CreateEnvironment.
        private const string PivotPrefix = "Pivot_";
        private const string MergedArmsObject = "Bras_Pivots";

        private static readonly Color SkyColor = new(0.96f, 0.85f, 0.72f);

        [MenuItem("GAME/Maze Playtest/Create Scene")]
        public static void CreateScene()
        {
            EnsureGeneratedDirectory();

            var layout = ReadLayout();
            var playerPrefab = CreatePlayerPrefab();
            var pivotDirectorPrefab = CreatePivotDirectorPrefab();
            var botPrefab = CreateBotPrefab();
            var prefabCollection = LoadOrCreatePrefabCollection();
            prefabCollection.Clear();
            prefabCollection.AddObject(playerPrefab, true);
            prefabCollection.AddObject(pivotDirectorPrefab, true);
            prefabCollection.AddObject(botPrefab, true);
            EditorUtility.SetDirty(prefabCollection);

            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            CreateEnvironment();
            var spawns = CreateSpawnPoints(layout);
            VerifySpawns(spawns);

            var networkRoot = new GameObject("NetworkManager");
            networkRoot.AddComponent<Tugboat>();
            var networkManager = networkRoot.AddComponent<NetworkManager>();
            networkManager.SpawnablePrefabs = prefabCollection;
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

        private static void CreateEnvironment()
        {
            var mazeModel = AssetDatabase.LoadAssetAtPath<GameObject>(MazeModelPath);
            if (mazeModel == null)
                throw new InvalidOperationException($"Modèle de labyrinthe introuvable: {MazeModelPath}.");

            var maze = (GameObject)PrefabUtility.InstantiatePrefab(mazeModel);
            maze.name = "Maze16x16";
            maze.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);

            var colliders = 0;
            var pivots = new List<Transform>();
            foreach (var child in maze.GetComponentsInChildren<Transform>(true))
            {
                if (child.name.StartsWith(MergedArmsObject, StringComparison.Ordinal))
                {
                    throw new InvalidOperationException(
                        $"{MazeModelPath} contient encore « {MergedArmsObject} » : les bras de tous les pivots y sont fusionnés et aucun ne peut tourner seul. " +
                        "Ré-exporter la map avec tools/maze-3d/build_maze.py, qui sort un objet par pivot.");
                }

                var isPivot = child.name.StartsWith(PivotPrefix, StringComparison.Ordinal);
                if (isPivot)
                    pivots.Add(child);
                else
                    // Un objet statique ne peut pas bouger : les pivots en sont exclus,
                    // sinon le batching fige leur maillage à l'orientation de départ.
                    GameObjectUtility.SetStaticEditorFlags(child.gameObject, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic);

                if (!BlocksThePlayer(child.name) || !child.TryGetComponent<MeshFilter>(out var meshFilter) || meshFilter.sharedMesh == null)
                    continue;

                child.gameObject.AddComponent<MeshCollider>();
                colliders++;
            }

            if (colliders == 0)
                throw new InvalidOperationException($"Aucun collider posé sur {MazeModelPath} : les noms d'objets du FBX ont changé, revoir CollidingObjectPrefixes.");
            if (pivots.Count == 0)
                throw new InvalidOperationException($"Aucun objet « {PivotPrefix}… » dans {MazeModelPath} : la map ne contient pas de mur pivotant.");

            // Ordre de nom : les trois machines numérotent les pivots pareil sans
            // s'échanger la carte, et l'index suffit à désigner un pivot sur le réseau.
            pivots.Sort((left, right) => string.CompareOrdinal(left.name, right.name));
            for (var index = 0; index < pivots.Count; index++)
            {
                var wall = pivots[index].gameObject.AddComponent<PivotWall>();
                var serializedWall = new SerializedObject(wall);
                serializedWall.FindProperty("_index").intValue = index;
                serializedWall.ApplyModifiedPropertiesWithoutUndo();
            }

            Debug.Log($"[GAME-MAZE] {colliders} MeshCollider(s) posé(s), {pivots.Count} pivot(s) mobile(s) indexé(s).");

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
        private static NetworkObject CreatePivotDirectorPrefab()
        {
            var root = new GameObject("PivotDirector");
            try
            {
                root.AddComponent<NetworkObject>();
                root.AddComponent<PivotDirector>();

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

            foreach (var entrance in layout.Entrances)
            {
                // Dans la cellule du seuil, et non dehors : le sable extérieur est
                // parsemé de props et le joueur y apparaîtrait le nez sur une colonne.
                var inward = InwardDirection(entrance, layout);
                var position = FindFreeSpot(CellCenterToUnity(entrance, layout) + Vector3.up * SpawnHeight, inward, entrance);
                var point = new GameObject($"Spawn_Cell_{entrance.x}_{entrance.y}").transform;
                point.SetParent(root, false);
                point.SetPositionAndRotation(position, Quaternion.LookRotation(ClearestDirection(position, inward), Vector3.up));
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
            public MazeLayout(int width, int height, List<Vector2Int> entrances, Vector2Int treasure)
            {
                Width = width;
                Height = height;
                Entrances = entrances;
                Treasure = treasure;
            }

            public int Width { get; }
            public int Height { get; }
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
