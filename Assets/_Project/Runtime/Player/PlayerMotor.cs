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

        // 5,5 m/s sous une gravité de 22 m/s² donnent une pointe à 0,69 m, soit la
        // moitié du gabarit : de quoi passer les gravats des couloirs sans donner
        // l'agilité qui rendrait les murs de 3 m franchissables.
        private const float JumpSpeed = 5.5f;

        // Deux tolérances qui font que marteler la touche répond au lieu d'avaler
        // des appuis : un saut reste permis juste après avoir quitté le sol, et un
        // appui juste avant l'atterrissage est rejoué à la réception.
        private const float CoyoteTime = 0.12f;
        private const float JumpBufferTime = 0.15f;

        // Durée d'appui continu pour arracher un quart de tour. Assez long pour que
        // pousser se sente comme un effort et qu'un clic perdu ne fasse pas tourner
        // un mur, assez court pour rester utilisable sous 200 ms de latence.
        private const float PushSeconds = 0.6f;

        // En dessous, la poussée est trop alignée avec le bras pour produire un
        // couple : on appuie dans l'axe du mur, il ne part d'aucun côté.
        private const float MinimumTorque = 0.2f;

        private static readonly Vector3 FirstPersonOffset = Vector3.zero;
        private static readonly Vector3 ThirdPersonOffset = new(0f, 0.55f, -3.4f);

        [SerializeField] private Transform _cameraPivot;
        [SerializeField] private Camera _camera;
        [SerializeField] private Transform _visual;

        private CharacterController _controller;
        private Renderer[] _visualRenderers = Array.Empty<Renderer>();
        private ConnectionSmokeTest _sessionPanel;
        private PivotDirector _pivotDirector;
        private PivotWall _pushedWall;
        private float _pushProgress;
        private float _pitch;
        private float _verticalVelocity;
        private float _lastGroundedAt = float.NegativeInfinity;
        private float _lastJumpPressedAt = float.NegativeInfinity;
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
            _pivotDirector = FindFirstObjectByType<PivotDirector>(FindObjectsInactive.Include);
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
            ApplyPush();
        }

        /// <summary>
        /// Clic gauche maintenu en avançant contre un bras de pivot : le mur part
        /// dans le sens où l'on appuie. Le signe du couple `r x F` autour de la
        /// verticale décide du sens, ce qui donne la règle attendue sans avoir à
        /// tester de quel côté du mur on se trouve.
        /// </summary>
        private void ApplyPush()
        {
            var mouse = Mouse.current;
            var keyboard = Keyboard.current;
            var pushing = mouse != null && mouse.leftButton.isPressed
                && keyboard != null && (keyboard.wKey.isPressed || keyboard.upArrowKey.isPressed);

            if (!pushing || _pivotDirector == null)
            {
                _pushedWall = null;
                _pushProgress = 0f;
                return;
            }

            // Le centre de la capsule, plutôt qu'une hauteur en dur : le gabarit vient
            // du CharacterController et changera avec les espèces jouables.
            var chest = transform.TransformPoint(_controller.center);
            if (!Physics.Raycast(chest, transform.forward, out var hit, PivotDirector.PushReach))
            {
                _pushedWall = null;
                _pushProgress = 0f;
                return;
            }

            var wall = hit.collider.GetComponentInParent<PivotWall>();
            if (wall == null)
            {
                _pushedWall = null;
                _pushProgress = 0f;
                return;
            }

            // Changer de mur en cours de poussée remet l'effort à zéro.
            if (wall != _pushedWall)
            {
                _pushedWall = wall;
                _pushProgress = 0f;
            }

            _pushProgress += Time.deltaTime / PushSeconds;
            if (_pushProgress < 1f)
                return;

            _pushProgress = 0f;

            var lever = hit.point - wall.transform.position;
            lever.y = 0f;
            var push = transform.forward;
            push.y = 0f;

            var torque = Vector3.Cross(lever, push).y;
            if (Mathf.Abs(torque) < MinimumTorque)
                return;

            _pivotDirector.RequestPush(wall.Index, torque > 0f);
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

                if (keyboard.spaceKey.wasPressedThisFrame)
                    _lastJumpPressedAt = Time.time;
            }

            input = Vector2.ClampMagnitude(input, 1f);

            if (_controller.isGrounded)
            {
                _lastGroundedAt = Time.time;
                if (_verticalVelocity < 0f)
                    _verticalVelocity = GroundedVelocity;
            }

            if (Time.time - _lastGroundedAt <= CoyoteTime && Time.time - _lastJumpPressedAt <= JumpBufferTime)
            {
                _verticalVelocity = JumpSpeed;

                // Consommer les deux fenêtres, sinon le même appui relancerait un saut
                // à chaque image tant qu'elles restent ouvertes.
                _lastGroundedAt = float.NegativeInfinity;
                _lastJumpPressedAt = float.NegativeInfinity;
            }

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
            var height = 76f;
            var area = new Rect(16f, Screen.height - height - 16f, Mathf.Min(760f, Screen.width - 32f), height);
            GUILayout.BeginArea(area, GUI.skin.box);
            GUILayout.Label("ZQSD / WASD se déplacer   ·   Maj sprint   ·   Espace sauter (marteler pour se décoincer)   ·   Souris regarder", style);
            GUILayout.Label($"Clic gauche maintenu + avancer contre un pivot turquoise = pousser{(_pushedWall != null ? $"  [{_pushProgress * 100f:F0} %]" : "")}", style);
            GUILayout.Label($"Échap curseur ({(_cursorLocked ? "capturé" : "libre")})   ·   Tab panneau réseau   ·   F1 vue {(_thirdPerson ? "3e personne" : "1re personne")}", style);
            GUILayout.EndArea();
        }
    }
}
