using System;
using System.Collections.Generic;
using FishNet.Connection;
using FishNet.Object;
using FishNet.Transporting;
using NotThatWay.Game.Simulation;
using UnityEngine;

namespace NotThatWay.Game.Sandbox
{
    /// <summary>
    /// Objet physique autoritaire ramassable. Le NetworkTransform ne transporte
    /// que sa pose ; phase, porteur et activation visuelle viennent du serveur.
    /// Un lancer ne peut infliger des dégâts qu'une fois avant son immobilisation.
    /// </summary>
    [DisallowMultipleComponent]
    [RequireComponent(typeof(NetworkObject))]
    [RequireComponent(typeof(Rigidbody))]
    public sealed class SandboxCarryable : NetworkBehaviour
    {
        private const float ThrowSpeedMetersPerSecond = 11f;
        private const float ThrowLiftMetersPerSecond = 2.4f;
        private const float MinimumDamageSpeedMetersPerSecond = 2.5f;
        private const float SettledSpeedMetersPerSecond = 0.2f;
        private const int SettledFixedUpdatesRequired = 20;
        // Flaque d'huile : rayon de glissade, élan requis, poussée de glissade et
        // cadence de balayage serveur. Baselines de banc.
        private const float OilSlickRadiusMeters = 0.95f;
        private const float OilSlipMinimumSpeedMetersPerSecond = 1.5f;
        private const float OilSlipBoostMetersPerSecond = 6f;
        private const int OilScanEveryFixedUpdates = 3;

        private static readonly List<SandboxCarryable> ServerInstances = new();

        [SerializeField] private SandboxCarryableKind _kind = SandboxCarryableKind.Rock;
        [SerializeField] private Transform _visualRoot;
        [SerializeField] private Collider _gameplayCollider;
        [SerializeField] private Rigidbody _body;

        private Renderer[] _renderers = Array.Empty<Renderer>();
        private Vector3 _spawnPosition;
        private Quaternion _spawnRotation;
        private SandboxCarryablePhase _phase = SandboxCarryablePhase.World;
        private int _holderObjectId = -1;
        private int _inventorySlot = -1;
        private bool _activeInHand;
        private int _throwerObjectId = -1;
        private Vector3 _throwDirection;
        private bool _damageArmed;
        private int _settledFixedUpdates;
        private bool _spilled;
        private int _oilScanCountdown;
        private readonly System.Collections.Generic.Dictionary<int, uint> _slipGraceByVictim = new();

        public SandboxCarryableKind Kind => _kind;
        public SandboxCarryablePhase Phase => _phase;
        public int HolderObjectId => _holderObjectId;
        public bool ActiveInHand => _activeInHand;
        public bool AvailableForPickup =>
            IsServerStarted && _phase == SandboxCarryablePhase.World && !_spilled;
        /// <summary>Bidon versé : l'objet est devenu la flaque, au sol, jusqu'au reset.</summary>
        public bool Spilled => _spilled;

        private void Awake()
        {
            _body ??= GetComponent<Rigidbody>();
            _gameplayCollider ??= GetComponent<Collider>();
            var root = _visualRoot != null ? _visualRoot : transform;
            _renderers = root.GetComponentsInChildren<Renderer>(true);
        }

        public override void OnStartServer()
        {
            base.OnStartServer();
            if (_kind == SandboxCarryableKind.None)
                throw new InvalidOperationException("Un carryable réseau doit avoir un type concret.");
            _spawnPosition = transform.position;
            _spawnRotation = transform.rotation;
            if (!ServerInstances.Contains(this))
                ServerInstances.Add(this);
            ApplyPhaseLocally();
            PublishState();
        }

        public override void OnStartClient()
        {
            base.OnStartClient();
            ApplyPhaseLocally();
        }

        public override void OnStopServer()
        {
            ServerInstances.Remove(this);
            base.OnStopServer();
        }

        public override void OnSpawnServer(NetworkConnection connection)
        {
            base.OnSpawnServer(connection);
            if (connection == null)
                return;
            SendStateTargetRpc(
                connection,
                (byte)_phase,
                _holderObjectId,
                (sbyte)_inventorySlot,
                _activeInHand,
                _spilled);
        }

        private void FixedUpdate()
        {
            if (!IsServerStarted)
                return;

            if (_spilled)
            {
                ScanForSlips();
                return;
            }

            if (_phase == SandboxCarryablePhase.Held)
            {
                FollowHolder();
                return;
            }

            if (_phase != SandboxCarryablePhase.Thrown || _body == null)
                return;
            if (_body.linearVelocity.sqrMagnitude >
                SettledSpeedMetersPerSecond * SettledSpeedMetersPerSecond)
            {
                _settledFixedUpdates = 0;
                return;
            }

            _settledFixedUpdates++;
            if (_settledFixedUpdates < SettledFixedUpdatesRequired)
                return;
            _phase = SandboxCarryablePhase.World;
            _throwerObjectId = -1;
            _throwDirection = Vector3.zero;
            _damageArmed = false;
            PublishState();
            Debug.Log(
                $"[GAME-SANDBOX-ITEM] settled item={ObjectId} kind={_kind} " +
                $"pickupReady={AvailableForPickup}.",
                this);
        }

        private void OnCollisionEnter(Collision collision)
        {
            if (!IsServerStarted || _phase != SandboxCarryablePhase.Thrown ||
                !_damageArmed || collision == null)
            {
                return;
            }

            var victim = collision.collider.GetComponentInParent<SandboxPlayerGameplay>();
            if (victim == null || victim.ObjectId == _throwerObjectId)
                return;
            var speed = collision.relativeVelocity.magnitude;
            if (speed < MinimumDamageSpeedMetersPerSecond)
                return;

            // Le Rigidbody peut déjà avoir rebondi lorsque le callback arrive.
            // Conserver le sens du lancer évite donc un knockback vers le lanceur.
            var direction = _throwDirection;
            if (direction.sqrMagnitude < 0.0001f)
                direction = _body != null ? _body.linearVelocity : collision.relativeVelocity;
            direction.y = 0f;
            if (direction.sqrMagnitude < 0.0001f)
                direction = transform.forward;
            direction.Normalize();
            if (_kind == SandboxCarryableKind.OilCan)
            {
                // Un bidon lancé cabosse, il ne blesse pas.
                _damageArmed = false;
                return;
            }
            var config = SandboxGameplayConfig.Baseline60Hz;
            var damage = _kind == SandboxCarryableKind.Trophy
                ? config.TrophyDamage
                : config.RockDamage;
            var damageKind = _kind == SandboxCarryableKind.Trophy
                ? SandboxDamageKind.Trophy
                : SandboxDamageKind.Rock;
            var knockback = direction * (_kind == SandboxCarryableKind.Trophy ? 3f : 5.5f);
            if (!victim.ApplyDamageFromServer(damage, damageKind, knockback))
                return;

            _damageArmed = false;
            Debug.Log(
                $"[GAME-SANDBOX-ITEM] impact item={ObjectId} kind={_kind} " +
                $"thrower={_throwerObjectId} target={victim.ObjectId} speed={speed:F2}.",
                this);
        }

        public void HoldFromServer(SandboxPlayerGameplay holder, int slot, bool active)
        {
            if (!IsServerStarted || holder == null)
                return;
            var changed = _phase != SandboxCarryablePhase.Held ||
                          _holderObjectId != holder.ObjectId ||
                          _inventorySlot != slot ||
                          _activeInHand != active;
            _phase = SandboxCarryablePhase.Held;
            _holderObjectId = holder.ObjectId;
            _inventorySlot = slot;
            _activeInHand = active;
            _throwerObjectId = -1;
            _throwDirection = Vector3.zero;
            _damageArmed = false;
            _settledFixedUpdates = 0;
            ApplyPhaseLocally();
            FollowHolder();
            if (changed)
                PublishState();
        }

        public void DropFromServer(SandboxPlayerGameplay holder, Vector3 inheritedVelocity)
        {
            if (!IsServerStarted)
                return;
            var origin = holder != null
                ? holder.transform.position + Vector3.up * 0.8f + holder.transform.forward * 0.75f
                : transform.position;
            ReleaseToWorld(origin, inheritedVelocity, SandboxCarryablePhase.World, -1, false);
        }

        public void ThrowFromServer(SandboxPlayerGameplay thrower, Vector3 direction)
        {
            if (!IsServerStarted || thrower == null)
                return;
            direction.y = 0f;
            if (direction.sqrMagnitude < 0.0001f)
                direction = thrower.transform.forward;
            direction.Normalize();
            var origin = thrower.transform.position + Vector3.up * 0.9f + direction * 0.8f;
            var velocity = direction * ThrowSpeedMetersPerSecond + Vector3.up * ThrowLiftMetersPerSecond;
            ReleaseToWorld(
                origin,
                velocity,
                SandboxCarryablePhase.Thrown,
                thrower.ObjectId,
                true);
        }

        /// <summary>
        /// Verse le bidon : l'objet devient la flaque, posée au sol devant le
        /// verseur, non ramassable jusqu'au reset de manche. La détection des
        /// glissades est serveur : quiconque la traverse avec de l'élan — verseur
        /// compris — reçoit une poussée dans son élan et une chute de
        /// <see cref="SandboxGameplayConfig.OilSlipKnockdownTicks"/> ticks, au plus
        /// une fois par fenêtre de grâce.
        /// </summary>
        public void PourFromServer(SandboxPlayerGameplay pourer, Vector3 groundPosition)
        {
            if (!IsServerStarted || _kind != SandboxCarryableKind.OilCan || _spilled)
                return;
            _spilled = true;
            _slipGraceByVictim.Clear();
            _oilScanCountdown = 0;
            ReleaseToWorld(
                groundPosition,
                Vector3.zero,
                SandboxCarryablePhase.World,
                -1,
                false);
            if (_body != null)
            {
                _body.isKinematic = true;
                _body.rotation = Quaternion.identity;
            }
            transform.rotation = Quaternion.identity;
            ApplyPhaseLocally();
            PublishState();
            Debug.Log(
                $"[GAME-SANDBOX-ITEM] oil_spilled item={ObjectId} pourer={pourer?.ObjectId ?? -1} " +
                $"position={groundPosition}.",
                this);
        }

        private void ScanForSlips()
        {
            if (--_oilScanCountdown > 0)
                return;
            _oilScanCountdown = OilScanEveryFixedUpdates;
            var config = SandboxGameplayConfig.Baseline60Hz;
            var tick = TimeManager != null ? TimeManager.Tick : 0u;
            var center = transform.position;
            var hits = Physics.OverlapSphere(
                center + Vector3.up * 0.4f,
                OilSlickRadiusMeters,
                1 << GameplayLayers.Player);
            foreach (var hit in hits)
            {
                var motor = hit.GetComponentInParent<PredictedPlayerMotor>();
                if (motor != null && motor.IsServerStarted)
                {
                    if (!TryConsumeGrace(motor.ObjectId, tick, config.OilSlipGraceTicks))
                        continue;
                    var velocity = motor.SimulationState.HorizontalVelocity;
                    var speed = velocity.HorizontalMagnitude;
                    if (speed < OilSlipMinimumSpeedMetersPerSecond)
                        continue;
                    var direction = new Vector3(
                        (float)(velocity.X / speed),
                        0f,
                        (float)(velocity.Z / speed));
                    motor.ApplyKnockbackFromServer(direction * OilSlipBoostMetersPerSecond);
                    motor.ApplyKnockdownFromServer(config.OilSlipKnockdownTicks);
                    Debug.Log(
                        $"[GAME-SANDBOX-ITEM] oil_slip item={ObjectId} victim={motor.ObjectId} " +
                        $"speed={speed:F2} tick={tick}.",
                        this);
                    continue;
                }

                var bot = hit.GetComponentInParent<SimpleBot>();
                if (bot != null)
                {
                    if (!TryConsumeGrace(bot.GetInstanceID(), tick, config.OilSlipGraceTicks))
                        continue;
                    bot.SlipFromServer(bot.transform.forward * OilSlipBoostMetersPerSecond);
                    Debug.Log(
                        $"[GAME-SANDBOX-ITEM] oil_slip item={ObjectId} victim=bot tick={tick}.",
                        this);
                }
            }
        }

        private bool TryConsumeGrace(int victimId, uint tick, uint graceTicks)
        {
            if (_slipGraceByVictim.TryGetValue(victimId, out var lastTick) &&
                TickMath.Elapsed(lastTick, tick) < graceTicks)
            {
                return false;
            }
            _slipGraceByVictim[victimId] = tick;
            return true;
        }

        public void DepositFromServer()
        {
            if (!IsServerStarted)
                return;
            _phase = SandboxCarryablePhase.Deposited;
            _holderObjectId = -1;
            _inventorySlot = -1;
            _activeInHand = true;
            _throwerObjectId = -1;
            _throwDirection = Vector3.zero;
            _damageArmed = false;
            if (_body != null)
            {
                _body.linearVelocity = Vector3.zero;
                _body.angularVelocity = Vector3.zero;
                _body.isKinematic = true;
                _body.position = SandboxDepositZone.DepositedTrophyPosition;
                _body.rotation = Quaternion.identity;
            }
            transform.SetPositionAndRotation(
                SandboxDepositZone.DepositedTrophyPosition,
                Quaternion.identity);
            ApplyPhaseLocally();
            PublishState();
        }

        public void ResetFromServer()
        {
            if (!IsServerStarted)
                return;
            _spilled = false;
            _slipGraceByVictim.Clear();
            _phase = SandboxCarryablePhase.World;
            _holderObjectId = -1;
            _inventorySlot = -1;
            _activeInHand = false;
            _throwerObjectId = -1;
            _throwDirection = Vector3.zero;
            _damageArmed = false;
            _settledFixedUpdates = 0;
            if (_body != null)
            {
                _body.isKinematic = true;
                _body.linearVelocity = Vector3.zero;
                _body.angularVelocity = Vector3.zero;
                _body.position = _spawnPosition;
                _body.rotation = _spawnRotation;
                _body.isKinematic = false;
                _body.WakeUp();
            }
            transform.SetPositionAndRotation(_spawnPosition, _spawnRotation);
            ApplyPhaseLocally();
            PublishState();
        }

        public static SandboxCarryable FindNearestAvailableServer(
            Vector3 position,
            float maximumDistance)
        {
            SandboxCarryable best = null;
            var bestDistance = maximumDistance * maximumDistance;
            for (var index = 0; index < ServerInstances.Count; index++)
            {
                var candidate = ServerInstances[index];
                if (candidate == null || !candidate.AvailableForPickup)
                    continue;
                var distance = (candidate.transform.position - position).sqrMagnitude;
                if (distance > bestDistance ||
                    (Mathf.Approximately(distance, bestDistance) && best != null &&
                     candidate.ObjectId >= best.ObjectId))
                {
                    continue;
                }
                best = candidate;
                bestDistance = distance;
            }
            return best;
        }

        public static bool TryFindServer(int objectId, out SandboxCarryable carryable)
        {
            for (var index = 0; index < ServerInstances.Count; index++)
            {
                var candidate = ServerInstances[index];
                if (candidate != null && candidate.IsServerStarted && candidate.ObjectId == objectId)
                {
                    carryable = candidate;
                    return true;
                }
            }
            carryable = null;
            return false;
        }

        internal static void ResetAllFromServer()
        {
            for (var index = 0; index < ServerInstances.Count; index++)
            {
                var carryable = ServerInstances[index];
                if (carryable != null && carryable.IsServerStarted)
                    carryable.ResetFromServer();
            }
        }

        private void ReleaseToWorld(
            Vector3 position,
            Vector3 velocity,
            SandboxCarryablePhase phase,
            int throwerObjectId,
            bool damageArmed)
        {
            _phase = phase;
            _holderObjectId = -1;
            _inventorySlot = -1;
            _activeInHand = false;
            _throwerObjectId = throwerObjectId;
            _throwDirection = damageArmed
                ? new Vector3(velocity.x, 0f, velocity.z).normalized
                : Vector3.zero;
            _damageArmed = damageArmed;
            _settledFixedUpdates = 0;
            transform.position = position;
            if (_body != null)
            {
                _body.isKinematic = false;
                _body.position = position;
                _body.linearVelocity = velocity;
                _body.angularVelocity = new Vector3(3f, 5f, 2f);
                _body.WakeUp();
            }
            ApplyPhaseLocally();
            PublishState();
        }

        private void FollowHolder()
        {
            if (!SandboxPlayerGameplay.TryFindServer(_holderObjectId, out var holder))
            {
                DropFromServer(null, Vector3.zero);
                return;
            }
            var side = (_inventorySlot - 1) * 0.16f;
            var position = holder.transform.position +
                           Vector3.up * 0.86f +
                           holder.transform.forward * 0.62f +
                           holder.transform.right * side;
            var rotation = Quaternion.LookRotation(holder.transform.forward, Vector3.up);
            if (_body != null)
            {
                _body.position = position;
                _body.rotation = rotation;
            }
            transform.SetPositionAndRotation(position, rotation);
        }

        private void ApplyPhaseLocally()
        {
            // Bidon versé : le groupe « Can » disparaît, le groupe « Slick » prend
            // sa place, à plat au sol. Purement visuel, répliqué par l'état.
            if (_kind == SandboxCarryableKind.OilCan && _visualRoot != null)
            {
                var can = _visualRoot.Find("Can");
                var slick = _visualRoot.Find("Slick");
                if (can != null)
                    can.gameObject.SetActive(!_spilled);
                if (slick != null)
                    slick.gameObject.SetActive(_spilled);
            }
            var visible = _phase != SandboxCarryablePhase.Held || _activeInHand;
            for (var index = 0; index < _renderers.Length; index++)
            {
                if (_renderers[index] != null)
                    _renderers[index].enabled = visible;
            }
            if (_gameplayCollider != null)
            {
                // Une flaque n'arrête personne : son corps n'existe plus, seule la
                // règle de glissade côté serveur la fait exister.
                _gameplayCollider.enabled =
                    !_spilled &&
                    (_phase == SandboxCarryablePhase.World ||
                     _phase == SandboxCarryablePhase.Thrown);
            }
            if (_body != null)
            {
                // Seul le serveur simule la physique. Les observateurs reçoivent
                // la pose du NetworkTransform et ne doivent pas ajouter leur
                // propre gravité entre deux snapshots.
                _body.isKinematic = !IsServerStarted ||
                    _spilled ||
                    _phase == SandboxCarryablePhase.Held ||
                    _phase == SandboxCarryablePhase.Deposited;
            }
        }

        private void PublishState()
        {
            if (!IsServerStarted)
                return;
            ReceiveStateObserversRpc(
                (byte)_phase,
                _holderObjectId,
                (sbyte)_inventorySlot,
                _activeInHand,
                _spilled,
                Channel.Reliable);
        }

        [ObserversRpc(BufferLast = true, ExcludeServer = true)]
        private void ReceiveStateObserversRpc(
            byte phase,
            int holderObjectId,
            sbyte inventorySlot,
            bool activeInHand,
            bool spilled,
            Channel channel = Channel.Reliable)
        {
            ApplyNetworkState(phase, holderObjectId, inventorySlot, activeInHand, spilled);
        }

        [TargetRpc]
        private void SendStateTargetRpc(
            NetworkConnection connection,
            byte phase,
            int holderObjectId,
            sbyte inventorySlot,
            bool activeInHand,
            bool spilled,
            Channel channel = Channel.Reliable)
        {
            ApplyNetworkState(phase, holderObjectId, inventorySlot, activeInHand, spilled);
        }

        private void ApplyNetworkState(
            byte phase,
            int holderObjectId,
            int inventorySlot,
            bool activeInHand,
            bool spilled)
        {
            _phase = (SandboxCarryablePhase)phase;
            _holderObjectId = holderObjectId;
            _inventorySlot = inventorySlot;
            _activeInHand = activeInHand;
            _spilled = spilled;
            ApplyPhaseLocally();
        }
    }
}
