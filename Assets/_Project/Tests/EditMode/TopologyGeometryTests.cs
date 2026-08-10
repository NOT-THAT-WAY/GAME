using System.Collections.Generic;
using System.IO;
using System.Linq;
using NotThatWay.Game.Topology;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace NotThatWay.Game.Tests.EditMode
{
    public sealed class TopologyGeometryTests
    {
        private const string GrayboxPath = "Assets/_Project/Maze/GrayboxTopology2x2.v1.json";

        [Test]
        public void GrayboxFixture_LoadsAsAnImmutableRuntimeMap()
        {
            var created = TopologyRuntimeMap.TryCreateVerified(
                File.ReadAllText(GrayboxPath),
                out var map,
                out var issues);

            Assert.That(created, Is.True, FormatIssues(issues));
            Assert.That(map.TopologyId, Is.EqualTo("graybox-duel-2x2-v1"));
            Assert.That(map.Checksum, Is.EqualTo("2f5f3b1148408d643cad9793fb59d511948bc4f1e252898cf375affd98c13365"));
            Assert.That(map.Walls, Has.Count.EqualTo(9));
            Assert.That(map.Pivots, Has.Count.EqualTo(1));
            // Enceinte close : plus aucune arête de périmètre ouverte, donc aucun
            // moyen de quitter le sol de l'arène pendant un test humain.
            Assert.That(map.Openings, Is.Empty);
            Assert.That(map.Spawns.Select(value => value.SpawnId), Is.EqualTo(new[] { 200, 201 }));
            Assert.That(map.Walls, Is.Not.InstanceOf<List<RuntimeWallDefinition>>());
        }

        [Test]
        public void WallBoxes_AreDerivedExactlyFromMillimeterDimensions()
        {
            var map = LoadMap();

            var stateA = TopologyGeometry.WallBox(map, 10, 0);
            var stateB = TopologyGeometry.WallBox(map, 10, 1);

            Assert.That(stateA.CenterMm.X, Is.EqualTo(0d));
            Assert.That(stateA.CenterMm.Y, Is.EqualTo(1500d));
            Assert.That(stateA.CenterMm.Z, Is.EqualTo(-1375d));
            Assert.That(stateA.SizeMm.X, Is.EqualTo(250d));
            Assert.That(stateA.SizeMm.Y, Is.EqualTo(3000d));
            Assert.That(stateA.SizeMm.Z, Is.EqualTo(2750d));

            Assert.That(stateB.CenterMm.X, Is.EqualTo(-1375d));
            Assert.That(stateB.CenterMm.Y, Is.EqualTo(1500d));
            Assert.That(stateB.CenterMm.Z, Is.EqualTo(0d));
            Assert.That(stateB.SizeMm.X, Is.EqualTo(2750d));
            Assert.That(stateB.SizeMm.Z, Is.EqualTo(250d));
        }

        [Test]
        public void BothGrayboxWallStates_PreserveSpawnConnectivityAndPerimeter()
        {
            var map = LoadMap();
            var states = map.CreateInitialWallStates();

            Assert.That(TopologyConnectivity.ShortestPathLength(
                map, states, map.Spawns[0].Cell, map.Spawns[1].Cell), Is.EqualTo(3));
            Assert.That(TopologyConnectivity.AreAllSpawnsConnected(map, states), Is.True);
            Assert.That(TopologyConnectivity.IsPerimeterClosedExceptOpenings(map, states), Is.True);

            states[10] = 1;

            Assert.That(TopologyConnectivity.ShortestPathLength(
                map, states, map.Spawns[0].Cell, map.Spawns[1].Cell), Is.EqualTo(1));
            Assert.That(TopologyConnectivity.AreAllSpawnsConnected(map, states), Is.True);
            Assert.That(TopologyConnectivity.IsPerimeterClosedExceptOpenings(map, states), Is.True);
        }

        [Test]
        public void Connectivity_ReturnsDisconnectedForAValidButBlockingTopology()
        {
            var source = File.ReadAllText("Assets/_Project/Tests/Fixtures/Topology/valid-minimal.json");
            var authorDocument = TopologyParser.Parse(source).Document;
            authorDocument.Checksum = TopologyCanonicalizer.ComputeChecksum(authorDocument);
            Assert.That(
                TopologyRuntimeMap.TryCreateVerified(
                    WithChecksum(source, authorDocument.Checksum), out var map, out var issues),
                Is.True,
                FormatIssues(issues));

            var states = map.CreateInitialWallStates();

            Assert.That(TopologyConnectivity.AreAllSpawnsConnected(map, states), Is.False);
            Assert.That(TopologyConnectivity.ShortestPathLength(
                map, states, map.Spawns[0].Cell, map.Spawns[1].Cell), Is.EqualTo(-1));

            states[10] = 1;
            var decision = TopologyTransitionGuard.Evaluate(
                map,
                states,
                10,
                0,
                new TopologyTransitionPolicy(true, false, false),
                new TopologyCircleObstacle[0]);
            Assert.That(decision.Allowed, Is.False);
            Assert.That(
                decision.RejectionCode,
                Is.EqualTo(TopologyTransitionRejectionCodes.ConnectivityWouldBreakDuelRegion));
            Assert.That(states[10], Is.EqualTo(1), "Le guard pur ne doit jamais muter l'état fourni.");
        }

        [Test]
        public void Occupancy_RequiresOneValidStatePerWall()
        {
            var map = LoadMap();
            var states = map.CreateInitialWallStates();

            states[10] = 1;
            Assert.That(TopologyConnectivity.BuildOccupiedEdges(map, states), Has.Count.EqualTo(9));

            states.Remove(1005);
            Assert.That(
                () => TopologyConnectivity.BuildOccupiedEdges(map, states),
                Throws.ArgumentException.With.Message.Contains("1005"));
        }

        [Test]
        public void Occupancy_RejectsAnAlternateStateThatCollidesWithAStaticWall()
        {
            var sourceJson = File.ReadAllText(GrayboxPath);
            var parsed = TopologyParser.Parse(sourceJson);
            var document = parsed.Document;
            var originalChecksum = document.Checksum;
            document.Checksum = null;
            document.Walls.Add(
                new TopologyWall
                {
                    WallId = 2000,
                    InitialStateId = 0,
                    States = new List<TopologyWallState>
                    {
                        new()
                        {
                            StateId = 0,
                            Edge = new TopologyEdge { Axis = TopologyEdge.HorizontalAxis, X = 0, Y = 1 },
                            QuarterTurns = 0
                        }
                    }
                });
            document.Checksum = TopologyCanonicalizer.ComputeChecksum(document);
            var extraWall =
                ",\n    {\n" +
                "      \"wallId\": 2000,\n" +
                "      \"initialStateId\": 0,\n" +
                "      \"states\": [\n" +
                "        {\"stateId\": 0, \"edge\": {\"axis\": \"horizontal\", \"x\": 0, \"y\": 1}, \"quarterTurns\": 0}\n" +
                "      ]\n" +
                "    }";
            var modifiedJson = sourceJson
                .Replace("\n  ],\n  \"pivots\":", extraWall + "\n  ],\n  \"pivots\":")
                .Replace(originalChecksum, document.Checksum);
            Assert.That(
                TopologyRuntimeMap.TryCreateVerified(
                    modifiedJson, out var map, out var issues),
                Is.True,
                FormatIssues(issues));
            var states = map.CreateInitialWallStates();
            states[10] = 1;

            Assert.That(
                () => TopologyConnectivity.BuildOccupiedEdges(map, states),
                Throws.InvalidOperationException.With.Message.Contains("Horizontal:0:1"));

            states[10] = 0;
            var decision = TopologyTransitionGuard.Evaluate(
                map,
                states,
                10,
                1,
                new TopologyTransitionPolicy(false, false, false),
                new TopologyCircleObstacle[0]);
            Assert.That(decision.Allowed, Is.False);
            Assert.That(decision.RejectionCode,
                Is.EqualTo(TopologyTransitionRejectionCodes.DestinationEdgeOccupied));
            Assert.That(decision.BlockingId, Is.EqualTo(2000));
            Assert.That(states[10], Is.EqualTo(0));
        }

        [Test]
        public void QuarterTurnSweep_DistinguishesTheSweptArcFromTheOppositeSide()
        {
            var map = LoadMap();
            var sweep = TopologyGeometry.QuarterTurnSweep(map, 10, 0, 1);

            Assert.That(sweep.SignedQuarterTurn, Is.EqualTo(1));
            Assert.That(sweep.IntersectsCircle(-1375, -1375, 450), Is.True);
            Assert.That(sweep.IntersectsCircle(1375, -1375, 450), Is.False);
            Assert.That(sweep.IntersectsCircle(0, 0, 450), Is.True);
            Assert.That(sweep.IntersectsCircle(-6000, -6000, 450), Is.False);
            Assert.That(sweep.IntersectsCircle(125, -1000, 0), Is.True,
                "La frontière fixe épaissie est volontairement inclusive.");
            Assert.That(sweep.IntersectsCircle(126, -1000, 0), Is.False);

            var reverse = TopologyGeometry.QuarterTurnSweep(map, 10, 1, 0);
            Assert.That(reverse.SignedQuarterTurn, Is.EqualTo(-1));
            Assert.That(reverse.IntersectsCircle(-1375, -1375, 450), Is.True);
            Assert.That(reverse.IntersectsCircle(1375, -1375, 450), Is.False);
        }

        [Test]
        public void TransitionGuard_RejectsPlayerInArcAndAcceptsTheOppositeSideWithoutMutation()
        {
            var map = LoadMap();
            var states = map.CreateInitialWallStates();

            var blocked = TopologyTransitionGuard.Evaluate(
                map,
                states,
                10,
                1,
                TopologyTransitionPolicy.GrayboxDuel,
                new[]
                {
                    new TopologyCircleObstacle(300, -1375, -1375, 450),
                    new TopologyCircleObstacle(200, -1375, -1375, 450)
                });
            Assert.That(blocked.Allowed, Is.False);
            Assert.That(blocked.RejectionCode, Is.EqualTo(TopologyTransitionRejectionCodes.PlayerInSweptArc));
            Assert.That(blocked.BlockingId, Is.EqualTo(200));
            Assert.That(states[10], Is.EqualTo(0));

            var maximumIdBlocked = TopologyTransitionGuard.Evaluate(
                map,
                states,
                10,
                1,
                TopologyTransitionPolicy.GrayboxDuel,
                new[] { new TopologyCircleObstacle(int.MaxValue, -1375, -1375, 450) });
            Assert.That(maximumIdBlocked.Allowed, Is.False);
            Assert.That(maximumIdBlocked.RejectionCode,
                Is.EqualTo(TopologyTransitionRejectionCodes.PlayerInSweptArc));
            Assert.That(maximumIdBlocked.BlockingId, Is.EqualTo(int.MaxValue));

            var accepted = TopologyTransitionGuard.Evaluate(
                map,
                states,
                10,
                1,
                TopologyTransitionPolicy.GrayboxDuel,
                new[] { new TopologyCircleObstacle(201, 1375, -1375, 450) });
            Assert.That(accepted.Allowed, Is.True, accepted.RejectionCode);
            Assert.That(states[10], Is.EqualTo(0), "La décision ne devient état qu'après commit autoritaire.");
        }

        [Test]
        public void M1PushPolicy_AllowsTheSweepButRejectsAnOccupiedDestination()
        {
            var map = LoadMap();
            var states = map.CreateInitialWallStates();

            var sweptOnly = TopologyTransitionGuard.Evaluate(
                map,
                states,
                10,
                1,
                TopologyTransitionPolicy.M1PushDuel,
                new[] { new TopologyCircleObstacle(201, -1375, -1375, 450) });
            Assert.That(sweptOnly.Allowed, Is.True, sweptOnly.RejectionCode);
            Assert.That(states[10], Is.EqualTo(0));

            var destinationOccupied = TopologyTransitionGuard.Evaluate(
                map,
                states,
                10,
                1,
                TopologyTransitionPolicy.M1PushDuel,
                new[]
                {
                    new TopologyCircleObstacle(300, -1375, 0, 450),
                    new TopologyCircleObstacle(200, -1375, 0, 450)
                });
            Assert.That(destinationOccupied.Allowed, Is.False);
            Assert.That(
                destinationOccupied.RejectionCode,
                Is.EqualTo(TopologyTransitionRejectionCodes.DestinationPoseOccupied));
            Assert.That(destinationOccupied.BlockingId, Is.EqualTo(200));
            Assert.That(states[10], Is.EqualTo(0),
                "Le preset jouable ne doit pas muter la topologie pendant sa décision.");
        }

        [Test]
        public void TransitionGuard_RejectsAnOpenedPerimeterWithoutMutation()
        {
            var source = File.ReadAllText("Assets/_Project/Tests/Fixtures/Topology/valid-minimal.json");
            var modified = source
                .Replace(
                    "{\"stateId\": 0, \"edge\": {\"axis\": \"vertical\", \"x\": 1, \"y\": 0}, \"quarterTurns\": 0}",
                    "{\"stateId\": 0, \"edge\": {\"axis\": \"horizontal\", \"x\": 0, \"y\": 1}, \"quarterTurns\": 0}")
                .Replace(
                    "{\"stateId\": 1, \"edge\": {\"axis\": \"horizontal\", \"x\": 0, \"y\": 1}, \"quarterTurns\": 1}",
                    "{\"stateId\": 1, \"edge\": {\"axis\": \"vertical\", \"x\": 1, \"y\": 0}, \"quarterTurns\": 3}")
                .Replace(
                    "\n  ],\n  \"pivots\":",
                    ",\n" +
                    "    {\"wallId\": 11, \"initialStateId\": 0, \"states\": [" +
                    "{\"stateId\": 0, \"edge\": {\"axis\": \"horizontal\", \"x\": 1, \"y\": 1}, \"quarterTurns\": 0}]},\n" +
                    "    {\"wallId\": 12, \"initialStateId\": 0, \"states\": [" +
                    "{\"stateId\": 0, \"edge\": {\"axis\": \"horizontal\", \"x\": 0, \"y\": 0}, \"quarterTurns\": 0}]},\n" +
                    "    {\"wallId\": 13, \"initialStateId\": 0, \"states\": [" +
                    "{\"stateId\": 0, \"edge\": {\"axis\": \"horizontal\", \"x\": 1, \"y\": 0}, \"quarterTurns\": 0}]}\n" +
                    "  ],\n  \"pivots\":");
            var author = TopologyParser.Parse(modified);
            Assert.That(author.IsValid, Is.True, FormatIssues(author.Issues));
            var checksum = TopologyCanonicalizer.ComputeChecksum(author.Document);
            Assert.That(
                TopologyRuntimeMap.TryCreateVerified(
                    WithChecksum(modified, checksum), out var map, out var issues),
                Is.True,
                FormatIssues(issues));

            var states = map.CreateInitialWallStates();
            Assert.That(TopologyConnectivity.IsPerimeterClosedExceptOpenings(map, states), Is.True);

            var decision = TopologyTransitionGuard.Evaluate(
                map,
                states,
                10,
                1,
                new TopologyTransitionPolicy(false, true, false),
                new TopologyCircleObstacle[0]);

            Assert.That(decision.Allowed, Is.False);
            Assert.That(decision.RejectionCode, Is.EqualTo(TopologyTransitionRejectionCodes.PerimeterWouldOpen));
            Assert.That(states[10], Is.EqualTo(0));
        }

        [Test]
        public void GeneratedGraybox_HasNoImportedMeshDependency()
        {
            var root = new GameObject("TopologyAssetDependencyTest");
            try
            {
                var arena = root.AddComponent<TopologyArena>();
                arena.BuildFromJson(File.ReadAllText(GrayboxPath));

                Assert.That(arena.GeneratedRoot.GetComponentsInChildren<MeshCollider>(true), Is.Empty);
                foreach (var filter in arena.GeneratedRoot.GetComponentsInChildren<MeshFilter>(true))
                {
                    var assetPath = AssetDatabase.GetAssetPath(filter.sharedMesh);
                    Assert.That(assetPath.EndsWith(".fbx", System.StringComparison.OrdinalIgnoreCase), Is.False,
                        $"Mesh importé interdit dans la collision graybox: {assetPath}");
                }
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        private static TopologyRuntimeMap LoadMap()
        {
            var created = TopologyRuntimeMap.TryCreateVerified(
                File.ReadAllText(GrayboxPath),
                out var map,
                out var issues);
            Assert.That(created, Is.True, FormatIssues(issues));
            return map;
        }

        private static string FormatIssues(IReadOnlyList<TopologyIssue> issues)
        {
            return string.Join(", ", issues.Select(issue => $"{issue.Code}@{issue.Path}"));
        }

        private static string WithChecksum(string source, string checksum)
        {
            var trimmed = source.TrimEnd();
            return trimmed.Substring(0, trimmed.Length - 1) +
                   $",\n  \"checksum\": \"{checksum}\"\n}}";
        }
    }
}
