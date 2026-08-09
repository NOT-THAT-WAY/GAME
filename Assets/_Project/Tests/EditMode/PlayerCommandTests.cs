using System;
using NotThatWay.Game.PlayerSimulation;
using NUnit.Framework;

namespace NotThatWay.Game.Tests.EditMode
{
    public sealed class PlayerCommandTests
    {
        [Test]
        public void Encoder_NormalizesDiagonalAndUsesStableAwayFromZeroRounding()
        {
            var diagonal = PlayerCommandEncoder.Encode(
                7u, 1d, 1d, 0.005d, -0.005d, PlayerCommandButtons.None);

            Assert.That(diagonal.MoveX, Is.EqualTo(90));
            Assert.That(diagonal.MoveY, Is.EqualTo(90));
            Assert.That(diagonal.LookYaw, Is.EqualTo(1));
            Assert.That(diagonal.LookPitch, Is.EqualTo(-1));
            Assert.That(diagonal.Tick, Is.EqualTo(7u));
        }

        [Test]
        public void Encoder_ClampsAxesAndLookWithoutWrapping()
        {
            var command = PlayerCommandEncoder.Encode(
                9u,
                double.MaxValue,
                0d,
                10000d,
                -10000d,
                PlayerCommandButtons.SprintHeld);

            Assert.That(command.MoveX, Is.EqualTo(PlayerCommandEncoder.AxisMagnitude));
            Assert.That(command.MoveY, Is.Zero);
            Assert.That(command.LookYaw, Is.EqualTo(short.MaxValue));
            Assert.That(command.LookPitch, Is.EqualTo(short.MinValue));
            Assert.That(command.Has(PlayerCommandButtons.SprintHeld), Is.True);
        }

        [Test]
        public void Accumulator_PreservesEdgesAndLookUntilOneTickOnly()
        {
            var accumulator = new PlayerCommandAccumulator();
            accumulator.Accumulate(new PlayerInputSample(
                0.5f,
                -0.25f,
                1.25f,
                -0.5f,
                PlayerCommandButtons.SprintHeld,
                PlayerCommandButtons.JumpPressed));
            accumulator.Accumulate(new PlayerInputSample(
                1f,
                0f,
                0.75f,
                0.25f,
                PlayerCommandButtons.SprintHeld,
                PlayerCommandButtons.PunchPressed));

            var first = accumulator.Consume(100u);
            var second = accumulator.Consume(101u);

            Assert.That(first.MoveX, Is.EqualTo(127));
            Assert.That(first.MoveY, Is.Zero);
            Assert.That(first.LookYaw, Is.EqualTo(200));
            Assert.That(first.LookPitch, Is.EqualTo(-25));
            Assert.That(first.Has(PlayerCommandButtons.SprintHeld), Is.True);
            Assert.That(first.Has(PlayerCommandButtons.JumpPressed), Is.True);
            Assert.That(first.Has(PlayerCommandButtons.PunchPressed), Is.True);

            Assert.That(second.MoveX, Is.EqualTo(127), "La dernière direction tenue persiste.");
            Assert.That(second.LookYaw, Is.Zero);
            Assert.That(second.LookPitch, Is.Zero);
            Assert.That(second.Has(PlayerCommandButtons.SprintHeld), Is.True);
            Assert.That(second.Has(PlayerCommandButtons.JumpPressed), Is.False);
            Assert.That(second.Has(PlayerCommandButtons.PunchPressed), Is.False);
        }

        [Test]
        public void Accumulator_KeepsTapThatStartsAndEndsBetweenTicks()
        {
            var accumulator = new PlayerCommandAccumulator();
            accumulator.Accumulate(new PlayerInputSample(
                0f, 0f, 0f, 0f,
                PlayerCommandButtons.InteractHeld,
                PlayerCommandButtons.InteractPressed));
            accumulator.Accumulate(new PlayerInputSample(
                0f, 0f, 0f, 0f,
                PlayerCommandButtons.None,
                PlayerCommandButtons.None));

            var command = accumulator.Consume(1u);

            Assert.That(command.Has(PlayerCommandButtons.InteractPressed), Is.True);
            Assert.That(command.Has(PlayerCommandButtons.InteractHeld), Is.False);
            Assert.That(accumulator.Consume(2u).Has(PlayerCommandButtons.InteractPressed), Is.False);
        }

        [Test]
        public void Accumulators_AreIndependentForTwoLocalPlayers()
        {
            var first = new PlayerCommandAccumulator();
            var second = new PlayerCommandAccumulator();
            first.Accumulate(new PlayerInputSample(
                1f, 0f, 2f, 0f,
                PlayerCommandButtons.None,
                PlayerCommandButtons.PunchPressed));
            second.Accumulate(new PlayerInputSample(
                -1f, 0f, -3f, 0f,
                PlayerCommandButtons.SprintHeld,
                PlayerCommandButtons.None));

            var firstCommand = first.Consume(3u);
            var secondCommand = second.Consume(3u);

            Assert.That(firstCommand.MoveX, Is.EqualTo(127));
            Assert.That(firstCommand.LookYaw, Is.EqualTo(200));
            Assert.That(firstCommand.Has(PlayerCommandButtons.PunchPressed), Is.True);
            Assert.That(secondCommand.MoveX, Is.EqualTo(-127));
            Assert.That(secondCommand.LookYaw, Is.EqualTo(-300));
            Assert.That(secondCommand.Has(PlayerCommandButtons.PunchPressed), Is.False);
            Assert.That(secondCommand.Has(PlayerCommandButtons.SprintHeld), Is.True);
        }

        [Test]
        public void InvalidNonFiniteSamplesAndWrongButtonKindsAreRejected()
        {
            Assert.That(
                () => new PlayerInputSample(
                    float.NaN, 0f, 0f, 0f,
                    PlayerCommandButtons.None,
                    PlayerCommandButtons.None),
                Throws.TypeOf<ArgumentOutOfRangeException>());
            Assert.That(
                () => new PlayerInputSample(
                    0f, 0f, 0f, 0f,
                    PlayerCommandButtons.JumpPressed,
                    PlayerCommandButtons.None),
                Throws.TypeOf<ArgumentOutOfRangeException>());
            Assert.That(
                () => PlayerCommandEncoder.Encode(
                    0u, 0d, 0d, double.PositiveInfinity, 0d, PlayerCommandButtons.None),
                Throws.TypeOf<ArgumentOutOfRangeException>());
        }
    }
}
