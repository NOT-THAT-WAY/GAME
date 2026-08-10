using System;

namespace NotThatWay.Game.Simulation
{
    /// <summary>
    /// Pose logique d'un battant à un tick donné. C'est le seul objet que le rendu
    /// et la collision consomment : l'angle vient toujours d'un tick, jamais d'une
    /// image ni d'une heure d'arrivée locale.
    /// </summary>
    public readonly struct WallPoseSample : IEquatable<WallPoseSample>
    {
        public WallPoseSample(
            int angleMilliDegrees,
            int angularVelocityMilliDegreesPerTick,
            uint elapsedTicks,
            bool isRotating)
        {
            if (angleMilliDegrees < 0 || angleMilliDegrees >= FixedTrigonometry.FullTurnMilliDegrees)
                throw new ArgumentOutOfRangeException(nameof(angleMilliDegrees));

            AngleMilliDegrees = angleMilliDegrees;
            AngularVelocityMilliDegreesPerTick = angularVelocityMilliDegreesPerTick;
            ElapsedTicks = elapsedTicks;
            IsRotating = isRotating;
        }

        public int AngleMilliDegrees { get; }
        public int AngularVelocityMilliDegreesPerTick { get; }

        /// <summary>Ticks écoulés depuis l'ancrage, déjà borné par l'extrapolation.</summary>
        public uint ElapsedTicks { get; }

        public bool IsRotating { get; }

        public static WallPoseSample Stable(int angleMilliDegrees) =>
            new(angleMilliDegrees, 0, 0u, false);

        public bool Equals(WallPoseSample other) =>
            AngleMilliDegrees == other.AngleMilliDegrees &&
            AngularVelocityMilliDegreesPerTick == other.AngularVelocityMilliDegreesPerTick &&
            ElapsedTicks == other.ElapsedTicks &&
            IsRotating == other.IsRotating;

        public override bool Equals(object value) => value is WallPoseSample other && Equals(other);

        public override int GetHashCode() => HashCode.Combine(
            AngleMilliDegrees, AngularVelocityMilliDegreesPerTick, ElapsedTicks, IsRotating);
    }
}
