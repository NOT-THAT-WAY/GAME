using System;
using FishNet.Connection;
using FishNet.Object;
using NotThatWay.Game.Input;
using NotThatWay.Game.PlayerSimulation;
using UnityEngine;
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
    [RequireComponent(typeof(PlayerInputSource))]
    public sealed class PlayerMotor : NetworkBehaviour
    {
        private const float WalkSpeed = 4.2f;
        private const float SprintSpeed = 7.0f;
        private const float Gravity = -22f;
        private const float GroundedVelocity = -3f;
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

        // Poussée d'un mur mobile : on doit être dessus, pas à bout de bras. L'hôte
        // mesure l'effort ; le client se contente de répéter son intention assez
        // souvent pour que l'hôte sache qu'on pousse encore.
        private const float WallPushReach = 1.2f;
        private const float WallPushIntentInterval = 0.1f;

        // Portée du seul retour d'écran : elle couvre le bout du poing, pour voir
        // l'effort monter en martelant un mur sans marcher dedans.
        private const float WallFeedbackReach = 2f;

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
        private PlayerInputSource _inputSource;
        private Renderer[] _visualRenderers = Array.Empty<Renderer>();
        private bool[] _visibleInFirstPerson = Array.Empty<bool>();
        private ConnectionSmokeTest _sessionPanel;
        private PivotDirector _pivotDirector;
        private PivotWall _pushedWall;
        private float _pushProgress;
        private MovableWallDirector _wallDirector;
        private MovableWall _pushedMovableWall;
        private float _nextWallPushIntentAt;
        private float _pitch;
        private float _verticalVelocity;
        private float _lastGroundedAt = float.NegativeInfinity;
        private float _lastJumpPressedAt = float.NegativeInfinity;
        private bool _thirdPerson;
        private bool _cursorLocked;
        private bool _humanSmokeTest;
        private bool _smokeLookLogged;
        private bool _smokeMovementLogged;
        private bool _smokeJumpLogged;
        private Vector3 _spawnPosition;
        private Vector3 _knockback;
        private string _unstickFeedback = string.Empty;
        private float _unstickFeedbackUntil = float.NegativeInfinity;

        private void Awake()
        {
            _humanSmokeTest = HumanSmokeTestMode.IsEnabled;
            _controller = GetComponent<CharacterController>();
            _inputSource = GetComponent<PlayerInputSource>();
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
            if (_inputSource != null)
                _inputSource.enabled = IsOwner;
            if (!IsOwner)
                return;

            var spectator = FindFirstObjectByType<SpectatorCamera>(FindObjectsInactive.Exclude);
            if (spectator != null)
                spectator.gameObject.SetActive(false);

            _sessionPanel = FindFirstObjectByType<ConnectionSmokeTest>(FindObjectsInactive.Include);
            if (_humanSmokeTest)
            {
                if (_sessionPanel != null)
                    _sessionPanel.enabled = false;

                var panelState = _sessionPanel != null ? "hidden" : "absent";
                HumanSmokeTestMode.LogEvent("ready", $"network_panel={panelState} gameplay=unchanged");
            }
            _pivotDirector = FindFirstObjectByType<PivotDirector>(FindObjectsInactive.Include);
            _wallDirector = FindFirstObjectByType<MovableWallDirector>(FindObjectsInactive.Include);
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
            if (_inputSource != null)
                _inputSource.enabled = false;
            if (IsOwner)
                SetCursorLocked(false);
        }

        public override void OnOwnershipClient(NetworkConnection previousOwner)
        {
            base.OnOwnershipClient(previousOwner);
            if (_inputSource != null)
            {
                _inputSource.ResetBufferedInput();
                _inputSource.enabled = IsOwner;
            }
            if (!IsOwner)
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
            ApplyWallPush();
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
        /// Avancer contre un mur mobile, l'épaule dedans : l'hôte accumule l'effort
        /// et le mur finit par céder d'un quart de tour. Pas de bouton — marcher
        /// dedans suffit, comme on force une porte lourde.
        ///
        /// Le client ne fait que répéter son intention. Il ne décide ni de la durée
        /// de l'effort, ni du gond, ni du sens, ni du moment où le mur bascule : tout
        /// ça appartient à <see cref="MovableWallDirector"/>, côté hôte.
        /// </summary>
        private void ApplyWallPush()
        {
            if (_wallDirector == null)
                _wallDirector = FindFirstObjectByType<MovableWallDirector>(FindObjectsInactive.Include);

            if (_wallDirector == null)
            {
                _pushedMovableWall = null;
                return;
            }

            // Le rayon part plus loin que le contact à l'épaule : il sert aussi à
            // afficher l'effort du mur qu'on est en train de marteler sans avancer.
            var chest = transform.TransformPoint(_controller.center);
            if (!Physics.Raycast(chest, transform.forward, out var hit, WallFeedbackReach, ~0, QueryTriggerInteraction.Ignore))
            {
                _pushedMovableWall = null;
                return;
            }

            _pushedMovableWall = hit.collider.GetComponentInParent<MovableWall>();
            if (_pushedMovableWall == null || hit.distance > WallPushReach)
                return;

            HumanSmokeTestMode.LogEventOnce(
                "wall_contact_local",
                "wall_contact",
                $"id={_pushedMovableWall.Id} distance={hit.distance:F2}");

            if (_inputSource == null || _inputSource.CurrentFrame.MoveY <= 0.5f)
                return;

            if (Time.time < _nextWallPushIntentAt)
                return;

            _nextWallPushIntentAt = Time.time + WallPushIntentInterval;
            HumanSmokeTestMode.LogEventOnce(
                "wall_request_local",
                "wall_request",
                $"id={_pushedMovableWall.Id}");
            _wallDirector.RequestWallPush(_pushedMovableWall.Id);
        }

        /// <summary>
        /// Clic gauche maintenu en avançant contre un bras de pivot : le mur part
        /// dans le sens où l'on appuie. Le signe du couple `r x F` autour de la
        /// verticale décide du sens, ce qui donne la règle attendue sans avoir à
        /// tester de quel côté du mur on se trouve.
        /// </summary>
        private void ApplyPush()
        {
            var frame = _inputSource != null ? _inputSource.CurrentFrame : default;
            var pushing = (frame.HeldButtons & PlayerCommandButtons.InteractHeld) != 0 &&
                frame.MoveY > 0.5f;

            if (pushing)
                HumanSmokeTestMode.LogEventOnce("pivot_input_local", "pivot_input");

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
                HumanSmokeTestMode.LogEventOnce(
                    "pivot_target_miss_no_hit",
                    "pivot_target_miss",
                    "reason=no_collider_in_reach");
                _pushedWall = null;
                _pushProgress = 0f;
                return;
            }

            var wall = hit.collider.GetComponentInParent<PivotWall>();
            if (wall == null)
            {
                HumanSmokeTestMode.LogEventOnce(
                    "pivot_target_miss_wrong_collider",
                    "pivot_target_miss",
                    $"reason=wrong_collider name={hit.collider.name}");
                _pushedWall = null;
                _pushProgress = 0f;
                return;
            }

            HumanSmokeTestMode.LogEventOnce(
                "pivot_contact_local",
                "pivot_contact",
                $"index={wall.Index} distance={hit.distance:F2}");

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
            {
                HumanSmokeTestMode.LogEventOnce(
                    "pivot_low_torque_local",
                    "pivot_rejected_local",
                    $"reason=low_torque value={torque:F2}");
                return;
            }

            HumanSmokeTestMode.LogEventOnce(
                "pivot_request_local",
                "pivot_request",
                $"index={wall.Index} torque={torque:F2}");
            _pivotDirector.RequestPush(wall.Index, torque > 0f);
        }

        private void ReadToggles()
        {
            if (_inputSource == null)
                return;

            if (_inputSource.PausePressedThisFrame)
                SetCursorLocked(!_cursorLocked);
        }

        private void ApplyLook()
        {
            if (!_cursorLocked)
                return;

            if (_inputSource == null)
                return;

            var frame = _inputSource.CurrentFrame;
            var delta = new Vector2(frame.LookYawDegrees, frame.LookPitchDegrees);
            if (!_smokeLookLogged && delta.sqrMagnitude > 0.0001f)
            {
                _smokeLookLogged = true;
                HumanSmokeTestMode.LogEvent("look");
            }
            transform.Rotate(0f, delta.x, 0f, Space.Self);

            _pitch = Mathf.Clamp(_pitch - delta.y, -MaxPitch, MaxPitch);
            if (_cameraPivot != null)
                _cameraPivot.localRotation = Quaternion.Euler(_pitch, 0f, 0f);
        }

        private void ApplyMove()
        {
            var frame = _inputSource != null ? _inputSource.CurrentFrame : default;
            var input = new Vector2(frame.MoveX, frame.MoveY);
            var sprinting = (frame.HeldButtons & PlayerCommandButtons.SprintHeld) != 0;
            if ((frame.PressedButtons & PlayerCommandButtons.JumpPressed) != 0)
                _lastJumpPressedAt = Time.time;

            input = Vector2.ClampMagnitude(input, 1f);
            if (!_smokeMovementLogged && input.sqrMagnitude > 0.01f)
            {
                _smokeMovementLogged = true;
                HumanSmokeTestMode.LogEvent("movement");
            }

            if (_controller.isGrounded)
            {
                _lastGroundedAt = Time.time;
                if (_verticalVelocity < 0f)
                    _verticalVelocity = GroundedVelocity;
            }

            if (Time.time - _lastGroundedAt <= CoyoteTime && Time.time - _lastJumpPressedAt <= JumpBufferTime)
            {
                _verticalVelocity = JumpSpeed;
                if (!_smokeJumpLogged)
                {
                    _smokeJumpLogged = true;
                    HumanSmokeTestMode.LogEvent("jump");
                }

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
            if (_humanSmokeTest)
            {
                DrawHumanSmokeTestHud(style);
                return;
            }

            var height = 118f;
            var area = new Rect(16f, Screen.height - height - 16f, Mathf.Min(760f, Screen.width - 32f), height);
            GUILayout.BeginArea(area, GUI.skin.box);
            GUILayout.Label("ZQSD / WASD / stick se déplacer   ·   Maj / stick press sprint   ·   Espace / A sauter   ·   Souris / stick regarder", style);
            GUILayout.Label($"Clic gauche / E / gâchette + avancer contre un pivot = pousser{(_pushedWall != null ? $"  [{_pushProgress * 100f:F0} %]" : "")}", style);
            var wallEffort = _pushedMovableWall != null && _wallDirector != null
                ? $"  [{_wallDirector.EffortFor(_pushedMovableWall.Id) * 100f:F0} %]"
                : "";
            GUILayout.Label($"Avancer contre un mur = le pousser{wallEffort}   ·   clic droit / F / épaule droite = coup de poing", style);
            GUILayout.Label($"Échap / Menu : curseur ({(_cursorLocked ? "capturé" : "libre")})", style);
            GUILayout.EndArea();
        }

        private void DrawHumanSmokeTestHud(GUIStyle style)
        {
            var wallEffort = _pushedMovableWall != null && _wallDirector != null
                ? _wallDirector.EffortFor(_pushedMovableWall.Id)
                : 0f;
            var hasEffort = _pushedWall != null || wallEffort > 0f;
            var height = hasEffort ? 116f : 94f;
            var area = new Rect(16f, Screen.height - height - 16f, Mathf.Min(760f, Screen.width - 32f), height);

            GUILayout.BeginArea(area, GUI.skin.box);
            GUILayout.Label("SMOKE TEST : déplacement · pivot · mur mobile · punch bot", style);
            GUILayout.Label("ZQSD / WASD / stick : bouger   ·   Souris / stick : regarder   ·   Espace / A : sauter", style);
            GUILayout.Label("Pivot : Interagir + avancer   ·   Mur : avancer ou Punch   ·   Échap / Menu : curseur", style);

            if (_pushedWall != null)
                GUILayout.Label($"Le pivot résiste… effort {_pushProgress * 100f:F0} %", style);
            else if (wallEffort > 0f)
                GUILayout.Label($"Le mur résiste… effort {wallEffort * 100f:F0} %", style);

            GUILayout.EndArea();
        }
    }
}
