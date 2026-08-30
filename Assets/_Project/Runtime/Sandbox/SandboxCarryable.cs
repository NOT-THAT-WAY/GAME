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
        // Tir au lance-pierre : de la pichenette au trait tendu selon la charge.
        // Baseline de banc ; la puissance en ‰ vient du modèle pur.
        private const float SlingshotMinimumSpeedMetersPerSecond = 12f;
        private const float SlingshotMaximumSpeedMetersPerSecond = 30f;
        private const float SlingshotLiftMetersPerSecond = 0.3f;
        /// <summary>Case d'inventaire fictive des cailloux gardés comme munitions, invisibles.</summary>
        public const int AmmoSlot = -2;
        /// <summary>Le caillou du dessus de la réserve, visible dans la poche de l'élastique.</summary>
        public const int PouchSlot = -3;
        // Géométrie de présentation du lance-pierre, partagée avec le caillou de
        // poche : la poche pend entre les pointes et recule avec la tension.
        // Le poing du rig fait 0,47 m : le bas du manche est en son centre et la
        // fourche doit émerger au-dessus, sinon elle semble plantée dans le poignet.
        private const float HandleInFistMeters = 0.26f;
        // Dégagement vers l'avant : l'arme est tenue au bout des doigts, devant le
        // poing, au lieu de traverser l'avant-bras levé.
        private const float HandClearanceMeters = 0.10f;
        private static readonly Vector3 GripToRoot =
            new(0f, HandleInFistMeters, HandClearanceMeters);
        private static readonly Vector3 PouchRestLocal = new(0f, 0.30f, -0.03f);
        private static readonly Vector3 TipLeftLocal = new(-0.165f, 0.30f, 0f);
        private static readonly Vector3 TipRightLocal = new(0.165f, 0.30f, 0f);
        private const float BandPullMeters = 0.20f;
        private const float BandPullDropMeters = 0.16f;
        private const float SnapOvershootMeters = 0.05f;
        private const float SnapSeconds = 0.12f;
        private const float PouchRockScale = 0.28f;
        private static readonly int BaseColorId = Shader.PropertyToID("_BaseColor");
        private const float RockKnockbackMetersPerSecond = 5.5f;
        private const float TrophyKnockbackMetersPerSecond = 3f;
        private const float SlingshotKnockbackMetersPerSecond = 7f;
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
        private Transform _pouch;
        private Transform _bandLeft;
        private Transform _bandRight;
        private SandboxPlayerGameplay _cachedHolder;
        private int _cachedHolderObjectId = -1;
        private bool _visualDetached;
        private Vector3 _visualRestScale = Vector3.one;
        private float _lastCharge;
        private float _snapRemainingSeconds;
        private bool _instanceLookApplied;
        private Vector3 _spawnPosition;
        private Quaternion _spawnRotation;
        private SandboxCarryablePhase _phase = SandboxCarryablePhase.World;
        private int _holderObjectId = -1;
        private int _inventorySlot = -1;
        private bool _activeInHand;
        private int _throwerObjectId = -1;
        private Vector3 _throwDirection;
        private bool _damageArmed;
        private bool _launchedBySlingshot;
        private int _launchDamage;
        private int _settledFixedUpdates;
        private Collider _ignoredThrowerCollider;
        private int _ignoreThrowerFixedUpdates;
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
            _pouch = root.Find("Pouch");
            _bandLeft = root.Find("BandLeft");
            _bandRight = root.Find("BandRight");
            _visualRestScale = root.localScale;
        }

        /// <summary>
        /// Deux galets identiques côte à côte trahissent la primitive. Chaque
        /// caillou reçoit une orientation et une teinte dérivées de son identifiant
        /// réseau — identiques sur tous les postes, sans rien répliquer de plus.
        /// </summary>
        private void ApplyInstanceLook()
        {
            if (_instanceLookApplied || _kind != SandboxCarryableKind.Rock || _visualRoot == null)
                return;
            _instanceLookApplied = true;
            var seed = (uint)ObjectId * 2654435761u;
            var yaw = seed % 360u;
            var pitch = (seed >> 9) % 50u - 25f;
            var tint = 0.90f + (seed >> 17) % 21u / 100f;
            var turn = Quaternion.Euler(pitch, yaw, 0f);
            foreach (Transform child in _visualRoot)
            {
                child.localPosition = turn * child.localPosition;
                child.localRotation = turn * child.localRotation;
            }
            var block = new MaterialPropertyBlock();
            foreach (var renderer in _renderers)
            {
                if (renderer == null || renderer.sharedMaterial == null)
                    continue;
                var baseColor = renderer.sharedMaterial.HasProperty(BaseColorId)
                    ? renderer.sharedMaterial.GetColor(BaseColorId)
                    : Color.gray;
                renderer.GetPropertyBlock(block);
                block.SetColor(BaseColorId, baseColor * tint);
                renderer.SetPropertyBlock(block);
                block.Clear();
            }
        }

        /// <summary>
        /// Présentation de l'objet tenu, sur tous les postes et après l'animation :
        /// le visuel se pose dans la main (ou devant, pour le trophée) à chaque
        /// image, sans attendre la physique ni le NetworkTransform. Le corps
        /// réseau, lui, continue de suivre grossièrement côté serveur. Aucune
        /// règle ici : collision et ramassage se jouent sur le corps.
        /// </summary>
        private void LateUpdate()
        {
            if (_visualRoot == null)
                return;
            ApplyInstanceLook();
            var visibleHeld = _phase == SandboxCarryablePhase.Held && _activeInHand;
            if (!visibleHeld || !TryResolveHolder(out var holder))
            {
                if (_visualDetached)
                {
                    _visualRoot.localPosition = Vector3.zero;
                    _visualRoot.localRotation = Quaternion.identity;
                    _visualRoot.localScale = _visualRestScale;
                    _visualDetached = false;
                    _lastCharge = 0f;
                    _snapRemainingSeconds = 0f;
                }
                if (_kind == SandboxCarryableKind.Slingshot)
                    LayoutSlingshot(0f, 0f);
                return;
            }

            _visualDetached = true;
            var charge = holder.ObservedChargePermille / (float)SandboxSlingshotModel.PermilleScale;
            if (_inventorySlot == PouchSlot)
            {
                // La pierre attend dans la poche, et recule avec elle quand on tend.
                holder.GetPresentedSlingshotGrip(out var gripPosition, out var gripRotation);
                var slingshotOrigin = gripPosition + gripRotation * GripToRoot;
                _visualRoot.SetPositionAndRotation(
                    slingshotOrigin + gripRotation * PouchLocal(charge, 0f),
                    gripRotation);
                _visualRoot.localScale = _visualRestScale * PouchRockScale;
                return;
            }

            _visualRoot.localScale = _visualRestScale;
            if (_kind == SandboxCarryableKind.Slingshot)
            {
                // Relâchement brutal : la poche dépasse légèrement vers l'avant
                // puis revient — le claquement de l'élastique, purement local.
                if (_lastCharge > 0.15f && charge <= 0f)
                    _snapRemainingSeconds = SnapSeconds;
                _lastCharge = charge;
                var snap = 0f;
                if (_snapRemainingSeconds > 0f)
                {
                    _snapRemainingSeconds -= Time.deltaTime;
                    snap = Mathf.Clamp01(_snapRemainingSeconds / SnapSeconds);
                }
                holder.GetPresentedSlingshotGrip(out var position, out var rotation);
                _visualRoot.SetPositionAndRotation(
                    position + rotation * GripToRoot,
                    rotation);
                LayoutSlingshot(charge, snap);
                return;
            }

            if (_kind == SandboxCarryableKind.Trophy)
            {
                _visualRoot.SetPositionAndRotation(
                    holder.PresentationFrame.TransformPoint(new Vector3(0f, 0.86f, 0.62f)),
                    holder.PresentationFrame.rotation);
                return;
            }

            // Caillou ou autre objet en main : dans le poing droit, bras levé.
            holder.GetPresentedSlingshotGrip(out var handPosition, out var handRotation);
            _visualRoot.SetPositionAndRotation(
                handPosition + handRotation * Vector3.forward * 0.06f,
                handRotation);
        }

        private static Vector3 PouchLocal(float charge, float snap) =>
            PouchRestLocal +
            new Vector3(
                0f,
                -BandPullDropMeters * charge,
                -BandPullMeters * charge + SnapOvershootMeters * snap);

        /// <summary>
        /// Place la poche et tend les deux élastiques entre les pointes et la poche :
        /// un cylindre unité fait 2 m de haut, donc demi-longueur en échelle Y.
        /// </summary>
        private void LayoutSlingshot(float charge, float snap)
        {
            if (_pouch == null)
                return;
            var pouchLocal = PouchLocal(charge, snap);
            _pouch.localPosition = pouchLocal;
            _pouch.localRotation = Quaternion.Euler(-55f * charge, 0f, 0f);
            StretchBand(_bandLeft, TipLeftLocal, pouchLocal + new Vector3(-0.045f, 0f, 0f));
            StretchBand(_bandRight, TipRightLocal, pouchLocal + new Vector3(0.045f, 0f, 0f));
        }

        private static void StretchBand(Transform band, Vector3 from, Vector3 to)
        {
            if (band == null)
                return;
            var delta = to - from;
            var length = delta.magnitude;
            band.localPosition = (from + to) * 0.5f;
            band.localRotation = length > 0.0001f
                ? Quaternion.FromToRotation(Vector3.up, delta / length)
                : Quaternion.identity;
            var thickness = Mathf.Lerp(0.016f, 0.010f, Mathf.InverseLerp(0.06f, 0.34f, length));
            band.localScale = new Vector3(thickness, length * 0.5f, thickness);
        }

        /// <summary>Porteur résolu localement, serveur ou client, d'après l'identifiant répliqué.</summary>
        private bool TryResolveHolder(out SandboxPlayerGameplay holder)
        {
            if (_holderObjectId < 0)
            {
                holder = null;
                return false;
            }
            if (_cachedHolder != null && _cachedHolderObjectId == _holderObjectId)
            {
                holder = _cachedHolder;
                return true;
            }

            var manager = NetworkManager;
            NetworkObject networkObject = null;
            if (manager != null)
            {
                var spawned = manager.IsServerStarted
                    ? manager.ServerManager.Objects.Spawned
                    : manager.ClientManager.Objects.Spawned;
                spawned.TryGetValue(_holderObjectId, out networkObject);
            }
            holder = networkObject != null ? networkObject.GetComponent<SandboxPlayerGameplay>() : null;
            _cachedHolder = holder;
            _cachedHolderObjectId = holder != null ? _holderObjectId : -1;
            return holder != null;
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

            if (_ignoreThrowerFixedUpdates > 0 && --_ignoreThrowerFixedUpdates == 0)
                RestoreThrowerCollision();
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
            _launchedBySlingshot = false;
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
            int damage;
            SandboxDamageKind damageKind;
            float knockbackSpeed;
            switch (_kind)
            {
                case SandboxCarryableKind.Trophy:
                    damage = config.TrophyDamage;
                    damageKind = SandboxDamageKind.Trophy;
                    knockbackSpeed = TrophyKnockbackMetersPerSecond;
                    break;
                case SandboxCarryableKind.Rock when _launchedBySlingshot:
                    damage = Mathf.Clamp(_launchDamage, config.RockDamage, config.SlingshotDamage);
                    damageKind = SandboxDamageKind.SlingshotRock;
                    knockbackSpeed = SlingshotKnockbackMetersPerSecond;
                    break;
                case SandboxCarryableKind.Rock:
                    damage = config.RockDamage;
                    damageKind = SandboxDamageKind.Rock;
                    knockbackSpeed = RockKnockbackMetersPerSecond;
                    break;
                default:
                    // Un lance-pierre n'est pas un projectile : lâché ou jeté, il ne blesse pas.
                    _damageArmed = false;
                    return;
            }
            if (!victim.ApplyDamageFromServer(damage, damageKind, direction * knockbackSpeed))
                return;

            _damageArmed = false;
            Debug.Log(
                $"[GAME-SANDBOX-ITEM] impact item={ObjectId} kind={_kind} " +
                $"damageKind={damageKind} thrower={_throwerObjectId} " +
                $"target={victim.ObjectId} speed={speed:F2}.",
                this);
        }

        public void HoldFromServer(SandboxPlayerGameplay holder, int slot, bool active)
        {
            if (!IsServerStarted || holder == null)
                return;
            RestoreThrowerCollision();
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
            _launchedBySlingshot = false;
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

        public void ThrowFromServer(SandboxPlayerGameplay thrower, Vector3 direction) =>
            LaunchFromServer(
                thrower,
                direction,
                ThrowSpeedMetersPerSecond,
                ThrowLiftMetersPerSecond,
                false);

        /// <summary>
        /// Tir depuis un lance-pierre tenu par <paramref name="shooter"/> : même
        /// objet caillou, vitesse et dégâts interpolés par la puissance chargée
        /// (en ‰, bornée par le modèle pur) entre le caillou à la main et le
        /// maximum du lance-pierre.
        /// </summary>
        public void FireFromSlingshotServer(
            SandboxPlayerGameplay shooter,
            Vector3 aimDirection,
            int powerPermille)
        {
            var power = Mathf.Clamp01(powerPermille / (float)SandboxSlingshotModel.PermilleScale);
            var config = SandboxGameplayConfig.Baseline60Hz;
            var damage = Mathf.RoundToInt(
                Mathf.Lerp(config.RockDamage, config.SlingshotDamage, power));
            // La pierre part de la poche tendue, là où on la voit : c'est le même
            // objet, sans téléportation vers la poitrine. Elle naît contre la
            // capsule du tireur, dont on ignore la collision le temps de sortir.
            shooter.GetSlingshotGrip(out var gripPosition, out var gripRotation);
            var origin = gripPosition + gripRotation * (GripToRoot + PouchLocal(power, 0f));
            LaunchFromServer(
                shooter,
                aimDirection,
                Mathf.Lerp(
                    SlingshotMinimumSpeedMetersPerSecond,
                    SlingshotMaximumSpeedMetersPerSecond,
                    power),
                SlingshotLiftMetersPerSecond,
                true,
                keepPitch: true,
                origin: origin);
            _launchDamage = damage;
            IgnoreThrowerBriefly(shooter);
        }

        private void IgnoreThrowerBriefly(SandboxPlayerGameplay thrower)
        {
            var throwerCollider = thrower != null ? thrower.GetComponent<Collider>() : null;
            if (throwerCollider == null || _gameplayCollider == null)
                return;
            Physics.IgnoreCollision(_gameplayCollider, throwerCollider, true);
            _ignoredThrowerCollider = throwerCollider;
            _ignoreThrowerFixedUpdates = 15;
        }

        private void RestoreThrowerCollision()
        {
            if (_ignoredThrowerCollider != null && _gameplayCollider != null)
                Physics.IgnoreCollision(_gameplayCollider, _ignoredThrowerCollider, false);
            _ignoredThrowerCollider = null;
            _ignoreThrowerFixedUpdates = 0;
        }

        /// <summary>Garde le caillou en réserve : invisible, sans collider, suit le porteur.</summary>
        public void StoreAsAmmoFromServer(SandboxPlayerGameplay holder) =>
            HoldFromServer(holder, AmmoSlot, false);

        /// <summary>Le caillou du dessus de la réserve, montré dans la poche de l'élastique.</summary>
        public void ShowInPouchFromServer(SandboxPlayerGameplay holder) =>
            HoldFromServer(holder, PouchSlot, true);

        private void LaunchFromServer(
            SandboxPlayerGameplay thrower,
            Vector3 direction,
            float speed,
            float lift,
            bool bySlingshot,
            bool keepPitch = false,
            Vector3? origin = null)
        {
            if (!IsServerStarted || thrower == null)
                return;
            // Un lancer à la main part à plat avec sa cloche ; un tir visé garde
            // l'inclinaison du regard. L'origine reste devant la poitrine, à plat,
            // pour ne jamais naître dans le sol en visant bas.
            var flat = new Vector3(direction.x, 0f, direction.z);
            if (flat.sqrMagnitude < 0.0001f)
                flat = thrower.transform.forward;
            flat.Normalize();
            if (!keepPitch || direction.sqrMagnitude < 0.0001f)
                direction = flat;
            direction.Normalize();
            var launchOrigin = origin ?? thrower.transform.position + Vector3.up * 0.9f + flat * 0.8f;
            var velocity = direction * speed + Vector3.up * lift;
            ReleaseToWorld(
                launchOrigin,
                velocity,
                SandboxCarryablePhase.Thrown,
                thrower.ObjectId,
                true);
            _launchedBySlingshot = bySlingshot;
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
            _launchedBySlingshot = false;
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
            _launchedBySlingshot = false;
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
            float maximumDistance) =>
            FindNearestAvailableServer(position, maximumDistance, SandboxCarryableKind.None);

        /// <summary>Le plus proche objet ramassable, limité à un genre si <paramref name="kind"/> n'est pas None.</summary>
        public static SandboxCarryable FindNearestAvailableServer(
            Vector3 position,
            float maximumDistance,
            SandboxCarryableKind kind)
        {
            SandboxCarryable best = null;
            var bestDistance = maximumDistance * maximumDistance;
            for (var index = 0; index < ServerInstances.Count; index++)
            {
                var candidate = ServerInstances[index];
                if (candidate == null || !candidate.AvailableForPickup)
                    continue;
                if (kind != SandboxCarryableKind.None && candidate.Kind != kind)
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
            _launchedBySlingshot = false;
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
            // Le corps réseau suit le porteur grossièrement (réseau, distances) ;
            // le visuel, lui, est posé à chaque image dans LateUpdate.
            var rotation = Quaternion.LookRotation(holder.transform.forward, Vector3.up);
            var position = _inventorySlot < 0
                ? holder.transform.position + Vector3.up * 0.5f
                : holder.transform.position + Vector3.up * 0.86f + holder.transform.forward * 0.5f;
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
