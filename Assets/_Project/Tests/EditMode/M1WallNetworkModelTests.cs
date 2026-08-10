using System;
using System.IO;
using NotThatWay.Game.Simulation;
using NotThatWay.Game.Topology;
using NUnit.Framework;

namespace NotThatWay.Game.Tests.EditMode
{
    public sealed class M1WallNetworkModelTests
    {
        private const string GrayboxPath = "Assets/_Project/Maze/GrayboxTopology2x2.v1.json";

        [Test]
        public void InteractionRule_DerivesOppositeSignsAndRangeFromCanonicalGeometry()
        {
            var map = LoadMap();

            var safeRight = M1WallInteractionRules.Evaluate(
                map, 10, 0, 1375, -1375, 451, 900);
            var sweptLeft = M1WallInteractionRules.Evaluate(
                map, 10, 0, -1375, -1375, 451, 900);
            var tooFar = M1WallInteractionRules.Evaluate(
                map, 10, 0, 5000, -1375, 451, 900);

            // Pose B : le mur pointe à l'ouest et son retour balaie le sud. On
            // le renvoie donc vers A depuis le nord, jamais depuis le sud où le
            // pousseur se placerait devant le battant.
            var northOfPoseB = M1WallInteractionRules.Evaluate(
                map, 10, 1, -1375, 800, 451, 900);
            var southOfPoseB = M1WallInteractionRules.Evaluate(
                map, 10, 1, -1375, -800, 451, 900);

            Assert.That(safeRight.Allowed, Is.True);
            Assert.That(safeRight.EffortSign, Is.EqualTo(1));
            Assert.That(sweptLeft.Allowed, Is.True);
            Assert.That(sweptLeft.EffortSign, Is.EqualTo(-1));
            Assert.That(tooFar.Allowed, Is.False);
            Assert.That(tooFar.Rejection, Is.EqualTo(M1WallInteractionRejection.OutOfReach));
            Assert.That(northOfPoseB.Allowed, Is.True);
            Assert.That(
                northOfPoseB.EffortSign,
                Is.EqualTo(-1),
                "Depuis le nord, le mur repart vers le sud : le trajet retour doit être possible.");
            Assert.That(southOfPoseB.Allowed, Is.True);
            Assert.That(
                southOfPoseB.EffortSign,
                Is.EqualTo(1),
                "Depuis l'arc balayé, on retient le mur au lieu de le ramener sur soi.");

            var staticWall = M1WallInteractionRules.Evaluate(
                map, 1000, 0, -2750, -1375, 451, 900);
            Assert.That(staticWall.Rejection, Is.EqualTo(M1WallInteractionRejection.WallStatic));
        }

        [Test]
        public void PunchCadence_RequiresThreeChainedPunchesToStartTheWall()
        {
            const int wallId = 10;
            const int effortPerTick = 4;
            var settings = new WallSimulationSettings(
                effortThreshold: 360,
                maximumEffortPerSourcePerTick: effortPerTick,
                effortDecayPerTick: 2,
                rejectedEffortRetention: 0,
                transitionDurationTicks: 90u);
            var machine = new WallStateMachine(settings, wallId, 0, 1, 0, 0u);
            var firstPunchTick = 1u;
            var secondPunchTick = firstPunchTick + M1PunchTuning.CooldownTicks;
            var thirdPunchTick = secondPunchTick + M1PunchTuning.CooldownTicks;
            var transitionTick = 0u;

            for (var tick = firstPunchTick;
                 tick < thirdPunchTick + M1PunchTuning.WallImpulseTicks;
                 tick++)
            {
                var impulseActive = PunchImpulseActive(tick, firstPunchTick) ||
                                    PunchImpulseActive(tick, secondPunchTick) ||
                                    PunchImpulseActive(tick, thirdPunchTick);
                var intents = impulseActive
                    ? new[] { new WallEffortIntent(wallId, 77, effortPerTick) }
                    : Array.Empty<WallEffortIntent>();
                var result = machine.AdvanceTick(
                    tick,
                    intents,
                    _ => WallTransitionGateDecision.Accept());

                if (tick == thirdPunchTick - 1u)
                {
                    Assert.That(machine.State.IsTransitioning, Is.False,
                        "Deux coups ne doivent jamais suffire à ouvrir le mur.");
                    Assert.That(machine.State.SignedEffort, Is.EqualTo(288));
                }

                if ((result.Events & WallTickEvents.TransitionStarted) == 0)
                    continue;
                transitionTick = tick;
                break;
            }

            Assert.That(M1PunchTuning.ChainedPunchesToOpen, Is.EqualTo(3));
            Assert.That(transitionTick, Is.EqualTo(114u));
            Assert.That(machine.State.IsTransitioning, Is.True);
            Assert.That(machine.State.SignedEffort, Is.Zero);
        }

        [Test]
        public void SnapshotHistory_RejectsReorderingAndProjectsLogicalTicksSeparately()
        {
            var history = new WallSnapshotHistory(3);
            var first = new WallSnapshot(new WallState(10, 0, 1u), 20u);
            var second = new WallSnapshot(new WallState(10, 0, 1u), 21u);
            var third = new WallSnapshot(new WallState(10, 0, 1u), 22u);
            var fourth = new WallSnapshot(new WallState(10, 0, 1u), 23u);

            Assert.That(history.Record(100u, first), Is.EqualTo(WallSnapshotRecordStatus.Added));
            Assert.That(history.PreviewRecord(101u, second), Is.EqualTo(WallSnapshotRecordStatus.Added));
            Assert.That(history.Count, Is.EqualTo(1), "PreviewRecord ne doit jamais muter l'anneau.");
            Assert.That(history.Record(101u, second), Is.EqualTo(WallSnapshotRecordStatus.Added));
            Assert.That(history.Record(101u, second), Is.EqualTo(WallSnapshotRecordStatus.Duplicate));
            Assert.That(
                history.Record(101u, new WallSnapshot(new WallState(10, 0, 2u), 21u)),
                Is.EqualTo(WallSnapshotRecordStatus.Conflict));
            Assert.That(history.Record(99u, first), Is.EqualTo(WallSnapshotRecordStatus.Stale));

            Assert.That(history.TryGetAtOrBefore(100u, out var atHundred), Is.True);
            Assert.That(atHundred.Snapshot, Is.EqualTo(first));
            Assert.That(atHundred.ProjectLogicalTick(103u), Is.EqualTo(23u));

            Assert.That(history.Record(102u, third), Is.EqualTo(WallSnapshotRecordStatus.Added));
            Assert.That(history.Record(103u, fourth), Is.EqualTo(WallSnapshotRecordStatus.Added));
            Assert.That(history.Count, Is.EqualTo(3));
            Assert.That(history.TryGetAtOrBefore(100u, out _), Is.False,
                "L'entrée 100 doit avoir été évincée par l'anneau de capacité trois.");
            Assert.That(history.TryGetAtOrBefore(102u, out var atHundredTwo), Is.True);
            Assert.That(atHundredTwo.Snapshot, Is.EqualTo(third));
            Assert.That(history.TryGetOldest(out var oldest), Is.True);
            Assert.That(oldest.Snapshot, Is.EqualTo(second));
        }

        [Test]
        public void ReceiverPolicy_ExcludesHostAndSizesHistoryBeyondPredictionWindow()
        {
            Assert.That(WallSnapshotReceiverPolicy.ShouldProcess(false), Is.True);
            Assert.That(WallSnapshotReceiverPolicy.ShouldProcess(true), Is.False,
                "Un host ne doit jamais réappliquer sur son mur serveur un RPC bufferisé.");
            Assert.That(
                WallSnapshotReceiverPolicy.CalculateHistoryCapacity(60),
                Is.GreaterThan(60 * 5));
            Assert.That(WallSnapshotReceiverPolicy.ShouldBroadcast(true, 7u, 60), Is.True);
            Assert.That(WallSnapshotReceiverPolicy.ShouldBroadcast(false, 59u, 60), Is.False);
            Assert.That(WallSnapshotReceiverPolicy.ShouldBroadcast(false, 60u, 60), Is.True,
                "Le flux fiable garde un heartbeat par seconde lorsqu'il est stable.");
        }

        [Test]
        public void LiveClock_UsesServerEstimateWithoutEverRewinding()
        {
            var clock = new WallLiveTickClock();
            Assert.That(clock.TryPreviewObservation(100u, 106u, out var candidate), Is.True);
            Assert.That(candidate, Is.EqualTo(106u), "L'ancrage compense le retard du snapshot.");
            clock.CommitObservation(candidate);

            Assert.That(clock.TryPreviewObservation(102u, 104u, out candidate), Is.True);
            Assert.That(candidate, Is.EqualTo(106u), "Une régression FishNet ne rembobine pas le mur.");
            clock.CommitObservation(candidate);
            Assert.That(clock.Tick, Is.EqualTo(106u));

            Assert.That(clock.TryPreviewObservation(109u, 108u, out candidate), Is.True);
            Assert.That(candidate, Is.EqualTo(109u));
        }

        [Test]
        public void SimulationFingerprint_ChangesWithEveryNetworkRelevantSetting()
        {
            var settings = new WallSimulationSettings(120, 4, 2, 0, 30u);
            var baseline = WallSnapshotReceiverPolicy.ComputeSimulationFingerprint(
                settings, 4, 900);
            Assert.That(
                WallSnapshotReceiverPolicy.ComputeSimulationFingerprint(settings, 3, 900),
                Is.Not.EqualTo(baseline));
            Assert.That(
                WallSnapshotReceiverPolicy.ComputeSimulationFingerprint(settings, 4, 901),
                Is.Not.EqualTo(baseline));
            Assert.That(
                WallSnapshotReceiverPolicy.ComputeSimulationFingerprint(
                    new WallSimulationSettings(121, 4, 2, 0, 30u), 4, 900),
                Is.Not.EqualTo(baseline));
        }

        [Test]
        public void SnapshotTimeline_ProjectsAcrossUintWrap()
        {
            var snapshot = new WallSnapshot(new WallState(10, 0), uint.MaxValue - 1u);
            var sample = new WallSnapshotTimelineSample(uint.MaxValue - 1u, snapshot);

            Assert.That(sample.ProjectLogicalTick(1u), Is.EqualTo(1u));
            Assert.That(sample.ProjectLogicalTick(uint.MaxValue - 2u),
                Is.EqualTo(uint.MaxValue - 1u), "Un tick transport plus ancien ne rembobine pas le mur.");
            Assert.That(
                () => sample.ProjectLogicalTick(unchecked(sample.ServerTransportTick + 0x80000000u)),
                Throws.TypeOf<ArgumentException>());
        }

        [Test]
        public void AutomatedPlan_ParsesAndProducesBinaryNetworkVerdict()
        {
            Assert.That(
                M1AutomatedTestPlan.TryParse(
                    new[]
                    {
                        "GAME",
                        "--m1-test-name=transition",
                        "--m1-run-id=run-42",
                        "--m1-evaluate-after-ready-seconds=5",
                        "--m1-auto-quit-seconds=6",
                        "--m1-expect-wall-state=1",
                        "--m1-expect-players=2",
                        "--m1-expect-completed-min=1",
                        "--m1-expect-target-snapshots-min=1"
                    },
                    out var plan,
                    out var parseError),
                Is.True,
                parseError);
            Assert.That(plan.Enabled, Is.True);

            Assert.That(plan.RunId, Is.EqualTo("run-42"));
            Assert.That(plan.EvaluateAfterReadySeconds, Is.EqualTo(5d));
            var healthy = new M1AutomatedTestObservation(
                true, 2, 0, true, 1, 31u, 0, false,
                1u, 0u, 0u, 30u, 1u, 29u, 0u, 0u);
            Assert.That(plan.IsReadyToArm(healthy), Is.True);
            Assert.That(plan.Evaluate(healthy, out var reason), Is.True, reason);

            var incompatible = new M1AutomatedTestObservation(
                true, 3, 0, true, 0, 31u, 4, true,
                0u, 0u, 0u, 30u, 1u, 29u, 1u, 0u);
            Assert.That(plan.IsReadyToArm(incompatible), Is.False,
                "L'échéance ne doit pas démarrer avant le roster exact attendu.");
            Assert.That(plan.Evaluate(incompatible, out reason), Is.False);
            Assert.That(reason, Does.Contain("players=3!=2"));
            Assert.That(reason, Does.Contain("wall_state=0!=1"));
            Assert.That(reason, Does.Contain("signedEffort=4"));
            Assert.That(reason, Does.Contain("wall_transitioning"));
            Assert.That(reason, Does.Contain("invalidSnapshots=1"));
        }

        private static TopologyRuntimeMap LoadMap()
        {
            Assert.That(
                TopologyRuntimeMap.TryCreateVerified(
                    File.ReadAllText(GrayboxPath), out var map, out var issues),
                Is.True,
                issues.Count == 0 ? string.Empty : issues[0].Code);
            return map;
        }

        private static bool PunchImpulseActive(uint tick, uint startTick) =>
            tick >= startTick && tick - startTick < M1PunchTuning.WallImpulseTicks;
    }
}
