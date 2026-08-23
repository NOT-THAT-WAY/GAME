using System;

namespace NotThatWay.Game.Sandbox
{
    /// <summary>
    /// Réglages purs de la fondation gameplay du sandbox. Les valeurs sont des
    /// baselines de playtest, jamais des constantes de production implicites.
    /// Les durées sont exprimées en ticks afin que Mac, Windows, l'hôte et les
    /// tests rendent le même verdict.
    /// </summary>
    public readonly struct SandboxGameplayConfig : IEquatable<SandboxGameplayConfig>
    {
        public const int PermilleScale = 1000;

        public SandboxGameplayConfig(
            ushort tickRate,
            int maximumHealth,
            int maximumEnergy,
            int punchDamage,
            int rockDamage,
            int trophyDamage,
            int punchEnergyCost,
            int throwEnergyCost,
            uint sprintDrainIntervalTicks,
            int sprintDrainAmount,
            uint pushDrainIntervalTicks,
            int pushDrainAmount,
            int trophySprintDrainMultiplier,
            uint energyRegenerationDelayTicks,
            uint energyRegenerationIntervalTicks,
            int energyRegenerationAmount,
            uint healthRegenerationDelayTicks,
            uint healthRegenerationIntervalTicks,
            int healthRegenerationAmount,
            uint knockoutDurationTicks,
            int recoveryHealth,
            uint recoveryProtectionTicks,
            int trophyMovementPermille,
            int slingshotDamage,
            int slingshotEnergyCost,
            int slingshotAmmoCapacity,
            uint slingshotChargeTicks,
            int slingshotMinimumPowerPermille,
            uint slingshotDropHoldTicks,
            int slingshotAimMovementPermille)
        {
            TickRate = tickRate;
            MaximumHealth = maximumHealth;
            MaximumEnergy = maximumEnergy;
            PunchDamage = punchDamage;
            RockDamage = rockDamage;
            TrophyDamage = trophyDamage;
            PunchEnergyCost = punchEnergyCost;
            ThrowEnergyCost = throwEnergyCost;
            SprintDrainIntervalTicks = sprintDrainIntervalTicks;
            SprintDrainAmount = sprintDrainAmount;
            PushDrainIntervalTicks = pushDrainIntervalTicks;
            PushDrainAmount = pushDrainAmount;
            TrophySprintDrainMultiplier = trophySprintDrainMultiplier;
            EnergyRegenerationDelayTicks = energyRegenerationDelayTicks;
            EnergyRegenerationIntervalTicks = energyRegenerationIntervalTicks;
            EnergyRegenerationAmount = energyRegenerationAmount;
            HealthRegenerationDelayTicks = healthRegenerationDelayTicks;
            HealthRegenerationIntervalTicks = healthRegenerationIntervalTicks;
            HealthRegenerationAmount = healthRegenerationAmount;
            KnockoutDurationTicks = knockoutDurationTicks;
            RecoveryHealth = recoveryHealth;
            RecoveryProtectionTicks = recoveryProtectionTicks;
            TrophyMovementPermille = trophyMovementPermille;
            SlingshotDamage = slingshotDamage;
            SlingshotEnergyCost = slingshotEnergyCost;
            SlingshotAmmoCapacity = slingshotAmmoCapacity;
            SlingshotChargeTicks = slingshotChargeTicks;
            SlingshotMinimumPowerPermille = slingshotMinimumPowerPermille;
            SlingshotDropHoldTicks = slingshotDropHoldTicks;
            SlingshotAimMovementPermille = slingshotAimMovementPermille;
            Validate();
        }

        public ushort TickRate { get; }
        public int MaximumHealth { get; }
        public int MaximumEnergy { get; }
        public int PunchDamage { get; }
        public int RockDamage { get; }
        public int TrophyDamage { get; }
        public int PunchEnergyCost { get; }
        public int ThrowEnergyCost { get; }
        public uint SprintDrainIntervalTicks { get; }
        public int SprintDrainAmount { get; }
        public uint PushDrainIntervalTicks { get; }
        public int PushDrainAmount { get; }
        public int TrophySprintDrainMultiplier { get; }
        public uint EnergyRegenerationDelayTicks { get; }
        public uint EnergyRegenerationIntervalTicks { get; }
        public int EnergyRegenerationAmount { get; }
        public uint HealthRegenerationDelayTicks { get; }
        public uint HealthRegenerationIntervalTicks { get; }
        public int HealthRegenerationAmount { get; }
        public uint KnockoutDurationTicks { get; }
        public int RecoveryHealth { get; }
        public uint RecoveryProtectionTicks { get; }
        public int TrophyMovementPermille { get; }

        /// <summary>
        /// Lance-pierre ramassable. Ses cailloux sont une réserve à part des trois
        /// cases (jusqu'à <see cref="SlingshotAmmoCapacity"/>), rechargée en
        /// ramassant au sol. Le tir se charge en tenant le bouton : la puissance
        /// va de <see cref="SlingshotMinimumPowerPermille"/> à 1000 ‰ sur
        /// <see cref="SlingshotChargeTicks"/> ticks et règle vitesse et dégâts,
        /// <see cref="SlingshotDamage"/> étant le maximum. Tenir le bouton
        /// lance-pierre <see cref="SlingshotDropHoldTicks"/> ticks le lâche.
        /// </summary>
        public int SlingshotDamage { get; }
        public int SlingshotEnergyCost { get; }
        public int SlingshotAmmoCapacity { get; }
        public uint SlingshotChargeTicks { get; }
        public int SlingshotMinimumPowerPermille { get; }
        public uint SlingshotDropHoldTicks { get; }
        /// <summary>Vitesse de déplacement pendant qu'on bande le lance-pierre : on vise, on ne court pas.</summary>
        public int SlingshotAimMovementPermille { get; }

        /// <summary>
        /// Baseline acceptée pour le sandbox à 60 Hz : valeurs publiques 0–100,
        /// saut et déplacement restant dans PlayerSimulationConfig.
        /// </summary>
        public static SandboxGameplayConfig Baseline60Hz => new(
            60,
            100,
            100,
            25,
            30,
            10,
            25,
            18,
            5u,
            1,
            4u,
            1,
            5,
            60u,
            4u,
            1,
            300u,
            10u,
            1,
            240u,
            40,
            60u,
            750,
            45,
            14,
            5,
            72u,
            350,
            30u,
            650);

        public void Validate()
        {
            if (TickRate == 0)
                throw new ArgumentOutOfRangeException(nameof(TickRate));
            EnsurePositive(MaximumHealth, nameof(MaximumHealth));
            EnsurePositive(MaximumEnergy, nameof(MaximumEnergy));
            EnsureRange(PunchDamage, 1, MaximumHealth, nameof(PunchDamage));
            EnsureRange(RockDamage, 1, MaximumHealth, nameof(RockDamage));
            EnsureRange(TrophyDamage, 1, MaximumHealth, nameof(TrophyDamage));
            EnsureRange(PunchEnergyCost, 1, MaximumEnergy, nameof(PunchEnergyCost));
            EnsureRange(ThrowEnergyCost, 1, MaximumEnergy, nameof(ThrowEnergyCost));
            EnsurePositive(SprintDrainIntervalTicks, nameof(SprintDrainIntervalTicks));
            EnsureRange(SprintDrainAmount, 1, MaximumEnergy, nameof(SprintDrainAmount));
            EnsurePositive(PushDrainIntervalTicks, nameof(PushDrainIntervalTicks));
            EnsureRange(PushDrainAmount, 1, MaximumEnergy, nameof(PushDrainAmount));
            EnsurePositive(TrophySprintDrainMultiplier, nameof(TrophySprintDrainMultiplier));
            if ((long)SprintDrainAmount * TrophySprintDrainMultiplier > MaximumEnergy)
            {
                throw new ArgumentOutOfRangeException(
                    nameof(TrophySprintDrainMultiplier),
                    "Un prélèvement de sprint avec trophée ne peut dépasser l'énergie maximale.");
            }
            EnsurePositive(EnergyRegenerationIntervalTicks, nameof(EnergyRegenerationIntervalTicks));
            EnsureRange(EnergyRegenerationAmount, 1, MaximumEnergy, nameof(EnergyRegenerationAmount));
            EnsurePositive(HealthRegenerationIntervalTicks, nameof(HealthRegenerationIntervalTicks));
            EnsureRange(HealthRegenerationAmount, 1, MaximumHealth, nameof(HealthRegenerationAmount));
            EnsurePositive(KnockoutDurationTicks, nameof(KnockoutDurationTicks));
            EnsureRange(RecoveryHealth, 1, MaximumHealth, nameof(RecoveryHealth));
            EnsureRange(
                TrophyMovementPermille,
                1,
                PermilleScale,
                nameof(TrophyMovementPermille));
            EnsureRange(SlingshotDamage, 1, MaximumHealth, nameof(SlingshotDamage));
            if (SlingshotDamage <= RockDamage)
            {
                throw new ArgumentOutOfRangeException(
                    nameof(SlingshotDamage),
                    "Le lance-pierre doit blesser plus qu'un caillou lancé à la main.");
            }
            EnsureRange(SlingshotEnergyCost, 1, MaximumEnergy, nameof(SlingshotEnergyCost));
            EnsureRange(SlingshotAmmoCapacity, 1, 64, nameof(SlingshotAmmoCapacity));
            EnsurePositive(SlingshotChargeTicks, nameof(SlingshotChargeTicks));
            EnsureRange(
                SlingshotMinimumPowerPermille,
                1,
                PermilleScale,
                nameof(SlingshotMinimumPowerPermille));
            EnsurePositive(SlingshotDropHoldTicks, nameof(SlingshotDropHoldTicks));
            EnsureRange(
                SlingshotAimMovementPermille,
                1,
                PermilleScale,
                nameof(SlingshotAimMovementPermille));
        }

        public bool Equals(SandboxGameplayConfig other) =>
            TickRate == other.TickRate &&
            MaximumHealth == other.MaximumHealth &&
            MaximumEnergy == other.MaximumEnergy &&
            PunchDamage == other.PunchDamage &&
            RockDamage == other.RockDamage &&
            TrophyDamage == other.TrophyDamage &&
            PunchEnergyCost == other.PunchEnergyCost &&
            ThrowEnergyCost == other.ThrowEnergyCost &&
            SprintDrainIntervalTicks == other.SprintDrainIntervalTicks &&
            SprintDrainAmount == other.SprintDrainAmount &&
            PushDrainIntervalTicks == other.PushDrainIntervalTicks &&
            PushDrainAmount == other.PushDrainAmount &&
            TrophySprintDrainMultiplier == other.TrophySprintDrainMultiplier &&
            EnergyRegenerationDelayTicks == other.EnergyRegenerationDelayTicks &&
            EnergyRegenerationIntervalTicks == other.EnergyRegenerationIntervalTicks &&
            EnergyRegenerationAmount == other.EnergyRegenerationAmount &&
            HealthRegenerationDelayTicks == other.HealthRegenerationDelayTicks &&
            HealthRegenerationIntervalTicks == other.HealthRegenerationIntervalTicks &&
            HealthRegenerationAmount == other.HealthRegenerationAmount &&
            KnockoutDurationTicks == other.KnockoutDurationTicks &&
            RecoveryHealth == other.RecoveryHealth &&
            RecoveryProtectionTicks == other.RecoveryProtectionTicks &&
            TrophyMovementPermille == other.TrophyMovementPermille &&
            SlingshotDamage == other.SlingshotDamage &&
            SlingshotEnergyCost == other.SlingshotEnergyCost &&
            SlingshotAmmoCapacity == other.SlingshotAmmoCapacity &&
            SlingshotChargeTicks == other.SlingshotChargeTicks &&
            SlingshotMinimumPowerPermille == other.SlingshotMinimumPowerPermille &&
            SlingshotDropHoldTicks == other.SlingshotDropHoldTicks &&
            SlingshotAimMovementPermille == other.SlingshotAimMovementPermille;

        public override bool Equals(object value) =>
            value is SandboxGameplayConfig other && Equals(other);

        public override int GetHashCode()
        {
            var hash = new HashCode();
            hash.Add(TickRate);
            hash.Add(MaximumHealth);
            hash.Add(MaximumEnergy);
            hash.Add(PunchDamage);
            hash.Add(RockDamage);
            hash.Add(TrophyDamage);
            hash.Add(PunchEnergyCost);
            hash.Add(ThrowEnergyCost);
            hash.Add(SprintDrainIntervalTicks);
            hash.Add(SprintDrainAmount);
            hash.Add(PushDrainIntervalTicks);
            hash.Add(PushDrainAmount);
            hash.Add(TrophySprintDrainMultiplier);
            hash.Add(EnergyRegenerationDelayTicks);
            hash.Add(EnergyRegenerationIntervalTicks);
            hash.Add(EnergyRegenerationAmount);
            hash.Add(HealthRegenerationDelayTicks);
            hash.Add(HealthRegenerationIntervalTicks);
            hash.Add(HealthRegenerationAmount);
            hash.Add(KnockoutDurationTicks);
            hash.Add(RecoveryHealth);
            hash.Add(RecoveryProtectionTicks);
            hash.Add(TrophyMovementPermille);
            hash.Add(SlingshotDamage);
            hash.Add(SlingshotEnergyCost);
            hash.Add(SlingshotAmmoCapacity);
            hash.Add(SlingshotChargeTicks);
            hash.Add(SlingshotMinimumPowerPermille);
            hash.Add(SlingshotDropHoldTicks);
            hash.Add(SlingshotAimMovementPermille);
            return hash.ToHashCode();
        }

        private static void EnsurePositive(int value, string name)
        {
            if (value <= 0)
                throw new ArgumentOutOfRangeException(name);
        }

        private static void EnsurePositive(uint value, string name)
        {
            if (value == 0u)
                throw new ArgumentOutOfRangeException(name);
        }

        private static void EnsureRange(int value, int minimum, int maximum, string name)
        {
            if (value < minimum || value > maximum)
                throw new ArgumentOutOfRangeException(name);
        }
    }
}
