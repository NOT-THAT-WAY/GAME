using System;
using NotThatWay.Game.Simulation;

namespace NotThatWay.Game.PlayerSimulation
{
    /// <summary>
    /// Modificateurs bornés fournis par une règle de jeu extérieure (trophée,
    /// KO). La simulation de locomotion ne dépend ainsi d'aucun mode de jeu.
    /// </summary>
    public readonly struct PlayerTickModifiers : IEquatable<PlayerTickModifiers>
    {
        public const int PermilleScale = 1000;

        public PlayerTickModifiers(int movementSpeedPermille)
        {
            if (movementSpeedPermille < 0 || movementSpeedPermille > PermilleScale)
                throw new ArgumentOutOfRangeException(nameof(movementSpeedPermille));
            MovementSpeedPermille = movementSpeedPermille;
        }

        public int MovementSpeedPermille { get; }
        public static PlayerTickModifiers FullSpeed => new(PermilleScale);
        public bool Equals(PlayerTickModifiers other) =>
            MovementSpeedPermille == other.MovementSpeedPermille;
        public override bool Equals(object value) =>
            value is PlayerTickModifiers other && Equals(other);
        public override int GetHashCode() => MovementSpeedPermille;
    }

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

    /// <summary>
    /// Convertit une vitesse de poussée cible en correction d'impulsion. Seule la
    /// composante projetée sur la direction cible est remplacée : répéter la même
    /// poussée maintient la vitesse au lieu de l'additionner sans limite.
    /// </summary>
    internal static class PlayerPushVelocity
    {
        public static PlayerVector3 CorrectionToTarget(
            PlayerVector3 currentVelocity,
            PlayerVector3 pendingCorrection,
            PlayerVector3 targetVelocity)
        {
            PlayerState.EnsureHorizontal(currentVelocity, nameof(currentVelocity));
            PlayerState.EnsureHorizontal(pendingCorrection, nameof(pendingCorrection));
            PlayerState.EnsureHorizontal(targetVelocity, nameof(targetVelocity));

            var targetMagnitude = targetVelocity.HorizontalMagnitude;
            if (targetMagnitude <= 0d)
            {
                throw new ArgumentOutOfRangeException(
                    nameof(targetVelocity),
                    "La vitesse de poussée cible doit être non nulle.");
            }

            var directionX = targetVelocity.X / targetMagnitude;
            var directionZ = targetVelocity.Z / targetMagnitude;
            var effectiveVelocity = currentVelocity + pendingCorrection;
            var projectedVelocity = effectiveVelocity.X * directionX +
                                    effectiveVelocity.Z * directionZ;
            var correctionMagnitude = targetMagnitude - projectedVelocity;
            return new PlayerVector3(
                directionX * correctionMagnitude,
                0d,
                directionZ * correctionMagnitude);
        }
    }

    [Flags]
    public enum PlayerTickEvents : byte
    {
        None = 0,
        Jumped = 1 << 0,
        Landed = 1 << 1,
        LeftGround = 1 << 2,
        HitSides = 1 << 3,
        HitCeiling = 1 << 4,
        Dived = 1 << 5,
        DiveLanded = 1 << 6
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
            PlayerCommandButtons.JumpHeld |
            PlayerCommandButtons.DivePressed |
            PlayerCommandButtons.PunchHeld |
            PlayerCommandButtons.SlingshotHeld |
            PlayerCommandButtons.SlingshotPressed |
            PlayerCommandButtons.JumpPressed |
            PlayerCommandButtons.InteractPressed |
            PlayerCommandButtons.PunchPressed |
            PlayerCommandButtons.DropPressed |
            PlayerCommandButtons.SelectSlot1Pressed |
            PlayerCommandButtons.SelectSlot2Pressed |
            PlayerCommandButtons.SelectSlot3Pressed |
            PlayerCommandButtons.CycleSlotPressed;

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
            AdvanceTick(
                command,
                PlayerTickForces.None,
                PlayerTickModifiers.FullSpeed,
                collisionWorld);

        public PlayerTickResult AdvanceTick(
            PlayerCommand command,
            PlayerTickForces forces,
            IPlayerCollisionWorld collisionWorld) =>
            AdvanceTick(command, forces, PlayerTickModifiers.FullSpeed, collisionWorld);

        public PlayerTickResult AdvanceTick(
            PlayerCommand command,
            PlayerTickForces forces,
            PlayerTickModifiers modifiers,
            IPlayerCollisionWorld collisionWorld)
        {
            if (_isAdvancing)
                throw new InvalidOperationException("AdvanceTick joueur réentrant interdit.");

            _isAdvancing = true;
            try
            {
                return AdvanceTickCore(command, forces, modifiers, collisionWorld);
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
            PlayerTickModifiers modifiers,
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

            // Plongeon : seulement lancé depuis un sprint vers l'avant. Le vol coupe
            // le contrôle horizontal, le relevé au sol l'immobilise, et l'attente
            // empêche d'enchaîner. Tout est en ticks.
            var diveEnabled = _config.DiveEnabled;
            var wasDiving = diveEnabled && previous.IsDiving;
            var diveRecoveryTicks = diveEnabled ? previous.DiveRecoveryTicksRemaining : 0u;
            var diveCooldownTicks = diveEnabled ? previous.DiveCooldownTicksRemaining : 0u;
            var isRecovering = diveRecoveryTicks > 0u;
            var crawlEnabled = _config.CrawlEnabled;
            var wasCrawling = crawlEnabled && previous.IsCrawling;
            var dived = diveEnabled &&
                        command.Has(PlayerCommandButtons.DivePressed) &&
                        command.Has(PlayerCommandButtons.SprintHeld) &&
                        localZ > 0d &&
                        previous.IsGrounded &&
                        !wasDiving &&
                        !isRecovering &&
                        !wasCrawling &&
                        diveCooldownTicks == 0u &&
                        modifiers.MovementSpeedPermille > 0;
            var diveLocksControl = dived || wasDiving || isRecovering;

            // Ramper : la même touche que le plongeon, hors sprint, bascule à plat
            // ventre ; la même touche ou le saut relève. Décidé maintenant pour que
            // vitesse et capsule du tick soient déjà celles de la nouvelle posture.
            var isCrawling = wasCrawling;
            if (crawlEnabled && previous.IsGrounded && !diveLocksControl)
            {
                if (command.Has(PlayerCommandButtons.DivePressed) && !dived)
                    isCrawling = !wasCrawling;
                else if (wasCrawling &&
                         (command.Has(PlayerCommandButtons.JumpPressed) ||
                          command.Has(PlayerCommandButtons.JumpHeld)))
                {
                    isCrawling = false;
                }
            }

            PlayerVector3 horizontalVelocity;
            if (dived)
            {
                // Impulsion franche dans la direction du regard, sans passer par
                // l'accélération : c'est un bond, pas une course.
                horizontalVelocity = new PlayerVector3(yawSine, 0d, yawCosine) *
                                     _config.DiveForwardSpeedMetersPerSecond;
            }
            else if (wasDiving)
            {
                horizontalVelocity = previous.HorizontalVelocity;
            }
            else
            {
                var targetSpeed = isCrawling
                    ? _config.CrawlSpeedMetersPerSecond
                    : command.Has(PlayerCommandButtons.SprintHeld)
                        ? _config.SprintSpeedMetersPerSecond
                        : _config.WalkSpeedMetersPerSecond;
                targetSpeed *= modifiers.MovementSpeedPermille /
                               (double)PlayerTickModifiers.PermilleScale;
                var targetVelocity = isRecovering
                    ? PlayerVector3.Zero
                    : worldDirection * targetSpeed;
                var targetMagnitude = targetVelocity.HorizontalMagnitude;
                var currentMagnitude = previous.HorizontalVelocity.HorizontalMagnitude;
                var isDecelerating = IsMeaningfullyLower(targetMagnitude, currentMagnitude);
                var velocityChangeRate = SelectVelocityChangeRate(
                    previous.IsGrounded,
                    isDecelerating);
                horizontalVelocity = MoveToward(
                    previous.HorizontalVelocity,
                    targetVelocity,
                    velocityChangeRate * _config.TickDurationSeconds);
            }

            var knockbackVelocity = previous.KnockbackVelocity + forces.HorizontalVelocityDelta;
            // Saut tenu : garder Espace enfoncé vaut un appui à chaque tick, donc
            // on ressaute dès que le sol revient, sprint ou pas. Le front seul
            // reste suffisant pour un saut unique.
            var jumpAllowed = _config.JumpEnabled && !diveLocksControl && !wasCrawling;
            var jumpPressed = jumpAllowed &&
                              (command.Has(PlayerCommandButtons.JumpPressed) ||
                               command.Has(PlayerCommandButtons.JumpHeld));
            var coyoteTicks = jumpAllowed ? previous.CoyoteTicksRemaining : 0u;
            var jumpBufferTicks = jumpAllowed ? previous.JumpBufferTicksRemaining : 0u;
            var canUseGroundWindow = previous.IsGrounded || coyoteTicks > 0u;
            var hasBufferedJump = jumpBufferTicks > 0u;
            var jumped = jumpAllowed &&
                         canUseGroundWindow &&
                         (jumpPressed || hasBufferedJump);
            var bufferSetThisTick = false;
            if (jumpAllowed && jumpPressed && !jumped)
            {
                jumpBufferTicks = _config.JumpBufferTicks;
                bufferSetThisTick = jumpBufferTicks > 0u;
            }

            var verticalVelocity = dived
                ? _config.DiveUpwardSpeedMetersPerSecond
                : jumped
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
                isCrawling ? _config.CrawlHeightMeters : _config.PlayerHeightMeters,
                _config.PlayerRadiusMeters);
            var collisionResult = collisionWorld.Move(in collisionRequest);
            var flags = collisionResult.Flags;
            var grounded = collisionResult.IsGrounded;

            if ((flags & PlayerCollisionFlags.Above) != 0 && verticalVelocity > 0d)
                verticalVelocity = 0d;
            if (grounded)
                verticalVelocity = _config.GroundedVelocityMetersPerSecond;

            // Le plongeon se termine au premier contact avec le sol : le joueur
            // s'étale (vitesse horizontale annulée) puis se relève pendant
            // DiveRecoveryTicks. L'attente court depuis le lancement.
            var isDiving = dived || wasDiving;
            if (isDiving && grounded)
            {
                isDiving = false;
                horizontalVelocity = PlayerVector3.Zero;
                diveRecoveryTicks = _config.DiveRecoveryTicks;
            }
            else if (isRecovering)
            {
                diveRecoveryTicks--;
            }
            if (dived)
                diveCooldownTicks = _config.DiveCooldownTicks;
            else if (diveCooldownTicks > 0u)
                diveCooldownTicks--;

            var events = PlayerTickEvents.None;
            if (jumped)
                events |= PlayerTickEvents.Jumped;
            if (dived)
                events |= PlayerTickEvents.Dived;
            if ((dived || wasDiving) && !isDiving)
                events |= PlayerTickEvents.DiveLanded;
            if (!previous.IsGrounded && grounded)
                events |= PlayerTickEvents.Landed;
            if (previous.IsGrounded && !grounded)
                events |= PlayerTickEvents.LeftGround;
            if ((flags & PlayerCollisionFlags.Sides) != 0)
                events |= PlayerTickEvents.HitSides;
            if ((flags & PlayerCollisionFlags.Above) != 0)
                events |= PlayerTickEvents.HitCeiling;

            if (!jumpAllowed || jumped)
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
                jumpBufferTicks,
                isDiving,
                diveRecoveryTicks,
                diveCooldownTicks,
                isCrawling);
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
            var maximumSpeed = config.MaximumControlledSpeedMetersPerSecond;
            var velocityTolerance = Math.Max(
                VelocityValidationAbsoluteTolerance,
                maximumSpeed * VelocityValidationRelativeTolerance);
            if (state.HorizontalVelocity.HorizontalMagnitude > maximumSpeed + velocityTolerance)
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
            if (!config.DiveEnabled &&
                (state.IsDiving ||
                 state.DiveRecoveryTicksRemaining != 0u ||
                 state.DiveCooldownTicksRemaining != 0u))
            {
                throw new ArgumentException(
                    "Un état sans plongeon ne peut pas conserver de phase de plongeon.",
                    parameterName);
            }
            if (state.IsGrounded && state.IsDiving)
            {
                throw new ArgumentException(
                    "Un état au sol ne peut pas être en plein plongeon.",
                    parameterName);
            }
            if (state.IsDiving && state.DiveRecoveryTicksRemaining != 0u)
            {
                throw new ArgumentException(
                    "Un plongeon en vol ne peut pas déjà être en relevé.",
                    parameterName);
            }
            if (state.DiveRecoveryTicksRemaining > config.DiveRecoveryTicks)
            {
                throw new ArgumentOutOfRangeException(
                    parameterName,
                    "Le relevé de plongeon dépasse le réglage de simulation.");
            }
            if (state.DiveCooldownTicksRemaining > config.DiveCooldownTicks)
            {
                throw new ArgumentOutOfRangeException(
                    parameterName,
                    "L'attente de plongeon dépasse le réglage de simulation.");
            }
            if (!config.CrawlEnabled && state.IsCrawling)
            {
                throw new ArgumentException(
                    "Un état sans ramper ne peut pas être à plat ventre.",
                    parameterName);
            }
            if (state.IsCrawling && state.IsDiving)
            {
                throw new ArgumentException(
                    "Un état ne peut pas ramper et plonger à la fois.",
                    parameterName);
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
