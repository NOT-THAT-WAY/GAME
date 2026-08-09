using System;
using NotThatWay.Game.Simulation;

namespace NotThatWay.Game.PlayerSimulation
{
    public readonly struct PlayerTickForces : IEquatable<PlayerTickForces>
    {
        public PlayerTickForces(PlayerVector3 horizontalVelocityDelta)
        {
            PlayerState.EnsureHorizontal(horizontalVelocityDelta, nameof(horizontalVelocityDelta));
            HorizontalVelocityDelta = horizontalVelocityDelta;
        }

        public PlayerVector3 HorizontalVelocityDelta { get; }
        public static PlayerTickForces None => default;

        public bool Equals(PlayerTickForces other) =>
            HorizontalVelocityDelta.Equals(other.HorizontalVelocityDelta);

        public override bool Equals(object value) => value is PlayerTickForces other && Equals(other);
        public override int GetHashCode() => HorizontalVelocityDelta.GetHashCode();
    }

    [Flags]
    public enum PlayerTickEvents : byte
    {
        None = 0,
        Jumped = 1 << 0,
        Landed = 1 << 1,
        LeftGround = 1 << 2,
        HitSides = 1 << 3,
        HitCeiling = 1 << 4
    }

    public readonly struct PlayerTickResult
    {
        internal PlayerTickResult(
            PlayerState previous,
            PlayerState current,
            PlayerCollisionRequest collisionRequest,
            PlayerCollisionResult collisionResult,
            PlayerTickEvents events)
        {
            Previous = previous;
            Current = current;
            CollisionRequest = collisionRequest;
            CollisionResult = collisionResult;
            Events = events;
        }

        public uint Tick => Current.Tick;
        public PlayerState Previous { get; }
        public PlayerState Current { get; }
        public PlayerCollisionRequest CollisionRequest { get; }
        public PlayerCollisionResult CollisionResult { get; }
        public PlayerTickEvents Events { get; }
    }

    /// <summary>
    /// Simulation joueur par ticks contigus. Elle calcule une intention de déplacement,
    /// délègue exactement une résolution au monde de collision, puis publie l'état atomiquement.
    /// Le serveur reste la référence : cette couche ne promet pas PhysX bit-identique entre OS.
    /// </summary>
    public sealed class PlayerStateMachine
    {
        // Tolérance purement numérique pour le round-trip futur double → float FishNet → double.
        // Un écart d'un millionième ne constitue ni une marge gameplay ni une tolérance anti-triche.
        private const double VelocityValidationRelativeTolerance = 0.000001d;
        private const double VelocityValidationAbsoluteTolerance = 0.000001d;

        private const PlayerCommandButtons KnownButtons =
            PlayerCommandButtons.SprintHeld |
            PlayerCommandButtons.InteractHeld |
            PlayerCommandButtons.JumpPressed |
            PlayerCommandButtons.InteractPressed |
            PlayerCommandButtons.PunchPressed;

        private readonly PlayerSimulationConfig _config;
        private PlayerState _state;
        private bool _isAdvancing;

        public PlayerStateMachine(PlayerSimulationConfig config, PlayerState initialState)
        {
            config.Validate();
            ValidateState(config, initialState, nameof(initialState));
            _config = config;
            _state = initialState;
        }

        public PlayerSimulationConfig Config => _config;
        public PlayerState State => _state;
        public uint LastProcessedTick => _state.Tick;

        public PlayerTickResult AdvanceTick(
            PlayerCommand command,
            IPlayerCollisionWorld collisionWorld) =>
            AdvanceTick(command, PlayerTickForces.None, collisionWorld);

        public PlayerTickResult AdvanceTick(
            PlayerCommand command,
            PlayerTickForces forces,
            IPlayerCollisionWorld collisionWorld)
        {
            if (_isAdvancing)
                throw new InvalidOperationException("AdvanceTick joueur réentrant interdit.");

            _isAdvancing = true;
            try
            {
                return AdvanceTickCore(command, forces, collisionWorld);
            }
            finally
            {
                _isAdvancing = false;
            }
        }

        public void RestoreState(PlayerState state)
        {
            if (_isAdvancing)
                throw new InvalidOperationException("Réconciliation interdite pendant AdvanceTick.");
            ValidateState(_config, state, nameof(state));
            _state = state;
        }

        private PlayerTickResult AdvanceTickCore(
            PlayerCommand command,
            PlayerTickForces forces,
            IPlayerCollisionWorld collisionWorld)
        {
            ValidateCommand(command);
            if (!TickMath.IsNext(command.Tick, _state.Tick))
            {
                throw new InvalidOperationException(
                    $"Tick joueur non contigu: reçu {command.Tick}, " +
                    $"attendu {TickMath.Next(_state.Tick)}.");
            }
            if (collisionWorld == null)
                throw new ArgumentNullException(nameof(collisionWorld));

            var previous = _state;
            var yaw = NormalizeYaw(previous.YawCentidegrees + command.LookYaw);
            var pitch = Clamp(
                previous.PitchCentidegrees + command.LookPitch,
                -_config.MaximumPitchCentidegrees,
                _config.MaximumPitchCentidegrees);

            DecodeMovement(command, out var localX, out var localZ);
            var yawRadians = yaw / 100d * Math.PI / 180d;
            var yawCosine = Math.Cos(yawRadians);
            var yawSine = Math.Sin(yawRadians);
            var worldDirection = new PlayerVector3(
                localX * yawCosine + localZ * yawSine,
                0d,
                localZ * yawCosine - localX * yawSine);
            var targetSpeed = command.Has(PlayerCommandButtons.SprintHeld)
                ? _config.SprintSpeedMetersPerSecond
                : _config.WalkSpeedMetersPerSecond;
            var targetVelocity = worldDirection * targetSpeed;
            var targetMagnitude = targetVelocity.HorizontalMagnitude;
            var currentMagnitude = previous.HorizontalVelocity.HorizontalMagnitude;
            var isDecelerating = IsMeaningfullyLower(targetMagnitude, currentMagnitude);
            var velocityChangeRate = SelectVelocityChangeRate(
                previous.IsGrounded,
                isDecelerating);
            var horizontalVelocity = MoveToward(
                previous.HorizontalVelocity,
                targetVelocity,
                velocityChangeRate * _config.TickDurationSeconds);

            var knockbackVelocity = previous.KnockbackVelocity + forces.HorizontalVelocityDelta;
            var jumpPressed = command.Has(PlayerCommandButtons.JumpPressed);
            var coyoteTicks = _config.JumpEnabled ? previous.CoyoteTicksRemaining : 0u;
            var jumpBufferTicks = _config.JumpEnabled ? previous.JumpBufferTicksRemaining : 0u;
            var canUseGroundWindow = previous.IsGrounded || coyoteTicks > 0u;
            var hasBufferedJump = jumpBufferTicks > 0u;
            var jumped = _config.JumpEnabled &&
                         canUseGroundWindow &&
                         (jumpPressed || hasBufferedJump);
            var bufferSetThisTick = false;
            if (_config.JumpEnabled && jumpPressed && !jumped)
            {
                jumpBufferTicks = _config.JumpBufferTicks;
                bufferSetThisTick = jumpBufferTicks > 0u;
            }

            var verticalVelocity = jumped
                ? _config.JumpSpeedMetersPerSecond
                : previous.VerticalVelocity;
            verticalVelocity +=
                _config.GravityMetersPerSecondSquared * _config.TickDurationSeconds;

            var totalVelocity = new PlayerVector3(
                horizontalVelocity.X + knockbackVelocity.X,
                verticalVelocity,
                horizontalVelocity.Z + knockbackVelocity.Z);
            var collisionRequest = new PlayerCollisionRequest(
                command.Tick,
                previous.Position,
                totalVelocity * _config.TickDurationSeconds,
                yaw,
                _config.PlayerHeightMeters,
                _config.PlayerRadiusMeters);
            var collisionResult = collisionWorld.Move(in collisionRequest);
            var flags = collisionResult.Flags;
            var grounded = collisionResult.IsGrounded;

            if ((flags & PlayerCollisionFlags.Above) != 0 && verticalVelocity > 0d)
                verticalVelocity = 0d;
            if (grounded)
                verticalVelocity = _config.GroundedVelocityMetersPerSecond;

            var events = PlayerTickEvents.None;
            if (jumped)
                events |= PlayerTickEvents.Jumped;
            if (!previous.IsGrounded && grounded)
                events |= PlayerTickEvents.Landed;
            if (previous.IsGrounded && !grounded)
                events |= PlayerTickEvents.LeftGround;
            if ((flags & PlayerCollisionFlags.Sides) != 0)
                events |= PlayerTickEvents.HitSides;
            if ((flags & PlayerCollisionFlags.Above) != 0)
                events |= PlayerTickEvents.HitCeiling;

            if (!_config.JumpEnabled || jumped)
            {
                coyoteTicks = 0u;
                jumpBufferTicks = 0u;
            }
            else
            {
                if (previous.IsGrounded && !grounded)
                    coyoteTicks = _config.CoyoteTicks;
                else if (!grounded && coyoteTicks > 0u)
                    coyoteTicks--;
                else if (grounded)
                    coyoteTicks = 0u;

                if (!grounded && jumpBufferTicks > 0u && !bufferSetThisTick)
                    jumpBufferTicks--;
            }

            knockbackVelocity = MoveToward(
                knockbackVelocity,
                PlayerVector3.Zero,
                _config.KnockbackDecayMetersPerSecondSquared *
                _config.TickDurationSeconds);

            var current = new PlayerState(
                command.Tick,
                collisionResult.ResolvedPosition,
                yaw,
                pitch,
                horizontalVelocity,
                verticalVelocity,
                knockbackVelocity,
                grounded,
                coyoteTicks,
                jumpBufferTicks);
            _state = current;
            return new PlayerTickResult(
                previous,
                current,
                collisionRequest,
                collisionResult,
                events);
        }

        private double SelectVelocityChangeRate(bool grounded, bool isDecelerating)
        {
            if (grounded)
            {
                return isDecelerating
                    ? _config.GroundDecelerationMetersPerSecondSquared
                    : _config.GroundAccelerationMetersPerSecondSquared;
            }

            return isDecelerating
                ? _config.AirDecelerationMetersPerSecondSquared
                : _config.AirAccelerationMetersPerSecondSquared;
        }

        private static void DecodeMovement(
            PlayerCommand command,
            out double localX,
            out double localZ)
        {
            localX = PlayerCommandEncoder.DecodeAxis(command.MoveX);
            localZ = PlayerCommandEncoder.DecodeAxis(command.MoveY);
            var magnitude = Math.Sqrt(localX * localX + localZ * localZ);
            if (magnitude > 1d)
            {
                localX /= magnitude;
                localZ /= magnitude;
            }
        }

        private static PlayerVector3 MoveToward(
            PlayerVector3 current,
            PlayerVector3 target,
            double maximumDelta)
        {
            var deltaX = target.X - current.X;
            var deltaZ = target.Z - current.Z;
            var distance = Math.Sqrt(deltaX * deltaX + deltaZ * deltaZ);
            if (distance == 0d || distance <= maximumDelta)
                return target;
            if (maximumDelta == 0d)
                return current;
            var scale = maximumDelta / distance;
            return new PlayerVector3(
                current.X + deltaX * scale,
                0d,
                current.Z + deltaZ * scale);
        }

        private static bool IsMeaningfullyLower(double candidate, double reference)
        {
            var tolerance = Math.Max(
                VelocityValidationAbsoluteTolerance,
                Math.Max(candidate, reference) * VelocityValidationRelativeTolerance);
            return candidate + tolerance < reference;
        }

        private static void ValidateCommand(PlayerCommand command)
        {
            if (command.MoveX == sbyte.MinValue || command.MoveY == sbyte.MinValue)
            {
                throw new ArgumentOutOfRangeException(
                    nameof(command),
                    "Les axes réseau utilisent exclusivement [-127, 127].");
            }
            if ((command.Buttons & ~KnownButtons) != 0)
            {
                throw new ArgumentOutOfRangeException(
                    nameof(command),
                    "La commande contient des bits de boutons inconnus.");
            }
        }

        private static void ValidateState(
            PlayerSimulationConfig config,
            PlayerState state,
            string parameterName)
        {
            var velocityTolerance = Math.Max(
                VelocityValidationAbsoluteTolerance,
                config.SprintSpeedMetersPerSecond * VelocityValidationRelativeTolerance);
            if (state.HorizontalVelocity.HorizontalMagnitude >
                config.SprintSpeedMetersPerSecond + velocityTolerance)
            {
                throw new ArgumentOutOfRangeException(
                    parameterName,
                    "La vitesse contrôlée de l'état dépasse la vitesse maximale configurée.");
            }
            if (state.IsGrounded && state.VerticalVelocity > 0d)
            {
                throw new ArgumentException(
                    "Un état au sol ne peut pas avoir une vitesse verticale positive.",
                    parameterName);
            }
            if (state.IsGrounded && state.CoyoteTicksRemaining != 0u)
            {
                throw new ArgumentException(
                    "Un état au sol ne peut pas conserver une fenêtre coyote.",
                    parameterName);
            }
            if (state.PitchCentidegrees < -config.MaximumPitchCentidegrees ||
                state.PitchCentidegrees > config.MaximumPitchCentidegrees)
            {
                throw new ArgumentOutOfRangeException(
                    parameterName,
                    "Le pitch de l'état dépasse le réglage de simulation.");
            }
            if (!config.JumpEnabled &&
                (state.CoyoteTicksRemaining != 0u || state.JumpBufferTicksRemaining != 0u))
            {
                throw new ArgumentException(
                    "Un état sans saut ne peut pas conserver de fenêtre de saut.",
                    parameterName);
            }
            if (state.CoyoteTicksRemaining > config.CoyoteTicks)
            {
                throw new ArgumentOutOfRangeException(
                    parameterName,
                    "La fenêtre coyote dépasse le réglage de simulation.");
            }
            if (state.JumpBufferTicksRemaining > config.JumpBufferTicks)
            {
                throw new ArgumentOutOfRangeException(
                    parameterName,
                    "Le buffer de saut dépasse le réglage de simulation.");
            }
        }

        private static int NormalizeYaw(int value)
        {
            value %= PlayerState.FullYawCentidegrees;
            return value < 0 ? value + PlayerState.FullYawCentidegrees : value;
        }

        private static int Clamp(int value, int minimum, int maximum) =>
            value < minimum ? minimum : value > maximum ? maximum : value;
    }
}
