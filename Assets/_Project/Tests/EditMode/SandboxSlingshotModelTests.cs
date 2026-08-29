using System;
using NotThatWay.Game.Sandbox;
using NUnit.Framework;

namespace NotThatWay.Game.Tests.EditMode
{
    public sealed class SandboxSlingshotModelTests
    {
        private const uint DropHold = 4u;
        private const uint Charge = 10u;
        private const int MinimumPower = 300;

        [Test]
        public void Config_RejectsZeroWindowsAndOutOfRangePower()
        {
            Assert.That(() => new SandboxSlingshotModel(0u, Charge, MinimumPower), Throws.TypeOf<ArgumentOutOfRangeException>());
            Assert.That(() => new SandboxSlingshotModel(DropHold, 0u, MinimumPower), Throws.TypeOf<ArgumentOutOfRangeException>());
            Assert.That(() => new SandboxSlingshotModel(DropHold, Charge, 0), Throws.TypeOf<ArgumentOutOfRangeException>());
            Assert.That(() => new SandboxSlingshotModel(DropHold, Charge, 1001), Throws.TypeOf<ArgumentOutOfRangeException>());
            Assert.That(SandboxSlingshotModel.FromConfig(SandboxGameplayConfig.Baseline60Hz), Is.Not.Null);
        }

        [Test]
        public void WithoutTheSlingshot_PressTakesImmediatelyAndTheFollowingHoldDropsNothing()
        {
            var model = new SandboxSlingshotModel(DropHold, Charge, MinimumPower);

            var press = model.Advance(Input(slingshotPressed: true, slingshotHeld: true, inHand: false));
            Assert.That(press.Action, Is.EqualTo(SlingshotActionKind.TakeOrLoad));

            // Pris au sol : dès le tick suivant l'arme est en main et le bouton
            // toujours tenu. Aucun lâcher ne doit en découler, même longtemps.
            for (var tick = 0; tick < 20; tick++)
            {
                var held = model.Advance(Input(slingshotHeld: true, inHand: true));
                Assert.That(held.Action, Is.EqualTo(SlingshotActionKind.None), $"tick {tick}");
            }
            var release = model.Advance(Input(inHand: true));
            Assert.That(release.Action, Is.EqualTo(SlingshotActionKind.None), "Ni tap ni lâcher au relâchement.");
        }

        [Test]
        public void InHand_ShortPressLoadsAndLongHoldDropsExactlyOnce()
        {
            var model = new SandboxSlingshotModel(DropHold, Charge, MinimumPower);

            // Tap sur deux ticks : appui puis relâchement.
            Assert.That(model.Advance(Input(slingshotPressed: true, slingshotHeld: true, inHand: true)).Action,
                Is.EqualTo(SlingshotActionKind.None));
            Assert.That(model.Advance(Input(inHand: true)).Action, Is.EqualTo(SlingshotActionKind.TakeOrLoad));

            // Tap dans le même tick : le front arrive sans état tenu.
            Assert.That(model.Advance(Input(slingshotPressed: true, inHand: true)).Action,
                Is.EqualTo(SlingshotActionKind.TakeOrLoad));

            // Maintien : le lâcher tombe au tick DropHold, une seule fois, et le
            // relâchement qui suit n'est pas un tap.
            Assert.That(model.Advance(Input(slingshotPressed: true, slingshotHeld: true, inHand: true)).Action,
                Is.EqualTo(SlingshotActionKind.None));
            SlingshotTickResult result = default;
            for (var tick = 2u; tick < DropHold; tick++)
            {
                result = model.Advance(Input(slingshotHeld: true, inHand: true));
                Assert.That(result.Action, Is.EqualTo(SlingshotActionKind.None), $"tick {tick}");
            }
            result = model.Advance(Input(slingshotHeld: true, inHand: true));
            Assert.That(result.Action, Is.EqualTo(SlingshotActionKind.Drop));
            Assert.That(model.Advance(Input(slingshotHeld: true, inHand: true)).Action, Is.EqualTo(SlingshotActionKind.None));
            Assert.That(model.Advance(Input(inHand: false)).Action, Is.EqualTo(SlingshotActionKind.None));
        }

        [Test]
        public void Fire_ChargesWhileHeldAndReleasesWithBoundedPower()
        {
            var model = new SandboxSlingshotModel(DropHold, Charge, MinimumPower);

            // Pichenette : appui-relâchement dans le même tick → puissance minimale.
            var tap = model.Advance(Input(firePressed: true, inHand: true));
            Assert.That(tap.Action, Is.EqualTo(SlingshotActionKind.Fire));
            Assert.That(tap.PowerPermille, Is.EqualTo(MinimumPower));

            // Demi-charge : 5 ticks tenus sur 10.
            for (var tick = 0; tick < 5; tick++)
            {
                var charging = model.Advance(Input(firePressed: tick == 0, fireHeld: true, inHand: true));
                Assert.That(charging.Action, Is.EqualTo(SlingshotActionKind.None));
                Assert.That(model.IsCharging, Is.True);
            }
            Assert.That(model.ChargePermille, Is.EqualTo(500));
            var half = model.Advance(Input(inHand: true));
            Assert.That(half.Action, Is.EqualTo(SlingshotActionKind.Fire));
            Assert.That(half.PowerPermille, Is.EqualTo(MinimumPower + (1000 - MinimumPower) / 2));
            Assert.That(model.IsCharging, Is.False);

            // Charge pleine et au-delà : plafonnée à 1000 ‰.
            for (var tick = 0; tick < 30; tick++)
                model.Advance(Input(firePressed: tick == 0, fireHeld: true, inHand: true));
            Assert.That(model.ChargePermille, Is.EqualTo(1000));
            var full = model.Advance(Input(inHand: true));
            Assert.That(full.PowerPermille, Is.EqualTo(1000));

            // Lâcher l'arme pendant la charge l'annule sans tir.
            model.Advance(Input(firePressed: true, fireHeld: true, inHand: true));
            model.Advance(Input(fireHeld: true, inHand: true));
            var cancelled = model.Advance(Input(fireHeld: true, inHand: false));
            Assert.That(cancelled.Action, Is.EqualTo(SlingshotActionKind.None));
            Assert.That(model.IsCharging, Is.False);
            Assert.That(model.Advance(Input(inHand: true)).Action, Is.EqualTo(SlingshotActionKind.None));
        }

        [Test]
        public void SlingshotButton_TakesPrecedenceOverAReleasedShotOnTheSameTick()
        {
            var model = new SandboxSlingshotModel(DropHold, Charge, MinimumPower);
            model.Advance(Input(firePressed: true, fireHeld: true, inHand: true));
            var both = model.Advance(Input(slingshotPressed: true, inHand: true));
            Assert.That(both.Action, Is.EqualTo(SlingshotActionKind.TakeOrLoad));
            Assert.That(both.PowerPermille, Is.Zero, "Le tir perdu ne porte aucune puissance.");
            Assert.That(model.IsCharging, Is.False);
        }

        private static SlingshotTickInput Input(
            bool slingshotPressed = false,
            bool slingshotHeld = false,
            bool firePressed = false,
            bool fireHeld = false,
            bool inHand = false) =>
            new(slingshotPressed, slingshotHeld, firePressed, fireHeld, inHand);
    }
}
