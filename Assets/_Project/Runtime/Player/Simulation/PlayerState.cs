using System;

namespace NotThatWay.Game.PlayerSimulation
{
    /// <summary>
    /// État intégral nécessaire pour reprendre ou réconcilier la simulation à un tick.
    /// Les vitesses horizontales ont toujours Y=0 ; la verticale reste un scalaire séparé.
    /// </summary>
    public readonly struct PlayerState : IEquatable<PlayerState>
    {
        public const int FullYawCentidegrees = 36000;
        public const int PhysicalPitchLimitCentidegrees = 9000;

        public PlayerState(
            uint tick,
            PlayerVector3 position,
            int yawCentidegrees,
            int pitchCentidegrees,
            PlayerVector3 horizontalVelocity,
            double verticalVelocity,
            PlayerVector3 knockbackVelocity,
            bool isGrounded,
            uint coyoteTicksRemaining = 0u,
            uint jumpBufferTicksRemaining = 0u)
        {
            if (yawCentidegrees < 0 || yawCentidegrees >= FullYawCentidegrees)
                throw new ArgumentOutOfRangeException(nameof(yawCentidegrees));
            if (pitchCentidegrees < -PhysicalPitchLimitCentidegrees ||
                pitchCentidegrees > PhysicalPitchLimitCentidegrees)
            {
                throw new ArgumentOutOfRangeException(nameof(pitchCentidegrees));
            }
            EnsureHorizontal(horizontalVelocity, nameof(horizontalVelocity));
            EnsureFinite(verticalVelocity, nameof(verticalVelocity));
            EnsureHorizontal(knockbackVelocity, nameof(knockbackVelocity));

            Tick = tick;
            Position = position;
            YawCentidegrees = yawCentidegrees;
            PitchCentidegrees = pitchCentidegrees;
            HorizontalVelocity = horizontalVelocity;
            VerticalVelocity = verticalVelocity;
            KnockbackVelocity = knockbackVelocity;
            IsGrounded = isGrounded;
            CoyoteTicksRemaining = coyoteTicksRemaining;
            JumpBufferTicksRemaining = jumpBufferTicksRemaining;
        }

        public uint Tick { get; }
        public PlayerVector3 Position { get; }
        public int YawCentidegrees { get; }
        public int PitchCentidegrees { get; }
        public PlayerVector3 HorizontalVelocity { get; }
        public double VerticalVelocity { get; }
        public PlayerVector3 KnockbackVelocity { get; }
        public bool IsGrounded { get; }
        public uint CoyoteTicksRemaining { get; }
        public uint JumpBufferTicksRemaining { get; }

        public bool Equals(PlayerState other) =>
            Tick == other.Tick &&
            Position.Equals(other.Position) &&
            YawCentidegrees == other.YawCentidegrees &&
            PitchCentidegrees == other.PitchCentidegrees &&
            HorizontalVelocity.Equals(other.HorizontalVelocity) &&
            VerticalVelocity.Equals(other.VerticalVelocity) &&
            KnockbackVelocity.Equals(other.KnockbackVelocity) &&
            IsGrounded == other.IsGrounded &&
            CoyoteTicksRemaining == other.CoyoteTicksRemaining &&
            JumpBufferTicksRemaining == other.JumpBufferTicksRemaining;

        public override bool Equals(object value) => value is PlayerState other && Equals(other);

        public override int GetHashCode()
        {
            var hash = new HashCode();
            hash.Add(Tick);
            hash.Add(Position);
            hash.Add(YawCentidegrees);
            hash.Add(PitchCentidegrees);
            hash.Add(HorizontalVelocity);
            hash.Add(VerticalVelocity);
            hash.Add(KnockbackVelocity);
            hash.Add(IsGrounded);
            hash.Add(CoyoteTicksRemaining);
            hash.Add(JumpBufferTicksRemaining);
            return hash.ToHashCode();
        }

        internal static void EnsureHorizontal(PlayerVector3 value, string parameterName)
        {
            if (value.Y != 0d)
            {
                throw new ArgumentException(
                    "Une vitesse horizontale doit avoir une composante Y exactement nulle.",
                    parameterName);
            }
        }

        private static void EnsureFinite(double value, string parameterName)
        {
            if (double.IsNaN(value) || double.IsInfinity(value))
                throw new ArgumentOutOfRangeException(parameterName);
        }
    }
}
