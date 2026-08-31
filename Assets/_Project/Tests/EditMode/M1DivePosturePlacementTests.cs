using NUnit.Framework;
using UnityEngine;

namespace NotThatWay.Game.Tests.EditMode
{
    /// <summary>
    /// Placement au sol de la posture plongeon/plat ventre. La bascule pivote aux
    /// pieds : sans compensation, la moitié avant du corps passe sous le plancher.
    /// Ces tests fixent la seule règle qui compte — quel que soit l'angle, le point
    /// le plus bas du modèle reste à la hauteur qu'il avait debout.
    ///
    /// Rien ici n'est autoritaire : la forme physique du joueur reste la capsule du
    /// CharacterController, dont la hauteur vient de l'état simulé du tick.
    /// </summary>
    public sealed class M1DivePosturePlacementTests
    {
        private const float Tolerance = 1e-4f;

        /// <summary>Portée avant d'un personnage « boule » de 1,40 m.</summary>
        private const float ForwardReach = 0.35f;

        /// <summary>
        /// Hauteur du point le plus bas une fois la bascule appliquée ET compensée.
        /// Reproduit ce que fait <c>M1DivePresentation.Update</c> : rotation de
        /// <paramref name="tiltDegrees"/> autour de X, puis remontée.
        /// </summary>
        private static float LowestAfterTilt(
            float tiltDegrees,
            float restLowest,
            float forwardReach)
        {
            var tilt = tiltDegrees * Mathf.Deg2Rad;
            var rotated = restLowest * Mathf.Cos(tilt) - forwardReach * Mathf.Sin(tilt);
            return rotated + M1DivePresentation.ProneLiftMeters(
                tiltDegrees, restLowest, forwardReach);
        }

        [Test]
        public void Standing_LeavesTheRestPoseUntouched()
        {
            Assert.That(
                M1DivePresentation.ProneLiftMeters(0f, 0f, ForwardReach),
                Is.EqualTo(0f).Within(Tolerance),
                "Debout, la posture ne doit rien décaler du tout.");
            Assert.That(
                M1DivePresentation.ProneLiftMeters(0f, 0.03f, ForwardReach),
                Is.EqualTo(0f).Within(Tolerance),
                "Y compris pour un modèle dont l'origine n'est pas pile aux pieds.");
        }

        [Test]
        public void Prone_LiftsTheBodyBackOntoTheFloorInsteadOfBuryingIt()
        {
            // À 90°, l'avant du corps devient son dessous : sans compensation il
            // descend de toute sa portée avant sous le plancher.
            var lift = M1DivePresentation.ProneLiftMeters(90f, 0f, ForwardReach);

            Assert.That(lift, Is.EqualTo(ForwardReach).Within(Tolerance));
            Assert.That(lift, Is.GreaterThan(0f),
                "L'ancienne posture descendait le corps de 12 cm de plus : " +
                "un personnage à plat ventre finissait enterré aux deux tiers.");
            Assert.That(
                LowestAfterTilt(90f, 0f, ForwardReach),
                Is.EqualTo(0f).Within(Tolerance),
                "À plat ventre, le corps repose sur le sol, il ne le traverse pas.");
        }

        [Test]
        public void EveryTilt_KeepsTheLowestPointAtItsStandingHeight()
        {
            // Le plongeon traverse toute la plage : la posture doit être juste à
            // chaque image de l'interpolation, pas seulement aux deux extrêmes.
            for (var tilt = 0f; tilt <= 90f; tilt += 5f)
            {
                Assert.That(
                    LowestAfterTilt(tilt, 0f, ForwardReach),
                    Is.EqualTo(0f).Within(Tolerance),
                    $"Le corps décolle ou s'enfonce à {tilt:F0}°.");
                Assert.That(
                    M1DivePresentation.ProneLiftMeters(tilt, 0f, ForwardReach),
                    Is.GreaterThanOrEqualTo(0f),
                    $"Aucune posture ne doit pousser le corps vers le bas ({tilt:F0}°).");
            }
        }

        [Test]
        public void ModelOffsetFromItsFeet_KeepsItsOwnFloorLevel()
        {
            const float restLowest = 0.03f;

            Assert.That(
                LowestAfterTilt(78f, restLowest, ForwardReach),
                Is.EqualTo(restLowest).Within(Tolerance),
                "Un modèle posé 3 cm au-dessus de sa racine garde ces 3 cm en vol.");
            Assert.That(
                LowestAfterTilt(90f, restLowest, ForwardReach),
                Is.EqualTo(restLowest).Within(Tolerance));
        }

        [Test]
        public void UnmeasurableModel_FallsBackToTheRestPoseRatherThanAGuess()
        {
            // MeasureBody met les deux mesures à zéro quand aucun maillage n'est
            // lisible : la posture bascule sans se déplacer, elle n'invente rien.
            for (var tilt = 0f; tilt <= 90f; tilt += 30f)
            {
                Assert.That(
                    M1DivePresentation.ProneLiftMeters(tilt, 0f, 0f),
                    Is.EqualTo(0f).Within(Tolerance));
            }
        }
    }
}
