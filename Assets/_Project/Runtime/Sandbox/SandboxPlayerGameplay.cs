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
        // Recharger le lance-pierre est un geste fréquent : un peu plus de portée
        // que le ramassage pour ne pas avoir à marcher sur le caillou.
        private const float AmmoPickupRangeMeters = 2.2f;

        private static readonly List<SandboxPlayerGameplay> ServerInstances = new();
        private static readonly int HitTrigger = Animator.StringToHash("Hit");
        private static readonly int KnockoutTrigger = Animator.StringToHash("Knockout");
        private static readonly int RecoverTrigger = Animator.StringToHash("Recover");
        private static readonly int PickupTrigger = Animator.StringToHash("Pickup");
        private static readonly int DropTrigger = Animator.StringToHash("Drop");
        private static readonly int DepositTrigger = Animator.StringToHash("Deposit");
        private static readonly int ThrowTrigger = Animator.StringToHash("Throw");
        private static readonly int KnockedOutBool = Animator.StringToHash("KnockedOut");
        private static readonly int CarryKindInt = Animator.StringToHash("CarryKind");

        private readonly SandboxCarryableKind[] _observedSlots =
            new SandboxCarryableKind[SandboxInventoryModel.Capacity];

        private readonly List<int> _ammoObjectIds = new();

        private SandboxGameplayConfig _config;
        private SandboxPlayerModel _model;
        private SandboxInventoryModel _inventory;
        private SandboxSlingshotModel _slingshot;
        private Transform _presentationFrame;
        private M1PlayerAppearance _appearance;
        private int _observedAmmo;
        private uint _chargeStartTick;
        private uint _observedChargeStartTick;
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
        public bool HasRock => IsServerStarted
            ? _inventory.HasKind(SandboxCarryableKind.Rock)
            : ObservedHasKind(SandboxCarryableKind.Rock);
        /// <summary>Cailloux gardés comme munitions du lance-pierre, hors des trois cases.</summary>
        public int AmmoCount => IsServerStarted ? _ammoObjectIds.Count : _observedAmmo;
        public bool HasSlingshotInHand => ActiveKind == SandboxCarryableKind.Slingshot;
        /// <summary>
        /// Point de prise du lance-pierre dans le repère graphique du personnage :
        /// devant et sous l'épaule droite (0,92 m), à portée du bras (0,51 m) et
        /// hors de la boule du corps. Le poing est ainsi vers l'avant-bas, la
        /// fourche (+0,42 m) à hauteur des yeux et la poche tendue vient à la joue.
        /// Le bras y est amené par <c>M1SlingshotArmPose</c> et l'objet s'y pose :
        /// une seule formule, donc jamais de retard d'une image entre main et arme.
        /// </summary>
        public static readonly Vector3 SlingshotGripLocal = new(0.30f, 0.70f, 0.40f);
        // Fourche tournée vers l'intérieur : la poche tendue vient vers la joue.
        public const float SlingshotGripYawDegrees = 28f;

        /// <summary>
        /// Modèle de vue : en vue subjective, le joueur local voit son lance-pierre
        /// ancré à sa caméra (yaw et pitch du regard), bas-droite, entier dans
        /// l'image quel que soit le bras du rig. Le bras visible est étiré jusqu'à
        /// lui par <c>M1SlingshotArmPose</c> ; l'épaule, cachée, suit. Les autres
        /// joueurs voient le modèle monde au point de prise du corps.
        /// </summary>
        public static readonly Vector3 SlingshotViewmodelLocal = new(0.22f, -0.34f, 0.50f);
        public const float SlingshotViewmodelYawDegrees = 24f;

        /// <summary>Racine graphique (lissée par FishNet) ou, à défaut, la racine réseau.</summary>
        public Transform PresentationFrame =>
            _presentationFrame != null ? _presentationFrame : transform;

        /// <summary>Le joueur local se regarde-t-il en vue subjective ? (modèle de vue)</summary>
        public bool UsesViewmodel =>
            IsOwner && _appearance != null && !_appearance.IsThirdPerson &&
            _appearance.PlayerCamera != null;

        /// <summary>Point de prise du monde (corps), pour la règle et les autres joueurs.</summary>
        public void GetSlingshotGrip(out Vector3 position, out Quaternion rotation)
        {
            var frame = PresentationFrame;
            position = frame.TransformPoint(SlingshotGripLocal);
            rotation = frame.rotation * Quaternion.Euler(0f, SlingshotGripYawDegrees, 0f);
        }

        /// <summary>Point de prise tel que ce poste doit le dessiner : modèle de vue ou monde.</summary>
        public void GetPresentedSlingshotGrip(out Vector3 position, out Quaternion rotation)
        {
            if (!UsesViewmodel)
            {
                GetSlingshotGrip(out position, out rotation);
                return;
            }
            var camera = _appearance.PlayerCamera.transform;
            position = camera.TransformPoint(SlingshotViewmodelLocal);
            rotation = camera.rotation * Quaternion.Euler(0f, SlingshotViewmodelYawDegrees, 0f);
        }

        /// <summary>
        /// Charge du lance-pierre vue d'ici, en ‰ : exacte chez l'hôte, estimée
        /// ailleurs depuis le tick de début répliqué et le tick local. Présentation
        /// seulement — la puissance réelle du tir est celle du modèle côté hôte.
        /// </summary>
        public int ObservedChargePermille
        {
            get
            {
                if (IsServerStarted)
                    return _slingshot.ChargePermille;
                if (_observedChargeStartTick == 0u || TimeManager == null)
                    return 0;
                var elapsed = TickMath.Elapsed(_observedChargeStartTick, TimeManager.Tick);
                var permille = elapsed * (long)SandboxSlingshotModel.PermilleScale /
                               _config.SlingshotChargeTicks;
                return (int)Math.Min(SandboxSlingshotModel.PermilleScale, permille);
            }
        }
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
        /// <summary>
        /// Modificateur de vitesse pour une commande donnée : la base (trophée,
        /// KO) puis le ralentissement de visée si le joueur bande le lance-pierre.
        /// Dérivé de la commande et de l'objet actif, donc identique chez l'hôte et
        /// le propriétaire qui prédit — sans état supplémentaire à répliquer.
        /// </summary>
        public int MovementSpeedPermilleFor(PlayerCommand command)
        {
            var permille = MovementSpeedPermille;
            if (permille > 0 && HasSlingshotInHand && command.Has(PlayerCommandButtons.PunchHeld))
            {
                permille = (int)((long)permille * _config.SlingshotAimMovementPermille /
                                 SandboxGameplayConfig.PermilleScale);
                if (permille < 1)
                    permille = 1;
            }
            return permille;
        }

        /// <summary>Direction du regard de l'hôte, pitch compris, pour un tir visé.</summary>
        private Vector3 AimDirection
        {
            get
            {
                var forward = transform.forward;
                forward.y = 0f;
                if (forward.sqrMagnitude < 0.0001f)
                    forward = Vector3.forward;
                forward.Normalize();
                var pitchDegrees = _motor != null && _motor.IsSimulationReady
                    ? _motor.SimulationState.PitchCentidegrees / 100f
                    : 0f;
                return Quaternion.LookRotation(forward, Vector3.up) *
                       Quaternion.Euler(-pitchDegrees, 0f, 0f) *
                       Vector3.forward;
            }
        }

        public bool CanPush => IsAlive && !HasTrophy && ObservedEnergy > 0;
        public bool CanPunch =>
            IsAlive && !HasTrophy && ActiveKind == SandboxCarryableKind.None &&
            ObservedEnergy >= _config.PunchEnergyCost;
        // Le lance-pierre en main ne se lance pas : il tire. Il se lâche avec Drop.
        public bool CanThrow =>
            IsAlive && ActiveKind != SandboxCarryableKind.None &&
            ActiveKind != SandboxCarryableKind.Slingshot &&
            ObservedEnergy >= _config.ThrowEnergyCost;
        public bool CanFireSlingshot =>
            IsAlive && HasSlingshotInHand && AmmoCount > 0 &&
            ObservedEnergy >= _config.SlingshotEnergyCost;

        private void Awake()
        {
            _config = SandboxGameplayConfig.Baseline60Hz;
            _model = new SandboxPlayerModel(_config);
            _inventory = new SandboxInventoryModel();
            _motor = GetComponent<PredictedPlayerMotor>();
            _animator = GetComponentInChildren<Animator>(true);
            _slingshot = SandboxSlingshotModel.FromConfig(_config);
            _appearance = GetComponent<M1PlayerAppearance>();
            _presentationFrame = _appearance != null ? _appearance.Body : null;
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
                (byte)_inventory.ActiveSlot,
                (byte)_ammoObjectIds.Count,
                _chargeStartTick);
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
                ProcessSlingshotCommand(command);
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
        /// Le bouton lance-pierre et la charge du tir passent par le modèle pur,
        /// un pas par tick de commande. L'hôte applique ou refuse chaque action.
        /// Un joueur KO ou qui ne tient plus l'arme voit sa charge annulée.
        /// </summary>
        private void ProcessSlingshotCommand(PlayerCommand command)
        {
            if (!IsAlive)
            {
                _slingshot.Reset();
                return;
            }

            var result = _slingshot.Advance(new SlingshotTickInput(
                command.Has(PlayerCommandButtons.SlingshotPressed),
                command.Has(PlayerCommandButtons.SlingshotHeld),
                command.Has(PlayerCommandButtons.PunchPressed),
                command.Has(PlayerCommandButtons.PunchHeld),
                HasSlingshotInHand));
            var chargeStart = _slingshot.IsCharging
                ? _chargeStartTick == 0u ? Math.Max(command.Tick, 1u) : _chargeStartTick
                : 0u;
            if (chargeStart != _chargeStartTick)
            {
                _chargeStartTick = chargeStart;
                PublishSnapshot(true);
            }
            switch (result.Action)
            {
                case SlingshotActionKind.TakeOrLoad:
                    if (HasSlingshotInHand)
                        TryLoadAmmoFromServer();
                    else
                        TryTakeSlingshotFromServer();
                    break;
                case SlingshotActionKind.Drop:
                    if (HasSlingshotInHand)
                        DropActiveFromServer();
                    break;
                case SlingshotActionKind.Fire:
                    TryFireSlingshotFromServer(result.PowerPermille);
                    break;
            }
        }

        /// <summary>Prendre le lance-pierre : depuis la poche s'il y est, sinon au sol à portée.</summary>
        private bool TryTakeSlingshotFromServer()
        {
            var pocketSlot = _inventory.IndexOfKind(SandboxCarryableKind.Slingshot);
            if (pocketSlot >= 0)
            {
                _inventory.Select(pocketSlot);
                RefreshHeldPresentations();
                Debug.Log($"[GAME-SANDBOX-ITEM] slingshot_drawn player={ObjectId} slot={pocketSlot}.", this);
                return true;
            }

            if (_inventory.IsFull)
                return false;
            var ground = SandboxCarryable.FindNearestAvailableServer(
                transform.position,
                PickupRangeMeters,
                SandboxCarryableKind.Slingshot);
            if (ground == null)
                return false;
            var entry = new SandboxInventoryEntry(ground.ObjectId, ground.Kind);
            if (!_inventory.TryAdd(entry, out var slot))
                return false;
            ground.HoldFromServer(this, slot, true);
            RefreshHeldPresentations();
            PlayInventoryEvent(0);
            Debug.Log(
                $"[GAME-SANDBOX-ITEM] slingshot_pickup player={ObjectId} item={ground.ObjectId} slot={slot}.",
                this);
            return true;
        }

        /// <summary>
        /// Charger un caillou : d'abord celui d'une case de l'inventaire, sinon le
        /// plus proche au sol. Il rejoint la réserve, invisible, jusqu'à la capacité.
        /// </summary>
        private bool TryLoadAmmoFromServer()
        {
            if (_ammoObjectIds.Count >= _config.SlingshotAmmoCapacity)
            {
                Debug.Log($"[GAME-SANDBOX-ITEM] slingshot_ammo_full player={ObjectId}.", this);
                return false;
            }

            SandboxCarryable rock;
            if (_inventory.TryFindFirstOfKind(SandboxCarryableKind.Rock, out var pocket) &&
                SandboxCarryable.TryFindServer(pocket.ObjectId, out rock) &&
                _inventory.TryRemoveObject(pocket.ObjectId, out _))
            {
                // La case active doit rester le lance-pierre après retrait.
                var slingshotSlot = _inventory.IndexOfKind(SandboxCarryableKind.Slingshot);
                if (slingshotSlot >= 0)
                    _inventory.Select(slingshotSlot);
            }
            else
            {
                rock = SandboxCarryable.FindNearestAvailableServer(
                    transform.position,
                    AmmoPickupRangeMeters,
                    SandboxCarryableKind.Rock);
                if (rock == null)
                    return false;
            }

            _ammoObjectIds.Add(rock.ObjectId);
            rock.StoreAsAmmoFromServer(this);
            RefreshHeldPresentations();
            PlayInventoryEvent(0);
            PublishSnapshot(false);
            Debug.Log(
                $"[GAME-SANDBOX-ITEM] slingshot_load player={ObjectId} rock={rock.ObjectId} " +
                $"ammo={_ammoObjectIds.Count}/{_config.SlingshotAmmoCapacity}.",
                this);
            return true;
        }

        /// <summary>
        /// Tir serveur : arme en main, une munition et l'énergie du tir. Le dernier
        /// caillou chargé part comme projectile à la puissance du modèle.
        /// </summary>
        private bool TryFireSlingshotFromServer(int powerPermille)
        {
            if (!HasSlingshotInHand || _ammoObjectIds.Count == 0)
            {
                Debug.Log($"[GAME-SANDBOX-ITEM] slingshot_empty player={ObjectId}.", this);
                return false;
            }
            var ammoId = _ammoObjectIds[_ammoObjectIds.Count - 1];
            if (!SandboxCarryable.TryFindServer(ammoId, out var rock))
            {
                _ammoObjectIds.RemoveAt(_ammoObjectIds.Count - 1);
                return false;
            }
            if (!_model.TrySpendSlingshotShot())
                return false;

            _ammoObjectIds.RemoveAt(_ammoObjectIds.Count - 1);
            rock.FireFromSlingshotServer(this, AimDirection, powerPermille);
            RefreshHeldPresentations();
            PlayInventoryEvent(3);
            PublishSnapshot(false);
            Debug.Log(
                $"[GAME-SANDBOX-ITEM] slingshot_fire player={ObjectId} rock={ammoId} " +
                $"power={powerPermille} ammo={_ammoObjectIds.Count}.",
                this);
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
                var standUp = index == missing &&
                              (command.Has(PlayerCommandButtons.JumpPressed) ||
                               command.Has(PlayerCommandButtons.JumpHeld));
                var result = _model.AdvanceTick(sprint, _inventory.HasTrophy, standUp);
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
            if (command.Has(PlayerCommandButtons.InteractPressed) &&
                !(HasSlingshotInHand && TryLoadAmmoFromServer()))
            {
                TryPickupNearestFromServer();
            }

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
            // La réserve appartient au lance-pierre : le lâcher rend ses cailloux à
            // l'arène au lieu de les garder confisqués dans une poche invisible.
            if (entry.Kind == SandboxCarryableKind.Slingshot)
                SpillAmmoFromServer(1);
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
            // Les munitions s'éparpillent aussi : un KO vide les poches.
            dropIndex += SpillAmmoFromServer(dropIndex);
            _slingshot.Reset();
            if (dropIndex > 0)
                PlayInventoryEvent(1);
        }

        /// <summary>Rend les cailloux de la réserve à l'arène en éventail autour du joueur.</summary>
        private int SpillAmmoFromServer(int dropIndex)
        {
            var spilled = 0;
            for (var index = 0; index < _ammoObjectIds.Count; index++)
            {
                if (!SandboxCarryable.TryFindServer(_ammoObjectIds[index], out var ammo))
                    continue;
                var angle = (dropIndex + index) * 72f + 36f;
                ammo.DropFromServer(
                    this,
                    Quaternion.Euler(0f, angle, 0f) * transform.forward * 0.8f);
                spilled++;
            }
            _ammoObjectIds.Clear();
            _chargeStartTick = 0u;
            return spilled;
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

            // Réserve : tout est invisible sauf, lance-pierre en main, le caillou du
            // dessus qui attend dans la poche de l'élastique.
            for (var index = 0; index < _ammoObjectIds.Count; index++)
            {
                if (!SandboxCarryable.TryFindServer(_ammoObjectIds[index], out var ammo))
                    continue;
                var inPouch = HasSlingshotInHand && index == _ammoObjectIds.Count - 1;
                if (inPouch)
                    ammo.ShowInPouchFromServer(this);
                else
                    ammo.StoreAsAmmoFromServer(this);
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

        private bool ObservedHasTrophy() => ObservedHasKind(SandboxCarryableKind.Trophy);

        private bool ObservedHasKind(SandboxCarryableKind kind)
        {
            for (var index = 0; index < _observedSlots.Length; index++)
            {
                if (_observedSlots[index] == kind)
                    return true;
            }
            return false;
        }

        private int InventoryFingerprint()
        {
            var value = _inventory.ActiveSlot;
            for (var slot = 0; slot < SandboxInventoryModel.Capacity; slot++)
                value = value * 31 + (int)KindAt(slot);
            return (value * 31 + _ammoObjectIds.Count) * 31 + (int)(_chargeStartTick & 0x7FFFFFFF);
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
                (byte)_ammoObjectIds.Count,
                _chargeStartTick,
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
                _inventory.ActiveSlot,
                _ammoObjectIds.Count,
                _chargeStartTick);
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
            byte ammo,
            uint chargeStartTick,
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
                activeSlot,
                ammo,
                chargeStartTick);
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
            byte ammo,
            uint chargeStartTick,
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
                activeSlot,
                ammo,
                chargeStartTick);
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
            int activeSlot,
            int ammo,
            uint chargeStartTick)
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
            _observedAmmo = Mathf.Clamp(ammo, 0, _config.SlingshotAmmoCapacity);
            _observedChargeStartTick = chargeStartTick;
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
                3 => ThrowTrigger,
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
