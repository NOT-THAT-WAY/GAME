using FishNet.Object;
using NotThatWay.Game.Sandbox;
using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Bot volontairement simple du banc de test. L'hôte le pilote et réplique sa
    /// racine : il alterne entre poursuivre le joueur pour lui mettre un petit coup
    /// et aller s'appuyer sur le mur mobile. Le joueur peut le frapper quatre fois
    /// pour le mettre brièvement KO, puis il se relève et reprend sa boucle.
    ///
    /// Hors du sandbox M1 (ancien banc labyrinthe), l'absence de joueur prédit et de
    /// mur autoritaire le fait retomber sur sa marche historique avec demi-tours.
    /// </summary>
    [RequireComponent(typeof(CharacterController))]
    public sealed class SimpleBot : NetworkBehaviour
    {
        public const int MaximumHealth = 100;

        private const int PlayerPunchDamage = 25;
        private const int BotPunchDamage = 10;
        private const float WalkSpeed = 2.35f;
        private const float TurnSpeed = 260f;
        private const float Gravity = -22f;
        private const float WallProbeDistance = 0.9f;
        private const float AttackRange = 1.55f;
        private const float AttackHalfAngle = 48f;
        private const float AttackWindupSeconds = 0.32f;
        private const float AttackCooldownSeconds = 1.65f;
        private const float AttackKnockbackSpeed = 3.2f;
        private const float AttackModeSeconds = 7.5f;
        private const float WallModeSeconds = 4.5f;
        private const float WallPushPulseSeconds = 0.18f;
        private const float WallTargetTolerance = 0.24f;
        private const float StaggerSeconds = 0.65f;
        private const float KnockoutSeconds = 2.8f;
        private const float KnockbackDecay = 8f;
        private const float StaggerTilt = 18f;
        private const float KnockoutTilt = 82f;
        private const float ChestHeight = 0.7f;

        private static readonly int MoveSpeedFloat = Animator.StringToHash("MoveSpeed");
        private static readonly int GroundedBool = Animator.StringToHash("Grounded");
        private static readonly int SprintingBool = Animator.StringToHash("Sprinting");
        private static readonly int CarryingBool = Animator.StringToHash("Carrying");
        private static readonly int PushBool = Animator.StringToHash("Push");
        private static readonly int PunchTrigger = Animator.StringToHash("Punch");
        private static readonly int HitTrigger = Animator.StringToHash("Hit");
        private static readonly int KnockoutTrigger = Animator.StringToHash("Knockout");
        private static readonly int RecoverTrigger = Animator.StringToHash("Recover");
        private static readonly int KnockedOutBool = Animator.StringToHash("KnockedOut");
        private static readonly int BaseColorId = Shader.PropertyToID("_BaseColor");

        [SerializeField] private Transform _visual;

        private CharacterController _controller;
        private Animator _animator;
        private SandboxPlayerGameplay _target;
        private M1AuthoritativeWallDirector _wallDirector;
        private TopologyWallView _wallView;
        private Vector3 _knockback;
        private Vector3 _lastPresentationPosition;
        private Quaternion _visualBaseRotation = Quaternion.identity;
        private float _verticalVelocity;
        private float _presentationSpeed;
        private float _staggeredUntil = float.NegativeInfinity;
        private float _knockedOutUntil = float.NegativeInfinity;
        private float _visualStaggeredUntil = float.NegativeInfinity;
        private float _modeUntil;
        private float _nextAttackAllowedAt = float.NegativeInfinity;
        private float _attackImpactAt;
        private float _nextWallPushPulseAt = float.NegativeInfinity;
        private float _turnDirection = 1f;
        private float _wallSide = 1f;
        private int _health = MaximumHealth;
        private bool _attacking;
        private bool _pushing;
        private bool _turning;
        private bool _visualKnockedOut;
        private bool _smokeHitLogged;
        private bool _wallPushLogged;
        private BrainMode _mode;

        public int Health => _health;
        public bool CanBeHit => _health > 0;

        private enum BrainMode : byte
        {
            AttackPlayer = 0,
            PushWall = 1
        }

        private void Awake()
        {
            _controller = GetComponent<CharacterController>();
            _animator = GetComponentInChildren<Animator>(true);
            if (_visual != null)
                _visualBaseRotation = _visual.localRotation;
            _lastPresentationPosition = transform.position;
            TintAsTrainingBot();
        }

        public override void OnStartServer()
        {
            base.OnStartServer();
            _health = MaximumHealth;
            EnterMode(BrainMode.AttackPlayer);
            Debug.Log($"[GAME-BOT] brain_started object={ObjectId} health={_health}.", this);
        }

        private void Update()
        {
            UpdatePresentation();
            if (!IsServerStarted)
                return;

            if (_health <= 0)
            {
                AdvanceKnockout();
                return;
            }

            if (Time.time < _staggeredUntil)
            {
                ApplyKnockbackMotion();
                return;
            }

            if (_attacking)
            {
                AdvanceAttack();
                return;
            }

            if (Time.time >= _modeUntil)
            {
                EnterMode(_mode == BrainMode.AttackPlayer
                    ? BrainMode.PushWall
                    : BrainMode.AttackPlayer);
            }

            if (_mode == BrainMode.AttackPlayer && TryAdvanceAttackMode())
                return;
            if (_mode == BrainMode.PushWall && TryAdvanceWallMode())
                return;

            // Compatibilité avec l'ancien banc labyrinthe : pas de joueur M1 ni
            // de mur autoritaire, donc le bot garde sa petite marche autonome.
            SetPushing(false);
            WalkAimlessly();
        }

        /// <summary>
        /// Entrée historique utilisée par PlayerPunch. Dans le sandbox, un coup de
        /// joueur vaut 25 PV : quatre impacts déclenchent le KO de test.
        /// </summary>
        public void ApplyKnockback(Vector3 velocity)
        {
            ApplyDamageFromServer(PlayerPunchDamage, velocity);
        }

        /// <summary>
        /// Dommage autoritaire reçu par le bot. Le recul et les réactions sont
        /// cosmétiques/répliqués ; aucun client ne choisit ses propres PV.
        /// </summary>
        public bool ApplyDamageFromServer(int damage, Vector3 velocity)
        {
            if (!IsServerStarted || damage <= 0 || _health <= 0)
                return false;

            velocity.y = 0f;
            _knockback = velocity;
            _health = Mathf.Max(0, _health - damage);
            _attacking = false;
            SetPushing(false);

            var knockedOut = _health == 0;
            if (knockedOut)
            {
                _knockedOutUntil = Time.time + KnockoutSeconds;
                _visualKnockedOut = true;
                PlayAnimatorTrigger(KnockoutTrigger);
                SetAnimatorBool(KnockedOutBool, true);
            }
            else
            {
                _staggeredUntil = Time.time + StaggerSeconds;
                _visualStaggeredUntil = _staggeredUntil;
                PlayAnimatorTrigger(HitTrigger);
            }

            PlayDamageObserversRpc(_health, knockedOut);
            if (!_smokeHitLogged)
            {
                _smokeHitLogged = true;
                HumanSmokeTestMode.LogEvent("bot_hit");
            }
            Debug.Log(
                $"[GAME-BOT] hit object={ObjectId} damage={damage} health={_health} ko={knockedOut}.",
                this);
            return true;
        }

        private bool TryAdvanceAttackMode()
        {
            if (!TryResolveTarget())
                return false;

            SetPushing(false);
            var offset = Flat(_target.transform.position - transform.position);
            var distance = offset.magnitude;
            if (distance > AttackRange)
            {
                MoveToward(_target.transform.position, true);
                return true;
            }

            ApplyGravityOnly();
            FaceDirection(offset);
            if (Time.time >= _nextAttackAllowedAt &&
                HasLineOfSight(_target.transform))
            {
                BeginAttack();
            }
            return true;
        }

        private void BeginAttack()
        {
            _attacking = true;
            _attackImpactAt = Time.time + AttackWindupSeconds;
            _nextAttackAllowedAt = Time.time + AttackCooldownSeconds;
            PlayAnimatorTrigger(PunchTrigger);
            PlayAttackObserversRpc();
            Debug.Log($"[GAME-BOT] attack_windup object={ObjectId}.", this);
        }

        private void AdvanceAttack()
        {
            ApplyGravityOnly();
            if (TryResolveTarget())
                FaceDirection(Flat(_target.transform.position - transform.position));
            if (Time.time < _attackImpactAt)
                return;

            _attacking = false;
            if (!TryResolveTarget())
                return;

            var offset = Flat(_target.transform.position - transform.position);
            if (offset.magnitude > AttackRange + 0.15f ||
                (offset.sqrMagnitude > 0.0001f &&
                 Vector3.Angle(transform.forward, offset) > AttackHalfAngle) ||
                !HasLineOfSight(_target.transform))
            {
                Debug.Log($"[GAME-BOT] attack_missed object={ObjectId}.", this);
                return;
            }

            var direction = offset.sqrMagnitude > 0.0001f
                ? offset.normalized
                : transform.forward;
            var applied = _target.ApplyDamageFromServer(
                BotPunchDamage,
                SandboxDamageKind.Punch,
                direction * AttackKnockbackSpeed);
            Debug.Log(
                $"[GAME-BOT] attack_impact object={ObjectId} target={_target.ObjectId} " +
                $"applied={applied} damage={BotPunchDamage}.",
                this);
        }

        private bool TryAdvanceWallMode()
        {
            if (!TryResolveWall())
                return false;

            var normal = _wallView.transform.right.normalized;
            var collider = _wallView.GetComponent<BoxCollider>();
            var halfThickness = collider == null
                ? 0.125f
                : collider.size.x * Mathf.Abs(_wallView.transform.lossyScale.x) * 0.5f;
            var scale = transform.lossyScale;
            var radius = _controller.radius * Mathf.Max(Mathf.Abs(scale.x), Mathf.Abs(scale.z));
            var targetPosition = _wallView.transform.position +
                                 normal * _wallSide * (halfThickness + radius + 0.06f);
            targetPosition.y = transform.position.y;

            if (Flat(targetPosition - transform.position).magnitude > WallTargetTolerance)
            {
                SetPushing(false);
                MoveToward(targetPosition, false);
                return true;
            }

            ApplyGravityOnly();
            FaceDirection(Flat(_wallView.transform.position - transform.position));
            SetPushing(true);
            if (Time.time < _nextWallPushPulseAt)
                return true;

            _nextWallPushPulseAt = Time.time + WallPushPulseSeconds;
            var accepted = _wallDirector.TryRegisterPunchImpulse(
                ObjectId,
                transform.position,
                radius);
            if (accepted && !_wallPushLogged)
            {
                _wallPushLogged = true;
                Debug.Log($"[GAME-BOT] wall_push object={ObjectId} wall={_wallDirector.WallId}.", this);
            }
            return true;
        }

        private void EnterMode(BrainMode mode)
        {
            _mode = mode;
            _modeUntil = Time.time + (mode == BrainMode.AttackPlayer
                ? AttackModeSeconds
                : WallModeSeconds);
            _attacking = false;
            SetPushing(false);
            _wallPushLogged = false;

            if (mode == BrainMode.PushWall && TryResolveWall())
            {
                var normal = _wallView.transform.right.normalized;
                var side = Vector3.Dot(transform.position - _wallView.transform.position, normal);
                if (Mathf.Abs(side) > 0.05f)
                    _wallSide = Mathf.Sign(side);
            }

            Debug.Log($"[GAME-BOT] mode object={ObjectId} value={mode}.", this);
        }

        private bool TryResolveTarget()
        {
            if (_target != null && _target.IsServerStarted && _target.IsAlive)
                return true;

            _target = null;
            var bestDistance = float.PositiveInfinity;
            foreach (var candidate in FindObjectsByType<SandboxPlayerGameplay>(FindObjectsSortMode.None))
            {
                if (candidate == null || !candidate.IsServerStarted || !candidate.IsAlive)
                    continue;
                var distance = Flat(candidate.transform.position - transform.position).sqrMagnitude;
                if (distance >= bestDistance)
                    continue;
                bestDistance = distance;
                _target = candidate;
            }
            return _target != null;
        }

        private bool TryResolveWall()
        {
            if (_wallDirector == null)
                _wallDirector = FindFirstObjectByType<M1AuthoritativeWallDirector>();
            if (_wallDirector == null)
                return false;

            if (_wallView == null)
            {
                var arena = FindFirstObjectByType<TopologyArena>();
                if (arena == null || arena.Map == null)
                    return false;
                _wallView = arena.GetWallView(_wallDirector.WallId);
            }
            return _wallView != null;
        }

        private void MoveToward(Vector3 destination, bool avoidObstacles)
        {
            var desired = Flat(destination - transform.position);
            if (desired.sqrMagnitude < 0.0001f)
            {
                ApplyGravityOnly();
                return;
            }
            desired.Normalize();

            if (avoidObstacles && WorldAhead(desired))
            {
                if (!_turning)
                {
                    _turning = true;
                    _turnDirection = -_turnDirection;
                }
                desired = Quaternion.AngleAxis(72f * _turnDirection, Vector3.up) * desired;
            }
            else
            {
                _turning = false;
            }

            FaceDirection(desired);
            _verticalVelocity = _controller.isGrounded
                ? -3f
                : _verticalVelocity + Gravity * Time.deltaTime;
            var motion = transform.forward * WalkSpeed;
            motion.y = _verticalVelocity;
            _controller.Move(motion * Time.deltaTime);
        }

        private void FaceDirection(Vector3 direction)
        {
            if (direction.sqrMagnitude < 0.0001f)
                return;
            var targetRotation = Quaternion.LookRotation(direction.normalized, Vector3.up);
            transform.rotation = Quaternion.RotateTowards(
                transform.rotation,
                targetRotation,
                TurnSpeed * Time.deltaTime);
        }

        private void WalkAimlessly()
        {
            if (WorldAhead(transform.forward))
            {
                if (!_turning)
                {
                    _turning = true;
                    _turnDirection = -_turnDirection;
                }
                transform.Rotate(0f, TurnSpeed * _turnDirection * Time.deltaTime, 0f, Space.Self);
                ApplyGravityOnly();
                return;
            }

            _turning = false;
            _verticalVelocity = _controller.isGrounded
                ? -3f
                : _verticalVelocity + Gravity * Time.deltaTime;
            var motion = transform.forward * WalkSpeed;
            motion.y = _verticalVelocity;
            _controller.Move(motion * Time.deltaTime);
        }

        private void ApplyGravityOnly()
        {
            _verticalVelocity = _controller.isGrounded
                ? -3f
                : _verticalVelocity + Gravity * Time.deltaTime;
            _controller.Move(Vector3.up * (_verticalVelocity * Time.deltaTime));
        }

        private void ApplyKnockbackMotion()
        {
            _verticalVelocity = _controller.isGrounded
                ? -3f
                : _verticalVelocity + Gravity * Time.deltaTime;
            var motion = _knockback;
            motion.y = _verticalVelocity;
            _controller.Move(motion * Time.deltaTime);
            _knockback = Vector3.MoveTowards(
                _knockback,
                Vector3.zero,
                KnockbackDecay * Time.deltaTime);
        }

        private void AdvanceKnockout()
        {
            SetPushing(false);
            ApplyKnockbackMotion();
            if (Time.time < _knockedOutUntil)
                return;

            _health = MaximumHealth;
            _knockback = Vector3.zero;
            _visualKnockedOut = false;
            _visualStaggeredUntil = float.NegativeInfinity;
            SetAnimatorBool(KnockedOutBool, false);
            PlayAnimatorTrigger(RecoverTrigger);
            PlayRecoveryObserversRpc();
            EnterMode(BrainMode.AttackPlayer);
            Debug.Log($"[GAME-BOT] recovered object={ObjectId} health={_health}.", this);
        }

        private bool HasLineOfSight(Transform target)
        {
            var start = transform.position + Vector3.up * ChestHeight;
            var end = target.position + Vector3.up * ChestHeight;
            if (!Physics.Linecast(start, end, out var hit, ~0, QueryTriggerInteraction.Ignore))
                return true;
            return hit.transform == target || hit.transform.IsChildOf(target);
        }

        private bool WorldAhead(Vector3 direction)
        {
            var chest = transform.position + Vector3.up * ChestHeight;
            var worldMask = 1 << GameplayLayers.World;
            return Physics.Raycast(
                chest,
                direction,
                WallProbeDistance,
                worldMask,
                QueryTriggerInteraction.Ignore);
        }

        private void SetPushing(bool pushing)
        {
            if (_pushing == pushing)
                return;
            _pushing = pushing;
            SetAnimatorBool(PushBool, pushing);
            SetPushingObserversRpc(pushing);
        }

        private void UpdatePresentation()
        {
            var deltaTime = Mathf.Max(Time.deltaTime, 0.0001f);
            var delta = Flat(transform.position - _lastPresentationPosition);
            var measuredSpeed = delta.magnitude / deltaTime;
            _presentationSpeed = Mathf.Lerp(
                _presentationSpeed,
                measuredSpeed,
                1f - Mathf.Exp(-12f * deltaTime));
            _lastPresentationPosition = transform.position;

            if (_animator != null && _animator.runtimeAnimatorController != null)
            {
                _animator.SetFloat(MoveSpeedFloat, _presentationSpeed);
                _animator.SetBool(GroundedBool, _controller != null && _controller.isGrounded);
                _animator.SetBool(SprintingBool, false);
                _animator.SetBool(CarryingBool, false);
            }

            if (_visual == null)
                return;
            var tilt = _visualKnockedOut
                ? KnockoutTilt
                : Time.time < _visualStaggeredUntil
                    ? StaggerTilt * Mathf.InverseLerp(
                        0f,
                        StaggerSeconds,
                        _visualStaggeredUntil - Time.time)
                    : 0f;
            _visual.localRotation = _visualBaseRotation * Quaternion.Euler(tilt, 0f, 0f);
        }

        private void TintAsTrainingBot()
        {
            if (_visual == null)
                return;
            var block = new MaterialPropertyBlock();
            foreach (var renderer in _visual.GetComponentsInChildren<Renderer>(true))
            {
                renderer.GetPropertyBlock(block);
                block.SetColor(BaseColorId, new Color(1f, 0.28f, 0.18f, 1f));
                renderer.SetPropertyBlock(block);
                block.Clear();
            }
        }

        private void PlayAnimatorTrigger(int trigger)
        {
            if (_animator != null && _animator.runtimeAnimatorController != null)
                _animator.SetTrigger(trigger);
        }

        private void SetAnimatorBool(int parameter, bool value)
        {
            if (_animator != null && _animator.runtimeAnimatorController != null)
                _animator.SetBool(parameter, value);
        }

        [ObserversRpc(ExcludeServer = true)]
        private void PlayAttackObserversRpc()
        {
            PlayAnimatorTrigger(PunchTrigger);
        }

        [ObserversRpc(ExcludeServer = true, BufferLast = true)]
        private void SetPushingObserversRpc(bool pushing)
        {
            _pushing = pushing;
            SetAnimatorBool(PushBool, pushing);
        }

        [ObserversRpc(ExcludeServer = true)]
        private void PlayDamageObserversRpc(int health, bool knockedOut)
        {
            _health = health;
            if (knockedOut)
            {
                _visualKnockedOut = true;
                SetAnimatorBool(KnockedOutBool, true);
                PlayAnimatorTrigger(KnockoutTrigger);
            }
            else
            {
                _visualStaggeredUntil = Time.time + StaggerSeconds;
                PlayAnimatorTrigger(HitTrigger);
            }
        }

        [ObserversRpc(ExcludeServer = true)]
        private void PlayRecoveryObserversRpc()
        {
            _health = MaximumHealth;
            _visualKnockedOut = false;
            _visualStaggeredUntil = float.NegativeInfinity;
            SetAnimatorBool(KnockedOutBool, false);
            PlayAnimatorTrigger(RecoverTrigger);
        }

        private void OnGUI()
        {
            if (!IsServerStarted)
                return;

            const float width = 300f;
            const float height = 72f;
            GUILayout.BeginArea(
                new Rect(Screen.width - width - 16f, 16f, width, height),
                GUI.skin.box);
            GUILayout.Label($"BOT TEST — {_health}/{MaximumHealth} PV");
            var action = _health <= 0
                ? "KO — il va se relever"
                : _mode == BrainMode.AttackPlayer
                    ? "cherche à te frapper"
                    : "essaie de pousser le mur";
            GUILayout.Label($"IA simple : {action} · frappe-le 4×");
            GUILayout.EndArea();
        }

        private static Vector3 Flat(Vector3 value) => new(value.x, 0f, value.z);
    }
}
