using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace NotThatWay.Game
{
    public readonly struct M1AutomatedTestObservation
    {
        public M1AutomatedTestObservation(
            bool authenticated,
            int playerCount,
            int serverConnectionCount,
            bool hasWall,
            int wallStateId,
            uint wallRevision,
            int signedEffort,
            bool isTransitioning,
            uint completedTransitions,
            uint rejectedTransitions,
            uint opposedEffortTicks,
            uint snapshots,
            uint targetSnapshots,
            uint observerSnapshots,
            uint invalidSnapshots,
            uint historyMisses)
        {
            Authenticated = authenticated;
            PlayerCount = playerCount;
            ServerConnectionCount = serverConnectionCount;
            HasWall = hasWall;
            WallStateId = wallStateId;
            WallRevision = wallRevision;
            SignedEffort = signedEffort;
            IsTransitioning = isTransitioning;
            CompletedTransitions = completedTransitions;
            RejectedTransitions = rejectedTransitions;
            OpposedEffortTicks = opposedEffortTicks;
            Snapshots = snapshots;
            TargetSnapshots = targetSnapshots;
            ObserverSnapshots = observerSnapshots;
            InvalidSnapshots = invalidSnapshots;
            HistoryMisses = historyMisses;
        }

        public bool Authenticated { get; }
        public int PlayerCount { get; }
        public int ServerConnectionCount { get; }
        public bool HasWall { get; }
        public int WallStateId { get; }
        public uint WallRevision { get; }
        public int SignedEffort { get; }
        public bool IsTransitioning { get; }
        public uint CompletedTransitions { get; }
        public uint RejectedTransitions { get; }
        public uint OpposedEffortTicks { get; }
        public uint Snapshots { get; }
        public uint TargetSnapshots { get; }
        public uint ObserverSnapshots { get; }
        public uint InvalidSnapshots { get; }
        public uint HistoryMisses { get; }
    }

    /// <summary>Contrat de verdict pour les scénarios M1 lancés en deux processus.</summary>
    public readonly struct M1AutomatedTestPlan
    {
        private M1AutomatedTestPlan(
            string name,
            string runId,
            double evaluateAfterReadySeconds,
            double quitAfterSeconds,
            double readinessTimeoutSeconds,
            int expectedWallState,
            long expectedWallRevision,
            int expectedPlayers,
            int expectedServerConnections,
            uint minimumCompletedTransitions,
            uint minimumRejectedTransitions,
            uint minimumOpposedEffortTicks,
            uint minimumSnapshots,
            uint minimumTargetSnapshots)
        {
            Name = name;
            RunId = runId;
            EvaluateAfterReadySeconds = evaluateAfterReadySeconds;
            QuitAfterSeconds = quitAfterSeconds;
            ReadinessTimeoutSeconds = readinessTimeoutSeconds;
            ExpectedWallState = expectedWallState;
            ExpectedWallRevision = expectedWallRevision;
            ExpectedPlayers = expectedPlayers;
            ExpectedServerConnections = expectedServerConnections;
            MinimumCompletedTransitions = minimumCompletedTransitions;
            MinimumRejectedTransitions = minimumRejectedTransitions;
            MinimumOpposedEffortTicks = minimumOpposedEffortTicks;
            MinimumSnapshots = minimumSnapshots;
            MinimumTargetSnapshots = minimumTargetSnapshots;
        }

        public string Name { get; }
        public string RunId { get; }
        public double EvaluateAfterReadySeconds { get; }
        public double QuitAfterSeconds { get; }
        public double ReadinessTimeoutSeconds { get; }
        public int ExpectedWallState { get; }
        public long ExpectedWallRevision { get; }
        public int ExpectedPlayers { get; }
        public int ExpectedServerConnections { get; }
        public uint MinimumCompletedTransitions { get; }
        public uint MinimumRejectedTransitions { get; }
        public uint MinimumOpposedEffortTicks { get; }
        public uint MinimumSnapshots { get; }
        public uint MinimumTargetSnapshots { get; }
        public bool Enabled => QuitAfterSeconds > 0d;

        public bool IsReadyToArm(M1AutomatedTestObservation observation)
        {
            if (!observation.Authenticated || !observation.HasWall)
                return false;
            if (ExpectedPlayers >= 0 && observation.PlayerCount != ExpectedPlayers)
                return false;
            if (ExpectedServerConnections >= 0 &&
                observation.ServerConnectionCount != ExpectedServerConnections)
            {
                return false;
            }
            return true;
        }

        public static bool TryParse(
            IReadOnlyList<string> arguments,
            out M1AutomatedTestPlan plan,
            out string error)
        {
            plan = default;
            error = string.Empty;
            if (arguments == null)
            {
                error = "arguments_null";
                return false;
            }

            var values = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            var keys = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
            {
                "--m1-test-name",
                "--m1-run-id",
                "--m1-evaluate-after-ready-seconds",
                "--m1-auto-quit-seconds",
                "--m1-readiness-timeout-seconds",
                "--m1-expect-wall-state",
                "--m1-expect-wall-revision",
                "--m1-expect-players",
                "--m1-expect-connections",
                "--m1-expect-completed-min",
                "--m1-expect-rejected-min",
                "--m1-expect-opposed-ticks-min",
                "--m1-expect-snapshots-min",
                "--m1-expect-target-snapshots-min"
            };
            for (var index = 0; index < arguments.Count; index++)
            {
                var argument = arguments[index] ?? string.Empty;
                string key = null;
                string value = null;
                var equalsIndex = argument.IndexOf('=');
                if (equalsIndex > 0)
                {
                    var candidate = argument.Substring(0, equalsIndex);
                    if (keys.Contains(candidate))
                    {
                        key = candidate;
                        value = argument.Substring(equalsIndex + 1);
                    }
                }
                else if (keys.Contains(argument))
                {
                    key = argument;
                    if (index + 1 >= arguments.Count)
                    {
                        error = $"value_missing:{key}";
                        return false;
                    }
                    value = arguments[++index];
                }

                if (key == null)
                    continue;
                if (values.ContainsKey(key))
                {
                    error = $"value_duplicate:{key}";
                    return false;
                }
                values.Add(key, value ?? string.Empty);
            }

            if (!values.TryGetValue("--m1-auto-quit-seconds", out var quitText))
            {
                if (values.Count == 0)
                    return true;
                error = "quit_seconds_required";
                return false;
            }
            if (!double.TryParse(
                    quitText,
                    NumberStyles.Float,
                    CultureInfo.InvariantCulture,
                    out var quitSeconds) ||
                quitSeconds < 1d || quitSeconds > 60d)
            {
                error = "quit_seconds_invalid";
                return false;
            }

            var evaluateText = ValueOr(
                values,
                "--m1-evaluate-after-ready-seconds",
                quitText);
            if (!double.TryParse(
                    evaluateText,
                    NumberStyles.Float,
                    CultureInfo.InvariantCulture,
                    out var evaluateSeconds) ||
                evaluateSeconds < 0.5d || evaluateSeconds > quitSeconds)
            {
                error = "evaluate_seconds_invalid";
                return false;
            }
            var timeoutText = ValueOr(values, "--m1-readiness-timeout-seconds", "10");
            if (!double.TryParse(
                    timeoutText,
                    NumberStyles.Float,
                    CultureInfo.InvariantCulture,
                    out var timeoutSeconds) ||
                timeoutSeconds < 2d || timeoutSeconds > 60d)
            {
                error = "readiness_timeout_invalid";
                return false;
            }

            var name = ValueOr(values, "--m1-test-name", "unnamed").Trim();
            if (name.Length == 0 || name.Length > 48)
            {
                error = "test_name_invalid";
                return false;
            }
            var runId = ValueOr(values, "--m1-run-id", name).Trim();
            if (runId.Length == 0 || runId.Length > 64)
            {
                error = "run_id_invalid";
                return false;
            }
            if (!TryInt(values, "--m1-expect-wall-state", -1, out var wallState) ||
                wallState < -1 || wallState > 1)
            {
                error = "wall_state_invalid";
                return false;
            }
            if (!TryLong(values, "--m1-expect-wall-revision", -1L, out var revision) ||
                revision < -1L || revision > uint.MaxValue)
            {
                error = "wall_revision_invalid";
                return false;
            }
            if (!TryInt(values, "--m1-expect-players", -1, out var players) ||
                players < -1 || players > 16)
            {
                error = "players_invalid";
                return false;
            }
            if (!TryInt(values, "--m1-expect-connections", -1, out var connections) ||
                connections < -1 || connections > 16)
            {
                error = "connections_invalid";
                return false;
            }
            if (!TryUint(values, "--m1-expect-completed-min", out var completed) ||
                !TryUint(values, "--m1-expect-rejected-min", out var rejected) ||
                !TryUint(values, "--m1-expect-opposed-ticks-min", out var opposed) ||
                !TryUint(values, "--m1-expect-snapshots-min", out var snapshots) ||
                !TryUint(values, "--m1-expect-target-snapshots-min", out var targetSnapshots))
            {
                error = "minimum_invalid";
                return false;
            }

            plan = new M1AutomatedTestPlan(
                name,
                runId,
                evaluateSeconds,
                quitSeconds,
                timeoutSeconds,
                wallState,
                revision,
                players,
                connections,
                completed,
                rejected,
                opposed,
                snapshots,
                targetSnapshots);
            return true;
        }

        public bool Evaluate(M1AutomatedTestObservation observation, out string reason)
        {
            var failures = new StringBuilder();
            AddFailure(!observation.Authenticated, "not_authenticated", failures);
            AddFailure(
                ExpectedPlayers >= 0 && observation.PlayerCount != ExpectedPlayers,
                $"players={observation.PlayerCount}!={ExpectedPlayers}",
                failures);
            AddFailure(
                ExpectedServerConnections >= 0 &&
                observation.ServerConnectionCount != ExpectedServerConnections,
                $"connections={observation.ServerConnectionCount}!={ExpectedServerConnections}",
                failures);

            var requiresWall = ExpectedWallState >= 0 || ExpectedWallRevision >= 0 ||
                               MinimumCompletedTransitions > 0u || MinimumRejectedTransitions > 0u ||
                               MinimumOpposedEffortTicks > 0u;
            AddFailure(requiresWall && !observation.HasWall, "wall_unavailable", failures);
            AddFailure(
                ExpectedWallState >= 0 && observation.WallStateId != ExpectedWallState,
                $"wall_state={observation.WallStateId}!={ExpectedWallState}",
                failures);
            AddFailure(
                ExpectedWallRevision >= 0 && observation.WallRevision != (uint)ExpectedWallRevision,
                $"wall_revision={observation.WallRevision}!={ExpectedWallRevision}",
                failures);
            AddFailure(requiresWall && observation.SignedEffort != 0,
                $"signedEffort={observation.SignedEffort}", failures);
            AddFailure(requiresWall && observation.IsTransitioning,
                "wall_transitioning", failures);
            AddFailure(
                observation.CompletedTransitions < MinimumCompletedTransitions,
                $"completed={observation.CompletedTransitions}<{MinimumCompletedTransitions}",
                failures);
            AddFailure(
                observation.RejectedTransitions < MinimumRejectedTransitions,
                $"rejected={observation.RejectedTransitions}<{MinimumRejectedTransitions}",
                failures);
            AddFailure(
                observation.OpposedEffortTicks < MinimumOpposedEffortTicks,
                $"opposedTicks={observation.OpposedEffortTicks}<{MinimumOpposedEffortTicks}",
                failures);
            AddFailure(
                observation.Snapshots < MinimumSnapshots,
                $"snapshots={observation.Snapshots}<{MinimumSnapshots}",
                failures);
            AddFailure(
                observation.TargetSnapshots < MinimumTargetSnapshots,
                $"targetSnapshots={observation.TargetSnapshots}<{MinimumTargetSnapshots}",
                failures);
            AddFailure(observation.InvalidSnapshots != 0u,
                $"invalidSnapshots={observation.InvalidSnapshots}", failures);
            AddFailure(observation.HistoryMisses != 0u,
                $"historyMisses={observation.HistoryMisses}", failures);

            reason = failures.Length == 0 ? "ok" : failures.ToString();
            return failures.Length == 0;
        }

        private static string ValueOr(
            IReadOnlyDictionary<string, string> values,
            string key,
            string fallback) => values.TryGetValue(key, out var value) ? value : fallback;

        private static bool TryInt(
            IReadOnlyDictionary<string, string> values,
            string key,
            int fallback,
            out int value)
        {
            var text = ValueOr(values, key, fallback.ToString(CultureInfo.InvariantCulture));
            return int.TryParse(text, NumberStyles.Integer, CultureInfo.InvariantCulture, out value);
        }

        private static bool TryLong(
            IReadOnlyDictionary<string, string> values,
            string key,
            long fallback,
            out long value)
        {
            var text = ValueOr(values, key, fallback.ToString(CultureInfo.InvariantCulture));
            return long.TryParse(text, NumberStyles.Integer, CultureInfo.InvariantCulture, out value);
        }

        private static bool TryUint(
            IReadOnlyDictionary<string, string> values,
            string key,
            out uint value)
        {
            var text = ValueOr(values, key, "0");
            return uint.TryParse(text, NumberStyles.Integer, CultureInfo.InvariantCulture, out value);
        }

        private static void AddFailure(bool condition, string code, StringBuilder failures)
        {
            if (!condition)
                return;
            if (failures.Length > 0)
                failures.Append(';');
            failures.Append(code);
        }
    }
}
