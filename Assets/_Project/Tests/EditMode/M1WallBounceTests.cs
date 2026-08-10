using NUnit.Framework;
using UnityEngine;

namespace NotThatWay.Game.Tests.EditMode
{
    /// <summary>
    /// Verrouille la vitesse du retour tactile d'une poussée contre le battant
    /// (« appuyer contre une porte lourde doit repousser un peu »,
    /// <see cref="M1WallBounceTuning"/>). Le déplacement d'un coup de poing vaut
    /// v² / (2a) = 4,5² / (2×10) ≈ 1,01 m, avec v =
    /// <see cref="M1WallBounceTuning.PunchKnockbackSpeedMetersPerSecond"/> et a =
    /// la décélération par défaut de <c>PredictedPlayerMotor._knockbackDecay</c>
    /// (10 m/s²). Le déplacement varie comme le carré de la vitesse, donc obtenir
    /// une fraction de ce déplacement exige un facteur racine carrée sur la
    /// vitesse, pas une règle de trois — c'est cette relation que ce test
    /// verrouille, indépendamment de tout réglage du coup de poing.
    /// </summary>
    public sealed class M1WallBounceTests
    {
        [Test]
        public void Speed_AtDefaultDisplacementPermille_MatchesDerivedValue()
        {
            // 4,5 × sqrt(100 / 1000) = 4,5 × sqrt(0,1) ≈ 1,4230249 m/s, pour un
            // recul d'environ 0,101 m (10 % du déplacement d'un coup de poing,
            // ≈1,01 m) — la demande du testeur. Valeur figée en dur : c'est un
            // nombre de game design, il doit apparaître dans un diff quand il
            // change.
            Assert.That(
                M1WallBounceTuning.Speed(M1WallBounceTuning.WallBounceDisplacementPermille),
                Is.EqualTo(1.4230249f).Within(0.0001f));
        }

        [Test]
        public void Speed_DoublingDisplacementPermille_ScalesBySqrtTwoNotByTwo()
        {
            // Le déplacement varie en v² : doubler le pour-mille de déplacement
            // (100 → 200, donc 10 % → 20 % du déplacement d'un coup de poing) doit
            // multiplier la vitesse par sqrt(2), pas par 2. C'est la preuve que la
            // relation quadratique n'a pas été platement linéarisée.
            var baseline = M1WallBounceTuning.Speed(100);
            var doubled = M1WallBounceTuning.Speed(200);

            Assert.That(doubled, Is.EqualTo(baseline * Mathf.Sqrt(2f)).Within(0.0001f));
            // Et donc pas le double de la vitesse de référence.
            Assert.That(doubled, Is.Not.EqualTo(baseline * 2f).Within(0.0001f));
        }
    }
}
