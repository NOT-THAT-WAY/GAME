using NotThatWay.Game.Simulation;
using NUnit.Framework;

namespace NotThatWay.Game.Tests.EditMode
{
    /// <summary>
    /// Verrouille la rotation produite par un coup de poing après l'étape 3 de
    /// <c>docs/M1_WALL_HANDOFF.md</c> : sans atténuation, un seul coup à pleine
    /// puissance versait jusqu'à 36° (40 ticks × 900 mdeg), jugé excessif par le
    /// testeur. Avec le battant alourdi de l'étape 2 (400 mdeg/tick, levier
    /// plancher 400 pour mille) et l'atténuation de coup de l'étape 3
    /// (<see cref="M1PunchTuning.PunchTorqueScalePermille"/>, 15 ticks au lieu
    /// de 40), la cible est ≈3°. Ce test rejoue l'impulsion sur le modèle pur
    /// <see cref="WallRotationMachine"/>, sans FishNet ni director : c'est ce que
    /// <c>M1AuthoritativeWallDirector.TryRegisterPunchImpulse</c> verse à la
    /// machine, pas la façon dont il y arrive.
    /// </summary>
    public sealed class M1PunchTorqueTests
    {
        private const int WallId = 10;
        private const int SourceId = 77;

        // Réglages de l'étape 2 (alourdissement du battant), reproduits ici en
        // dur plutôt que lus sur le director : c'est le contrat du modèle pur,
        // indépendant de toute scène Unity.
        private const int MaximumSpeed = 400;
        private const int MinimumLeverage = 400;

        private static WallSimulationSettings Settings =>
            new(MaximumSpeed, MinimumLeverage, 180u);

        /// <summary>
        /// Rejoue exactement ce que <c>TryRegisterPunchImpulse</c> fait côté
        /// serveur : atténuer le levier du contact une seule fois, puis verser ce
        /// même couple pendant <see cref="M1PunchTuning.WallImpulseTicks"/> ticks.
        /// Utiliser les constantes de production ici (et pas des nombres en dur)
        /// est volontaire : si quelqu'un change la durée ou le facteur
        /// d'atténuation, ce test doit tourner sur le nouveau réglage — c'est
        /// l'angle final, lui, qui reste une valeur figée.
        /// </summary>
        private static int SweepPunch(int contactLeveragePermille)
        {
            var scaledLeverage = contactLeveragePermille * M1PunchTuning.PunchTorqueScalePermille /
                                  WallSimulationSettings.PermilleScale;
            var machine = new WallRotationMachine(Settings, WallId, 0, 0u);
            for (var tick = 1u; tick <= M1PunchTuning.WallImpulseTicks; tick++)
            {
                machine.AdvanceTick(
                    tick,
                    new[] { new WallTorqueIntent(WallId, SourceId, 1, scaledLeverage) });
            }

            return machine.State.AngleMilliDegrees;
        }

        [Test]
        public void PunchTorqueScale_SweepsThreeDegreesAtTheTip()
        {
            // Contact au bout du battant : levier plein (1000 pour mille) avant
            // atténuation. 15 ticks × (1000 × 500‰ atténué, quantifié à 500‰) ×
            // 400 mdeg/tick / 1000 = 15 × 200 = 3 000 mdeg, soit 3° — la cible de
            // l'étape 3 du handoff M1 (« un à-coup lisible, pas une bourrasque »).
            Assert.That(SweepPunch(1000), Is.EqualTo(3000));
        }

        [Test]
        public void PunchTorqueScale_SweepsLessAtTheHinge()
        {
            // Contact au gond : levier plancher de l'étape 2 (400 pour mille)
            // avant atténuation. 15 ticks × (400 × 500‰ atténué = 200‰) ×
            // 400 mdeg/tick / 1000 = 15 × 80 = 1 200 mdeg, soit 1,2° : le même
            // coup, mais au bras de levier minimal.
            Assert.That(SweepPunch(MinimumLeverage), Is.EqualTo(1200));
        }
    }
}
