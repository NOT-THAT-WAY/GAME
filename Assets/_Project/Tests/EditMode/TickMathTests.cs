using System;
using NotThatWay.Game.Simulation;
using NUnit.Framework;

namespace NotThatWay.Game.Tests.EditMode
{
    public sealed class TickMathTests
    {
        [Test]
        public void TickComparisons_StayOrderedAcrossUintWrap()
        {
            Assert.That(TickMath.Next(uint.MaxValue), Is.EqualTo(0u));
            Assert.That(TickMath.IsNext(0u, uint.MaxValue), Is.True);
            Assert.That(TickMath.IsNewer(0u, uint.MaxValue), Is.True);
            Assert.That(TickMath.IsOlder(uint.MaxValue, 0u), Is.True);

            var start = uint.MaxValue - 1u;
            Assert.That(TickMath.Elapsed(start, 1u), Is.EqualTo(3u));
            Assert.That(TickMath.HasElapsed(start, 3u, 1u), Is.True);
        }

        [Test]
        public void ProgressQ16_IsExactAtBoundariesIncludingWrap()
        {
            var start = uint.MaxValue - 1u;

            Assert.That(TickMath.ProgressQ16(start, 3u, start), Is.EqualTo(0));
            Assert.That(TickMath.ProgressQ16(start, 3u, start - 1u), Is.EqualTo(0));
            Assert.That(TickMath.Elapsed(start, start - 1u), Is.Zero);
            Assert.That(TickMath.HasElapsed(start, 3u, start - 1u), Is.False);
            Assert.That(TickMath.ProgressQ16(start, 3u, uint.MaxValue), Is.EqualTo(21845));
            Assert.That(TickMath.ProgressQ16(start, 3u, 0u), Is.EqualTo(43690));
            Assert.That(TickMath.ProgressQ16(start, 3u, 1u), Is.EqualTo(ushort.MaxValue));
            Assert.That(TickMath.ProgressQ16(start, 3u, 2u), Is.EqualTo(ushort.MaxValue));
        }

        [Test]
        public void HalfRangeAndInvalidDurations_AreRejectedExplicitly()
        {
            Assert.That(
                () => TickMath.Compare(0u, 0x80000000u),
                Throws.ArgumentException.With.Message.Contains("2^31"));
            Assert.That(() => TickMath.ValidateDuration(0u), Throws.TypeOf<ArgumentOutOfRangeException>());
            Assert.That(
                () => TickMath.ValidateDuration((uint)int.MaxValue + 1u),
                Throws.TypeOf<ArgumentOutOfRangeException>());
        }
    }
}
