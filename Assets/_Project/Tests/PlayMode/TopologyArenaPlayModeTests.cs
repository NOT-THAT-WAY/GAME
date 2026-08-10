using System.Collections;
using System.Globalization;
using System.IO;
using System.Linq;
using NotThatWay.Game.Simulation;
using NotThatWay.Game.Topology;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace NotThatWay.Game.Tests.PlayMode
{
    public sealed class TopologyArenaPlayModeTests
    {
        private const string GrayboxPath = "Assets/_Project/Maze/GrayboxTopology2x2.v1.json";

        [UnityTest]
        public IEnumerator PunchRay_OnlyResolvesTheMobileWallInFrontOfThePlayer()
        {
            var root = new GameObject("PunchRayTest");
            try
            {
                var arena = root.AddComponent<TopologyArena>();
                arena.BuildFromJson(File.ReadAllText(GrayboxPath));
                yield return null;
                Physics.SyncTransforms();

                var origin = new Vector3(1.375f, 0.7f, -1.375f);
                var worldMask = 1 << GameplayLayers.World;
                Assert.That(
                    Physics.Raycast(
                        origin,
                        Vector3.left,
                        out var towardWall,
                        2f,
                        worldMask,
                        QueryTriggerInteraction.Ignore),
                    Is.True);
                Assert.That(
                    M1PunchTargeting.TryResolveWallCollider(
                        towardWall.collider,
                        10,
                        out var mobileWall),
                    Is.True);
                Assert.That(mobileWall, Is.EqualTo(arena.GetWallView(10)));

                // L'arène est passée de 2x2 à 6x6 cellules (Étape 1) : l'enceinte la
                // plus proche à l'est de la cellule (3,2) est désormais à 6,75 m
                // (grille x=6, face intérieure à 8,25 m - 0,125 m de demi-épaisseur -
                // 1,375 m d'origine), donc la portée du rayon doit suivre.
                Assert.That(
                    Physics.Raycast(
                        origin,
                        Vector3.right,
                        out var awayFromWall,
                        10f,
                        worldMask,
                        QueryTriggerInteraction.Ignore),
                    Is.True,
                    "Le rayon opposé doit rencontrer l'enceinte statique, pas le battant.");
                Assert.That(
                    M1PunchTargeting.TryResolveWallCollider(
                        awayFromWall.collider,
                        10,
                        out _),
                    Is.False,
                    "Un coup dos au battant ne doit jamais verser d'effort au mur mobile.");
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        /// <summary>
        /// Le mur qui balaie doit réellement recouvrir la capsule d'un joueur
        /// planté dans l'arc : c'est ce recouvrement, mesuré à mi-course, qui
        /// déclenche la poussée autoritaire du banc M1.
        /// </summary>
        [UnityTest]
        public IEnumerator MidTransitionPose_OverlapsAPlayerStandingInTheSweptArc()
        {
            var root = new GameObject("SweepOverlapTest");
            var player = new GameObject("SweepOverlapPlayer") { layer = GameplayLayers.Player };
            try
            {
                var arena = root.AddComponent<TopologyArena>();
                arena.BuildFromJson(File.ReadAllText(GrayboxPath));
                yield return null;

                var controller = player.AddComponent<CharacterController>();
                controller.height = 1.4f;
                controller.radius = 0.4f;
                controller.center = new Vector3(0f, 0.7f, 0f);
                // Centre de la cellule (2,2), c'est-à-dire le quart balayé (arène
                // 6x6, mêmes coordonnées monde que l'ancienne cellule (0,0) en 2x2
                // puisque le pivot reste centré sur l'origine).
                player.transform.position = new Vector3(-1.375f, 0f, -1.375f);
                Physics.SyncTransforms();

                var view = arena.GetWallView(10);
                var box = view.GetComponent<BoxCollider>();
                var found = false;
                var results = new Collider[8];
                for (var angle = 0; angle <= 90000 && !found; angle += 1000)
                {
                    arena.ApplyAuthoritativePose(10, WallPoseSample.Stable(angle));

                    var scale = view.transform.lossyScale;
                    var halfExtents = new Vector3(
                        Mathf.Abs(box.size.x * scale.x),
                        Mathf.Abs(box.size.y * scale.y),
                        Mathf.Abs(box.size.z * scale.z)) * 0.5f;
                    var count = Physics.OverlapBoxNonAlloc(
                        view.transform.TransformPoint(box.center),
                        halfExtents,
                        results,
                        view.transform.rotation,
                        1 << GameplayLayers.Player,
                        QueryTriggerInteraction.Ignore);
                    for (var index = 0; index < count; index++)
                        found |= results[index] == controller;
                }

                Assert.That(
                    found,
                    Is.True,
                    "La pose intermédiaire du mur doit recouvrir un joueur resté dans l'arc.");
            }
            finally
            {
                Object.DestroyImmediate(player);
                Object.DestroyImmediate(root);
            }
        }

        [UnityTest]
        public IEnumerator Graybox_IsBuiltFromCanonicalPrimitiveCollidersAndResetsExactly()
        {
            var root = new GameObject("TopologyArenaPlayModeTest");
            try
            {
                var arena = root.AddComponent<TopologyArena>();
                arena.BuildFromJson(File.ReadAllText(GrayboxPath));
                yield return null;

                Assert.That(arena.Map.Checksum,
                    Is.EqualTo("b21e351222f20d1e3433de8f4d7db25535ff6a66edaef0b6e58b2228e4e0bc4e"));
                Assert.That(arena.WallCount, Is.EqualTo(25));
                Assert.That(arena.HasOnlyPrimitiveGameplayColliders(), Is.True);
                Assert.That(arena.GeneratedRoot.GetComponentsInChildren<MeshCollider>(true), Is.Empty);
                var enabledColliders = arena.GeneratedRoot.GetComponentsInChildren<Collider>(true)
                    .Where(value => value.enabled)
                    .ToArray();
                Assert.That(enabledColliders, Has.Length.EqualTo(26),
                    "Un sol et vingt-cinq murs doivent être les seuls colliders actifs.");
                Assert.That(enabledColliders.All(value => value.gameObject.layer == GameplayLayers.World), Is.True);
                Assert.That(
                    arena.GeneratedRoot.GetComponentsInChildren<Collider>(true)
                        .Where(value => !value.enabled)
                        .All(value => value.gameObject.layer == GameplayLayers.VisualOnly),
                    Is.True);
                GameplayLayers.ValidateProjectConfiguration();
                for (var firstLayer = 0; firstLayer < 32; firstLayer++)
                {
                    for (var secondLayer = firstLayer; secondLayer < 32; secondLayer++)
                    {
                        Assert.That(
                            Physics.GetIgnoreLayerCollision(firstLayer, secondLayer),
                            Is.EqualTo(!GameplayLayers.ShouldCollide(firstLayer, secondLayer)),
                            $"Paire de layers {firstLayer}/{secondLayer}");
                    }
                }

                var ids = arena.GeneratedRoot.GetComponentsInChildren<TopologyWallView>(true)
                    .Select(value => value.WallId)
                    .ToArray();
                Assert.That(
                    ids,
                    Is.EqualTo(new[]
                    {
                        10,
                        1000, 1001, 1002, 1003, 1004, 1005,
                        1006, 1007, 1008, 1009, 1010, 1011,
                        1012, 1013, 1014, 1015, 1016, 1017,
                        1018, 1019, 1020, 1021, 1022, 1023
                    }));

                var wall = arena.GetWallView(10);
                var initialPosition = wall.transform.localPosition;
                var initialScale = wall.transform.localScale;
                var initialSnapshot = Snapshot(arena);
                var initialStates = StateSnapshot(arena);
                Assert.That(wall.StateId, Is.EqualTo(0));

                var blocked = arena.TryGrayboxTransitionWall(
                    10,
                    1,
                    new[] { new TopologyCircleObstacle(200, -1375, -1375, 450) });
                Assert.That(blocked.Allowed, Is.False);
                Assert.That(blocked.RejectionCode, Is.EqualTo(TopologyTransitionRejectionCodes.PlayerInSweptArc));
                Assert.That(blocked.BlockingId, Is.EqualTo(200));
                Assert.That(wall.StateId, Is.EqualTo(0));
                Assert.That(wall.transform.localPosition, Is.EqualTo(initialPosition));
                Assert.That(wall.transform.localScale, Is.EqualTo(initialScale));

                // Le battant est libre : une pose intermédiaire n'est plus un
                // couple d'états mais un angle, et le collider la suit exactement.
                arena.ApplyAuthoritativePose(10, WallPoseSample.Stable(45000));
                Assert.That(wall.AngleMilliDegrees, Is.EqualTo(45000));
                Assert.That(wall.transform.localPosition.x, Is.EqualTo(-0.9723f).Within(0.002f));
                Assert.That(wall.transform.localPosition.z, Is.EqualTo(-0.9723f).Within(0.002f));
                Assert.That(wall.transform.eulerAngles.y, Is.EqualTo(45f).Within(0.01f));
                Assert.That(wall.transform.localScale, Is.EqualTo(new Vector3(0.25f, 3f, 2.75f)));
                arena.ApplyAuthoritativeState(10, 0);

                var forward = arena.TryGrayboxTransitionWall(
                    10,
                    1,
                    new[] { new TopologyCircleObstacle(201, 1375, -1375, 450) });
                Assert.That(forward.Allowed, Is.True, forward.RejectionCode);

                var reverseBlocked = arena.TryGrayboxTransitionWall(
                    10,
                    0,
                    new[] { new TopologyCircleObstacle(200, -1375, -1375, 450) });
                Assert.That(reverseBlocked.Allowed, Is.False);
                Assert.That(reverseBlocked.RejectionCode,
                    Is.EqualTo(TopologyTransitionRejectionCodes.PlayerInSweptArc));
                Assert.That(wall.StateId, Is.EqualTo(1));

                var reverseAccepted = arena.TryGrayboxTransitionWall(
                    10,
                    0,
                    new[] { new TopologyCircleObstacle(201, 1375, -1375, 450) });
                Assert.That(reverseAccepted.Allowed, Is.True, reverseAccepted.RejectionCode);
                Assert.That(StateSnapshot(arena), Is.EqualTo(initialStates));
                Assert.That(Snapshot(arena), Is.EqualTo(initialSnapshot));

                for (var reset = 0; reset < 3; reset++)
                {
                    var accepted = arena.TryGrayboxTransitionWall(
                        10,
                        1,
                        new[] { new TopologyCircleObstacle(201, 1375, -1375, 450) });
                    Assert.That(accepted.Allowed, Is.True, accepted.RejectionCode);
                    Assert.That(wall.StateId, Is.EqualTo(1));
                    Assert.That(wall.AngleMilliDegrees, Is.EqualTo(90000));
                    // La pose déclarée est désormais atteinte par rotation autour du
                    // gond : la comparaison garde la tolérance d'un quaternion.
                    Assert.That(wall.transform.localPosition.x, Is.EqualTo(-1.375f).Within(0.0005f));
                    Assert.That(wall.transform.localPosition.y, Is.EqualTo(1.5f).Within(0.0005f));
                    Assert.That(wall.transform.localPosition.z, Is.EqualTo(0f).Within(0.0005f));
                    Assert.That(wall.transform.localScale, Is.EqualTo(new Vector3(0.25f, 3f, 2.75f)));
                    Assert.That(wall.transform.eulerAngles.y, Is.EqualTo(90f).Within(0.001f));
                    Assert.That(TopologyConnectivity.AreAllSpawnsConnected(arena.Map, arena.WallStates), Is.True);

                    arena.ResetToInitialStates();
                    Assert.That(wall.StateId, Is.EqualTo(0));
                    Assert.That(wall.transform.localPosition, Is.EqualTo(initialPosition));
                    Assert.That(wall.transform.localScale, Is.EqualTo(initialScale));
                    Assert.That(StateSnapshot(arena), Is.EqualTo(initialStates));
                    Assert.That(Snapshot(arena), Is.EqualTo(initialSnapshot));
                }

                var initialSpec = TopologyGeometry.WallBox(arena.Map, 10, 0);
                var hits = Physics.OverlapBox(initialSpec.CenterMeters, initialSpec.SizeMeters * 0.45f);
                Assert.That(hits.Select(value => value.GetComponent<TopologyWallView>()?.WallId), Does.Contain(10));
                var alternateSpec = TopologyGeometry.WallBox(arena.Map, 10, 1);
                var alternateHits = Physics.OverlapBox(
                    alternateSpec.CenterMeters,
                    alternateSpec.SizeMeters * 0.45f);
                Assert.That(
                    alternateHits.Any(value => value.GetComponent<TopologyWallView>()?.WallId == 10),
                    Is.False);
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        [UnityTest]
        public IEnumerator TwoIndependentBuilds_ProduceTheSameHierarchyAndTransforms()
        {
            var firstRoot = new GameObject("FirstArena");
            var secondRoot = new GameObject("SecondArena");
            try
            {
                var source = File.ReadAllText(GrayboxPath);
                firstRoot.transform.position = new Vector3(4f, 0f, -2f);
                firstRoot.transform.rotation = Quaternion.Euler(0f, 90f, 0f);
                var first = firstRoot.AddComponent<TopologyArena>();
                var second = secondRoot.AddComponent<TopologyArena>();
                first.BuildFromJson(source);
                second.BuildFromJson(source);

                var worldCenter = firstRoot.transform.TransformPoint(new Vector3(-1.375f, 0f, -1.375f));
                var localObstacle = first.CreateObstacleFromWorld(200, worldCenter, 0.45f);
                Assert.That(localObstacle.CenterXMm, Is.EqualTo(-1375));
                Assert.That(localObstacle.CenterZMm, Is.EqualTo(-1375));
                Assert.That(localObstacle.RadiusMm, Is.EqualTo(451));

                var beforeRebuild = Snapshot(first);
                var previousGeneratedRoot = first.GeneratedRoot;
                first.BuildFromJson(source);
                Assert.That(previousGeneratedRoot.gameObject.activeSelf, Is.False,
                    "La racine remplacée doit quitter la physique avant le Destroy différé.");
                Assert.That(
                    firstRoot.transform.Cast<Transform>()
                        .Count(value => value.gameObject.activeSelf && value.name.StartsWith("Generated_")),
                    Is.EqualTo(1));
                Assert.That(Snapshot(first), Is.EqualTo(beforeRebuild));
                yield return null;

                Assert.That(previousGeneratedRoot == null, Is.True);
                Assert.That(Snapshot(second), Is.EqualTo(Snapshot(first)));
            }
            finally
            {
                Object.DestroyImmediate(firstRoot);
                Object.DestroyImmediate(secondRoot);
            }
        }

        private static string[] Snapshot(TopologyArena arena)
        {
            return arena.GeneratedRoot.GetComponentsInChildren<Transform>(true)
                .Select(value =>
                {
                    var position = value.localPosition;
                    var rotation = value.localRotation;
                    var scale = value.localScale;
                    var collider = value.GetComponent<Collider>();
                    var colliderDescription = collider == null
                        ? "none"
                        : $"{collider.GetType().Name}:{collider.enabled}";
                    return $"{PathFrom(value, arena.GeneratedRoot)}|" +
                           $"{Format(position.x)},{Format(position.y)},{Format(position.z)}|" +
                           $"{Format(rotation.x)},{Format(rotation.y)},{Format(rotation.z)},{Format(rotation.w)}|" +
                           $"{Format(scale.x)},{Format(scale.y)},{Format(scale.z)}|" +
                           $"L{value.gameObject.layer}|{colliderDescription}";
                })
                .ToArray();
        }

        private static string[] StateSnapshot(TopologyArena arena)
        {
            return arena.WallStates
                .OrderBy(value => value.Key)
                .Select(value => $"{value.Key}:{value.Value}")
                .ToArray();
        }

        private static string PathFrom(Transform value, Transform root)
        {
            var path = value.name;
            while (value != root)
            {
                value = value.parent;
                if (value != null)
                    path = value.name + "/" + path;
            }
            return path;
        }

        private static string Format(float value) => value.ToString("R", CultureInfo.InvariantCulture);
    }
}
