using System;
using System.Collections.Generic;
using System.Linq;
using NotThatWay.Game.Simulation;
using NUnit.Framework;

namespace NotThatWay.Game.Tests.EditMode
{
    public sealed class WallStateMachineTests
    {
        private const int WallId = 7001;
        private const int NegativeState = 17;
        private const int PositiveState = 903;

        private static readonly WallSimulationSettings Settings = new(
            effortThreshold: 100,
            maximumEffortPerSourcePerTick: 60,
            effortDecayPerTick: 5,
            rejectedEffortRetention: 0,
            transitionDurationTicks: 3u);

        [Test]
        public void IntentAggregation_IsIndependentOfArrivalOrderAndClientIdentity()
        {
            var first = CreateMachine(initialTick: 9u);
            var second = CreateMachine(initialTick: 9u);
            var intents = new[]
            {
                new WallEffortIntent(WallId, 91, 80),
                new WallEffortIntent(WallId, 12, 30),
                new WallEffortIntent(WallId, 91, -20),
                new WallEffortIntent(WallId, 42, -30),
                new WallEffortIntent(9999, 12, int.MaxValue)
            };

            var firstResult = first.AdvanceTick(10u, intents, Allow);
            var secondResult = second.AdvanceTick(10u, intents.Reverse().ToArray(), Allow);

            Assert.That(firstResult.AggregatedEffort, Is.EqualTo(60));
            Assert.That(secondResult.AggregatedEffort, Is.EqualTo(60));
            Assert.That(second.State, Is.EqualTo(first.State));
            Assert.That(first.State.SignedEffort, Is.EqualTo(60));
            Assert.That(first.State.Revision, Is.EqualTo(1u));

            var equalOpposition = new[]
            {
                new WallEffortIntent(WallId, 1, 60),
                new WallEffortIntent(WallId, 2, -60)
            };
            firstResult = first.AdvanceTick(11u, equalOpposition, Allow);
            secondResult = second.AdvanceTick(11u, equalOpposition.Reverse().ToArray(), Allow);

            Assert.That(firstResult.AggregatedEffort, Is.Zero);
            Assert.That(first.State.SignedEffort, Is.EqualTo(55),
                "Une égalité n'ajoute aucun effort; le decay paramétré reste applicable.");
            Assert.That(second.State, Is.EqualTo(first.State));
        }

        [Test]
        public void PerSourceEffortCap_IsAppliedSymmetricallyAfterAggregation()
        {
            var towardPositive = CreateMachine(initialTick: 0u);
            var positive = towardPositive.AdvanceTick(
                1u,
                new[]
                {
                    new WallEffortIntent(WallId, 1, 100),
                    new WallEffortIntent(WallId, 1, 100),
                    new WallEffortIntent(WallId, 2, -10)
                },
                Allow);
            Assert.That(positive.AggregatedEffort, Is.EqualTo(50));
            Assert.That(towardPositive.State.SignedEffort, Is.EqualTo(50));

            var towardNegative = new WallStateMachine(
                Settings,
                WallId,
                NegativeState,
                PositiveState,
                PositiveState,
                initialTick: 0u);
            var negative = towardNegative.AdvanceTick(
                1u,
                new[]
                {
                    new WallEffortIntent(WallId, 1, -100),
                    new WallEffortIntent(WallId, 1, -100),
                    new WallEffortIntent(WallId, 2, 10)
                },
                Allow);
            Assert.That(negative.AggregatedEffort, Is.EqualTo(-50));
            Assert.That(towardNegative.State.SignedEffort, Is.EqualTo(-50));

            towardNegative.AdvanceTick(
                2u,
                Array.Empty<WallEffortIntent>(),
                Allow);
            Assert.That(towardNegative.State.SignedEffort, Is.EqualTo(-45));
        }

        [Test]
        public void Transition_UsesIntegerTicksCompletesAndCanReverse()
        {
            var machine = CreateMachine(initialTick: 20u);
            machine.AdvanceTick(21u, Push(60), Allow);
            var started = machine.AdvanceTick(22u, Push(40), Allow);

            Assert.That((started.Events & WallTickEvents.TransitionStarted) != 0, Is.True);
            Assert.That(machine.State.StateId, Is.EqualTo(NegativeState));
            Assert.That(machine.State.IsTransitioning, Is.True);
            Assert.That(machine.State.SignedEffort, Is.Zero);
            Assert.That(machine.State.ActiveTransition.Value.StartTick, Is.EqualTo(22u));
            var startPose = machine.State.SamplePose(22u);
            Assert.That(startPose.FromStateId, Is.EqualTo(NegativeState));
            Assert.That(startPose.ToStateId, Is.EqualTo(PositiveState));
            Assert.That(startPose.ElapsedTicks, Is.Zero);
            Assert.That(startPose.DurationTicks, Is.EqualTo(3u));
            Assert.That(startPose.ProgressQ16, Is.Zero);
            Assert.That(startPose.IsTransitioning, Is.True);

            var ignored = machine.AdvanceTick(23u, Push(int.MaxValue), Allow);
            Assert.That(ignored.Changed, Is.False);
            var middlePose = machine.State.SamplePose(23u);
            Assert.That(middlePose.FromStateId, Is.EqualTo(NegativeState));
            Assert.That(middlePose.ToStateId, Is.EqualTo(PositiveState));
            Assert.That(middlePose.ElapsedTicks, Is.EqualTo(1u));
            Assert.That(middlePose.DurationTicks, Is.EqualTo(3u));
            Assert.That(middlePose.ProgressQ16, Is.EqualTo(21845));
            Assert.That(middlePose.IsTransitioning, Is.True);
            machine.AdvanceTick(24u, Array.Empty<WallEffortIntent>(), Allow);
            Assert.That(machine.State.SamplePose(24u).ProgressQ16, Is.EqualTo(43690));

            var logicalEndPose = machine.State.SamplePose(25u);
            Assert.That(logicalEndPose.FromStateId, Is.EqualTo(NegativeState));
            Assert.That(logicalEndPose.ToStateId, Is.EqualTo(PositiveState));
            Assert.That(logicalEndPose.ElapsedTicks, Is.EqualTo(3u));
            Assert.That(logicalEndPose.DurationTicks, Is.EqualTo(3u));
            Assert.That(logicalEndPose.ProgressQ16, Is.EqualTo(ushort.MaxValue));
            Assert.That(logicalEndPose.IsTransitioning, Is.False);

            var completed = machine.AdvanceTick(
                25u,
                new[]
                {
                    new WallEffortIntent(WallId, 1, -60),
                    new WallEffortIntent(WallId, 2, -40)
                },
                _ => throw new AssertionException("La gate ne doit pas être appelée au tick de complétion."));
            Assert.That((completed.Events & WallTickEvents.TransitionCompleted) != 0, Is.True);
            Assert.That((completed.Events & WallTickEvents.TransitionStarted) == 0, Is.True);
            Assert.That(completed.AggregatedEffort, Is.EqualTo(-100));
            Assert.That(machine.State.StateId, Is.EqualTo(PositiveState));
            Assert.That(machine.State.IsTransitioning, Is.False);
            Assert.That(machine.State.SignedEffort, Is.Zero);
            var stablePose = machine.State.SamplePose(25u);
            Assert.That(stablePose.FromStateId, Is.EqualTo(PositiveState));
            Assert.That(stablePose.ToStateId, Is.EqualTo(PositiveState));
            Assert.That(stablePose.ElapsedTicks, Is.Zero);
            Assert.That(stablePose.DurationTicks, Is.Zero);
            Assert.That(stablePose.ProgressQ16, Is.EqualTo(ushort.MaxValue));
            Assert.That(stablePose.IsTransitioning, Is.False);

            var reverseStarted = machine.AdvanceTick(
                26u,
                new[]
                {
                    new WallEffortIntent(WallId, 1, -60),
                    new WallEffortIntent(WallId, 2, -40)
                },
                Allow);
            Assert.That((reverseStarted.Events & WallTickEvents.TransitionStarted) != 0, Is.True);
            Assert.That(machine.State.ActiveTransition.Value.ToStateId, Is.EqualTo(NegativeState));

            machine.AdvanceTick(27u, Array.Empty<WallEffortIntent>(), Allow);
            machine.AdvanceTick(28u, Array.Empty<WallEffortIntent>(), Allow);
            machine.AdvanceTick(29u, Array.Empty<WallEffortIntent>(), Allow);
            Assert.That(machine.State.StateId, Is.EqualTo(NegativeState));
            Assert.That(machine.State.Revision, Is.EqualTo(5u));
        }

        [Test]
        public void RejectedTransition_IsAtomicAndCarriesStableReason()
        {
            var machine = CreateMachine(initialTick: 0u);
            var gateCalls = 0;

            var result = machine.AdvanceTick(
                1u,
                new[]
                {
                    new WallEffortIntent(WallId, 1, 60),
                    new WallEffortIntent(WallId, 2, 40)
                },
                request =>
                {
                    gateCalls++;
                    Assert.That(request.WallId, Is.EqualTo(WallId));
                    Assert.That(request.FromStateId, Is.EqualTo(NegativeState));
                    Assert.That(request.ToStateId, Is.EqualTo(PositiveState));
                    Assert.That(request.StartTick, Is.EqualTo(1u));
                    Assert.That(request.DurationTicks, Is.EqualTo(Settings.TransitionDurationTicks));
                    Assert.That(request.NextRevision, Is.EqualTo(1u));
                    return WallTransitionGateDecision.Reject("player_in_swept_arc");
                });

            Assert.That(gateCalls, Is.EqualTo(1));
            Assert.That((result.Events & WallTickEvents.TransitionRejected) != 0, Is.True);
            Assert.That(result.RejectionCode, Is.EqualTo("player_in_swept_arc"));
            Assert.That(machine.State.StateId, Is.EqualTo(NegativeState));
            Assert.That(machine.State.IsTransitioning, Is.False);
            Assert.That(machine.State.SignedEffort, Is.Zero);
            Assert.That(machine.State.Revision, Is.EqualTo(1u));
        }

        [Test]
        public void RejectedEffortRetention_IsConfigurableInBothDirections()
        {
            var retentionSettings = new WallSimulationSettings(100, 100, 0, 25, 3u);
            var positive = new WallStateMachine(
                retentionSettings, WallId, NegativeState, PositiveState, NegativeState, 0u);
            var negative = new WallStateMachine(
                retentionSettings, WallId, NegativeState, PositiveState, PositiveState, 0u);

            positive.AdvanceTick(
                1u,
                new[] { new WallEffortIntent(WallId, 1, 100) },
                _ => WallTransitionGateDecision.Reject("occupied"));
            negative.AdvanceTick(
                1u,
                new[] { new WallEffortIntent(WallId, 1, -100) },
                _ => WallTransitionGateDecision.Reject("occupied"));

            Assert.That(positive.State.StateId, Is.EqualTo(NegativeState));
            Assert.That(positive.State.SignedEffort, Is.EqualTo(25));
            Assert.That(negative.State.StateId, Is.EqualTo(PositiveState));
            Assert.That(negative.State.SignedEffort, Is.EqualTo(-25));
        }

        [Test]
        public void Gate_IsOnlyCalledAtThresholdAndARejectionRequiresACode()
        {
            var machine = CreateMachine(initialTick: 0u);
            var calls = 0;
            machine.AdvanceTick(
                1u,
                Push(50),
                _ =>
                {
                    calls++;
                    return WallTransitionGateDecision.Accept();
                });
            Assert.That(calls, Is.Zero);

            machine.AdvanceTick(
                2u,
                Push(50),
                _ =>
                {
                    calls++;
                    return WallTransitionGateDecision.Accept();
                });
            Assert.That(calls, Is.EqualTo(1));
            machine.AdvanceTick(
                3u,
                Push(100),
                _ =>
                {
                    calls++;
                    return WallTransitionGateDecision.Reject("must_not_be_called");
                });
            Assert.That(calls, Is.EqualTo(1));

            var invalidGate = CreateMachine(initialTick: 0u);
            Assert.That(
                () => invalidGate.AdvanceTick(
                    1u,
                    new[]
                    {
                        new WallEffortIntent(WallId, 1, 60),
                        new WallEffortIntent(WallId, 2, 40)
                    },
                    _ => default),
                Throws.InvalidOperationException.With.Message.Contains("code stable"));
            Assert.That(invalidGate.State.Revision, Is.Zero);
            Assert.That(invalidGate.State.SignedEffort, Is.Zero);
            Assert.That(invalidGate.LastProcessedTick, Is.Zero);
        }

        [Test]
        public void Gate_CannotReenterOrApplySnapshotAndFailureRemainsAtomic()
        {
            var machine = CreateMachine(initialTick: 0u);
            var threshold = new[]
            {
                new WallEffortIntent(WallId, 1, 60),
                new WallEffortIntent(WallId, 2, 40)
            };

            Assert.That(
                () => machine.AdvanceTick(
                    1u,
                    threshold,
                    _ =>
                    {
                        machine.AdvanceTick(
                            1u,
                            Array.Empty<WallEffortIntent>(),
                            Allow);
                        return WallTransitionGateDecision.Accept();
                    }),
                Throws.InvalidOperationException.With.Message.Contains("réentrant"));
            Assert.That(machine.State, Is.EqualTo(CreateMachine(initialTick: 0u).State));
            Assert.That(machine.LastProcessedTick, Is.Zero);

            Assert.That(
                () => machine.AdvanceTick(
                    1u,
                    threshold,
                    _ =>
                    {
                        machine.TryApplySnapshot(machine.CaptureSnapshot());
                        return WallTransitionGateDecision.Accept();
                    }),
                Throws.InvalidOperationException.With.Message.Contains("snapshot"));
            Assert.That(machine.State.Revision, Is.Zero);
            Assert.That(machine.LastProcessedTick, Is.Zero);

            var recovered = machine.AdvanceTick(1u, threshold, Allow);
            Assert.That(recovered.Events & WallTickEvents.TransitionStarted, Is.Not.Zero);
            Assert.That(machine.LastProcessedTick, Is.EqualTo(1u));
        }

        [Test]
        public void Snapshot_RoundTripsAndRestoresALateJoinDuringUintWrap()
        {
            var machine = CreateMachine(initialTick: uint.MaxValue - 2u);
            machine.AdvanceTick(uint.MaxValue - 1u, Push(60), Allow);
            machine.AdvanceTick(uint.MaxValue, Push(40), Allow);
            machine.AdvanceTick(0u, Array.Empty<WallEffortIntent>(), Allow);

            var snapshot = machine.CaptureSnapshot();
            var bytes = snapshot.ToBytes();
            Assert.That(bytes, Has.Length.EqualTo(46));
            Assert.That(
                BitConverter.ToString(bytes).Replace("-", string.Empty).ToLowerInvariant(),
                Is.EqualTo(
                    "01591b00001100000002000000000000000000000001" +
                    "591b00001100000087030000ffffffff0300000002000000"),
                "Golden vector v1 de transition active.");
            Assert.That(WallSnapshot.TryFromBytes(bytes, out var decoded, out var code), Is.True, code);
            Assert.That(code, Is.EqualTo(WallSnapshotDecodeCodes.None));
            Assert.That(decoded, Is.EqualTo(snapshot));
            Assert.That(decoded.ToBytes(), Is.EqualTo(bytes));

            var lateJoin = WallStateMachine.FromSnapshot(
                Settings, NegativeState, PositiveState, decoded);
            Assert.That(lateJoin.State, Is.EqualTo(machine.State));
            Assert.That(lateJoin.State.SamplePose(0u), Is.EqualTo(machine.State.SamplePose(0u)));

            machine.AdvanceTick(1u, Array.Empty<WallEffortIntent>(), Allow);
            lateJoin.AdvanceTick(1u, Array.Empty<WallEffortIntent>(), Allow);
            machine.AdvanceTick(2u, Array.Empty<WallEffortIntent>(), Allow);
            lateJoin.AdvanceTick(2u, Array.Empty<WallEffortIntent>(), Allow);
            Assert.That(lateJoin.CaptureSnapshot(), Is.EqualTo(machine.CaptureSnapshot()));
            Assert.That(machine.State.StateId, Is.EqualTo(PositiveState));
        }

        [Test]
        public void Snapshot_RejectsStaleAndConflictingRevisions()
        {
            var machine = CreateMachine(initialTick: 40u);
            Assert.That(
                machine.TryApplySnapshot(default),
                Is.EqualTo(WallSnapshotApplyStatus.Invalid));
            machine.AdvanceTick(41u, Push(60), Allow);
            machine.AdvanceTick(42u, Push(40), Allow);
            var activeSnapshot = machine.CaptureSnapshot();
            machine.AdvanceTick(43u, Array.Empty<WallEffortIntent>(), Allow);
            machine.AdvanceTick(44u, Array.Empty<WallEffortIntent>(), Allow);
            machine.AdvanceTick(45u, Array.Empty<WallEffortIntent>(), Allow);

            Assert.That(
                machine.TryApplySnapshot(activeSnapshot),
                Is.EqualTo(WallSnapshotApplyStatus.Stale));
            Assert.That(
                machine.TryApplySnapshot(machine.CaptureSnapshot()),
                Is.EqualTo(WallSnapshotApplyStatus.Duplicate));

            var conflict = new WallSnapshot(
                new WallState(WallId, NegativeState, machine.State.Revision),
                machine.LastProcessedTick);
            Assert.That(
                machine.TryApplySnapshot(conflict),
                Is.EqualTo(WallSnapshotApplyStatus.RevisionConflict));
            Assert.That(machine.State.StateId, Is.EqualTo(PositiveState));
        }

        [Test]
        public void SnapshotApply_HandlesNewerRevisionAndEqualRevisionTicksIncludingWrap()
        {
            var authorityWithNewRevision = CreateMachine(initialTick: 0u);
            var receiverWithOldRevision = CreateMachine(initialTick: 0u);
            authorityWithNewRevision.AdvanceTick(1u, Push(50), Allow);
            Assert.That(
                receiverWithOldRevision.TryApplySnapshot(authorityWithNewRevision.CaptureSnapshot()),
                Is.EqualTo(WallSnapshotApplyStatus.Applied));
            Assert.That(receiverWithOldRevision.State, Is.EqualTo(authorityWithNewRevision.State));
            Assert.That(receiverWithOldRevision.LastProcessedTick, Is.EqualTo(1u));
            authorityWithNewRevision.AdvanceTick(2u, Array.Empty<WallEffortIntent>(), Allow);
            receiverWithOldRevision.AdvanceTick(2u, Array.Empty<WallEffortIntent>(), Allow);
            Assert.That(receiverWithOldRevision.State, Is.EqualTo(authorityWithNewRevision.State));

            var stable = CreateMachine(initialTick: uint.MaxValue);
            var newerStable = new WallSnapshot(stable.State, 0u);
            Assert.That(
                stable.TryApplySnapshot(newerStable),
                Is.EqualTo(WallSnapshotApplyStatus.Applied));
            Assert.That(stable.LastProcessedTick, Is.EqualTo(0u));
            Assert.That(
                stable.TryApplySnapshot(new WallSnapshot(stable.State, uint.MaxValue)),
                Is.EqualTo(WallSnapshotApplyStatus.Stale));
            Assert.That(
                stable.TryApplySnapshot(newerStable),
                Is.EqualTo(WallSnapshotApplyStatus.Duplicate));
            stable.AdvanceTick(1u, Array.Empty<WallEffortIntent>(), Allow);

            var authority = CreateMachine(initialTick: 9u);
            authority.AdvanceTick(10u, Push(60), Allow);
            authority.AdvanceTick(11u, Push(40), Allow);
            var receiver = WallStateMachine.FromSnapshot(
                Settings, NegativeState, PositiveState, authority.CaptureSnapshot());
            authority.AdvanceTick(12u, Array.Empty<WallEffortIntent>(), Allow);

            Assert.That(
                receiver.TryApplySnapshot(authority.CaptureSnapshot()),
                Is.EqualTo(WallSnapshotApplyStatus.Applied));
            Assert.That(receiver.LastProcessedTick, Is.EqualTo(12u));
            receiver.AdvanceTick(13u, Array.Empty<WallEffortIntent>(), Allow);
            authority.AdvanceTick(13u, Array.Empty<WallEffortIntent>(), Allow);
            Assert.That(receiver.State, Is.EqualTo(authority.State));
        }

        [Test]
        public void SnapshotCodec_RejectsVersionTrailingBytesAndTruncation()
        {
            var snapshot = CreateMachine(initialTick: 7u).CaptureSnapshot();
            var bytes = snapshot.ToBytes();
            Assert.That(bytes, Has.Length.EqualTo(22));
            Assert.That(
                BitConverter.ToString(bytes).Replace("-", string.Empty).ToLowerInvariant(),
                Is.EqualTo("01591b00001100000000000000070000000000000000"),
                "Golden vector v1: version, int32/uint32 little-endian, flag de transition.");

            var wrongVersion = (byte[])bytes.Clone();
            wrongVersion[0] = 99;
            Assert.That(WallSnapshot.TryFromBytes(wrongVersion, out _, out var versionCode), Is.False);
            Assert.That(versionCode, Is.EqualTo(WallSnapshotDecodeCodes.FormatUnsupported));

            var trailing = bytes.Concat(new byte[] { 0 }).ToArray();
            Assert.That(WallSnapshot.TryFromBytes(trailing, out _, out var trailingCode), Is.False);
            Assert.That(trailingCode, Is.EqualTo(WallSnapshotDecodeCodes.PayloadTrailingBytes));

            var invalidBoolean = (byte[])bytes.Clone();
            invalidBoolean[21] = 2;
            Assert.That(
                WallSnapshot.TryFromBytes(invalidBoolean, out _, out var booleanCode),
                Is.False);
            Assert.That(booleanCode, Is.EqualTo(WallSnapshotDecodeCodes.PayloadMalformed));

            Assert.That(
                WallSnapshot.TryFromBytes(bytes.Take(5).ToArray(), out _, out var malformedCode),
                Is.False);
            Assert.That(malformedCode, Is.EqualTo(WallSnapshotDecodeCodes.PayloadMalformed));
        }

        [TestCase(30)]
        [TestCase(60)]
        [TestCase(120)]
        public void RenderSamplingRate_CannotChangeAuthoritativeOutcome(int renderFramesPerSecond)
        {
            var baseline = RunAuthoritativeSequenceWithRenderSampling(0, out var baselineTrace);
            var snapshot = RunAuthoritativeSequenceWithRenderSampling(
                renderFramesPerSecond, out var sampledTrace);

            Assert.That(sampledTrace, Is.EqualTo(baselineTrace),
                "Chaque état autoritaire par tick doit rester identique à la baseline sans rendu.");
            Assert.That(snapshot, Is.EqualTo(baseline));
            Assert.That(snapshot.StateId, Is.EqualTo(NegativeState));
            Assert.That(snapshot.Revision, Is.EqualTo(6u));
            Assert.That(snapshot.CapturedTick, Is.EqualTo(60u));
            Assert.That(snapshot.IsTransitioning, Is.False);
        }

        [Test]
        public void DuplicateSkippedAndOutOfOrderTicks_AreRejected()
        {
            var machine = CreateMachine(initialTick: 10u);
            machine.AdvanceTick(11u, Array.Empty<WallEffortIntent>(), Allow);

            Assert.That(
                () => machine.AdvanceTick(11u, Array.Empty<WallEffortIntent>(), Allow),
                Throws.InvalidOperationException.With.Message.Contains("attendu 12"));
            Assert.That(
                () => machine.AdvanceTick(13u, Array.Empty<WallEffortIntent>(), Allow),
                Throws.InvalidOperationException.With.Message.Contains("attendu 12"));
        }

        [Test]
        public void Revision_IncrementsAcrossUintWrap()
        {
            var machine = new WallStateMachine(
                Settings,
                WallId,
                NegativeState,
                PositiveState,
                NegativeState,
                initialTick: 0u,
                initialRevision: uint.MaxValue);

            machine.AdvanceTick(1u, Push(1), Allow);

            Assert.That(machine.State.Revision, Is.EqualTo(0u));

            var receiver = new WallStateMachine(
                Settings,
                WallId,
                NegativeState,
                PositiveState,
                NegativeState,
                initialTick: 0u,
                initialRevision: uint.MaxValue);
            var wrapped = new WallSnapshot(new WallState(WallId, NegativeState, 0u), 1u);
            Assert.That(
                receiver.TryApplySnapshot(wrapped),
                Is.EqualTo(WallSnapshotApplyStatus.Applied));
            Assert.That(receiver.State.Revision, Is.Zero);
            Assert.That(
                receiver.TryApplySnapshot(
                    new WallSnapshot(new WallState(WallId, NegativeState, uint.MaxValue), 0u)),
                Is.EqualTo(WallSnapshotApplyStatus.Stale));
            Assert.That(
                receiver.TryApplySnapshot(
                    new WallSnapshot(new WallState(WallId, NegativeState, 0x80000000u), 2u)),
                Is.EqualTo(WallSnapshotApplyStatus.Invalid));
        }

        [Test]
        public void DefaultSettingsAndImpossibleStableThreshold_AreRejected()
        {
            Assert.That(
                () => new WallStateMachine(
                    default,
                    WallId,
                    NegativeState,
                    PositiveState,
                    NegativeState,
                    0u),
                Throws.TypeOf<ArgumentOutOfRangeException>());

            var bytes = CreateMachine(initialTick: 0u).CaptureSnapshot().ToBytes();
            var thresholdBytes = BitConverter.GetBytes(Settings.EffortThreshold);
            Array.Copy(thresholdBytes, 0, bytes, 17, thresholdBytes.Length);
            Assert.That(WallSnapshot.TryFromBytes(bytes, out var decoded, out var code), Is.True, code);
            Assert.That(
                () => WallStateMachine.FromSnapshot(
                    Settings, NegativeState, PositiveState, decoded),
                Throws.ArgumentException.With.Message.Contains("incompatible"));
        }

        private static WallSnapshot RunAuthoritativeSequenceWithRenderSampling(
            int renderRate,
            out WallState[] trace)
        {
            const int simulationRate = 60;
            var machine = CreateMachine(initialTick: 0u);
            var renderAccumulator = 0;
            var states = new List<WallState>(60);
            for (uint tick = 1u; tick <= 60u; tick++)
            {
                IReadOnlyList<WallEffortIntent> intents = tick switch
                {
                    1u => Push(60),
                    2u => Push(40),
                    10u => new[] { new WallEffortIntent(WallId, 1, -60) },
                    11u => new[] { new WallEffortIntent(WallId, 1, -40) },
                    _ => Array.Empty<WallEffortIntent>()
                };
                machine.AdvanceTick(tick, intents, Allow);
                states.Add(machine.State);

                renderAccumulator += renderRate;
                while (renderAccumulator >= simulationRate)
                {
                    _ = machine.State.SamplePose(tick);
                    renderAccumulator -= simulationRate;
                }
            }
            trace = states.ToArray();
            return machine.CaptureSnapshot();
        }

        private static WallStateMachine CreateMachine(uint initialTick) => new(
            Settings,
            WallId,
            NegativeState,
            PositiveState,
            NegativeState,
            initialTick);

        private static WallEffortIntent[] Push(int effort) =>
            new[] { new WallEffortIntent(WallId, 1, effort) };

        private static WallTransitionGateDecision Allow(WallTransitionRequest request) =>
            WallTransitionGateDecision.Accept();
    }
}
