using System;
using NotThatWay.Game.Sandbox;
using NUnit.Framework;

namespace NotThatWay.Game.Tests.EditMode
{
    public sealed class SandboxGameplayModelTests
    {
        [Test]
        public void Baseline_ExposesTheAcceptedSandboxTuning()
        {
            var config = SandboxGameplayConfig.Baseline60Hz;

            Assert.That(config.TickRate, Is.EqualTo(60));
            Assert.That(config.MaximumHealth, Is.EqualTo(100));
            Assert.That(config.MaximumEnergy, Is.EqualTo(100));
            Assert.That(config.PunchDamage, Is.EqualTo(25));
            Assert.That(config.RockDamage, Is.EqualTo(30));
            Assert.That(config.TrophyDamage, Is.EqualTo(10));
            Assert.That(config.PunchEnergyCost, Is.EqualTo(25));
            Assert.That(config.ThrowEnergyCost, Is.EqualTo(18));
            Assert.That(config.SprintDrainIntervalTicks, Is.EqualTo(5u));
            Assert.That(config.SprintDrainAmount, Is.EqualTo(1));
            Assert.That(config.PushDrainIntervalTicks, Is.EqualTo(4u));
            Assert.That(config.PushDrainAmount, Is.EqualTo(1));
            Assert.That(config.TrophyMovementPermille, Is.EqualTo(750));
            Assert.That(config.TrophySprintDrainMultiplier, Is.EqualTo(5));
            Assert.That(config.EnergyRegenerationDelayTicks, Is.EqualTo(60u));
            Assert.That(config.EnergyRegenerationIntervalTicks, Is.EqualTo(4u));
            Assert.That(config.EnergyRegenerationAmount, Is.EqualTo(1));
            Assert.That(config.HealthRegenerationDelayTicks, Is.EqualTo(300u));
            Assert.That(config.HealthRegenerationIntervalTicks, Is.EqualTo(10u));
            Assert.That(config.HealthRegenerationAmount, Is.EqualTo(1));
            Assert.That(config.KnockoutDurationTicks, Is.EqualTo(120u));
            Assert.That(config.RecoveryHealth, Is.EqualTo(40));
            Assert.That(config.RecoveryProtectionTicks, Is.EqualTo(60u));
            Assert.That(config.SlingshotDamage, Is.EqualTo(45));
            Assert.That(config.SlingshotEnergyCost, Is.EqualTo(14));
            Assert.That(config.SlingshotAmmoCapacity, Is.EqualTo(5));
            Assert.That(config.SlingshotChargeTicks, Is.EqualTo(72u));
            Assert.That(config.SlingshotMinimumPowerPermille, Is.EqualTo(350));
            Assert.That(config.SlingshotDropHoldTicks, Is.EqualTo(30u));
            Assert.That(config.SlingshotAimMovementPermille, Is.EqualTo(650));
        }

        [Test]
        public void Slingshot_FiresAPocketRockHarderThanAHandThrowAndReloadsByPickup()
        {
            var baseline = SandboxGameplayConfig.Baseline60Hz;
            Assert.That(baseline.SlingshotDamage, Is.GreaterThan(baseline.RockDamage));
            Assert.That(
                () => new SandboxGameplayConfig(
                    baseline.TickRate, baseline.MaximumHealth, baseline.MaximumEnergy,
                    baseline.PunchDamage, baseline.RockDamage, baseline.TrophyDamage,
                    baseline.PunchEnergyCost, baseline.ThrowEnergyCost,
                    baseline.SprintDrainIntervalTicks, baseline.SprintDrainAmount,
                    baseline.PushDrainIntervalTicks, baseline.PushDrainAmount,
                    baseline.TrophySprintDrainMultiplier,
                    baseline.EnergyRegenerationDelayTicks, baseline.EnergyRegenerationIntervalTicks,
                    baseline.EnergyRegenerationAmount,
                    baseline.HealthRegenerationDelayTicks, baseline.HealthRegenerationIntervalTicks,
                    baseline.HealthRegenerationAmount,
                    baseline.KnockoutDurationTicks, baseline.RecoveryHealth,
                    baseline.RecoveryProtectionTicks, baseline.TrophyMovementPermille,
                    slingshotDamage: baseline.RockDamage,
                    slingshotEnergyCost: baseline.SlingshotEnergyCost,
                    slingshotAmmoCapacity: baseline.SlingshotAmmoCapacity,
                    slingshotChargeTicks: baseline.SlingshotChargeTicks,
                    slingshotMinimumPowerPermille: baseline.SlingshotMinimumPowerPermille,
                    slingshotDropHoldTicks: baseline.SlingshotDropHoldTicks,
                    slingshotAimMovementPermille: baseline.SlingshotAimMovementPermille),
                Throws.TypeOf<ArgumentOutOfRangeException>(),
                "Un lance-pierre qui ne frappe pas plus fort qu'un lancer à la main n'a pas de raison d'être.");

            // Inventaire : le lance-pierre occupe une case, les cailloux sont les munitions.
            var inventory = new SandboxInventoryModel();
            Assert.That(inventory.TryAdd(new SandboxInventoryEntry(20, SandboxCarryableKind.Slingshot), out _), Is.True);
            Assert.That(inventory.HasKind(SandboxCarryableKind.Rock), Is.False, "Vide : rien à tirer.");
            Assert.That(inventory.TryAdd(new SandboxInventoryEntry(21, SandboxCarryableKind.Rock), out _), Is.True);
            Assert.That(inventory.TryAdd(new SandboxInventoryEntry(22, SandboxCarryableKind.Rock), out _), Is.True);
            Assert.That(inventory.IndexOfKind(SandboxCarryableKind.Slingshot), Is.EqualTo(0));
            Assert.That(inventory.IndexOfKind(SandboxCarryableKind.Trophy), Is.EqualTo(-1));
            Assert.That(inventory.Select(0), Is.True);
            Assert.That(inventory.ActiveEntry?.Kind, Is.EqualTo(SandboxCarryableKind.Slingshot));
            Assert.That(inventory.TryFindFirstOfKind(SandboxCarryableKind.Rock, out var ammo), Is.True);
            Assert.That(ammo.ObjectId, Is.EqualTo(21), "Le premier caillou par ordre de case part en premier.");
            Assert.That(inventory.TryRemoveObject(ammo.ObjectId, out _), Is.True);
            Assert.That(inventory.ActiveEntry?.Kind, Is.EqualTo(SandboxCarryableKind.Slingshot),
                "Tirer ne change pas la main active : le lance-pierre reste tenu.");
            Assert.That(inventory.TryFindFirstOfKind(SandboxCarryableKind.Rock, out ammo), Is.True);
            Assert.That(ammo.ObjectId, Is.EqualTo(22));
            Assert.That(inventory.TryRemoveObject(ammo.ObjectId, out _), Is.True);
            Assert.That(inventory.HasKind(SandboxCarryableKind.Rock), Is.False);
            Assert.That(inventory.TryAdd(new SandboxInventoryEntry(23, SandboxCarryableKind.Rock), out _), Is.True,
                "Recharger, c'est ramasser un caillou.");
            Assert.That(inventory.HasKind(SandboxCarryableKind.Rock), Is.True);

            // Énergie : un tir coûte SlingshotEnergyCost, jamais pendant un KO.
            var model = new SandboxPlayerModel(baseline);
            Assert.That(model.TrySpendSlingshotShot(), Is.True);
            Assert.That(model.State.Energy, Is.EqualTo(baseline.MaximumEnergy - baseline.SlingshotEnergyCost));
            var knockout = model.ApplyDamage(baseline.MaximumHealth, SandboxDamageKind.SlingshotRock);
            Assert.That(knockout.KnockedOut, Is.True);
            Assert.That(model.TrySpendSlingshotShot(), Is.False);
        }

        [Test]
        public void Sprint_DrainsByTickCadenceAndTrophyCostsFiveTimesMore()
        {
            var normal = new SandboxPlayerModel(SandboxGameplayConfig.Baseline60Hz);
            var trophy = new SandboxPlayerModel(SandboxGameplayConfig.Baseline60Hz);

            for (var tick = 0; tick < 6; tick++)
            {
                normal.AdvanceTick(true, false);
                trophy.AdvanceTick(true, true);
            }

            Assert.That(normal.State.Energy, Is.EqualTo(98));
            Assert.That(trophy.State.Energy, Is.EqualTo(90));
            Assert.That(normal.State.SprintingLastTick, Is.True);
            Assert.That(trophy.State.SprintingLastTick, Is.True);
        }

        [Test]
        public void ActionsAndRegeneration_UseEnergyAndWaitForTheConfiguredDelay()
        {
            var model = new SandboxPlayerModel(SandboxGameplayConfig.Baseline60Hz);

            Assert.That(model.TrySpendPunch(), Is.True);
            Assert.That(model.TrySpendThrow(), Is.True);
            Assert.That(model.State.Energy, Is.EqualTo(57));

            for (var tick = 0; tick < 60; tick++)
                model.AdvanceTick(false, false);
            Assert.That(model.State.Energy, Is.EqualTo(57), "Pas de régénération pendant le délai d'une seconde.");

            for (var tick = 0; tick < 4; tick++)
                model.AdvanceTick(false, false);
            Assert.That(model.State.Energy, Is.EqualTo(58));
        }

        [Test]
        public void Push_IsChargedOnlyOnItsCadenceAndOncePerCommandTick()
        {
            var model = new SandboxPlayerModel(SandboxGameplayConfig.Baseline60Hz);

            Assert.That(model.TryConsumePush(40u), Is.True);
            Assert.That(model.State.Energy, Is.EqualTo(99));
            Assert.That(model.TryConsumePush(40u), Is.True, "Le même tick doit être idempotent.");
            Assert.That(model.State.Energy, Is.EqualTo(99));
            Assert.That(model.TryConsumePush(41u), Is.True);
            Assert.That(model.TryConsumePush(42u), Is.True);
            Assert.That(model.State.Energy, Is.EqualTo(99));
            Assert.That(model.TryConsumePush(43u), Is.True);
            Assert.That(model.State.Energy, Is.EqualTo(99));
            Assert.That(model.TryConsumePush(44u), Is.True);
            Assert.That(model.State.Energy, Is.EqualTo(98));
        }

        [Test]
        public void FourPunches_KnockOutThenStandUpOnlyByRequestAfterTheFloorDelay()
        {
            var config = SandboxGameplayConfig.Baseline60Hz;
            var victim = new SandboxPlayerModel(config);

            for (var hit = 0; hit < 4; hit++)
                victim.ApplyDamage(config.PunchDamage, SandboxDamageKind.Punch);

            Assert.That(victim.State.LifeState, Is.EqualTo(SandboxLifeState.KnockedOut));
            Assert.That(victim.State.Health, Is.Zero);
            Assert.That(victim.ApplyDamage(1, SandboxDamageKind.World).Applied, Is.False);

            // Marteler Espace pendant le délai au sol ne relève pas.
            for (var tick = 0u; tick < config.KnockoutDurationTicks; tick++)
            {
                victim.AdvanceTick(false, false, standUpRequested: true);
                if (tick < config.KnockoutDurationTicks - 1u)
                    Assert.That(victim.State.LifeState, Is.EqualTo(SandboxLifeState.KnockedOut));
            }
            // Le dernier tick du délai portait déjà la demande : relevé accepté.
            Assert.That(victim.State.LifeState, Is.EqualTo(SandboxLifeState.Alive));
            Assert.That(victim.State.Health, Is.EqualTo(config.RecoveryHealth));
            Assert.That(victim.State.Energy, Is.EqualTo(config.MaximumEnergy));
            Assert.That(victim.State.ProtectionTicksRemaining, Is.EqualTo(config.RecoveryProtectionTicks));
            Assert.That(victim.ApplyDamage(1, SandboxDamageKind.World).Applied, Is.False);

            // Sans demande, on reste au sol indéfiniment ; la demande relève.
            var idle = new SandboxPlayerModel(config);
            idle.ApplyDamage(config.MaximumHealth, SandboxDamageKind.Punch);
            for (var tick = 0u; tick < config.KnockoutDurationTicks * 3u; tick++)
                idle.AdvanceTick(false, false);
            Assert.That(idle.State.LifeState, Is.EqualTo(SandboxLifeState.KnockedOut));
            idle.AdvanceTick(false, false, standUpRequested: true);
            Assert.That(idle.State.LifeState, Is.EqualTo(SandboxLifeState.Alive));
        }

        [Test]
        public void Trophy_SlowsMovementAndKnockoutStopsItEntirely()
        {
            var config = SandboxGameplayConfig.Baseline60Hz;
            var model = new SandboxPlayerModel(config);

            Assert.That(model.MovementPermille(false), Is.EqualTo(1000));
            Assert.That(model.MovementPermille(true), Is.EqualTo(750));
            model.ApplyDamage(100, SandboxDamageKind.World);
            Assert.That(model.MovementPermille(false), Is.Zero);
            Assert.That(model.MovementPermille(true), Is.Zero);
            Assert.That(model.TrySpendPunch(), Is.False);
        }

        [Test]
        public void Inventory_UsesThreeExplicitSlotsAndRejectsDuplicates()
        {
            var inventory = new SandboxInventoryModel();

            Assert.That(inventory.TryAdd(new SandboxInventoryEntry(10, SandboxCarryableKind.Rock), out var first), Is.True);
            Assert.That(first, Is.EqualTo(0));
            Assert.That(inventory.TryAdd(new SandboxInventoryEntry(11, SandboxCarryableKind.Trophy), out var second), Is.True);
            Assert.That(second, Is.EqualTo(1));
            Assert.That(inventory.TryAdd(new SandboxInventoryEntry(12, SandboxCarryableKind.Rock), out var third), Is.True);
            Assert.That(third, Is.EqualTo(2));
            Assert.That(inventory.IsFull, Is.True);
            Assert.That(inventory.HasTrophy, Is.True);
            Assert.That(inventory.TryAdd(new SandboxInventoryEntry(10, SandboxCarryableKind.Rock), out _), Is.False);
            Assert.That(inventory.Select(1), Is.True);
            Assert.That(inventory.TryRemoveActive(out var removed), Is.True);
            Assert.That(removed.ObjectId, Is.EqualTo(11));
            Assert.That(inventory.HasTrophy, Is.False);
            Assert.That(inventory.Count, Is.EqualTo(2));
            Assert.That(inventory.Select(1), Is.True, "Une case vide peut libérer la main active.");
            Assert.That(inventory.ActiveEntry.HasValue, Is.False);
            Assert.That(inventory.TryRemoveAny(out var remaining), Is.True);
            Assert.That(remaining.ObjectId, Is.EqualTo(10));
            Assert.That(inventory.TryRemoveAny(out remaining), Is.True);
            Assert.That(remaining.ObjectId, Is.EqualTo(12));
            Assert.That(inventory.TryRemoveAny(out _), Is.False);
            Assert.That(inventory.Count, Is.Zero);
        }

        [Test]
        public void Inventory_RejectsInvalidEntriesAndSlots()
        {
            Assert.That(
                () => new SandboxInventoryEntry(-1, SandboxCarryableKind.Rock),
                Throws.TypeOf<ArgumentOutOfRangeException>());
            Assert.That(
                () => new SandboxInventoryEntry(1, SandboxCarryableKind.None),
                Throws.TypeOf<ArgumentOutOfRangeException>());
            var inventory = new SandboxInventoryModel();
            Assert.That(() => inventory.Select(3), Throws.TypeOf<ArgumentOutOfRangeException>());
        }

        [Test]
        public void Round_CountsDownPlaysCompletesAndRequestsAReset()
        {
            var config = new SandboxRoundConfig(1, 2u, 3u, 2u);
            var round = new SandboxRoundModel(config);

            Assert.That(round.AdvanceTick(1), Is.EqualTo(SandboxRoundEvents.CountdownStarted));
            Assert.That(round.State.Phase, Is.EqualTo(SandboxRoundPhase.Countdown));
            Assert.That(round.AdvanceTick(1), Is.EqualTo(SandboxRoundEvents.None));
            var started = round.AdvanceTick(1);
            Assert.That(started.HasFlag(SandboxRoundEvents.RoundStarted), Is.True);
            Assert.That(started.HasFlag(SandboxRoundEvents.ResetRequested), Is.True);
            Assert.That(round.TryComplete(17), Is.True);
            Assert.That(round.State.WinnerObjectId, Is.EqualTo(17));
            Assert.That(round.AdvanceTick(1), Is.EqualTo(SandboxRoundEvents.None));
            var reset = round.AdvanceTick(1);
            Assert.That(reset.HasFlag(SandboxRoundEvents.ResetRequested), Is.True);
            Assert.That(reset.HasFlag(SandboxRoundEvents.CountdownStarted), Is.True);
            Assert.That(round.State.RoundNumber, Is.EqualTo(2u));
        }
    }
}
