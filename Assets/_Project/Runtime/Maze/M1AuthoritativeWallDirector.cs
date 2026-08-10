using System;
using System.Collections.Generic;
using FishNet.Connection;
using FishNet;
using FishNet.Managing.Predicting;
using FishNet.Managing.Timing;
using FishNet.Object;
using FishNet.Transporting;
using FishNet.Utility.Template;
using NotThatWay.Game.PlayerSimulation;
using NotThatWay.Game.Simulation;
using NotThatWay.Game.Topology;
using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Adaptateur WALL-01 du banc M1. Le serveur dérive cible, côté, portée et
    /// occupation depuis ses propres joueurs, avance la machine pure, puis diffuse
    /// un snapshot autonome. Aucun transform ni wallId ne vient d'un client.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class M1AuthoritativeWallDirector : TickNetworkBehaviour
    {
        private const byte SnapshotSchemaVersion = 2;

        [Header("Mur canonique M1")]
        [SerializeField] private int _wallId = 10;
        [SerializeField, Min(1)] private int _effortThreshold = 120;
        [SerializeField, Min(1)] private int _maximumEffortPerSourcePerTick = 4;
        [SerializeField, Min(0)] private int _effortDecayPerTick = 2;
        [SerializeField, Min(0)] private int _rejectedEffortRetention;
        [SerializeField, Min(1)] private uint _transitionDurationTicks = 30u;

        [Header("Validation serveur M1")]
        [SerializeField, Min(1)] private int _effortPerHeldTick = 4;
        [SerializeField, Min(0)] private int _reachFromCapsuleMm = 900;

        private readonly List<PredictedPlayerMotor> _serverPlayers = new(4);
        private readonly List<WallEffortIntent> _intents = new(4);
        private readonly List<TopologyCircleObstacle> _obstacles = new(4);
        private readonly Dictionary<int, uint> _lastConsumedPlayerTick = new();
        private WallSnapshotHistory _history;

        private TopologyArena _arena;
        private RuntimeWallDefinition _wallDefinition;
        private WallSimulationSettings _settings;
        private WallStateMachine _serverMachine;
        private WallStateMachine _clientMachine;
        private PredictionManager _predictionManager;
        private WallLiveTickClock _liveClock;
        private WallSnapshotTimelineSample _latestTimeline;
        private bool _hasLatestTimeline;
        private ulong _simulationFingerprint;
        private int _negativeStateId;
        private int _positiveStateId;
        private int _lastGateBlockingId;
        private uint _snapshotCount;
        private uint _invalidSnapshotCount;
        private uint _historyMissCount;
        private uint _rejectedInteractionCount;
        private uint _completedTransitionCount;
        private uint _rejectedTransitionCount;
        private uint _opposedEffortTickCount;
        private uint _targetSnapshotCount;
        private uint _observerSnapshotCount;
        private int _lastMidTransitionBlockingId;

        // La porte écarte, elle ne catapulte pas : la vitesse tangentielle est
        // bornée, et l'échantillon vaut un tick sur deux pour ne pas noyer le
        // propriétaire distant sous les RPC pendant les 90 ticks de bascule.
        private const float MaximumPushSpeedMetersPerSecond = 3.5f;
        private const float ClearanceSpeedMetersPerSecond = 1f;
        private const uint PushSampleIntervalTicks = 2u;
        private uint _sweptPushCount;

        // Quarante ticks d'impulsion avec un cooldown de quarante-huit ticks :
        // deux coups restent sous le seuil malgré le decay, le troisième ouvre.
        private readonly Dictionary<int, PunchImpulse> _punchImpulses = new(4);
        private readonly Dictionary<int, PunchImpulse> _pendingPunchImpulses = new(4);
        private readonly List<int> _expiredPunchSources = new(4);

        public bool IsReady => _arena != null && _wallDefinition != null;
        public WallState AuthoritativeState => _serverMachine?.State ?? default;
        public uint AuthoritativeTick => _serverMachine?.LastProcessedTick ?? 0u;
        public WallState ObservedState => _serverMachine?.State ?? _clientMachine?.State ?? default;
        public uint ObservedTick => _serverMachine?.LastProcessedTick ??
                                    _clientMachine?.LastProcessedTick ?? 0u;
        public bool HasObservedState => _serverMachine != null || _hasLatestTimeline;
        public uint SnapshotCount => _snapshotCount;
        public uint InvalidSnapshotCount => _invalidSnapshotCount;
        public uint HistoryMissCount => _historyMissCount;
        public uint RejectedInteractionCount => _rejectedInteractionCount;
        public uint CompletedTransitionCount => _completedTransitionCount;
        public uint RejectedTransitionCount => _rejectedTransitionCount;
        public uint OpposedEffortTickCount => _opposedEffortTickCount;
        public uint SweptPushCount => _sweptPushCount;

        // Exposé pour l'indicateur local du pousseur : il rejoue la règle pure
        // sur sa propre position pour savoir pourquoi rien ne bouge. L'hôte
        // reste seul juge de l'effort réellement compté.
        public int WallId => _wallId;
        public int EffortThreshold => _effortThreshold;
        public int ReachFromCapsuleMm => _reachFromCapsuleMm;
        public int NegativeStateId => _negativeStateId;
        public uint TargetSnapshotCount => _targetSnapshotCount;
        public uint ObserverSnapshotCount => _observerSnapshotCount;

        private void Awake()
        {
            SetTickCallbacks(TickCallback.PreTick);
        }

        public override void OnStartNetwork()
        {
            base.OnStartNetwork();
            ResolveContract();
        }

        public override void OnStartServer()
        {
            base.OnStartServer();
            ResolveContract();
            _serverMachine = new WallStateMachine(
                _settings,
                _wallId,
                _negativeStateId,
                _positiveStateId,
                _wallDefinition.InitialStateId,
                0u);
            _lastConsumedPlayerTick.Clear();
            _completedTransitionCount = 0u;
            _rejectedTransitionCount = 0u;
            _opposedEffortTickCount = 0u;
            ApplyState(_serverMachine.State, _serverMachine.LastProcessedTick);
            Debug.Log(
                $"[GAME-M1-WALL] authority_ready wall={_wallId} " +
                $"states={_negativeStateId},{_positiveStateId} tickRate={TimeManager.TickRate}.");
        }

        public override void OnSpawnServer(NetworkConnection connection)
        {
            base.OnSpawnServer(connection);
            if (_serverMachine == null || connection == null)
                return;

            var snapshot = _serverMachine.CaptureSnapshot();
            ReceiveSnapshotTargetRpc(
                connection,
                snapshot.ToBytes(),
                TimeManager.Tick,
                SnapshotSchemaVersion,
                _arena.Map.Checksum,
                TimeManager.TickRate,
                _simulationFingerprint,
                Channel.Reliable);
        }

        public override void OnStopServer()
        {
            _serverMachine = null;
            _lastConsumedPlayerTick.Clear();
            base.OnStopServer();
        }

        public override void OnStartClient()
        {
            base.OnStartClient();
            ResolveContract();
            _history = new WallSnapshotHistory(
                WallSnapshotReceiverPolicy.CalculateHistoryCapacity(TimeManager.TickRate));
            _liveClock = new WallLiveTickClock();
            _historyMissCount = 0u;
            _targetSnapshotCount = 0u;
            _observerSnapshotCount = 0u;
            _predictionManager = InstanceFinder.PredictionManager;
            if (_predictionManager != null)
            {
                _predictionManager.OnPreReplicateReplay += OnPreReplicateReplay;
                _predictionManager.OnPostReconcile += OnPostReconcile;
            }
        }

        public override void OnStopClient()
        {
            if (_predictionManager != null)
            {
                _predictionManager.OnPreReplicateReplay -= OnPreReplicateReplay;
                _predictionManager.OnPostReconcile -= OnPostReconcile;
            }
            _predictionManager = null;
            _clientMachine = null;
            _history?.Clear();
            _history = null;
            _liveClock?.Reset();
            _liveClock = null;
            _hasLatestTimeline = false;
            base.OnStopClient();
        }

        protected override void TimeManager_OnPreTick()
        {
            if (IsServerStarted)
            {
                AdvanceServerTick();
                return;
            }

            if (IsClientStarted && _hasLatestTimeline && _liveClock?.IsInitialized == true)
            {
                if (_liveClock.TryPreviewObservation(
                        _latestTimeline.ServerTransportTick,
                        TimeManager.Tick,
                        out var liveTickCandidate))
                {
                    _liveClock.CommitObservation(liveTickCandidate);
                    ApplyTimeline(_latestTimeline, _liveClock.Tick);
                }
            }
        }

        private void AdvanceServerTick()
        {
            if (_serverMachine == null)
                return;

            CollectServerIntents();
            ObserveIntentComposition();
            _lastGateBlockingId = 0;
            var logicalTick = TickMath.Next(_serverMachine.LastProcessedTick);
            var result = _serverMachine.AdvanceTick(logicalTick, _intents, EvaluateTransition);
            ApplyState(result.Current, logicalTick);
            PushSweptPlayers(result.Current, logicalTick);

            if ((result.Events & WallTickEvents.TransitionStarted) != 0)
            {
                var transition = result.Current.ActiveTransition.Value;
                Debug.Log(
                    $"[GAME-M1-WALL] transition_started wall={_wallId} " +
                    $"from={transition.FromStateId} to={transition.ToStateId} " +
                    $"logicalTick={logicalTick} revision={result.Current.Revision}.");
            }
            if ((result.Events & WallTickEvents.TransitionRejected) != 0)
            {
                _rejectedTransitionCount++;
                Debug.Log(
                    $"[GAME-M1-WALL] transition_rejected wall={_wallId} " +
                    $"reason={result.RejectionCode} blockingId={_lastGateBlockingId} " +
                    $"logicalTick={logicalTick}.");
            }
            if ((result.Events & WallTickEvents.TransitionCompleted) != 0)
            {
                _completedTransitionCount++;
                ValidateCompletedPoseClear(result.Current.StateId, logicalTick);
                Debug.Log(
                    $"[GAME-M1-WALL] transition_completed wall={_wallId} " +
                    $"state={result.Current.StateId} logicalTick={logicalTick} " +
                    $"revision={result.Current.Revision}.");
            }

            if (WallSnapshotReceiverPolicy.ShouldBroadcast(
                    result.Changed,
                    logicalTick,
                    TimeManager.TickRate))
            {
                var payload = _serverMachine.CaptureSnapshot().ToBytes();
                ReceiveSnapshotObserversRpc(
                    payload,
                    TimeManager.Tick,
                    SnapshotSchemaVersion,
                    _arena.Map.Checksum,
                    TimeManager.TickRate,
                    _simulationFingerprint,
                    Channel.Reliable);
            }
        }

        private void CollectServerIntents()
        {
            _intents.Clear();
            PredictedPlayerMotor.CopyServerInstances(_serverPlayers);
            _serverPlayers.Sort((left, right) => left.ObjectId.CompareTo(right.ObjectId));
            for (var index = 0; index < _serverPlayers.Count; index++)
            {
                var player = _serverPlayers[index];
                if (player.ObjectId < 0 ||
                    !player.TryGetLatestAuthoritativeCommand(out var command))
                {
                    continue;
                }

                if (_lastConsumedPlayerTick.TryGetValue(player.ObjectId, out var consumedTick) &&
                    consumedTick == command.Tick)
                {
                    continue;
                }
                _lastConsumedPlayerTick[player.ObjectId] = command.Tick;

                if (!command.Has(PlayerCommandButtons.InteractHeld))
                    continue;
                var state = _serverMachine.State;
                if (state.IsTransitioning)
                    continue;

                var localPosition = _arena.transform.InverseTransformPoint(player.transform.position);
                var controller = player.CharacterController;
                var scale = player.transform.lossyScale;
                var radiusMeters = controller == null
                    ? 0.4f
                    : controller.radius * Mathf.Max(Mathf.Abs(scale.x), Mathf.Abs(scale.z));
                var decision = M1WallInteractionRules.Evaluate(
                    _arena.Map,
                    _wallId,
                    state.StateId,
                    QuantizeMillimeters(localPosition.x),
                    QuantizeMillimeters(localPosition.z),
                    QuantizeRadiusMillimeters(radiusMeters),
                    _reachFromCapsuleMm);
                if (!decision.Allowed)
                {
                    _rejectedInteractionCount++;
                    continue;
                }

                _intents.Add(new WallEffortIntent(
                    _wallId,
                    player.ObjectId,
                    decision.EffortSign * _effortPerHeldTick));
                _punchImpulses.Remove(player.ObjectId);
            }

            AppendPunchIntents();
        }

        /// <summary>
        /// Un coup de poing verse une impulsion bornée par le même plafond par
        /// source et par tick que la poussée continue. La durée partagée avec le
        /// cooldown garantit que deux coups ne suffisent pas et que trois coups
        /// enchaînés atteignent le seuil.
        /// </summary>
        public bool TryRegisterPunchImpulse(int sourceId, Vector3 worldPosition, float radiusMeters)
        {
            if (!IsServerStarted || _serverMachine == null || _arena?.Map == null)
                return false;

            var state = _serverMachine.State;
            if (state.IsTransitioning)
                return false;

            var localPosition = _arena.transform.InverseTransformPoint(worldPosition);
            var decision = M1WallInteractionRules.Evaluate(
                _arena.Map,
                _wallId,
                state.StateId,
                QuantizeMillimeters(localPosition.x),
                QuantizeMillimeters(localPosition.z),
                QuantizeRadiusMillimeters(radiusMeters),
                _reachFromCapsuleMm);
            if (!decision.Allowed)
                return false;

            _punchImpulses[sourceId] = new PunchImpulse(
                decision.EffortSign,
                M1PunchTuning.WallImpulseTicks);
            return true;
        }

        private void AppendPunchIntents()
        {
            if (_punchImpulses.Count == 0)
                return;

            _expiredPunchSources.Clear();
            foreach (var entry in _punchImpulses)
            {
                var impulse = entry.Value;
                _intents.Add(new WallEffortIntent(
                    _wallId,
                    entry.Key,
                    impulse.Sign * _effortPerHeldTick));
                if (impulse.RemainingTicks <= 1u)
                    _expiredPunchSources.Add(entry.Key);
                else
                    _pendingPunchImpulses[entry.Key] = impulse.Consumed();
            }

            foreach (var pair in _pendingPunchImpulses)
                _punchImpulses[pair.Key] = pair.Value;
            _pendingPunchImpulses.Clear();
            for (var index = 0; index < _expiredPunchSources.Count; index++)
                _punchImpulses.Remove(_expiredPunchSources[index]);
        }

        private readonly struct PunchImpulse
        {
            public PunchImpulse(int sign, uint remainingTicks)
            {
                Sign = sign;
                RemainingTicks = remainingTicks;
            }

            public int Sign { get; }
            public uint RemainingTicks { get; }

            public PunchImpulse Consumed() => new(Sign, RemainingTicks - 1u);
        }

        private WallTransitionGateDecision EvaluateTransition(WallTransitionRequest request)
        {
            BuildServerObstacles();
            var decision = TopologyTransitionGuard.Evaluate(
                _arena.Map,
                _arena.WallStates,
                request.WallId,
                request.ToStateId,
                TopologyTransitionPolicy.M1PushDuel,
                _obstacles);
            _lastGateBlockingId = decision.BlockingId;
            return decision.Allowed
                ? WallTransitionGateDecision.Accept()
                : WallTransitionGateDecision.Reject(decision.RejectionCode);
        }

        private void ObserveIntentComposition()
        {
            var hasNegative = false;
            var hasPositive = false;
            for (var index = 0; index < _intents.Count; index++)
            {
                hasNegative |= _intents[index].SignedEffort < 0;
                hasPositive |= _intents[index].SignedEffort > 0;
            }
            if (hasNegative && hasPositive)
            {
                long netEffort = 0L;
                for (var index = 0; index < _intents.Count; index++)
                    netEffort += _intents[index].SignedEffort;
                if (netEffort != 0L)
                    return;

                _opposedEffortTickCount++;
                if (_opposedEffortTickCount == 1u)
                {
                    Debug.Log(
                        $"[GAME-M1-WALL] balanced_opposition wall={_wallId} " +
                        $"sources={_intents.Count} netEffort=0 logicalTick={AuthoritativeTick}.",
                        this);
                }
            }
        }

        private void BuildServerObstacles()
        {
            _obstacles.Clear();
            PredictedPlayerMotor.CopyServerInstances(_serverPlayers);
            _serverPlayers.Sort((left, right) => left.ObjectId.CompareTo(right.ObjectId));
            for (var index = 0; index < _serverPlayers.Count; index++)
            {
                var player = _serverPlayers[index];
                if (player.ObjectId < 0)
                    continue;
                var controller = player.CharacterController;
                var scale = player.transform.lossyScale;
                var radius = controller == null
                    ? 0.4f
                    : controller.radius * Mathf.Max(Mathf.Abs(scale.x), Mathf.Abs(scale.z));
                _obstacles.Add(_arena.CreateObstacleFromWorld(
                    player.ObjectId,
                    player.transform.position,
                    radius));
            }
        }

        /// <summary>
        /// Preuve runtime de la post-condition physique : une transition terminée
        /// ne doit laisser aucune capsule dans le volume stable du battant. Le log
        /// est consommé par le scénario réseau d'occupation.
        /// </summary>
        private void ValidateCompletedPoseClear(int stateId, uint logicalTick)
        {
            BuildServerObstacles();
            var destination = TopologyGeometry.WallBox(_arena.Map, _wallId, stateId);
            var hasBlockingPlayer = false;
            var blockingId = 0;
            var blockingCenterXMm = 0;
            var blockingCenterZMm = 0;
            var blockingRadiusMm = 0;
            for (var index = 0; index < _obstacles.Count; index++)
            {
                var obstacle = _obstacles[index];
                if (!destination.IntersectsCircle(
                        obstacle.CenterXMm,
                        obstacle.CenterZMm,
                        obstacle.RadiusMm))
                {
                    continue;
                }

                if (!hasBlockingPlayer || obstacle.ObstacleId < blockingId)
                {
                    blockingId = obstacle.ObstacleId;
                    blockingCenterXMm = obstacle.CenterXMm;
                    blockingCenterZMm = obstacle.CenterZMm;
                    blockingRadiusMm = obstacle.RadiusMm;
                }
                hasBlockingPlayer = true;
            }

            if (hasBlockingPlayer)
            {
                Debug.LogError(
                    $"[GAME-M1-WALL] completed_pose_overlap wall={_wallId} " +
                    $"state={stateId} playerId={blockingId} " +
                    $"playerMm={blockingCenterXMm},{blockingCenterZMm} " +
                    $"radiusMm={blockingRadiusMm} logicalTick={logicalTick}.",
                    this);
                return;
            }

            Debug.Log(
                $"[GAME-M1-WALL] completed_pose_clear wall={_wallId} state={stateId} " +
                $"logicalTick={logicalTick}.",
                this);
        }

        /// <summary>
        /// La porte écarte ce qu'elle balaie. L'hôte mesure le recouvrement réel
        /// de la pose du tick et injecte une vitesse tangentielle par le même
        /// chemin autoritaire que le recul d'un coup : le propriétaire la prédit,
        /// la réconciliation corrige. Le mur, lui, ne s'arrête jamais — sa pose
        /// reste une fonction du tick.
        /// </summary>
        private void PushSweptPlayers(WallState state, uint logicalTick)
        {
            if (!state.ActiveTransition.HasValue)
            {
                _lastMidTransitionBlockingId = 0;
                return;
            }
            if (logicalTick % PushSampleIntervalTicks != 0u)
                return;

            var transition = state.ActiveTransition.Value;
            var map = _arena.Map;
            var pivotLocal = TopologyGeometry
                .QuarterTurnSweep(map, _wallId, transition.FromStateId, transition.ToStateId)
                .PivotMm.Meters;
            var progress = state.SamplePose(logicalTick).ProgressQ16 /
                           (float)TickMath.CompleteProgressQ16;
            var fromDirection = FlatDirection(
                TopologyGeometry.WallBox(map, _wallId, transition.FromStateId).CenterMeters -
                pivotLocal);
            var toDirection = FlatDirection(
                TopologyGeometry.WallBox(map, _wallId, transition.ToStateId).CenterMeters -
                pivotLocal);
            var turnSign = Mathf.Sign(Vector3.Cross(fromDirection, toDirection).y);
            var bladeDirection = Quaternion.Euler(0f, turnSign * 90f * progress, 0f) * fromDirection;

            // Le battant est un segment issu du gond : longueur d'arête et
            // demi-épaisseur viennent de la topologie, pas d'une requête physique
            // dont le résultat dépendrait du moteur et de la plateforme.
            var bladeLength = map.Dimensions.CellPitchMm / 1000f;
            var halfThickness = map.Dimensions.WallThicknessMm / 2000f;
            var angularSpeed = SignedAngularSpeed(transition, pivotLocal);

            PredictedPlayerMotor.CopyServerInstances(_serverPlayers);
            var pushedThisSample = false;
            for (var index = 0; index < _serverPlayers.Count; index++)
            {
                var motor = _serverPlayers[index];
                if (motor == null)
                    continue;

                var radial = FlatVector(
                    _arena.transform.InverseTransformPoint(motor.transform.position) - pivotLocal);
                var controller = motor.CharacterController;
                var scale = motor.transform.lossyScale;
                var radius = controller == null
                    ? 0.4f
                    : controller.radius * Mathf.Max(Mathf.Abs(scale.x), Mathf.Abs(scale.z));

                var along = Mathf.Clamp(Vector3.Dot(radial, bladeDirection), 0f, bladeLength);
                var lateral = (radial - bladeDirection * along).magnitude;
                if (lateral > halfThickness + radius)
                    continue;
                if (radial.sqrMagnitude < 0.0001f)
                    continue;

                var surfaceVelocity = Vector3.Cross(
                    new Vector3(0f, angularSpeed, 0f),
                    radial);
                var targetSpeed = Mathf.Min(
                    MaximumPushSpeedMetersPerSecond,
                    surfaceVelocity.magnitude + ClearanceSpeedMetersPerSecond);
                var localVelocity = surfaceVelocity.normalized * targetSpeed;
                motor.ApplyPushVelocityFromServer(
                    _arena.transform.TransformDirection(localVelocity));
                _sweptPushCount++;
                pushedThisSample = true;

                if (motor.ObjectId == _lastMidTransitionBlockingId)
                    continue;
                _lastMidTransitionBlockingId = motor.ObjectId;
                Debug.Log(
                    $"[GAME-M1-WALL] swept_player_pushed wall={_wallId} " +
                    $"playerId={motor.ObjectId} speed={localVelocity.magnitude:F2} " +
                    $"logicalTick={logicalTick}.");
            }

            if (!pushedThisSample)
                _lastMidTransitionBlockingId = 0;
        }

        private static Vector3 FlatVector(Vector3 value) => new(value.x, 0f, value.z);

        private static Vector3 FlatDirection(Vector3 value) => FlatVector(value).normalized;

        /// <summary>
        /// Sens et vitesse de rotation déduits des deux poses : la pose d'arrivée
        /// donne le sens, la durée de transition donne la cadence.
        /// </summary>
        private float SignedAngularSpeed(WallTransition transition, Vector3 pivotLocal)
        {
            var from = TopologyGeometry
                .WallBox(_arena.Map, _wallId, transition.FromStateId).CenterMeters - pivotLocal;
            var to = TopologyGeometry
                .WallBox(_arena.Map, _wallId, transition.ToStateId).CenterMeters - pivotLocal;
            from.y = 0f;
            to.y = 0f;
            var sign = Mathf.Sign(Vector3.Cross(from.normalized, to.normalized).y);
            var durationSeconds = (float)(transition.DurationTicks * TimeManager.TickDelta);
            return durationSeconds <= 0f
                ? 0f
                : sign * (Mathf.PI * 0.5f) / durationSeconds;
        }

        [ObserversRpc(BufferLast = true, ExcludeServer = true)]
        private void ReceiveSnapshotObserversRpc(
            byte[] payload,
            uint serverTransportTick,
            byte schemaVersion,
            string topologyChecksum,
            ushort tickRate,
            ulong simulationFingerprint,
            Channel channel = Channel.Reliable)
        {
            ProcessRemoteSnapshot(
                payload,
                serverTransportTick,
                schemaVersion,
                topologyChecksum,
                tickRate,
                simulationFingerprint,
                "observer");
        }

        [TargetRpc]
        private void ReceiveSnapshotTargetRpc(
            NetworkConnection connection,
            byte[] payload,
            uint serverTransportTick,
            byte schemaVersion,
            string topologyChecksum,
            ushort tickRate,
            ulong simulationFingerprint,
            Channel channel = Channel.Reliable)
        {
            ProcessRemoteSnapshot(
                payload,
                serverTransportTick,
                schemaVersion,
                topologyChecksum,
                tickRate,
                simulationFingerprint,
                "target");
        }

        private void ProcessRemoteSnapshot(
            byte[] payload,
            uint serverTransportTick,
            byte schemaVersion,
            string topologyChecksum,
            ushort tickRate,
            ulong simulationFingerprint,
            string source)
        {
            // FishNet ne conserve pas ExcludeServer lors du rejeu d'un RPC bufferisé.
            // Ce test doit donc précéder toute résolution ou mutation côté client.
            if (!WallSnapshotReceiverPolicy.ShouldProcess(IsServerStarted))
                return;

            ResolveContract();
            if (schemaVersion != SnapshotSchemaVersion)
            {
                RejectSnapshot("schema_mismatch");
                return;
            }
            if (!string.Equals(topologyChecksum, _arena.Map.Checksum, StringComparison.Ordinal))
            {
                RejectSnapshot("topology_checksum_mismatch");
                return;
            }
            if (tickRate != TimeManager.TickRate)
            {
                RejectSnapshot("tick_rate_mismatch");
                return;
            }
            if (simulationFingerprint != _simulationFingerprint)
            {
                RejectSnapshot("simulation_fingerprint_mismatch");
                return;
            }
            if (!WallSnapshot.TryFromBytes(payload, out var snapshot, out var rejectionCode))
            {
                RejectSnapshot(rejectionCode);
                return;
            }
            if (snapshot.WallId != _wallId)
            {
                RejectSnapshot("wall_id_mismatch");
                return;
            }

            // Ces compteurs mesurent une livraison décodée et compatible. L'application
            // effective reste prouvée séparément par SnapshotCount : FishNet peut rejouer le
            // buffer ObserversRpc juste avant le TargetRpc frais, qui devient alors un doublon
            // valide du même état.
            if (string.Equals(source, "target", StringComparison.Ordinal))
                _targetSnapshotCount++;
            else
                _observerSnapshotCount++;

            EnsureClientHistory();
            var historyStatus = _history.PreviewRecord(serverTransportTick, snapshot);
            if (historyStatus == WallSnapshotRecordStatus.Conflict ||
                historyStatus == WallSnapshotRecordStatus.Invalid)
            {
                RejectSnapshot(historyStatus.ToString().ToLowerInvariant());
                return;
            }
            if (historyStatus == WallSnapshotRecordStatus.Stale ||
                historyStatus == WallSnapshotRecordStatus.Duplicate)
            {
                LogFreshTargetSnapshot(source, snapshot, serverTransportTick, historyStatus);
                return;
            }

            WallStateMachine candidateMachine = null;
            WallSnapshotApplyStatus applyStatus;
            if (_clientMachine == null)
            {
                try
                {
                    candidateMachine = WallStateMachine.FromSnapshot(
                        _settings,
                        _negativeStateId,
                        _positiveStateId,
                        snapshot);
                    applyStatus = WallSnapshotApplyStatus.Applied;
                }
                catch (ArgumentException)
                {
                    RejectSnapshot(WallSnapshotDecodeCodes.PayloadMalformed);
                    return;
                }
            }
            else
            {
                applyStatus = _clientMachine.PreviewSnapshot(snapshot);
                if (applyStatus == WallSnapshotApplyStatus.Invalid ||
                    applyStatus == WallSnapshotApplyStatus.RevisionConflict)
                {
                    RejectSnapshot(applyStatus.ToString().ToLowerInvariant());
                    return;
                }
                if (applyStatus == WallSnapshotApplyStatus.Stale)
                    return;
            }

            EnsureLiveClock();
            if (!_liveClock.TryPreviewObservation(
                    serverTransportTick,
                    TimeManager.Tick,
                    out var liveTickCandidate))
            {
                RejectSnapshot("live_tick_ambiguous");
                return;
            }

            var recorded = _history.Record(serverTransportTick, snapshot);
            if (recorded != WallSnapshotRecordStatus.Added)
            {
                RejectSnapshot($"history_commit_{recorded.ToString().ToLowerInvariant()}");
                return;
            }

            if (candidateMachine != null)
                _clientMachine = candidateMachine;
            else if (applyStatus == WallSnapshotApplyStatus.Applied &&
                     _clientMachine.TryApplySnapshot(snapshot) != WallSnapshotApplyStatus.Applied)
            {
                RejectSnapshot("machine_commit_failed");
                return;
            }

            _latestTimeline = new WallSnapshotTimelineSample(serverTransportTick, snapshot);
            _hasLatestTimeline = true;
            _liveClock.CommitObservation(liveTickCandidate);
            _snapshotCount++;
            if (_snapshotCount == 1u)
            {
                Debug.Log(
                    $"[GAME-M1-WALL] first_snapshot wall={_wallId} " +
                    $"state={snapshot.StateId} revision={snapshot.Revision} " +
                    $"capturedTick={snapshot.CapturedTick} transitioning={snapshot.IsTransitioning} " +
                    $"source={source} serverTick={serverTransportTick} " +
                    $"liveTick={_liveClock.Tick} checksum={topologyChecksum}.",
                    this);
            }
            LogFreshTargetSnapshot(
                source,
                snapshot,
                serverTransportTick,
                WallSnapshotRecordStatus.Added);
            ApplyTimeline(_latestTimeline, _liveClock.Tick);
        }

        private void OnPreReplicateReplay(uint clientTick, uint serverTick)
        {
            if (_history != null && _history.TryGetAtOrBefore(serverTick, out var sample))
            {
                ApplyTimeline(sample, serverTick);
                return;
            }

            _historyMissCount++;
            if (_historyMissCount == 1u || _historyMissCount % 120u == 0u)
            {
                Debug.LogWarning(
                    $"[GAME-M1-WALL] history_miss wall={_wallId} serverTick={serverTick} " +
                    $"count={_historyMissCount} fallback=oldest.",
                    this);
            }
            if (_history != null && _history.TryGetOldest(out var oldest))
                ApplyTimeline(oldest, oldest.ServerTransportTick);
        }

        private void OnPostReconcile(uint clientTick, uint serverTick)
        {
            if (_hasLatestTimeline && _liveClock?.IsInitialized == true)
                ApplyTimeline(_latestTimeline, _liveClock.Tick);
        }

        private void ApplyTimeline(WallSnapshotTimelineSample sample, uint serverTransportTick)
        {
            ApplyState(sample.Snapshot.ToWallState(), sample.ProjectLogicalTick(serverTransportTick));
        }

        private void ApplyState(WallState state, uint logicalTick)
        {
            var pose = state.SamplePose(logicalTick);
            _arena.ApplyAuthoritativePose(_wallId, state.StateId, pose);
        }

        private void RejectSnapshot(string reason)
        {
            _invalidSnapshotCount++;
            if (_invalidSnapshotCount == 1u || _invalidSnapshotCount % 120u == 0u)
            {
                Debug.LogWarning(
                    $"[GAME-M1-WALL] snapshot_rejected wall={_wallId} reason={reason} " +
                    $"count={_invalidSnapshotCount}.",
                    this);
            }
        }

        private void ResolveContract()
        {
            if (TimeManager == null || TimeManager.PhysicsMode != PhysicsMode.TimeManager)
            {
                throw new InvalidOperationException(
                    "Le banc M1 exige FishNet PhysicsMode.TimeManager.");
            }
            if (_arena == null)
                _arena = FindFirstObjectByType<TopologyArena>();
            if (_arena == null || _arena.Map == null)
                throw new InvalidOperationException("TopologyArena M1 construite introuvable.");

            _wallDefinition = _arena.Map.GetWall(_wallId);
            if (!_wallDefinition.IsMobile || _wallDefinition.States.Count != 2)
            {
                throw new InvalidOperationException(
                    $"Le mur M1 {_wallId} doit être mobile et posséder exactement deux états.");
            }

            _negativeStateId = _wallDefinition.States[0].StateId;
            _positiveStateId = _wallDefinition.States[1].StateId;
            _settings = new WallSimulationSettings(
                _effortThreshold,
                _maximumEffortPerSourcePerTick,
                _effortDecayPerTick,
                _rejectedEffortRetention,
                _transitionDurationTicks);
            _simulationFingerprint = WallSnapshotReceiverPolicy.ComputeSimulationFingerprint(
                _settings,
                _effortPerHeldTick,
                _reachFromCapsuleMm);
            if (_effortPerHeldTick <= 0 ||
                _effortPerHeldTick > _maximumEffortPerSourcePerTick)
            {
                throw new InvalidOperationException(
                    "L'effort M1 par tick doit être positif et borné par source.");
            }
        }

        private void EnsureClientHistory()
        {
            _history ??= new WallSnapshotHistory(
                WallSnapshotReceiverPolicy.CalculateHistoryCapacity(TimeManager.TickRate));
        }

        private void EnsureLiveClock()
        {
            _liveClock ??= new WallLiveTickClock();
        }

        private void LogFreshTargetSnapshot(
            string source,
            WallSnapshot snapshot,
            uint serverTransportTick,
            WallSnapshotRecordStatus recordStatus)
        {
            if (!string.Equals(source, "target", StringComparison.Ordinal))
                return;
            Debug.Log(
                $"[GAME-M1-WALL] target_snapshot wall={_wallId} state={snapshot.StateId} " +
                $"revision={snapshot.Revision} capturedTick={snapshot.CapturedTick} " +
                $"transitioning={snapshot.IsTransitioning} serverTick={serverTransportTick} " +
                $"record={recordStatus.ToString().ToLowerInvariant()}.",
                this);
        }

        private static int QuantizeMillimeters(float meters)
        {
            var millimeters = Math.Round(
                meters * 1000d,
                MidpointRounding.AwayFromZero);
            if (double.IsNaN(millimeters) || double.IsInfinity(millimeters) ||
                millimeters < int.MinValue || millimeters > int.MaxValue)
            {
                throw new ArgumentOutOfRangeException(nameof(meters));
            }
            return (int)millimeters;
        }

        private static int QuantizeRadiusMillimeters(float meters)
        {
            if (float.IsNaN(meters) || float.IsInfinity(meters) || meters < 0f)
                throw new ArgumentOutOfRangeException(nameof(meters));
            var millimeters = Math.Ceiling(meters * 1000d) + 1d;
            if (millimeters > int.MaxValue)
                throw new ArgumentOutOfRangeException(nameof(meters));
            return (int)millimeters;
        }
    }
}
