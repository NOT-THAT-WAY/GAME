using System;
using System.Collections.Generic;
using FishNet.Connection;
using FishNet.Object;
using FishNet.Transporting;
using FishNet.Utility.Template;
using NotThatWay.Game.PlayerSimulation;
using NotThatWay.Game.Simulation;
using UnityEngine;

namespace NotThatWay.Game.Sandbox
{
    /// <summary>
    /// Adaptateur autoritaire du modèle de vie, d'énergie et d'inventaire. Le
    /// propriétaire ne transmet que les mêmes fronts que la locomotion ; le
    /// serveur décide dépense, cible, ramassage, KO et contenu des trois cases.
    /// </summary>
    [DisallowMultipleComponent]
    [RequireComponent(typeof(PredictedPlayerMotor))]
    public sealed class SandboxPlayerGameplay : TickNetworkBehaviour
    {
        private const uint PeriodicSnapshotTicks = 30u;
        private const float PickupRangeMeters = 1.7f;

        private static readonly List<SandboxPlayerGameplay> ServerInstances = new();
        private static readonly int HitTrigger = Animator.StringToHash("Hit");
        private static readonly int KnockoutTrigger = Animator.StringToHash("Knockout");
        private static readonly int RecoverTrigger = Animator.StringToHash("Recover");
        private static readonly int PickupTrigger = Animator.StringToHash("Pickup");
        private static readonly int DropTrigger = Animator.StringToHash("Drop");
        private static readonly int DepositTrigger = Animator.StringToHash("Deposit");
        private static readonly int KnockedOutBool = Animator.StringToHash("KnockedOut");
        private static readonly int CarryKindInt = Animator.StringToHash("CarryKind");

        private readonly SandboxCarryableKind[] _observedSlots =
            new SandboxCarryableKind[SandboxInventoryModel.Capacity];

        private SandboxGameplayConfig _config;
        private SandboxPlayerModel _model;
        private SandboxInventoryModel _inventory;
        private PredictedPlayerMotor _motor;
        private Animator _animator;
        private uint _lastInventoryCommandTick;
        private bool _hasProcessedInventoryCommand;
        private SandboxPlayerState _lastPublishedState;
        private int _lastPublishedInventoryFingerprint;
        private uint _lastPublishedTick;
        private bool _hasPublished;
        private int _observedHealth;
        private int _observedEnergy;
        private SandboxLifeState _observedLifeState;
        private uint _observedKnockoutTicks;
        private uint _observedProtectionTicks;
        private int _observedActiveSlot;
        private uint _observedTick;

        public SandboxGameplayConfig Config => _config;
        public int ObservedHealth => IsServerStarted ? _model.State.Health : _observedHealth;
        public int ObservedEnergy => IsServerStarted ? _model.State.Energy : _observedEnergy;
        public SandboxLifeState ObservedLifeState =>
            IsServerStarted ? _model.State.LifeState : _observedLifeState;
        public uint ObservedKnockoutTicksRemaining =>
            IsServerStarted ? _model.State.KnockoutTicksRemaining : _observedKnockoutTicks;
        public uint ObservedProtectionTicksRemaining =>
            IsServerStarted ? _model.State.ProtectionTicksRemaining : _observedProtectionTicks;
        public int ObservedActiveSlot =>
            IsServerStarted ? _inventory.ActiveSlot : _observedActiveSlot;
        public bool IsAlive => ObservedLifeState == SandboxLifeState.Alive;
        public bool HasTrophy => IsServerStarted ? _inventory.HasTrophy : ObservedHasTrophy();
        public SandboxCarryableKind ActiveKind => IsServerStarted
            ? _inventory.ActiveEntry?.Kind ?? SandboxCarryableKind.None
            : ObservedKindAt(_observedActiveSlot);
        public int MovementSpeedPermille => IsServerStarted
            ? _model.MovementPermille(_inventory.HasTrophy)
            : !IsAlive
                ? 0
                : HasTrophy
                    ? _config.TrophyMovementPermille
                    : SandboxGameplayConfig.PermilleScale;
        public bool CanPush => IsAlive && !HasTrophy && ObservedEnergy > 0;
        public bool CanPunch =>
            IsAlive && !HasTrophy && ActiveKind == SandboxCarryableKind.None &&
            ObservedEnergy >= _config.PunchEnergyCost;
        public bool CanThrow =>
            IsAlive && ActiveKind != SandboxCarryableKind.None &&
            ObservedEnergy >= _config.ThrowEnergyCost;

        private void Awake()
        {
            _config = SandboxGameplayConfig.Baseline60Hz;
            _model = new SandboxPlayerModel(_config);
            _inventory = new SandboxInventoryModel();
            _motor = GetComponent<PredictedPlayerMotor>();
            _animator = GetComponentInChildren<Animator>(true);
            _observedHealth = _config.MaximumHealth;
            _observedEnergy = _config.MaximumEnergy;
            _observedLifeState = SandboxLifeState.Alive;
            SetTickCallbacks(TickCallback.PostTick);
        }

        public override void OnStartServer()
        {
            base.OnStartServer();
            if (!ServerInstances.Contains(this))
                ServerInstances.Add(this);
            PublishSnapshot(true);
        }

        public override void OnStopServer()
        {
            DropAllFromServer();
            ServerInstances.Remove(this);
            base.OnStopServer();
        }

        public override void OnSpawnServer(NetworkConnection connection)
        {
            base.OnSpawnServer(connection);
            if (connection == null || _model == null)
                return;
            SendSnapshotTargetRpc(
                connection,
                _model.State.Tick,
                (short)_model.State.Health,
                (short)_model.State.Energy,
                (byte)_model.State.LifeState,
                _model.State.KnockoutTicksRemaining,
                _model.State.ProtectionTicksRemaining,
                (byte)KindAt(0),
                (byte)KindAt(1),
                (byte)KindAt(2),
                (byte)_inventory.ActiveSlot);
        }

        protected override void TimeManager_OnPostTick()
        {
            if (!IsServerStarted || _motor == null ||
                !_motor.TryGetLatestAuthoritativeCommand(out var command))
            {
                return;
            }

            if (!EnsureAdvanced(command))
                return;
            if (!_hasProcessedInventoryCommand || _lastInventoryCommandTick != command.Tick)
            {
                _hasProcessedInventoryCommand = true;
                _lastInventoryCommandTick = command.Tick;
                ProcessInventoryCommand(command);
            }
            PublishSnapshot(false);
        }

        /// <summary>
        /// Filtre utilisé par la prédiction comme par le serveur : un joueur KO
        /// conserve le regard mais aucune intention physique ; le trophée coupe
        /// la poussée, et le sprint disparaît dès que son prochain prélèvement ne
        /// peut plus être payé.
        /// </summary>
        public PlayerCommand FilterCommandForSimulation(PlayerCommand command)
        {
            var alive = IsAlive;
            if (!alive)
            {
                return new PlayerCommand(
                    command.Tick,
                    0,
                    0,
                    command.LookYaw,
                    command.LookPitch,
                    PlayerCommandButtons.None);
            }

            var buttons = command.Buttons;
            if (!CanSprintForNextCharge())
                buttons &= ~PlayerCommandButtons.SprintHeld;
            if (HasTrophy)
                buttons &= ~PlayerCommandButtons.InteractHeld;
            return new PlayerCommand(
                command.Tick,
                command.MoveX,
                command.MoveY,
                command.LookYaw,
                command.LookPitch,
                buttons);
        }

        public bool TrySpendPunch(PlayerCommand command)
        {
            if (!IsServerStarted || ActiveKind != SandboxCarryableKind.None || HasTrophy)
                return false;
            if (!EnsureAdvanced(command))
                return false;
            var accepted = _model.TrySpendPunch();
            if (accepted)
                PublishSnapshot(false);
            return accepted;
        }

        public bool TryThrowActive(PlayerCommand command, Vector3 direction)
        {
            if (!IsServerStarted || !IsAlive)
                return false;
            if (!EnsureAdvanced(command))
                return false;
            if (!_inventory.ActiveEntry.HasValue)
                return false;
            var selected = _inventory.ActiveEntry.Value;
            if (!SandboxCarryable.TryFindServer(selected.ObjectId, out var carryable) ||
                !_model.TrySpendThrow() ||
                !_inventory.TryRemoveActive(out var entry))
            {
                return false;
            }

            carryable.ThrowFromServer(this, direction);
            RefreshHeldPresentations();
            PublishSnapshot(false);
            return true;
        }

        /// <summary>
        /// Verse le bidon actif : énergie, retrait de la case, puis l'objet devient
        /// une flaque posée au sol 1,1 m devant le joueur. Le verseur n'est pas
        /// épargné : il glissera comme les autres s'il repasse dessus avec de l'élan.
        /// </summary>
        public bool TryPourOilFromServer(PlayerCommand command)
        {
            if (!IsServerStarted || !IsAlive)
                return false;
            if (!EnsureAdvanced(command))
                return false;
            if (ActiveKind != SandboxCarryableKind.OilCan ||
                !_inventory.ActiveEntry.HasValue)
            {
                return false;
            }
            var entry = _inventory.ActiveEntry.Value;
            if (!SandboxCarryable.TryFindServer(entry.ObjectId, out var can) ||
                !_model.TrySpendEnergyForOilPour() ||
                !_inventory.TryRemoveActive(out _))
            {
                return false;
            }

            var forward = transform.forward;
            forward.y = 0f;
            forward = forward.sqrMagnitude > 0.0001f ? forward.normalized : Vector3.forward;
            var ground = transform.position + forward * 1.1f;
            ground.y = transform.position.y + 0.02f;
            can.PourFromServer(this, ground);
            RefreshHeldPresentations();
            PlayInventoryEvent(1);
            PublishSnapshot(false);
            return true;
        }

        public bool TryConsumePushEnergy(uint commandTick)
        {
            if (!IsServerStarted || !CanPush)
                return false;
            var accepted = _model.TryConsumePush(commandTick);
            PublishSnapshot(false);
            return accepted;
        }

        public bool ApplyDamageFromServer(
            int damage,
            SandboxDamageKind kind,
            Vector3 knockbackVelocity)
        {
            if (!IsServerStarted)
                return false;
            var result = _model.ApplyDamage(damage, kind);
            if (!result.Applied)
                return false;

            if (_motor != null)
                _motor.ApplyKnockbackFromServer(knockbackVelocity);
            if (result.KnockedOut)
                DropAllFromServer();
            PlayDamageEvent(result.KnockedOut);
            PublishSnapshot(true);
            Debug.Log(
                $"[GAME-SANDBOX-DAMAGE] target={ObjectId} kind={kind} " +
                $"damage={result.AppliedDamage} health={_model.State.Health} " +
                $"ko={result.KnockedOut} tick={_model.State.Tick}.",
                this);
            return true;
        }

        public bool TryDepositTrophyFromServer()
        {
            if (!IsServerStarted || !IsAlive || !TryFindTrophy(out var slot, out var entry))
                return false;
            if (!SandboxCarryable.TryFindServer(entry.ObjectId, out var trophy))
            {
                Debug.LogError(
                    $"[GAME-SANDBOX-TROPHY] carried trophy {entry.ObjectId} is missing.",
                    this);
                return false;
            }
            var round = SandboxRoundDirector.ServerInstance;
            if (round == null || !round.TryCompleteRound(ObjectId))
                return false;
            if (!_inventory.TryRemoveObject(entry.ObjectId, out _))
            {
                throw new InvalidOperationException(
                    $"Le trophée {entry.ObjectId} a disparu de l'inventaire pendant son dépôt.");
            }

            trophy.DepositFromServer();
            PlayInventoryEvent(2);
            RefreshHeldPresentations();
            PublishSnapshot(true);
            Debug.Log(
                $"[GAME-SANDBOX-TROPHY] deposited player={ObjectId} slot={slot}.",
                this);
            return true;
        }

        public void ResetForRoundFromServer()
        {
            if (!IsServerStarted)
                return;
            DropAllFromServer();
            _model.Reset(_model.State.Tick);
            PublishSnapshot(true);
        }

        internal static void CopyServerInstances(List<SandboxPlayerGameplay> destination)
        {
            if (destination == null)
                throw new ArgumentNullException(nameof(destination));
            destination.Clear();
            for (var index = 0; index < ServerInstances.Count; index++)
            {
                var player = ServerInstances[index];
                if (player != null && player.IsServerStarted)
                    destination.Add(player);
            }
        }

        internal static bool TryFindServer(int objectId, out SandboxPlayerGameplay player)
        {
            for (var index = 0; index < ServerInstances.Count; index++)
            {
                var candidate = ServerInstances[index];
                if (candidate != null && candidate.IsServerStarted && candidate.ObjectId == objectId)
                {
                    player = candidate;
                    return true;
                }
            }
            player = null;
            return false;
        }

        private bool EnsureAdvanced(PlayerCommand command)
        {
            if (_model.State.Tick == command.Tick)
                return true;
            if (TickMath.IsOlder(command.Tick, _model.State.Tick))
                return false;

            var missing = TickMath.Elapsed(_model.State.Tick, command.Tick);
            if (missing > 256u)
            {
                Debug.LogWarning(
                    $"[GAME-SANDBOX] Avance de ressources refusée: {missing} ticks manquants.",
                    this);
                return false;
            }

            for (var index = 1u; index <= missing; index++)
            {
                var sprint = index == missing &&
                             command.Has(PlayerCommandButtons.SprintHeld);
                var result = _model.AdvanceTick(sprint, _inventory.HasTrophy);
                if ((result.Events & SandboxPlayerEvents.Recovered) != 0)
                    PlayRecoveryEvent();
            }
            return true;
        }

        private void ProcessInventoryCommand(PlayerCommand command)
        {
            if (!IsAlive)
                return;

            if (command.Has(PlayerCommandButtons.SelectSlot1Pressed))
                _inventory.Select(0);
            if (command.Has(PlayerCommandButtons.SelectSlot2Pressed))
                _inventory.Select(1);
            if (command.Has(PlayerCommandButtons.SelectSlot3Pressed))
                _inventory.Select(2);
            if (command.Has(PlayerCommandButtons.CycleSlotPressed))
                SelectNextSlot();

            if (command.Has(PlayerCommandButtons.DropPressed))
                DropActiveFromServer();
            if (command.Has(PlayerCommandButtons.InteractPressed))
                TryPickupNearestFromServer();

            RefreshHeldPresentations();
        }

        private bool TryPickupNearestFromServer()
        {
            if (_inventory.IsFull)
                return false;
            var carryable = SandboxCarryable.FindNearestAvailableServer(
                transform.position,
                PickupRangeMeters);
            if (carryable == null)
            {
                var nearest = SandboxCarryable.FindNearestAvailableServer(
                    transform.position,
                    1000f);
                var distance = nearest == null
                    ? -1f
                    : Vector3.Distance(transform.position, nearest.transform.position);
                Debug.Log(
                    $"[GAME-SANDBOX-ITEM] pickup_rejected player={ObjectId} " +
                    $"position={transform.position} nearestDistance={distance:F2} " +
                    $"inventory={_inventory.Count}/{SandboxInventoryModel.Capacity}.",
                    this);
                return false;
            }
            var entry = new SandboxInventoryEntry(carryable.ObjectId, carryable.Kind);
            if (!_inventory.TryAdd(entry, out var slot))
                return false;

            carryable.HoldFromServer(this, slot, true);
            PlayInventoryEvent(0);
            Debug.Log(
                $"[GAME-SANDBOX-ITEM] pickup player={ObjectId} item={carryable.ObjectId} " +
                $"kind={carryable.Kind} slot={slot}.",
                this);
            return true;
        }

        private bool DropActiveFromServer()
        {
            if (!_inventory.TryRemoveActive(out var entry))
                return false;
            if (SandboxCarryable.TryFindServer(entry.ObjectId, out var carryable))
                carryable.DropFromServer(this, Vector3.zero);
            PlayInventoryEvent(1);
            Debug.Log(
                $"[GAME-SANDBOX-ITEM] drop player={ObjectId} item={entry.ObjectId} kind={entry.Kind}.",
                this);
            return true;
        }

        private void DropAllFromServer()
        {
            if (_inventory == null)
                return;
            var dropIndex = 0;
            // La case active peut volontairement être vide pour libérer les
            // mains. Un KO/reset doit tout de même lâcher les autres cases.
            while (_inventory.TryRemoveAny(out var entry))
            {
                if (SandboxCarryable.TryFindServer(entry.ObjectId, out var carryable))
                {
                    var angle = dropIndex * 120f - 60f;
                    carryable.DropFromServer(
                        this,
                        Quaternion.Euler(0f, angle, 0f) * transform.forward * 1.2f);
                }
                dropIndex++;
            }
            if (dropIndex > 0)
                PlayInventoryEvent(1);
        }

        private void SelectNextSlot()
        {
            for (var offset = 1; offset <= SandboxInventoryModel.Capacity; offset++)
            {
                var candidate = (_inventory.ActiveSlot + offset) % SandboxInventoryModel.Capacity;
                if (_inventory.Select(candidate))
                    return;
            }
        }

        private void RefreshHeldPresentations()
        {
            for (var slot = 0; slot < SandboxInventoryModel.Capacity; slot++)
            {
                var entry = _inventory.EntryAt(slot);
                if (!entry.HasValue ||
                    !SandboxCarryable.TryFindServer(entry.Value.ObjectId, out var carryable))
                {
                    continue;
                }
                carryable.HoldFromServer(this, slot, slot == _inventory.ActiveSlot);
            }
        }

        private bool TryFindTrophy(out int slot, out SandboxInventoryEntry entry)
        {
            for (slot = 0; slot < SandboxInventoryModel.Capacity; slot++)
            {
                var value = _inventory.EntryAt(slot);
                if (!value.HasValue || value.Value.Kind != SandboxCarryableKind.Trophy)
                    continue;
                entry = value.Value;
                return true;
            }
            slot = -1;
            entry = default;
            return false;
        }

        private bool CanSprintForNextCharge()
        {
            var amount = _config.SprintDrainAmount *
                         (HasTrophy ? _config.TrophySprintDrainMultiplier : 1);
            return IsAlive && ObservedEnergy >= amount;
        }

        private SandboxCarryableKind KindAt(int slot) =>
            _inventory.EntryAt(slot)?.Kind ?? SandboxCarryableKind.None;

        private SandboxCarryableKind ObservedKindAt(int slot) =>
            slot >= 0 && slot < _observedSlots.Length
                ? _observedSlots[slot]
                : SandboxCarryableKind.None;

        private bool ObservedHasTrophy()
        {
            for (var index = 0; index < _observedSlots.Length; index++)
            {
                if (_observedSlots[index] == SandboxCarryableKind.Trophy)
                    return true;
            }
            return false;
        }

        private int InventoryFingerprint()
        {
            var value = _inventory.ActiveSlot;
            for (var slot = 0; slot < SandboxInventoryModel.Capacity; slot++)
                value = value * 31 + (int)KindAt(slot);
            return value;
        }

        private static bool PublicStateChanged(
            SandboxPlayerState current,
            SandboxPlayerState previous) =>
            current.Health != previous.Health ||
            current.Energy != previous.Energy ||
            current.LifeState != previous.LifeState;

        private void PublishSnapshot(bool force)
        {
            if (!IsServerStarted)
                return;
            var state = _model.State;
            var fingerprint = InventoryFingerprint();
            var periodic = !_hasPublished ||
                           TickMath.Elapsed(_lastPublishedTick, state.Tick) >= PeriodicSnapshotTicks;
            if (!force && !periodic && !PublicStateChanged(state, _lastPublishedState) &&
                fingerprint == _lastPublishedInventoryFingerprint)
            {
                return;
            }

            _hasPublished = true;
            _lastPublishedState = state;
            _lastPublishedInventoryFingerprint = fingerprint;
            _lastPublishedTick = state.Tick;
            ReceiveSnapshotObserversRpc(
                state.Tick,
                (short)state.Health,
                (short)state.Energy,
                (byte)state.LifeState,
                state.KnockoutTicksRemaining,
                state.ProtectionTicksRemaining,
                (byte)KindAt(0),
                (byte)KindAt(1),
                (byte)KindAt(2),
                (byte)_inventory.ActiveSlot,
                Channel.Reliable);
            ApplySnapshot(
                state.Tick,
                state.Health,
                state.Energy,
                state.LifeState,
                state.KnockoutTicksRemaining,
                state.ProtectionTicksRemaining,
                KindAt(0),
                KindAt(1),
                KindAt(2),
                _inventory.ActiveSlot);
        }

        [ObserversRpc(BufferLast = true, ExcludeServer = true)]
        private void ReceiveSnapshotObserversRpc(
            uint tick,
            short health,
            short energy,
            byte lifeState,
            uint knockoutTicks,
            uint protectionTicks,
            byte slot0,
            byte slot1,
            byte slot2,
            byte activeSlot,
            Channel channel = Channel.Reliable)
        {
            ApplySnapshot(
                tick,
                health,
                energy,
                (SandboxLifeState)lifeState,
                knockoutTicks,
                protectionTicks,
                (SandboxCarryableKind)slot0,
                (SandboxCarryableKind)slot1,
                (SandboxCarryableKind)slot2,
                activeSlot);
        }

        [TargetRpc]
        private void SendSnapshotTargetRpc(
            NetworkConnection connection,
            uint tick,
            short health,
            short energy,
            byte lifeState,
            uint knockoutTicks,
            uint protectionTicks,
            byte slot0,
            byte slot1,
            byte slot2,
            byte activeSlot,
            Channel channel = Channel.Reliable)
        {
            ApplySnapshot(
                tick,
                health,
                energy,
                (SandboxLifeState)lifeState,
                knockoutTicks,
                protectionTicks,
                (SandboxCarryableKind)slot0,
                (SandboxCarryableKind)slot1,
                (SandboxCarryableKind)slot2,
                activeSlot);
        }

        private void ApplySnapshot(
            uint tick,
            int health,
            int energy,
            SandboxLifeState lifeState,
            uint knockoutTicks,
            uint protectionTicks,
            SandboxCarryableKind slot0,
            SandboxCarryableKind slot1,
            SandboxCarryableKind slot2,
            int activeSlot)
        {
            if (_observedTick != 0u && TickMath.IsOlder(tick, _observedTick))
                return;
            _observedTick = tick;
            _observedHealth = Mathf.Clamp(health, 0, _config.MaximumHealth);
            _observedEnergy = Mathf.Clamp(energy, 0, _config.MaximumEnergy);
            _observedLifeState = lifeState;
            _observedKnockoutTicks = knockoutTicks;
            _observedProtectionTicks = protectionTicks;
            _observedSlots[0] = slot0;
            _observedSlots[1] = slot1;
            _observedSlots[2] = slot2;
            _observedActiveSlot = Mathf.Clamp(activeSlot, 0, SandboxInventoryModel.Capacity - 1);
            if (_animator != null && _animator.runtimeAnimatorController != null)
            {
                _animator.SetBool(KnockedOutBool, lifeState == SandboxLifeState.KnockedOut);
                _animator.SetInteger(CarryKindInt, (int)ObservedKindAt(_observedActiveSlot));
            }
        }

        private void PlayDamageEvent(bool knockedOut)
        {
            ApplyDamageAnimation(knockedOut);
            PlayDamageObserversRpc(knockedOut);
        }

        [ObserversRpc(ExcludeServer = true)]
        private void PlayDamageObserversRpc(bool knockedOut) => ApplyDamageAnimation(knockedOut);

        private void ApplyDamageAnimation(bool knockedOut)
        {
            if (_animator == null || _animator.runtimeAnimatorController == null)
                return;
            _animator.SetTrigger(knockedOut ? KnockoutTrigger : HitTrigger);
            if (knockedOut)
                _animator.SetBool(KnockedOutBool, true);
        }

        private void PlayRecoveryEvent()
        {
            ApplyRecoveryAnimation();
            PlayRecoveryObserversRpc();
        }

        private void PlayInventoryEvent(byte eventKind)
        {
            ApplyInventoryAnimation(eventKind);
            PlayInventoryObserversRpc(eventKind);
        }

        [ObserversRpc(ExcludeServer = true)]
        private void PlayInventoryObserversRpc(byte eventKind) =>
            ApplyInventoryAnimation(eventKind);

        private void ApplyInventoryAnimation(byte eventKind)
        {
            if (_animator == null || _animator.runtimeAnimatorController == null)
                return;
            _animator.SetTrigger(eventKind switch
            {
                0 => PickupTrigger,
                1 => DropTrigger,
                _ => DepositTrigger
            });
        }

        [ObserversRpc(ExcludeServer = true)]
        private void PlayRecoveryObserversRpc() => ApplyRecoveryAnimation();

        private void ApplyRecoveryAnimation()
        {
            if (_animator == null || _animator.runtimeAnimatorController == null)
                return;
            _animator.SetBool(KnockedOutBool, false);
            _animator.SetTrigger(RecoverTrigger);
        }

        private void OnGUI()
        {
            if (!IsOwner)
                return;
            const float width = 330f;
            const float barHeight = 20f;
            var panel = new Rect(16f, 16f, width, 160f);
            GUILayout.BeginArea(panel, GUI.skin.box);
            GUILayout.Label(ObservedLifeState == SandboxLifeState.KnockedOut
                ? $"KO — retour dans {ObservedKnockoutTicksRemaining / (float)_config.TickRate:F1} s"
                : ObservedProtectionTicksRemaining > 0u
                    ? "DEBOUT — protection temporaire"
                    : "SANDBOX");
            DrawBar("VIE", ObservedHealth, _config.MaximumHealth, new Color(0.85f, 0.20f, 0.22f), width - 20f, barHeight);
            DrawBar("ENERGIE", ObservedEnergy, _config.MaximumEnergy, new Color(0.15f, 0.72f, 0.88f), width - 20f, barHeight);
            GUILayout.BeginHorizontal();
            for (var slot = 0; slot < SandboxInventoryModel.Capacity; slot++)
            {
                var selected = slot == ObservedActiveSlot ? ">" : "";
                GUILayout.Box($"{selected}{slot + 1} {LabelFor(ObservedKindAt(slot))}", GUILayout.Width(98f));
            }
            GUILayout.EndHorizontal();
            if (HasTrophy)
                GUILayout.Label("TROPHEE — vitesse 75 % · sprint energie x5");
            GUILayout.EndArea();
        }

        private static void DrawBar(
            string label,
            int value,
            int maximum,
            Color color,
            float width,
            float height)
        {
            var rect = GUILayoutUtility.GetRect(width, height);
            GUI.Box(rect, GUIContent.none);
            var previous = GUI.color;
            GUI.color = color;
            GUI.Box(
                new Rect(rect.x, rect.y, rect.width * value / Mathf.Max(1f, maximum), rect.height),
                GUIContent.none);
            GUI.color = previous;
            GUI.Label(rect, $"{label}  {value}/{maximum}");
        }

        private static string LabelFor(SandboxCarryableKind kind) => kind switch
        {
            SandboxCarryableKind.Rock => "CAILLOU",
            SandboxCarryableKind.Trophy => "TROPHEE",
            _ => "VIDE"
        };
    }
}
