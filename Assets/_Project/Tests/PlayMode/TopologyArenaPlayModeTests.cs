using System.Collections;
using System.Globalization;
using System.IO;
using System.Linq;
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
        public IEnumerator Graybox_IsBuiltFromCanonicalPrimitiveCollidersAndResetsExactly()
        {
            var root = new GameObject("TopologyArenaPlayModeTest");
            try
            {
                var arena = root.AddComponent<TopologyArena>();
                arena.BuildFromJson(File.ReadAllText(GrayboxPath));
                yield return null;

                Assert.That(arena.Map.Checksum,
                    Is.EqualTo("031f7dfb01b8308cdc1c773842a6e1a31a2d293bc82cbcfb1fa06b7af94d03aa"));
                Assert.That(arena.WallCount, Is.EqualTo(7));
                Assert.That(arena.HasOnlyPrimitiveGameplayColliders(), Is.True);
                Assert.That(arena.GeneratedRoot.GetComponentsInChildren<MeshCollider>(true), Is.Empty);
                var enabledColliders = arena.GeneratedRoot.GetComponentsInChildren<Collider>(true)
                    .Where(value => value.enabled)
                    .ToArray();
                Assert.That(enabledColliders, Has.Length.EqualTo(8),
                    "Un sol et sept murs doivent être les seuls colliders actifs.");
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
                Assert.That(ids, Is.EqualTo(new[] { 10, 1000, 1001, 1002, 1003, 1004, 1005 }));

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
                    Assert.That(wall.transform.localPosition, Is.EqualTo(new Vector3(-1.375f, 1.5f, 0f)));
                    Assert.That(wall.transform.localScale, Is.EqualTo(new Vector3(2.75f, 3f, 0.25f)));
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
