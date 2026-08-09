using System;

namespace NotThatWay.Game.Simulation
{
    public readonly struct WallPoseSample : IEquatable<WallPoseSample>
    {
        internal WallPoseSample(
            int fromStateId,
            int toStateId,
            uint elapsedTicks,
            uint durationTicks,
            ushort progressQ16,
            bool isTransitioning)
        {
            FromStateId = fromStateId;
            ToStateId = toStateId;
            ElapsedTicks = elapsedTicks;
            DurationTicks = durationTicks;
            ProgressQ16 = progressQ16;
            IsTransitioning = isTransitioning;
        }

        public int FromStateId { get; }
        public int ToStateId { get; }
        public uint ElapsedTicks { get; }
        public uint DurationTicks { get; }
        public ushort ProgressQ16 { get; }
        public bool IsTransitioning { get; }

        public static WallPoseSample Stable(int stateId) =>
            new(stateId, stateId, 0u, 0u, TickMath.CompleteProgressQ16, false);

        public bool Equals(WallPoseSample other) =>
            FromStateId == other.FromStateId &&
            ToStateId == other.ToStateId &&
            ElapsedTicks == other.ElapsedTicks &&
            DurationTicks == other.DurationTicks &&
            ProgressQ16 == other.ProgressQ16 &&
            IsTransitioning == other.IsTransitioning;

        public override bool Equals(object value) => value is WallPoseSample other && Equals(other);
        public override int GetHashCode() => HashCode.Combine(
            FromStateId, ToStateId, ElapsedTicks, DurationTicks, ProgressQ16, IsTransitioning);
    }

    public readonly struct WallTransition : IEquatable<WallTransition>
    {
        public WallTransition(
            int wallId,
            int fromStateId,
            int toStateId,
            uint startTick,
            uint durationTicks,
            uint revision)
        {
            if (wallId <= 0)
                throw new ArgumentOutOfRangeException(nameof(wallId));
            if (fromStateId < 0)
                throw new ArgumentOutOfRangeException(nameof(fromStateId));
            if (toStateId < 0 || toStateId == fromStateId)
                throw new ArgumentOutOfRangeException(nameof(toStateId));
            TickMath.ValidateDuration(durationTicks);

            WallId = wallId;
            FromStateId = fromStateId;
            ToStateId = toStateId;
            StartTick = startTick;
            DurationTicks = durationTicks;
            Revision = revision;
        }

        public int WallId { get; }
        public int FromStateId { get; }
        public int ToStateId { get; }
        public uint StartTick { get; }
        public uint DurationTicks { get; }
        public uint Revision { get; }

        public bool IsComplete(uint tick) => TickMath.HasElapsed(StartTick, DurationTicks, tick);

        public WallPoseSample Sample(uint tick)
        {
            var elapsed = TickMath.Elapsed(StartTick, tick);
            if (elapsed > DurationTicks)
                elapsed = DurationTicks;
            return new WallPoseSample(
                FromStateId,
                ToStateId,
                elapsed,
                DurationTicks,
                TickMath.ProgressQ16(StartTick, DurationTicks, tick),
                !IsComplete(tick));
        }

        public bool Equals(WallTransition other) =>
            WallId == other.WallId &&
            FromStateId == other.FromStateId &&
            ToStateId == other.ToStateId &&
            StartTick == other.StartTick &&
            DurationTicks == other.DurationTicks &&
            Revision == other.Revision;

        public override bool Equals(object value) => value is WallTransition other && Equals(other);
        public override int GetHashCode() => HashCode.Combine(
            WallId, FromStateId, ToStateId, StartTick, DurationTicks, Revision);
    }
}
