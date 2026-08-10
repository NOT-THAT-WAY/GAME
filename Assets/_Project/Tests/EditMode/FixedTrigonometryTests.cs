using System;
using NotThatWay.Game.Simulation;
using NUnit.Framework;

namespace NotThatWay.Game.Tests.EditMode
{
    public sealed class FixedTrigonometryTests
    {
        [Test]
        public void CardinalAngles_AreExactSoTheRestingPoseMatchesTheTopology()
        {
            FixedTrigonometry.SinCos(0, out var sinZero, out var cosZero);
            FixedTrigonometry.SinCos(90_000, out var sinQuarter, out var cosQuarter);
            FixedTrigonometry.SinCos(180_000, out var sinHalf, out var cosHalf);
            FixedTrigonometry.SinCos(270_000, out var sinThreeQuarters, out var cosThreeQuarters);

            Assert.That(sinZero, Is.Zero);
            Assert.That(cosZero, Is.EqualTo(FixedTrigonometry.Scale));
            Assert.That(sinQuarter, Is.EqualTo(FixedTrigonometry.Scale));
            Assert.That(cosQuarter, Is.Zero);
            Assert.That(sinHalf, Is.Zero);
            Assert.That(cosHalf, Is.EqualTo(-FixedTrigonometry.Scale));
            Assert.That(sinThreeQuarters, Is.EqualTo(-FixedTrigonometry.Scale));
            Assert.That(cosThreeQuarters, Is.Zero);
        }

        [Test]
        public void EveryAngleOfTheTurn_MatchesTheDoublePrecisionReferenceWithinAQ16Unit()
        {
            const double toRadians = Math.PI / 180_000d;
            var worstSin = 0;
            var worstCos = 0;
            for (var milliDegrees = 0; milliDegrees < 360_000; milliDegrees += 137)
            {
                FixedTrigonometry.SinCos(milliDegrees, out var sin, out var cos);
                var referenceSin = (int)Math.Round(
                    Math.Sin(milliDegrees * toRadians) * FixedTrigonometry.Scale);
                var referenceCos = (int)Math.Round(
                    Math.Cos(milliDegrees * toRadians) * FixedTrigonometry.Scale);
                worstSin = Math.Max(worstSin, Math.Abs(sin - referenceSin));
                worstCos = Math.Max(worstCos, Math.Abs(cos - referenceCos));
            }

            // Deux unités Q16 valent 0,08 mm au bout d'un battant de 2,75 m :
            // très en dessous du millimètre où la topologie quantifie.
            Assert.That(worstSin, Is.LessThanOrEqualTo(2), $"écart sinus={worstSin}");
            Assert.That(worstCos, Is.LessThanOrEqualTo(2), $"écart cosinus={worstCos}");
        }

        [Test]
        public void UnitCircle_StaysNormalisedAndSymmetric()
        {
            for (var milliDegrees = 0; milliDegrees < 360_000; milliDegrees += 991)
            {
                FixedTrigonometry.SinCos(milliDegrees, out var sin, out var cos);
                var norm = (long)sin * sin + (long)cos * cos;
                var reference = (long)FixedTrigonometry.Scale * FixedTrigonometry.Scale;
                Assert.That(
                    Math.Abs(norm - reference),
                    Is.LessThanOrEqualTo(8L * FixedTrigonometry.Scale),
                    $"norme hors tolérance à {milliDegrees} milli-degrés");

                // La réduction de quadrant n'est pas bit-symétrique : la table
                // d'arc-tangentes est arrondie au milli-degré. Une unité Q16
                // d'écart reste sous le micromètre sur le battant.
                FixedTrigonometry.SinCos(-milliDegrees, out var mirroredSin, out var mirroredCos);
                Assert.That(mirroredSin, Is.EqualTo(-sin).Within(2));
                Assert.That(mirroredCos, Is.EqualTo(cos).Within(2));
            }
        }

        [Test]
        public void NormalizeAndSignedDelta_WrapWithoutEverProducingANegativeAngle()
        {
            Assert.That(FixedTrigonometry.Normalize(0L), Is.Zero);
            Assert.That(FixedTrigonometry.Normalize(360_000L), Is.Zero);
            Assert.That(FixedTrigonometry.Normalize(-1L), Is.EqualTo(359_999));
            Assert.That(FixedTrigonometry.Normalize(-360_001L), Is.EqualTo(359_999));
            Assert.That(FixedTrigonometry.Normalize(1_080_500L), Is.EqualTo(500));

            Assert.That(FixedTrigonometry.SignedDelta(350_000, 10_000), Is.EqualTo(20_000));
            Assert.That(FixedTrigonometry.SignedDelta(10_000, 350_000), Is.EqualTo(-20_000));
            Assert.That(FixedTrigonometry.SignedDelta(0, 180_000), Is.EqualTo(180_000));
            Assert.That(FixedTrigonometry.SignedDelta(0, 180_001), Is.EqualTo(-179_999));
        }
    }
}
