using FishNet.Object;
using FishNet.Transporting;
using FishNet.Utility.Template;
using NotThatWay.Game.Input;
using NotThatWay.Game.PlayerSimulation;
using NotThatWay.Game.Sandbox;
using NotThatWay.Game.Simulation;
using NotThatWay.Game.Topology;
using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Contrat partagé entre la résolution du coup et l'impulsion murale. Les
    /// valeurs restent en ticks pour être identiques sur l'hôte et dans les tests
    /// du modèle, indépendamment du framerate d'affichage.
    /// </summary>
    internal static class M1PunchTuning
    {
        public const uint CooldownTicks = 48u;

        /// <summary>
        /// Un coup verse son couple pendant cette fenêtre de ticks. Avec
        /// <see cref="PunchTorqueScalePermille"/> = 1000 (atténuation neutre) et
        /// le battant réglé à 400 mdeg/tick, un coup au bout du battant (levier
        /// plein, 1000‰) vaut 45 × 400 = 18 000 mdeg = 18°, soit un cinquième de
        /// tour (90° / 5) : demande explicite du testeur pour qu'une vingtaine de
        /// coups fassent un tour complet, après que le premier réglage (3°) a été
        /// jugé trop faible. Au gond (levier plancher 400‰), le même coup vaut
        /// 45 × 160 = 7 200 mdeg = 7,2°. La fenêtre reste sous
        /// <see cref="CooldownTicks"/> (marge de 3 ticks) : deux impulsions d'une
        /// même source ne se chevauchent jamais, voir
        /// <c>M1AuthoritativeWallDirector.TryRegisterPunchImpulse</c> et
        /// <c>M1PunchTorqueTests</c>.
        /// </summary>
        public const uint WallImpulseTicks = 45u;

        /// <summary>
        /// Facteur d'atténuation du levier d'un coup par rapport à un appui
        /// continu. Remonté de 500 à 1000 (atténuation neutre) : demande
        /// explicite du testeur après avoir jugé le premier réglage (3° par coup)
        /// trop timide. La constante et son point d'application
        /// (<c>ScalePunchLeverage</c>, appliqué serveur dans
        /// <c>M1AuthoritativeWallDirector.TryRegisterPunchImpulse</c>) restent en
        /// place même neutralisés : c'est le bouton de réglage si le ressenti
        /// change encore.
        /// </summary>
        public const int PunchTorqueScalePermille = 1000;
    }

    /// <summary>
    /// Réglage du retour tactile d'une poussée contre le battant : « appuyer
    /// contre une porte lourde doit repousser un peu ». Le déplacement d'un
    /// rebond est exprimé en pour-mille du déplacement que produit un coup de
    /// poing plutôt qu'en mètres par seconde codés en dur, pour que la relation
    /// quadratique entre vitesse et déplacement reste visible dans le réglage.
    /// </summary>
    internal static class M1WallBounceTuning
    {
        /// <summary>
        /// Référence de calcul, alignée sur le champ <c>_knockbackSpeed</c> de
        /// <see cref="M1PlayerActions"/> (4,5 m/s). Avec la décélération par
        /// défaut de <c>PredictedPlayerMotor._knockbackDecay</c> (10 m/s²), un
        /// coup de poing déplace le joueur de v² / (2a) = 4,5² / 20 ≈ 1,01 m.
        /// </summary>
        public const float PunchKnockbackSpeedMetersPerSecond = 4.5f;

        /// <summary>
        /// Déplacement du rebond, en pour-mille du déplacement d'un coup de
        /// poing. 100 = 10 %.
        /// </summary>
        public const int WallBounceDisplacementPermille = 100;

        /// <summary>
        /// Dérive la vitesse de rebond depuis un déplacement cible. Le
        /// déplacement varie comme le carré de la vitesse (v² / (2a)), donc
        /// atteindre une fraction <paramref name="displacementPermille"/> / 1000
        /// du déplacement d'un coup de poing exige un facteur
        /// sqrt(displacementPermille / 1000) sur la vitesse de référence — pas
        /// une simple règle de trois — pour que doubler le pour-mille double
        /// bien le déplacement plutôt que la vitesse.
        /// </summary>
        public static float Speed(int displacementPermille) =>
            PunchKnockbackSpeedMetersPerSecond *
            Mathf.Sqrt(displacementPermille / (float)WallSimulationSettings.PermilleScale);
    }

    internal static class M1PunchTargeting
    {
        public static bool TryResolveWallCollider(
            Collider collider,
            int expectedWallId,
            out TopologyWallView wall)
        {
            wall = collider == null
                ? null
                : collider.GetComponentInParent<TopologyWallView>();
            return wall != null && wall.WallId == expectedWallId;
        }
    }

    /// <summary>
    /// Coup de poing et pose de poussée du banc M1. Le client n'envoie qu'une
    /// intention : l'appui voyage déjà dans la commande répliquée, et l'hôte
    /// décide seul du cooldown, de la cible, de la portée et de l'effet. Les
    /// animations, elles, restent cosmétiques et n'ouvrent aucune règle.
    /// </summary>
    [DisallowMultipleComponent]
    [RequireComponent(typeof(PredictedPlayerMotor))]
    [RequireComponent(typeof(PlayerInputSource))]
    public sealed class M1PlayerActions : TickNetworkBehaviour
    {
        private static readonly int PunchTrigger = Animator.StringToHash("Punch");
        private static readonly int ThrowTrigger = Animator.StringToHash("Throw");
        private static readonly int PushBool = Animator.StringToHash("Push");

        [Header("Frappe — validée par l'hôte")]
        [SerializeField, Min(1)] private uint _punchCooldownTicks = M1PunchTuning.CooldownTicks;
        [SerializeField, Min(0f)] private float _punchRangeMeters = 2f;
        [SerializeField, Min(0f)] private float _punchHalfAngleDegrees = 30f;
        // Garder synchronisé avec M1WallBounceTuning.PunchKnockbackSpeedMetersPerSecond :
        // le rebond de contact dérive son déplacement de celui d'un coup de poing.
        [SerializeField, Min(0f)] private float _knockbackSpeed = 4.5f;
        [SerializeField, Min(0f)] private float _chestHeightMeters = 0.7f;

        private PredictedPlayerMotor _motor;
        private PlayerInputSource _inputSource;
        private SandboxPlayerGameplay _sandboxGameplay;
        private Animator _animator;
        private M1AuthoritativeWallDirector _wallDirector;
        private TopologyArena _arena;
        private uint _lastPunchTick;
        private bool _hasPunched;
        private uint _lastResolvedCommandTick;
        private bool _hasResolvedCommand;
        private bool _pushing;

        private void Awake()
        {
            _motor = GetComponent<PredictedPlayerMotor>();
            _inputSource = GetComponent<PlayerInputSource>();
            _sandboxGameplay = GetComponent<SandboxPlayerGameplay>();
            _animator = GetComponentInChildren<Animator>(true);
            SetTickCallbacks(TickCallback.PostTick);
        }

        private void Update()
        {
            if (!IsOwner || _inputSource == null)
                return;

            var frame = _inputSource.CurrentFrame;

            // Retour immédiat chez le frappeur : l'hôte tranchera l'effet, mais le
            // bras ne doit pas attendre l'aller-retour réseau pour partir.
            if ((frame.PressedButtons & PlayerCommandButtons.PunchPressed) != 0)
            {
                if (_sandboxGameplay == null)
                {
                    PlayPunchAnimation();
                }
                else if (_sandboxGameplay.CanThrow || _sandboxGameplay.CanFireSlingshot)
                {
                    PlayThrowAnimation();
                }
                else if (_sandboxGameplay.CanPunch)
                {
                    PlayPunchAnimation();
                }
            }

            var pushing = (frame.HeldButtons & PlayerCommandButtons.InteractHeld) != 0 &&
                          (_sandboxGameplay == null || _sandboxGameplay.CanPush);
            if (pushing == _pushing)
                return;
            _pushing = pushing;
            ApplyPushPose(pushing);
            SetPushPoseServerRpc(pushing);
        }

        protected override void TimeManager_OnPostTick()
        {
            if (!IsServerStarted || _motor == null)
                return;
            if (!_motor.TryGetLatestAuthoritativeCommand(out var command))
                return;
            if (_hasResolvedCommand && command.Tick == _lastResolvedCommandTick)
                return;

            _lastResolvedCommandTick = command.Tick;
            _hasResolvedCommand = true;
            if ((command.Buttons & PlayerCommandButtons.PunchPressed) == 0)
                return;

            var serverTick = TimeManager.Tick;
            if (_hasPunched && TickMath.Elapsed(_lastPunchTick, serverTick) < _punchCooldownTicks)
                return;

            var direction = transform.forward;
            direction.y = 0f;
            if (_sandboxGameplay != null &&
                _sandboxGameplay.ActiveKind == SandboxCarryableKind.Slingshot)
            {
                if (!_sandboxGameplay.TryFireSlingshot(command, direction))
                    return;
                _lastPunchTick = serverTick;
                _hasPunched = true;
                PlayThrowObserversRpc();
                return;
            }
            if (_sandboxGameplay != null &&
                _sandboxGameplay.ActiveKind != SandboxCarryableKind.None)
            {
                if (!_sandboxGameplay.TryThrowActive(command, direction))
                    return;
                _lastPunchTick = serverTick;
                _hasPunched = true;
                PlayThrowObserversRpc();
                return;
            }

            if (_sandboxGameplay != null && !_sandboxGameplay.TrySpendPunch(command))
                return;
            _lastPunchTick = serverTick;
            _hasPunched = true;
            ResolvePunch();
        }

        /// <summary>
        /// Cible la plus proche dans le cône, sinon le mur mobile devant le poing.
        /// Portée, angle et ligne de vue sont mesurés sur la copie serveur.
        /// </summary>
        private void ResolvePunch()
        {
            PlayPunchObserversRpc();

            var direction = transform.forward;
            direction.y = 0f;
            if (direction.sqrMagnitude < 0.0001f)
                return;
            direction.Normalize();

            FindVictim(out var victimPlayer, out var victimBot);
            if (victimPlayer != null)
            {
                var victimGameplay = victimPlayer.GetComponent<SandboxPlayerGameplay>();
                if (victimGameplay != null)
                {
                    if (!victimGameplay.ApplyDamageFromServer(
                            SandboxGameplayConfig.Baseline60Hz.PunchDamage,
                            SandboxDamageKind.Punch,
                            direction * _knockbackSpeed))
                    {
                        return;
                    }
                }
                else
                {
                    victimPlayer.ApplyKnockbackFromServer(direction * _knockbackSpeed);
                }
                Debug.Log(
                    $"[GAME-M1-PUNCH] hit source={ObjectId} target={victimPlayer.ObjectId} " +
                    $"tick={TimeManager.Tick}.");
                return;
            }

            if (victimBot != null)
            {
                if (!victimBot.ApplyDamageFromServer(
                        SandboxGameplayConfig.Baseline60Hz.PunchDamage,
                        direction * _knockbackSpeed))
                {
                    return;
                }
                Debug.Log(
                    $"[GAME-M1-PUNCH] hit source={ObjectId} bot={victimBot.ObjectId} " +
                    $"health={victimBot.Health} tick={TimeManager.Tick}.");
                return;
            }

            TryPunchWall(direction);
        }

        private void FindVictim(
            out PredictedPlayerMotor victimPlayer,
            out SimpleBot victimBot)
        {
            victimPlayer = null;
            victimBot = null;
            var bestDistance = float.PositiveInfinity;
            var origin = transform.position;
            var forward = transform.forward;

            foreach (var candidate in FindObjectsByType<PredictedPlayerMotor>(FindObjectsSortMode.None))
            {
                if (candidate == _motor || candidate == null)
                    continue;

                var offset = candidate.transform.position - origin;
                offset.y = 0f;
                var distance = offset.magnitude;
                if (distance > _punchRangeMeters || distance >= bestDistance)
                    continue;
                if (distance > 0.01f &&
                    Vector3.Angle(forward, offset) > _punchHalfAngleDegrees)
                {
                    continue;
                }
                if (!HasLineOfSight(candidate.transform))
                    continue;

                bestDistance = distance;
                victimPlayer = candidate;
                victimBot = null;
            }

            foreach (var candidate in FindObjectsByType<SimpleBot>(FindObjectsSortMode.None))
            {
                if (candidate == null || !candidate.CanBeHit)
                    continue;

                var offset = candidate.transform.position - origin;
                offset.y = 0f;
                var distance = offset.magnitude;
                if (distance > _punchRangeMeters || distance >= bestDistance)
                    continue;
                if (distance > 0.01f &&
                    Vector3.Angle(forward, offset) > _punchHalfAngleDegrees)
                {
                    continue;
                }
                if (!HasLineOfSight(candidate.transform))
                    continue;

                bestDistance = distance;
                victimPlayer = null;
                victimBot = candidate;
            }
        }

        private bool HasLineOfSight(Transform target)
        {
            var start = transform.position + Vector3.up * _chestHeightMeters;
            var end = target.position + Vector3.up * _chestHeightMeters;
            if (!Physics.Linecast(start, end, out var hit, ~0, QueryTriggerInteraction.Ignore))
                return true;
            return hit.transform == target || hit.transform.IsChildOf(target);
        }

        /// <summary>
        /// Un coup dans le vide verse sa part d'effort seulement si le rayon du
        /// poing serveur touche le mur mobile. L'hôte résout donc cible, portée,
        /// ligne de vue, côté et sens sans accepter de wallId fourni par le client.
        /// </summary>
        private void TryPunchWall(Vector3 direction)
        {
            if (_wallDirector == null)
                _wallDirector = FindFirstObjectByType<M1AuthoritativeWallDirector>();
            if (_wallDirector == null)
                return;

            var origin = transform.position + Vector3.up * _chestHeightMeters;
            var worldMask = 1 << GameplayLayers.World;
            if (!Physics.Raycast(
                    origin,
                    direction,
                    out var hit,
                    _punchRangeMeters,
                    worldMask,
                    QueryTriggerInteraction.Ignore))
            {
                return;
            }

            if (!M1PunchTargeting.TryResolveWallCollider(
                    hit.collider,
                    _wallDirector.WallId,
                    out var wall))
                return;

            var controller = _motor.CharacterController;
            var scale = transform.lossyScale;
            var radius = controller == null
                ? 0.4f
                : controller.radius * Mathf.Max(Mathf.Abs(scale.x), Mathf.Abs(scale.z));
            if (_wallDirector.TryRegisterPunchImpulse(ObjectId, transform.position, radius))
            {
                Debug.Log(
                    $"[GAME-M1-PUNCH] wall_impulse source={ObjectId} wall={wall.WallId} " +
                    $"tick={TimeManager.Tick}.");
            }
        }

        [ServerRpc]
        private void SetPushPoseServerRpc(bool pushing)
        {
            if (_sandboxGameplay != null && !_sandboxGameplay.CanPush)
                pushing = false;
            SetPushPoseObserversRpc(pushing);
        }

        [ObserversRpc(ExcludeOwner = true, BufferLast = true)]
        private void SetPushPoseObserversRpc(bool pushing)
        {
            ApplyPushPose(pushing);
        }

        [ObserversRpc(ExcludeOwner = true)]
        private void PlayPunchObserversRpc()
        {
            PlayPunchAnimation();
        }

        [ObserversRpc(ExcludeOwner = true)]
        private void PlayThrowObserversRpc()
        {
            PlayThrowAnimation();
        }

        private void PlayPunchAnimation()
        {
            if (_animator != null && _animator.runtimeAnimatorController != null)
                _animator.SetTrigger(PunchTrigger);
        }

        private void PlayThrowAnimation()
        {
            if (_animator != null && _animator.runtimeAnimatorController != null)
                _animator.SetTrigger(ThrowTrigger);
        }

        private void ApplyPushPose(bool pushing)
        {
            if (_animator != null && _animator.runtimeAnimatorController != null)
                _animator.SetBool(PushBool, pushing);
        }

        /// <summary>
        /// Retour local du pousseur. Sans lui, le bras de levier est invisible : un
        /// joueur collé au gond conclut que la touche ne répond pas alors qu'il
        /// applique 40 % de la puissance. L'indicateur rejoue la règle pure sur la
        /// position locale et lit l'angle de l'état observé ; il ne décide rien.
        /// </summary>
        private void OnGUI()
        {
            if (!IsOwner || !TryDescribeWall(out var headline, out var status, out var leverage))
                return;

            const float width = 380f;
            const float height = 74f;
            var area = new Rect(
                (Screen.width - width) * 0.5f,
                Screen.height - height - 24f,
                width,
                height);
            GUILayout.BeginArea(area, GUI.skin.box);
            GUILayout.Label(headline);
            var bar = GUILayoutUtility.GetRect(width - 16f, 12f);
            GUI.Box(bar, GUIContent.none);
            if (leverage > 0f)
            {
                GUI.Box(
                    new Rect(bar.x, bar.y, bar.width * Mathf.Clamp01(leverage), bar.height),
                    GUIContent.none);
            }
            GUILayout.Label(status);
            GUILayout.EndArea();
        }

        private bool TryDescribeWall(out string headline, out string status, out float leverage)
        {
            headline = null;
            status = null;
            leverage = 0f;
            if (_wallDirector == null)
                _wallDirector = FindFirstObjectByType<M1AuthoritativeWallDirector>();
            if (_arena == null)
                _arena = FindFirstObjectByType<TopologyArena>();
            if (_wallDirector == null || _arena == null || _arena.Map == null)
                return false;

            var state = _wallDirector.ObservedState;
            if (state.WallId == 0)
                return false;

            var local = _arena.transform.InverseTransformPoint(transform.position);
            var controller = _motor.CharacterController;
            var scale = transform.lossyScale;
            var radius = controller == null
                ? 0.4f
                : controller.radius * Mathf.Max(Mathf.Abs(scale.x), Mathf.Abs(scale.z));
            var decision = M1WallInteractionRules.Evaluate(
                _arena.Map,
                _wallDirector.WallId,
                state.AngleMilliDegrees,
                Millimeters(local.x),
                Millimeters(local.z),
                Mathf.CeilToInt(radius * 1000f) + 1,
                _wallDirector.ReachFromCapsuleMm,
                _wallDirector.MinimumLeveragePermille);
            if (!decision.Allowed)
                return false;

            leverage = decision.LeveragePermille / (float)WallSimulationSettings.PermilleScale;
            headline = $"MUR — levier {leverage * 100f:F0} %";

            var velocity = state.AngularVelocityMilliDegreesPerTick;
            if (velocity == 0)
            {
                status = _pushing
                    ? "bloqué — quelqu'un pousse aussi fort en face"
                    : decision.ContactPermille < 500
                        ? "MAINTENIR E — plus loin du gond, plus de force"
                        : "MAINTENIR E — le mur s'écarte de vous";
                return true;
            }

            var degreesPerSecond = Mathf.Abs(velocity) * TimeManager.TickRate / 1000f;
            status = Mathf.Sign(velocity) == decision.Direction
                ? $"{degreesPerSecond:F0} °/s — il s'écarte de vous"
                : $"{degreesPerSecond:F0} °/s — il revient sur vous";
            return true;
        }

        private static int Millimeters(float meters) =>
            Mathf.RoundToInt(meters * 1000f);
    }
}
