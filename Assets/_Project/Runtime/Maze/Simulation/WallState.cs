using System;

namespace NotThatWay.Game.Simulation
{
    public readonly struct WallSimulationSettings : IEquatable<WallSimulationSettings>
    {
        public WallSimulationSettings(
            int effortThreshold,
            int maximumEffortPerSourcePerTick,
            int effortDecayPerTick,
            int rejectedEffortRetention,
            uint transitionDurationTicks)
        {
            if (effortThreshold <= 0)
                throw new ArgumentOutOfRangeException(nameof(effortThreshold));
            if (maximumEffortPerSourcePerTick <= 0)
                throw new ArgumentOutOfRangeException(nameof(maximumEffortPerSourcePerTick));
            if (effortDecayPerTick < 0 || effortDecayPerTick > effortThreshold)
                throw new ArgumentOutOfRangeException(nameof(effortDecayPerTick));
            if (rejectedEffortRetention < 0 || rejectedEffortRetention >= effortThreshold)
                throw new ArgumentOutOfRangeException(nameof(rejectedEffortRetention));
            TickMath.ValidateDuration(transitionDurationTicks);

            EffortThreshold = effortThreshold;
            MaximumEffortPerSourcePerTick = maximumEffortPerSourcePerTick;
            EffortDecayPerTick = effortDecayPerTick;
            RejectedEffortRetention = rejectedEffortRetention;
            TransitionDurationTicks = transitionDurationTicks;
        }

        public int EffortThreshold { get; }
        public int MaximumEffortPerSourcePerTick { get; }
        public int EffortDecayPerTick { get; }
        public int RejectedEffortRetention { get; }
        public uint TransitionDurationTicks { get; }

        public void Validate()
        {
            if (EffortThreshold <= 0)
                throw new ArgumentOutOfRangeException(nameof(EffortThreshold));
            if (MaximumEffortPerSourcePerTick <= 0)
                throw new ArgumentOutOfRangeException(nameof(MaximumEffortPerSourcePerTick));
            if (EffortDecayPerTick < 0 || EffortDecayPerTick > EffortThreshold)
                throw new ArgumentOutOfRangeException(nameof(EffortDecayPerTick));
            if (RejectedEffortRetention < 0 || RejectedEffortRetention >= EffortThreshold)
                throw new ArgumentOutOfRangeException(nameof(RejectedEffortRetention));
            TickMath.ValidateDuration(TransitionDurationTicks);
        }

        public bool Equals(WallSimulationSettings other) =>
            EffortThreshold == other.EffortThreshold &&
            MaximumEffortPerSourcePerTick == other.MaximumEffortPerSourcePerTick &&
            EffortDecayPerTick == other.EffortDecayPerTick &&
            RejectedEffortRetention == other.RejectedEffortRetention &&
            TransitionDurationTicks == other.TransitionDurationTicks;

        public override bool Equals(object value) => value is WallSimulationSettings other && Equals(other);
        public override int GetHashCode() => HashCode.Combine(
            EffortThreshold,
            MaximumEffortPerSourcePerTick,
            EffortDecayPerTick,
            RejectedEffortRetention,
            TransitionDurationTicks);
    }

    public readonly struct WallEffortIntent
    {
        public WallEffortIntent(int wallId, int sourceId, int signedEffort)
        {
            if (wallId <= 0)
                throw new ArgumentOutOfRangeException(nameof(wallId));
            if (sourceId < 0)
                throw new ArgumentOutOfRangeException(nameof(sourceId));
            WallId = wallId;
            SourceId = sourceId;
            SignedEffort = signedEffort;
        }

        public int WallId { get; }
        public int SourceId { get; }
        public int SignedEffort { get; }
    }

    public readonly struct WallState : IEquatable<WallState>
    {
        public WallState(int wallId, int stateId, uint revision = 0u)
            : this(wallId, stateId, revision, 0, null)
        {
        }

        internal WallState(
            int wallId,
            int stateId,
            uint revision,
            int signedEffort,
            WallTransition? activeTransition)
        {
            if (wallId <= 0)
                throw new ArgumentOutOfRangeException(nameof(wallId));
            if (stateId < 0)
                throw new ArgumentOutOfRangeException(nameof(stateId));
            if (activeTransition.HasValue)
            {
                var transition = activeTransition.Value;
                if (transition.WallId != wallId || transition.FromStateId != stateId ||
                    transition.Revision != revision || signedEffort != 0)
                {
                    throw new ArgumentException("Transition active incohérente avec l'état du mur.");
                }
            }

            WallId = wallId;
            StateId = stateId;
            Revision = revision;
            SignedEffort = signedEffort;
            ActiveTransition = activeTransition;
        }

        public int WallId { get; }
        public int StateId { get; }
        public uint Revision { get; }
        public int SignedEffort { get; }
        public WallTransition? ActiveTransition { get; }
        public bool IsTransitioning => ActiveTransition.HasValue;

        public WallPoseSample SamplePose(uint tick) => ActiveTransition.HasValue
            ? ActiveTransition.Value.Sample(tick)
            : WallPoseSample.Stable(StateId);

        public bool Equals(WallState other) =>
            WallId == other.WallId &&
            StateId == other.StateId &&
            Revision == other.Revision &&
            SignedEffort == other.SignedEffort &&
            Nullable.Equals(ActiveTransition, other.ActiveTransition);

        public override bool Equals(object value) => value is WallState other && Equals(other);
        public override int GetHashCode() => HashCode.Combine(
            WallId, StateId, Revision, SignedEffort, ActiveTransition);
    }

    public readonly struct WallTransitionRequest
    {
        public WallTransitionRequest(
            int wallId,
            int fromStateId,
            int toStateId,
            uint startTick,
            uint durationTicks,
            uint nextRevision)
        {
            WallId = wallId;
            FromStateId = fromStateId;
            ToStateId = toStateId;
            StartTick = startTick;
            DurationTicks = durationTicks;
            NextRevision = nextRevision;
        }

        public int WallId { get; }
        public int FromStateId { get; }
        public int ToStateId { get; }
        public uint StartTick { get; }
        public uint DurationTicks { get; }
        public uint NextRevision { get; }
    }

    public readonly struct WallTransitionGateDecision
    {
        private WallTransitionGateDecision(bool allowed, string rejectionCode)
        {
            Allowed = allowed;
            RejectionCode = rejectionCode;
        }

        public bool Allowed { get; }
        public string RejectionCode { get; }

        public static WallTransitionGateDecision Accept() => new(true, string.Empty);

        public static WallTransitionGateDecision Reject(string rejectionCode)
        {
            if (string.IsNullOrWhiteSpace(rejectionCode))
                throw new ArgumentException("Un refus doit porter un code stable.", nameof(rejectionCode));
            return new WallTransitionGateDecision(false, rejectionCode);
        }
    }
}
