using System;
using NotThatWay.Game.PlayerSimulation;
using NotThatWay.Game.Sandbox;
using NUnit.Framework;

namespace NotThatWay.Game.Tests.EditMode
{
    public sealed class SandboxCommandContextTests
    {
        private const int Scale = SandboxGameplayConfig.PermilleScale;

        private static PlayerCommand Command(
            uint tick = 1u,
            sbyte moveX = 40,
            sbyte moveY = 100,
            PlayerCommandButtons buttons = PlayerCommandButtons.None) =>
            new(tick, moveX, moveY, 1234, -560, buttons);

        private static SandboxCommandContext Context(
            bool alive = true,
            bool hasTrophy = false,
            bool canSprint = true,
            bool hasSlingshotInHand = false,
            int movementPermille = Scale,
            int aimMovementPermille = 650) =>
            new(alive, hasTrophy, canSprint, hasSlingshotInHand, movementPermille, aimMovementPermille);

        [Test]
        public void Filter_KeepsOnlyTheLookOfAKnockedOutPlayer()
        {
            var command = Command(
                buttons: PlayerCommandButtons.SprintHeld | PlayerCommandButtons.JumpPressed);

            var filtered = Context(alive: false).Filter(command);

            Assert.That(filtered.Tick, Is.EqualTo(command.Tick));
            Assert.That(filtered.MoveX, Is.Zero);
            Assert.That(filtered.MoveY, Is.Zero);
            Assert.That(filtered.Buttons, Is.EqualTo(PlayerCommandButtons.None));
            Assert.That(filtered.LookYaw, Is.EqualTo(command.LookYaw),
                "Un joueur au sol garde le droit de regarder autour de lui.");
            Assert.That(filtered.LookPitch, Is.EqualTo(command.LookPitch));
        }

        [Test]
        public void Filter_DropsSprintWhenUnaffordableAndPushWhileCarryingTheTrophy()
        {
            var buttons = PlayerCommandButtons.SprintHeld |
                          PlayerCommandButtons.InteractHeld |
                          PlayerCommandButtons.PunchHeld;

            var broke = Context(canSprint: false).Filter(Command(buttons: buttons));
            Assert.That(broke.Has(PlayerCommandButtons.SprintHeld), Is.False);
            Assert.That(broke.Has(PlayerCommandButtons.InteractHeld), Is.True);

            var carrying = Context(hasTrophy: true).Filter(Command(buttons: buttons));
            Assert.That(carrying.Has(PlayerCommandButtons.InteractHeld), Is.False);
            Assert.That(carrying.Has(PlayerCommandButtons.SprintHeld), Is.True);
            Assert.That(carrying.Has(PlayerCommandButtons.PunchHeld), Is.True,
                "Le filtre ne touche que le sprint et la poussée.");
        }

        [Test]
        public void MovementPermille_SlowsDownOnlyWhileTheSlingshotIsDrawn()
        {
            var aiming = Command(buttons: PlayerCommandButtons.PunchHeld);

            Assert.That(
                Context(hasSlingshotInHand: true).MovementPermilleFor(aiming),
                Is.EqualTo(650));
            Assert.That(
                Context(hasSlingshotInHand: true).MovementPermilleFor(Command()),
                Is.EqualTo(Scale),
                "Sans le bouton tenu, viser ne ralentit pas.");
            Assert.That(
                Context(hasSlingshotInHand: false).MovementPermilleFor(aiming),
                Is.EqualTo(Scale),
                "Sans lance-pierre en main, le clic gauche est un coup de poing.");
            Assert.That(
                Context(alive: false, movementPermille: 0).MovementPermilleFor(aiming),
                Is.Zero);
            Assert.That(
                Context(hasSlingshotInHand: true, movementPermille: 1, aimMovementPermille: 1)
                    .MovementPermilleFor(aiming),
                Is.EqualTo(1),
                "Viser ralentit, ne cloue jamais au sol.");
        }

        [Test]
        public void Context_RefusesAPermilleOutsideItsScale()
        {
            Assert.That(
                () => new SandboxCommandContext(true, false, true, false, Scale + 1, 650),
                Throws.TypeOf<ArgumentOutOfRangeException>());
            Assert.That(
                () => new SandboxCommandContext(true, false, true, false, Scale, 0),
                Throws.TypeOf<ArgumentOutOfRangeException>());
        }

        [Test]
        public void History_ReplaysTheContextOfTheTickInsteadOfTheCurrentOne()
        {
            var history = new SandboxCommandContextHistory();
            var aiming = Command(tick: 10u, buttons: PlayerCommandButtons.PunchHeld);

            // Tick 10 joué une première fois : le lance-pierre est en main.
            var atTen = Context(hasSlingshotInHand: true);
            history.Record(10u, atTen);

            // Le joueur lâche l'arme et prend le trophée : l'état « courant »
            // n'a plus rien à voir avec celui du tick 10.
            var now = Context(hasTrophy: true, movementPermille: 750);
            Assert.That(now.MovementPermilleFor(aiming), Is.EqualTo(750));

            Assert.That(history.TryGet(10u, out var replayed), Is.True);
            Assert.That(replayed, Is.EqualTo(atTen));
            Assert.That(replayed.MovementPermilleFor(aiming), Is.EqualTo(650),
                "Le rejeu du tick 10 doit revoir le lance-pierre bandé, pas le trophée d'aujourd'hui.");
        }

        [Test]
        public void History_ForgetsRatherThanReturningANeighbourTick()
        {
            var history = new SandboxCommandContextHistory();
            history.Record(5u, Context(movementPermille: 400));

            Assert.That(history.TryGet(6u, out _), Is.False, "Un tick jamais écrit n'existe pas.");
            Assert.That(history.TryGet(0u, out _), Is.False);

            // Le même emplacement d'anneau, un tour plus tard : l'ancien contexte
            // ne doit jamais être servi à la place du nouveau.
            var wrapped = 5u + (uint)SandboxCommandContextHistory.Capacity;
            Assert.That(history.TryGet(wrapped, out _), Is.False);
            history.Record(wrapped, Context(movementPermille: 900));
            Assert.That(history.TryGet(5u, out _), Is.False,
                "Le tick sorti de la fenêtre est oublié, pas confondu avec son successeur.");
            Assert.That(history.TryGet(wrapped, out var fresh), Is.True);
            Assert.That(fresh.MovementPermille, Is.EqualTo(900));
        }

        [Test]
        public void History_ForgetsEverythingWhenTheObjectStartsANewLife()
        {
            var history = new SandboxCommandContextHistory();
            history.Record(3u, Context(movementPermille: 400));
            Assert.That(history.TryGet(3u, out _), Is.True);

            history.Clear();

            Assert.That(history.TryGet(3u, out _), Is.False);
        }

        [Test]
        public void Unrestricted_LeavesAPlayerWithoutSandboxLayerAtFullSpeed()
        {
            var context = SandboxCommandContext.Unrestricted;
            var command = Command(
                buttons: PlayerCommandButtons.SprintHeld | PlayerCommandButtons.InteractHeld);

            Assert.That(context.Filter(command).Buttons, Is.EqualTo(command.Buttons));
            Assert.That(context.MovementPermilleFor(command), Is.EqualTo(Scale));
        }
    }
}
