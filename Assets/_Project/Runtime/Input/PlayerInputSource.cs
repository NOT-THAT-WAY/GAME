using System;
using NotThatWay.Game.PlayerSimulation;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;

namespace NotThatWay.Game.Input
{
    /// <summary>
    /// Unique frontière vers les périphériques. Chaque instance clone son asset,
    /// échantillonne les frames et conserve les fronts jusqu'au prochain tick.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class PlayerInputSource : MonoBehaviour
    {
        [SerializeField] private InputActionAsset _sourceAsset;
        [SerializeField, Min(0f)] private float _pointerDegreesPerPixel = 0.12f;
        [SerializeField, Min(0f)] private float _stickDegreesPerSecond = 180f;

        private readonly PlayerCommandAccumulator _accumulator = new();
        private InputActionAsset _runtimeAsset;
        private InputActionMap _playerMap;
        private InputAction _move;
        private InputAction _lookPointer;
        private InputAction _lookStick;
        private InputAction _sprint;
        private InputAction _interact;
        private InputAction _punch;
        private InputAction _jump;
        private InputAction _pause;
        private InputDevice[] _restrictedDevices;
        private Vector2 _latestStick;
        private bool _subscribedToInputUpdates;
        private bool _hasFocus = true;

        public bool IsReady => _runtimeAsset != null && _playerMap != null && _playerMap.enabled;
        public bool PausePressedThisFrame { get; private set; }
        public PlayerInputSample CurrentFrame { get; private set; }

        public void Configure(InputActionAsset sourceAsset)
        {
            if (sourceAsset == null)
                throw new ArgumentNullException(nameof(sourceAsset));
            if (!GameControlsContract.TryValidate(sourceAsset, out var error))
                throw new ArgumentException($"Asset Input Actions invalide: {error}.", nameof(sourceAsset));

            ResetBufferedInput();
            DisposeRuntimeAsset();
            _sourceAsset = sourceAsset;
            if (isActiveAndEnabled)
                InitializeRuntimeAsset();
        }

        /// <summary>
        /// Restreint cette copie à des périphériques précis, utile pour plusieurs
        /// joueurs locaux et pour les tests. Un tableau vide signifie aucun device.
        /// </summary>
        public void RestrictToDevices(params InputDevice[] devices)
        {
            if (devices == null)
                throw new ArgumentNullException(nameof(devices));

            _restrictedDevices = (InputDevice[])devices.Clone();
            ResetBufferedInput();
            if (_runtimeAsset != null)
                _runtimeAsset.devices = _restrictedDevices;
        }

        public void UseAllDevices()
        {
            _restrictedDevices = null;
            ResetBufferedInput();
            if (_runtimeAsset != null)
                _runtimeAsset.devices = null;
        }

        public PlayerCommand ConsumeCommand(uint tick, float tickDurationSeconds)
        {
            if (!IsReady)
                throw new InvalidOperationException("PlayerInputSource n'est pas initialisé.");
            if (float.IsNaN(tickDurationSeconds) || float.IsInfinity(tickDurationSeconds) ||
                tickDurationSeconds <= 0f)
            {
                throw new ArgumentOutOfRangeException(nameof(tickDurationSeconds));
            }

            if (!_hasFocus)
                return _accumulator.Consume(tick);

            // Le stick est un taux : une seule intégration par tick. Le pointeur est
            // un delta et a déjà été additionné frame par frame dans l'accumulateur.
            var held = ReadHeldButtons();
            var move = _move.ReadValue<Vector2>();
            _accumulator.Accumulate(new PlayerInputSample(
                move.x,
                move.y,
                _latestStick.x * _stickDegreesPerSecond * tickDurationSeconds,
                _latestStick.y * _stickDegreesPerSecond * tickDurationSeconds,
                held,
                PlayerCommandButtons.None));
            return _accumulator.Consume(tick);
        }

        public void ResetBufferedInput()
        {
            _accumulator.Reset();
            _latestStick = Vector2.zero;
            CurrentFrame = default;
            PausePressedThisFrame = false;
        }

        private void OnEnable()
        {
            _hasFocus = !Application.isPlaying || Application.isFocused || Application.isBatchMode;
            ResetBufferedInput();
            if (_sourceAsset != null)
                InitializeRuntimeAsset();
        }

        private void HandleAfterInputUpdate()
        {
            if (!IsReady || !_hasFocus)
                return;
            var updateType = InputState.currentUpdateType;
            if (updateType == InputUpdateType.BeforeRender || updateType == InputUpdateType.Editor)
                return;

            var move = _move.ReadValue<Vector2>();
            var pointer = _lookPointer.ReadValue<Vector2>();
            _latestStick = _lookStick.ReadValue<Vector2>();
            var held = ReadHeldButtons();
            var pressed = PlayerCommandButtons.None;
            if (_jump.WasPressedThisFrame())
                pressed |= PlayerCommandButtons.JumpPressed;
            if (_interact.WasPressedThisFrame())
                pressed |= PlayerCommandButtons.InteractPressed;
            if (_punch.WasPressedThisFrame())
                pressed |= PlayerCommandButtons.PunchPressed;

            PausePressedThisFrame = _pause.WasPressedThisFrame();
            var pointerYaw = pointer.x * _pointerDegreesPerPixel;
            var pointerPitch = pointer.y * _pointerDegreesPerPixel;
            CurrentFrame = new PlayerInputSample(
                move.x,
                move.y,
                pointerYaw + _latestStick.x * _stickDegreesPerSecond * Time.unscaledDeltaTime,
                pointerPitch + _latestStick.y * _stickDegreesPerSecond * Time.unscaledDeltaTime,
                held,
                pressed);
            _accumulator.Accumulate(new PlayerInputSample(
                move.x,
                move.y,
                pointerYaw,
                pointerPitch,
                held,
                pressed));
        }

        private PlayerCommandButtons ReadHeldButtons()
        {
            var held = PlayerCommandButtons.None;
            if (_sprint.IsPressed())
                held |= PlayerCommandButtons.SprintHeld;
            if (_interact.IsPressed())
                held |= PlayerCommandButtons.InteractHeld;
            return held;
        }

        private void OnApplicationFocus(bool hasFocus)
        {
            _hasFocus = hasFocus;
            ResetBufferedInput();
        }

        private void OnDisable()
        {
            ResetBufferedInput();
            DisposeRuntimeAsset();
        }

        private void InitializeRuntimeAsset()
        {
            if (_runtimeAsset != null)
                return;
            if (!GameControlsContract.TryValidate(_sourceAsset, out var error))
            {
                Debug.LogError($"[GAME-INPUT] Asset invalide: {error}.", this);
                return;
            }

            _runtimeAsset = Instantiate(_sourceAsset);
            _runtimeAsset.name = $"{_sourceAsset.name} ({name})";
            if (_restrictedDevices != null)
                _runtimeAsset.devices = _restrictedDevices;

            _playerMap = _runtimeAsset.FindActionMap(GameControlsContract.PlayerMap, true);
            _move = _playerMap.FindAction(GameControlsContract.Move, true);
            _lookPointer = _playerMap.FindAction(GameControlsContract.LookPointer, true);
            _lookStick = _playerMap.FindAction(GameControlsContract.LookStick, true);
            _sprint = _playerMap.FindAction(GameControlsContract.Sprint, true);
            _interact = _playerMap.FindAction(GameControlsContract.Interact, true);
            _punch = _playerMap.FindAction(GameControlsContract.Punch, true);
            _jump = _playerMap.FindAction(GameControlsContract.Jump, true);
            _pause = _playerMap.FindAction(GameControlsContract.Pause, true);
            _playerMap.Enable();
            InputSystem.onAfterUpdate += HandleAfterInputUpdate;
            _subscribedToInputUpdates = true;
        }

        private void DisposeRuntimeAsset()
        {
            if (_runtimeAsset == null)
                return;

            if (_subscribedToInputUpdates)
            {
                InputSystem.onAfterUpdate -= HandleAfterInputUpdate;
                _subscribedToInputUpdates = false;
            }
            _runtimeAsset.Disable();
            if (Application.isPlaying)
                Destroy(_runtimeAsset);
            else
                DestroyImmediate(_runtimeAsset);

            _runtimeAsset = null;
            _playerMap = null;
            _move = null;
            _lookPointer = null;
            _lookStick = null;
            _sprint = null;
            _interact = null;
            _punch = null;
            _jump = null;
            _pause = null;
        }
    }
}
