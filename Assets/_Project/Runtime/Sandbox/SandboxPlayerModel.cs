using System;
using NotThatWay.Game.Simulation;

namespace NotThatWay.Game.Sandbox
{
    public enum SandboxLifeState : byte
    {
        Alive = 0,
        KnockedOut = 1
    }

    public enum SandboxDamageKind : byte
    {
        Punch = 0,
        Rock = 1,
        Trophy = 2,
        World = 3
    }

    [Flags]
    public enum SandboxPlayerEvents : ushort
    {
        None = 0,
        HealthChanged = 1 << 0,
        EnergyChanged = 1 << 1,
        KnockoutStarted = 1 << 2,
        Recovered = 1 << 3,
        DamageRejected = 1 << 4,
        ActionRejected = 1 << 5
    }

    /// <summary>Snapshot complet et indépendant du framerate du joueur sandbox.</summary>
    public readonly struct SandboxPlayerState : IEquatable<SandboxPlayerState>
    {
        public SandboxPlayerState(
            uint tick,
            int health,
            int energy,
            SandboxLifeState lifeState,
            uint knockoutTicksRemaining,
            uint protectionTicksRemaining,
            uint energyRegenerationDelayTicksRemaining,
            uint energyRegenerationCadenceTicks,
            uint healthRegenerationDelayTicksRemaining,
            uint healthRegenerationCadenceTicks,
            bool sprintingLastTick,
            uint sprintCadenceTicks,
            bool pushingLastTick,
            uint pushCadenceTicks,
            bool hasConsumedPushTick,
            uint lastConsumedPushTick)
        {
            Tick = tick;
            Health = health;
            Energy = energy;
            LifeState = lifeState;
            KnockoutTicksRemaining = knockoutTicksRemaining;
            ProtectionTicksRemaining = protectionTicksRemaining;
            EnergyRegenerationDelayTicksRemaining = energyRegenerationDelayTicksRemaining;
            EnergyRegenerationCadenceTicks = energyRegenerationCadenceTicks;
            HealthRegenerationDelayTicksRemaining = healthRegenerationDelayTicksRemaining;
            HealthRegenerationCadenceTicks = healthRegenerationCadenceTicks;
            SprintingLastTick = sprintingLastTick;
            SprintCadenceTicks = sprintCadenceTicks;
            PushingLastTick = pushingLastTick;
            PushCadenceTicks = pushCadenceTicks;
            HasConsumedPushTick = hasConsumedPushTick;
            LastConsumedPushTick = lastConsumedPushTick;
        }

        public uint Tick { get; }
        public int Health { get; }
        public int Energy { get; }
        public SandboxLifeState LifeState { get; }
        public uint KnockoutTicksRemaining { get; }
        public uint ProtectionTicksRemaining { get; }
        public uint EnergyRegenerationDelayTicksRemaining { get; }
        public uint EnergyRegenerationCadenceTicks { get; }
        public uint HealthRegenerationDelayTicksRemaining { get; }
        public uint HealthRegenerationCadenceTicks { get; }
        public bool SprintingLastTick { get; }
        public uint SprintCadenceTicks { get; }
        public bool PushingLastTick { get; }
        public uint PushCadenceTicks { get; }
        public bool HasConsumedPushTick { get; }
        public uint LastConsumedPushTick { get; }
        public bool IsAlive => LifeState == SandboxLifeState.Alive;

        public bool Equals(SandboxPlayerState other) =>
            Tick == other.Tick &&
            Health == other.Health &&
            Energy == other.Energy &&
            LifeState == other.LifeState &&
            KnockoutTicksRemaining == other.KnockoutTicksRemaining &&
            ProtectionTicksRemaining == other.ProtectionTicksRemaining &&
            EnergyRegenerationDelayTicksRemaining == other.EnergyRegenerationDelayTicksRemaining &&
            EnergyRegenerationCadenceTicks == other.EnergyRegenerationCadenceTicks &&
            HealthRegenerationDelayTicksRemaining == other.HealthRegenerationDelayTicksRemaining &&
            HealthRegenerationCadenceTicks == other.HealthRegenerationCadenceTicks &&
            SprintingLastTick == other.SprintingLastTick &&
            SprintCadenceTicks == other.SprintCadenceTicks &&
            PushingLastTick == other.PushingLastTick &&
            PushCadenceTicks == other.PushCadenceTicks &&
            HasConsumedPushTick == other.HasConsumedPushTick &&
            LastConsumedPushTick == other.LastConsumedPushTick;

        public override bool Equals(object value) =>
            value is SandboxPlayerState other && Equals(other);

        public override int GetHashCode()
        {
            var hash = new HashCode();
            hash.Add(Tick);
            hash.Add(Health);
            hash.Add(Energy);
            hash.Add(LifeState);
            hash.Add(KnockoutTicksRemaining);
            hash.Add(ProtectionTicksRemaining);
            hash.Add(EnergyRegenerationDelayTicksRemaining);
            hash.Add(EnergyRegenerationCadenceTicks);
            hash.Add(HealthRegenerationDelayTicksRemaining);
            hash.Add(HealthRegenerationCadenceTicks);
            hash.Add(SprintingLastTick);
            hash.Add(SprintCadenceTicks);
            hash.Add(PushingLastTick);
            hash.Add(PushCadenceTicks);
            hash.Add(HasConsumedPushTick);
            hash.Add(LastConsumedPushTick);
            return hash.ToHashCode();
        }
    }

    public readonly struct SandboxPlayerTickResult
    {
        public SandboxPlayerTickResult(
            SandboxPlayerState previous,
            SandboxPlayerState current,
            SandboxPlayerEvents events,
            bool sprintAllowed)
        {
            Previous = previous;
            Current = current;
            Events = events;
            SprintAllowed = sprintAllowed;
        }

        public SandboxPlayerState Previous { get; }
        public SandboxPlayerState Current { get; }
        public SandboxPlayerEvents Events { get; }
        public bool SprintAllowed { get; }
    }

    public readonly struct SandboxDamageResult
    {
        public SandboxDamageResult(
            SandboxPlayerState previous,
            SandboxPlayerState current,
            SandboxPlayerEvents events,
            SandboxDamageKind kind,
            int appliedDamage)
        {
            Previous = previous;
            Current = current;
            Events = events;
            Kind = kind;
            AppliedDamage = appliedDamage;
        }

        public SandboxPlayerState Previous { get; }
        public SandboxPlayerState Current { get; }
        public SandboxPlayerEvents Events { get; }
        public SandboxDamageKind Kind { get; }
        public int AppliedDamage { get; }
        public bool Applied => AppliedDamage > 0;
        public bool KnockedOut => (Events & SandboxPlayerEvents.KnockoutStarted) != 0;
    }

    /// <summary>
    /// Modèle unique des ressources et du KO. Il ne connaît ni GameObject, ni
    /// FishNet, ni animation : l'adaptateur réseau applique les effets visuels.
    /// </summary>
    public sealed class SandboxPlayerModel
    {
        private readonly SandboxGameplayConfig _config;
        private SandboxPlayerState _state;

        public SandboxPlayerModel(SandboxGameplayConfig config, uint initialTick = 0u)
        {
            config.Validate();
            _config = config;
            _state = FullState(initialTick);
        }

        public SandboxGameplayConfig Config => _config;
        public SandboxPlayerState State => _state;
        public bool CanAct => _state.IsAlive;
        public bool IsProtected => _state.ProtectionTicksRemaining > 0u;

        public bool CanSprint(bool carryingTrophy)
        {
            if (!CanAct)
                return false;
            var amount = _config.SprintDrainAmount *
                         (carryingTrophy ? _config.TrophySprintDrainMultiplier : 1);
            return _state.Energy >= amount;
        }

        public int MovementPermille(bool carryingTrophy) =>
            !CanAct
                ? 0
                : carryingTrophy
                    ? _config.TrophyMovementPermille
                    : SandboxGameplayConfig.PermilleScale;

        public SandboxPlayerTickResult AdvanceTick(
            bool sprintRequested,
            bool carryingTrophy,
            bool standUpRequested = false)
        {
            var previous = _state;
            var tick = TickMath.Next(previous.Tick);
            var health = previous.Health;
            var energy = previous.Energy;
            var life = previous.LifeState;
            var knockout = previous.KnockoutTicksRemaining;
            var protection = previous.ProtectionTicksRemaining;
            var energyDelay = previous.EnergyRegenerationDelayTicksRemaining;
            var energyCadence = previous.EnergyRegenerationCadenceTicks;
            var healthDelay = previous.HealthRegenerationDelayTicksRemaining;
            var healthCadence = previous.HealthRegenerationCadenceTicks;
            var sprinting = false;
            var sprintCadence = previous.SprintCadenceTicks;
            var events = SandboxPlayerEvents.None;

            if (protection > 0u)
                protection--;

            if (life == SandboxLifeState.KnockedOut)
            {
                sprintCadence = 0u;
                if (knockout > 0u)
                    knockout--;
                // Le compte à rebours n'est plus qu'un délai minimal au sol : une
                // fois écoulé, le joueur reste KO tant qu'il ne demande pas à se
                // relever (Espace), et se relève alors avec les mêmes restaurations.
                if (knockout == 0u && standUpRequested)
                {
                    life = SandboxLifeState.Alive;
                    health = _config.RecoveryHealth;
                    energy = _config.MaximumEnergy;
                    protection = _config.RecoveryProtectionTicks;
                    healthDelay = _config.HealthRegenerationDelayTicks;
                    healthCadence = 0u;
                    energyDelay = 0u;
                    energyCadence = 0u;
                    events |= SandboxPlayerEvents.Recovered |
                              SandboxPlayerEvents.HealthChanged |
                              SandboxPlayerEvents.EnergyChanged;
                }
            }
            else
            {
                var sprintAmount = _config.SprintDrainAmount *
                                   (carryingTrophy ? _config.TrophySprintDrainMultiplier : 1);
                sprinting = sprintRequested && energy >= sprintAmount;
                if (sprinting)
                {
                    if (!previous.SprintingLastTick || sprintCadence == 0u)
                    {
                        energy -= sprintAmount;
                        sprintCadence = _config.SprintDrainIntervalTicks - 1u;
                        energyDelay = _config.EnergyRegenerationDelayTicks;
                        energyCadence = 0u;
                        events |= SandboxPlayerEvents.EnergyChanged;
                    }
                    else
                    {
                        sprintCadence--;
                    }
                }
                else
                {
                    sprintCadence = 0u;
                }

                if (!sprinting)
                {
                    Regenerate(
                        ref energy,
                        _config.MaximumEnergy,
                        ref energyDelay,
                        ref energyCadence,
                        _config.EnergyRegenerationIntervalTicks,
                        _config.EnergyRegenerationAmount,
                        SandboxPlayerEvents.EnergyChanged,
                        ref events);
                }

                Regenerate(
                    ref health,
                    _config.MaximumHealth,
                    ref healthDelay,
                    ref healthCadence,
                    _config.HealthRegenerationIntervalTicks,
                    _config.HealthRegenerationAmount,
                    SandboxPlayerEvents.HealthChanged,
                    ref events);
            }

            _state = new SandboxPlayerState(
                tick,
                health,
                energy,
                life,
                knockout,
                protection,
                energyDelay,
                energyCadence,
                healthDelay,
                healthCadence,
                sprinting,
                sprintCadence,
                false,
                previous.PushCadenceTicks,
                previous.HasConsumedPushTick,
                previous.LastConsumedPushTick);
            return new SandboxPlayerTickResult(previous, _state, events, sprinting);
        }

        public bool TrySpendPunch()
        {
            if (!CanAct)
                return false;
            return TrySpendEnergy(_config.PunchEnergyCost);
        }

        public bool TrySpendThrow()
        {
            if (!CanAct)
                return false;
            return TrySpendEnergy(_config.ThrowEnergyCost);
        }

        /// <summary>
        /// Coût continu appliqué uniquement après contact serveur accepté. Un
        /// même tick de commande ne peut jamais être facturé deux fois.
        /// </summary>
        public bool TryConsumePush(uint commandTick)
        {
            if (!CanAct)
                return false;
            if (_state.HasConsumedPushTick && _state.LastConsumedPushTick == commandTick)
                return _state.PushingLastTick;

            var contiguous = _state.HasConsumedPushTick &&
                             TickMath.IsNext(commandTick, _state.LastConsumedPushTick);
            var cadence = contiguous ? _state.PushCadenceTicks : 0u;
            var energy = _state.Energy;
            if (cadence == 0u)
            {
                if (energy < _config.PushDrainAmount)
                {
                    _state = WithPushState(commandTick, false, 0u, energy);
                    return false;
                }
                energy -= _config.PushDrainAmount;
                cadence = _config.PushDrainIntervalTicks - 1u;
            }
            else
            {
                cadence--;
            }

            _state = WithPushState(commandTick, true, cadence, energy);
            return true;
        }

        public SandboxDamageResult ApplyDamage(int damage, SandboxDamageKind kind)
        {
            if (damage <= 0)
                throw new ArgumentOutOfRangeException(nameof(damage));

            var previous = _state;
            if (!previous.IsAlive || previous.ProtectionTicksRemaining > 0u)
            {
                return new SandboxDamageResult(
                    previous,
                    previous,
                    SandboxPlayerEvents.DamageRejected,
                    kind,
                    0);
            }

            var applied = Math.Min(damage, previous.Health);
            var health = previous.Health - applied;
            var life = previous.LifeState;
            var knockout = previous.KnockoutTicksRemaining;
            var events = SandboxPlayerEvents.HealthChanged;
            if (health == 0)
            {
                life = SandboxLifeState.KnockedOut;
                knockout = _config.KnockoutDurationTicks;
                events |= SandboxPlayerEvents.KnockoutStarted;
            }

            _state = new SandboxPlayerState(
                previous.Tick,
                health,
                previous.Energy,
                life,
                knockout,
                previous.ProtectionTicksRemaining,
                previous.EnergyRegenerationDelayTicksRemaining,
                previous.EnergyRegenerationCadenceTicks,
                _config.HealthRegenerationDelayTicks,
                0u,
                false,
                0u,
                false,
                previous.PushCadenceTicks,
                previous.HasConsumedPushTick,
                previous.LastConsumedPushTick);
            return new SandboxDamageResult(previous, _state, events, kind, applied);
        }

        public void Reset(uint tick = 0u)
        {
            _state = FullState(tick);
        }

        public void RestoreState(SandboxPlayerState state)
        {
            ValidateState(state);
            _state = state;
        }

        private bool TrySpendEnergy(int amount)
        {
            var previous = _state;
            if (previous.Energy < amount)
                return false;
            _state = new SandboxPlayerState(
                previous.Tick,
                previous.Health,
                previous.Energy - amount,
                previous.LifeState,
                previous.KnockoutTicksRemaining,
                previous.ProtectionTicksRemaining,
                _config.EnergyRegenerationDelayTicks,
                0u,
                previous.HealthRegenerationDelayTicksRemaining,
                previous.HealthRegenerationCadenceTicks,
                previous.SprintingLastTick,
                previous.SprintCadenceTicks,
                previous.PushingLastTick,
                previous.PushCadenceTicks,
                previous.HasConsumedPushTick,
                previous.LastConsumedPushTick);
            return true;
        }

        private SandboxPlayerState WithPushState(
            uint commandTick,
            bool pushing,
            uint cadence,
            int energy)
        {
            var previous = _state;
            return new SandboxPlayerState(
                previous.Tick,
                previous.Health,
                energy,
                previous.LifeState,
                previous.KnockoutTicksRemaining,
                previous.ProtectionTicksRemaining,
                pushing
                    ? _config.EnergyRegenerationDelayTicks
                    : previous.EnergyRegenerationDelayTicksRemaining,
                pushing ? 0u : previous.EnergyRegenerationCadenceTicks,
                previous.HealthRegenerationDelayTicksRemaining,
                previous.HealthRegenerationCadenceTicks,
                previous.SprintingLastTick,
                previous.SprintCadenceTicks,
                pushing,
                cadence,
                true,
                commandTick);
        }

        private SandboxPlayerState FullState(uint tick) => new(
            tick,
            _config.MaximumHealth,
            _config.MaximumEnergy,
            SandboxLifeState.Alive,
            0u,
            0u,
            0u,
            0u,
            0u,
            0u,
            false,
            0u,
            false,
            0u,
            false,
            0u);

        private static void Regenerate(
            ref int value,
            int maximum,
            ref uint delay,
            ref uint cadence,
            uint interval,
            int amount,
            SandboxPlayerEvents changedEvent,
            ref SandboxPlayerEvents events)
        {
            if (value >= maximum)
            {
                delay = 0u;
                cadence = 0u;
                return;
            }
            if (delay > 0u)
            {
                delay--;
                cadence = 0u;
                return;
            }
            cadence++;
            if (cadence < interval)
                return;
            cadence = 0u;
            value = Math.Min(maximum, value + amount);
            events |= changedEvent;
        }

        private void ValidateState(SandboxPlayerState state)
        {
            if (state.Health < 0 || state.Health > _config.MaximumHealth)
                throw new ArgumentOutOfRangeException(nameof(state));
            if (state.Energy < 0 || state.Energy > _config.MaximumEnergy)
                throw new ArgumentOutOfRangeException(nameof(state));
            if (state.LifeState == SandboxLifeState.Alive && state.Health == 0)
                throw new ArgumentException("Un joueur vivant doit avoir de la vie.", nameof(state));
            if (state.LifeState == SandboxLifeState.KnockedOut && state.Health != 0)
                throw new ArgumentException("Un joueur KO doit avoir zéro vie.", nameof(state));
        }
    }
}
