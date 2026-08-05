using System;
using FishNet.Connection;
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

        // Se dégager ne se calcule pas en repoussant le joueur hors du mur :
        // `Physics.ComputePenetration` ne résout rien contre un MeshCollider non
        // convexe, et les murs du labyrinthe en sont. On vise donc un centre de
        // cellule voisin, validé par des tests d'overlap qui, eux, fonctionnent
        // contre une géométrie concave.
        //
        // Même pas de grille que `MazePlaytestBuild` : la grille JSON ne le
        // transporte pas. S'il s'en écarte, le dégagement vise entre deux couloirs.
        private const float RespawnGridPitch = 2.75f;

        // Une à deux cellules suffisent à sortir du mur où l'on est encastré sans
        // rendre la touche téléporteuse. Le troisième anneau n'est qu'un secours
        // pour les culs-de-sac ceinturés de gravats.
        private const int RespawnNearestRing = 1;
        private const int RespawnFurthestRing = 3;

        // Le sol se cherche depuis la hauteur des yeux, pas depuis le ciel : un tir
        // parti au-dessus des murs prendrait le dessus d'un mur de 3 m pour un sol,
        // et le dégagement déposerait le joueur sur le toit du labyrinthe. Parti d'ici,
        // un tir lancé dans un mur le traverse sans accrocher — les faces arrière ne
        // sont pas testées — et retombe sur la dalle, que le test de gabarit refusera.
        private const float GroundProbeHeight = 1.5f;

        // Un sol qui s'écarte trop des pieds du joueur n'est pas le sien : la map n'a
        // qu'un niveau, l'écart ne peut venir que d'un dessus de mur ou d'un trou.
        private const float MaxGroundStep = 1.5f;

        // Le joueur est reposé légèrement au-dessus du sol touché, comme les
        // apparitions de `MazePlaytestBuild`.
        private const float RespawnGroundOffset = 0.2f;

        // On teste un gabarit un peu plus fin que le joueur : un couloir de 2,50 m
        // laisse largement la place, et cette marge évite de refuser une cellule
        // parce que la capsule frôle la plinthe d'un mur.
        private const float RespawnClearance = 0.9f;

        private const float UnstickFeedbackSeconds = 2f;

        // Amortissement du knockback reçu d'un coup de poing : l'impulsion de
        // départ (~4,5 m/s) s'éteint en une fraction de seconde.
        private const float KnockbackDecay = 10f;

        private static readonly Vector3 FirstPersonOffset = Vector3.zero;
        private static readonly Vector3 ThirdPersonOffset = new(0f, 0.55f, -3.4f);

        // Parties du modèle riggé que son porteur voit en vue subjective : sans
        // elles, un coup de poing ne produit aucun retour à l'écran. Le corps et
        // les pieds restent en ombre seule, la caméra étant à hauteur des yeux,
        // donc à l'intérieur du volume du corps qu'elle masquerait entièrement.
        // Ces noms viennent de l'export et ne servent qu'au rendu : aucune règle
        // gameplay ni aucun identifiant réseau n'en dépend (ADR 0004).
        private static readonly string[] FirstPersonVisibleParts = { "Forearm", "Fist" };

        [SerializeField] private Transform _cameraPivot;
        [SerializeField] private Camera _camera;
        [SerializeField] private Transform _visual;

        private CharacterController _controller;
        private Renderer[] _visualRenderers = Array.Empty<Renderer>();
        private bool[] _visibleInFirstPerson = Array.Empty<bool>();
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
        private Vector3 _spawnPosition;
        private Vector3 _knockback;
        private string _unstickFeedback = string.Empty;
        private float _unstickFeedbackUntil = float.NegativeInfinity;

        private void Awake()
        {
            _controller = GetComponent<CharacterController>();
            if (_visual == null)
                return;

            _visualRenderers = _visual.GetComponentsInChildren<Renderer>(true);
            _visibleInFirstPerson = new bool[_visualRenderers.Length];
            for (var i = 0; i < _visualRenderers.Length; i++)
                _visibleInFirstPerson[i] = IsFirstPersonPart(_visualRenderers[i]);
        }

        /// <summary>
        /// Vrai si ce mesh reste affiché pour son propre porteur en vue subjective.
        /// </summary>
        private static bool IsFirstPersonPart(Renderer visualRenderer)
        {
            if (visualRenderer == null)
                return false;

            foreach (var part in FirstPersonVisibleParts)
            {
                if (visualRenderer.name.IndexOf(part, StringComparison.OrdinalIgnoreCase) >= 0)
                    return true;
            }

            return false;
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

            // Dernier recours du dégagement : `MazePlaytestBuild` refuse de produire
            // la scène si une apparition n'a pas de sol, chevauche un collider ou
            // manque de dégagement. C'est le seul point dont la validité est acquise.
            _spawnPosition = transform.position;

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
        /// Replace le joueur encastré sur le centre d'une cellule voisine libre, en
        /// s'éloignant par anneaux : on prend la plus proche qui a du sol et de quoi
        /// tenir debout. Faute de quoi on retombe sur l'apparition, seul point dont
        /// la validité soit garantie par la génération de scène.
        /// </summary>
        private void ApplyUnstick()
        {
            for (var ring = RespawnNearestRing; ring <= RespawnFurthestRing; ring++)
            {
                if (!TryFindFreeCell(ring, out var target))
                    continue;

                Teleport(target);
                SetUnstickFeedback($"replacé {ring} cellule{(ring > 1 ? "s" : "")} plus loin");
                return;
            }

            Teleport(_spawnPosition);
            SetUnstickFeedback("aucune cellule libre : renvoyé à l'entrée");
        }

        /// <summary>
        /// Parcourt les cellules situées exactement à <paramref name="ring"/> cases du
        /// joueur et retient la plus proche qui soit praticable.
        /// </summary>
        private bool TryFindFreeCell(int ring, out Vector3 target)
        {
            var position = transform.position;
            var originX = SnapToCell(position.x);
            var originZ = SnapToCell(position.z);

            target = Vector3.zero;
            var bestDistance = float.PositiveInfinity;

            for (var dx = -ring; dx <= ring; dx++)
            {
                for (var dz = -ring; dz <= ring; dz++)
                {
                    // Seulement le pourtour de l'anneau : l'intérieur a déjà été testé
                    // par les tours précédents.
                    if (Mathf.Max(Mathf.Abs(dx), Mathf.Abs(dz)) != ring)
                        continue;

                    var candidate = new Vector3(
                        originX + dx * RespawnGridPitch,
                        position.y,
                        originZ + dz * RespawnGridPitch);

                    if (!TryStandAt(candidate, out var standing))
                        continue;

                    var distance = (standing - position).sqrMagnitude;
                    if (distance >= bestDistance)
                        continue;

                    bestDistance = distance;
                    target = standing;
                }
            }

            return !float.IsPositiveInfinity(bestDistance);
        }

        /// <summary>
        /// Cherche le sol sous un centre de cellule et vérifie qu'un joueur y tient.
        /// Les deux tests utilisent des requêtes d'overlap, qui fonctionnent contre les
        /// MeshCollider concaves du labyrinthe.
        /// </summary>
        private bool TryStandAt(Vector3 cellCenter, out Vector3 standing)
        {
            standing = cellCenter;

            var from = new Vector3(cellCenter.x, cellCenter.y + GroundProbeHeight, cellCenter.z);
            if (!Physics.Raycast(from, Vector3.down, out var ground, GroundProbeHeight + MaxGroundStep,
                    ~0, QueryTriggerInteraction.Ignore))
                return false;

            // Deuxième garde contre le dessus d'un mur, au cas où la cellule visée
            // porterait une marche : on ne se dégage pas vers un autre étage.
            if (Mathf.Abs(ground.point.y - cellCenter.y) > MaxGroundStep)
                return false;

            standing = ground.point + Vector3.up * RespawnGroundOffset;

            var scale = transform.lossyScale;
            var radius = _controller.radius * Mathf.Max(scale.x, scale.z) * RespawnClearance;
            var height = Mathf.Max(_controller.height * scale.y, radius * 2f);
            var center = standing + Vector3.up * (height * 0.5f);
            var half = Mathf.Max(0f, height * 0.5f - radius);

            return !Physics.CheckCapsule(
                center - Vector3.up * half, center + Vector3.up * half, radius,
                ~0, QueryTriggerInteraction.Ignore);
        }

        /// <summary>
        /// Les centres de cellule tombent sur les demi-pas de la grille : la map fait
        /// un nombre pair de cases et reste centrée sur l'origine.
        /// </summary>
        private static float SnapToCell(float value)
        {
            return (Mathf.Round(value / RespawnGridPitch - 0.5f) + 0.5f) * RespawnGridPitch;
        }

        /// <summary>
        /// Le <see cref="CharacterController"/> réécrit la position à chaque image :
        /// il faut le désactiver le temps du déplacement, sinon la téléportation est
        /// annulée dans la foulée.
        /// </summary>
        private void Teleport(Vector3 position)
        {
            _controller.enabled = false;
            transform.position = position;
            _controller.enabled = true;

            // Repartir d'une chute nulle : garder la vitesse accumulée en étant coincé
            // renverrait le joueur dans le sol.
            _verticalVelocity = GroundedVelocity;
        }

        private void SetUnstickFeedback(string message)
        {
            _unstickFeedback = message;
            _unstickFeedbackUntil = Time.time + UnstickFeedbackSeconds;

            // Tracé dans le log du joueur : c'est ce qui permet de dire après coup si
            // la touche n'a rien fait ou si elle a visé une cellule qui ne dégageait pas.
            Debug.Log($"[GAME-DEBLOCAGE] {message} — {transform.position}");
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

            if (keyboard.uKey.wasPressedThisFrame)
                ApplyUnstick();
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
            motion += _knockback;
            motion.y = _verticalVelocity;
            _controller.Move(motion * Time.deltaTime);

            _knockback = Vector3.MoveTowards(_knockback, Vector3.zero, KnockbackDecay * Time.deltaTime);
        }

        /// <summary>
        /// Distribue depuis l'hôte une impulsion au propriétaire de ce joueur.
        /// Le smoke test reste client-authoritative : l'hôte valide le coup, puis
        /// le client victime applique lui-même le déplacement temporaire.
        /// </summary>
        public void ApplyKnockbackFromServer(Vector3 velocity)
        {
            if (!IsServerStarted || !Owner.IsValid)
                return;

            // En host mode, serveur et propriétaire partagent cette instance :
            // appliquer directement évite un aller-retour TargetRpc inutile.
            if (Owner.IsLocalClient)
                ApplyKnockback(velocity);
            else
                ApplyKnockbackTargetRpc(Owner, velocity);
        }

        [TargetRpc]
        private void ApplyKnockbackTargetRpc(NetworkConnection connection, Vector3 velocity)
        {
            ApplyKnockback(velocity);
        }

        private void ApplyKnockback(Vector3 velocity)
        {
            velocity.y = 0f;
            _knockback = velocity;
        }

        private void ApplyCameraMode()
        {
            if (_camera != null)
                _camera.transform.localPosition = _thirdPerson ? ThirdPersonOffset : FirstPersonOffset;

            // En vue subjective le corps masquerait l'écran : il ne garde que son
            // ombre. Les avant-bras et les poings restent affichés, sans quoi une
            // frappe ne produirait aucun retour visible pour celui qui la donne.
            for (var i = 0; i < _visualRenderers.Length; i++)
            {
                var visualRenderer = _visualRenderers[i];
                if (visualRenderer == null)
                    continue;

                var visible = _thirdPerson || _visibleInFirstPerson[i];
                visualRenderer.shadowCastingMode = visible
                    ? ShadowCastingMode.On
                    : ShadowCastingMode.ShadowsOnly;
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
            var height = 118f;
            var area = new Rect(16f, Screen.height - height - 16f, Mathf.Min(760f, Screen.width - 32f), height);
            GUILayout.BeginArea(area, GUI.skin.box);
            GUILayout.Label("ZQSD / WASD se déplacer   ·   Maj sprint   ·   Espace sauter (marteler pour se décoincer)   ·   Souris regarder", style);
            GUILayout.Label($"Clic gauche maintenu + avancer contre un pivot turquoise = pousser{(_pushedWall != null ? $"  [{_pushProgress * 100f:F0} %]" : "")}", style);
            GUILayout.Label("Clic droit — coup de poing (joueur ou bot devant, à bout de bras)", style);
            GUILayout.Label($"Échap curseur ({(_cursorLocked ? "capturé" : "libre")})   ·   Tab panneau réseau   ·   F1 vue {(_thirdPerson ? "3e personne" : "1re personne")}", style);
            GUILayout.Label($"U se dégager d'un mur{(Time.time < _unstickFeedbackUntil ? $"   —   {_unstickFeedback}" : "")}", style);
            GUILayout.EndArea();
        }
    }
}
