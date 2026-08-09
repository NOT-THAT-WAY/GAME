using System;
using NotThatWay.Game.PlayerSimulation;
using NUnit.Framework;

namespace NotThatWay.Game.Tests.EditMode
{
    public sealed class PlayerSimulationTests
    {
        private const double Tolerance = 0.000000001d;

        [Test]
        public void ConfigAndState_RejectInvalidOrImplicitValues()
        {
            Assert.That(
                () => new PlayerStateMachine(default, InitialState()),
                Throws.TypeOf<ArgumentOutOfRangeException>());
            Assert.That(
                () => Config(height: 0.9d, radius: 0.5d),
                Throws.TypeOf<ArgumentOutOfRangeException>());
            Assert.That(
                () => Config(walkSpeed: 5d, sprintSpeed: 4d),
                Throws.TypeOf<ArgumentOutOfRangeException>());
            Assert.That(
                () => Config(jumpEnabled: true, jumpSpeed: 0d),
                Throws.TypeOf<ArgumentOutOfRangeException>());
            Assert.That(
                () => new PlayerState(
                    0u,
                    PlayerVector3.Zero,
                    0,
                    0,
                    new PlayerVector3(0d, 1d, 0d),
                    0d,
                    PlayerVector3.Zero,
                    false),
                Throws.TypeOf<ArgumentException>());
            Assert.That(
                () => new PlayerStateMachine(
                    Config(jumpEnabled: false),
                    InitialState(coyoteTicks: 1u)),
                Throws.TypeOf<ArgumentException>());
            Assert.That(
                () => new PlayerStateMachine(
                    Config(),
                    InitialState(grounded: true, verticalVelocity: 1d)),
                Throws.TypeOf<ArgumentException>());
            Assert.That(
                () => new PlayerStateMachine(
                    Config(),
                    InitialState(horizontalVelocity: new PlayerVector3(9d, 0d, 0d))),
                Throws.TypeOf<ArgumentOutOfRangeException>());
        }

        [Test]
        public void AdvanceTick_CallsCollisionOnceAndUsesItsResolvedPosition()
        {
            var world = new PassThroughWorld(PlayerCollisionFlags.Below);
            var simulation = new PlayerStateMachine(
                Config(),
                InitialState(
                    position: new PlayerVector3(4d, 2d, -3d),
                    grounded: true,
                    verticalVelocity: -2d));

            var result = simulation.AdvanceTick(Command(1u), world);

            Assert.That(world.CallCount, Is.EqualTo(1));
            Assert.That(result.CollisionRequest.StartPosition, Is.EqualTo(new PlayerVector3(4d, 2d, -3d)));
            Assert.That(result.CollisionRequest.DesiredDisplacement.Y, Is.EqualTo(-0.3d).Within(Tolerance));
            Assert.That(result.Current.Position, Is.EqualTo(world.LastResult.ResolvedPosition));
            Assert.That(result.Current.IsGrounded, Is.True);
            Assert.That(result.Current.VerticalVelocity, Is.EqualTo(-2d));
            Assert.That(simulation.State, Is.EqualTo(result.Current));
        }

        [Test]
        public void AdvanceTick_RequiresContiguousTicksIncludingUnsignedWrap()
        {
            var world = new PassThroughWorld(PlayerCollisionFlags.None);
            var simulation = new PlayerStateMachine(
                Config(),
                InitialState(tick: uint.MaxValue - 1u));

            Assert.That(
                () => simulation.AdvanceTick(Command(0u), world),
                Throws.TypeOf<InvalidOperationException>());
            Assert.That(simulation.State.Tick, Is.EqualTo(uint.MaxValue - 1u));
            simulation.AdvanceTick(Command(uint.MaxValue), world);
            simulation.AdvanceTick(Command(0u), world);
            Assert.That(simulation.State.Tick, Is.Zero);
            Assert.That(
                () => simulation.AdvanceTick(Command(0u), world),
                Throws.TypeOf<InvalidOperationException>());
            Assert.That(
                () => simulation.AdvanceTick(Command(2u), world),
                Throws.TypeOf<InvalidOperationException>());
            Assert.That(world.CallCount, Is.EqualTo(2));
        }

        [Test]
        public void Look_IsAppliedBeforeMovementAndPitchIsClamped()
        {
            var world = new PassThroughWorld(PlayerCollisionFlags.None);
            var simulation = new PlayerStateMachine(Config(), InitialState(grounded: true));

            var result = simulation.AdvanceTick(
                Command(1u, moveY: 127, lookYaw: 9000, lookPitch: 9000),
                world);

            Assert.That(result.Current.YawCentidegrees, Is.EqualTo(9000));
            Assert.That(result.Current.PitchCentidegrees, Is.EqualTo(8000));
            Assert.That(result.Current.HorizontalVelocity.X, Is.EqualTo(4d).Within(Tolerance));
            Assert.That(result.Current.HorizontalVelocity.Z, Is.EqualTo(0d).Within(Tolerance));
            Assert.That(result.CollisionRequest.DesiredDisplacement.X, Is.EqualTo(0.4d).Within(Tolerance));
        }

        [Test]
        public void Movement_NormalizesForgedDiagonalAndSprintChangesOnlyTargetSpeed()
        {
            var walking = new PlayerStateMachine(Config(), InitialState(grounded: true));
            var sprinting = new PlayerStateMachine(Config(), InitialState(grounded: true));
            var walkingWorld = new PassThroughWorld(PlayerCollisionFlags.Below);
            var sprintingWorld = new PassThroughWorld(PlayerCollisionFlags.Below);

            var walk = walking.AdvanceTick(Command(1u, moveX: 127, moveY: 127), walkingWorld);
            var sprint = sprinting.AdvanceTick(
                Command(
                    1u,
                    moveX: 127,
                    moveY: 127,
                    buttons: PlayerCommandButtons.SprintHeld),
                sprintingWorld);

            Assert.That(walk.Current.HorizontalVelocity.HorizontalMagnitude, Is.EqualTo(4d).Within(Tolerance));
            Assert.That(sprint.Current.HorizontalVelocity.HorizontalMagnitude, Is.EqualTo(8d).Within(Tolerance));
            Assert.That(
                sprint.Current.HorizontalVelocity.X,
                Is.EqualTo(sprint.Current.HorizontalVelocity.Z).Within(Tolerance));

            var angled = new PlayerStateMachine(Config(), InitialState(grounded: true));
            var angledWorld = new PassThroughWorld(PlayerCollisionFlags.Below);
            angled.AdvanceTick(
                Command(
                    1u,
                    moveX: 64,
                    moveY: 127,
                    lookYaw: -15,
                    buttons: PlayerCommandButtons.SprintHeld),
                angledWorld);
            Assert.That(
                () => new PlayerStateMachine(Config(), angled.State),
                Throws.Nothing,
                "Un état produit avec trigonométrie doit être restaurable après round-trip réseau.");
            var restored = new PlayerStateMachine(Config(), InitialState());
            Assert.That(() => restored.RestoreState(angled.State), Throws.Nothing);
        }

        [Test]
        public void AccelerationAndDeceleration_ComeOnlyFromSuppliedConfig()
        {
            var slow = new PlayerStateMachine(
                Config(groundAcceleration: 2d, groundDeceleration: 1d),
                InitialState(grounded: true));
            var fast = new PlayerStateMachine(
                Config(groundAcceleration: 6d, groundDeceleration: 4d),
                InitialState(grounded: true));
            var slowWorld = new PassThroughWorld(PlayerCollisionFlags.Below);
            var fastWorld = new PassThroughWorld(PlayerCollisionFlags.Below);

            slow.AdvanceTick(Command(1u, moveY: 127), slowWorld);
            fast.AdvanceTick(Command(1u, moveY: 127), fastWorld);
            Assert.That(slow.State.HorizontalVelocity.Z, Is.EqualTo(0.2d).Within(Tolerance));
            Assert.That(fast.State.HorizontalVelocity.Z, Is.EqualTo(0.6d).Within(Tolerance));

            slow.AdvanceTick(Command(2u), slowWorld);
            fast.AdvanceTick(Command(2u), fastWorld);
            Assert.That(slow.State.HorizontalVelocity.Z, Is.EqualTo(0.1d).Within(Tolerance));
            Assert.That(fast.State.HorizontalVelocity.Z, Is.EqualTo(0.2d).Within(Tolerance));

            var releaseSprint = new PlayerStateMachine(
                Config(groundAcceleration: 2d, groundDeceleration: 10d),
                InitialState(
                    horizontalVelocity: new PlayerVector3(0d, 0d, 8d),
                    grounded: true));
            releaseSprint.AdvanceTick(
                Command(1u, moveY: 127),
                new PassThroughWorld(PlayerCollisionFlags.Below));
            Assert.That(
                releaseSprint.State.HorizontalVelocity.Z,
                Is.EqualTo(7d).Within(Tolerance),
                "Relâcher le sprint utilise la décélération, même si le stick reste tenu.");

            var reduceStick = new PlayerStateMachine(
                Config(groundAcceleration: 2d, groundDeceleration: 10d),
                InitialState(
                    horizontalVelocity: new PlayerVector3(0d, 0d, 4d),
                    grounded: true));
            reduceStick.AdvanceTick(
                Command(1u, moveY: 64),
                new PassThroughWorld(PlayerCollisionFlags.Below));
            Assert.That(
                reduceStick.State.HorizontalVelocity.Z,
                Is.EqualTo(3d).Within(Tolerance),
                "Réduire le stick utilise la décélération configurée.");

            var accelerateInAir = new PlayerStateMachine(
                Config(airAcceleration: 3d, airDeceleration: 7d),
                InitialState());
            accelerateInAir.AdvanceTick(
                Command(1u, moveY: 127),
                new PassThroughWorld(PlayerCollisionFlags.None));
            Assert.That(
                accelerateInAir.State.HorizontalVelocity.Z,
                Is.EqualTo(0.3d).Within(Tolerance));

            var decelerateInAir = new PlayerStateMachine(
                Config(airAcceleration: 3d, airDeceleration: 7d),
                InitialState(horizontalVelocity: new PlayerVector3(0d, 0d, 4d)));
            decelerateInAir.AdvanceTick(
                Command(1u, moveY: 64),
                new PassThroughWorld(PlayerCollisionFlags.None));
            Assert.That(
                decelerateInAir.State.HorizontalVelocity.Z,
                Is.EqualTo(3.3d).Within(Tolerance));
        }

        [Test]
        public void CollisionFlags_ResolveVerticalVelocityAndStableEvents()
        {
            var returnedPosition = new PlayerVector3(9d, 8d, 7d);
            var world = new ScriptedWorld(
                new PlayerCollisionResult(
                    returnedPosition,
                    PlayerCollisionFlags.Above | PlayerCollisionFlags.Sides),
                new PlayerCollisionResult(
                    new PlayerVector3(9d, 0d, 7d),
                    PlayerCollisionFlags.Below));
            var simulation = new PlayerStateMachine(
                Config(),
                InitialState(verticalVelocity: 5d));

            var ceiling = simulation.AdvanceTick(Command(1u), world);
            Assert.That(ceiling.Current.Position, Is.EqualTo(returnedPosition));
            Assert.That(ceiling.Current.VerticalVelocity, Is.Zero);
            Assert.That(ceiling.Events.HasFlag(PlayerTickEvents.HitCeiling), Is.True);
            Assert.That(ceiling.Events.HasFlag(PlayerTickEvents.HitSides), Is.True);

            var landing = simulation.AdvanceTick(Command(2u), world);
            Assert.That(landing.Current.IsGrounded, Is.True);
            Assert.That(landing.Current.VerticalVelocity, Is.EqualTo(-2d));
            Assert.That(landing.Events.HasFlag(PlayerTickEvents.Landed), Is.True);
            Assert.That(world.CallCount, Is.EqualTo(2));
        }

        [Test]
        public void JumpDisabled_IgnoresInputAndKeepsNoWindows()
        {
            var world = new PassThroughWorld(PlayerCollisionFlags.None);
            var simulation = new PlayerStateMachine(
                Config(jumpEnabled: false, jumpSpeed: 0d, coyoteTicks: 3u, bufferTicks: 3u),
                InitialState(grounded: true));

            var result = simulation.AdvanceTick(
                Command(1u, buttons: PlayerCommandButtons.JumpPressed),
                world);

            Assert.That(result.Events.HasFlag(PlayerTickEvents.Jumped), Is.False);
            Assert.That(result.Current.VerticalVelocity, Is.EqualTo(-1d).Within(Tolerance));
            Assert.That(result.Current.CoyoteTicksRemaining, Is.Zero);
            Assert.That(result.Current.JumpBufferTicksRemaining, Is.Zero);
        }

        [Test]
        public void CoyoteWindow_HasExactConfiguredFutureTickCount()
        {
            var config = Config(jumpEnabled: true, coyoteTicks: 2u, bufferTicks: 0u);
            var world = new PassThroughWorld(PlayerCollisionFlags.None);
            var simulation = new PlayerStateMachine(config, InitialState(grounded: true));

            simulation.AdvanceTick(Command(1u), world);
            Assert.That(simulation.State.CoyoteTicksRemaining, Is.EqualTo(2u));
            simulation.AdvanceTick(Command(2u), world);
            Assert.That(simulation.State.CoyoteTicksRemaining, Is.EqualTo(1u));
            var lastAllowed = simulation.AdvanceTick(
                Command(3u, buttons: PlayerCommandButtons.JumpPressed),
                world);
            Assert.That(lastAllowed.Events.HasFlag(PlayerTickEvents.Jumped), Is.True);

            var expired = new PlayerStateMachine(config, InitialState(grounded: true));
            expired.AdvanceTick(Command(1u), world);
            expired.AdvanceTick(Command(2u), world);
            expired.AdvanceTick(Command(3u), world);
            var rejected = expired.AdvanceTick(
                Command(4u, buttons: PlayerCommandButtons.JumpPressed),
                world);
            Assert.That(rejected.Events.HasFlag(PlayerTickEvents.Jumped), Is.False);
            Assert.That(rejected.Current.JumpBufferTicksRemaining, Is.Zero);
        }

        [Test]
        public void JumpBuffer_IsPreservedOnLandingAndConsumedNextTick()
        {
            var world = new ScriptedWorld(
                PassThroughResult(InitialState().Position, -0.1d, PlayerCollisionFlags.None),
                new PlayerCollisionResult(PlayerVector3.Zero, PlayerCollisionFlags.Below),
                new PlayerCollisionResult(PlayerVector3.Zero, PlayerCollisionFlags.None));
            var simulation = new PlayerStateMachine(
                Config(jumpEnabled: true, coyoteTicks: 0u, bufferTicks: 2u),
                InitialState());

            simulation.AdvanceTick(
                Command(1u, buttons: PlayerCommandButtons.JumpPressed),
                world);
            Assert.That(simulation.State.JumpBufferTicksRemaining, Is.EqualTo(2u));
            var landing = simulation.AdvanceTick(Command(2u), world);
            Assert.That(landing.Events.HasFlag(PlayerTickEvents.Landed), Is.True);
            Assert.That(simulation.State.JumpBufferTicksRemaining, Is.EqualTo(2u));
            var bufferedJump = simulation.AdvanceTick(Command(3u), world);
            Assert.That(bufferedJump.Events.HasFlag(PlayerTickEvents.Jumped), Is.True);
            Assert.That(bufferedJump.Current.JumpBufferTicksRemaining, Is.Zero);
            Assert.That(bufferedJump.CollisionRequest.DesiredDisplacement.Y, Is.GreaterThan(0d));

            var expiryWorld = new ScriptedWorld(
                default,
                default,
                default,
                new PlayerCollisionResult(PlayerVector3.Zero, PlayerCollisionFlags.Below),
                default);
            var expiry = new PlayerStateMachine(
                Config(jumpEnabled: true, coyoteTicks: 0u, bufferTicks: 2u),
                InitialState());
            expiry.AdvanceTick(
                Command(1u, buttons: PlayerCommandButtons.JumpPressed),
                expiryWorld);
            Assert.That(expiry.State.JumpBufferTicksRemaining, Is.EqualTo(2u));
            expiry.AdvanceTick(Command(2u), expiryWorld);
            Assert.That(expiry.State.JumpBufferTicksRemaining, Is.EqualTo(1u));
            expiry.AdvanceTick(Command(3u), expiryWorld);
            Assert.That(expiry.State.JumpBufferTicksRemaining, Is.Zero);
            expiry.AdvanceTick(Command(4u), expiryWorld);
            var afterExpiry = expiry.AdvanceTick(Command(5u), expiryWorld);
            Assert.That(afterExpiry.Events.HasFlag(PlayerTickEvents.Jumped), Is.False);

            var lastTickWorld = new ScriptedWorld(
                default,
                default,
                new PlayerCollisionResult(PlayerVector3.Zero, PlayerCollisionFlags.Below),
                default);
            var lastTick = new PlayerStateMachine(
                Config(jumpEnabled: true, coyoteTicks: 0u, bufferTicks: 2u),
                InitialState());
            lastTick.AdvanceTick(
                Command(1u, buttons: PlayerCommandButtons.JumpPressed),
                lastTickWorld);
            lastTick.AdvanceTick(Command(2u), lastTickWorld);
            lastTick.AdvanceTick(Command(3u), lastTickWorld);
            Assert.That(lastTick.State.JumpBufferTicksRemaining, Is.EqualTo(1u));
            var jumpOnLastValidTick = lastTick.AdvanceTick(Command(4u), lastTickWorld);
            Assert.That(jumpOnLastValidTick.Events.HasFlag(PlayerTickEvents.Jumped), Is.True);
        }

        [Test]
        public void KnockbackImpulse_MovesThisTickThenDecaysForFollowingTicks()
        {
            var world = new PassThroughWorld(PlayerCollisionFlags.None);
            var simulation = new PlayerStateMachine(
                Config(
                    walkSpeed: 0d,
                    sprintSpeed: 0d,
                    knockbackDecay: 10d),
                InitialState());

            var impulse = simulation.AdvanceTick(
                Command(1u),
                new PlayerTickForces(new PlayerVector3(4d, 0d, 0d)),
                world);
            Assert.That(impulse.CollisionRequest.DesiredDisplacement.X, Is.EqualTo(0.4d).Within(Tolerance));
            Assert.That(impulse.Current.KnockbackVelocity.X, Is.EqualTo(3d).Within(Tolerance));

            var decay = simulation.AdvanceTick(Command(2u), world);
            Assert.That(decay.CollisionRequest.DesiredDisplacement.X, Is.EqualTo(0.3d).Within(Tolerance));
            Assert.That(decay.Current.KnockbackVelocity.X, Is.EqualTo(2d).Within(Tolerance));
        }

        [Test]
        public void RestoreState_ReplacesEveryReconciledFieldAndTickOrigin()
        {
            var simulation = new PlayerStateMachine(Config(jumpEnabled: true), InitialState());
            var restored = new PlayerState(
                50u,
                new PlayerVector3(1d, 2d, 3d),
                35900,
                -4000,
                new PlayerVector3(2d, 0d, 3d),
                -4d,
                new PlayerVector3(-1d, 0d, 2d),
                false,
                1u,
                2u);

            simulation.RestoreState(restored);

            Assert.That(simulation.State, Is.EqualTo(restored));
            var invalid = InitialState(
                tick: 99u,
                horizontalVelocity: new PlayerVector3(9d, 0d, 0d));
            Assert.That(
                () => simulation.RestoreState(invalid),
                Throws.TypeOf<ArgumentOutOfRangeException>());
            Assert.That(simulation.State, Is.EqualTo(restored),
                "Un restore invalide ne doit modifier aucun champ ni le tick courant.");
            var next = simulation.AdvanceTick(
                Command(51u, lookYaw: 200),
                new PassThroughWorld(PlayerCollisionFlags.None));
            Assert.That(next.Previous, Is.EqualTo(restored));
            Assert.That(next.Current.YawCentidegrees, Is.EqualTo(100));
        }

        [Test]
        public void StateSamplingBetweenTicks_DoesNotChangeSimulationTrace()
        {
            var expected = RunTrace(samplesPerTick: 0);

            Assert.That(RunTrace(samplesPerTick: 1), Is.EqualTo(expected));
            Assert.That(RunTrace(samplesPerTick: 4), Is.EqualTo(expected));
            Assert.That(RunTrace(samplesPerTick: 12), Is.EqualTo(expected));
        }

        [Test]
        public void MalformedCommands_AreRejectedAtomicallyBeforeCollision()
        {
            var world = new PassThroughWorld(PlayerCollisionFlags.None);
            var initial = InitialState();
            var simulation = new PlayerStateMachine(Config(), initial);

            Assert.That(
                () => simulation.AdvanceTick(
                    Command(1u, moveX: sbyte.MinValue),
                    world),
                Throws.TypeOf<ArgumentOutOfRangeException>());
            Assert.That(
                () => simulation.AdvanceTick(
                    Command(1u, buttons: (PlayerCommandButtons)(1 << 15)),
                    world),
                Throws.TypeOf<ArgumentOutOfRangeException>());
            Assert.That(world.CallCount, Is.Zero);
            Assert.That(simulation.State, Is.EqualTo(initial));
        }

        [Test]
        public void ReentrantAdvanceAndRestore_AreRejectedAndGuardAlwaysResets()
        {
            var simulation = new PlayerStateMachine(Config(), InitialState());
            var nestedAdvance = new DelegateWorld(_ =>
            {
                simulation.AdvanceTick(
                    Command(1u),
                    new PassThroughWorld(PlayerCollisionFlags.None));
                return default;
            });

            Assert.That(
                () => simulation.AdvanceTick(Command(1u), nestedAdvance),
                Throws.TypeOf<InvalidOperationException>());
            Assert.That(simulation.State.Tick, Is.Zero);

            var nestedRestore = new DelegateWorld(request =>
            {
                simulation.RestoreState(InitialState(tick: request.Tick));
                return default;
            });
            Assert.That(
                () => simulation.AdvanceTick(Command(1u), nestedRestore),
                Throws.TypeOf<InvalidOperationException>());
            Assert.That(simulation.State.Tick, Is.Zero);

            simulation.AdvanceTick(Command(1u), new PassThroughWorld(PlayerCollisionFlags.None));
            Assert.That(simulation.State.Tick, Is.EqualTo(1u));
        }

        [Test]
        public void CollisionFailure_DoesNotPublishPartialState()
        {
            var initial = InitialState(yaw: 1000, grounded: true);
            var simulation = new PlayerStateMachine(Config(), initial);
            var world = new DelegateWorld(_ => throw new InvalidOperationException("fixture"));

            Assert.That(
                () => simulation.AdvanceTick(
                    Command(1u, moveY: 127, lookYaw: 500),
                    world),
                Throws.TypeOf<InvalidOperationException>());
            Assert.That(simulation.State, Is.EqualTo(initial));
        }

        private static PlayerState RunTrace(int samplesPerTick)
        {
            var simulation = new PlayerStateMachine(Config(), InitialState(grounded: true));
            var world = new PassThroughWorld(PlayerCollisionFlags.Below);
            for (uint tick = 1u; tick <= 20u; tick++)
            {
                simulation.AdvanceTick(
                    Command(
                        tick,
                        moveX: tick % 3u == 0u ? (sbyte)64 : (sbyte)0,
                        moveY: 127,
                        lookYaw: 125,
                        buttons: tick > 10u
                            ? PlayerCommandButtons.SprintHeld
                            : PlayerCommandButtons.None),
                    world);
                for (var sample = 0; sample < samplesPerTick; sample++)
                    _ = simulation.State;
            }

            return simulation.State;
        }

        private static PlayerSimulationConfig Config(
            double tickDuration = 0.1d,
            double height = 1.8d,
            double radius = 0.4d,
            double walkSpeed = 4d,
            double sprintSpeed = 8d,
            double groundAcceleration = 100d,
            double airAcceleration = 50d,
            double groundDeceleration = 100d,
            double airDeceleration = 25d,
            double gravity = -10d,
            double groundedVelocity = -2d,
            bool jumpEnabled = false,
            double jumpSpeed = 6d,
            uint coyoteTicks = 2u,
            uint bufferTicks = 2u,
            double knockbackDecay = 5d,
            int maximumPitch = 8000) =>
            new(
                tickDuration,
                height,
                radius,
                walkSpeed,
                sprintSpeed,
                groundAcceleration,
                airAcceleration,
                groundDeceleration,
                airDeceleration,
                gravity,
                groundedVelocity,
                jumpEnabled,
                jumpSpeed,
                coyoteTicks,
                bufferTicks,
                knockbackDecay,
                maximumPitch);

        private static PlayerState InitialState(
            uint tick = 0u,
            PlayerVector3 position = default,
            int yaw = 0,
            int pitch = 0,
            PlayerVector3 horizontalVelocity = default,
            double verticalVelocity = 0d,
            PlayerVector3 knockbackVelocity = default,
            bool grounded = false,
            uint coyoteTicks = 0u,
            uint bufferTicks = 0u) =>
            new(
                tick,
                position,
                yaw,
                pitch,
                horizontalVelocity,
                verticalVelocity,
                knockbackVelocity,
                grounded,
                coyoteTicks,
                bufferTicks);

        private static PlayerCommand Command(
            uint tick,
            sbyte moveX = 0,
            sbyte moveY = 0,
            short lookYaw = 0,
            short lookPitch = 0,
            PlayerCommandButtons buttons = PlayerCommandButtons.None) =>
            new(tick, moveX, moveY, lookYaw, lookPitch, buttons);

        private static PlayerCollisionResult PassThroughResult(
            PlayerVector3 start,
            double yDisplacement,
            PlayerCollisionFlags flags) =>
            new(
                start + new PlayerVector3(0d, yDisplacement, 0d),
                flags);

        private sealed class PassThroughWorld : IPlayerCollisionWorld
        {
            private readonly PlayerCollisionFlags _flags;

            public PassThroughWorld(PlayerCollisionFlags flags)
            {
                _flags = flags;
            }

            public int CallCount { get; private set; }
            public PlayerCollisionRequest LastRequest { get; private set; }
            public PlayerCollisionResult LastResult { get; private set; }

            public PlayerCollisionResult Move(in PlayerCollisionRequest request)
            {
                CallCount++;
                LastRequest = request;
                LastResult = new PlayerCollisionResult(
                    request.StartPosition + request.DesiredDisplacement,
                    _flags);
                return LastResult;
            }
        }

        private sealed class ScriptedWorld : IPlayerCollisionWorld
        {
            private readonly PlayerCollisionResult[] _results;

            public ScriptedWorld(params PlayerCollisionResult[] results)
            {
                _results = results;
            }

            public int CallCount { get; private set; }

            public PlayerCollisionResult Move(in PlayerCollisionRequest request)
            {
                if (CallCount >= _results.Length)
                    throw new InvalidOperationException("Fixture collision épuisée.");
                return _results[CallCount++];
            }
        }

        private sealed class DelegateWorld : IPlayerCollisionWorld
        {
            private readonly Func<PlayerCollisionRequest, PlayerCollisionResult> _move;

            public DelegateWorld(Func<PlayerCollisionRequest, PlayerCollisionResult> move)
            {
                _move = move;
            }

            public PlayerCollisionResult Move(in PlayerCollisionRequest request) => _move(request);
        }
    }
}
