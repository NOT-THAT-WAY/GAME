using System;
using FishNet.Object;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.Rendering;

namespace NotThatWay.Game
{
    /// <summary>
    /// Déplacement prototype du sprint A : marche, sprint et vue souris sur un
    /// <see cref="CharacterController"/>. L'autorité reste côté client pour ce
    /// premier test jouable ; l'autorité hôte est le sujet du sprint B et n'est
    /// volontairement pas anticipée ici.
    /// </summary>
    [RequireComponent(typeof(CharacterController))]
    public sealed class PlayerMotor : NetworkBehaviour
    {
        private const float WalkSpeed = 4.2f;
        private const float SprintSpeed = 7.0f;
        private const float Gravity = -22f;
        private const float GroundedVelocity = -3f;
        private const float LookSensitivity = 0.12f;
        private const float MaxPitch = 85f;

        private static readonly Vector3 FirstPersonOffset = Vector3.zero;
        private static readonly Vector3 ThirdPersonOffset = new(0f, 0.55f, -3.4f);

        [SerializeField] private Transform _cameraPivot;
        [SerializeField] private Camera _camera;
        [SerializeField] private Transform _visual;

        private CharacterController _controller;
        private Renderer[] _visualRenderers = Array.Empty<Renderer>();
        private ConnectionSmokeTest _sessionPanel;
        private float _pitch;
        private float _verticalVelocity;
        private bool _thirdPerson;
        private bool _cursorLocked;

        private void Awake()
        {
            _controller = GetComponent<CharacterController>();
            if (_visual != null)
                _visualRenderers = _visual.GetComponentsInChildren<Renderer>(true);
        }

        public override void OnStartClient()
        {
            base.OnStartClient();
            if (!IsOwner)
                return;

            var spectator = FindFirstObjectByType<SpectatorCamera>(FindObjectsInactive.Exclude);
            if (spectator != null)
                spectator.gameObject.SetActive(false);

            _sessionPanel = FindFirstObjectByType<ConnectionSmokeTest>(FindObjectsInactive.Include);
            if (_camera != null)
                _camera.gameObject.SetActive(true);

            ApplyCameraMode();
            SetCursorLocked(true);
        }

        public override void OnStopClient()
        {
            base.OnStopClient();
            if (IsOwner)
                SetCursorLocked(false);
        }

        private void Update()
        {
            // Les copies distantes sont pilotées par le NetworkTransform : seul le
            // propriétaire calcule un déplacement.
            if (!IsOwner)
                return;

            ReadToggles();
            ApplyLook();
            ApplyMove();
        }

        private void ReadToggles()
        {
            var keyboard = Keyboard.current;
            if (keyboard == null)
                return;

            if (keyboard.escapeKey.wasPressedThisFrame)
                SetCursorLocked(!_cursorLocked);

            if (keyboard.tabKey.wasPressedThisFrame && _sessionPanel != null)
                _sessionPanel.enabled = !_sessionPanel.enabled;

            if (keyboard.f1Key.wasPressedThisFrame)
            {
                _thirdPerson = !_thirdPerson;
                ApplyCameraMode();
            }
        }

        private void ApplyLook()
        {
            if (!_cursorLocked)
                return;

            var mouse = Mouse.current;
            if (mouse == null)
                return;

            // Le delta souris est déjà exprimé par image : pas de Time.deltaTime.
            var delta = mouse.delta.ReadValue() * LookSensitivity;
            transform.Rotate(0f, delta.x, 0f, Space.Self);

            _pitch = Mathf.Clamp(_pitch - delta.y, -MaxPitch, MaxPitch);
            if (_cameraPivot != null)
                _cameraPivot.localRotation = Quaternion.Euler(_pitch, 0f, 0f);
        }

        private void ApplyMove()
        {
            var keyboard = Keyboard.current;
            var input = Vector2.zero;
            var sprinting = false;

            if (keyboard != null)
            {
                // Les touches de l'Input System sont repérées par position physique :
                // wKey/aKey correspondent à Z/Q sur un clavier AZERTY.
                if (keyboard.wKey.isPressed || keyboard.upArrowKey.isPressed) input.y += 1f;
                if (keyboard.sKey.isPressed || keyboard.downArrowKey.isPressed) input.y -= 1f;
                if (keyboard.dKey.isPressed || keyboard.rightArrowKey.isPressed) input.x += 1f;
                if (keyboard.aKey.isPressed || keyboard.leftArrowKey.isPressed) input.x -= 1f;
                sprinting = keyboard.leftShiftKey.isPressed || keyboard.rightShiftKey.isPressed;
            }

            input = Vector2.ClampMagnitude(input, 1f);

            if (_controller.isGrounded && _verticalVelocity < 0f)
                _verticalVelocity = GroundedVelocity;
            _verticalVelocity += Gravity * Time.deltaTime;

            var motion = (transform.right * input.x + transform.forward * input.y) * (sprinting ? SprintSpeed : WalkSpeed);
            motion.y = _verticalVelocity;
            _controller.Move(motion * Time.deltaTime);
        }

        private void ApplyCameraMode()
        {
            if (_camera != null)
                _camera.transform.localPosition = _thirdPerson ? ThirdPersonOffset : FirstPersonOffset;

            // En vue subjective le corps masquerait l'écran : il ne garde que son ombre.
            var mode = _thirdPerson ? ShadowCastingMode.On : ShadowCastingMode.ShadowsOnly;
            foreach (var visualRenderer in _visualRenderers)
            {
                if (visualRenderer != null)
                    visualRenderer.shadowCastingMode = mode;
            }
        }

        private void SetCursorLocked(bool locked)
        {
            _cursorLocked = locked;
            Cursor.lockState = locked ? CursorLockMode.Locked : CursorLockMode.None;
            Cursor.visible = !locked;
        }

        private void OnGUI()
        {
            if (!IsOwner)
                return;

            var style = new GUIStyle(GUI.skin.label) { fontSize = 14, wordWrap = true };
            var height = 54f;
            var area = new Rect(16f, Screen.height - height - 16f, Mathf.Min(760f, Screen.width - 32f), height);
            GUILayout.BeginArea(area, GUI.skin.box);
            GUILayout.Label("ZQSD / WASD se déplacer   ·   Maj sprint   ·   Souris regarder", style);
            GUILayout.Label($"Échap curseur ({(_cursorLocked ? "capturé" : "libre")})   ·   Tab panneau réseau   ·   F1 vue {(_thirdPerson ? "3e personne" : "1re personne")}", style);
            GUILayout.EndArea();
        }
    }
}
