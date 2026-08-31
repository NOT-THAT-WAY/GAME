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
        private const int PlayerRadiusMm = 451;
        private const int ReachMm = 900;
        private const int MinimumLeverage = 300;

        [Test]
        public void ContactRule_DerivesOppositeDirectionsAndRangeFromCanonicalGeometry()
        {
            var map = LoadMap();

            var east = Evaluate(map, 0, 1375, -1375);
            var west = Evaluate(map, 0, -1375, -1375);
            var tooFar = Evaluate(map, 0, 5000, -1375);
            var onThePlane = Evaluate(map, 0, 0, -1375);

            Assert.That(east.Allowed, Is.True);
            Assert.That(west.Allowed, Is.True);
            Assert.That(
                east.Direction,
                Is.EqualTo(-west.Direction),
                "Les deux faces d'un battant imposent deux sens opposés.");
            Assert.That(east.LeveragePermille, Is.EqualTo(west.LeveragePermille));
            Assert.That(tooFar.Allowed, Is.False);
            Assert.That(tooFar.Rejection, Is.EqualTo(M1WallInteractionRejection.OutOfReach));
            Assert.That(onThePlane.Rejection,
                Is.EqualTo(M1WallInteractionRejection.CenterOnWallPlane));

            var staticWall = M1WallInteractionRules.Evaluate(
                map, 1000, 0, -2750, -1375, PlayerRadiusMm, ReachMm, MinimumLeverage);
            Assert.That(staticWall.Rejection, Is.EqualTo(M1WallInteractionRejection.WallStatic));
        }

        /// <summary>
        /// Le sens ne dépend plus d'un couple de poses : à n'importe quel angle du
        /// tour, changer de face suffit à inverser la rotation. C'est ce qui rend
        /// la contre-poussée et les 360 degrés atteignables sans état de destination.
        /// </summary>
        [Test]
        public void ContactRule_ReversesWithTheFaceAtEveryAngleOfTheTurn()
        {
            var map = LoadMap();
            for (var angle = 0; angle < 360_000; angle += 7_500)
            {
                var positive = ContactPoint(angle, 1800, 700);
                var negative = ContactPoint(angle, 1800, -700);
                var onSide = Evaluate(map, angle, positive.x, positive.z);
                var onOtherSide = Evaluate(map, angle, negative.x, negative.z);

                Assert.That(onSide.Allowed, Is.True, $"angle={angle}");
                Assert.That(onOtherSide.Allowed, Is.True, $"angle={angle}");
                Assert.That(onSide.Direction, Is.EqualTo(-1), $"angle={angle}");
                Assert.That(onOtherSide.Direction, Is.EqualTo(1), $"angle={angle}");
                Assert.That(
                    onSide.LeveragePermille,
                    Is.EqualTo(onOtherSide.LeveragePermille).Within(1),
                    $"angle={angle}");
            }
        }

        [Test]
        public void Leverage_GoesFromTheHingeMinimumToFullPowerAtTheTip()
        {
            var map = LoadMap();

            var hinge = Evaluate(map, 0, 400, 0);
            var middle = Evaluate(map, 0, 400, -1375);
            var tip = Evaluate(map, 0, 400, -2750);

            Assert.That(hinge.Allowed, Is.True);
            Assert.That(hinge.ContactPermille, Is.Zero);
            Assert.That(
                hinge.LeveragePermille,
                Is.EqualTo(MinimumLeverage),
                "Au gond, il reste 30 % de puissance : lent, jamais nul.");
            Assert.That(middle.ContactPermille, Is.EqualTo(500));
            Assert.That(middle.LeveragePermille, Is.EqualTo(650));
            Assert.That(tip.ContactPermille, Is.EqualTo(1000));
            Assert.That(
                tip.LeveragePermille,
                Is.EqualTo(1000),
                "Au bout du battant, la poussée vaut 100 %.");

            // Le prorata est monotone entre les deux bornes.
            var previous = -1;
            for (var alongMm = 0; alongMm <= 2750; alongMm += 250)
            {
                var decision = Evaluate(map, 0, 400, -alongMm);
                Assert.That(decision.Allowed, Is.True, $"along={alongMm}");
                Assert.That(decision.LeveragePermille, Is.GreaterThanOrEqualTo(previous));
                previous = decision.LeveragePermille;
            }
        }

        /// <summary>
        /// Deux joueurs sur les deux faces, à la même distance du gond, annulent
        /// exactement la rotation ; celui qui s'écarte du gond reprend la main.
        /// </summary>
        [Test]
        public void CounterPush_CancelsAtEqualLeverageAndTiltsWithTheLongerArm()
        {
            var map = LoadMap();
            var settings = new WallSimulationSettings(900, MinimumLeverage, 180u);
            var machine = new WallRotationMachine(settings, 10, 0, 0u);

            var east = Evaluate(map, 0, 1375, -1375);
            var west = Evaluate(map, 0, -1375, -1375);
            var balanced = machine.AdvanceTick(1u, new[]
            {
                new WallTorqueIntent(10, 1, east.Direction, east.LeveragePermille),
                new WallTorqueIntent(10, 2, west.Direction, west.LeveragePermille)
            });
            Assert.That(balanced.Current.AngleMilliDegrees, Is.Zero);
            Assert.That(balanced.Events & WallTickEvents.TorqueOpposed,
                Is.EqualTo(WallTickEvents.TorqueOpposed));

            var eastAtTheTip = Evaluate(map, 0, 400, -2600);
            var tilted = machine.AdvanceTick(2u, new[]
            {
                new WallTorqueIntent(10, 1, eastAtTheTip.Direction, eastAtTheTip.LeveragePermille),
                new WallTorqueIntent(10, 2, west.Direction, west.LeveragePermille)
            });
            Assert.That(eastAtTheTip.Direction, Is.EqualTo(east.Direction));
            Assert.That(
                tilted.NetLeveragePermille,
                Is.EqualTo(east.Direction * (eastAtTheTip.LeveragePermille - west.LeveragePermille)));
            Assert.That(tilted.Current.IsRotating, Is.True);
        }

        [Test]
        public void PunchImpulse_TurnsTheWallByExactlyItsTorqueWindow()
        {
            const int wallId = 10;
            const int leverage = 650;
            var settings = new WallSimulationSettings(900, MinimumLeverage, 180u);
            var machine = new WallRotationMachine(settings, wallId, 0, 0u);
            var velocity = settings.VelocityFromNetLeverage(leverage);

            for (var tick = 1u; tick <= M1PunchTuning.WallImpulseTicks; tick++)
            {
                machine.AdvanceTick(tick, new[] { new WallTorqueIntent(wallId, 77, 1, leverage) });
            }
            var afterPunch = machine.State.AngleMilliDegrees;
            Assert.That(afterPunch, Is.EqualTo((int)M1PunchTuning.WallImpulseTicks * velocity));

            var settled = machine.AdvanceTick(
                M1PunchTuning.WallImpulseTicks + 1u,
                Array.Empty<WallTorqueIntent>());
            Assert.That(settled.Current.AngleMilliDegrees, Is.EqualTo(afterPunch));
            Assert.That(settled.Current.IsRotating, Is.False,
                "Un coup ne lance pas une bascule : il verse un couple pendant sa fenêtre.");
        }

        [Test]
        public void SnapshotHistory_RejectsReorderingAndProjectsLogicalTicksSeparately()
        {
            var history = new WallSnapshotHistory(3);
            var first = new WallSnapshot(new WallState(10, 0, 0, 20u, 1u));
            var second = new WallSnapshot(new WallState(10, 0, 0, 21u, 1u));
            var third = new WallSnapshot(new WallState(10, 0, 0, 22u, 1u));
            var fourth = new WallSnapshot(new WallState(10, 0, 0, 23u, 1u));

            Assert.That(history.Record(100u, first), Is.EqualTo(WallSnapshotRecordStatus.Added));
            Assert.That(history.PreviewRecord(101u, second), Is.EqualTo(WallSnapshotRecordStatus.Added));
            Assert.That(history.Count, Is.EqualTo(1), "PreviewRecord ne doit jamais muter l'anneau.");
            Assert.That(history.Record(101u, second), Is.EqualTo(WallSnapshotRecordStatus.Added));
            Assert.That(history.Record(101u, second), Is.EqualTo(WallSnapshotRecordStatus.Duplicate));
            Assert.That(
                history.Record(101u, new WallSnapshot(new WallState(10, 0, 0, 21u, 2u))),
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
        public void ReceiverPolicy_ExcludesHostAndOnlyBroadcastsSegmentChanges()
        {
            Assert.That(WallSnapshotReceiverPolicy.ShouldProcess(false), Is.True);
            Assert.That(WallSnapshotReceiverPolicy.ShouldProcess(true), Is.False,
                "Un host ne doit jamais réappliquer sur son mur serveur un RPC bufferisé.");
            Assert.That(
                WallSnapshotReceiverPolicy.CalculateHistoryCapacity(60),
                Is.GreaterThan(60 * 5));
            Assert.That(WallSnapshotReceiverPolicy.ShouldBroadcast(true, 7u, 60), Is.True);
            Assert.That(
                WallSnapshotReceiverPolicy.ShouldBroadcast(false, 59u, 60),
                Is.False,
                "Un battant qui tourne à vitesse constante ne se synchronise pas par image.");
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
            var settings = new WallSimulationSettings(900, 300, 180u);
            var baseline = WallSnapshotReceiverPolicy.ComputeSimulationFingerprint(settings, 900);
            Assert.That(
                WallSnapshotReceiverPolicy.ComputeSimulationFingerprint(settings, 901),
                Is.Not.EqualTo(baseline));
            Assert.That(
                WallSnapshotReceiverPolicy.ComputeSimulationFingerprint(
                    new WallSimulationSettings(901, 300, 180u), 900),
                Is.Not.EqualTo(baseline));
            Assert.That(
                WallSnapshotReceiverPolicy.ComputeSimulationFingerprint(
                    new WallSimulationSettings(900, 301, 180u), 900),
                Is.Not.EqualTo(baseline));
            Assert.That(
                WallSnapshotReceiverPolicy.ComputeSimulationFingerprint(
                    new WallSimulationSettings(900, 300, 181u), 900),
                Is.Not.EqualTo(baseline));
        }

        [Test]
        public void SnapshotTimeline_ProjectsAcrossUintWrap()
        {
            var snapshot = new WallSnapshot(new WallState(10, 0, uint.MaxValue - 1u));
            var sample = new WallSnapshotTimelineSample(uint.MaxValue - 1u, snapshot);

            Assert.That(sample.ProjectLogicalTick(1u), Is.EqualTo(1u));
            Assert.That(sample.ProjectLogicalTick(uint.MaxValue - 2u),
                Is.EqualTo(uint.MaxValue - 1u), "Un tick transport plus ancien ne rembobine pas le mur.");
            Assert.That(
                () => sample.ProjectLogicalTick(unchecked(sample.ServerTransportTick + 0x80000000u)),
                Throws.TypeOf<ArgumentException>());
        }

        [Test]
        public void AutomatedRun_IsRecognisedSoTheBenchCanEmptyItself()
        {
            // Un plan armé : le bot d'entraînement doit se taire, sinon il
            // frappe, pousse les murs et relance des manches pendant la mesure.
            Assert.That(
                M1AutomatedTestPlan.IsAutomatedRun(new[]
                {
                    "GAME",
                    "--m1-test-name=occupancy-host",
                    "--m1-auto-quit-seconds=19"
                }),
                Is.True);

            // Banc humain et captures de contrôle : aucun plan, donc bot présent.
            Assert.That(
                M1AutomatedTestPlan.IsAutomatedRun(new[]
                {
                    "GAME",
                    "--game-role=host",
                    "--game-port=7770"
                }),
                Is.False);

            // Un nom de test sans durée d'arrêt ne suffit pas : le plan n'est
            // pas armé, rien n'est mesuré, le banc reste complet.
            Assert.That(
                M1AutomatedTestPlan.IsAutomatedRun(new[] { "GAME", "--m1-test-name=rotation" }),
                Is.False);

            // Un plan illisible est refusé plus tard par les diagnostics, qui
            // font quitter le processus ; ici il ne doit pas vider le banc.
            Assert.That(
                M1AutomatedTestPlan.IsAutomatedRun(new[]
                {
                    "GAME",
                    "--m1-auto-quit-seconds=pas-un-nombre"
                }),
                Is.False);

            Assert.That(M1AutomatedTestPlan.IsAutomatedRun(null), Is.False);
        }

        [Test]
        public void AutomatedPlan_ParsesAndProducesBinaryNetworkVerdict()
        {
            Assert.That(
                M1AutomatedTestPlan.TryParse(
                    new[]
                    {
                        "GAME",
                        "--m1-test-name=rotation",
                        "--m1-run-id=run-42",
                        "--m1-evaluate-after-ready-seconds=5",
                        "--m1-auto-quit-seconds=6",
                        "--m1-expect-players=2",
                        "--m1-expect-rotation-min-mdeg=30000",
                        "--m1-expect-swept-pushes-min=1",
                        "--m1-expect-target-snapshots-min=1"
                    },
                    out var plan,
                    out var parseError),
                Is.True,
                parseError);
            Assert.That(plan.Enabled, Is.True);
            Assert.That(plan.RunId, Is.EqualTo("run-42"));
            Assert.That(plan.EvaluateAfterReadySeconds, Is.EqualTo(5d));
            Assert.That(plan.MinimumRotationMilliDegrees, Is.EqualTo(30000L));

            var healthy = new M1AutomatedTestObservation(
                true, 2, 0, true, 44000, 3u, 0, -45000L,
                0u, 0u, 0u, 12u, 30u, 1u, 29u, 0u, 0u);
            Assert.That(plan.IsReadyToArm(healthy), Is.True);
            Assert.That(
                plan.Evaluate(healthy, out var reason),
                Is.True,
                $"{reason} — une rotation négative compte par sa valeur absolue.");

            var broken = new M1AutomatedTestObservation(
                true, 3, 0, true, 900, 1u, 900, 900L,
                0u, 0u, 0u, 0u, 30u, 1u, 29u, 1u, 0u);
            Assert.That(plan.IsReadyToArm(broken), Is.False,
                "L'échéance ne doit pas démarrer avant le roster exact attendu.");
            Assert.That(plan.Evaluate(broken, out reason), Is.False);
            Assert.That(reason, Does.Contain("players=3!=2"));
            Assert.That(reason, Does.Contain("rotation=900<30000"));
            Assert.That(reason, Does.Contain("sweptPushes=0<1"));
            Assert.That(reason, Does.Contain("invalidSnapshots=1"));

            Assert.That(
                M1AutomatedTestPlan.TryParse(
                    new[]
                    {
                        "GAME",
                        "--m1-auto-quit-seconds=6",
                        "--m1-expect-rotation-max-mdeg=5000"
                    },
                    out var still,
                    out parseError),
                Is.True,
                parseError);
            Assert.That(
                still.Evaluate(
                    new M1AutomatedTestObservation(
                        true, 2, 0, true, 0, 0u, 0, 0L,
                        0u, 0u, 120u, 0u, 5u, 1u, 4u, 0u, 0u),
                    out reason),
                Is.True,
                reason);
            Assert.That(
                still.Evaluate(
                    new M1AutomatedTestObservation(
                        true, 2, 0, true, 9000, 4u, 0, 9000L,
                        0u, 0u, 0u, 0u, 5u, 1u, 4u, 0u, 0u),
                    out reason),
                Is.False);
            Assert.That(reason, Does.Contain("rotation=9000>5000"));
        }

        /// <summary>
        /// Point situé à une abscisse donnée le long du battant et à un décalage
        /// latéral signé, calculé avec la même trigonométrie entière que la règle.
        /// </summary>
        private static (int x, int z) ContactPoint(int angleMilliDegrees, int alongMm, int lateralMm)
        {
            FixedTrigonometry.SinCos(angleMilliDegrees, out var sin, out var cos);
            // Direction du battant à l'angle zéro : le sud, soit (0, -1).
            var unitX = -sin;
            var unitZ = -cos;
            // Normale de signe positif au sens de rotation : (unitZ, -unitX).
            var x = (alongMm * (long)unitX + lateralMm * (long)unitZ) / FixedTrigonometry.Scale;
            var z = (alongMm * (long)unitZ - lateralMm * (long)unitX) / FixedTrigonometry.Scale;
            return ((int)x, (int)z);
        }

        private static M1WallInteractionDecision Evaluate(
            TopologyRuntimeMap map,
            int angleMilliDegrees,
            int xMm,
            int zMm) =>
            M1WallInteractionRules.Evaluate(
                map,
                10,
                angleMilliDegrees,
                xMm,
                zMm,
                PlayerRadiusMm,
                ReachMm,
                MinimumLeverage);

        private static TopologyRuntimeMap LoadMap()
        {
            Assert.That(
                TopologyRuntimeMap.TryCreateVerified(
                    File.ReadAllText(GrayboxPath), out var map, out var issues),
                Is.True,
                issues.Count == 0 ? string.Empty : issues[0].Code);
            return map;
        }
    }
}
