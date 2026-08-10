using System;
using System.Collections.Generic;

namespace NotThatWay.Game.Simulation
{
    [Flags]
    public enum WallTickEvents : byte
    {
        None = 0,

        /// <summary>Le battant a tourné pendant ce tick.</summary>
        Rotating = 1 << 0,

        /// <summary>La vitesse a changé : un nouveau segment doit être diffusé.</summary>
        SegmentChanged = 1 << 1,

        RotationStarted = 1 << 2,
        RotationStopped = 1 << 3,

        /// <summary>Le sens s'est inversé sans repasser par l'arrêt.</summary>
        DirectionReversed = 1 << 4,

        /// <summary>Des sources poussent en même temps sur les deux faces.</summary>
        TorqueOpposed = 1 << 5
    }

    public readonly struct WallTickResult
    {
        internal WallTickResult(
            uint tick,
            WallState previous,
            WallState current,
            int netLeveragePermille,
            int contributingSourceCount,
            WallTickEvents events)
        {
            Tick = tick;
            Previous = previous;
            Current = current;
            NetLeveragePermille = netLeveragePermille;
            ContributingSourceCount = contributingSourceCount;
            Events = events;
        }

        public uint Tick { get; }
        public WallState Previous { get; }
        public WallState Current { get; }
        public int NetLeveragePermille { get; }
        public int ContributingSourceCount { get; }
        public WallTickEvents Events { get; }
        public bool Changed => !Previous.Equals(Current);

        /// <summary>
        /// Seul un changement de segment justifie une diffusion hors battement :
        /// entre deux segments, la pose reste une fonction du tick chez le client.
        /// </summary>
        public bool SegmentChanged => (Events & WallTickEvents.SegmentChanged) != 0;
    }

    /// <summary>
    /// Simulation autoritaire d'un battant libre. Le couple net des sources donne
    /// directement la vitesse angulaire du tick : pas de seuil à charger, donc
    /// aucune latence à l'appui, et pas d'inertie, donc l'arrêt et la contre-poussée
    /// sont exacts. La machine ne connaît ni fréquence concrète, ni deltaTime, ni
    /// PhysX ; la géométrie du contact reste calculée par l'appelant.
    /// </summary>
    public sealed class WallRotationMachine
    {
        private readonly WallSimulationSettings _settings;
        private readonly Dictionary<int, int> _leverageBySource = new(4);
        private WallState _state;
        private uint _lastProcessedTick;
        private bool _isAdvancing;

        public WallRotationMachine(
            WallSimulationSettings settings,
            int wallId,
            int initialAngleMilliDegrees,
            uint initialTick,
            uint initialRevision = 0u)
        {
            settings.Validate();
            _settings = settings;
            _state = new WallState(wallId, initialAngleMilliDegrees, 0, initialTick, initialRevision);
            _lastProcessedTick = initialTick;
        }

        public WallSimulationSettings Settings => _settings;
        public WallState State => _state;
        public uint LastProcessedTick => _lastProcessedTick;

        public WallTickResult AdvanceTick(uint tick, IReadOnlyList<WallTorqueIntent> intents)
        {
            if (_isAdvancing)
            {
                throw new InvalidOperationException(
                    $"AdvanceTick réentrant interdit pour le mur {_state.WallId}.");
            }

            _isAdvancing = true;
            try
            {
                return AdvanceTickCore(tick, intents);
            }
            finally
            {
                _isAdvancing = false;
            }
        }

        private WallTickResult AdvanceTickCore(uint tick, IReadOnlyList<WallTorqueIntent> intents)
        {
            if (!TickMath.IsNext(tick, _lastProcessedTick))
            {
                throw new InvalidOperationException(
                    $"Tick non contigu pour le mur {_state.WallId}: reçu {tick}, " +
                    $"attendu {TickMath.Next(_lastProcessedTick)}.");
            }
            if (intents == null)
                throw new ArgumentNullException(nameof(intents));

            var previous = _state;
            var net = AggregateLeverage(intents, out var contributingSources, out var opposed);
            var velocity = _settings.VelocityFromNetLeverage(net);
            var events = WallTickEvents.None;

            if (opposed)
                events |= WallTickEvents.TorqueOpposed;
            if (velocity != previous.AngularVelocityMilliDegreesPerTick)
            {
                events |= WallTickEvents.SegmentChanged;
                if (previous.AngularVelocityMilliDegreesPerTick == 0)
                    events |= WallTickEvents.RotationStarted;
                else if (velocity == 0)
                    events |= WallTickEvents.RotationStopped;
                else if (velocity > 0 != previous.AngularVelocityMilliDegreesPerTick > 0)
                    events |= WallTickEvents.DirectionReversed;
            }
            if (velocity != 0)
                events |= WallTickEvents.Rotating;

            // L'angle avance d'un tick de vitesse : la pose du tick est toujours
            // celle que le client rejouera pour ce même tick.
            var angle = FixedTrigonometry.Normalize((long)previous.AngleMilliDegrees + velocity);
            var revision = (events & WallTickEvents.SegmentChanged) != 0
                ? TickMath.Next(previous.Revision)
                : previous.Revision;

            _state = new WallState(previous.WallId, angle, velocity, tick, revision);
            _lastProcessedTick = tick;
            return new WallTickResult(tick, previous, _state, net, contributingSources, events);
        }

        /// <summary>
        /// Somme des couples signés. Une source est bornée à la pleine puissance,
        /// et la somme est bornée par la vitesse maximale : deux pousseurs du même
        /// côté ne dépassent pas un pousseur bien placé, mais deux pousseurs opposés
        /// se retranchent au prorata de leur bras de levier.
        /// </summary>
        private int AggregateLeverage(
            IReadOnlyList<WallTorqueIntent> intents,
            out int contributingSources,
            out bool opposed)
        {
            _leverageBySource.Clear();
            for (var index = 0; index < intents.Count; index++)
            {
                var intent = intents[index];
                if (intent.WallId != _state.WallId || intent.LeveragePermille == 0)
                    continue;
                _leverageBySource.TryGetValue(intent.SourceId, out var current);
                _leverageBySource[intent.SourceId] = current + intent.SignedLeveragePermille;
            }

            contributingSources = 0;
            var hasNegative = false;
            var hasPositive = false;
            var net = 0L;
            foreach (var pair in _leverageBySource)
            {
                var signed = Clamp(
                    pair.Value,
                    -WallSimulationSettings.PermilleScale,
                    WallSimulationSettings.PermilleScale);
                if (signed == 0)
                    continue;
                contributingSources++;
                hasNegative |= signed < 0;
                hasPositive |= signed > 0;
                net += signed;
            }

            opposed = hasNegative && hasPositive;
            return (int)Clamp(net, int.MinValue, int.MaxValue);
        }

        public WallSnapshot CaptureSnapshot() => new(_state);

        /// <summary>Évalue un snapshot sans muter la machine.</summary>
        public WallSnapshotApplyStatus PreviewSnapshot(WallSnapshot snapshot)
        {
            if (_isAdvancing)
            {
                throw new InvalidOperationException(
                    $"Application de snapshot interdite pendant AdvanceTick pour le mur {_state.WallId}.");
            }
            if (!IsSnapshotCompatible(snapshot))
                return WallSnapshotApplyStatus.Invalid;

            var candidate = snapshot.ToWallState();
            int revisionOrder;
            try
            {
                revisionOrder = TickMath.Compare(candidate.Revision, _state.Revision);
            }
            catch (ArgumentException)
            {
                return WallSnapshotApplyStatus.Invalid;
            }

            if (revisionOrder < 0)
                return WallSnapshotApplyStatus.Stale;
            if (revisionOrder > 0)
                return WallSnapshotApplyStatus.Applied;

            // Même révision : deux ancrages du même segment sont légitimes, mais
            // une vitesse différente sous la même révision est une incohérence.
            if (!candidate.SharesSegment(_state))
                return WallSnapshotApplyStatus.RevisionConflict;

            int tickOrder;
            try
            {
                tickOrder = TickMath.Compare(candidate.AnchorTick, _state.AnchorTick);
            }
            catch (ArgumentException)
            {
                return WallSnapshotApplyStatus.Invalid;
            }
            if (tickOrder < 0)
                return WallSnapshotApplyStatus.Stale;
            if (tickOrder > 0)
                return WallSnapshotApplyStatus.Applied;
            return candidate.Equals(_state)
                ? WallSnapshotApplyStatus.Duplicate
                : WallSnapshotApplyStatus.RevisionConflict;
        }

        public WallSnapshotApplyStatus TryApplySnapshot(WallSnapshot snapshot)
        {
            var status = PreviewSnapshot(snapshot);
            if (status != WallSnapshotApplyStatus.Applied)
                return status;

            _state = snapshot.ToWallState();
            _lastProcessedTick = _state.AnchorTick;
            return WallSnapshotApplyStatus.Applied;
        }

        public static WallRotationMachine FromSnapshot(
            WallSimulationSettings settings,
            WallSnapshot snapshot)
        {
            var machine = new WallRotationMachine(
                settings,
                snapshot.WallId,
                snapshot.AngleMilliDegrees,
                snapshot.AnchorTick,
                snapshot.Revision);
            if (!machine.IsSnapshotCompatible(snapshot))
            {
                throw new ArgumentException(
                    "Snapshot incompatible avec le contrat du mur.",
                    nameof(snapshot));
            }
            machine._state = snapshot.ToWallState();
            return machine;
        }

        private bool IsSnapshotCompatible(WallSnapshot snapshot) =>
            snapshot.WallId == _state.WallId &&
            Math.Abs(snapshot.AngularVelocityMilliDegreesPerTick) <=
            _settings.MaximumAngularSpeedMilliDegreesPerTick;

        private static long Clamp(long value, long minimum, long maximum) =>
            value < minimum ? minimum : value > maximum ? maximum : value;
    }
}
