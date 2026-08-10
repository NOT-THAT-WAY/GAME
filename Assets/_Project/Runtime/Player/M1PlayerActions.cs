using FishNet.Object;
using FishNet.Transporting;
using FishNet.Utility.Template;
using NotThatWay.Game.Input;
using NotThatWay.Game.PlayerSimulation;
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
        public const uint WallImpulseTicks = 40u;
        public const int ChainedPunchesToOpen = 3;
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
        private static readonly int PushBool = Animator.StringToHash("Push");

        [Header("Frappe — validée par l'hôte")]
        [SerializeField, Min(1)] private uint _punchCooldownTicks = M1PunchTuning.CooldownTicks;
        [SerializeField, Min(0f)] private float _punchRangeMeters = 2f;
        [SerializeField, Min(0f)] private float _punchHalfAngleDegrees = 30f;
        [SerializeField, Min(0f)] private float _knockbackSpeed = 4.5f;
        [SerializeField, Min(0f)] private float _chestHeightMeters = 0.7f;

        private PredictedPlayerMotor _motor;
        private PlayerInputSource _inputSource;
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
                PlayPunchAnimation();

            var pushing = (frame.HeldButtons & PlayerCommandButtons.InteractHeld) != 0;
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

            var victim = FindVictim();
            if (victim != null)
            {
                victim.ApplyKnockbackFromServer(direction * _knockbackSpeed);
                Debug.Log(
                    $"[GAME-M1-PUNCH] hit source={ObjectId} target={victim.ObjectId} " +
                    $"tick={TimeManager.Tick}.");
                return;
            }

            TryPunchWall(direction);
        }

        private PredictedPlayerMotor FindVictim()
        {
            PredictedPlayerMotor best = null;
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
                best = candidate;
            }

            return best;
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

        private void PlayPunchAnimation()
        {
            if (_animator != null && _animator.runtimeAnimatorController != null)
                _animator.SetTrigger(PunchTrigger);
        }

        private void ApplyPushPose(bool pushing)
        {
            if (_animator != null && _animator.runtimeAnimatorController != null)
                _animator.SetBool(PushBool, pushing);
        }

        /// <summary>
        /// Retour local du pousseur. Il ne donne aucune consigne de test : il
        /// affiche seulement l'effort observé pendant l'action et rejoue la règle
        /// pure sur la position locale. L'hôte reste seul à décider.
        /// </summary>
        private void OnGUI()
        {
            if (!IsOwner || !TryDescribePush(out var label, out var progress))
                return;

            const float width = 340f;
            const float height = 54f;
            var area = new Rect(
                (Screen.width - width) * 0.5f,
                Screen.height - height - 24f,
                width,
                height);
            GUILayout.BeginArea(area, GUI.skin.box);
            GUILayout.Label(label);
            var bar = GUILayoutUtility.GetRect(width - 16f, 12f);
            GUI.Box(bar, GUIContent.none);
            if (progress > 0f)
            {
                GUI.Box(
                    new Rect(bar.x, bar.y, bar.width * Mathf.Clamp01(progress), bar.height),
                    GUIContent.none);
            }

            GUILayout.EndArea();
        }

        private bool TryDescribePush(out string label, out float progress)
        {
            label = null;
            progress = 0f;
            if (_wallDirector == null)
                _wallDirector = FindFirstObjectByType<M1AuthoritativeWallDirector>();
            if (_arena == null)
                _arena = FindFirstObjectByType<TopologyArena>();
            if (_wallDirector == null || _arena == null || _arena.Map == null)
                return false;

            var threshold = _wallDirector.EffortThreshold;
            if (threshold <= 0 || !_pushing)
                return false;
            var state = _wallDirector.ObservedState;
            if (state.IsTransitioning)
            {
                label = "MUR — en mouvement";
                progress = 1f;
                return true;
            }

            var local = _arena.transform.InverseTransformPoint(transform.position);
            var controller = _motor.CharacterController;
            var scale = transform.lossyScale;
            var radius = controller == null
                ? 0.4f
                : controller.radius * Mathf.Max(Mathf.Abs(scale.x), Mathf.Abs(scale.z));
            var decision = M1WallInteractionRules.Evaluate(
                _arena.Map,
                _wallDirector.WallId,
                state.StateId,
                Millimeters(local.x),
                Millimeters(local.z),
                Mathf.CeilToInt(radius * 1000f) + 1,
                _wallDirector.ReachFromCapsuleMm);
            if (!decision.Allowed)
                return false;

            var towardOther = state.StateId == _wallDirector.NegativeStateId ? 1 : -1;
            progress = Mathf.Abs(state.SignedEffort) / (float)threshold;
            label = decision.EffortSign == towardOther
                ? $"MUR — poussée {progress * 100f:F0} %"
                : "MUR — effort opposé";
            return true;
        }

        private static int Millimeters(float meters) =>
            Mathf.RoundToInt(meters * 1000f);
    }
}
