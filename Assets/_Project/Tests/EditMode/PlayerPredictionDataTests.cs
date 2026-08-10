using System;
using NotThatWay.Game.PlayerNetwork;
using NotThatWay.Game.PlayerSimulation;
using NUnit.Framework;

namespace NotThatWay.Game.Tests.EditMode
{
    public sealed class PlayerPredictionDataTests
    {
        [Test]
        public void ReplicateData_UsesFishNetTickOnlyAsTransportMetadata()
        {
            var source = new PlayerCommand(
                77u,
                64,
                -12,
                250,
                -125,
                PlayerCommandButtons.SprintHeld |
                PlayerCommandButtons.JumpPressed |
                PlayerCommandButtons.PunchPressed);
            var data = new PlayerReplicateData(source);

            Assert.That(data.GetTick(), Is.Zero);
            data.SetTick(900u);
            var command = data.ToCommand(12u);

            Assert.That(data.GetTick(), Is.EqualTo(900u));
            Assert.That(command.Tick, Is.EqualTo(12u));
            Assert.That(command.MoveX, Is.EqualTo(64));
            Assert.That(command.MoveY, Is.EqualTo(-12));
            Assert.That(command.LookYaw, Is.EqualTo(250));
            Assert.That(command.LookPitch, Is.EqualTo(-125));
            Assert.That(command.Buttons, Is.EqualTo(source.Buttons));
        }

        [Test]
        public void FutureReplicate_KeepsHeldIntentButNeverRepeatsEdgesOrLook()
        {
            var source = new PlayerCommand(
                1u,
                127,
                0,
                500,
                -300,
                PlayerCommandButtons.SprintHeld |
                PlayerCommandButtons.InteractHeld |
                PlayerCommandButtons.JumpPressed |
                PlayerCommandButtons.InteractPressed |
                PlayerCommandButtons.PunchPressed);
            var data = new PlayerReplicateData(source);
            data.SetTick(42u);

            var future = data.WithoutOneShotInputs();

            Assert.That(future.GetTick(), Is.EqualTo(42u));
            Assert.That(future.MoveX, Is.EqualTo(127));
            Assert.That(future.LookYaw, Is.Zero);
            Assert.That(future.LookPitch, Is.Zero);
            Assert.That(
                (PlayerCommandButtons)future.Buttons,
                Is.EqualTo(PlayerCommandButtons.SprintHeld | PlayerCommandButtons.InteractHeld));
            Assert.That(data.LookYaw, Is.EqualTo(500), "Le DTO source reste immuable par copie.");
        }

        [Test]
        public void ReconcileData_RoundTripsCompleteStateAndKeepsTicksSeparate()
        {
            var state = new PlayerState(
                123u,
                new PlayerVector3(1.25d, 2.5d, -3.75d),
                35999,
                -4321,
                new PlayerVector3(3.5d, 0d, -2.25d),
                -8.5d,
                new PlayerVector3(-1.5d, 0d, 0.75d),
                false,
                2u,
                3u);
            var data = new PlayerReconcileData(state);
            data.SetTick(987u);

            var restored = data.ToState();

            Assert.That(data.GetTick(), Is.EqualTo(987u), "Tick de transport FishNet.");
            Assert.That(restored.Tick, Is.EqualTo(123u), "Tick logique PLY-01.");
            Assert.That(restored.Position.X, Is.EqualTo(state.Position.X).Within(0.000001d));
            Assert.That(restored.Position.Y, Is.EqualTo(state.Position.Y).Within(0.000001d));
            Assert.That(restored.Position.Z, Is.EqualTo(state.Position.Z).Within(0.000001d));
            Assert.That(restored.YawCentidegrees, Is.EqualTo(state.YawCentidegrees));
            Assert.That(restored.PitchCentidegrees, Is.EqualTo(state.PitchCentidegrees));
            Assert.That(
                restored.HorizontalVelocity.X,
                Is.EqualTo(state.HorizontalVelocity.X).Within(0.000001d));
            Assert.That(restored.VerticalVelocity, Is.EqualTo(state.VerticalVelocity).Within(0.000001d));
            Assert.That(
                restored.KnockbackVelocity.Z,
                Is.EqualTo(state.KnockbackVelocity.Z).Within(0.000001d));
            Assert.That(restored.IsGrounded, Is.False);
            Assert.That(restored.CoyoteTicksRemaining, Is.EqualTo(2u));
            Assert.That(restored.JumpBufferTicksRemaining, Is.EqualTo(3u));
        }

        [Test]
        public void ReconcileData_RejectsValuesThatCannotFitTheWireFormat()
        {
            var state = new PlayerState(
                1u,
                new PlayerVector3(double.MaxValue, 0d, 0d),
                0,
                0,
                PlayerVector3.Zero,
                0d,
                PlayerVector3.Zero,
                false);

            Assert.That(
                () => new PlayerReconcileData(state),
                Throws.TypeOf<ArgumentOutOfRangeException>());
        }

        [Test]
        public void M1Automation_ParsesExplicitProfilesAndEmitsTickBoundCommands()
        {
            Assert.That(
                M1AutomatedCommandSource.TryParseArguments(
                    new[] { "GAME", "--m1-auto-player=clear-sweep" },
                    out var mover,
                    out var error),
                Is.True,
                error);
            Assert.That(mover.CreateCommand(45u).MoveY, Is.EqualTo(127));
            Assert.That(mover.CreateCommand(46u).MoveY, Is.Zero);
            Assert.That(mover.WasSpecified, Is.True);

            Assert.That(
                M1AutomatedCommandSource.TryParseArguments(
                    new[] { "GAME", "--m1-auto-player", "interact-120" },
                    out var pusher,
                    out error),
                Is.True,
                error);
            Assert.That(
                pusher.CreateCommand(119u).Has(PlayerCommandButtons.InteractHeld),
                Is.False);
            Assert.That(
                pusher.CreateCommand(120u).Has(PlayerCommandButtons.InteractHeld),
                Is.True);
            Assert.That(
                pusher.CreateCommand(164u).Has(PlayerCommandButtons.InteractHeld),
                Is.True);
            Assert.That(
                pusher.CreateCommand(165u).Has(PlayerCommandButtons.InteractHeld),
                Is.True,
                "Le seuil d'une porte lourde se compte en secondes : l'appui doit " +
                "rester tenu, une fenêtre fixe le manquerait.");

            // Un pousseur immobile perd le contact dès que le battant s'écarte :
            // le profil d'accompagnement marche en même temps qu'il pousse.
            Assert.That(
                M1AutomatedCommandSource.TryParseArguments(
                    new[] { "GAME", "--m1-auto-player=push-left" },
                    out var follower,
                    out error),
                Is.True,
                error);
            Assert.That(follower.Name, Is.EqualTo("push-left"));
            Assert.That(follower.CreateCommand(0u).MoveX, Is.EqualTo(-127));
            Assert.That(
                follower.CreateCommand(89u).Has(PlayerCommandButtons.InteractHeld),
                Is.False);
            Assert.That(follower.CreateCommand(89u).LookYaw, Is.Zero);
            Assert.That(
                follower.CreateCommand(90u).Has(PlayerCommandButtons.InteractHeld),
                Is.True);
            Assert.That(
                follower.CreateCommand(90u).LookYaw,
                Is.EqualTo(28),
                "Le lacet suit la porte : sans lui le pousseur perd le contact. " +
                "La valeur suit la vitesse du battant, 280 mdeg/tick au réglage " +
                "courant, et se recalcule avec elle.");
            // Amplitude réduite au contact : le surplus de vitesse ne pousse pas
            // plus fort, il fait glisser le pousseur jusqu'à contourner le battant.
            Assert.That(follower.CreateCommand(600u).MoveX, Is.EqualTo(-24));
            // Puis relâchement, une fois le quart de tour acquis : un pousseur qui
            // maintient indéfiniment finit sur l'autre face et contre-pousse sa
            // propre porte.
            Assert.That(follower.CreateCommand(610u).MoveX, Is.Zero);
            Assert.That(
                follower.CreateCommand(610u).Has(PlayerCommandButtons.InteractHeld),
                Is.False,
                "Passé la fenêtre de poussée, le pousseur automatisé lâche le mur.");

            Assert.That(
                M1AutomatedCommandSource.TryParseArguments(
                    new[] { "GAME", "--m1-auto-player=push-right" },
                    out var mirrored,
                    out error),
                Is.True,
                error);
            Assert.That(mirrored.CreateCommand(120u).MoveX, Is.EqualTo(24));
            Assert.That(mirrored.CreateCommand(120u).LookYaw, Is.EqualTo(-28));

            Assert.That(
                M1AutomatedCommandSource.TryParseArguments(
                    new[] { "GAME", "--m1-auto-player=unknown" },
                    out _,
                    out error),
                Is.False);
            Assert.That(error, Is.EqualTo("profile_unknown"));

            Assert.That(
                M1AutomatedCommandSource.TryParseArguments(
                    new[] { "GAME" }, out var absent, out error),
                Is.True,
                error);
            Assert.That(absent.WasSpecified, Is.False);
        }
    }
}
