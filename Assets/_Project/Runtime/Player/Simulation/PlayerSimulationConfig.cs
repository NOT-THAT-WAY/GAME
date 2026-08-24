using System;

namespace NotThatWay.Game.PlayerSimulation
{
    /// <summary>
    /// Paramètres explicites d'une simulation. Il n'existe volontairement aucun
    /// singleton ni preset implicite : le banc, puis le game design, choisissent les valeurs.
    /// </summary>
    public readonly struct PlayerSimulationConfig : IEquatable<PlayerSimulationConfig>
    {
        public PlayerSimulationConfig(
            double tickDurationSeconds,
            double playerHeightMeters,
            double playerRadiusMeters,
            double walkSpeedMetersPerSecond,
            double sprintSpeedMetersPerSecond,
            double groundAccelerationMetersPerSecondSquared,
            double airAccelerationMetersPerSecondSquared,
            double groundDecelerationMetersPerSecondSquared,
            double airDecelerationMetersPerSecondSquared,
            double gravityMetersPerSecondSquared,
            double groundedVelocityMetersPerSecond,
            bool jumpEnabled,
            double jumpSpeedMetersPerSecond,
            uint coyoteTicks,
            uint jumpBufferTicks,
            double knockbackDecayMetersPerSecondSquared,
            int maximumPitchCentidegrees,
            bool diveEnabled = false,
            double diveForwardSpeedMetersPerSecond = 0d,
            double diveUpwardSpeedMetersPerSecond = 0d,
            uint diveRecoveryTicks = 0u,
            uint diveCooldownTicks = 0u)
        {
            TickDurationSeconds = tickDurationSeconds;
            PlayerHeightMeters = playerHeightMeters;
            PlayerRadiusMeters = playerRadiusMeters;
            WalkSpeedMetersPerSecond = walkSpeedMetersPerSecond;
            SprintSpeedMetersPerSecond = sprintSpeedMetersPerSecond;
            GroundAccelerationMetersPerSecondSquared = groundAccelerationMetersPerSecondSquared;
            AirAccelerationMetersPerSecondSquared = airAccelerationMetersPerSecondSquared;
            GroundDecelerationMetersPerSecondSquared = groundDecelerationMetersPerSecondSquared;
            AirDecelerationMetersPerSecondSquared = airDecelerationMetersPerSecondSquared;
            GravityMetersPerSecondSquared = gravityMetersPerSecondSquared;
            GroundedVelocityMetersPerSecond = groundedVelocityMetersPerSecond;
            JumpEnabled = jumpEnabled;
            JumpSpeedMetersPerSecond = jumpSpeedMetersPerSecond;
            CoyoteTicks = coyoteTicks;
            JumpBufferTicks = jumpBufferTicks;
            KnockbackDecayMetersPerSecondSquared = knockbackDecayMetersPerSecondSquared;
            MaximumPitchCentidegrees = maximumPitchCentidegrees;
            DiveEnabled = diveEnabled;
            DiveForwardSpeedMetersPerSecond = diveForwardSpeedMetersPerSecond;
            DiveUpwardSpeedMetersPerSecond = diveUpwardSpeedMetersPerSecond;
            DiveRecoveryTicks = diveRecoveryTicks;
            DiveCooldownTicks = diveCooldownTicks;
            Validate();
        }

        public double TickDurationSeconds { get; }
        public double PlayerHeightMeters { get; }
        public double PlayerRadiusMeters { get; }
        public double WalkSpeedMetersPerSecond { get; }
        public double SprintSpeedMetersPerSecond { get; }
        public double GroundAccelerationMetersPerSecondSquared { get; }
        public double AirAccelerationMetersPerSecondSquared { get; }
        public double GroundDecelerationMetersPerSecondSquared { get; }
        public double AirDecelerationMetersPerSecondSquared { get; }
        public double GravityMetersPerSecondSquared { get; }
        public double GroundedVelocityMetersPerSecond { get; }
        public bool JumpEnabled { get; }
        public double JumpSpeedMetersPerSecond { get; }
        public uint CoyoteTicks { get; }
        public uint JumpBufferTicks { get; }
        public double KnockbackDecayMetersPerSecondSquared { get; }
        public int MaximumPitchCentidegrees { get; }

        /// <summary>
        /// Plongeon avant : une impulsion horizontale dans la direction du regard et
        /// une impulsion verticale, le contrôle coupé jusqu'à l'atterrissage, puis un
        /// relevé au sol pendant lequel le joueur ne se déplace pas. Comme le saut,
        /// c'est une baseline de banc tant que DEC-01 n'a pas tranché.
        /// </summary>
        public bool DiveEnabled { get; }
        public double DiveForwardSpeedMetersPerSecond { get; }
        public double DiveUpwardSpeedMetersPerSecond { get; }
        public uint DiveRecoveryTicks { get; }
        public uint DiveCooldownTicks { get; }

        /// <summary>
        /// Vitesse horizontale maximale qu'un état valide peut porter : le sprint, ou
        /// le plongeon s'il est activé et plus rapide.
        /// </summary>
        public double MaximumControlledSpeedMetersPerSecond =>
            DiveEnabled && DiveForwardSpeedMetersPerSecond > SprintSpeedMetersPerSecond
                ? DiveForwardSpeedMetersPerSecond
                : SprintSpeedMetersPerSecond;

        public void Validate()
        {
            EnsurePositiveFinite(TickDurationSeconds, nameof(TickDurationSeconds));
            EnsurePositiveFinite(PlayerHeightMeters, nameof(PlayerHeightMeters));
            EnsurePositiveFinite(PlayerRadiusMeters, nameof(PlayerRadiusMeters));
            if (PlayerHeightMeters < PlayerRadiusMeters * 2d)
            {
                throw new ArgumentOutOfRangeException(
                    nameof(PlayerHeightMeters),
                    "La hauteur de capsule doit être au moins égale à deux rayons.");
            }

            EnsureNonNegativeFinite(WalkSpeedMetersPerSecond, nameof(WalkSpeedMetersPerSecond));
            EnsureNonNegativeFinite(SprintSpeedMetersPerSecond, nameof(SprintSpeedMetersPerSecond));
            if (SprintSpeedMetersPerSecond < WalkSpeedMetersPerSecond)
            {
                throw new ArgumentOutOfRangeException(
                    nameof(SprintSpeedMetersPerSecond),
                    "La vitesse de sprint ne peut pas être inférieure à la marche.");
            }

            EnsureNonNegativeFinite(
                GroundAccelerationMetersPerSecondSquared,
                nameof(GroundAccelerationMetersPerSecondSquared));
            EnsureNonNegativeFinite(
                AirAccelerationMetersPerSecondSquared,
                nameof(AirAccelerationMetersPerSecondSquared));
            EnsureNonNegativeFinite(
                GroundDecelerationMetersPerSecondSquared,
                nameof(GroundDecelerationMetersPerSecondSquared));
            EnsureNonNegativeFinite(
                AirDecelerationMetersPerSecondSquared,
                nameof(AirDecelerationMetersPerSecondSquared));

            EnsureFinite(GravityMetersPerSecondSquared, nameof(GravityMetersPerSecondSquared));
            if (GravityMetersPerSecondSquared >= 0d)
                throw new ArgumentOutOfRangeException(nameof(GravityMetersPerSecondSquared));
            EnsureFinite(GroundedVelocityMetersPerSecond, nameof(GroundedVelocityMetersPerSecond));
            if (GroundedVelocityMetersPerSecond > 0d)
                throw new ArgumentOutOfRangeException(nameof(GroundedVelocityMetersPerSecond));

            EnsureNonNegativeFinite(JumpSpeedMetersPerSecond, nameof(JumpSpeedMetersPerSecond));
            if (JumpEnabled && JumpSpeedMetersPerSecond <= 0d)
                throw new ArgumentOutOfRangeException(nameof(JumpSpeedMetersPerSecond));
            EnsureNonNegativeFinite(
                KnockbackDecayMetersPerSecondSquared,
                nameof(KnockbackDecayMetersPerSecondSquared));
            if (MaximumPitchCentidegrees < 0 || MaximumPitchCentidegrees > 9000)
                throw new ArgumentOutOfRangeException(nameof(MaximumPitchCentidegrees));

            EnsureNonNegativeFinite(
                DiveForwardSpeedMetersPerSecond,
                nameof(DiveForwardSpeedMetersPerSecond));
            EnsureNonNegativeFinite(
                DiveUpwardSpeedMetersPerSecond,
                nameof(DiveUpwardSpeedMetersPerSecond));
            if (DiveEnabled && DiveForwardSpeedMetersPerSecond <= 0d)
                throw new ArgumentOutOfRangeException(nameof(DiveForwardSpeedMetersPerSecond));
            if (DiveEnabled && DiveUpwardSpeedMetersPerSecond <= 0d)
                throw new ArgumentOutOfRangeException(nameof(DiveUpwardSpeedMetersPerSecond));
        }

        public bool Equals(PlayerSimulationConfig other) =>
            TickDurationSeconds.Equals(other.TickDurationSeconds) &&
            PlayerHeightMeters.Equals(other.PlayerHeightMeters) &&
            PlayerRadiusMeters.Equals(other.PlayerRadiusMeters) &&
            WalkSpeedMetersPerSecond.Equals(other.WalkSpeedMetersPerSecond) &&
            SprintSpeedMetersPerSecond.Equals(other.SprintSpeedMetersPerSecond) &&
            GroundAccelerationMetersPerSecondSquared.Equals(
                other.GroundAccelerationMetersPerSecondSquared) &&
            AirAccelerationMetersPerSecondSquared.Equals(other.AirAccelerationMetersPerSecondSquared) &&
            GroundDecelerationMetersPerSecondSquared.Equals(
                other.GroundDecelerationMetersPerSecondSquared) &&
            AirDecelerationMetersPerSecondSquared.Equals(other.AirDecelerationMetersPerSecondSquared) &&
            GravityMetersPerSecondSquared.Equals(other.GravityMetersPerSecondSquared) &&
            GroundedVelocityMetersPerSecond.Equals(other.GroundedVelocityMetersPerSecond) &&
            JumpEnabled == other.JumpEnabled &&
            JumpSpeedMetersPerSecond.Equals(other.JumpSpeedMetersPerSecond) &&
            CoyoteTicks == other.CoyoteTicks &&
            JumpBufferTicks == other.JumpBufferTicks &&
            KnockbackDecayMetersPerSecondSquared.Equals(other.KnockbackDecayMetersPerSecondSquared) &&
            MaximumPitchCentidegrees == other.MaximumPitchCentidegrees &&
            DiveEnabled == other.DiveEnabled &&
            DiveForwardSpeedMetersPerSecond.Equals(other.DiveForwardSpeedMetersPerSecond) &&
            DiveUpwardSpeedMetersPerSecond.Equals(other.DiveUpwardSpeedMetersPerSecond) &&
            DiveRecoveryTicks == other.DiveRecoveryTicks &&
            DiveCooldownTicks == other.DiveCooldownTicks;

        public override bool Equals(object value) =>
            value is PlayerSimulationConfig other && Equals(other);

        public override int GetHashCode()
        {
            var hash = new HashCode();
            hash.Add(TickDurationSeconds);
            hash.Add(PlayerHeightMeters);
            hash.Add(PlayerRadiusMeters);
            hash.Add(WalkSpeedMetersPerSecond);
            hash.Add(SprintSpeedMetersPerSecond);
            hash.Add(GroundAccelerationMetersPerSecondSquared);
            hash.Add(AirAccelerationMetersPerSecondSquared);
            hash.Add(GroundDecelerationMetersPerSecondSquared);
            hash.Add(AirDecelerationMetersPerSecondSquared);
            hash.Add(GravityMetersPerSecondSquared);
            hash.Add(GroundedVelocityMetersPerSecond);
            hash.Add(JumpEnabled);
            hash.Add(JumpSpeedMetersPerSecond);
            hash.Add(CoyoteTicks);
            hash.Add(JumpBufferTicks);
            hash.Add(KnockbackDecayMetersPerSecondSquared);
            hash.Add(MaximumPitchCentidegrees);
            hash.Add(DiveEnabled);
            hash.Add(DiveForwardSpeedMetersPerSecond);
            hash.Add(DiveUpwardSpeedMetersPerSecond);
            hash.Add(DiveRecoveryTicks);
            hash.Add(DiveCooldownTicks);
            return hash.ToHashCode();
        }

        private static void EnsurePositiveFinite(double value, string parameterName)
        {
            EnsureFinite(value, parameterName);
            if (value <= 0d)
                throw new ArgumentOutOfRangeException(parameterName);
        }

        private static void EnsureNonNegativeFinite(double value, string parameterName)
        {
            EnsureFinite(value, parameterName);
            if (value < 0d)
                throw new ArgumentOutOfRangeException(parameterName);
        }

        private static void EnsureFinite(double value, string parameterName)
        {
            if (double.IsNaN(value) || double.IsInfinity(value))
                throw new ArgumentOutOfRangeException(parameterName);
        }
    }
}
