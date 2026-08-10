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
    /// Adaptateur WALL-01 du banc M1. Le battant tourne librement sur 360 degrés :
    /// le serveur dérive contact, côté et bras de levier depuis ses propres joueurs,
    /// somme les couples opposés, avance l'intégrateur pur d'un tick, puis diffuse
    /// le segment de mouvement. Aucun transform ni wallId ne vient d'un client.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class M1AuthoritativeWallDirector : TickNetworkBehaviour
    {
        private const byte SnapshotSchemaVersion = 3;

        [Header("Mur canonique M1")]
        [SerializeField] private int _wallId = 10;

        /// <summary>
        /// Vitesse d'un pousseur seul au bout du battant. À 60 ticks par seconde,
        /// 400 milli-degrés par tick font un quart de tour en 3,75 s au bout et en
        /// 9,375 s contre le gond (levier plancher 400 pour mille, ci-dessous) :
        /// un battant alourdi par rapport au premier réglage (900 mdeg/tick),
        /// mais jamais immobile.
        /// </summary>
        [SerializeField, Min(1)] private int _maximumAngularSpeedMilliDegreesPerTick = 400;

        [SerializeField, Range(0, 1000)] private int _minimumLeveragePermille = 400;
        [SerializeField, Min(1)] private uint _maximumExtrapolationTicks = 180u;

        [Header("Validation serveur M1")]
        [SerializeField, Min(0)] private int _reachFromCapsuleMm = 900;

        private readonly List<PredictedPlayerMotor> _serverPlayers = new(4);
        private readonly List<WallTorqueIntent> _intents = new(4);
        private readonly Dictionary<int, uint> _lastConsumedPlayerTick = new();
        private WallSnapshotHistory _history;

        private TopologyArena _arena;
        private RuntimeWallDefinition _wallDefinition;
        private TopologyBladeSpec _blade;
        private WallSimulationSettings _settings;
        private WallRotationMachine _serverMachine;
        private WallRotationMachine _clientMachine;
        private PredictionManager _predictionManager;
        private WallLiveTickClock _liveClock;
        private WallSnapshotTimelineSample _latestTimeline;
        private bool _hasLatestTimeline;
        private ulong _simulationFingerprint;
        private uint _snapshotCount;
        private uint _invalidSnapshotCount;
        private uint _historyMissCount;
        private uint _rejectedInteractionCount;
        private uint _rotatingTickCount;
        private uint _segmentCount;
        private uint _reversalCount;
        private uint _quarterTurnCount;
        private uint _opposedTorqueTickCount;
        private uint _targetSnapshotCount;
        private uint _observerSnapshotCount;
        private long _cumulativeRotationMilliDegrees;
        private long _lastQuarterIndex;
        private bool _wasOpposed;
        private int _lastMidRotationBlockingId;

        // La porte écarte, elle ne catapulte pas : la vitesse tangentielle est
        // bornée, et l'échantillon vaut un tick sur deux pour ne pas noyer le
        // propriétaire distant sous les RPC pendant toute la rotation.
        private const float MaximumPushSpeedMetersPerSecond = 3.5f;
        private const float ClearanceSpeedMetersPerSecond = 1f;
        private const uint PushSampleIntervalTicks = 2u;
        private uint _sweptPushCount;

        // Une frappe verse un couple atténué (M1PunchTuning.PunchTorqueScalePermille)
        // pendant quinze ticks au lieu de l'appui continu : le battant bouge
        // visiblement à chaque coup, sans balancer une fraction de tour, et sans
        // qu'un client puisse désigner son mur ni son sens.
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
        public uint RotatingTickCount => _rotatingTickCount;
        public uint SegmentCount => _segmentCount;
        public uint ReversalCount => _reversalCount;
        public uint QuarterTurnCount => _quarterTurnCount;
        public uint OpposedTorqueTickCount => _opposedTorqueTickCount;
        public uint SweptPushCount => _sweptPushCount;
        public long CumulativeRotationMilliDegrees => _cumulativeRotationMilliDegrees;

        // Exposé pour l'indicateur local du pousseur : il rejoue la règle pure sur
        // sa propre position pour savoir dans quel sens et avec quelle puissance il
        // agit. L'hôte reste seul juge du couple réellement compté.
        public int WallId => _wallId;
        public int ReachFromCapsuleMm => _reachFromCapsuleMm;
        public int MinimumLeveragePermille => _minimumLeveragePermille;
        public int MaximumAngularSpeedMilliDegreesPerTick => _maximumAngularSpeedMilliDegreesPerTick;
        public uint MaximumExtrapolationTicks => _maximumExtrapolationTicks;
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
            _serverMachine = new WallRotationMachine(_settings, _wallId, 0, 0u);
            _lastConsumedPlayerTick.Clear();
            _rotatingTickCount = 0u;
            _segmentCount = 0u;
            _reversalCount = 0u;
            _quarterTurnCount = 0u;
            _opposedTorqueTickCount = 0u;
            _cumulativeRotationMilliDegrees = 0L;
            _lastQuarterIndex = 0L;
            _wasOpposed = false;
            ApplyState(_serverMachine.State, _serverMachine.LastProcessedTick);
            Debug.Log(
                $"[GAME-M1-WALL] authority_ready wall={_wallId} " +
                $"maxSpeedMdegPerTick={_maximumAngularSpeedMilliDegreesPerTick} " +
                $"minLeveragePermille={_minimumLeveragePermille} " +
                $"reachMm={_reachFromCapsuleMm} tickRate={TimeManager.TickRate}.");
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
            var logicalTick = TickMath.Next(_serverMachine.LastProcessedTick);
            var result = _serverMachine.AdvanceTick(logicalTick, _intents);
            ApplyState(result.Current, logicalTick);
            PushSweptPlayers(result.Current, logicalTick);
            ObserveRotation(result, logicalTick);

            if (WallSnapshotReceiverPolicy.ShouldBroadcast(
                    result.SegmentChanged,
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

        /// <summary>
        /// Diagnostics du battant. Aucun de ces compteurs ne modifie l'état partagé :
        /// ils rendent lisible dans le journal ce que le tick a décidé.
        /// </summary>
        private void ObserveRotation(WallTickResult result, uint logicalTick)
        {
            var velocity = result.Current.AngularVelocityMilliDegreesPerTick;
            if (velocity != 0)
                _rotatingTickCount++;
            _cumulativeRotationMilliDegrees += velocity;

            if ((result.Events & WallTickEvents.SegmentChanged) != 0)
            {
                _segmentCount++;
                if ((result.Events & WallTickEvents.RotationStarted) != 0)
                {
                    Debug.Log(
                        $"[GAME-M1-WALL] rotation_started wall={_wallId} " +
                        $"direction={Math.Sign(velocity)} netPermille={result.NetLeveragePermille} " +
                        $"velocityMdeg={velocity} angleMdeg={result.Current.AngleMilliDegrees} " +
                        $"sources={result.ContributingSourceCount} logicalTick={logicalTick} " +
                        $"revision={result.Current.Revision}.");
                }
                else if ((result.Events & WallTickEvents.RotationStopped) != 0)
                {
                    Debug.Log(
                        $"[GAME-M1-WALL] rotation_stopped wall={_wallId} " +
                        $"angleMdeg={result.Current.AngleMilliDegrees} " +
                        $"cumulativeMdeg={_cumulativeRotationMilliDegrees} " +
                        $"logicalTick={logicalTick} revision={result.Current.Revision}.");
                }
                else if ((result.Events & WallTickEvents.DirectionReversed) != 0)
                {
                    _reversalCount++;
                    Debug.Log(
                        $"[GAME-M1-WALL] direction_reversed wall={_wallId} " +
                        $"direction={Math.Sign(velocity)} netPermille={result.NetLeveragePermille} " +
                        $"angleMdeg={result.Current.AngleMilliDegrees} logicalTick={logicalTick} " +
                        $"revision={result.Current.Revision}.");
                }
            }

            var opposed = (result.Events & WallTickEvents.TorqueOpposed) != 0;
            if (opposed)
            {
                _opposedTorqueTickCount++;
                if (!_wasOpposed)
                {
                    Debug.Log(
                        $"[GAME-M1-WALL] torque_opposed wall={_wallId} " +
                        $"sources={result.ContributingSourceCount} " +
                        $"netPermille={result.NetLeveragePermille} " +
                        $"angleMdeg={result.Current.AngleMilliDegrees} logicalTick={logicalTick}.");
                }
            }
            _wasOpposed = opposed;

            // Un quart de tour franchi est la preuve lisible qu'un battant libre
            // dépasse ses deux poses historiques ; quatre d'affilée dans le même
            // sens valent un tour complet.
            var quarterIndex = _cumulativeRotationMilliDegrees /
                               FixedTrigonometry.QuarterTurnMilliDegrees;
            if (quarterIndex != _lastQuarterIndex)
            {
                _lastQuarterIndex = quarterIndex;
                _quarterTurnCount++;
                Debug.Log(
                    $"[GAME-M1-WALL] quarter_turn wall={_wallId} quarterIndex={quarterIndex} " +
                    $"angleMdeg={result.Current.AngleMilliDegrees} " +
                    $"cumulativeMdeg={_cumulativeRotationMilliDegrees} logicalTick={logicalTick}.");
            }
        }

        private void CollectServerIntents()
        {
            _intents.Clear();
            PredictedPlayerMotor.CopyServerInstances(_serverPlayers);
            _serverPlayers.Sort((left, right) => left.ObjectId.CompareTo(right.ObjectId));
            var angle = _serverMachine.State.AngleMilliDegrees;
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

                var decision = EvaluateContact(angle, player.transform.position, RadiusOf(player));
                if (!decision.Allowed)
                {
                    _rejectedInteractionCount++;
                    continue;
                }

                _intents.Add(new WallTorqueIntent(
                    _wallId,
                    player.ObjectId,
                    decision.Direction,
                    decision.LeveragePermille));
                _punchImpulses.Remove(player.ObjectId);
            }

            AppendPunchIntents();
        }

        /// <summary>
        /// Rejoue la règle pure sur une position monde. Le quantifieur reste ici :
        /// la règle, elle, ne connaît que des millimètres entiers.
        /// </summary>
        private M1WallInteractionDecision EvaluateContact(
            int angleMilliDegrees,
            Vector3 worldPosition,
            float radiusMeters)
        {
            var local = _arena.transform.InverseTransformPoint(worldPosition);
            return M1WallInteractionRules.Evaluate(
                _arena.Map,
                _wallId,
                angleMilliDegrees,
                QuantizeMillimeters(local.x),
                QuantizeMillimeters(local.z),
                QuantizeRadiusMillimeters(radiusMeters),
                _reachFromCapsuleMm,
                _minimumLeveragePermille);
        }

        private static float RadiusOf(PredictedPlayerMotor player)
        {
            var controller = player.CharacterController;
            var scale = player.transform.lossyScale;
            return controller == null
                ? 0.4f
                : controller.radius * Mathf.Max(Mathf.Abs(scale.x), Mathf.Abs(scale.z));
        }

        /// <summary>
        /// Un coup de poing verse un couple atténué par rapport à un appui
        /// continu, pendant une durée bornée : le sens et le levier sont figés au
        /// moment de l'impact, le battant continue donc de tourner un instant
        /// après le coup. L'atténuation est appliquée ici, sur le levier calculé
        /// par le serveur — jamais sur une valeur qu'un client pourrait fournir —
        /// donc une seule fois par coup, sans détour possible.
        /// </summary>
        public bool TryRegisterPunchImpulse(int sourceId, Vector3 worldPosition, float radiusMeters)
        {
            if (!IsServerStarted || _serverMachine == null || _arena?.Map == null)
                return false;

            var decision = EvaluateContact(
                _serverMachine.State.AngleMilliDegrees,
                worldPosition,
                radiusMeters);
            if (!decision.Allowed)
                return false;

            _punchImpulses[sourceId] = new PunchImpulse(
                decision.Direction,
                ScalePunchLeverage(decision.LeveragePermille),
                M1PunchTuning.WallImpulseTicks);
            return true;
        }

        /// <summary>
        /// Réduit le levier d'un coup au pour-mille défini par
        /// <see cref="M1PunchTuning.PunchTorqueScalePermille"/>. Division entière
        /// tronquée vers zéro — comportement natif de C# sur les entiers, donc
        /// symétrique quel que soit le signe — pour rester cohérent avec le
        /// modèle de mur, entièrement entier. <paramref name="leveragePermille"/>
        /// n'est aujourd'hui jamais négatif (il vient de
        /// <see cref="M1WallInteractionDecision"/>, qui l'interdit), mais la
        /// division reste correcte si cette garantie changeait un jour.
        /// </summary>
        private static int ScalePunchLeverage(int leveragePermille) =>
            (int)((long)leveragePermille * M1PunchTuning.PunchTorqueScalePermille /
                  WallSimulationSettings.PermilleScale);

        private void AppendPunchIntents()
        {
            if (_punchImpulses.Count == 0)
                return;

            _expiredPunchSources.Clear();
            foreach (var entry in _punchImpulses)
            {
                var impulse = entry.Value;
                _intents.Add(new WallTorqueIntent(
                    _wallId,
                    entry.Key,
                    impulse.Direction,
                    impulse.LeveragePermille));
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
            public PunchImpulse(int direction, int leveragePermille, uint remainingTicks)
            {
                Direction = direction;
                LeveragePermille = leveragePermille;
                RemainingTicks = remainingTicks;
            }

            public int Direction { get; }
            public int LeveragePermille { get; }
            public uint RemainingTicks { get; }

            public PunchImpulse Consumed() =>
                new(Direction, LeveragePermille, RemainingTicks - 1u);
        }

        /// <summary>
        /// La porte écarte ce qu'elle balaie. L'hôte mesure le recouvrement de la
        /// pose du tick sur le segment déterministe du battant, puis injecte une
        /// vitesse tangentielle par le même chemin autoritaire que le recul d'un
        /// coup : le propriétaire la prédit, la réconciliation corrige. Le battant,
        /// lui, ne s'arrête jamais — sa pose reste une fonction du tick.
        /// </summary>
        private void PushSweptPlayers(WallState state, uint logicalTick)
        {
            if (!state.IsRotating)
            {
                _lastMidRotationBlockingId = 0;
                return;
            }
            if (logicalTick % PushSampleIntervalTicks != 0u)
                return;

            var map = _arena.Map;
            var pivotLocal = _blade.PivotMm.Meters;
            _blade.UnitDirection(state.AngleMilliDegrees, out var unitXQ16, out var unitZQ16);
            var bladeDirection = new Vector3(
                unitXQ16 / (float)FixedTrigonometry.Scale,
                0f,
                unitZQ16 / (float)FixedTrigonometry.Scale);
            var bladeLength = map.Dimensions.CellPitchMm / 1000f;
            var halfThickness = map.Dimensions.WallThicknessMm / 2000f;
            var angularSpeed = state.AngularVelocityMilliDegreesPerTick *
                               TimeManager.TickRate * 0.001f * Mathf.Deg2Rad;

            PredictedPlayerMotor.CopyServerInstances(_serverPlayers);
            var pushedThisSample = false;
            for (var index = 0; index < _serverPlayers.Count; index++)
            {
                var motor = _serverPlayers[index];
                if (motor == null)
                    continue;

                // Celui qui pousse n'est pas balayé : ses mains sont sur le battant
                // par choix. Lui injecter la vitesse tangentielle le catapulterait
                // sur le côté au lieu de le laisser accompagner la porte.
                if (IsPushing(motor.ObjectId))
                    continue;

                var radial = FlatVector(
                    _arena.transform.InverseTransformPoint(motor.transform.position) - pivotLocal);
                if (radial.sqrMagnitude < 0.0001f)
                    continue;

                var along = Mathf.Clamp(Vector3.Dot(radial, bladeDirection), 0f, bladeLength);
                var lateral = (radial - bladeDirection * along).magnitude;
                if (lateral > halfThickness + RadiusOf(motor))
                    continue;

                var surfaceVelocity = Vector3.Cross(new Vector3(0f, angularSpeed, 0f), radial);
                var targetSpeed = Mathf.Min(
                    MaximumPushSpeedMetersPerSecond,
                    surfaceVelocity.magnitude + ClearanceSpeedMetersPerSecond);
                var localVelocity = surfaceVelocity.normalized * targetSpeed;
                motor.ApplyPushVelocityFromServer(
                    _arena.transform.TransformDirection(localVelocity));
                _sweptPushCount++;
                pushedThisSample = true;

                if (motor.ObjectId == _lastMidRotationBlockingId)
                    continue;
                _lastMidRotationBlockingId = motor.ObjectId;
                Debug.Log(
                    $"[GAME-M1-WALL] swept_player_pushed wall={_wallId} " +
                    $"playerId={motor.ObjectId} speed={localVelocity.magnitude:F2} " +
                    $"angleMdeg={state.AngleMilliDegrees} logicalTick={logicalTick}.");
            }

            if (!pushedThisSample)
                _lastMidRotationBlockingId = 0;
        }

        private bool IsPushing(int sourceId)
        {
            for (var index = 0; index < _intents.Count; index++)
            {
                if (_intents[index].SourceId == sourceId)
                    return true;
            }

            return false;
        }

        private static Vector3 FlatVector(Vector3 value) => new(value.x, 0f, value.z);

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

            WallRotationMachine candidateMachine = null;
            WallSnapshotApplyStatus applyStatus;
            if (_clientMachine == null)
            {
                try
                {
                    candidateMachine = WallRotationMachine.FromSnapshot(_settings, snapshot);
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
                    $"angleMdeg={snapshot.AngleMilliDegrees} revision={snapshot.Revision} " +
                    $"capturedTick={snapshot.CapturedTick} rotating={snapshot.IsRotating} " +
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
            ApplyState(
                sample.Snapshot.ToWallState(),
                sample.ProjectLogicalTick(serverTransportTick));
        }

        private void ApplyState(WallState state, uint logicalTick)
        {
            _arena.ApplyAuthoritativePose(
                _wallId,
                state.SamplePose(logicalTick, _settings.MaximumExtrapolationTicks));
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
            if (!_wallDefinition.IsMobile)
            {
                throw new InvalidOperationException(
                    $"Le mur M1 {_wallId} doit être mobile et déclarer un gond.");
            }

            _blade = TopologyGeometry.Blade(_arena.Map, _wallId);
            _settings = new WallSimulationSettings(
                _maximumAngularSpeedMilliDegreesPerTick,
                _minimumLeveragePermille,
                _maximumExtrapolationTicks);
            _simulationFingerprint = WallSnapshotReceiverPolicy.ComputeSimulationFingerprint(
                _settings,
                _reachFromCapsuleMm);
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
                $"[GAME-M1-WALL] target_snapshot wall={_wallId} " +
                $"angleMdeg={snapshot.AngleMilliDegrees} revision={snapshot.Revision} " +
                $"capturedTick={snapshot.CapturedTick} rotating={snapshot.IsRotating} " +
                $"serverTick={serverTransportTick} " +
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
