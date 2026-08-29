using System;
using System.Collections.Generic;
using FishNet.Connection;
using FishNet.Object;
using FishNet.Object.Prediction;
using FishNet.Transporting;
using FishNet.Utility.Template;
using NotThatWay.Game.Input;
using NotThatWay.Game.PlayerNetwork;
using NotThatWay.Game.PlayerSimulation;
using NotThatWay.Game.Sandbox;
using NotThatWay.Game.Simulation;
using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Adaptateur M1 FishNet autour de PlayerStateMachine. Le propriétaire ne transmet
    /// que des intentions ; le serveur simule le même tick et publie l'état complet.
    /// </summary>
    [DisallowMultipleComponent]
    [RequireComponent(typeof(CharacterController))]
    [RequireComponent(typeof(PlayerInputSource))]
    public sealed class PredictedPlayerMotor : TickNetworkBehaviour
    {
        private static readonly List<PredictedPlayerMotor> ServerInstances = new();

        [Header("Présentation locale")]
        [SerializeField] private Transform _cameraPivot;
        [SerializeField] private Camera _camera;

        [Header("Paramètres de banc — à sérialiser explicitement")]
        [SerializeField, Min(0f)] private float _walkSpeed = 4.2f;
        [SerializeField, Min(0f)] private float _sprintSpeed = 7f;
        [SerializeField, Min(0f)] private float _groundAcceleration = 35f;
        [SerializeField, Min(0f)] private float _airAcceleration = 12f;
        [SerializeField, Min(0f)] private float _groundDeceleration = 45f;
        [SerializeField, Min(0f)] private float _airDeceleration = 8f;
        [SerializeField] private float _gravity = -22f;
        [SerializeField] private float _groundedVelocity = -3f;
        [SerializeField] private bool _jumpEnabled;
        [SerializeField, Min(0f)] private float _jumpSpeed = 5.5f;
        [SerializeField] private uint _coyoteTicks = 7u;
        [SerializeField] private uint _jumpBufferTicks = 9u;
        [SerializeField, Min(0f)] private float _knockbackDecay = 10f;
        [SerializeField] private bool _diveEnabled;
        [SerializeField, Min(0f)] private float _diveForwardSpeed = 13f;
        [SerializeField, Min(0f)] private float _diveUpwardSpeed = 4.2f;
        [SerializeField] private uint _diveRecoveryTicks = 24u;
        [SerializeField] private uint _diveCooldownTicks = 90u;
        [SerializeField] private bool _crawlEnabled;
        [SerializeField, Min(0f)] private float _crawlSpeed = 1.7f;
        [SerializeField, Min(0f)] private float _crawlHeight = 0.85f;
        [SerializeField, Range(0, PlayerState.PhysicalPitchLimitCentidegrees)]
        private int _maximumPitchCentidegrees = 8500;

        private CharacterController _controller;
        private PlayerInputSource _inputSource;
        private SandboxPlayerGameplay _sandboxGameplay;
        private UnityCharacterControllerWorld _collisionWorld;
        private PlayerStateMachine _simulation;
        private PlayerVector3 _pendingKnockbackVelocityDelta;
        private PlayerReplicateData _lastTickedReplicateData;
        private bool _hasLastTickedReplicateData;
        private bool _cursorLocked;
        private bool _ownsPresentation;
        private uint _rejectedCommandCount;
        private uint _reconcileCount;
        private float _lastCorrectionMeters;
        private PlayerCommand _latestAuthoritativeCommand;
        private bool _hasLatestAuthoritativeCommand;
        private M1AutomatedCommandSource _automatedCommands;
        private string _automationParseError;
        private bool _automationLogged;

        public bool IsSimulationReady => _simulation != null;
        public uint SimulationTick => _simulation?.State.Tick ?? 0u;
        public PlayerState SimulationState => _simulation?.State ?? default;
        public uint RejectedCommandCount => _rejectedCommandCount;
        public uint ReconcileCount => _reconcileCount;
        public float LastCorrectionMeters => _lastCorrectionMeters;
        public CharacterController CharacterController => _controller;

        private void Awake()
        {
            _controller = GetComponent<CharacterController>();
            _inputSource = GetComponent<PlayerInputSource>();
            _sandboxGameplay = GetComponent<SandboxPlayerGameplay>();
            _collisionWorld = new UnityCharacterControllerWorld(_controller);
            if (!M1AutomatedCommandSource.TryParseArguments(
                    Environment.GetCommandLineArgs(),
                    out _automatedCommands,
                    out _automationParseError))
            {
                _automatedCommands = default;
            }
            SetTickCallbacks(TickCallback.Tick | TickCallback.PostTick);
        }

        public override void OnStartClient()
        {
            base.OnStartClient();
            SetOwnerPresentation(IsOwner);
        }

        public override void OnStartServer()
        {
            base.OnStartServer();
            if (!ServerInstances.Contains(this))
                ServerInstances.Add(this);
        }

        public override void OnStopServer()
        {
            ServerInstances.Remove(this);
            _hasLatestAuthoritativeCommand = false;
            base.OnStopServer();
        }

        public override void OnStopClient()
        {
            if (_inputSource != null)
                _inputSource.enabled = false;
            if (_ownsPresentation)
            {
                SetCursorLocked(false);
                _ownsPresentation = false;
            }
            base.OnStopClient();
        }

        public override void OnOwnershipClient(NetworkConnection previousOwner)
        {
            base.OnOwnershipClient(previousOwner);
            if (_inputSource != null)
                _inputSource.ResetBufferedInput();
            SetOwnerPresentation(IsOwner);
        }

        private void Update()
        {
            if (!IsOwner || _inputSource == null)
                return;
            if (_inputSource.PausePressedThisFrame)
                SetCursorLocked(!_cursorLocked);
        }

        protected override void TimeManager_OnTick()
        {
            SimulateReplicate(BuildReplicateData());
        }

        protected override void TimeManager_OnPostTick()
        {
            CreateReconcile();
        }

        private PlayerReplicateData BuildReplicateData()
        {
            if (!IsOwner)
                return default;

            if (_automatedCommands.Enabled)
            {
                var simulationTick = TickMath.Next(_simulation?.State.Tick ?? 0u);
                return new PlayerReplicateData(
                    _automatedCommands.CreateCommand(simulationTick));
            }

            if (_inputSource == null || !_inputSource.IsReady)
                return default;

            var command = _inputSource.ConsumeCommand(
                TimeManager.LocalTick,
                (float)TimeManager.TickDelta);
            if (!_cursorLocked && (command.LookYaw != 0 || command.LookPitch != 0))
            {
                command = new PlayerCommand(
                    command.Tick,
                    command.MoveX,
                    command.MoveY,
                    0,
                    0,
                    command.Buttons);
            }
            return new PlayerReplicateData(command);
        }

        public override void CreateReconcile()
        {
            if (_simulation == null)
                return;

            // Appel direct requis par le codegen FishNet.
            SimulateReconcile(new PlayerReconcileData(_simulation.State));
        }

        [Replicate]
        private void SimulateReplicate(
            PlayerReplicateData data,
            ReplicateState replicateState = ReplicateState.Invalid,
            Channel channel = Channel.Unreliable)
        {
            EnsureSimulation();
            if (!_controller.enabled)
                return;

            data = ResolveForwardedInput(data, replicateState);
            var simulationTick = TickMath.Next(_simulation.State.Tick);
            var command = ValidatedCommand(data, simulationTick);
            if (_sandboxGameplay != null)
                command = _sandboxGameplay.FilterCommandForSimulation(command);
            PlayerTickForces forces = default;
            if (replicateState.ContainsTicked() &&
                !_pendingKnockbackVelocityDelta.Equals(PlayerVector3.Zero))
            {
                forces = new PlayerTickForces(_pendingKnockbackVelocityDelta);
                _pendingKnockbackVelocityDelta = PlayerVector3.Zero;
            }

            var modifiers = _sandboxGameplay == null
                ? PlayerTickModifiers.FullSpeed
                : new PlayerTickModifiers(_sandboxGameplay.MovementSpeedPermilleFor(command));
            var result = _simulation.AdvanceTick(command, forces, modifiers, _collisionWorld);
            if (IsServerStarted && replicateState.ContainsTicked() &&
                !replicateState.ContainsReplayed())
            {
                _latestAuthoritativeCommand = command;
                _hasLatestAuthoritativeCommand = true;
            }
            ApplyPresentation(result.Current);
        }

        public bool TryGetLatestAuthoritativeCommand(out PlayerCommand command)
        {
            if (IsServerStarted && _hasLatestAuthoritativeCommand)
            {
                command = _latestAuthoritativeCommand;
                return true;
            }

            command = default;
            return false;
        }

        internal static void CopyServerInstances(List<PredictedPlayerMotor> destination)
        {
            if (destination == null)
                throw new ArgumentNullException(nameof(destination));
            destination.Clear();
            for (var index = 0; index < ServerInstances.Count; index++)
            {
                var motor = ServerInstances[index];
                if (motor != null && motor.IsServerStarted)
                    destination.Add(motor);
            }
        }

        [Reconcile]
        private void SimulateReconcile(
            PlayerReconcileData data,
            Channel channel = Channel.Unreliable)
        {
            var state = data.ToState();
            var before = transform.position;
            EnsureSimulation(state);
            _simulation.RestoreState(state);
            _collisionWorld.SetPose(state.Position, state.YawCentidegrees);
            _lastCorrectionMeters = Vector3.Distance(before, transform.position);
            _reconcileCount++;
            ApplyPresentation(state);
        }

        /// <summary>
        /// Injection autoritaire provisoire du knockback. Le serveur conserve sa
        /// propre impulsion et la copie propriétaire la prédit jusqu'au prochain reconcile.
        /// </summary>
        public void ApplyKnockbackFromServer(Vector3 velocity)
        {
            if (!IsServerStarted || !Owner.IsValid)
                return;

            QueueKnockback(velocity);
            if (!Owner.IsLocalClient)
                ApplyKnockbackTargetRpc(Owner, velocity);
        }

        /// <summary>
        /// Maintient la composante tangentielle du recul à une vitesse cible. À
        /// la différence d'un coup de poing, l'appui continu d'un battant ne doit
        /// pas empiler une nouvelle impulsion complète à chaque échantillon.
        /// </summary>
        public void ApplyPushVelocityFromServer(Vector3 targetVelocity)
        {
            if (!IsServerStarted || !Owner.IsValid)
                return;

            targetVelocity.y = 0f;
            var currentVelocity = _simulation?.State.KnockbackVelocity ?? PlayerVector3.Zero;
            var correction = PlayerPushVelocity.CorrectionToTarget(
                currentVelocity,
                _pendingKnockbackVelocityDelta,
                UnityCharacterControllerWorld.ToDomain(targetVelocity));
            var unityCorrection = new Vector3(
                (float)correction.X,
                0f,
                (float)correction.Z);
            if (unityCorrection.sqrMagnitude <= 0.000001f)
                return;

            QueueKnockback(unityCorrection);
            if (!Owner.IsLocalClient)
                ApplyPushCorrectionTargetRpc(Owner, unityCorrection);
        }

        [TargetRpc]
        private void ApplyKnockbackTargetRpc(NetworkConnection connection, Vector3 velocity)
        {
            QueueKnockback(velocity);
        }

        [TargetRpc]
        private void ApplyPushCorrectionTargetRpc(
            NetworkConnection connection,
            Vector3 velocityCorrection)
        {
            QueueKnockback(velocityCorrection);
        }

        private void QueueKnockback(Vector3 velocity)
        {
            velocity.y = 0f;
            _pendingKnockbackVelocityDelta += UnityCharacterControllerWorld.ToDomain(velocity);
        }

        private void EnsureSimulation()
        {
            if (_simulation != null)
            {
                EnsureTickDurationUnchanged();
                return;
            }

            var config = CreateConfig();
            var grounded = _controller.enabled && _controller.isGrounded;
            var initial = new PlayerState(
                0u,
                UnityCharacterControllerWorld.ToDomain(transform.position),
                QuantizeYaw(transform.eulerAngles.y),
                0,
                PlayerVector3.Zero,
                grounded ? config.GroundedVelocityMetersPerSecond : 0d,
                PlayerVector3.Zero,
                grounded);
            _simulation = new PlayerStateMachine(config, initial);
        }

        private void EnsureSimulation(PlayerState authoritativeState)
        {
            if (_simulation == null)
            {
                var config = CreateConfig();
                _simulation = new PlayerStateMachine(config, authoritativeState);
                return;
            }

            EnsureTickDurationUnchanged();
        }

        private PlayerSimulationConfig CreateConfig()
        {
            var scale = transform.lossyScale;
            var height = _controller.height * Mathf.Abs(scale.y);
            var radius = _controller.radius * Mathf.Max(Mathf.Abs(scale.x), Mathf.Abs(scale.z));
            return new PlayerSimulationConfig(
                TimeManager.TickDelta,
                height,
                radius,
                _walkSpeed,
                _sprintSpeed,
                _groundAcceleration,
                _airAcceleration,
                _groundDeceleration,
                _airDeceleration,
                _gravity,
                _groundedVelocity,
                _jumpEnabled,
                _jumpSpeed,
                _coyoteTicks,
                _jumpBufferTicks,
                _knockbackDecay,
                _maximumPitchCentidegrees,
                _diveEnabled,
                _diveForwardSpeed,
                _diveUpwardSpeed,
                _diveRecoveryTicks,
                _diveCooldownTicks,
                _crawlEnabled,
                _crawlSpeed,
                _crawlHeight);
        }

        private void EnsureTickDurationUnchanged()
        {
            var current = TimeManager.TickDelta;
            if (Math.Abs(_simulation.Config.TickDurationSeconds - current) > 0.000000001d)
            {
                throw new InvalidOperationException(
                    "Le tick rate FishNet a changé pendant une simulation joueur active.");
            }
        }

        private void ApplyPresentation(PlayerState state)
        {
            if (_cameraPivot != null && IsOwner)
            {
                _cameraPivot.localRotation = Quaternion.Euler(
                    -state.PitchCentidegrees / 100f,
                    0f,
                    0f);
            }
        }

        private void SetOwnerPresentation(bool isOwner)
        {
            if (_inputSource != null)
                _inputSource.enabled = isOwner;
            if (_camera != null)
                _camera.gameObject.SetActive(isOwner);
            if (isOwner)
            {
                LogAutomationConfiguration();
                _ownsPresentation = true;
                var spectator = FindFirstObjectByType<SpectatorCamera>(FindObjectsInactive.Exclude);
                if (spectator != null)
                    spectator.gameObject.SetActive(false);
                SetCursorLocked(true);
            }
            else if (_ownsPresentation)
            {
                SetCursorLocked(false);
                _ownsPresentation = false;
            }
        }

        private void LogAutomationConfiguration()
        {
            if (_automationLogged)
                return;
            _automationLogged = true;
            if (!string.IsNullOrEmpty(_automationParseError))
            {
                Debug.LogError(
                    $"[GAME-M1-AUTO] invalid_player_profile reason={_automationParseError}.",
                    this);
                return;
            }
            if (!_automatedCommands.WasSpecified)
                return;
            if (!Debug.isDebugBuild && !Application.isEditor)
            {
                Debug.LogError("[GAME-M1-AUTO] player automation refused outside Development build.", this);
                _automatedCommands = default;
                return;
            }
            Debug.Log(
                $"[GAME-M1-AUTO] player_profile={_automatedCommands.Name} object={ObjectId}.",
                this);
        }

        /// <summary>Le menu pause s'affiche quand le curseur est libre (Échap).</summary>
        public bool CursorLocked => _cursorLocked;

        /// <summary>Reprendre depuis le menu : re-verrouille le curseur du porteur.</summary>
        public void ResumeFromMenu()
        {
            if (IsOwner)
                SetCursorLocked(true);
        }

        private void SetCursorLocked(bool locked)
        {
            _cursorLocked = locked;
            Cursor.lockState = locked ? CursorLockMode.Locked : CursorLockMode.None;
            Cursor.visible = !locked;
        }

        private PlayerReplicateData ResolveForwardedInput(
            PlayerReplicateData data,
            ReplicateState replicateState)
        {
            if (IsServerStarted || IsOwner)
                return data;

            if (replicateState.ContainsTicked())
            {
                _lastTickedReplicateData = data;
                _hasLastTickedReplicateData = true;
                return data;
            }

            if (!replicateState.IsFuture())
                return data;

            var fishNetTick = data.GetTick();
            if (!_hasLastTickedReplicateData ||
                !TickMath.IsNext(fishNetTick, _lastTickedReplicateData.GetTick()))
            {
                var neutral = default(PlayerReplicateData);
                neutral.SetTick(fishNetTick);
                return neutral;
            }

            var predicted = _lastTickedReplicateData.WithoutOneShotInputs();
            predicted.SetTick(fishNetTick);
            return predicted;
        }

        private PlayerCommand ValidatedCommand(
            PlayerReplicateData data,
            uint simulationTick)
        {
            const PlayerCommandButtons knownButtons =
                PlayerInputSample.HeldMask | PlayerInputSample.PressedMask;
            var buttons = (PlayerCommandButtons)data.Buttons;
            var malformed = data.MoveX == sbyte.MinValue ||
                            data.MoveY == sbyte.MinValue ||
                            (buttons & ~knownButtons) != 0;
            if (!malformed)
                return data.ToCommand(simulationTick);

            _rejectedCommandCount++;
            if (_rejectedCommandCount == 1u || _rejectedCommandCount % 120u == 0u)
            {
                Debug.LogWarning(
                    $"[GAME-PLAYER] Payload invalide neutralisé au tick {data.GetTick()}.",
                    this);
            }

            return new PlayerCommand(
                simulationTick,
                0,
                0,
                data.LookYaw,
                data.LookPitch,
                PlayerCommandButtons.None);
        }

        private static int QuantizeYaw(float yawDegrees)
        {
            var centidegrees = (int)Math.Round(
                yawDegrees * 100d,
                MidpointRounding.AwayFromZero);
            centidegrees %= PlayerState.FullYawCentidegrees;
            return centidegrees < 0
                ? centidegrees + PlayerState.FullYawCentidegrees
                : centidegrees;
        }
    }
}
