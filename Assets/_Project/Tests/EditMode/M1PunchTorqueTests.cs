using NotThatWay.Game.Simulation;
using NUnit.Framework;

namespace NotThatWay.Game.Tests.EditMode
{
    /// <summary>
    /// Verrouille la rotation produite par un coup de poing. Un premier réglage
    /// (atténuation 500‰, 15 ticks, cible ≈3°) a été jugé trop timide par le
    /// testeur, qui veut désormais qu'un coup au bout du battant vaille un
    /// cinquième de tour (18°), pour qu'une vingtaine de coups fassent un tour
    /// complet. Avec le battant à 400 mdeg/tick (levier plancher 400 pour
    /// mille), la vitesse d'un coup passe par
    /// <see cref="WallSimulationSettings.VelocityFromNetLeverage"/>, dont le
    /// levier est borné à 1000 pour mille : 400 mdeg/tick est donc la vitesse
    /// maximale atteignable, et balayer 18 000 mdeg exige au minimum 45 ticks à
    /// pleine puissance — d'où <see cref="M1PunchTuning.WallImpulseTicks"/> = 45
    /// et une atténuation neutre (<see cref="M1PunchTuning.PunchTorqueScalePermille"/>
    /// = 1000). Ce test rejoue l'impulsion sur le modèle pur
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
        public void PunchTorqueScale_SweepsEighteenDegreesAtTheTip()
        {
            // Contact au bout du battant : levier plein (1000 pour mille), atténuation
            // neutre (1000‰) donc levier net inchangé = 1000‰ = vitesse maximale.
            // 45 ticks × 400 mdeg/tick = 18 000 mdeg, soit 18° = 1/5 de tour — demande
            // explicite du testeur pour qu'une vingtaine de coups fassent un tour
            // complet.
            Assert.That(SweepPunch(1000), Is.EqualTo(18000));
        }

        [Test]
        public void PunchTorqueScale_SweepsSevenPointTwoDegreesAtTheHinge()
        {
            // Contact au gond : levier plancher (400 pour mille), atténuation neutre.
            // 45 ticks × (400‰ × 400 mdeg/tick / 1000) = 45 ticks × 160 mdeg/tick =
            // 7 200 mdeg, soit 7,2° : le même coup, mais au bras de levier minimal.
            Assert.That(SweepPunch(MinimumLeverage), Is.EqualTo(7200));
        }
    }
}
