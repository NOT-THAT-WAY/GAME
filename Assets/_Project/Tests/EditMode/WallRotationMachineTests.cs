using System;
using System.Collections.Generic;
using NotThatWay.Game.Simulation;
using NUnit.Framework;

namespace NotThatWay.Game.Tests.EditMode
{
    public sealed class WallRotationMachineTests
    {
        private const int WallId = 10;
        private const int MaximumSpeed = 900;
        private const int MinimumLeverage = 300;

        private static WallSimulationSettings Settings =>
            new(MaximumSpeed, MinimumLeverage, 180u);

        private static WallRotationMachine NewMachine(int initialAngle = 0) =>
            new(Settings, WallId, initialAngle, 0u);

        private static WallTorqueIntent Push(int sourceId, int direction, int leverage) =>
            new(WallId, sourceId, direction, leverage);

        [Test]
        public void TorqueAggregation_IsIndependentOfArrivalOrderAndClientIdentity()
        {
            var ascending = NewMachine();
            var descending = NewMachine();
            var first = new[] { Push(3, 1, 400), Push(11, 1, 250) };
            var second = new[] { Push(11, 1, 250), Push(3, 1, 400) };

            var left = ascending.AdvanceTick(1u, first);
            var right = descending.AdvanceTick(1u, second);

            Assert.That(left.NetLeveragePermille, Is.EqualTo(650));
            Assert.That(right.NetLeveragePermille, Is.EqualTo(650));
            Assert.That(left.Current, Is.EqualTo(right.Current));
            Assert.That(
                left.Current.AngularVelocityMilliDegreesPerTick,
                Is.EqualTo(585),
                "650 pour mille de 900 milli-degrés font 585, en division entière.");
        }

        [Test]
        public void OpposedSources_SubtractExactlyAndTheStrongerLeverageWins()
        {
            var machine = NewMachine();

            // Deux pousseurs face à face, même bras de levier : le battant ne
            // bouge pas d'un milli-degré, et l'événement le dit.
            var balanced = machine.AdvanceTick(
                1u,
                new[] { Push(1, 1, 650), Push(2, -1, 650) });
            Assert.That(balanced.NetLeveragePermille, Is.Zero);
            Assert.That(balanced.Current.AngularVelocityMilliDegreesPerTick, Is.Zero);
            Assert.That(balanced.Current.AngleMilliDegrees, Is.Zero);
            Assert.That(balanced.Events & WallTickEvents.TorqueOpposed,
                Is.EqualTo(WallTickEvents.TorqueOpposed));
            Assert.That(balanced.ContributingSourceCount, Is.EqualTo(2));

            // Un pas de côté qui ne change le levier que d'un pour mille ne doit
            // pas ouvrir un segment : sans quantification, le battant se
            // synchroniserait à chaque tick.
            var jittered = machine.AdvanceTick(2u, new[] { Push(1, 1, 649) });
            var stable = machine.AdvanceTick(3u, new[] { Push(1, 1, 651) });
            Assert.That(
                stable.Current.AngularVelocityMilliDegreesPerTick,
                Is.EqualTo(jittered.Current.AngularVelocityMilliDegreesPerTick));
            Assert.That(stable.SegmentChanged, Is.False);
            Assert.That(WallSimulationSettings.QuantizeLeverage(-649), Is.EqualTo(-650));

            // Le pousseur au bout du battant l'emporte sur celui du gond, à la
            // différence exacte de leurs leviers.
            var contested = machine.AdvanceTick(
                4u,
                new[] { Push(1, 1, 1000), Push(2, -1, 300) });
            Assert.That(contested.NetLeveragePermille, Is.EqualTo(700));
            Assert.That(contested.Current.AngularVelocityMilliDegreesPerTick, Is.EqualTo(630));
            Assert.That(contested.Current.AngleMilliDegrees, Is.EqualTo(2 * 585 + 630));

            // Une seule source ne dépasse jamais la pleine puissance, même si
            // deux intentions lui sont attribuées par erreur au même tick.
            var saturated = machine.AdvanceTick(
                5u,
                new[] { Push(1, 1, 1000), Push(1, 1, 1000) });
            Assert.That(saturated.NetLeveragePermille, Is.EqualTo(1000));
            Assert.That(
                saturated.Current.AngularVelocityMilliDegreesPerTick,
                Is.EqualTo(MaximumSpeed));

            // Deux pousseurs du même côté n'accélèrent pas le battant au-delà
            // de sa vitesse nominale.
            var together = machine.AdvanceTick(
                6u,
                new[] { Push(1, 1, 1000), Push(2, 1, 1000) });
            Assert.That(together.NetLeveragePermille, Is.EqualTo(2000));
            Assert.That(
                together.Current.AngularVelocityMilliDegreesPerTick,
                Is.EqualTo(MaximumSpeed));
        }

        [Test]
        public void Rotation_StartsOnTheFirstHeldTickAndStopsOnRelease()
        {
            var machine = NewMachine();

            var first = machine.AdvanceTick(1u, new[] { Push(1, 1, 1000) });
            Assert.That(
                first.Current.AngleMilliDegrees,
                Is.EqualTo(MaximumSpeed),
                "Aucun seuil à charger : le premier tick d'appui déplace déjà le battant.");
            Assert.That(first.Events & WallTickEvents.RotationStarted,
                Is.EqualTo(WallTickEvents.RotationStarted));
            Assert.That(first.SegmentChanged, Is.True);

            var second = machine.AdvanceTick(2u, new[] { Push(1, 1, 1000) });
            Assert.That(second.Current.AngleMilliDegrees, Is.EqualTo(2 * MaximumSpeed));
            Assert.That(second.SegmentChanged, Is.False,
                "Une vitesse inchangée ne justifie aucune diffusion hors battement.");
            Assert.That(second.Current.Revision, Is.EqualTo(first.Current.Revision));

            var released = machine.AdvanceTick(3u, Array.Empty<WallTorqueIntent>());
            Assert.That(released.Current.AngularVelocityMilliDegreesPerTick, Is.Zero);
            Assert.That(
                released.Current.AngleMilliDegrees,
                Is.EqualTo(2 * MaximumSpeed),
                "Sans inertie, le battant s'arrête au tick où l'appui cesse.");
            Assert.That(released.Events & WallTickEvents.RotationStopped,
                Is.EqualTo(WallTickEvents.RotationStopped));
            Assert.That(released.Current.Revision, Is.EqualTo(TickMath.Next(first.Current.Revision)));
        }

        [Test]
        public void Rotation_CoversAFullTurnAndReversesWithoutPassingThroughAPose()
        {
            var machine = NewMachine();
            var tick = 0u;
            var full = new[] { Push(1, 1, 1000) };

            // 400 ticks à 900 milli-degrés font exactement un tour complet.
            for (var index = 0; index < 400; index++)
                machine.AdvanceTick(++tick, full);
            Assert.That(machine.State.AngleMilliDegrees, Is.Zero,
                "Un tour complet ramène l'angle à son origine, sans butée.");

            for (var index = 0; index < 100; index++)
                machine.AdvanceTick(++tick, full);
            Assert.That(machine.State.AngleMilliDegrees, Is.EqualTo(90000));

            var reversed = machine.AdvanceTick(++tick, new[] { Push(1, -1, 1000) });
            Assert.That(reversed.Events & WallTickEvents.DirectionReversed,
                Is.EqualTo(WallTickEvents.DirectionReversed));
            Assert.That(reversed.Current.AngleMilliDegrees, Is.EqualTo(90000 - MaximumSpeed));

            for (var index = 0; index < 200; index++)
                machine.AdvanceTick(++tick, new[] { Push(1, -1, 1000) });
            Assert.That(
                machine.State.AngleMilliDegrees,
                Is.EqualTo(FixedTrigonometry.Normalize(90000 - 201 * MaximumSpeed)),
                "Le passage sous zéro repasse par 360000, jamais par une valeur négative.");
        }

        [Test]
        public void PoseSampling_IsAFunctionOfTheTickAndBoundedInExtrapolation()
        {
            var state = new WallState(WallId, 1000, 600, 100u, 5u);

            Assert.That(state.SamplePose(100u, 180u).AngleMilliDegrees, Is.EqualTo(1000));
            Assert.That(state.SamplePose(110u, 180u).AngleMilliDegrees, Is.EqualTo(7000));
            Assert.That(state.SamplePose(110u, 180u).ElapsedTicks, Is.EqualTo(10u));
            Assert.That(
                state.SamplePose(99u, 180u).AngleMilliDegrees,
                Is.EqualTo(1000),
                "Un tick antérieur à l'ancrage ne doit inventer aucun passé.");
            Assert.That(
                state.SamplePose(100u + 5000u, 180u).AngleMilliDegrees,
                Is.EqualTo(FixedTrigonometry.Normalize(1000 + 600L * 180)),
                "Un segment perdu ne doit pas faire tourner le battant indéfiniment.");
        }

        [Test]
        [TestCase(30)]
        [TestCase(60)]
        [TestCase(120)]
        public void RenderSamplingRate_CannotChangeAuthoritativeOutcome(int renderFramesPerSecond)
        {
            var machine = NewMachine();
            var intents = new[] { Push(1, 1, 650) };
            for (var tick = 1u; tick <= 120u; tick++)
                machine.AdvanceTick(tick, intents);

            var samples = new List<int>();
            var step = Math.Max(1, 60 / renderFramesPerSecond);
            for (var tick = 120u; tick <= 180u; tick += (uint)step)
                samples.Add(machine.State.SamplePose(tick, 180u).AngleMilliDegrees);

            Assert.That(machine.State.AngleMilliDegrees, Is.EqualTo(120 * 585));
            Assert.That(samples[0], Is.EqualTo(120 * 585));
            Assert.That(
                samples[samples.Count - 1],
                Is.EqualTo(FixedTrigonometry.Normalize(120 * 585 + 585L * (samples.Count - 1) * step)),
                "L'échantillonnage d'affichage lit l'état, il ne le produit pas.");
        }

        [Test]
        public void Snapshot_RoundTripsAndRestoresALateJoinDuringUintWrap()
        {
            var machine = new WallRotationMachine(Settings, WallId, 12345, uint.MaxValue - 2u, 7u);
            machine.AdvanceTick(uint.MaxValue - 1u, new[] { Push(1, 1, 1000) });
            machine.AdvanceTick(uint.MaxValue, new[] { Push(1, 1, 1000) });
            machine.AdvanceTick(0u, new[] { Push(1, 1, 1000) });

            var snapshot = machine.CaptureSnapshot();
            Assert.That(snapshot.AnchorTick, Is.Zero);
            Assert.That(snapshot.AngleMilliDegrees, Is.EqualTo(12345 + 3 * MaximumSpeed));

            Assert.That(
                WallSnapshot.TryFromBytes(snapshot.ToBytes(), out var decoded, out var code),
                Is.True,
                code);
            Assert.That(decoded, Is.EqualTo(snapshot));

            var lateJoin = WallRotationMachine.FromSnapshot(Settings, decoded);
            Assert.That(lateJoin.State, Is.EqualTo(machine.State));
            Assert.That(lateJoin.LastProcessedTick, Is.EqualTo(machine.LastProcessedTick));
        }

        [Test]
        public void Snapshot_RejectsStaleConflictingAndIncompatiblePayloads()
        {
            var machine = NewMachine();
            machine.AdvanceTick(1u, new[] { Push(1, 1, 1000) });
            var current = machine.CaptureSnapshot();

            Assert.That(machine.PreviewSnapshot(current), Is.EqualTo(WallSnapshotApplyStatus.Duplicate));
            Assert.That(
                machine.PreviewSnapshot(new WallSnapshot(new WallState(WallId, 0, 0, 0u, 0u))),
                Is.EqualTo(WallSnapshotApplyStatus.Stale));

            // Même révision, vitesse différente : deux segments distincts ne
            // peuvent pas porter le même numéro.
            Assert.That(
                machine.PreviewSnapshot(new WallSnapshot(new WallState(
                    WallId,
                    current.AngleMilliDegrees,
                    -MaximumSpeed,
                    current.AnchorTick,
                    current.Revision))),
                Is.EqualTo(WallSnapshotApplyStatus.RevisionConflict));

            // Même segment, ancrage plus récent : c'est le battement périodique.
            Assert.That(
                machine.PreviewSnapshot(new WallSnapshot(new WallState(
                    WallId,
                    current.AngleMilliDegrees + MaximumSpeed,
                    current.AngularVelocityMilliDegreesPerTick,
                    current.AnchorTick + 1u,
                    current.Revision))),
                Is.EqualTo(WallSnapshotApplyStatus.Applied));

            Assert.That(
                machine.PreviewSnapshot(new WallSnapshot(new WallState(
                    WallId,
                    0,
                    FixedTrigonometry.QuarterTurnMilliDegrees,
                    current.AnchorTick + 2u,
                    current.Revision + 1u))),
                Is.EqualTo(WallSnapshotApplyStatus.Invalid),
                "Une vitesse hors contrat doit être refusée avant toute application.");

            Assert.That(
                machine.PreviewSnapshot(new WallSnapshot(new WallState(11, 0, 0u))),
                Is.EqualTo(WallSnapshotApplyStatus.Invalid));
        }

        [Test]
        public void SnapshotCodec_RejectsVersionTrailingBytesAndTruncation()
        {
            var payload = new WallSnapshot(new WallState(WallId, 4200, -450, 9u, 3u)).ToBytes();

            var wrongVersion = (byte[])payload.Clone();
            wrongVersion[0] = 99;
            Assert.That(WallSnapshot.TryFromBytes(wrongVersion, out _, out var versionCode), Is.False);
            Assert.That(versionCode, Is.EqualTo(WallSnapshotDecodeCodes.FormatUnsupported));

            var trailing = new byte[payload.Length + 1];
            Array.Copy(payload, trailing, payload.Length);
            Assert.That(WallSnapshot.TryFromBytes(trailing, out _, out var trailingCode), Is.False);
            Assert.That(trailingCode, Is.EqualTo(WallSnapshotDecodeCodes.PayloadTrailingBytes));

            var truncated = new byte[payload.Length - 3];
            Array.Copy(payload, truncated, truncated.Length);
            Assert.That(WallSnapshot.TryFromBytes(truncated, out _, out var truncatedCode), Is.False);
            Assert.That(truncatedCode, Is.EqualTo(WallSnapshotDecodeCodes.PayloadMalformed));

            Assert.That(WallSnapshot.TryFromBytes(null, out _, out var missingCode), Is.False);
            Assert.That(missingCode, Is.EqualTo(WallSnapshotDecodeCodes.PayloadMissing));

            // Un angle hors domaine ne doit jamais franchir le décodeur.
            var corrupted = (byte[])payload.Clone();
            BitConverter.GetBytes(400_000).CopyTo(corrupted, 5);
            Assert.That(WallSnapshot.TryFromBytes(corrupted, out _, out var corruptedCode), Is.False);
            Assert.That(corruptedCode, Is.EqualTo(WallSnapshotDecodeCodes.PayloadMalformed));
        }

        [Test]
        public void DuplicateSkippedAndOutOfOrderTicks_AreRejected()
        {
            var machine = NewMachine();
            machine.AdvanceTick(1u, Array.Empty<WallTorqueIntent>());

            Assert.That(
                () => machine.AdvanceTick(1u, Array.Empty<WallTorqueIntent>()),
                Throws.InvalidOperationException);
            Assert.That(
                () => machine.AdvanceTick(3u, Array.Empty<WallTorqueIntent>()),
                Throws.InvalidOperationException);
            Assert.That(
                () => machine.AdvanceTick(2u, null),
                Throws.ArgumentNullException);
            Assert.That(machine.LastProcessedTick, Is.EqualTo(1u));
        }

        [Test]
        public void Revision_IncrementsOnlyOnSegmentChangeAcrossUintWrap()
        {
            var machine = new WallRotationMachine(Settings, WallId, 0, 10u, uint.MaxValue - 1u);
            var pushing = new[] { Push(1, 1, 1000) };

            machine.AdvanceTick(11u, pushing);
            Assert.That(machine.State.Revision, Is.EqualTo(uint.MaxValue));
            machine.AdvanceTick(12u, pushing);
            Assert.That(machine.State.Revision, Is.EqualTo(uint.MaxValue),
                "Un segment stable ne consomme pas de révision.");
            machine.AdvanceTick(13u, Array.Empty<WallTorqueIntent>());
            Assert.That(machine.State.Revision, Is.Zero, "La révision boucle modulo 2^32.");
        }

        [Test]
        public void Settings_RejectImpossibleValues()
        {
            Assert.That(() => new WallSimulationSettings(0, 300, 180u), Throws.TypeOf<ArgumentOutOfRangeException>());
            Assert.That(
                () => new WallSimulationSettings(FixedTrigonometry.QuarterTurnMilliDegrees + 1, 300, 180u),
                Throws.TypeOf<ArgumentOutOfRangeException>());
            Assert.That(() => new WallSimulationSettings(900, 1001, 180u), Throws.TypeOf<ArgumentOutOfRangeException>());
            Assert.That(() => new WallSimulationSettings(900, 300, 0u), Throws.TypeOf<ArgumentOutOfRangeException>());
            Assert.That(() => new WallTorqueIntent(WallId, 1, 0, 500), Throws.TypeOf<ArgumentOutOfRangeException>());
            Assert.That(() => new WallTorqueIntent(WallId, 1, 1, 1001), Throws.TypeOf<ArgumentOutOfRangeException>());
            Assert.That(() => new WallState(WallId, -1, 0u), Throws.TypeOf<ArgumentOutOfRangeException>());
            Assert.That(() => new WallState(WallId, 360000, 0u), Throws.TypeOf<ArgumentOutOfRangeException>());
        }
    }
}
