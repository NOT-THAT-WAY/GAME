using System;

namespace NotThatWay.Game.PlayerSimulation
{
    [Flags]
    public enum PlayerCollisionFlags : byte
    {
        None = 0,
        Sides = 1 << 0,
        Above = 1 << 1,
        Below = 1 << 2
    }

    public readonly struct PlayerCollisionRequest : IEquatable<PlayerCollisionRequest>
    {
        public PlayerCollisionRequest(
            uint tick,
            PlayerVector3 startPosition,
            PlayerVector3 desiredDisplacement,
            int yawCentidegrees,
            double playerHeightMeters,
            double playerRadiusMeters)
        {
            if (yawCentidegrees < 0 || yawCentidegrees >= PlayerState.FullYawCentidegrees)
                throw new ArgumentOutOfRangeException(nameof(yawCentidegrees));
            if (playerHeightMeters <= 0d || double.IsNaN(playerHeightMeters) ||
                double.IsInfinity(playerHeightMeters))
            {
                throw new ArgumentOutOfRangeException(nameof(playerHeightMeters));
            }
            if (playerRadiusMeters <= 0d || double.IsNaN(playerRadiusMeters) ||
                double.IsInfinity(playerRadiusMeters))
            {
                throw new ArgumentOutOfRangeException(nameof(playerRadiusMeters));
            }

            Tick = tick;
            StartPosition = startPosition;
            DesiredDisplacement = desiredDisplacement;
            YawCentidegrees = yawCentidegrees;
            PlayerHeightMeters = playerHeightMeters;
            PlayerRadiusMeters = playerRadiusMeters;
        }

        public uint Tick { get; }
        public PlayerVector3 StartPosition { get; }
        public PlayerVector3 DesiredDisplacement { get; }
        public int YawCentidegrees { get; }
        public double PlayerHeightMeters { get; }
        public double PlayerRadiusMeters { get; }

        public bool Equals(PlayerCollisionRequest other) =>
            Tick == other.Tick &&
            StartPosition.Equals(other.StartPosition) &&
            DesiredDisplacement.Equals(other.DesiredDisplacement) &&
            YawCentidegrees == other.YawCentidegrees &&
            PlayerHeightMeters.Equals(other.PlayerHeightMeters) &&
            PlayerRadiusMeters.Equals(other.PlayerRadiusMeters);

        public override bool Equals(object value) =>
            value is PlayerCollisionRequest other && Equals(other);

        public override int GetHashCode() => HashCode.Combine(
            Tick,
            StartPosition,
            DesiredDisplacement,
            YawCentidegrees,
            PlayerHeightMeters,
            PlayerRadiusMeters);
    }

    public readonly struct PlayerCollisionResult : IEquatable<PlayerCollisionResult>
    {
        private const PlayerCollisionFlags KnownFlags =
            PlayerCollisionFlags.Sides |
            PlayerCollisionFlags.Above |
            PlayerCollisionFlags.Below;

        public PlayerCollisionResult(PlayerVector3 resolvedPosition, PlayerCollisionFlags flags)
        {
            if ((flags & ~KnownFlags) != 0)
                throw new ArgumentOutOfRangeException(nameof(flags));
            ResolvedPosition = resolvedPosition;
            Flags = flags;
        }

        public PlayerVector3 ResolvedPosition { get; }
        public PlayerCollisionFlags Flags { get; }
        public bool IsGrounded => (Flags & PlayerCollisionFlags.Below) != 0;

        public bool Equals(PlayerCollisionResult other) =>
            ResolvedPosition.Equals(other.ResolvedPosition) && Flags == other.Flags;

        public override bool Equals(object value) =>
            value is PlayerCollisionResult other && Equals(other);

        public override int GetHashCode() => HashCode.Combine(ResolvedPosition, Flags);
    }

    /// <summary>
    /// Frontière unique vers la collision réelle. Move doit retourner la position
    /// effectivement résolue et n'est appelé qu'une fois pour chaque tick accepté.
    /// </summary>
    public interface IPlayerCollisionWorld
    {
        PlayerCollisionResult Move(in PlayerCollisionRequest request);
    }
}
