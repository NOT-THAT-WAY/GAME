using System;
using System.Collections.Generic;
using FishNet.Connection;
using FishNet.Object;
using FishNet.Transporting;
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

        public SandboxCarryableKind Kind => _kind;
        public SandboxCarryablePhase Phase => _phase;
        public int HolderObjectId => _holderObjectId;
        public bool ActiveInHand => _activeInHand;
        public bool AvailableForPickup =>
            IsServerStarted && _phase == SandboxCarryablePhase.World;

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
                _activeInHand);
        }

        private void FixedUpdate()
        {
            if (!IsServerStarted)
                return;

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
            var visible = _phase != SandboxCarryablePhase.Held || _activeInHand;
            for (var index = 0; index < _renderers.Length; index++)
            {
                if (_renderers[index] != null)
                    _renderers[index].enabled = visible;
            }
            if (_gameplayCollider != null)
            {
                _gameplayCollider.enabled =
                    _phase == SandboxCarryablePhase.World ||
                    _phase == SandboxCarryablePhase.Thrown;
            }
            if (_body != null)
            {
                // Seul le serveur simule la physique. Les observateurs reçoivent
                // la pose du NetworkTransform et ne doivent pas ajouter leur
                // propre gravité entre deux snapshots.
                _body.isKinematic = !IsServerStarted ||
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
                Channel.Reliable);
        }

        [ObserversRpc(BufferLast = true, ExcludeServer = true)]
        private void ReceiveStateObserversRpc(
            byte phase,
            int holderObjectId,
            sbyte inventorySlot,
            bool activeInHand,
            Channel channel = Channel.Reliable)
        {
            ApplyNetworkState(phase, holderObjectId, inventorySlot, activeInHand);
        }

        [TargetRpc]
        private void SendStateTargetRpc(
            NetworkConnection connection,
            byte phase,
            int holderObjectId,
            sbyte inventorySlot,
            bool activeInHand,
            Channel channel = Channel.Reliable)
        {
            ApplyNetworkState(phase, holderObjectId, inventorySlot, activeInHand);
        }

        private void ApplyNetworkState(
            byte phase,
            int holderObjectId,
            int inventorySlot,
            bool activeInHand)
        {
            _phase = (SandboxCarryablePhase)phase;
            _holderObjectId = holderObjectId;
            _inventorySlot = inventorySlot;
            _activeInHand = activeInHand;
            ApplyPhaseLocally();
        }
    }
}
