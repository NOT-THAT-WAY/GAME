using System;
using FishNet.Managing;
using FishNet.Managing.Timing;
using UnityEngine;

namespace NotThatWay.Game
{
    /// <summary>
    /// Marqueurs structurés du banc M1. Ils ne décident rien : ils rendent les
    /// preuves de connexion, topology, joueur et mur lisibles après fermeture.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class M1PlaytestDiagnostics : MonoBehaviour
    {
        private NetworkManager _networkManager;
        private TopologyArena _arena;
        private int _lastServerConnectionCount = -1;
        private float _nextHeartbeatAt;
        private bool _readyLogged;
        private M1AutomatedTestPlan _automatedPlan;
        private float _automatedReadinessDeadline;
        private float _automatedEvaluationDeadline;
        private float _automatedQuitDeadline;
        private bool _automatedArmed;
        private bool _automatedResultLogged;
        private bool _automatedResultPassed;

        private void Start()
        {
            _networkManager = GetComponentInParent<NetworkManager>();
            if (_networkManager == null)
                _networkManager = FindFirstObjectByType<NetworkManager>();
            _arena = FindFirstObjectByType<TopologyArena>();
            if (!M1AutomatedTestPlan.TryParse(
                    Environment.GetCommandLineArgs(),
                    out _automatedPlan,
                    out var planError))
            {
                Debug.LogError($"[GAME-M1-RESULT] FAIL name=configuration reason={planError}.");
                Application.Quit(2);
                return;
            }
            if (_automatedPlan.Enabled)
            {
                if (!Debug.isDebugBuild && !Application.isEditor)
                {
                    Debug.LogError(
                        "[GAME-M1-RESULT] FAIL name=configuration " +
                        "reason=automation_requires_development_build.");
                    Application.Quit(2);
                    return;
                }
                _automatedReadinessDeadline = Time.realtimeSinceStartup +
                                              (float)_automatedPlan.ReadinessTimeoutSeconds;
                Debug.Log(
                    $"[GAME-M1-AUTO] test={_automatedPlan.Name} run={_automatedPlan.RunId} " +
                    $"evaluateAfterReady={_automatedPlan.EvaluateAfterReadySeconds:0.###}s " +
                    $"quitAfterReady={_automatedPlan.QuitAfterSeconds:0.###}s.");
            }
            TryLogReady();
        }

        private void Update()
        {
            TryLogReady();
            if (_networkManager == null)
                return;

            var serverConnections = _networkManager.ServerManager.Started
                ? _networkManager.ServerManager.Clients.Count
                : 0;
            if (serverConnections != _lastServerConnectionCount)
            {
                _lastServerConnectionCount = serverConnections;
                Debug.Log($"[GAME-M1] server_connections={serverConnections}.");
            }

            if (Time.unscaledTime < _nextHeartbeatAt)
            {
                TryFinishAutomatedTest();
                return;
            }
            _nextHeartbeatAt = Time.unscaledTime + 5f;
            LogHeartbeat("heartbeat");
            TryFinishAutomatedTest();
        }

        private void OnApplicationQuit()
        {
            LogHeartbeat("shutdown");
        }

        private void TryLogReady()
        {
            if (_readyLogged)
                return;
            if (_networkManager == null)
                _networkManager = FindFirstObjectByType<NetworkManager>();
            if (_arena == null)
                _arena = FindFirstObjectByType<TopologyArena>();
            if (_networkManager == null || _arena == null || _arena.Map == null)
                return;

            var timeManager = _networkManager.GetComponent<TimeManager>();
            Debug.Log(
                $"[GAME-M1] ready topology={_arena.Map.TopologyId} " +
                $"checksum={_arena.Map.Checksum} tickRate={timeManager?.TickRate ?? 0} " +
                $"physics={timeManager?.PhysicsMode.ToString() ?? "missing"}.");
            _readyLogged = true;
        }

        private void LogHeartbeat(string marker)
        {
            if (!_readyLogged || _networkManager == null)
                return;

            var wall = FindFirstObjectByType<M1AuthoritativeWallDirector>();
            var players = FindObjectsByType<PredictedPlayerMotor>(
                FindObjectsInactive.Exclude,
                FindObjectsSortMode.None);
            var wallState = wall != null && wall.HasObservedState
                ? $"{wall.ObservedState.StateId}:{wall.ObservedState.Revision}:" +
                  $"{wall.ObservedState.SignedEffort}:{wall.ObservedState.IsTransitioning}"
                : "unavailable";
            Debug.Log(
                $"[GAME-M1] {marker} server={_networkManager.ServerManager.Started} " +
                $"client={_networkManager.ClientManager.Started} players={players.Length} " +
                $"wall={wallState} snapshots={wall?.SnapshotCount ?? 0u} " +
                $"invalidSnapshots={wall?.InvalidSnapshotCount ?? 0u} " +
                $"historyMisses={wall?.HistoryMissCount ?? 0u}.");
        }

        private void TryFinishAutomatedTest()
        {
            if (!_automatedPlan.Enabled || _networkManager == null)
            {
                return;
            }

            var wall = FindFirstObjectByType<M1AuthoritativeWallDirector>();
            var authenticated = _networkManager.ClientManager.Started &&
                                _networkManager.ClientManager.Connection.IsAuthenticated;
            if (!_automatedArmed)
            {
                var readinessObservation = CaptureObservation(wall, authenticated);
                if (_automatedPlan.IsReadyToArm(readinessObservation))
                {
                    _automatedArmed = true;
                    _automatedEvaluationDeadline = Time.realtimeSinceStartup +
                        (float)_automatedPlan.EvaluateAfterReadySeconds;
                    _automatedQuitDeadline = Time.realtimeSinceStartup +
                        (float)_automatedPlan.QuitAfterSeconds;
                    Debug.Log(
                        $"[GAME-M1-AUTO] armed test={_automatedPlan.Name} " +
                        $"run={_automatedPlan.RunId}.");
                    return;
                }
                if (Time.realtimeSinceStartup >= _automatedReadinessDeadline)
                {
                    _automatedResultLogged = true;
                    Debug.LogError(
                        $"[GAME-M1-RESULT] FAIL name={_automatedPlan.Name} " +
                        $"run={_automatedPlan.RunId} reason=readiness_timeout.");
                    Application.Quit(2);
                }
                return;
            }

            if (!_automatedResultLogged &&
                Time.realtimeSinceStartup >= _automatedEvaluationDeadline)
            {
                EvaluateAutomatedTest(wall, authenticated);
            }
            if (_automatedResultLogged && _automatedResultPassed &&
                Time.realtimeSinceStartup >= _automatedQuitDeadline)
                Application.Quit(0);
        }

        private void EvaluateAutomatedTest(
            M1AuthoritativeWallDirector wall,
            bool authenticated)
        {
            _automatedResultLogged = true;
            var observation = CaptureObservation(wall, authenticated);
            var passed = _automatedPlan.Evaluate(observation, out var reason);
            _automatedResultPassed = passed;
            var state = wall?.ObservedState ?? default;
            Debug.Log(
                $"[GAME-M1-RESULT] {(passed ? "PASS" : "FAIL")} " +
                $"name={_automatedPlan.Name} run={_automatedPlan.RunId} reason={reason} " +
                $"players={observation.PlayerCount} connections={observation.ServerConnectionCount} " +
                $"wall={state.StateId}:{state.Revision}:{state.SignedEffort}:" +
                $"{state.IsTransitioning} completed={observation.CompletedTransitions} " +
                $"rejected={observation.RejectedTransitions} " +
                $"opposedTicks={observation.OpposedEffortTicks} snapshots={observation.Snapshots} " +
                $"targetSnapshots={observation.TargetSnapshots} " +
                $"observerSnapshots={observation.ObserverSnapshots} " +
                $"invalidSnapshots={observation.InvalidSnapshots} " +
                $"historyMisses={observation.HistoryMisses}.");
            if (!passed)
                Application.Quit(2);
        }

        private M1AutomatedTestObservation CaptureObservation(
            M1AuthoritativeWallDirector wall,
            bool authenticated)
        {
            var players = FindObjectsByType<PredictedPlayerMotor>(
                FindObjectsInactive.Exclude,
                FindObjectsSortMode.None);
            var state = wall?.ObservedState ?? default;
            var serverConnections = _networkManager.ServerManager.Started
                ? _networkManager.ServerManager.Clients.Count
                : 0;
            return new M1AutomatedTestObservation(
                authenticated,
                players.Length,
                serverConnections,
                wall != null && wall.HasObservedState,
                state.StateId,
                state.Revision,
                state.SignedEffort,
                state.IsTransitioning,
                wall?.CompletedTransitionCount ?? 0u,
                wall?.RejectedTransitionCount ?? 0u,
                wall?.OpposedEffortTickCount ?? 0u,
                wall?.SnapshotCount ?? 0u,
                wall?.TargetSnapshotCount ?? 0u,
                wall?.ObserverSnapshotCount ?? 0u,
                wall?.InvalidSnapshotCount ?? 0u,
                wall?.HistoryMissCount ?? 0u);
        }
    }
}
