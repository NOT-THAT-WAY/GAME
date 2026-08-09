using System;
using System.Collections.Generic;

namespace NotThatWay.Game.Simulation
{
    [Flags]
    public enum WallTickEvents : byte
    {
        None = 0,
        EffortChanged = 1 << 0,
        TransitionStarted = 1 << 1,
        TransitionCompleted = 1 << 2,
        TransitionRejected = 1 << 3
    }

    public readonly struct WallTickResult
    {
        internal WallTickResult(
            uint tick,
            WallState previous,
            WallState current,
            long aggregatedEffort,
            WallTickEvents events,
            string rejectionCode)
        {
            Tick = tick;
            Previous = previous;
            Current = current;
            AggregatedEffort = aggregatedEffort;
            Events = events;
            RejectionCode = rejectionCode ?? string.Empty;
        }

        public uint Tick { get; }
        public WallState Previous { get; }
        public WallState Current { get; }
        public long AggregatedEffort { get; }
        public WallTickEvents Events { get; }
        public string RejectionCode { get; }
        public bool Changed => !Previous.Equals(Current);
    }

    /// <summary>
    /// Simulation autoritaire d'un mur à deux poses. Elle ne connaît ni fréquence
    /// concrète, ni deltaTime, ni PhysX : tous les réglages sont exprimés en ticks
    /// et la validation de destination reste injectée par l'adaptateur serveur.
    /// </summary>
    public sealed class WallStateMachine
    {
        private readonly WallSimulationSettings _settings;
        private readonly int _negativeStateId;
        private readonly int _positiveStateId;
        private WallState _state;
        private uint _lastProcessedTick;
        private bool _isAdvancing;

        public WallStateMachine(
            WallSimulationSettings settings,
            int wallId,
            int negativeStateId,
            int positiveStateId,
            int initialStateId,
            uint initialTick,
            uint initialRevision = 0u)
        {
            settings.Validate();
            if (wallId <= 0)
                throw new ArgumentOutOfRangeException(nameof(wallId));
            if (negativeStateId < 0)
                throw new ArgumentOutOfRangeException(nameof(negativeStateId));
            if (positiveStateId < 0 || positiveStateId == negativeStateId)
                throw new ArgumentOutOfRangeException(nameof(positiveStateId));
            if (initialStateId != negativeStateId && initialStateId != positiveStateId)
                throw new ArgumentOutOfRangeException(nameof(initialStateId));

            _settings = settings;
            _negativeStateId = negativeStateId;
            _positiveStateId = positiveStateId;
            _state = new WallState(wallId, initialStateId, initialRevision);
            _lastProcessedTick = initialTick;
        }

        public WallSimulationSettings Settings => _settings;
        public WallState State => _state;
        public uint LastProcessedTick => _lastProcessedTick;
        public int NegativeStateId => _negativeStateId;
        public int PositiveStateId => _positiveStateId;

        public WallTickResult AdvanceTick(
            uint tick,
            IReadOnlyList<WallEffortIntent> intents,
            Func<WallTransitionRequest, WallTransitionGateDecision> transitionGate)
        {
            if (_isAdvancing)
            {
                throw new InvalidOperationException(
                    $"AdvanceTick réentrant interdit pour le mur {_state.WallId}.");
            }

            _isAdvancing = true;
            try
            {
                return AdvanceTickCore(tick, intents, transitionGate);
            }
            finally
            {
                _isAdvancing = false;
            }
        }

        private WallTickResult AdvanceTickCore(
            uint tick,
            IReadOnlyList<WallEffortIntent> intents,
            Func<WallTransitionRequest, WallTransitionGateDecision> transitionGate)
        {
            if (!TickMath.IsNext(tick, _lastProcessedTick))
            {
                throw new InvalidOperationException(
                    $"Tick non contigu pour le mur {_state.WallId}: reçu {tick}, " +
                    $"attendu {TickMath.Next(_lastProcessedTick)}.");
            }
            if (intents == null)
                throw new ArgumentNullException(nameof(intents));
            if (transitionGate == null)
                throw new ArgumentNullException(nameof(transitionGate));

            var previous = _state;
            var aggregatedEffort = AggregateEffort(intents);
            var stateId = previous.StateId;
            var signedEffort = previous.SignedEffort;
            var activeTransition = previous.ActiveTransition;
            var events = WallTickEvents.None;
            var rejectionCode = string.Empty;
            var changed = false;

            if (activeTransition.HasValue)
            {
                var transition = activeTransition.Value;
                if (!transition.IsComplete(tick))
                {
                    _lastProcessedTick = tick;
                    return new WallTickResult(
                        tick, previous, previous, aggregatedEffort, events, rejectionCode);
                }

                _state = new WallState(
                    previous.WallId,
                    transition.ToStateId,
                    TickMath.Next(previous.Revision));
                _lastProcessedTick = tick;
                return new WallTickResult(
                    tick,
                    previous,
                    _state,
                    aggregatedEffort,
                    WallTickEvents.TransitionCompleted,
                    rejectionCode);
            }

            var candidateEffort = aggregatedEffort == 0
                ? DecayTowardZero(signedEffort, _settings.EffortDecayPerTick)
                : (long)signedEffort + aggregatedEffort;

            int targetStateId;
            var thresholdReached = false;
            if (stateId == _negativeStateId)
            {
                signedEffort = (int)Clamp(candidateEffort, 0L, _settings.EffortThreshold);
                targetStateId = _positiveStateId;
                thresholdReached = signedEffort == _settings.EffortThreshold;
            }
            else
            {
                signedEffort = (int)Clamp(candidateEffort, -_settings.EffortThreshold, 0L);
                targetStateId = _negativeStateId;
                thresholdReached = signedEffort == -_settings.EffortThreshold;
            }

            if (signedEffort != previous.SignedEffort)
            {
                events |= WallTickEvents.EffortChanged;
                changed = true;
            }

            var nextRevision = changed || thresholdReached
                ? TickMath.Next(previous.Revision)
                : previous.Revision;

            if (thresholdReached)
            {
                var request = new WallTransitionRequest(
                    previous.WallId,
                    stateId,
                    targetStateId,
                    tick,
                    _settings.TransitionDurationTicks,
                    nextRevision);
                var decision = transitionGate(request);
                if (decision.Allowed)
                {
                    activeTransition = new WallTransition(
                        previous.WallId,
                        stateId,
                        targetStateId,
                        tick,
                        _settings.TransitionDurationTicks,
                        nextRevision);
                    signedEffort = 0;
                    events |= WallTickEvents.TransitionStarted;
                    changed = true;
                }
                else
                {
                    if (string.IsNullOrWhiteSpace(decision.RejectionCode))
                    {
                        throw new InvalidOperationException(
                            "La gate a refusé une transition sans code stable.");
                    }
                    signedEffort = stateId == _negativeStateId
                        ? _settings.RejectedEffortRetention
                        : -_settings.RejectedEffortRetention;
                    rejectionCode = decision.RejectionCode;
                    events |= WallTickEvents.TransitionRejected;
                    changed = true;
                }
            }

            if (changed)
            {
                nextRevision = TickMath.Next(previous.Revision);
                if (activeTransition.HasValue && activeTransition.Value.Revision != nextRevision)
                {
                    var transition = activeTransition.Value;
                    activeTransition = new WallTransition(
                        transition.WallId,
                        transition.FromStateId,
                        transition.ToStateId,
                        transition.StartTick,
                        transition.DurationTicks,
                        nextRevision);
                }
                _state = new WallState(
                    previous.WallId,
                    stateId,
                    nextRevision,
                    signedEffort,
                    activeTransition);
            }

            _lastProcessedTick = tick;
            return new WallTickResult(
                tick, previous, _state, aggregatedEffort, events, rejectionCode);
        }

        public WallSnapshot CaptureSnapshot() => new(_state, _lastProcessedTick);

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

            int revisionOrder;
            try
            {
                revisionOrder = TickMath.Compare(snapshot.Revision, _state.Revision);
            }
            catch (ArgumentException)
            {
                return WallSnapshotApplyStatus.Invalid;
            }

            var candidate = snapshot.ToWallState();
            if (revisionOrder < 0)
                return WallSnapshotApplyStatus.Stale;
            if (revisionOrder == 0)
            {
                if (!candidate.Equals(_state))
                    return WallSnapshotApplyStatus.RevisionConflict;

                int tickOrder;
                try
                {
                    tickOrder = TickMath.Compare(snapshot.CapturedTick, _lastProcessedTick);
                }
                catch (ArgumentException)
                {
                    return WallSnapshotApplyStatus.Invalid;
                }
                if (tickOrder < 0)
                    return WallSnapshotApplyStatus.Stale;
                if (tickOrder == 0)
                    return WallSnapshotApplyStatus.Duplicate;
                return WallSnapshotApplyStatus.Applied;
            }

            return WallSnapshotApplyStatus.Applied;
        }

        public WallSnapshotApplyStatus TryApplySnapshot(WallSnapshot snapshot)
        {
            var status = PreviewSnapshot(snapshot);
            if (status != WallSnapshotApplyStatus.Applied)
                return status;

            _state = snapshot.ToWallState();
            _lastProcessedTick = snapshot.CapturedTick;
            return WallSnapshotApplyStatus.Applied;
        }

        public static WallStateMachine FromSnapshot(
            WallSimulationSettings settings,
            int negativeStateId,
            int positiveStateId,
            WallSnapshot snapshot)
        {
            var machine = new WallStateMachine(
                settings,
                snapshot.WallId,
                negativeStateId,
                positiveStateId,
                snapshot.StateId,
                snapshot.CapturedTick,
                snapshot.Revision);
            if (!machine.IsSnapshotCompatible(snapshot))
                throw new ArgumentException("Snapshot incompatible avec le contrat du mur.", nameof(snapshot));
            machine._state = snapshot.ToWallState();
            return machine;
        }

        private long AggregateEffort(IReadOnlyList<WallEffortIntent> intents)
        {
            Dictionary<int, long> bySource = null;
            for (var index = 0; index < intents.Count; index++)
            {
                var intent = intents[index];
                if (intent.WallId != _state.WallId || intent.SignedEffort == 0)
                    continue;
                bySource ??= new Dictionary<int, long>();
                bySource.TryGetValue(intent.SourceId, out var current);
                bySource[intent.SourceId] = current + intent.SignedEffort;
            }

            if (bySource == null)
                return 0;
            long total = 0;
            foreach (var pair in bySource)
            {
                total += Clamp(
                    pair.Value,
                    -_settings.MaximumEffortPerSourcePerTick,
                    _settings.MaximumEffortPerSourcePerTick);
            }
            return total;
        }

        private bool IsSnapshotCompatible(WallSnapshot snapshot)
        {
            if (snapshot.WallId != _state.WallId ||
                snapshot.StateId != _negativeStateId && snapshot.StateId != _positiveStateId)
                return false;
            if (snapshot.SignedEffort < -_settings.EffortThreshold ||
                snapshot.SignedEffort > _settings.EffortThreshold)
                return false;
            if (snapshot.StateId == _negativeStateId && snapshot.SignedEffort < 0 ||
                snapshot.StateId == _positiveStateId && snapshot.SignedEffort > 0)
                return false;
            if (!snapshot.ActiveTransition.HasValue)
                return Math.Abs(snapshot.SignedEffort) < _settings.EffortThreshold;

            var transition = snapshot.ActiveTransition.Value;
            return transition.DurationTicks == _settings.TransitionDurationTicks &&
                   transition.FromStateId == snapshot.StateId &&
                   (transition.FromStateId == _negativeStateId && transition.ToStateId == _positiveStateId ||
                    transition.FromStateId == _positiveStateId && transition.ToStateId == _negativeStateId);
        }

        private static long DecayTowardZero(int value, int decay)
        {
            if (value > 0)
                return Math.Max(0, value - decay);
            if (value < 0)
                return Math.Min(0, value + decay);
            return 0;
        }

        private static long Clamp(long value, long minimum, long maximum) =>
            value < minimum ? minimum : value > maximum ? maximum : value;
    }
}
